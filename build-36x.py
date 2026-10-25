#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.60–3.62 поверх канонической цепочки main (3.59):
   3.60 снапшот-дифф канона (локально и против сервера),
   3.61 бригадир в печатной ведомости, ICS и «Моём месяце»,
   3.62 подписи приказов (SHA-256) и реестр приказов."""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))

MODULE_360 = r"""/* ================= 3.60: СНАПШОТ-ДИФФ КАНОНА =================
   Сравнение офлайн-снапшота (3.59) с текущим каноном и с каноном сервера
   (GET /api/v1/canon): ячейки плана (add/del/chg по месяцам), счётчики
   справочников, counter канона. Помогает решить «публиковать force или
   сначала слить изменения» после долгого офлайна. */
function diffStates(a,b){
  const out={months:[],cellsAdd:0,cellsDel:0,cellsChg:0,dicts:[],counterA:a.counter||0,counterB:b.counter||0};
  const mks=new Set([...Object.keys(a.plan||{}),...Object.keys(b.plan||{})]);
  mks.forEach(mk=>{
    const pa=(a.plan||{})[mk]||{},pb=(b.plan||{})[mk]||{};
    let add=0,del=0,chg=0;
    const eids=new Set([...Object.keys(pa),...Object.keys(pb)]);
    eids.forEach(eid=>{
      const ra=pa[eid]||{},rb=pb[eid]||{};
      const ds=new Set([...Object.keys(ra),...Object.keys(rb)]);
      ds.forEach(d=>{
        const va=ra[d],vb=rb[d];
        if(va==null&&vb!=null)add++;
        else if(va!=null&&vb==null)del++;
        else if(va!==vb)chg++;
      });
    });
    if(add||del||chg)out.months.push({mk,add,del,chg});
    out.cellsAdd+=add;out.cellsDel+=del;out.cellsChg+=chg;
  });
  [['employees','штатка'],['departments','подразделения'],['reasons','причины'],['patterns','шаблоны'],
   ['brigades','бригады'],['budgets','бюджеты'],['vac','отпуска'],['swaps','обмены']].forEach(([k,label])=>{
    const na=Array.isArray(a[k])?a[k].length:Object.keys(a[k]||{}).length;
    const nb=Array.isArray(b[k])?b[k].length:Object.keys(b[k]||{}).length;
    if(na!==nb)out.dicts.push({label,a:na,b:nb});
  });
  return out;
}
async function pubSnapState(){
  const s=pubSnapLoad();if(!s)return null;
  const json=s.data||(s.gz?await gzDecompress(s.gz):null);
  if(!json)return null;
  try{return JSON.parse(json)}catch(e){return null}
}
async function pubSnapDiffLocal(){
  const old=await pubSnapState();
  if(!old)return null;
  return diffStates(old,state);
}
async function pubSnapDiffServer(){
  if(!/^https?:$/.test(location.protocol))return{err:'офлайн: сравнение с сервером доступно по HTTP'};
  const old=await pubSnapState();
  if(!old)return{err:'нет снапшота'};
  try{
    const r=await fetch('api/v1/canon'+(wsToken()?'?token='+encodeURIComponent(wsToken()):''),{cache:'no-store'});
    const j=await r.json();
    let srv=null;
    if(j&&j.gz)srv=JSON.parse(await gzDecompress(j.gz));
    else if(j&&j.data)srv=JSON.parse(j.data);
    else if(j&&j.state)srv=j.state;
    else if(j&&j.canon&&j.canon.gz)srv=JSON.parse(await gzDecompress(j.canon.gz));
    if(!srv)return{err:'на сервере нет канона'};
    return{diff:diffStates(old,srv),serverCounter:srv.counter||0};
  }catch(e){return{err:'сервер недоступен: '+String(e.message||e).slice(0,90)}}
}
function diffRenderHtml(d,title){
  if(!d)return `<div class="status err" style="margin-top:8px">${esc(title)}: нет данных.</div>`;
  if(d.err)return `<div class="status err" style="margin-top:8px">${esc(title)}: ${esc(d.err)}</div>`;
  const tot=d.cellsAdd+d.cellsDel+d.cellsChg;
  return `<div class="status ${tot?'':'ok'}" style="margin-top:8px"><b>${esc(title)}</b>: ячеек добавлено ${fmtStd(d.cellsAdd)}, удалено ${fmtStd(d.cellsDel)}, изменено ${fmtStd(d.cellsChg)}; counter ${fmtStd(d.counterA)} → ${fmtStd(d.counterB)}${d.serverCounter!=null?` (сервер: ${fmtStd(d.serverCounter)})`:''}.</div>
  ${d.months.length?`<div class="scroll-x" style="max-height:26vh;overflow:auto;margin-top:6px"><table class="rtbl"><thead><tr><th>Месяц</th><th class="n">+</th><th class="n">−</th><th class="n">изм.</th></tr></thead><tbody>${d.months.slice(0,24).map(m=>`<tr><td>${esc(m.mk)}</td><td class="n">${fmtStd(m.add)}</td><td class="n">${fmtStd(m.del)}</td><td class="n">${fmtStd(m.chg)}</td></tr>`).join('')}</tbody></table></div>`:''}
  ${d.dicts.length?`<div style="margin-top:6px">${d.dicts.map(x=>`<span class="pill a" style="margin:1px">${esc(x.label)}: ${fmtStd(x.a)} → ${fmtStd(x.b)}</span>`).join(' ')}</div>`:'<div class="hint" style="margin-top:6px">Справочники не менялись.</div>'}`;
}
"""

MODULE_362 = r"""/* ================= 3.62: ПОДПИСИ ПРИКАЗОВ И РЕЕСТР =================
   Подпись приказа = SHA-256 текста (фолбэк FNV при отсутствии crypto.subtle);
   реестр state.orders: номер, дата, автор, текст, hash, статус; сверка подписи
   и выгрузка текста из реестра. */
function ordersReg(){if(!Array.isArray(state.orders))state.orders=[];return state.orders}
async function sha359(text){
  try{
    const buf=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(String(text)));
    return Array.from(new Uint8Array(buf)).map(x=>x.toString(16).padStart(2,'0')).join('');
  }catch(e){
    let h=5381;const s=String(text);
    for(let i=0;i<s.length;i++)h=((h*33)^s.charCodeAt(i))>>>0;
    return 'fnv-'+h.toString(16);
  }
}
async function orderSign(text,num,tplName){
  const rec={id:uid('ord'),num:num||'',tpl:tplName||'',date:new Date().toLocaleDateString('ru-RU'),
    ts:Date.now(),by:actor(),text:String(text),hash:await sha359(text),status:'signed'};
  ordersReg().unshift(rec);
  if(ordersReg().length>100)ordersReg().length=100;
  save(true);
  audit('Приказ подписан в реестр',`${rec.num||'б/н'} · ${rec.tpl} · SHA-256 ${rec.hash.slice(0,12)}…`,'orders');
  try{teleHit('order:sign')}catch(e){}
  toast('Приказ в реестре: подпись '+rec.hash.slice(0,8)+'…','ok');
  try{renderOrdersRegistry()}catch(e){}
  return rec;
}
async function orderVerify(rec){
  if(!rec)return false;
  return (await sha359(rec.text))===rec.hash;
}
function renderOrdersRegistry(){
  const box=$('ordersRegBox');if(!box)return;
  const L=ordersReg();
  box.innerHTML=L.length?L.slice(0,15).map(r=>`<div class="log-row" style="align-items:center">
    <span style="flex:1">${tsStr(r.ts)} · <b>${esc(r.num||'б/н')}</b>${r.tpl?` · ${esc(r.tpl)}`:''} · ${esc(r.by)} · <span class="mono hint">${esc(String(r.hash).slice(0,16))}…</span></span>
    <button class="btn ghost tiny" data-ordv="${r.id}" title="Пересчитать SHA-256 текста и сравнить с подписью">✔ сверить</button>
    <button class="btn ghost tiny" data-ordd="${r.id}" title="Выгрузить подписанный текст">⤓ текст</button>
  </div>`).join(''):'<div class="hint">Реестр пуст: подпишите приказ из конструктора («✍ Подписать в реестр»).</div>';
  box.querySelectorAll('[data-ordv]').forEach(b=>b.onclick=async()=>{
    const r=ordersReg().find(x=>x.id===b.dataset.ordv);if(!r)return;
    const okv=await orderVerify(r);
    toast(okv?'Подпись корректна: текст не изменялся':'ПОДПИСЬ НЕ СХОДИТСЯ: текст изменён после подписания',okv?'ok':'err');
    audit('Сверка подписи приказа',(okv?'корректна':'НЕСООТВЕТСТВИЕ')+' · '+(r.num||'б/н'),'orders');
  });
  box.querySelectorAll('[data-ordd]').forEach(b=>b.onclick=()=>{
    const r=ordersReg().find(x=>x.id===b.dataset.ordd);if(!r)return;
    download('prikaz-podpisan-' +(r.num||r.id)+'.txt',r.text,'text/plain');
    toast('Текст приказа выгружен','ok');
  });
}
"""

def V360(c):
    c.ver('3.60')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_360 + '\n' + c.s[i:]
    c.rep("""    <div class="hint">Снапшот — страховка отложенной публикации (3.54): если устройство потеряется до реконнекта, снимок канона останется в localStorage и его можно выгрузить и импортировать на другом рабочем месте. После успешной доставки публикации снимок очищается автоматически.</div>`,
    buttons:'<button class="btn ghost" data-cps359>Закрыть</button><button class="btn ghost" id="psDl359">⤓ Выгрузить снимок</button><button class="btn warn" id="psDel359">✕ Очистить</button>',""",
          """    <div class="hint">Снапшот — страховка отложенной публикации (3.54): если устройство потеряется до реконнекта, снимок канона останется в localStorage и его можно выгрузить и импортировать на другом рабочем месте. После успешной доставки публикации снимок очищается автоматически.</div>
    <div class="mini" style="margin-top:8px;display:flex;gap:6px">
      <button class="btn ghost small" id="psDiffLocal" title="Сравнить снимок с текущим каноном этого рабочего места">🔍 Дифф с текущим</button>
      <button class="btn ghost small" id="psDiffSrv" title="Сравнить снимок с каноном сервера ЛВС (GET /api/v1/canon)">🌐 Дифф с сервером</button>
    </div>
    <div id="psDiff"></div>`,
    buttons:'<button class="btn ghost" data-cps359>Закрыть</button><button class="btn ghost" id="psDl359">⤓ Выгрузить снимок</button><button class="btn warn" id="psDel359">✕ Очистить</button>',""", 'snap diff ui')
    c.rep("""      b.querySelector('#psDel359').onclick=()=>{pubSnapClear();closeModal();toast('Снапшот очищен')};""",
          """      b.querySelector('#psDel359').onclick=()=>{pubSnapClear();closeModal();toast('Снапшот очищен')};
      b.querySelector('#psDiffLocal').onclick=async()=>{
        const d=await pubSnapDiffLocal();
        b.querySelector('#psDiff').innerHTML=diffRenderHtml(d,'Снимок ↔ текущий канон');
        try{teleHit('pub:snapdiff')}catch(e){}
        try{audit('Снапшот-дифф (локально)',`ячеек: +${d?d.cellsAdd:0}/−${d?d.cellsDel:0}/±${d?d.cellsChg:0}`,'ops')}catch(e){}
      };
      b.querySelector('#psDiffSrv').onclick=async()=>{
        const r=await pubSnapDiffServer();
        b.querySelector('#psDiff').innerHTML=diffRenderHtml(r.diff||r,'Снимок ↔ канон сервера');
        try{teleHit('pub:snapdiff:srv')}catch(e){}
      };""", 'snap diff binds')
    c.rep("""    {ic:'📦',title:'Офлайн-снапшот канона: показать/выгрузить',hint:'синхронизация · 3.59',run:()=>openPubSnap()},""",
          """    {ic:'📦',title:'Офлайн-снапшот канона: показать/выгрузить',hint:'синхронизация · 3.59',run:()=>openPubSnap()},
    {ic:'🔍',title:'Снапшот-дифф: снимок против канона',hint:'синхронизация · 3.60',run:()=>openPubSnap()},""", 'palette 360')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.59 — роли бригад (бригадир) и офлайн-снапшот публикации</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.60 — снапшот-дифф канона</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>«🔍 Дифф с текущим»</b> в модалке снапшота: сравнение gzip-снимка (3.59) с текущим каноном рабочего места — добавленные/удалённые/изменённые ячейки плана по месяцам, изменения счётчиков справочников (штатка, причины, шаблоны, бригады, бюджеты, отпуска, обмены), counter канона «было → стало».</li>
        <li><b>«🌐 Дифф с сервером»</b>: то же против канона сервера ЛВС (<code>GET /api/v1/canon</code>, с токеном) — видно, ушёл ли сервер вперёд за время офлайна, прежде чем решать «публиковать force или сначала слить».</li>
        <li>Таблица месяцев и пиллы справочников рендерятся прямо в модалке; аудит «Снапшот-дифф (локально)», телеметрия <code>pub:snapdiff</code> / <code>pub:snapdiff:srv</code>; офлайн-ответы деградируют до понятной подсказки.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.59 — роли бригад (бригадир) и офлайн-снапшот публикации</div>""", 'help 360')
    c.rep("""    pubSnapKey,pubSnapSave,pubSnapLoad,pubSnapClear,pubSnapBadge,openPubSnap,""",
          """    pubSnapKey,pubSnapSave,pubSnapLoad,pubSnapClear,pubSnapBadge,openPubSnap,
    /* ===== 3.60: снапшот-дифф ===== */
    diffStates,pubSnapState,pubSnapDiffLocal,pubSnapDiffServer,diffRenderHtml,""", 'exports 360')

def V361(c):
    c.ver('3.61')
    c.rep("""    rows+=`<tr><td colspan="${DIM+3}" style="background:#eef1f7;font-weight:700">${esc(b.name)}${pat?` · шаблон «${esc(pat.name)}» (${esc(pat.seq)}) · смещение фазы ${fmtStd(b.offset||0,{unit:'дн'})} · якорь ${esc(b.anchor||'—')}`:''}</td></tr>`;""",
          """    rows+=`<tr><td colspan="${DIM+3}" style="background:#eef1f7;font-weight:700">${esc(b.name)}${pat?` · шаблон «${esc(pat.name)}» (${esc(pat.seq)}) · смещение фазы ${fmtStd(b.offset||0,{unit:'дн'})} · якорь ${esc(b.anchor||'—')}`:''}${brigLead(b)?` · бригадир: ${esc(empName(brigLead(b)))}`:''}</td></tr>`;   /* 3.61 */""", 'vedomost lead')
    c.rep("""          `SUMMARY:${esc(c)} · ${e.name} (${b.name})`,""",
          """          `SUMMARY:${esc(c)} · ${e.name}${brigRole(b,e.id)==='lead'?' (бригадир)':''} (${b.name})`,   /* 3.61: роль в календаре */""", 'ics lead')
    c.rep("""        <div class="hint" style="margin-top:0"><b>${esc(myBr.name)}</b> · шаблон «${esc(myPat.name)}» (${esc(myPat.seq)}) · смещение фазы ${fmtStd(myBr.offset||0,{unit:'дн'})} · якорь ${esc(myBr.anchor||'—')} · состав: ${fmtStd((myBr.members||[]).length,{unit:'чел'})}</div>""",
          """        <div class="hint" style="margin-top:0"><b>${esc(myBr.name)}</b> · шаблон «${esc(myPat.name)}» (${esc(myPat.seq)}) · смещение фазы ${fmtStd(myBr.offset||0,{unit:'дн'})} · якорь ${esc(myBr.anchor||'—')} · состав: ${fmtStd((myBr.members||[]).length,{unit:'чел'})}${(myBr.roles||{})[e.id]==='lead'?' <span class="pill g">вы — бригадир</span>':''}</div>""", 'me lead pill')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.60 — снапшот-дифф канона</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.61 — бригадир в печатных формах и календаре</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Бригадная ведомость</b> (печать): в шапке каждой бригады — «бригадир: ФИО» (роль 3.59).</li>
        <li><b>ICS-экспорт ротаций</b>: события бригадира получают суффикс «(бригадир)» в SUMMARY — календарь видит роль без открытия приложения.</li>
        <li><b>«Мой месяц → Моя бригада»</b>: пилл «вы — бригадир» для сотрудника с ролью lead.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.60 — снапшот-дифф канона</div>""", 'help 361')

def V362(c):
    c.ver('3.62')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_362 + '\n' + c.s[i:]
    c.rep("""      <div id="orderBox" class="hint"></div>
      <button class="btn small" id="btnOrderNew" style="margin-top:8px">📜 Открыть конструктор приказов</button>""",
          """      <div id="orderBox" class="hint"></div>
      <button class="btn small" id="btnOrderNew" style="margin-top:8px">📜 Открыть конструктор приказов</button>
      <div class="lbl" style="margin-top:12px">Реестр подписанных приказов<span class="sub">3.62 · SHA-256 текста · сверка подписи · выгрузка текста</span></div>
      <div id="ordersRegBox"></div>""", 'registry ui')
    c.rep("""  bindClick('btnOrderNew',()=>openOrderConstructor());   /* 3.44 */""",
          """  bindClick('btnOrderNew',()=>openOrderConstructor());   /* 3.44 */
  try{renderOrdersRegistry()}catch(e){}   /* 3.62 */""", 'registry render bind')
    c.rep("""    buttons:`<button class="btn ghost" data-coc>Закрыть</button><button class="btn ghost" id="ocSave">💾 Сохранить шаблон</button><button class="btn ghost" id="ocTxt">⤓ .txt</button><button class="btn" id="ocDocx">⤓ DOCX</button>`,""",
          """    buttons:`<button class="btn ghost" data-coc>Закрыть</button><button class="btn ghost" id="ocSave">💾 Сохранить шаблон</button><button class="btn ghost" id="ocSign" title="SHA-256 текста приказа и запись в реестр (3.62)">✍ Подписать в реестр</button><button class="btn ghost" id="ocTxt">⤓ .txt</button><button class="btn" id="ocDocx">⤓ DOCX</button>`,""", 'sign button')
    c.rep("""      b.querySelector('#ocTxt').onclick=()=>{""",
          """      b.querySelector('#ocSign').onclick=async()=>{
        const{tpl,ctx:cc}=ctx();
        const text=orderRender({body:b.querySelector('#ocBody').value},cc);
        await orderSign(text,cc.num,tpl.name);
      };
      b.querySelector('#ocTxt').onclick=()=>{""", 'sign bind')
    c.rep("""    {ic:'🔍',title:'Снапшот-дифф: снимок против канона',hint:'синхронизация · 3.60',run:()=>openPubSnap()},""",
          """    {ic:'🔍',title:'Снапшот-дифф: снимок против канона',hint:'синхронизация · 3.60',run:()=>openPubSnap()},
    {ic:'✍',title:'Реестр подписанных приказов',hint:'отчёты · 3.62',run:()=>{showTab('rep');setTimeout(()=>{const c=$('ordersRegBox');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'});renderOrdersRegistry()},300)}},""", 'palette 362')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.61 — бригадир в печатных формах и календаре</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.62 — подписи приказов и реестр</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Подпись приказа</b>: «✍ Подписать в реестр» в конструкторе — SHA-256 текста приказа (фолбэк FNV без crypto.subtle) пишется в реестр канона (<code>state.orders</code>: номер, шаблон, дата, автор, текст, hash, статус); до 100 записей.</li>
        <li><b>Реестр в «Отчётах»</b>: список подписанных приказов с обрезанным хешем, «✔ сверить» (пересчёт SHA-256 текста: корректна / не сходится — с аудитом обоих исходов) и «⤓ текст» (выгрузка подписанного текста); аудит «Приказ подписан в реестр», телеметрия <code>order:sign</code>.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.61 — бригадир в печатных формах и календаре</div>""", 'help 362')
    c.rep("""    brigRole,brigLead,brigSetRole,openBrigRolePicker,""",
          """    brigRole,brigLead,brigSetRole,openBrigRolePicker,
    /* ===== 3.62: подписи приказов ===== */
    ordersReg,sha359,orderSign,orderVerify,renderOrdersRegistry,""", 'exports 362')

SPECS = [('3.60', V360), ('3.61', V361), ('3.62', V362)]

class Ctx:
    def __init__(self, s): self.s = s
    def rep(self, old, new, label):
        n = self.s.count(old)
        if n != 1: raise SystemExit('ANCHOR FAIL [%s]: %d' % (label, n))
        self.s = self.s.replace(old, new, 1)
    def ver(self, v):
        prev = '%.2f' % (float(v) - 0.01)
        self.rep('<title>План-табель служебной деятельности · WFM %s</title>' % prev,
                 '<title>План-табель служебной деятельности · WFM %s</title>' % v, 'title ' + v)
        self.rep("geoPrev,ver:'%s'," % prev, "geoPrev,ver:'%s'," % v, 'ver ' + v)
        self.rep("const ver=(window.APP&&APP.ver)||'%s';" % prev,
                 "const ver=(window.APP&&APP.ver)||'%s';" % v, 'ver fallback ' + v)

def main():
    chain = [('План-табель-WFM-3.59.html', 'План-табель-WFM-3.60.html'),
             ('План-табель-WFM-3.60.html', 'План-табель-WFM-3.61.html'),
             ('План-табель-WFM-3.61.html', 'План-табель-WFM-3.62.html'),
             ('План-табель-WFM-3.59-offline.html', 'План-табель-WFM-3.60-offline.html'),
             ('План-табель-WFM-3.60-offline.html', 'План-табель-WFM-3.61-offline.html'),
             ('План-табель-WFM-3.61-offline.html', 'План-табель-WFM-3.62-offline.html')]
    fns = [V360, V361, V362]
    for (src, dst), fn in zip(chain[:3], fns):
        s = io.open(os.path.join(HERE, src), encoding='utf-8').read()
        c = Ctx(s); fn(c)
        io.open(os.path.join(HERE, dst), 'w', encoding='utf-8').write(c.s)
        print('OK %s -> %s (+%d)' % (src, dst, len(c.s) - len(s)))
    for (src, dst), fn in zip(chain[3:], fns):
        s = io.open(os.path.join(HERE, src), encoding='utf-8').read()
        c = Ctx(s); fn(c)
        io.open(os.path.join(HERE, dst), 'w', encoding='utf-8').write(c.s)
        print('OK %s -> %s (+%d)' % (src, dst, len(c.s) - len(s)))

if __name__ == '__main__':
    main()
