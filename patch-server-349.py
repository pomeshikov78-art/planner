#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.49: серверный контур бригад — GET/PUT /api/v1/brigades (файл PT_BRIG_FILE,
права staff/admin, аудит, WS-трансляция {type:'brigades'}, merge по id/ts)."""
import io, sys
p = sys.argv[1] if len(sys.argv) > 1 else 'server/sync-server.mjs'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL [%s]: %d' % (label, n))
    s = s.replace(old, new, 1)

rep("     PT_MAP_FILE=plan-tabel-xchg-map.json 3.35: справочник сопоставления кодов Т-13 ↔ причины",
    "     PT_MAP_FILE=plan-tabel-xchg-map.json 3.35: справочник сопоставления кодов Т-13 ↔ причины\n"
    "     PT_BRIG_FILE=plan-tabel-brigades.json 3.49: общий справочник бригад ротаций", 'env doc')

rep("const persistXmap=()=>save(MAP_FILE,XMAP).catch(()=>{});",
    "const persistXmap=()=>save(MAP_FILE,XMAP).catch(()=>{});\n"
    "/* ===== 3.49: общий справочник бригад ротаций (GET/PUT /api/v1/brigades) ===== */\n"
    "const BRIG_FILE=path.resolve(E('PT_BRIG_FILE')||path.join(__dirname,'plan-tabel-brigades.json'));\n"
    "let BRIG=await j(BRIG_FILE,{items:[],ts:0,by:''});\n"
    "if(!BRIG||!Array.isArray(BRIG.items))BRIG={items:[],ts:0,by:''};\n"
    "const persistBrig=()=>save(BRIG_FILE,BRIG).catch(()=>{});", 'brig state')

rep("  return sendJ(404,{err:'неизвестный метод API; см. README: /api/v1 login|canon|push|ops|sigs|signal|users|tabel|skud|ocr|xchg/map|xchg/log|xchg/retry'});",
    "  /* ===== 3.49: серверный контур бригад ротаций ===== */\n"
    "  if(p==='/api/v1/brigades'&&req.method==='GET'){\n"
    "    return sendJ(200,{ok:1,items:BRIG.items,ts:BRIG.ts||0,by:BRIG.by||'',total:BRIG.items.length});\n"
    "  }\n"
    "  if(p==='/api/v1/brigades'&&(req.method==='PUT'||req.method==='POST')){\n"
    "    if(USERS&&!can(AU,'staff')&&!can(AU,'admin'))return sendJ(403,{err:'нужны права ведения справочников (staff) или администратора'});\n"
    "    if(!Array.isArray(m.items))return sendJ(400,{err:'ожидается {items:[{id,name,patId,anchor,offset,members,ts?}]}'});\n"
    "    if(m.items.length>200)return sendJ(400,{err:'слишком много бригад (максимум 200)'});\n"
    "    const errors=[];const byId={};BRIG.items.forEach(it=>byId[it.id]=it);\n"
    "    let touched=0;\n"
    "    m.items.forEach(it=>{\n"
    "      const id=String(it.id||'').slice(0,40);\n"
    "      if(!id){errors.push({err:'пустой id бригады'});return}\n"
    "      const rec={id,\n"
    "        name:String(it.name||'').slice(0,80)||('бригада '+id),\n"
    "        patId:String(it.patId||'').slice(0,40),\n"
    "        anchor:String(it.anchor||'').slice(0,10),\n"
    "        offset:Math.max(0,Math.min(60,Math.round(+it.offset||0))),\n"
    "        members:Array.isArray(it.members)?it.members.slice(0,200).map(x=>String(x).slice(0,40)):[],\n"
    "        ts:+it.ts||now()};\n"
    "      const ex=byId[id];\n"
    "      if(ex&&(ex.ts||0)>rec.ts)return;   /* last-write-wins по ts */\n"
    "      byId[id]=rec;touched++;\n"
    "    });\n"
    "    if(errors.length)return sendJ(400,{ok:0,errors});\n"
    "    BRIG={items:Object.values(byId),ts:now(),by:AU.login||'api'};\n"
    "    await persistBrig();\n"
    "    broadcast({type:'brigades',ts:BRIG.ts,by:BRIG.by,total:BRIG.items.length});\n"
    "    await audit('brigades','справочник бригад: сохранено/обновлено '+touched+' из '+BRIG.items.length,{login:AU.login});\n"
    "    return sendJ(200,{ok:1,saved:touched,total:BRIG.items.length,ts:BRIG.ts,by:BRIG.by});\n"
    "  }\n"
    "  return sendJ(404,{err:'неизвестный метод API; см. README: /api/v1 login|canon|push|ops|sigs|signal|users|tabel|skud|ocr|xchg/map|xchg/log|xchg/retry|brigades'});", 'brig routes')

rep("   обмен 3.35: /api/v1/xchg/map (сопоставление кодов Т-13), /api/v1/xchg/log (журнал выгрузок/импортов), /api/v1/xchg/retry (повтор)`);",
    "   обмен 3.35: /api/v1/xchg/map (сопоставление кодов Т-13), /api/v1/xchg/log (журнал выгрузок/импортов), /api/v1/xchg/retry (повтор)`);\n"
    "  console.log(`   бригады 3.49: GET/PUT /api/v1/brigades (общий справочник бригад, файл ${path.basename(BRIG_FILE)})`);", 'boot log')

io.open(p, 'w', encoding='utf-8').write(s)
print('server patched: %d bytes' % len(s))
