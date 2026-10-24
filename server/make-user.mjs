#!/usr/bin/env node
/* Создание/обновление пользователя офлайн-аутентификации WFM.
   Использование:
     node server/make-user.mjs <login> <pin> <role> [users.json] [emp] [--allow=a,b] [--deny=c,d] [--mods=m1,m2] [--block]
   Роли: admin | hr | editor | tab | viewer
   PIN хранится как SHA-256 хэш ('s2$…') — тот же формат, что проверяет сервер и клиент.
   Формат файла: {"users":[{login,pinHash,role,emp,allow,deny,modsOff,blocked}]} */
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';

const args=process.argv.slice(2);
if(args.length<3){
  console.log('Использование: node server/make-user.mjs <login> <pin> <role> [users.json] [emp] [--allow=a,b] [--deny=c,d] [--mods=m1,m2] [--block]');
  process.exit(1);
}
const login=args[0],pin=args[1],role=args[2];
const ROLES=['admin','hr','editor','tab','viewer'];
if(!ROLES.includes(role)){console.error('Роль должна быть одной из: '+ROLES.join(', '));process.exit(1)}
let file='users.json',emp=null;
const flags={};
{
  const rest=args.slice(3);
  const pos=[];
  for(const a of rest){
    if(a.startsWith('--')){const eq=a.indexOf('=');const k=a.slice(2,eq<0?a.length:eq);flags[k]=eq<0?'1':a.slice(eq+1)}
    else pos.push(a);
  }
  if(pos[0]&&pos[0].endsWith('.json')){file=pos[0];emp=pos[1]||null}
  else if(pos[0]){emp=pos[0];if(pos[1]&&pos[1].endsWith('.json'))file=pos[1]}
}

const pinHash='s2$'+createHash('sha256').update('planTabel$'+pin).digest('hex');
let data={users:[]};
try{data=JSON.parse(readFileSync(file,'utf8'));if(Array.isArray(data))data={users:data}}catch(e){}
if(!Array.isArray(data.users))data.users=[];
const rec={login,pinHash,role,
  emp:flags.emp!==undefined?flags.emp:emp,
  allow:flags.allow?String(flags.allow).split(',').filter(Boolean):[],
  deny:flags.deny?String(flags.deny).split(',').filter(Boolean):[],
  modsOff:flags.mods?String(flags.mods).split(',').filter(Boolean):[],
  blocked:!!flags.block};
const i=data.users.findIndex(u=>u.login===login);
if(i>=0){
  const oldPin=data.users[i].pinHash;
  data.users[i]={...data.users[i],...rec,pinHash:pin==='-'?oldPin:pinHash};
  console.log('Обновлён пользователь:',login,'→ роль',role);
}else{
  data.users.push(rec);
  console.log('Добавлен пользователь:',login,'· роль',role,rec.emp?'· emp '+rec.emp:'');
}
writeFileSync(path.resolve(file),JSON.stringify(data,null,1));
console.log('Файл:',path.resolve(file),'· запуск сервера: PT_USERS_FILE='+path.resolve(file)+' node server/sync-server.mjs');
