#!/usr/bin/env node
/* =====================================================================
   План-табель служебной деятельности · WFM — сервер ЛВС (воссоздан по
   протоколу клиента 3.18/3.19, README и релиз-нотам).
   HTTP-раздача приложения, WS-синхронизация канона, операционный
   протокол (ops), аутентификация и права (deny на сервере), мессенджер,
   журнал сигналов с квитированием, /health, /status, /admin, реплика,
   квоты публикаций, аудит с ротацией, cron-дайджест, раздача /ocr/*.

   Запуск:  node server/sync-server.mjs
   Переменные окружения:
     PT_PORT=8787 PT_HOST=0.0.0.0
     PT_FILE           раздаваемый HTML (по умолчанию: ищет План-табель-WFM-*.html рядом,
                       приоритет -offline)
     PT_CANON=plan-tabel-canon.json      канон базы
     PT_HIST_DIR=plan-tabel-hist         история канона (откат из /admin)
     PT_AUDIT=plan-tabel-server-audit.jsonl  PT_AUDIT_MAX_MB=5
     PT_USERS_FILE                       users.json — включает аутентификацию
     PT_SIG_FILE=plan-tabel-sigs.json    журнал сигналов (до 600)
     PT_CHAT_FILE=plan-tabel-chat.json   история чата (PT_CHAT_MAX=500)
     PT_QUOTA='editor:300,hr:500'        суточные квоты публикаций по ролям
     PT_REPLICA_OF=ws://primary:8787     режим резервного узла (только чтение)
     PT_SHARED_SECRET                    общий секрет реплик
     PT_DIGEST_CRON='08:30,17:00'        дайджест в чат (PT_DIGEST_OUT, PT_DIGEST_WEBHOOK)
     PT_OCR_DIR=server/ocr               ассеты OCR для раздачи /ocr/*
     PT_SSO_HEADER=X-Forwarded-User      3.34: доверенный заголовок SSO-реверс-прокси
     PT_SSO_NAME_HEADER=X-Forwarded-Name 3.34: ФИО из прокси (для авторегистрации)
     PT_SSO_ROLE=viewer                  3.34: роль автозарегистрированных SSO-пользователей
     PT_SSO_PROVISION=1                  3.34: 0 — запретить авторегистрацию (только существующие)
     PT_XCHG_FILE=plan-tabel-xchg.json   3.35: журнал обмена (выгрузки/импорты, до PT_XCHG_MAX=300)
     PT_MAP_FILE=plan-tabel-xchg-map.json 3.35: справочник сопоставления кодов Т-13 ↔ причины
     PT_BRIG_FILE=plan-tabel-brigades.json 3.49: общий справочник бригад ротаций
     PT_BRIG_QUOTA='editor:60,tab:120'        3.55: часовые квоты PUT /api/v1/brigades по ролям
     PT_BUDGET_FILE=plan-tabel-budgets.json 3.53: общий справочник лимитов ФОТ
   Обмен 3.34: GET/POST /api/v1/tabel (табель для «1С»), POST /api/v1/skud (события СКУД → факт).
   Обмен 3.35: GET/PUT /api/v1/xchg/map — справочник сопоставления кодов Т-13 с валидацией;
   GET /api/v1/tabel?map=1c и POST /api/v1/tabel {map:"1c"} — конвертация кодов по справочнику;
   GET /api/v1/xchg/log — журнал выгрузок/импортов; POST /api/v1/xchg/retry {id} — повтор
   неудачной операции по сохранённому запросу (с учётом прав и комплаенса закрытых периодов).
   ===================================================================== */
import http from 'node:http';
import {createHash,randomBytes} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createCipheriv,createDecipheriv} from 'node:crypto';
import {createRequire} from 'node:module';
import {readFile,writeFile,appendFile,rename,mkdir,readdir,stat,unlink} from 'node:fs/promises';
import {existsSync,readFileSync,writeFileSync,mkdirSync,readdirSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {WebSocketServer,WebSocket} from 'ws';

const __dirname=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(__dirname,'..');
const E=k=>process.env[k];
const PORT=+(E('PT_PORT')||8787);
const HOST=E('PT_HOST')||'0.0.0.0';
const USERS_FILE=E('PT_USERS_FILE')?path.resolve(E('PT_USERS_FILE')):null;
const CANON_FILE=path.resolve(E('PT_CANON')||path.join(__dirname,'plan-tabel-canon.json'));
const HIST_DIR=path.resolve(E('PT_HIST_DIR')||path.join(__dirname,'plan-tabel-hist'));
const AUDIT_FILE=path.resolve(E('PT_AUDIT')||path.join(__dirname,'plan-tabel-server-audit.jsonl'));
const AUDIT_MAX=+(E('PT_AUDIT_MAX_MB')||5)*1024*1024;
const SIG_FILE=path.resolve(E('PT_SIG_FILE')||path.join(__dirname,'plan-tabel-sigs.json'));
const CHAT_FILE=path.resolve(E('PT_CHAT_FILE')||path.join(__dirname,'plan-tabel-chat.json'));
const CHAT_MAX=+(E('PT_CHAT_MAX')||500);
const OCR_DIR=path.resolve(E('PT_OCR_DIR')||path.join(__dirname,'ocr'));
/* 3.35: журнал обмена и справочник сопоставления кодов «1С» */
const XCHG_FILE=path.resolve(E('PT_XCHG_FILE')||path.join(__dirname,'plan-tabel-xchg.json'));
const XCHG_MAX=+(E('PT_XCHG_MAX')||300);
const MAP_FILE=path.resolve(E('PT_MAP_FILE')||path.join(__dirname,'plan-tabel-xchg-map.json'));
const PAY_MAX=200*1024;   /* потолок сохраняемого payload для ретрая (байт JSON-строки) */
const REPLICA_OF=E('PT_REPLICA_OF')||'';
const SHARED_SECRET=E('PT_SHARED_SECRET')||'';
/* 3.34: SSO — доверенные заголовки реверс-прокси */
const SSO_HEADER=(E('PT_SSO_HEADER')||'').trim().toLowerCase();
const SSO_NAME_HEADER=(E('PT_SSO_NAME_HEADER')||'').trim().toLowerCase();
const SSO_ROLE=E('PT_SSO_ROLE')||'viewer';
const SSO_PROVISION=E('PT_SSO_PROVISION')!=='0';
const DIGEST_TIMES=(E('PT_DIGEST_CRON')||'').split(',').map(s=>s.trim()).filter(Boolean);
const GZ_PREFIX='GZ1:';
const VER='3.35';
/* 3.22: счётчики для /metrics (Prometheus) */
const MET={pushes:0,opsBatches:0,opsApplied:0,denies:0,authFail:0,backups:0,sso:0,tabel:0,skud:0,xchg:{},xchgRetry:0};   /* 3.35: +журнал обмена */
/* 3.23: резервные копии канона по расписанию */
const BACKUP_DIR=path.resolve(E('PT_BACKUP_DIR')||path.join(__dirname,'backups'));
const BACKUP_KEEP=+(E('PT_BACKUP_KEEP')||14);
const BACKUP_TIMES=(E('PT_BACKUP_CRON')||'').split(',').map(x=>x.trim()).filter(Boolean);
const BACKUP_EVERY_MIN=E('PT_BACKUP_CRON')?null:+(E('PT_BACKUP_EVERY_MIN')||360);
let lastBackupTs=0,lastBackupKey='';

/* ---------- утилиты ---------- */
const now=()=>Date.now();
const j=async(f,def)=>{try{return JSON.parse(await readFile(f,'utf8'))}catch(e){return def}};
const jSync=(f,def)=>{try{return JSON.parse(readFileSync(f,'utf8'))}catch(e){return def}};
const save=async(f,obj)=>{await writeFile(f,JSON.stringify(obj))};
const sha256=s=>createHash('sha256').update(s).digest('hex');
const hashPin=pin=>'s2$'+sha256('planTabel$'+pin);
const gzEnc=obj=>GZ_PREFIX+gzipSync(Buffer.from(JSON.stringify(obj),'utf8')).toString('base64');
const gzDec=s=>JSON.parse(gunzipSync(Buffer.from(String(s).slice(GZ_PREFIX.length),'base64')).toString('utf8'));
function canonDecode(c){
  if(!c)return null;
  try{return c.gz?gzDec(c.gz):(c.data?JSON.parse(c.data):null)}catch(e){return null}
}
async function audit(ev,detail,extra){
  const rec={ts:now(),ev,detail:detail||'',...(extra||{})};
  try{
    const st=await stat(AUDIT_FILE).catch(()=>null);
    if(st&&st.size>AUDIT_MAX)await rename(AUDIT_FILE,AUDIT_FILE+'.1').catch(()=>{});
    await appendFile(AUDIT_FILE,JSON.stringify(rec)+'\n');
  }catch(e){}
  if(ev==='deny'||ev==='admin-deny')MET.denies++;
  if(ev==='auth-fail')MET.authFail++;
  AUDIT_MEM.unshift(rec);if(AUDIT_MEM.length>500)AUDIT_MEM.length=500;
}
const AUDIT_MEM=[];

/* ---------- матрица ролей (зеркалит клиентскую ROLE_PERM) ---------- */
const ROLE_PERM={
  admin:{admin:1,edit:1,staff:1,import:1,sign:1,chat:1,brig:1,budget:1},
  hr:{edit:1,staff:1,import:1,sign:1,chat:1,brig:1,budget:1},
  editor:{edit:1,sign:1,chat:1,brig:1},
  tab:{edit:1,planOnly:1,chat:1,brig:1},
  viewer:{chat:0}
};
function permsOf(u){
  const base={...(ROLE_PERM[u&&u.role]||ROLE_PERM.viewer||{})};
  if(u&&Array.isArray(u.allow))u.allow.forEach(k=>base[k]=1);
  if(u&&Array.isArray(u.deny))u.deny.forEach(k=>base[k]=0);   /* deny имеет приоритет */
  return base;
}
const can=(u,k)=>!!permsOf(u)[k];

/* ---------- пользователи ---------- */
let USERS=null;   /* null = аутентификация выключена */
async function loadUsers(){
  if(!USERS_FILE){USERS=null;return}
  const d=await j(USERS_FILE,{users:[]});
  USERS=Array.isArray(d)?d:(d.users||[]);
}
async function saveUsers(){if(USERS_FILE&&USERS)await save(USERS_FILE,{users:USERS})}
const findUser=l=>USERS?USERS.find(u=>u.login===l):null;
/* 3.34: SSO — разрешение пользователя по доверенному заголовку (с авторегистрацией) */
async function ssoUser(login,name){
  if(!USERS||!SSO_HEADER)return null;
  login=String(login||'').trim().slice(0,60);
  if(!login)return null;
  let u=findUser(login);
  if(!u){
    if(!SSO_PROVISION)return null;
    u={login,pinHash:'',role:SSO_ROLE,emp:null,allow:[],deny:[],modsOff:[],blocked:false,sso:true};
    if(name)u.name=String(name).slice(0,80);
    USERS.push(u);await saveUsers();
    await audit('sso-provision','авторегистрация через SSO: '+login+' ('+SSO_ROLE+')');
  }
  if(u.blocked)return null;
  MET.sso++;
  return u;
}
loadUsers();

/* ---------- токены сессий ---------- */
const TOKENS=new Map();   /* token -> {login,role,emp,allow,deny,modsOff,ts} */
function issueToken(u){
  const t=randomBytes(24).toString('base64url');
  TOKENS.set(t,{login:u.login,role:u.role||'viewer',emp:u.emp||null,
    allow:u.allow||[],deny:u.deny||[],modsOff:u.modsOff||[],ts:now()});
  return t;
}
const tokUser=t=>{const s=t&&TOKENS.get(t);return s||null};
const ANON={login:'',role:'viewer',emp:null,allow:[],deny:[],modsOff:[]};
function authOf(msg,sock){
  if(!USERS)return{u:{login:(msg&&msg.by)||sock.by||'',role:'admin',emp:null,allow:[],deny:[],modsOff:[]},need:false};
  const s=tokUser(msg&&msg.token)||tokUser(sock.token);
  return{u:s||ANON,need:true,ok:!!s};
}

/* ---------- квоты публикаций ---------- */
const QUOTAS={};   /* role -> лимит в сутки */
(E('PT_QUOTA')||'').split(',').forEach(p=>{const[k,v]=p.split(':');if(k&&+v>0)QUOTAS[k.trim()]=+v});
/* ===== 3.55: часовые квоты PUT /api/v1/brigades по ролям ===== */
const BRIG_QUOTAS={};
(E('PT_BRIG_QUOTA')||'').split(',').forEach(p=>{const[k,v]=p.split(':');if(k&&+v>0)BRIG_QUOTAS[k.trim()]=+v});
const BRIG_QUOTA_USED={};
const brigHourKey=()=>Math.floor(now()/3600000);
function brigQuotaLeft(role){
  const q=BRIG_QUOTAS[role||''];if(!q)return Infinity;
  const used=BRIG_QUOTA_USED[(role||'')+':'+brigHourKey()]||0;
  return Math.max(0,q-used);
}
function brigQuotaUse(role){BRIG_QUOTA_USED[(role||'')+':'+brigHourKey()]=(BRIG_QUOTA_USED[(role||'')+':'+brigHourKey()]||0)+1}
const QUOTA_USED={};   /* 'role|YYYY-MM-DD' -> n */
function quotaLeft(role){
  const lim=QUOTAS[role];if(lim==null)return null;
  const day=new Date().toISOString().slice(0,10);
  const used=QUOTA_USED[role+'|'+day]||0;
  return Math.max(0,lim-used);
}
function quotaUse(role){
  if(QUOTAS[role]==null)return;
  const day=new Date().toISOString().slice(0,10),k=role+'|'+day;
  QUOTA_USED[k]=(QUOTA_USED[k]||0)+1;
}

/* ---------- канон и история ---------- */
let CANON=null;              /* {counter,ts,by,org,gz|data} */
let REPLICA_OFF=false;       /* повысили реплику до primary */
/* ===== 3.30: ХРАНИЛИЩЕ КАНОНА: JSON-файл (по умолчанию) или SQLite (PT_DB),
   опционально шифрование at rest AES-256-GCM (PT_CANON_KEY) — 152-ФЗ ===== */
const DB_FILE=E('PT_DB')?path.resolve(E('PT_DB')):null;
const CANON_KEY=E('PT_CANON_KEY')||'';
let DB=null;
const requireSql=createRequire(import.meta.url);
function encWrap(obj){
  if(!CANON_KEY)return JSON.stringify(obj);
  const iv=randomBytes(12);
  const c=createCipheriv('aes-256-gcm',createHash('sha256').update(CANON_KEY).digest(),iv);
  const data=Buffer.concat([c.update(JSON.stringify(obj),'utf8'),c.final()]);
  return JSON.stringify({enc:'aes-256-gcm',iv:iv.toString('base64'),tag:c.getAuthTag().toString('base64'),data:data.toString('base64')});
}
function decWrap(txt){
  if(txt==null)return null;
  let o;try{o=JSON.parse(txt)}catch(e){return null}
  if(o&&o.enc==='aes-256-gcm'){
    if(!CANON_KEY)return null;
    try{
      const d=createDecipheriv('aes-256-gcm',createHash('sha256').update(CANON_KEY).digest(),Buffer.from(o.iv,'base64'));
      d.setAuthTag(Buffer.from(o.tag,'base64'));
      return JSON.parse(Buffer.concat([d.update(Buffer.from(o.data,'base64')),d.final()]).toString('utf8'));
    }catch(e){return null}
  }
  return o;
}
async function initDb(){
  if(DB)return;
  const initSqlJs=requireSql('sql.js');
  const wasmDir=path.dirname(requireSql.resolve('sql.js'));   /* dist/ пакет sql.js */
  const SQ=await initSqlJs({locateFile:f=>path.join(wasmDir,f)});
  let bytes=null;
  try{
    const raw=await readFile(DB_FILE,'utf8');
    const w=decWrap(raw);
    if(w&&w.dbB64)bytes=Buffer.from(w.dbB64,'base64');
  }catch(e){}
  DB=bytes?new SQ.Database(bytes):new SQ.Database();
  DB.run('CREATE TABLE IF NOT EXISTS canon(id INTEGER PRIMARY KEY CHECK(id=1), counter INT, ts INT, by TEXT, gz TEXT)');
  DB.run('CREATE TABLE IF NOT EXISTS hist(counter INT PRIMARY KEY, ts INT, by TEXT, gz TEXT)');
  DB.run('CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)');
}
function dbReadCanon(){
  if(!DB)return null;
  const r=DB.exec('SELECT counter,ts,by,gz FROM canon WHERE id=1');
  if(!r.length||!r[0].values.length)return null;
  const v=r[0].values[0];
  return{counter:v[0],ts:v[1],by:v[2],gz:v[3]};
}
async function loadCanon(){
  if(CANON&&CANON.gz&&!CANON.data)return;   /* нормализация ниже в persist */
  if(DB_FILE){
    try{
      await initDb();
      const c=dbReadCanon();
      if(c){CANON=c;return}
    }catch(e){await audit('db-error','SQLite: '+String(e.message||e).slice(0,160))}
  }
  const txt=await readFile(CANON_FILE,'utf8').catch(()=>null);
  CANON=txt?decWrap(txt):null;
  /* миграция JSON → SQLite при первом запуске с PT_DB */
  if(DB_FILE&&CANON)await persistCanon();
}
async function persistCanon(){
  if(CANON&&!CANON.gz&&CANON.data){try{CANON.gz=gzEnc(JSON.parse(CANON.data));CANON.data=null}catch(e){}}
  if(DB){
    try{
      DB.run('REPLACE INTO canon(id,counter,ts,by,gz) VALUES(1,?,?,?,?)',[CANON.counter,CANON.ts,CANON.by||'',CANON.gz||'']);
      DB.run('REPLACE INTO hist(counter,ts,by,gz) VALUES(?,?,?,?)',[CANON.counter,CANON.ts,CANON.by||'',CANON.gz||'']);
      DB.run('DELETE FROM hist WHERE counter NOT IN (SELECT counter FROM hist ORDER BY counter DESC LIMIT 50)');
      const cutoff=now()-(+(E('PT_HIST_DAYS')||30))*864e5;
      DB.run('DELETE FROM hist WHERE ts<'+cutoff);
      const bytes=Buffer.from(DB.export());
      await writeFile(DB_FILE,CANON_KEY?encWrap({dbB64:bytes.toString('base64')}):bytes);
      return;
    }catch(e){await audit('db-error','SQLite persist: '+String(e.message||e).slice(0,160))}
  }
  try{await writeFile(CANON_FILE,encWrap(CANON))}catch(e){}
  try{
    await mkdir(HIST_DIR,{recursive:true});
    if(CANON)await writeFile(path.join(HIST_DIR,`${String(CANON.counter).padStart(6,'0')}-${CANON.ts}.json`),encWrap(CANON));
    let files=(await readdir(HIST_DIR)).sort();
    while(files.length>50){const f=files.shift();await unlink(path.join(HIST_DIR,f)).catch(()=>{})}
    /* 3.22: ротация по возрасту (имя файла содержит ts) */
    const cutoff=now()-(+(E('PT_HIST_DAYS')||30))*864e5;
    for(const f of files){
      const ts=+(f.replace('.json','').split('-')[1]||0);
      if(ts&&ts<cutoff)await unlink(path.join(HIST_DIR,f)).catch(()=>{});
    }
  }catch(e){}
}
await loadCanon();

/* ---------- сигналы ---------- */
let SIGS=await j(SIG_FILE,{sigs:[]});
if(!Array.isArray(SIGS.sigs))SIGS={sigs:[]};
const persistSigs=()=>save(SIG_FILE,SIGS).catch(()=>{});

/* ---------- чат ---------- */
let CHAT=await j(CHAT_FILE,{msgs:[]});
if(!Array.isArray(CHAT.msgs))CHAT={msgs:[]};
const persistChat=()=>save(CHAT_FILE,{msgs:CHAT.msgs.slice(-CHAT_MAX)}).catch(()=>{});

/* ---------- 3.35: журнал обмена (выгрузки/импорты «1С»/СКУД/OCR) и справочник кодов Т-13 ---------- */
let XCHG=await j(XCHG_FILE,{items:[]});
if(!XCHG||!Array.isArray(XCHG.items))XCHG={items:[]};
XCHG.items=XCHG.items.slice(0,XCHG_MAX);
const persistXchg=()=>save(XCHG_FILE,{items:XCHG.items.slice(0,XCHG_MAX)}).catch(()=>{});
let XMAP=await j(MAP_FILE,{items:[],ts:0,by:''});
if(!XMAP||!Array.isArray(XMAP.items))XMAP={items:[],ts:0,by:''};
const persistXmap=()=>save(MAP_FILE,XMAP).catch(()=>{});
/* ===== 3.49: общий справочник бригад ротаций (GET/PUT /api/v1/brigades) ===== */
const BRIG_FILE=path.resolve(E('PT_BRIG_FILE')||path.join(__dirname,'plan-tabel-brigades.json'));
let BRIG=await j(BRIG_FILE,{items:[],ts:0,by:''});
if(!BRIG||!Array.isArray(BRIG.items))BRIG={items:[],ts:0,by:''};
const persistBrig=()=>save(BRIG_FILE,BRIG).catch(()=>{});
/* ===== 3.53: общий справочник лимитов ФОТ (GET/PUT /api/v1/budgets) ===== */
const BUDG_FILE=path.resolve(E('PT_BUDGET_FILE')||path.join(__dirname,'plan-tabel-budgets.json'));
let BUDG=await j(BUDG_FILE,{items:{},ts:0,by:''});
if(!BUDG||typeof BUDG.items!=='object'||Array.isArray(BUDG.items))BUDG={items:{},ts:0,by:''};
const persistBudg=()=>save(BUDG_FILE,BUDG).catch(()=>{});
/* коды унифицированной формы Т-13 (зеркалит клиентский T13_REASONS) */
const T13_CODES=['Я','Н','РВ','С','К','ОТ','ОД','Б','ДО','У','ПР','НН','НС','В'];
function buildAutoMap(st){
  /* авто-сопоставление: код Т-13 равен коду причины или входит в её алиасы */
  const reasons=(st&&st.reasons)||[],byCode={},byAlias={};
  reasons.forEach(r=>{const c=String(r.code||'').toUpperCase();if(c)byCode[c]=r;
    (r.aliases||[]).forEach(a=>{const ac=String(a||'').toUpperCase();if(ac&&byAlias[ac]===undefined)byAlias[ac]=r})});
  const m={},missing=[];
  for(const t of T13_CODES){const r=byCode[t]||byAlias[t];if(r)m[t]=String(r.code);else missing.push(t)}
  return{map:m,missing};
}
function eff1cMap(st){
  /* эффективный справочник: авто-правила + сохранённые переопределения (XMAP); local='' — снято */
  const m={...buildAutoMap(st).map};
  for(const it of XMAP.items){
    const t=String(it.t13||'').toUpperCase();if(!t)continue;
    const l=String(it.local||'');
    if(l)m[t]=l;else delete m[t];
  }
  return m;
}
function rev1cMap(m){
  /* обратный справочник local→Т-13: приоритет у точного совпадения кода */
  const rev={};
  for(const t of T13_CODES){const l=m[t];if(!l)continue;
    if(rev[l]===undefined||String(l).toUpperCase()===t)rev[l]=t}
  for(const t in m){const l=m[t];if(l&&rev[l]===undefined)rev[l]=t}
  return rev;
}
function xjAdd(kind,dir,status,detail,counters,payload,by,extra){
  let pay=null,tooBig=false;
  if(payload!=null){try{const ps=JSON.stringify(payload);if(ps.length<=PAY_MAX)pay=payload;else tooBig=true}catch(e){tooBig=true}}
  const rec={id:'x'+now().toString(36)+Math.random().toString(36).slice(2,6),ts:now(),
    kind,dir,status,detail:String(detail||'').slice(0,300),counters:counters||{},
    payload:pay,payloadTooBig:tooBig,by:String(by||'').slice(0,40),retries:0,...(extra||{})};
  XCHG.items.unshift(rec);if(XCHG.items.length>XCHG_MAX)XCHG.items.length=XCHG_MAX;
  persistXchg();
  const kk=kind+'|'+status;MET.xchg[kk]=(MET.xchg[kk]||0)+1;
  try{broadcast({type:'xchg',id:rec.id,kind,dir,status,detail:rec.detail,counters:rec.counters,ts:rec.ts,by:rec.by,retryOf:rec.retryOf||null})}catch(e){}
  return rec;
}
function xjList(limit,kind,status){
  let L=XCHG.items;
  if(kind)L=L.filter(x=>x.kind===kind);
  if(status)L=L.filter(x=>x.status===status);
  const total=L.length;
  L=L.slice(0,Math.max(1,Math.min(500,+limit||50)));
  return{total,items:L.map(x=>({...x,payload:undefined,hasPayload:!!x.payload}))};
}

/* ---------- HTTP ---------- */
function findAppFile(){
  if(E('PT_FILE'))return path.resolve(E('PT_FILE'));
  try{
    /* поиск HTML приложения рядом с сервером: приоритет свежей offline-сборке, затем обычной */
    const all=readdirSync(ROOT).filter(f=>/\.html$/i.test(f)&&/План-табель/.test(f));
    const score=f=>(f.includes('offline')?100:0)+(parseFloat((f.match(/WFM-([0-9.]+)/)||[0,'0'])[1])||0);
    all.sort((a,b)=>score(b)-score(a));
    return all.length?path.join(ROOT,all[0]):null;
  }catch(e){return null}
}
const APP_FILE=findAppFile();

const MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8',
  '.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json',
  '.gz':'application/gzip','.wasm':'application/wasm','.png':'image/png','.jpg':'image/jpeg',
  '.svg':'image/svg+xml','.ico':'image/x-icon','.woff2':'font/woff2'};

const server=http.createServer(async(req,res)=>{
  const u=new URL(req.url,'http://x');
  const p=u.pathname;
  try{
    if(p.startsWith('/api/v1/')){return apiHttp(req,res,u,p)}   /* 3.30: REST API */
    if(p==='/'||p==='/index.html'){
      if(!APP_FILE||!existsSync(APP_FILE)){res.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'});return res.end('PT_FILE не задан и HTML приложения не найден рядом с сервером')}
      const buf=await readFile(APP_FILE);
      res.writeHead(200,{'Content-Type':MIME['.html'],'Cache-Control':'no-store'});
      return res.end(buf);
    }
    if(p==='/health'){
      res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'});
      const rtts=[...CLIENTS].map(c=>c.rtt).filter(v=>v!=null);
      return res.end(JSON.stringify({app:'План-табель служебной деятельности · WFM',ver:VER,
        clients:WSS?WSS.clients.size:0,auth:!!USERS,replica:!!(REPLICA_OF&&!REPLICA_OFF),
        counter:CANON?CANON.counter:0,ts:CANON?CANON.ts:null,uptime:process.uptime(),
        rttAvgMs:rtts.length?Math.round(rtts.reduce((a,b)=>a+b,0)/rtts.length):null,
        db:DB?'sqlite':'json',encrypted:!!CANON_KEY,sso:!!SSO_HEADER,
        xchg:XCHG.items.length,xchgMap:XMAP.items.length}));   /* 3.35: +журнал обмена и справочник Т-13 */
    }
    if(p==='/metrics'){   /* 3.22: Prometheus-метрики */
      const rtts=[...CLIENTS].map(c=>c.rtt).filter(v=>v!=null);
      const rttAvg=rtts.length?Math.round(rtts.reduce((a,b)=>a+b,0)/rtts.length):-1;
      const lines=[
        ['# HELP wfm_clients_connected Подключённые WS-клиенты','# TYPE wfm_clients_connected gauge','wfm_clients_connected '+WSS.clients.size],
        ['# HELP wfm_canon_counter Версия канона','# TYPE wfm_canon_counter counter','wfm_canon_counter '+(CANON?CANON.counter:0)],
        ['# HELP wfm_canon_updated_ts_ms Время последнего обновления канона (unix ms)','# TYPE wfm_canon_updated_ts_ms gauge','wfm_canon_updated_ts_ms '+(CANON?CANON.ts:0)],
        ['# HELP wfm_rtt_avg_ms Средний RTT WS-пинга по клиентам','# TYPE wfm_rtt_avg_ms gauge','wfm_rtt_avg_ms '+rttAvg],
        ['# HELP wfm_pushes_total Принятые полные публикации канона','# TYPE wfm_pushes_total counter','wfm_pushes_total '+MET.pushes],
        ['# HELP wfm_ops_batches_total Принятые батчи операций','# TYPE wfm_ops_batches_total counter','wfm_ops_batches_total '+MET.opsBatches],
        ['# HELP wfm_ops_applied_total Применённые операции','# TYPE wfm_ops_applied_total counter','wfm_ops_applied_total '+MET.opsApplied],
        ['# HELP wfm_denies_total Отказы серверных прав (deny)','# TYPE wfm_denies_total counter','wfm_denies_total '+MET.denies],
        ['# HELP wfm_signals_total Сигналов в журнале','# TYPE wfm_signals_total gauge','wfm_signals_total '+SIGS.sigs.length],
        ['# HELP wfm_chat_messages_total Сообщений чата в хранилище','# TYPE wfm_chat_messages_total gauge','wfm_chat_messages_total '+CHAT.msgs.length],
        ['# HELP wfm_auth_fail_total Неудачных входов','# TYPE wfm_auth_fail_total counter','wfm_auth_fail_total '+MET.authFail],
        ['# HELP wfm_backups_total Создано резервных копий канона','# TYPE wfm_backups_total counter','wfm_backups_total '+MET.backups],
        ['# HELP wfm_sso_auth_total Входов через SSO-заголовок','# TYPE wfm_sso_auth_total counter','wfm_sso_auth_total '+MET.sso],
        ['# HELP wfm_tabel_total Запросы обмена табелем (1С)','# TYPE wfm_tabel_total counter','wfm_tabel_total '+MET.tabel],
        ['# HELP wfm_skud_days_total Дней факта из событий СКУД','# TYPE wfm_skud_days_total counter','wfm_skud_days_total '+MET.skud],
        ['# HELP wfm_xchg_total Операции обмена по журналу (выгрузки/импорты)','# TYPE wfm_xchg_total counter',
          Object.keys(MET.xchg).map(kk=>{const i=kk.indexOf('|');return'wfm_xchg_total{kind="'+kk.slice(0,i)+'",status="'+kk.slice(i+1)+'"} '+MET.xchg[kk]}).join('\n')],
        ['# HELP wfm_xchg_retries_total Повторы операций обмена из журнала','# TYPE wfm_xchg_retries_total counter','wfm_xchg_retries_total '+MET.xchgRetry],
        ['# HELP wfm_xchg_journal_entries Записей в журнале обмена','# TYPE wfm_xchg_journal_entries gauge','wfm_xchg_journal_entries '+XCHG.items.length],
        ['# HELP wfm_xchg_map_items Строк в справочнике сопоставления Т-13','# TYPE wfm_xchg_map_items gauge','wfm_xchg_map_items '+XMAP.items.length],
        ['# HELP wfm_uptime_seconds Аптайм процесса','# TYPE wfm_uptime_seconds gauge','wfm_uptime_seconds '+Math.round(process.uptime())],
      ];
      res.writeHead(200,{'Content-Type':'text/plain; version=0.0.4; charset=utf-8','Cache-Control':'no-store'});
      return res.end(lines.map(x=>x.join('\n')).join('\n')+'\n');
    }
    if(p==='/status'){
      const body={app:'WFM',ver:VER,node:REPLICA_OF&&!REPLICA_OFF?'replica':'primary',
        primary:REPLICA_OF||null,clients:WSS?WSS.clients.size:0,auth:!!USERS,sso:!!SSO_HEADER,   /* 3.34 */
        canon:CANON?{counter:CANON.counter,ts:CANON.ts,by:CANON.by,size:CANON.gz?CANON.gz.length:0}:null,
        signals:SIGS.sigs.length,chat:CHAT.msgs.length,uptime:process.uptime()};
      if(u.searchParams.get('json')!=null||req.headers.accept?.includes('application/json')){
        res.writeHead(200,{'Content-Type':'application/json'});return res.end(JSON.stringify(body));
      }
      res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});
      return res.end(`<!doctype html><meta charset=utf-8><title>WFM · статус</title><meta http-equiv=refresh content=5>
        <body style="font:14px/1.6 system-ui;margin:24px;background:#0c1220;color:#e6ecf7">
        <h2>🛰 Узел синхронизации WFM ${VER}</h2><pre style="background:#141c2e;padding:14px;border-radius:10px">${JSON.stringify(body,null,2).replace(/</g,'&lt;')}</pre>
        <p><a style="color:#7fb0ff" href="/">Открыть приложение</a> · <a style="color:#7fb0ff" href="/admin">Администрирование</a></p>`);
    }
    if(p==='/admin'||p.startsWith('/admin/')){return adminHttp(req,res,u)}
    if(p.startsWith('/ocr/')){
      const rel=decodeURIComponent(p.slice(5)).replace(/\.\./g,'');
      const f=path.join(OCR_DIR,rel);
      if(!f.startsWith(OCR_DIR)||!existsSync(f)){res.writeHead(404);return res.end('not found')}
      const buf=await readFile(f);
      res.writeHead(200,{'Content-Type':MIME[path.extname(f)]||'application/octet-stream','Cache-Control':'public, max-age=3600'});
      return res.end(buf);
    }
    res.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'});res.end('не найдено');
  }catch(e){
    res.writeHead(500,{'Content-Type':'text/plain; charset=utf-8'});res.end('ошибка сервера: '+e.message);
  }
});

/* ---------- 3.31: серверный OCR (Tesseract в Node, ассеты server/ocr) ---------- */
let OCR_WORKERS=null;
function ocrWorker(lang){
  OCR_WORKERS=OCR_WORKERS||new Map();
  if(!OCR_WORKERS.has(lang)){
    const T=requireSql('tesseract.js');
    /* в Node воркер tesseract.js свой (worker_threads): переопределяем только
       corePath/langPath на локальные ассеты server/ocr — сеть не нужна */
    const pr=(async()=>{
      const w=await T.createWorker(lang,1,{
        /* полный путь к ядру: в LAN-пакете tesseract.js-core кладётся точечно */
        corePath:path.join(OCR_DIR,'core','tesseract-core-simd-lstm.wasm.js'),
        langPath:path.join(OCR_DIR,'tessdata'),
        gzip:true,logger:()=>{}
      });
      try{w.worker&&w.worker.on&&w.worker.on('error',e=>{log('OCR-воркер: '+String(e&&e.message||e).slice(0,160))})}catch(e){}
      return w;
    })();
    OCR_WORKERS.set(lang,pr);
    pr.catch(()=>OCR_WORKERS.delete(lang));
  }
  return OCR_WORKERS.get(lang);
}
async function ocrRecognize(buf,lang){
  const w=await ocrWorker(lang||'rus');
  const r=await w.recognize(buf);
  return{text:String((r&&r.data&&r.data.text)||'').trim(),conf:Math.round((r&&r.data&&r.data.confidence)||0)};
}
/* ===== 3.35: общая логика импорта табеля/СКУД — для REST и для повтора из журнала ===== */
async function applyTabelRows(m,AU,retryOf){
  const st=canonDecode(CANON);
  if(!st)return{code:409,json:{err:'на сервере нет канона — сначала полная публикация'},status:'error',detail:'нет канона',counters:{}};
  const y=+(m.y||0),mo=+(m.m||0);
  if(!y||!mo||mo<1||mo>12||!Array.isArray(m.rows)||!m.rows.length)
    return{code:400,json:{err:'ожидается {y,m,layer?,map?,rows:[{eid|tab|name,d,code,layer?}]}'},status:'error',detail:'неверный формат запроса',counters:{}};
  const byTab={},byName={};
  (st.employees||[]).forEach(e=>{if(e.tab!=null&&e.tab!=='')byTab[String(e.tab)]=e.id;byName[String(e.name||'').trim().toLowerCase()]=e.id});
  const defLayer=m.layer==='fact'?'fact':'plan';
  /* 3.35: map='1c' — входящие коды Т-13 конвертируются в локальные коды причин */
  const use1c=!!(m.map&&(m.map===true||m.map===1||['1c','true','1'].includes(String(m.map).toLowerCase())));
  const fwd=use1c?eff1cMap(st):null;
  const codeWarn={};
  const ops=[];let unknown=0,mapped=0;
  for(const r of m.rows){
    const eid=r.eid||(r.tab!=null&&byTab[String(r.tab)])||byName[String(r.name||'').trim().toLowerCase()];
    const d=+r.d;
    if(!eid||!d||d<1||d>31){unknown++;continue}
    let code=(r.code==null||r.code==='')?'':String(r.code).slice(0,12);
    if(fwd&&code){const up=code.toUpperCase();
      if(fwd[up]){code=fwd[up];mapped++}
      else codeWarn[code]=(codeWarn[code]||0)+1}
    ops.push({k:r.layer==='fact'||r.layer==='plan'?r.layer:defLayer,y,m:mo,eid,d,code});
  }
  const warnings=Object.keys(codeWarn).map(c=>({code:c,count:codeWarn[c],why:'код не найден в справочнике сопоставления Т-13'}));
  const mk2=y+'-'+String(mo).padStart(2,'0');
  if(!ops.length){
    xjAdd('tabel-post','in','error','импорт «1С»: нет ни одной распознанной строки',{rows:(m.rows||[]).length,unknown,warnings:warnings.length},m,AU.login,retryOf?{retryOf}:null);
    return{code:400,json:{err:'нет ни одной распознанной строки (неизвестные табельный/ФИО)',unknown,warnings},status:'error',detail:'нет распознанных строк',counters:{rows:(m.rows||[]).length,unknown}};
  }
  const r=await doOps(AU,'tabel-'+now().toString(36),ops);
  if(r.kind==='err'){
    xjAdd('tabel-post','in','error',(retryOf?'повтор #'+retryOf+': ':'')+String(r.reason||r.text||'операции отклонены').slice(0,280),
      {rows:ops.length,applied:0,unknown,mapped,warnings:warnings.length,period:mk2},m,AU.login,retryOf?{retryOf}:null);
    return{code:409,json:r,status:'error',detail:String(r.reason||r.text||'').slice(0,280),counters:{rows:ops.length,applied:0,unknown}};
  }
  MET.tabel++;
  const status=warnings.length||unknown?'warn':'ok';
  xjAdd('tabel-post','in',status,
    (retryOf?'повтор #'+retryOf+': ':'')+'обмен «1С» импорт: '+ops.length+' строк ('+(r.applied||0)+' применено), период '+mk2+(use1c?', map=1c — сконвертировано кодов: '+mapped:''),
    {rows:ops.length,applied:r.applied||0,unknown,mapped,warnings:warnings.length,period:mk2},m,AU.login,retryOf?{retryOf}:{period:mk2});
  await audit('xchg-tabel','обмен «1С»: '+ops.length+' строк ('+(r.applied||0)+' применено), период '+mk2,{login:AU.login});
  return{code:200,json:{ok:1,counter:r.counter,applied:r.applied||0,unknown,warnings,map:use1c?'1c':null},status,
    detail:'импорт '+ops.length+' строк',counters:{rows:ops.length,applied:r.applied||0,unknown}};
}
async function applySkudRows(m,AU,retryOf){
  const st=canonDecode(CANON);
  if(!st)return{code:409,json:{err:'на сервере нет канона — сначала полная публикация'},status:'error',detail:'нет канона',counters:{}};
  if(!Array.isArray(m.rows)||!m.rows.length)
    return{code:400,json:{err:'ожидается {rows:[{eid|tab|name,ts}],code?,minEvents?,minHours?}'},status:'error',detail:'неверный формат запроса',counters:{}};
  const minEv=Math.max(1,+(m.minEvents||2)),minH=Math.max(0,+(m.minHours==null?4:m.minHours));
  const code=String(m.code||'Я').slice(0,12);
  const byTab={},byName={};
  (st.employees||[]).forEach(e=>{if(e.tab!=null&&e.tab!=='')byTab[String(e.tab)]=e.id;byName[String(e.name||'').trim().toLowerCase()]=e.id});
  const byDay={};let unknown=0;
  for(const r of m.rows){
    const eid=r.eid||(r.tab!=null&&byTab[String(r.tab)])||byName[String(r.name||'').trim().toLowerCase()];
    if(!eid){unknown++;continue}
    const t=typeof r.ts==='number'?r.ts:Date.parse(String(r.ts).replace(' ','T'));
    if(!isFinite(t)){unknown++;continue}
    const dt=new Date(t);
    const key=eid+'|'+dt.getFullYear()+'|'+(dt.getMonth()+1)+'|'+dt.getDate();
    (byDay[key]=byDay[key]||[]).push(t);
  }
  const ops=[];let skipped=0;
  for(const key in byDay){
    const ts=byDay[key].sort((a,b)=>a-b);
    const spanH=(ts[ts.length-1]-ts[0])/3600000;
    if(ts.length<minEv||spanH<minH){skipped++;continue}
    const[eid,y,mo,d]=key.split('|');
    ops.push({k:'fact',y:+y,m:+mo,eid,d:+d,code});
  }
  if(!ops.length){
    xjAdd('skud-post','in','warn',(retryOf?'повтор #'+retryOf+': ':'')+'СКУД: '+m.rows.length+' событий — ни одного дня не набрано (порог '+minEv+' события / '+minH+' ч)',
      {events:m.rows.length,days:0,skipped,unknown},m,AU.login,retryOf?{retryOf}:null);
    return{code:200,json:{ok:1,applied:0,days:0,skipped,unknown},status:'warn',detail:'ни одного дня не набрано',counters:{events:m.rows.length,days:0,skipped,unknown}};
  }
  const r=await doOps(AU,'skud-'+now().toString(36),ops);
  if(r.kind==='err'){
    xjAdd('skud-post','in','error',(retryOf?'повтор #'+retryOf+': ':'')+String(r.reason||r.text||'операции отклонены').slice(0,280),
      {events:m.rows.length,days:ops.length,applied:0,skipped,unknown},m,AU.login,retryOf?{retryOf}:null);
    return{code:409,json:r,status:'error',detail:String(r.reason||r.text||'').slice(0,280),counters:{events:m.rows.length,days:ops.length}};
  }
  MET.skud+=ops.length;
  const status=unknown?'warn':'ok';
  xjAdd('skud-post','in',status,(retryOf?'повтор #'+retryOf+': ':'')+'СКУД: '+m.rows.length+' событий → '+ops.length+' дн. факта (код «'+code+'», порог '+minEv+' события / '+minH+' ч)',
    {events:m.rows.length,days:ops.length,applied:r.applied||0,skipped,unknown},m,AU.login,retryOf?{retryOf}:null);
  await audit('xchg-skud','СКУД: '+m.rows.length+' событий → '+ops.length+' дн. факта (код «'+code+'», порог '+minEv+' события / '+minH+' ч)',{login:AU.login});
  return{code:200,json:{ok:1,counter:r.counter,applied:r.applied||0,days:ops.length,skipped,unknown},status,
    detail:'СКУД → '+ops.length+' дн.',counters:{events:m.rows.length,days:ops.length,applied:r.applied||0}};
}
async function xchgRetry(id,AU){
  const it=XCHG.items.find(x=>x.id===id);
  if(!it)return{ok:0,err:'запись журнала не найдена'};
  if(!it.payload)return{ok:0,err:'исходный запрос не сохранён'+(it.payloadTooBig?' (больше '+Math.round(PAY_MAX/1024)+' КБ)':'')+' — повтор невозможен'};
  if(USERS&&!can(AU,'import'))return{ok:0,err:'нужны права импорта (import) — роли admin/hr'};
  if(REPLICA_OF&&!REPLICA_OFF)return{ok:0,err:'узел работает как реплика (только чтение)'};
  let r;
  if(it.kind==='tabel-post')r=await applyTabelRows(it.payload,AU,it.id);
  else if(it.kind==='skud-post')r=await applySkudRows(it.payload,AU,it.id);
  else return{ok:0,err:'повтор операции «'+it.kind+'» не поддерживается (доступно: tabel-post, skud-post)'};
  it.retries=(it.retries||0)+1;it.lastRetryTs=now();persistXchg();
  MET.xchgRetry++;
  await audit('xchg-retry','повтор обмена '+it.kind+' (#'+it.id+') → '+r.status+(r.detail?' — '+r.detail:''),{login:AU.login});
  return{ok:1,source:it.id,kind:it.kind,status:r.status,detail:r.detail||'',counters:r.counters||{},result:r.json};
}

/* ---------- 3.30: REST API /api/v1 (токены те же, что у WS) ---------- */
async function apiHttp(req,res,u,p){
  const sendJ=(code,obj)=>{res.writeHead(code,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(obj))};
  let body='';for await(const c of req)body+=c;
  let m={};try{m=JSON.parse(body||'{}')}catch(e){}
  const tok=String(req.headers.authorization||'').replace(/^Bearer /i,'')||u.searchParams.get('token')||'';
  let su=tokUser(tok);
  /* 3.34: SSO — доверенный заголовок реверс-прокси для REST */
  if(!su&&USERS&&SSO_HEADER&&p!=='/api/v1/login'){
    const hl=String(req.headers[SSO_HEADER]||'');
    if(hl){
      const usr=await ssoUser(hl,SSO_NAME_HEADER?String(req.headers[SSO_NAME_HEADER]||''):'');
      if(usr){su=TOKENS.get(issueToken(usr));await audit('sso-auth','REST-вход через SSO: '+usr.login,{login:usr.login});}
    }
  }
  const AU=USERS?(su||ANON):{login:String(m.by||'api').slice(0,40),role:'admin',emp:null,allow:[],deny:[],modsOff:[]};
  if(USERS&&!su&&p!=='/api/v1/login')return sendJ(401,{err:'требуется аутентификация: POST /api/v1/login {login,pin}'});
  if(p==='/api/v1/login'){
    if(!USERS)return sendJ(400,{err:'аутентификация выключена (нет PT_USERS_FILE): API доступно без токена'});
    const usr=findUser(String(m.login||''));
    const h=String((usr&&usr.pinHash)||'');
    const pinOk=h&&(h===hashPin(String(m.pin||''))||(!h.startsWith('s2$')&&!h.startsWith('fb$')&&h===String(m.pin)));
    if(!usr||usr.blocked||!pinOk){await audit('auth-fail','REST: неверный вход '+String(m.login||'').slice(0,40));return sendJ(401,{err:'Неверная пара логин/PIN'})}
    const tk=issueToken(usr);
    await audit('auth-ok','REST вход: '+usr.login+' ('+(usr.role||'viewer')+')');
    return sendJ(200,{ok:1,token:tk,role:usr.role||'viewer',emp:usr.emp||null});
  }
  if(p==='/api/v1/canon'&&req.method==='GET')
    return sendJ(200,{ok:1,counter:CANON?CANON.counter:0,ts:CANON?CANON.ts:null,by:CANON?CANON.by:null,state:canonDecode(CANON)});
  if(p==='/api/v1/push'&&req.method==='POST'){
    const gz=m.gz||(m.state?gzEnc(m.state):null);   /* 3.30: state кодируется в gz-формат канона */
    const data=gz?null:(m.data||null);
    const r=await doPush(AU,{base:m.base,force:!!m.force,ts:m.ts||now(),by:m.by||AU.login,org:m.org,gz,data});
    if(r.kind==='err')return sendJ(409,r);
    if(r.kind==='conflict')return sendJ(409,{err:'conflict',counter:CANON?CANON.counter:0});
    return sendJ(200,{ok:1,counter:r.counter,quotaLeft:r.quotaLeft});
  }
  if(p==='/api/v1/ops'&&req.method==='POST'){
    const r=await doOps(AU,m.cid||('api'+now().toString(36)),m.ops||[]);
    if(r.kind==='err')return sendJ(409,r);
    return sendJ(200,{ok:1,counter:r.counter,applied:r.applied||0});
  }
  /* 3.34: REST-обмен «1С» — выгрузка табеля (CSV/JSON) и импорт строк */
  if(p==='/api/v1/tabel'&&req.method==='GET'){
    const st=canonDecode(CANON);
    if(!st)return sendJ(409,{err:'на сервере нет канона — сначала полная публикация'});
    const y=+(u.searchParams.get('y')||new Date().getFullYear());
    const mo=+(u.searchParams.get('m')||(new Date().getMonth()+1));
    const dept=u.searchParams.get('dept')||'';
    if(!y||!mo||mo<1||mo>12)return sendJ(400,{err:'неверный период (?y=YYYY&m=MM)'});
    const mk=y+'-'+String(mo).padStart(2,'0');
    const plan=(st.plan||{})[mk]||{},fact=(st.fact||{})[mk]||{};
    const days=new Date(y,mo,0).getDate();
    const emps=(st.employees||[]).filter(e=>!dept||e.deptId===dept);
    const rows=[];
    for(const e of emps)for(let d=1;d<=days;d++){
      const pc=(plan[e.id]||{})[d]||'',fc=(fact[e.id]||{})[d]||'';
      if(!pc&&!fc)continue;
      rows.push({tab:String(e.tab||''),eid:e.id,name:e.name,dept:e.deptId||'',
        date:mk+'-'+String(d).padStart(2,'0'),dow:new Date(y,mo-1,d).getDay(),plan:pc,fact:fc});
    }
    /* 3.35: map=1c — локальные коды конвертируются в коды Т-13 по справочнику сопоставления */
    const use1c=(u.searchParams.get('map')||'').toLowerCase()==='1c';
    let warnings=[],mapped=0;
    if(use1c){
      const rev=rev1cMap(eff1cMap(st));const miss={};
      for(const rw of rows){
        for(const lay of['plan','fact']){const c=rw[lay];if(!c)continue;
          if(rev[c]){rw[lay]=rev[c];mapped++}else miss[c]=(miss[c]||0)+1}
      }
      warnings=Object.keys(miss).map(c=>({code:c,count:miss[c],why:'локальный код не сопоставлен с кодом Т-13'}));
    }
    MET.tabel++;
    xjAdd('tabel-get','out',warnings.length?'warn':'ok',
      'обмен «1С» выгрузка: '+rows.length+' строк, период '+mk+(dept?', подразделение '+dept:'')+(use1c?', map=1c — сконвертировано кодов: '+mapped:''),
      {rows:rows.length,period:mk,mapped,warnings:warnings.length},null,AU.login,{period:mk});
    if((u.searchParams.get('fmt')||'json')==='csv'){
      const csv=['Табельный;ФИО;Дата;ДеньНед;План;Факт',
        ...rows.map(r=>[r.tab,r.name,r.date,r.dow,r.plan,r.fact].map(x=>'"'+String(x).replace(/"/g,'""')+'"').join(';'))].join('\r\n');
      res.writeHead(200,{'Content-Type':'text/csv; charset=utf-8','Cache-Control':'no-store',
        'Content-Disposition':'attachment; filename="tabel-'+mk+'.csv"'});
      return res.end('\ufeff'+csv);
    }
    return sendJ(200,{ok:1,y,m:mo,dept:dept||null,count:rows.length,hoursDay:(st.settings||{}).hoursDay||8,map:use1c?'1c':null,warnings,rows});
  }
  if(p==='/api/v1/tabel'&&req.method==='POST'){
    /* 3.35: логика вынесена в applyTabelRows — общая для REST-вызова и повтора из журнала обмена */
    const r=await applyTabelRows(m,AU);
    return sendJ(r.code,r.json);
  }
  /* 3.34: СКУД — события прохода → день факта (по порогу событий и длительности) */
  /* 3.34: СКУД — события прохода → день факта (по порогу событий и длительности); 3.35: журнал обмена + ретрай */
  if(p==='/api/v1/skud'&&req.method==='POST'){
    const r=await applySkudRows(m,AU);
    return sendJ(r.code,r.json);
  }
  if(p==='/api/v1/ocr'&&req.method==='POST'){   /* 3.31: серверный OCR — разгрузка браузера */
    const b64=String(m.image||'');
    if(!b64)return sendJ(400,{err:'нет изображения (base64 в поле image)'});
    const lang=String(m.lang||'rus').slice(0,12);
    try{
      const t0=now();
      const r=await ocrRecognize(Buffer.from(b64,'base64'),lang);
      const ms=now()-t0;
      xjAdd('ocr-post','in',r.conf>=40?'ok':'warn','серверный OCR ('+lang+'): достоверность '+r.conf+'%, распознано символов: '+r.text.length,{conf:r.conf,ms,chars:r.text.length},null,AU.login);
      await audit('ocr','серверное распознавание '+lang+': достоверность '+r.conf+'%',{login:AU.login});
      return sendJ(200,{ok:1,text:r.text,conf:r.conf,ms,engine:'server'});
    }catch(e){
      xjAdd('ocr-post','in','error','серверный OCR: '+String(e&&e.message||e).slice(0,160),{},null,AU.login);
      return sendJ(500,{err:String(e&&e.message||e).slice(0,200)});
    }
  }
  if(p==='/api/v1/sigs'&&req.method==='GET')return sendJ(200,{ok:1,sigs:SIGS.sigs});
  if(p==='/api/v1/signal'&&req.method==='POST'){
    if(USERS&&!can(AU,'admin'))return sendJ(403,{err:'нужны права администратора'});
    const sig={sid:'sig'+now().toString(36)+Math.random().toString(36).slice(2,6),ts:now(),
      sev:m.sev==='crit'?'crit':'warn',text:String(m.text||'').slice(0,300),by:AU.login||'api'};
    SIGS.sigs.unshift(sig);if(SIGS.sigs.length>600)SIGS.sigs.length=600;
    await persistSigs();broadcast({type:'signal',...sig});
    await audit('signal',sig.sev+': '+sig.text,{by:AU.login,sid:sig.sid});
    return sendJ(200,{ok:1,sig});
  }
  if(p==='/api/v1/users'&&USERS){
    if(!can(AU,'admin'))return sendJ(403,{err:'нужны права администратора'});
    if(req.method==='GET')return sendJ(200,{ok:1,users:USERS.map(x=>({...x,pinHash:'***'}))});
    if(req.method==='POST'){const adm=await adminApi({action:'userSave',user:m.user||{}},AU);return sendJ(adm.ok?200:400,adm)}
  }
  /* ===== 3.35: коннектор «1С» — справочник сопоставления кодов Т-13 ↔ причины ===== */
  if(p==='/api/v1/xchg/map'&&req.method==='GET'){
    const st=canonDecode(CANON);
    if(!st)return sendJ(409,{err:'на сервере нет канона — сначала полная публикация'});
    const auto=buildAutoMap(st),eff=eff1cMap(st);
    return sendJ(200,{ok:1,codes:T13_CODES,auto:auto.map,missingAuto:auto.missing,
      items:XMAP.items,ts:XMAP.ts||null,by:XMAP.by||'',effective:eff,
      unmapped:T13_CODES.filter(t=>!eff[t]),overridden:XMAP.items.length});
  }
  if(p==='/api/v1/xchg/map'&&(req.method==='PUT'||req.method==='POST')){
    const st=canonDecode(CANON);
    if(!st)return sendJ(409,{err:'на сервере нет канона — сначала полная публикация'});
    if(USERS&&!can(AU,'staff')&&!can(AU,'admin'))return sendJ(403,{err:'нужны права ведения справочников (staff) или администратора'});
    if(!Array.isArray(m.items))return sendJ(400,{err:'ожидается {items:[{t13,local,note?}]} (local="" — снять сопоставление)'});
    if(m.items.length>200)return sendJ(400,{err:'слишком много строк сопоставления (максимум 200)'});
    const codes={};(st.reasons||[]).forEach(r=>codes[String(r.code||'').toUpperCase()]=1);
    const errors=[],warnings=[],seen={},items=[];
    m.items.forEach(it=>{
      const t13=String(it.t13||'').trim().toUpperCase().slice(0,4);
      const local=String(it.local==null?'':it.local).trim().slice(0,12);
      const note=String(it.note||'').slice(0,120);
      if(!t13){errors.push({row:items.length,err:'пустой код Т-13'});return}
      if(seen[t13]){errors.push({t13,err:'код Т-13 «'+t13+'» встречается дважды'});return}
      seen[t13]=1;
      if(local&&!codes[local.toUpperCase()]){errors.push({t13,local,err:'локальный код «'+local+'» отсутствует в справочнике причин канона'});return}
      if(!T13_CODES.includes(t13))warnings.push({t13,why:'нестандартный код Т-13 (вне списка унифицированной формы)'});
      items.push({t13,local:local?local.toUpperCase():'',note});
    });
    const locCount={};items.forEach(x=>{if(x.local)locCount[x.local]=(locCount[x.local]||0)+1});
    Object.keys(locCount).forEach(l=>{if(locCount[l]>1)warnings.push({local:l,why:'несколько кодов Т-13 сопоставлены с одним локальным кодом «'+l+'» — обратная выгрузка неоднозначна'})});
    if(errors.length){
      xjAdd('map-put','in','error','сопоставление Т-13 отклонено: ошибок валидации '+errors.length,{items:m.items.length,errors:errors.length,warnings:warnings.length},{items:m.items},AU.login);
      return sendJ(400,{ok:0,errors,warnings});
    }
    XMAP={items,ts:now(),by:AU.login||'api'};
    await persistXmap();
    const eff=eff1cMap(st),unmapped=T13_CODES.filter(t=>!eff[t]);
    unmapped.forEach(t=>warnings.push({t13:t,why:'код Т-13 не сопоставлен (авто-правило не сработало, переопределения нет)'}));
    xjAdd('map-put','in',warnings.length?'warn':'ok','справочник сопоставления Т-13 сохранён: '+items.length+' строк'+(unmapped.length?', без сопоставления: '+unmapped.join(','):''),
      {items:items.length,warnings:warnings.length,unmapped:unmapped.length},{items},AU.login);
    await audit('xchg-map','справочник «1С»: сохранено '+items.length+' сопоставлений кодов Т-13'+(warnings.length?', предупреждений '+warnings.length:''),{login:AU.login});
    return sendJ(200,{ok:1,saved:items.length,ts:XMAP.ts,by:XMAP.by,warnings,unmapped,effective:eff});
  }
  /* ===== 3.35: веб-панель обмена — журнал выгрузок/импортов и повтор операций ===== */
  if(p==='/api/v1/xchg/log'&&req.method==='GET'){
    const r=xjList(u.searchParams.get('limit'),u.searchParams.get('kind')||'',u.searchParams.get('status')||'');
    return sendJ(200,{ok:1,total:r.total,items:r.items,max:XCHG_MAX});
  }
  if(p==='/api/v1/xchg/retry'&&req.method==='POST'){
    const id=String(m.id||'').slice(0,40);
    if(!id)return sendJ(400,{err:'ожидается {id} — идентификатор записи журнала обмена'});
    const r=await xchgRetry(id,AU);
    if(!r.ok)return sendJ(400,r);
    return sendJ(200,r);
  }
  /* ===== 3.49: серверный контур бригад ротаций ===== */
  if(p==='/api/v1/brigades'&&req.method==='GET'){
    return sendJ(200,{ok:1,items:BRIG.items,ts:BRIG.ts||0,by:BRIG.by||'',total:BRIG.items.length});
  }
  if(p==='/api/v1/brigades'&&(req.method==='PUT'||req.method==='POST')){
    if(USERS&&!can(AU,'staff')&&!can(AU,'admin')&&!can(AU,'brig'))return sendJ(403,{err:'нужны права brig, staff или администратора'});
    if(brigQuotaLeft(AU.role||'anon')===0){
      await audit('brig-quota','превышена часовая квота PUT бригад для роли '+(AU.role||'anon'),{login:AU.login});
      return sendJ(429,{err:'часовая квота PUT бригад исчерпана',retryAfterMin:60-new Date().getMinutes()});
    }
    if(!Array.isArray(m.items))return sendJ(400,{err:'ожидается {items:[{id,name,patId,anchor,offset,members,ts?}]}'});
    if(m.items.length>200)return sendJ(400,{err:'слишком много бригад (максимум 200)'});
    const errors=[];const byId={};BRIG.items.forEach(it=>byId[it.id]=it);
    let touched=0;
    m.items.forEach(it=>{
      const id=String(it.id||'').slice(0,40);
      if(!id){errors.push({err:'пустой id бригады'});return}
      const rec={id,
        name:String(it.name||'').slice(0,80)||('бригада '+id),
        patId:String(it.patId||'').slice(0,40),
        anchor:String(it.anchor||'').slice(0,10),
        offset:Math.max(0,Math.min(60,Math.round(+it.offset||0))),
        members:Array.isArray(it.members)?it.members.slice(0,200).map(x=>String(x).slice(0,40)):[],
        ts:+it.ts||now()};
      const ex=byId[id];
      if(ex&&(ex.ts||0)>rec.ts)return;   /* last-write-wins по ts */
      byId[id]=rec;touched++;
    });
    if(errors.length)return sendJ(400,{ok:0,errors});
    brigQuotaUse(AU.role||'anon');
    BRIG={items:Object.values(byId),ts:now(),by:AU.login||'api'};
    await persistBrig();
    broadcast({type:'brigades',ts:BRIG.ts,by:BRIG.by,total:BRIG.items.length});
    await audit('brigades','справочник бригад: сохранено/обновлено '+touched+' из '+BRIG.items.length,{login:AU.login});
    return sendJ(200,{ok:1,saved:touched,total:BRIG.items.length,ts:BRIG.ts,by:BRIG.by,quotaLeft:brigQuotaLeft(AU.role||'anon')===Infinity?null:brigQuotaLeft(AU.role||'anon')});
  }
  /* ===== 3.53: лимиты ФОТ по подразделениям и месяцам ===== */
  if(p==='/api/v1/budgets'&&req.method==='GET'){
    return sendJ(200,{ok:1,items:BUDG.items,ts:BUDG.ts||0,by:BUDG.by||'',total:Object.keys(BUDG.items).length});
  }
  if(p==='/api/v1/budgets'&&(req.method==='PUT'||req.method==='POST')){
    if(USERS&&!can(AU,'staff')&&!can(AU,'admin')&&!can(AU,'budget'))return sendJ(403,{err:'нужны права staff, admin или budget'});
    if(!m.items||typeof m.items!=='object'||Array.isArray(m.items))return sendJ(400,{err:'ожидается {items:{"YYYY-MM":{deptId:лимит|null}}}'});
    const mks=Object.keys(m.items);
    if(mks.length>240)return sendJ(400,{err:'слишком много месяцев (максимум 240)'});
    const errors=[];let touched=0;
    mks.forEach(mk=>{
      if(!/^\d{4}-\d{2}$/.test(mk)||+mk.slice(5,7)<1||+mk.slice(5,7)>12){errors.push({mk,err:'формат месяца YYYY-MM (01–12)'});return}
      const lim=m.items[mk];
      if(!lim||typeof lim!=='object'||Array.isArray(lim)){errors.push({mk,err:'ожидается объект лимитов по подразделениям'});return}
      const deps=Object.keys(lim);
      if(deps.length>100){errors.push({mk,err:'слишком много подразделений (максимум 100)'});return}
      const rec={limits:{},ts:+lim.ts||now(),by:AU.login||'api'};
      deps.forEach(did=>{
        if(did==='ts'||did==='by')return;
        const v=lim[did];
        if(v!==null&&(typeof v!=='number'||!isFinite(v)||v<0)){errors.push({mk,dept:did,err:'лимит — число ≥ 0 или null'});return}
        rec.limits[String(did).slice(0,40)]=v;
      });
      const ex=BUDG.items[mk];
      if(ex&&(ex.ts||0)>rec.ts)return;   /* last-write-wins по ts месяца */
      BUDG.items[mk]=rec;touched++;
    });
    if(errors.length)return sendJ(400,{ok:0,errors});
    BUDG.ts=now();BUDG.by=AU.login||'api';
    await persistBudg();
    broadcast({type:'budgets',ts:BUDG.ts,by:BUDG.by,total:Object.keys(BUDG.items).length});
    await audit('budgets','лимита ФОТ: месяцев обновлено '+touched+' из '+Object.keys(BUDG.items).length,{login:AU.login});
    return sendJ(200,{ok:1,saved:touched,total:Object.keys(BUDG.items).length,ts:BUDG.ts,by:BUDG.by});
  }
  return sendJ(404,{err:'неизвестный метод API; см. README: /api/v1 login|canon|push|ops|sigs|signal|users|tabel|skud|ocr|xchg/map|xchg/log|xchg/retry|brigades'});
}

/* ---------- /admin ---------- */
const ADMIN_SESSIONS=new Map();   /* cookie -> login */
async function adminHttp(req,res,u){
  const send=(code,body,type='application/json')=>{res.writeHead(code,{'Content-Type':type});res.end(body)};
  const cookie=(req.headers.cookie||'').split(';').map(s=>s.trim()).find(s=>s.startsWith('ptadm='));
  const sess=cookie?ADMIN_SESSIONS.get(cookie.slice(6)):null;
  const usr=sess?findUser(sess):null;
  const adminUser=usr?{login:usr.login,role:usr.role||'viewer',allow:usr.allow||[],deny:usr.deny||[]}:null;
  if(USERS&&u.pathname!=='/admin/login'){
    if(!sess||!usr){
      /* нет сессии — показываем форму входа (не 403, иначе некуда вводить PIN) */
      if(u.pathname==='/admin/api')return send(401,JSON.stringify({err:'требуется вход'}));
      return send(200,adminLoginPage(''),'text/html; charset=utf-8');
    }
    if(usr.blocked||!can(adminUser,'admin')){
      await audit('admin-deny','отказ доступа в /admin',{login:sess||'?',ip:req.socket.remoteAddress});
      if(u.pathname==='/admin/api')return send(403,JSON.stringify({err:'нет прав администратора'}));
      return send(403,adminLoginPage('Доступ запрещён: нужны права администратора.'),'text/html; charset=utf-8');
    }
  }
  if(req.method==='POST'&&u.pathname==='/admin/login'){
    let b='';for await(const c of req)b+=c;
    let login='',pin='';
    if(b.startsWith('{')){const o=JSON.parse(b||'{}');login=o.login;pin=o.pin}
    else{const q=new URLSearchParams(b);login=q.get('login');pin=q.get('pin')}
    const usr=findUser(login||'');
    const h=String((usr&&usr.pinHash)||'');
    const pinOk=h&&(h===hashPin(pin||'')||(!h.startsWith('s2$')&&!h.startsWith('fb$')&&h===String(pin)));
    if(usr&&!usr.blocked&&pinOk){
      if(!can(usr,'admin')){
        await audit('admin-deny','отказ входа в /admin: нет прав admin',{login:usr.login,ip:req.socket.remoteAddress});
        return send(403,adminLoginPage('Учётка не имеет прав администратора.'),'text/html; charset=utf-8');
      }
      const c2=randomBytes(18).toString('base64url');
      ADMIN_SESSIONS.set(c2,login);
      res.writeHead(302,{'Set-Cookie':`ptadm=${c2}; Path=/; HttpOnly; SameSite=Strict`,'Location':'/admin'});
      return res.end();
    }
    return send(401,adminLoginPage('Неверная пара логин/PIN.'),'text/html; charset=utf-8');
  }
  if(u.pathname==='/admin'&&!USERS||u.pathname==='/admin'&&USERS&&adminUser){
    res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});
    return res.end(adminPage());
  }
  if(u.pathname==='/admin/api'){
    let b='';for await(const c of req)b+=c;
    let m={};try{m=JSON.parse(b||'{}')}catch(e){}
    return send(200,JSON.stringify(await adminApi(m,adminUser||{login:'local',role:'admin'})));
  }
  return send(404,'not found','text/plain');
}
function adminLoginPage(err){
  return`<!doctype html><meta charset=utf-8><title>WFM · вход в /admin</title>
  <body style="font:14px system-ui;display:grid;place-items:center;min-height:90vh;background:#0c1220;color:#e6ecf7">
  <form method=post action=/admin/login style="background:#141c2e;padding:24px;border-radius:12px;display:grid;gap:10px;min-width:300px">
    <b>🛡 Вход в панель администратора</b><div style="color:#ef6a60;min-height:18px">${err||''}</div>
    <input name=login placeholder=логин style="padding:8px;border-radius:8px;border:1px solid #26324a;background:#0c1220;color:#e6ecf7">
    <input name=pin type=password placeholder=PIN style="padding:8px;border-radius:8px;border:1px solid #26324a;background:#0c1220;color:#e6ecf7">
    <button style="padding:8px;border-radius:8px;border:0;background:#e79814;font-weight:700">Войти</button>
  </form></body>`;
}
async function adminApi(m,au){
  const act=m.action;
  if(act==='state')return{ok:1,ver:VER,replica:!!(REPLICA_OF&&!REPLICA_OFF),
    clients:WSS?WSS.clients.size:0,canon:CANON?{counter:CANON.counter,ts:CANON.ts,by:CANON.by}:null,
    quotas:QUOTAS,quotaUsed:QUOTA_USED,
    clientsList:[...CLIENTS].map(c=>({login:c.login||c.by||'(без имени)',rtt:c.rtt,since:c.since,replica:!!c.isReplica})),   /* 3.21 */
    db:DB?'sqlite':'json',encrypted:!!CANON_KEY,api:'/api/v1 (login, canon, push, ops, sigs, signal, users)'};
  if(act==='auditCsv'){   /* 3.21: выгрузка журнала сервера в CSV */
    let lines=[];
    try{lines=(await readFile(AUDIT_FILE,'utf8')).trim().split('\n')}catch(e){}
    const esc=v=>{v=String(v==null?'':v);return /[";\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v};
    const csv='ts;iso;ev;detail;login\n'+lines.map(l=>{try{const o=JSON.parse(l);
      return [o.ts,new Date(o.ts||0).toISOString(),o.ev,o.detail,o.login||''].map(esc).join(';')}catch(e){return ''}}).filter(Boolean).join('\n');
    return{ok:1,csv};
  }
  if(act==='users')return{ok:1,users:(USERS||[]).map(u=>({...u,pinHash:u.pinHash?'***':''}))};
  if(act==='userSave'){
    if(!USERS)return{ok:0,err:'аутентификация выключена (нет PT_USERS_FILE)'};
    const u=m.user||{};if(!u.login)return{ok:0,err:'нет логина'};
    const ex=findUser(u.login);
    if(ex)Object.assign(ex,{role:u.role||ex.role,emp:u.emp!==undefined?u.emp:ex.emp,
      allow:u.allow||ex.allow,deny:u.deny||ex.deny,modsOff:u.modsOff||ex.modsOff,blocked:!!u.blocked});
    else USERS.push({login:u.login,pinHash:u.pin?hashPin(u.pin):hashPin('0000'),role:u.role||'viewer',
      emp:u.emp||null,allow:u.allow||[],deny:u.deny||[],modsOff:u.modsOff||[],blocked:false});
    await saveUsers();broadcastPerms(findUser(u.login));
    await audit('user-save','пользователь сохранён: '+u.login,{by:au.login});
    return{ok:1};
  }
  if(act==='userDel'){
    if(!USERS)return{ok:0};
    USERS=USERS.filter(x=>x.login!==m.login);await saveUsers();
    await audit('user-del','удалён пользователь '+m.login,{by:au.login});return{ok:1};
  }
  if(act==='resetPin'){
    const usr=findUser(m.login);if(!usr)return{ok:0,err:'нет пользователя'};
    usr.pinHash=hashPin(String(m.pin||'0000'));await saveUsers();
    await audit('pin-reset','сброшен PIN '+m.login,{by:au.login});return{ok:1};
  }
  if(act==='sigs')return{ok:1,sigs:SIGS.sigs.slice(0,600)};
  if(act==='signal'){
    const sig={sid:'sig'+now().toString(36)+Math.random().toString(36).slice(2,6),
      ts:now(),sev:m.sev==='crit'?'crit':'warn',text:String(m.text||'').slice(0,300),by:au.login||'admin'};
    SIGS.sigs.unshift(sig);if(SIGS.sigs.length>600)SIGS.sigs.length=600;
    await persistSigs();broadcast({type:'signal',...sig});
    await audit('signal',sig.sev+': '+sig.text,{by:au.login,sid:sig.sid});
    return{ok:1,sig};
  }
  if(act==='audit'){
    let lines=[];
    try{lines=(await readFile(AUDIT_FILE,'utf8')).trim().split('\n').slice(-(+m.limit||200))}catch(e){}
    return{ok:1,lines:lines.map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean).reverse()};
  }
  if(act==='hist'){
    try{
      const files=(await readdir(HIST_DIR)).sort().reverse().slice(0,50);
      return{ok:1,items:files.map(f=>{const[ctr,ts]=f.replace('.json','').split('-');
        return{file:f,counter:+ctr,ts:+ts}})};
    }catch(e){return{ok:1,items:[]}}
  }
  if(act==='rollback'){
    const f=path.join(HIST_DIR,path.basename(String(m.file||'')));
    if(!existsSync(f))return{ok:0,err:'нет файла истории'};
    const old=decWrap(await readFile(f,'utf8').catch(()=>null));if(!old)return{ok:0,err:'повреждённая запись истории'};
    CANON={...old,counter:(CANON?CANON.counter:0)+1,ts:now(),by:'rollback:'+(au.login||'admin')};
    await persistCanon();broadcast({type:'update',canon:CANON});
    await audit('rollback','канон откачен к counter='+old.counter,{by:au.login});
    return{ok:1,counter:CANON.counter};
  }
  if(act==='backups'){   /* 3.23 */
    try{
      const files=(await readdir(BACKUP_DIR)).filter(f=>f.startsWith('backup-')).sort().reverse();
      return{ok:1,items:files.map(f=>{const mm=f.match(/c(\d+)\.json$/);const ts=f.split('-')[1];
        return{file:f,counter:mm?+mm[1]:0,stamp:ts}})};
    }catch(e){return{ok:1,items:[]}}
  }
  if(act==='backupNow'){const n=await makeBackup(au.login||'admin');return n?{ok:1,file:n}:{ok:0,err:'нет канона'}}
  if(act==='backupRestore'){   /* 3.23 */
    const f=path.join(BACKUP_DIR,path.basename(String(m.file||'')));
    if(!existsSync(f))return{ok:0,err:'нет файла копии'};
    const b=decWrap(await readFile(f,'utf8').catch(()=>null));if(!b||!b.canon)return{ok:0,err:'повреждённая копия'};
    CANON={...b.canon,counter:(CANON?CANON.counter:0)+1,ts:now(),by:'restore:'+(au.login||'admin')};
    await persistCanon();broadcast({type:'update',canon:CANON});
    await audit('restore','канон восстановлен из копии '+path.basename(f)+' (был №'+b.counter+')',{by:au.login});
    return{ok:1,counter:CANON.counter};
  }
  if(act==='promote'){
    if(!REPLICA_OF)return{ok:0,err:'узел не реплика'};
    REPLICA_OFF=true;if(REPLICA_WS){try{REPLICA_WS.close()}catch(e){}REPLICA_WS=null}
    await audit('promote','реплика повышена до primary',{by:au.login});
    return{ok:1};
  }
  if(act==='xchgLog'){   /* 3.35: журнал обмена для панели /admin */
    const r=xjList(m.limit||60,m.kind||'',m.status||'');
    return{ok:1,total:r.total,items:r.items,max:XCHG_MAX,map:{items:XMAP.items,ts:XMAP.ts||null,by:XMAP.by||''}};
  }
  if(act==='xchgRetry'){   /* 3.35: повтор операции обмена */
    return await xchgRetry(String(m.id||''),au||{login:'local',role:'admin'});
  }
  return{ok:0,err:'неизвестное действие'};
}
function adminPage(){
  return`<!doctype html><meta charset=utf-8><title>WFM · администрирование</title>
<body style="font:13.5px/1.55 system-ui;margin:0;background:#0c1220;color:#e6ecf7">
<div style="padding:16px 22px;background:#141c2e;border-bottom:2px solid #e79814;display:flex;gap:12px;align-items:center">
  <b style="font-size:16px">🛡 Панель администратора сети · WFM ${VER}</b>
  <span id=st style="margin-left:auto;color:#8fa0bd"></span>
  <a href="/" style="color:#7fb0ff">→ приложение</a>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:16px 22px;max-width:1500px;margin:0 auto">
  <section style="background:#141c2e;border:1px solid #26324a;border-radius:12px;padding:14px">
    <h3 style="margin:0 0 8px">Пользователи и права</h3><div id=users></div>
    <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">
      <input id=nLogin placeholder=логин style="width:110px"><input id=nPin placeholder=PIN type=password style="width:80px">
      <select id=nRole>${['admin','hr','editor','tab','viewer'].map(r=>`<option>${r}</option>`).join('')}</select>
      <input id=nEmp placeholder="emp (id сотрудника)" style="width:150px">
      <button onclick=addUser()>Добавить</button></div>
    <div class=hint style="color:#8fa0bd;margin-top:6px">Права: allow/deny через запятую (edit, chat, sign, admin, staff, import, planOnly). deny применяется сервером.</div>
  </section>
  <section style="background:#141c2e;border:1px solid #26324a;border-radius:12px;padding:14px">
    <h3 style="margin:0 0 8px">Сигналы оповещения</h3>
    <div style="display:flex;gap:6px;margin-bottom:8px"><input id=sigText placeholder="текст сигнала" style="flex:1">
      <select id=sigSev><option value=warn>warn</option><option value=crit>crit</option></select>
      <button onclick=sendSig()>🚨 Послать</button></div>
    <div id=sigs style="max-height:280px;overflow:auto"></div>
  </section>
  <section style="background:#141c2e;border:1px solid #26324a;border-radius:12px;padding:14px">
    <h3 style="margin:0 0 8px">История канона и откат</h3><div id=hist style="max-height:260px;overflow:auto"></div>
  </section>
  <section style="background:#141c2e;border:1px solid #26324a;border-radius:12px;padding:14px">
    <h3 style="margin:0 0 8px">Журнал сервера <button onclick=dlCsv() style="margin-left:8px">⇩ CSV</button></h3>
    <div id=aud style="max-height:240px;overflow:auto;font-family:monospace;font-size:11.5px"></div>
    <h3 style="margin:12px 0 8px">Узел и клиенты</h3><div id=node></div><div id=clients style="margin-top:6px"></div>
    <h3 style="margin:12px 0 8px">Резервные копии канона <button onclick="api('backupNow').then(refresh)" style="margin-left:8px">Создать сейчас</button></h3>
    <div id=backs style="max-height:200px;overflow:auto"></div>
  </section>
  <section style="background:#141c2e;border:1px solid #26324a;border-radius:12px;padding:14px;grid-column:1/-1">
    <h3 style="margin:0 0 8px">Обмен «1С» / СКУД — журнал выгрузок и импортов (3.35)
      <select id=xKind style="margin-left:10px"><option value="">все операции</option><option value="tabel-get">tabel-get · выгрузка</option><option value="tabel-post">tabel-post · импорт</option><option value="skud-post">skud-post · СКУД</option><option value="ocr-post">ocr-post · распознавание</option><option value="map-put">map-put · справочник Т-13</option></select>
      <select id=xStatus><option value="">все статусы</option><option value="ok">ok</option><option value="warn">warn</option><option value="error">error</option></select>
      <button onclick=loadXchg() style="margin-left:6px">↻ Обновить</button>
      <span id=xMap style="margin-left:10px;color:#8fa0bd"></span></h3>
    <div id=xchg style="max-height:340px;overflow:auto"></div>
    <div style="color:#8fa0bd;margin-top:6px;font-size:12px">Журнал ведётся сервером (до 300 записей, PT_XCHG_FILE): выгрузки табеля «1С», импорты табеля и событий СКУД, распознавание, сохранение справочника сопоставления кодов Т-13. Для неудачных импортов сохраняется исходный запрос — кнопка «↻ повтор» применяет его заново с учётом прав и комплаенса закрытых периодов. REST: <code>GET /api/v1/xchg/log</code>, <code>POST /api/v1/xchg/retry</code>.</div>
  </section>
</div>
<style>input,select,button{padding:5px 8px;border-radius:7px;border:1px solid #26324a;background:#0c1220;color:#e6ecf7}
button{cursor:pointer;background:#e79814;color:#12213a;border:0;font-weight:700}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #1d2740;padding:3px 6px;text-align:left;font-size:12px}
.row{display:flex;gap:6px;align-items:center;padding:4px 0;border-bottom:1px dashed #1d2740;flex-wrap:wrap}</style>
<script>
const api=(action,body)=>fetch('/admin/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...body})}).then(r=>r.json());
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function refresh(){
  const st=await api('state');
  document.getElementById('st').textContent='клиентов: '+st.clients+' · канон №'+(st.canon?st.canon.counter:0)+(st.replica?' · РЕПЛИКА':'');
  document.getElementById('node').innerHTML=st.replica
    ?'<div>Режим: <b>реплика</b> (только чтение).</div><button onclick="api(&quot;promote&quot;).then(refresh)">Повысить до primary</button>'
    :'<div>Режим: <b>primary</b>. Квоты: '+esc(JSON.stringify(st.quotas||{}))+'</div>';
  document.getElementById('clients').innerHTML=(st.clientsList||[]).map(c=>\`<div class=row><b>\${esc(c.login)}</b>\${c.replica?' <i>реплика</i>':''} <span style=color:#8fa0bd>RTT \${c.rtt==null?'—':c.rtt+' мс'} · подключён \${new Date(c.since).toLocaleTimeString('ru-RU')}</span></div>\`).join('')||'<i style=color:#8fa0bd>клиентов нет</i>';
  const us=await api('users');
  document.getElementById('users').innerHTML=(us.users||[]).map(u=>\`
    <div class=row><b>\${esc(u.login)}</b> <span>\${esc(u.role)}</span>\${u.blocked?' <b style=color:#ef6a60>заблокирован</b>':''}
    <span style=color:#8fa0bd>emp:\${esc(u.emp||'—')} allow:\${esc((u.allow||[]).join(','))} deny:\${esc((u.deny||[]).join(','))}</span>
    <button onclick=resetPin('\${esc(u.login)}')>PIN</button>
    <button onclick="toggleBlock('\${esc(u.login)}',\${!!u.blocked})">\${u.blocked?'разблок.':'блок.'}</button>
    <button onclick=delUser('\${esc(u.login)}')>✕</button></div>\`).join('')||'<i style=color:#8fa0bd>аутентификация выключена (нет PT_USERS_FILE)</i>';
  const sg=await api('sigs');
  document.getElementById('sigs').innerHTML=(sg.sigs||[]).slice(0,80).map(s=>{
    const acked=Object.keys(s.acks||{});
    return\`<div class=row><b style=color:\${s.sev==='crit'?'#ef6a60':'#e79814'}>\${s.sev}</b> \${esc(s.text)}
      <span style=color:#8fa0bd>\${new Date(s.ts).toLocaleString('ru-RU')} · квитировали \${acked.length}: \${esc(acked.join(', ')||'—')}</span></div>\`}).join('')||'—';
  const bk=await api('backups');
  document.getElementById('backs').innerHTML=(bk.items||[]).map(x=>\`<div class=row>№\${x.counter} · метка \${esc(x.stamp||'')}
    <button onclick="restoreBk('\${esc(x.file)}')">восстановить</button></div>\`).join('')||'<i style=color:#8fa0bd>копий пока нет — создаются по расписанию (PT_BACKUP_CRON / PT_BACKUP_EVERY_MIN) или кнопкой</i>';
  const hs=await api('hist');
  document.getElementById('hist').innerHTML=(hs.items||[]).map(h=>\`<div class=row>№\${h.counter} · \${new Date(h.ts).toLocaleString('ru-RU')}
    <button onclick=rollback('\${esc(h.file)}')>откатить</button></div>\`).join('')||'—';
  const au=await api('audit',{limit:120});
  document.getElementById('aud').innerHTML=(au.lines||[]).map(l=>\`<div>\${new Date(l.ts).toLocaleTimeString('ru-RU')} <b>\${esc(l.ev)}</b> \${esc(l.detail||'')}</div>\`).join('')||'—';
  try{await loadXchg()}catch(e){}
}
async function loadXchg(){
  const r=await api('xchgLog',{limit:80,kind:document.getElementById('xKind').value,status:document.getElementById('xStatus').value});
  const st={ok:'#59d97c',warn:'#e79814',error:'#ef6a60'};
  document.getElementById('xMap').textContent='справочник Т-13: '+((r.map&&r.map.items)?r.map.items.length:0)+' переопределений'+((r.map&&r.map.ts)?' · обновлён '+new Date(r.map.ts).toLocaleString('ru-RU')+' ('+(r.map.by||'')+')':'');
  const items=r.items||[];
  document.getElementById('xchg').innerHTML=items.length
    ?'<table><thead><tr><th>Время</th><th>Операция</th><th>Статус</th><th>Подробности</th><th>Счётчики</th><th>Кто</th><th>Повтор</th></tr></thead><tbody>'
      +items.map(x=>\`<tr><td style=white-space:nowrap>\${new Date(x.ts).toLocaleString('ru-RU')}</td>
        <td><b>\${esc(x.kind)}</b> \${x.dir==='out'?'⇧ выгрузка':'⇩ импорт'}\${x.retryOf?' <i style=color:#8fa0bd>повтор</i>':''}</td>
        <td><b style=color:\${st[x.status]||'#8fa0bd'}>\${esc(x.status)}</b></td>
        <td>\${esc(x.detail||'')}</td>
        <td style=font-family:monospace>\${esc(Object.entries(x.counters||{}).map(([k,v])=>k+'='+v).join(' '))}</td>
        <td>\${esc(x.by||'—')}</td>
        <td>\${x.hasPayload&&x.status!=='ok'?'<button onclick="retryX(\\''+esc(x.id)+'\\')">↻ повтор</button>':''}\${x.retries?' <span style=color:#8fa0bd>×'+x.retries+'</span>':''}</td></tr>\`).join('')
      +'</tbody></table>'
    :'<i style=color:#8fa0bd>журнал обмена пуст — записи появляются при выгрузках и импортах «1С»/СКУД/OCR</i>';
}
async function retryX(id){
  if(!confirm('Повторить операцию обмена из журнала? Исходный запрос будет применён заново.'))return;
  const r=await api('xchgRetry',{id});
  alert(r.ok?('Повтор выполнен: '+r.status+(r.detail?' — '+r.detail:'')):('Повтор не выполнен: '+r.err));
  loadXchg();refresh();
}
async function addUser(){const login=document.getElementById('nLogin').value.trim();if(!login)return;
  await api('userSave',{user:{login,pin:document.getElementById('nPin').value||'0000',
    role:document.getElementById('nRole').value,emp:document.getElementById('nEmp').value.trim()||null}});refresh()}
async function delUser(l){if(!confirm('Удалить '+l+'?'))return;await api('userDel',{login:l});refresh()}
async function resetPin(l){const p=prompt('Новый PIN (4–16 цифр) для '+l);if(!p)return;await api('resetPin',{login:l,pin:p});alert('PIN установлен')}
async function toggleBlock(l,b){const us=await api('users');const u=(us.users||[]).find(x=>x.login===l);if(u)await api('userSave',{user:{...u,blocked:!b}});refresh()}
async function sendSig(){const t=document.getElementById('sigText').value.trim();if(!t)return;
  await api('signal',{text:t,sev:document.getElementById('sigSev').value});document.getElementById('sigText').value='';refresh()}
async function rollback(f){if(!confirm('Откатить канон к этой версии? Текущая будет заменена.'))return;await api('rollback',{file:f});refresh()}
async function restoreBk(f){if(!confirm('Восстановить канон из этой копии? Текущая версия станет историей.'))return;await api('backupRestore',{file:f});refresh()}
async function dlCsv(){const r=await api('auditCsv');if(!r.ok)return alert('Журнал пуст или недоступен');
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([r.csv],{type:'text/csv'}));
  a.download='plan-tabel-server-audit.csv';a.click()}
refresh();setInterval(refresh,5000);
</script></body>`;
}

/* ---------- WebSocket ---------- */
const WSS=new WebSocketServer({server});
const CLIENTS=new Set();
function broadcast(m,except){
  const s=JSON.stringify(m);
  for(const c of WSS.clients){if(c!==except&&c.readyState===1)try{c.send(s)}catch(e){}}
}
let _presLast=0,_presT=null;
function broadcastPresence(){
  /* 3.34: троттлинг leading+trailing — при массовых подключениях (500+ клиентов)
     не рассылаем presence чаще раза в 1,5 с; первый вызов всегда мгновенный */
  const fire=()=>{_presLast=Date.now();
    const logins=[...new Set([...CLIENTS].map(c=>c.login||c.by).filter(Boolean))];
    broadcast({type:'presence',logins});};
  if(Date.now()-_presLast>=1500){fire();return}
  if(_presT)clearTimeout(_presT);
  _presT=setTimeout(()=>{_presT=null;fire()},1500-(Date.now()-_presLast));
}
function broadcastPerms(u){
  if(!u)return;
  for(const c of CLIENTS){
    if(c.login===u.login){
      send(c,{type:'permsUpdate',login:u.login,role:u.role,mods:u.modsOff||[],
        perms:{allow:u.allow||[],deny:u.deny||[]}});
    }
  }
}
const send=(c,m)=>{try{if(c.readyState===1)c.send(JSON.stringify(m))}catch(e){}};

WSS.on('connection',(ws,req)=>{
  ws.by='';ws.login='';ws.token='';ws.isReplica=false;
  ws._socket=req.socket;ws._headers=req.headers||{};   /* 3.34: для SSO и IP в аудите */
  ws.since=now();ws.rtt=null;ws._pingTs=0;   /* 3.21: статистика клиента */
  CLIENTS.add(ws);
  ws.on('message',async data=>{
    let m;try{m=JSON.parse(data.toString('utf8'))}catch(e){return}
    try{await handle(ws,m)}catch(e){
      send(ws,{type:'err',text:'ошибка сервера: '+(e&&e.message||e)});
      audit('ws-error',String(e&&e.message||e).slice(0,200));
    }
  });
  ws.on('close',()=>{CLIENTS.delete(ws);broadcastPresence()});
  ws.isAlive=true;
  ws.on('pong',()=>{ws.isAlive=true;if(ws._pingTs)ws.rtt=Date.now()-ws._pingTs});   /* 3.21: RTT */
});
setInterval(()=>{for(const c of WSS.clients){if(c.isAlive===false){try{c.terminate()}catch(e){}continue}c.isAlive=false;c._pingTs=Date.now();try{c.ping()}catch(e){}}},30000);

/* ===== 3.30: общие операции публикации/ops для WS и REST ===== */
async function complianceCheck(incoming,force,login){
  const st=canonDecode(incoming);if(!st||!CANON)return null;
  const old=canonDecode(CANON);if(!old)return null;
  const locks=st.locks||old.locks||{};
  const closed=Object.keys(locks).filter(mk=>locks[mk]&&locks[mk].mode==='closed');
  if(!closed.length)return null;
  const touched=closed.filter(mk=>JSON.stringify((st.plan||{})[mk]||null)!==JSON.stringify((old.plan||{})[mk]||null)
    ||JSON.stringify((st.fact||{})[mk]||null)!==JSON.stringify((old.fact||{})[mk]||null));
  if(!touched.length)return null;
  if(force){await audit('compliance-override','force-публикация touching закрытые периоды '+touched.join(','),{login});return null}
  await audit('compliance-deny','публикация отклонена: закрытые периоды '+touched.join(','),{login});
  return{kind:'err',text:'Комплаенс сервера: периоды '+touched.join(', ')+' закрыты — изменение отклонено'};
}
async function doPush(AU,o){
  if(REPLICA_OF&&!REPLICA_OFF)return{kind:'err',text:'узел работает как реплика (только чтение)'};
  if(USERS&&!can(AU,'edit')){
    await audit('deny','отклонена публикация (deny: edit)',{login:AU.login});
    return{kind:'err',text:'публикация запрещена вашими правами (deny: edit)'};
  }
  const incoming={counter:0,ts:+o.ts||now(),by:String(o.by||AU.login||'').slice(0,60),org:o.org||'',
    gz:o.gz||null,data:o.gz?null:(o.data||null)};
  if(!incoming.gz&&!incoming.data)return{kind:'err',text:'пустая публикация'};
  if(USERS&&(can(AU,'planOnly')||!can(AU,'staff')||!can(AU,'import'))){
    const newState=canonDecode(incoming),oldState=canonDecode(CANON);
    if(newState&&oldState){
      const changed=changedSections(oldState,newState);
      if(can(AU,'planOnly')){
        const banned=changed.filter(k=>STAFF_SECTIONS.has(k)||IMPORT_SECTIONS.has(k));
        if(banned.length){await audit('deny','planOnly: отклонена публикация, разделы '+banned.join(','),{login:AU.login});
          return{kind:'err',text:'Роль «табельщик» (planOnly): нельзя менять разделы '+banned.join(', ')}}
      }
      if(!can(AU,'staff')&&changed.some(k=>STAFF_SECTIONS.has(k))){
        await audit('deny','отклонена публикация (deny: staff)',{login:AU.login});
        return{kind:'err',text:'Изменение штатки и справочников запрещено (deny: staff)'};
      }
      if(!can(AU,'import')&&changed.some(k=>IMPORT_SECTIONS.has(k))){
        await audit('deny','отклонена публикация (deny: import)',{login:AU.login});
        return{kind:'err',text:'Изменение импорта и документов запрещено (deny: import)'};
      }
    }
  }
  const comp=await complianceCheck(incoming,o.force,AU.login);
  if(comp)return comp;
  if(CANON&&!o.force&&(+o.base||0)!==CANON.counter)return{kind:'conflict'};
  const ql=quotaLeft(AU.role);
  if(ql===0){await audit('quota','превышена квота публикаций '+AU.role,{login:AU.login});
    return{kind:'err',text:'Суточная квота публикаций исчерпана'}}
  incoming.counter=(CANON?CANON.counter:0)+1;
  CANON=incoming;quotaUse(AU.role);MET.pushes++;
  await persistCanon();
  await audit('push','канон №'+CANON.counter+' от '+CANON.by,{login:AU.login});
  return{kind:'ok',counter:CANON.counter,quotaLeft:quotaLeft(AU.role)};
}
async function doOps(AU,cid,ops){
  if(REPLICA_OF&&!REPLICA_OFF)return{kind:'err',reason:'узел-реплика (только чтение)'};
  if(!Array.isArray(ops)||!ops.length)return{kind:'err',reason:'пустой батч'};
  if(USERS&&!can(AU,'edit')){
    const allSelf=ops.every(o=>o.k==='req'&&selfReqOk(o,AU));
    if(!allSelf){
      await audit('deny','отклонены операции (deny: edit)',{login:AU.login});
      return{kind:'err',reason:'правка запрещена вашими правами (deny: edit)'};
    }
  }
  if(USERS&&can(AU,'planOnly')&&ops.some(o=>o.k!=='plan'&&o.k!=='fact'&&!(o.k==='req'&&selfReqOk(o,AU)))){
    await audit('deny','planOnly: отклонены операции вне плана/факта',{login:AU.login});
    return{kind:'err',reason:'роль «табельщик»: разрешены только план и факт'};
  }
  const st=canonDecode(CANON);
  if(!st)return{kind:'err',reason:'на сервере нет канона — сначала полная публикация'};
  /* 3.30: серверный комплаенс-триггер — закрытый период не редактируется операциями */
  const locks=st.locks||{};
  for(const op of ops){
    if(op.k==='plan'||op.k==='fact'){
      const mk=op.y+'-'+String(op.m).padStart(2,'0');
      const l=locks[mk];
      if(l&&l.mode==='closed'){
        await audit('compliance-deny','операция отклонена: период '+mk+' закрыт',{login:AU.login,cid});
        return{kind:'err',reason:'период '+mk+' закрыт (серверный комплаенс, 3.30)'};
      }
    }
  }
  const before=JSON.stringify(st);
  let applied=0;
  try{
    for(const op of ops){
      if(USERS&&op.k==='req'&&!can(AU,'edit')&&!selfReqOk(op,AU,st)){
        throw new Error('заявка не «за себя» — недостаточно прав');
      }
      if(applyOp(st,op))applied++;
    }
  }catch(e){
    await audit('ops-err',String(e.message||e).slice(0,160),{login:AU.login,cid});
    return{kind:'err',reason:String(e.message||e).slice(0,160)};
  }
  if(JSON.stringify(st)===before&&applied===0){
    return{kind:'ok',counter:CANON?CANON.counter:0,quotaLeft:quotaLeft(AU.role),applied:0,changed:false};
  }
  CANON={counter:(CANON?CANON.counter:0)+1,ts:now(),by:CANON?CANON.by:AU.login,
    org:CANON?CANON.org:(st.org||''),gz:gzEnc(st)};
  await persistCanon();
  MET.opsBatches++;MET.opsApplied+=applied;
  await audit('ops','батч '+ops.length+' оп. ('+applied+' применено), канон №'+CANON.counter,{login:AU.login,cid});
  return{kind:'ok',counter:CANON.counter,quotaLeft:quotaLeft(AU.role),applied,changed:true};
}
async function handle(ws,m){
  const t=m.type;
  /* --- реплика --- */
  if(t==='replicaHello'){
    if(SHARED_SECRET&&m.secret!==SHARED_SECRET){audit('replica-deny','реплика с неверным секретом');return send(ws,{type:'err',text:'secret mismatch'})}
    ws.isReplica=true;ws.by='replica';
    send(ws,{type:'state',canon:CANON});
    return audit('replica','подключена реплика');
  }
  if(t==='hello'){
    ws.by=String(m.by||'').slice(0,60);
    if(USERS){
      let s=tokUser(m.token);
      /* 3.34: SSO — токена нет, но реверс-прокси передал доверенный заголовок */
      if(!s&&SSO_HEADER&&ws._headers&&ws._headers[SSO_HEADER]){
        const usr=await ssoUser(ws._headers[SSO_HEADER],SSO_NAME_HEADER?ws._headers[SSO_NAME_HEADER]:'');
        if(usr){
          const tk=issueToken(usr);ws.token=tk;
          await audit('sso-auth','WS-вход через SSO: '+usr.login+' ('+(usr.role||'viewer')+')');
          send(ws,{type:'auth',token:tk,login:usr.login,role:usr.role||'viewer',emp:usr.emp||null,
            mods:usr.modsOff||[],perms:{allow:usr.allow||[],deny:usr.deny||[]}});
          s=tokUser(tk);
        }
      }
      if(!s){ws.login='';return send(ws,{type:'state',canon:null,authRequired:true,tokenOk:false})}
      if(m.token)ws.token=m.token;ws.login=s.login;
      const usr=findUser(s.login);
      if(usr&&usr.blocked){TOKENS.delete(m.token);return send(ws,{type:'authfail',text:'Учётная запись заблокирована'})}
      send(ws,{type:'state',canon:CANON,authRequired:true,tokenOk:true,login:s.login,role:s.role,
        emp:s.emp,mods:s.modsOff,perms:{allow:s.allow,deny:s.deny},quotaLeft:quotaLeft(s.role)});
    }else{
      ws.login=ws.by;
      send(ws,{type:'state',canon:CANON,authRequired:false,quotaLeft:null});
    }
    send(ws,{type:'sigHist',sigs:SIGS.sigs.slice(0,100)});
    send(ws,{type:'chatHist',msgs:CHAT.msgs.slice(-100)});
    broadcastPresence();
    return;
  }
  if(t==='login'){
    if(!USERS)return send(ws,{type:'err',text:'аутентификация выключена'});
    const usr=findUser(String(m.login||''));
    if(!usr||usr.blocked||usr.pinHash!==String(m.pinHash||'')){
      await audit('auth-fail','неверный вход: '+String(m.login||'').slice(0,40),{ip:ws._socket&&ws._socket.remoteAddress});
      return send(ws,{type:'authfail',text:'Неверная пара логин/PIN'});
    }
    const token=issueToken(usr);ws.token=token;ws.login=usr.login;
    await audit('auth-ok','вход: '+usr.login+' ('+usr.role+')');
    send(ws,{type:'auth',token,login:usr.login,role:usr.role||'viewer',emp:usr.emp||null,
      mods:usr.modsOff||[],perms:{allow:usr.allow||[],deny:usr.deny||[]}});
    broadcastPresence();
    return;
  }
  const{u:AU,need,ok}=authOf(m,ws);
  if(need&&!ok)return send(ws,{type:'state',canon:null,authRequired:true,tokenOk:false});

  /* --- публикация канона --- */
  if(t==='push'||t==='force'){
    const r=await doPush(AU,{base:m.base,force:t==='force',ts:m.ts,by:m.by,org:m.org,gz:m.gz,data:m.data});
    if(r.kind==='err')return send(ws,{type:'err',text:r.text});
    if(r.kind==='conflict')return send(ws,{type:'conflict',canon:CANON});
    send(ws,{type:'ack',counter:r.counter,quotaLeft:r.quotaLeft});
    broadcast({type:'update',canon:CANON},ws);
    return;
  }
  /* --- операционный протокол --- */
  if(t==='ops'){
    const r=await doOps(AU,m.cid,m.ops);
    if(r.kind==='err')return send(ws,{type:'opsErr',cid:m.cid,reason:r.reason});
    send(ws,{type:'opsAck',cid:m.cid,counter:r.counter,quotaLeft:r.quotaLeft});
    if(r.changed)broadcast({type:'update',canon:CANON},ws);
    return;
  }
  /* --- чат --- */
  if(t==='chat'){
    if(USERS&&!can(AU,'chat')){
      await audit('deny','отклонено сообщение чата (deny: chat)',{login:AU.login});
      return send(ws,{type:'err',text:'мессенджер запрещён вашими правами (deny: chat)'});
    }
    const msg={id:'m'+now().toString(36)+Math.random().toString(36).slice(2,6),
      login:AU.login||String(m.by||'').slice(0,40)||'?',text:String(m.text||'').slice(0,2000),
      channel:String(m.channel||'general').slice(0,40),ts:now()};
    if(m.replyTo)msg.replyTo=m.replyTo;
    CHAT.msgs.push(msg);if(CHAT.msgs.length>CHAT_MAX)CHAT.msgs=CHAT.msgs.slice(-CHAT_MAX);
    persistChat();
    broadcast({type:'chat',msg});
    if(m.cid)send(ws,{type:'chatAck',id:m.cid});
    return;
  }
  if(t==='chatRead'){broadcast({type:'chatRead',ids:m.ids||[],login:AU.login||ws.by});return}
  if(t==='typing'){broadcast({type:'typing',login:AU.login||ws.by,channel:m.channel||'general'},ws);return}
  /* --- самоознакомление (подписи) --- */
  if(t==='ackSign'){
    if(USERS&&!can(AU,'sign')){
      await audit('deny','отклонено самоознакомление (deny: sign)',{login:AU.login});
      return send(ws,{type:'err',text:'самоознакомление запрещено вашими правами (deny: sign)'});
    }
    const st=canonDecode(CANON);
    if(!st)return send(ws,{type:'err',text:'нет канона'});
    const eid=AU.emp||('login:'+(AU.login||ws.by));
    st.acks=st.acks||{};st.acks[m.year]=st.acks[m.year]||{};
    const entry={ts:now(),by:AU.login||ws.by,digest:String(m.digest||'').slice(0,128)};
    st.acks[m.year][eid]=entry;
    CANON={counter:(CANON?CANON.counter:0)+1,ts:now(),by:CANON?CANON.by:entry.by,org:CANON?CANON.org:'',gz:gzEnc(st)};
    await persistCanon();
    await audit('ackSign','ознакомление '+m.year+' · '+eid,{login:AU.login});
    send(ws,{type:'ackOk'});
    broadcast({type:'ackUpdate',year:m.year,eid,entry});
    return;
  }
  /* --- сигналы: квитирование и запрос архива --- */
  if(t==='sigAck'){
    const login=AU.login||ws.by;if(!login)return;
    const s=SIGS.sigs.find(x=>x.sid===m.sid);
    if(s){s.acks=s.acks||{};s.acks[login]=now();await persistSigs();
      await audit('sigAck','квитирование '+m.sid,{login});
      broadcast({type:'sigAckUpdate',sid:m.sid,login,ts:s.acks[login]});}
    return;
  }
  if(t==='sigQuery'){
    const from=+m.from||0,to=+m.to||now(),lim=Math.min(+m.limit||600,600);
    const sigs=SIGS.sigs.filter(s=>s.ts>=from&&s.ts<=to).slice(0,lim);
    return send(ws,{type:'sigList',cid:m.cid,sigs});
  }
  if(t==='ping')return send(ws,{type:'pong',ts:now()});
}
/* разделы канона для групп прав */
const PLAN_SECTIONS=new Set(['plan','fact']);
const STAFF_SECTIONS=new Set(['employees','departments','reasons','rules','patterns','certTypes','hol']);
const IMPORT_SECTIONS=new Set(['docs','uploads','aliases']);
/* служебные разделы меняются при любой сессии (wsUrl, журнал, снимки) — для deny-сверки игнорируются */
const VOLATILE_SECTIONS=new Set(['settings','log','snapshots','acks','version','org']);
function changedSections(a,b){
  const keys=new Set([...Object.keys(a||{}),...Object.keys(b||{})]);
  const out=[];
  for(const k of keys){
    if(VOLATILE_SECTIONS.has(k))continue;
    if(JSON.stringify(a?a[k]:null)!==JSON.stringify(b?b[k]:null))out.push(k);
  }
  return out;
}
/* «заявка за себя»: eid операции совпадает с сотрудником учётки */
function selfReqOk(op,AU,st){
  if(!AU.emp)return false;
  if(op.sub==='vac')return op.req&&op.req.eid===AU.emp;
  if(op.sub==='swap')return op.req&&(op.req.eidA===AU.emp||op.req.eid===AU.emp||op.req.eidB===AU.emp);
  if(op.sub==='vacDel'||op.sub==='swapDel'){
    const s=st||canonDecode(CANON);if(!s)return false;
    if(op.sub==='vacDel'){const r=(s.vac||[]).find(x=>x.id===op.id);return r&&r.eid===AU.emp}
    const r=(s.swaps||[]).find(x=>x.id===op.id);return r&&(r.eidA===AU.emp||r.eid===AU.emp||r.eidB===AU.emp);
  }
  return false;
}
/* атомарное применение одной операции к состоянию канона */
function applyOp(st,op){
  const mk=y=>`${y.y}-${String(y.m).padStart(2,'0')}`;
  if(op.k==='plan'||op.k==='fact'){
    const store=op.k==='plan'?(st.plan=st.plan||{}):(st.fact=st.fact||{});
    const key=mk(op);
    store[key]=store[key]||{};
    store[key][op.eid]=store[key][op.eid]||{};
    if(op.code==null||op.code==='')delete store[key][op.eid][op.d];
    else store[key][op.eid][op.d]=String(op.code);
    return true;
  }
  if(op.k==='req'){
    if(op.sub==='vac'){
      if(!op.req||!op.req.id)return false;
      st.vac=Array.isArray(st.vac)?st.vac:[];
      const i=st.vac.findIndex(x=>x.id===op.req.id);
      if(i>=0)st.vac[i]=op.req;else st.vac.push(op.req);
      return true;
    }
    if(op.sub==='vacDel'){
      if(!Array.isArray(st.vac))return false;
      const n=st.vac.length;st.vac=st.vac.filter(x=>x.id!==op.id);return st.vac.length!==n;
    }
    if(op.sub==='swap'){
      if(!op.req||!op.req.id)return false;
      st.swaps=Array.isArray(st.swaps)?st.swaps:[];
      const i=st.swaps.findIndex(x=>x.id===op.req.id);
      if(i>=0)st.swaps[i]=op.req;else st.swaps.push(op.req);
      return true;
    }
    if(op.sub==='swapDel'){
      if(!Array.isArray(st.swaps))return false;
      const n=st.swaps.length;st.swaps=st.swaps.filter(x=>x.id!==op.id);return st.swaps.length!==n;
    }
  }
  return false;
}

/* ---------- реплика: тянем канон с primary ---------- */
let REPLICA_WS=null;
function replicaConnect(){
  if(!REPLICA_OF||REPLICA_OFF)return;
  try{
    const ws=new WebSocket(REPLICA_OF);
    REPLICA_WS=ws;
    ws.on('open',()=>{try{ws.send(JSON.stringify({type:'replicaHello',secret:SHARED_SECRET}))}catch(e){}});
    ws.on('message',data=>{
      let m;try{m=JSON.parse(data.toString('utf8'))}catch(e){return}
      if((m.type==='state'||m.type==='update')&&m.canon){
        CANON=m.canon;persistCanon();
        broadcast({type:'update',canon:CANON});
      }
    });
    ws.on('close',()=>{REPLICA_WS=null;if(!REPLICA_OFF)setTimeout(replicaConnect,3000)});
    ws.on('error',()=>{try{ws.close()}catch(e){}});
  }catch(e){setTimeout(replicaConnect,5000)}
}
replicaConnect();

/* ---------- 3.23: резервные копии канона ---------- */
async function makeBackup(who){
  if(!CANON)return null;
  try{await mkdir(BACKUP_DIR,{recursive:true})}catch(e){}
  const d=new Date();
  const name=`backup-${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}-`
    +`${String(d.getHours()).padStart(2,'0')}${String(d.getMinutes()).padStart(2,'0')}${String(d.getSeconds()).padStart(2,'0')}-c${CANON.counter}.json`;
  const rec={ts:now(),counter:CANON.counter,by:CANON.by,who:who||'cron',canon:CANON};
  try{await writeFile(path.join(BACKUP_DIR,name),encWrap(rec))}catch(e){return null}
  lastBackupTs=now();MET.backups++;
  /* ротация: держим BACKUP_KEEP последних */
  try{
    const files=(await readdir(BACKUP_DIR)).filter(f=>f.startsWith('backup-')).sort();
    while(files.length>BACKUP_KEEP){const f=files.shift();await unlink(path.join(BACKUP_DIR,f)).catch(()=>{})}
  }catch(e){}
  await audit('backup','резервная копия канона №'+CANON.counter+(who?' ('+who+')':' (по расписанию)'));
  return name;
}
setInterval(()=>{
  const d=new Date(),hhmm=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
  if(BACKUP_TIMES.length){
    const key=hhmm+'|'+d.toDateString();
    if(BACKUP_TIMES.includes(hhmm)&&key!==lastBackupKey){lastBackupKey=key;makeBackup()}
  }else if(BACKUP_EVERY_MIN&&now()-lastBackupTs>=BACKUP_EVERY_MIN*60000){makeBackup()}
},20000);

/* ---------- cron-дайджест ---------- */
let lastDigestKey='';
setInterval(()=>{
  if(!DIGEST_TIMES.length)return;
  const d=new Date(),hhmm=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
  if(!DIGEST_TIMES.includes(hhmm))return;
  const key=hhmm+'|'+d.toDateString();
  if(key===lastDigestKey)return;
  lastDigestKey=key;
  const st=canonDecode(CANON);
  const y=d.getFullYear(),mo=d.getMonth()+1,mk2=`${y}-${String(mo).padStart(2,'0')}`;
  let cells=0,duties=0;
  if(st&&st.plan&&st.plan[mk2])for(const eid of Object.keys(st.plan[mk2]))
    for(const dd of Object.keys(st.plan[mk2][eid])){cells++;
      if(st.reasons){const code=String(st.plan[mk2][eid][dd]).split('|')[0];
        const r=st.reasons.find(x=>x.code===code);if(r&&r.cat==='duty')duties++}}
  const vacRev=st&&Array.isArray(st.vac)?st.vac.filter(r=>r.status==='review').length:0;
  const unacked=SIGS.sigs.filter(s=>s.ts>now()-7*864e5&&Object.keys(s.acks||{}).length===0).length;
  const text=`📋 Дайджест ${d.toLocaleDateString('ru-RU')} ${hhmm}: план ${mo}/${y} — ${cells} отметок, дежурств ${duties}; на согласовании отпусков ${vacRev}; неквитированных сигналов ${unacked}; клиентов ${WSS.clients.size}.`;
  const msg={id:'m'+now().toString(36),login:'Сервер',text,channel:'general',ts:now()};
  CHAT.msgs.push(msg);persistChat();broadcast({type:'chat',msg});
  if(E('PT_DIGEST_OUT'))appendFile(path.resolve(E('PT_DIGEST_OUT')),text+'\n').catch(()=>{});
  if(E('PT_DIGEST_WEBHOOK'))fetch(E('PT_DIGEST_WEBHOOK'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})}).catch(()=>{});
  audit('digest','cron-дайджест отправлен');
},20000);

/* ---------- старт ---------- */
server.listen(PORT,HOST,()=>{
  const ifs=[];
  try{
    for(const[n,addrs]of Object.entries(os.networkInterfaces()))
      for(const a of addrs||[])if(a.family==='IPv4'&&!a.internal)ifs.push(`http://${a.address}:${PORT}/`);
  }catch(e){}
  console.log(`🛰 WFM ${VER} · сервер ЛВС на порту ${PORT}`);
  console.log(`   приложение: ${APP_FILE||'(не найдено — задайте PT_FILE)'}`);
  console.log(`   канон: ${CANON_FILE}${CANON?' (№'+CANON.counter+')':' (пуст — первый клиент опубликует базу)'}`);
  console.log(`   аутентификация: ${USERS?'вкл ('+USERS.length+' польз.)':'выкл'}`);
  console.log(`   хранилище канона: ${DB?'SQLite ('+DB_FILE+')':'JSON ('+CANON_FILE+')'}${CANON_KEY?' · шифрование at rest: AES-256-GCM':''}`);
  console.log(`   REST API: http://localhost:${PORT}/api/v1 (login, canon, push, ops, tabel, skud, ocr, sigs, signal, users)`);
  console.log(`   обмен 3.35: /api/v1/xchg/map (сопоставление кодов Т-13), /api/v1/xchg/log (журнал выгрузок/импортов), /api/v1/xchg/retry (повтор)`);
  console.log(`   бригады 3.49: GET/PUT /api/v1/brigades (общий справочник бригад, файл ${path.basename(BRIG_FILE)})`);
  console.log(`   бюджеты 3.53: GET/PUT /api/v1/budgets (лимита ФОТ, файл ${path.basename(BUDG_FILE)})`);
  console.log(`   журнал обмена: ${XCHG_FILE} (до ${XCHG_MAX} записей)${XCHG.items.length?' · сейчас '+XCHG.items.length:''}`);
  if(SSO_HEADER)console.log(`   SSO: доверенный заголовок «${SSO_HEADER}» → роль ${SSO_ROLE}${SSO_PROVISION?' (авторегистрация вкл)':' (только существующие учётки)'}`);
  if(REPLICA_OF)console.log(`   режим: РЕПЛИКА от ${REPLICA_OF}`);
  ifs.forEach(a=>console.log('   LAN: '+a));
  console.log(`   статус: http://localhost:${PORT}/status · админ: /admin · здоровье: /health`);
});
