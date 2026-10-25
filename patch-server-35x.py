#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.53: GET/PUT /api/v1/budgets; 3.55: roles в бригадах + квота PT_BRIG_QUOTA (429)."""
import io, sys
p = sys.argv[1] if len(sys.argv) > 1 else 'server/sync-server.mjs'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL [%s]: %d' % (label, n))
    s = s.replace(old, new, 1)

# ---- 3.53 budgets state ----
rep("const persistBrig=()=>save(BRIG_FILE,BRIG).catch(()=>{});",
    "const persistBrig=()=>save(BRIG_FILE,BRIG).catch(()=>{});\n"
    "/* ===== 3.53: общий справочник лимитов ФОТ (GET/PUT /api/v1/budgets) ===== */\n"
    "const BUD_FILE=path.resolve(E('PT_BUD_FILE')||path.join(__dirname,'plan-tabel-budgets.json'));\n"
    "let BUD=await j(BUD_FILE,{items:{},ts:0,by:''});\n"
    "if(!BUD||typeof BUD.items!=='object'||Array.isArray(BUD.items))BUD={items:{},ts:0,by:''};\n"
    "const persistBud=()=>save(BUD_FILE,BUD).catch(()=>{});\n"
    "/* ===== 3.55: часовая квота PUT /api/v1/brigades ===== */\n"
    "const BRIG_QUOTA=+(E('PT_BRIG_QUOTA')||60);\n"
    "let BRIG_Q={};", 'bud state')

# ---- 3.55 roles validation in brigades PUT ----
rep("        members:Array.isArray(it.members)?it.members.slice(0,200).map(x=>String(x).slice(0,40)):[],\n"
    "        ts:+it.ts||now()};",
    "        members:Array.isArray(it.members)?it.members.slice(0,200).map(x=>String(x).slice(0,40)):[],\n"
    "        ts:+it.ts||now()};\n"
    "      /* 3.55: роли — только участники бригады, значения lead|member */\n"
    "      const roles={};\n"
    "      if(it.roles&&typeof it.roles==='object')Object.entries(it.roles).slice(0,200).forEach(([eid,rl])=>{\n"
    "        if(rec.members.includes(String(eid))&&(rl==='lead'||rl==='member'))roles[String(eid)]=rl});\n"
    "      let leads=Object.keys(roles).filter(x=>roles[x]==='lead');\n"
    "      leads.slice(1).forEach(x=>{roles[x]='member'});   /* бригадир один */\n"
    "      rec.roles=roles;", 'roles validation')

# ---- 3.55 quota check at top of brigades PUT ----
rep("  if(p==='/api/v1/brigades'&&(req.method==='PUT'||req.method==='POST')){\n"
    "    if(USERS&&!can(AU,'staff')&&!can(AU,'admin'))return sendJ(403,{err:'нужны права ведения справочников (staff) или администратора'});",
    "  if(p==='/api/v1/brigades'&&(req.method==='PUT'||req.method==='POST')){\n"
    "    if(USERS&&!can(AU,'staff')&&!can(AU,'admin'))return sendJ(403,{err:'нужны права ведения справочников (staff) или администратора'});\n"
    "    /* 3.55: часовая квота обновлений справочника бригад */\n"
    "    const qk=AU.login||'api',qh=Math.floor(now()/3600000),qe=BRIG_Q[qk];\n"
    "    if(qe&&qe.h===qh&&qe.n>=BRIG_QUOTA){\n"
    "      await audit('brig-quota','превышена квота PUT /api/v1/brigades: '+BRIG_QUOTA+'/час ('+qk+')',{login:qk});\n"
    "      return sendJ(429,{err:'квота обновлений бригад превышена ('+BRIG_QUOTA+'/час)',retryAfter:(qh+1)*3600000-now()});\n"
    "    }", 'brig quota')
rep("    BRIG={items:Object.values(byId),ts:now(),by:AU.login||'api'};\n"
    "    await persistBrig();",
    "    BRIG_Q[qk]={h:qh,n:(qe&&qe.h===qh?qe.n:0)+1};\n"
    "    BRIG={items:Object.values(byId),ts:now(),by:AU.login||'api'};\n"
    "    await persistBrig();", 'brig quota count')

# ---- 3.53 budgets routes (перед 404) ----
rep("  return sendJ(404,{err:'неизвестный метод API; см. README: /api/v1 login|canon|push|ops|sigs|signal|users|tabel|skud|ocr|xchg/map|xchg/log|xchg/retry|brigades'});",
    "  /* ===== 3.53: серверный справочник лимитов ФОТ ===== */\n"
    "  if(p==='/api/v1/budgets'&&req.method==='GET'){\n"
    "    return sendJ(200,{ok:1,items:BUD.items,ts:BUD.ts||0,by:BUD.by||'',months:Object.keys(BUD.items).length});\n"
    "  }\n"
    "  if(p==='/api/v1/budgets'&&(req.method==='PUT'||req.method==='POST')){\n"
    "    if(USERS&&!can(AU,'staff')&&!can(AU,'admin'))return sendJ(403,{err:'нужны права ведения справочников (staff) или администратора'});\n"
    "    if(!m.items||typeof m.items!=='object'||Array.isArray(m.items))return sendJ(400,{err:'ожидается {items:{\"YYYY-MM\":{deptId:limit}} , ts?}'});\n"
    "    const ts=+m.ts||now();\n"
    "    if(ts<(BUD.ts||0))return sendJ(200,{ok:1,skipped:1,ts:BUD.ts,by:BUD.by,months:Object.keys(BUD.items).length});\n"
    "    const clean={};let months=0;\n"
    "    Object.entries(m.items).slice(0,240).forEach(([mk,vals])=>{\n"
    "      if(!/^\\d{4}-\\d{2}$/.test(String(mk)))return;\n"
    "      const row={};\n"
    "      Object.entries(vals||{}).slice(0,200).forEach(([dp,v])=>{\n"
    "        const n=Math.round(+v);\n"
    "        if(isFinite(n)&&n>=0)row[String(dp).slice(0,40)]=n;\n"
    "      });\n"
    "      if(Object.keys(row).length){clean[mk]=row;months++}\n"
    "    });\n"
    "    BUD={items:clean,ts:now(),by:AU.login||'api'};\n"
    "    await persistBud();\n"
    "    broadcast({type:'budgets',ts:BUD.ts,by:BUD.by,months});\n"
    "    await audit('budgets','справочник лимитов ФОТ: месяцев '+months,{login:AU.login});\n"
    "    return sendJ(200,{ok:1,saved:months,months,ts:BUD.ts,by:BUD.by});\n"
    "  }\n"
    "  return sendJ(404,{err:'неизвестный метод API; см. README: /api/v1 login|canon|push|ops|sigs|signal|users|tabel|skud|ocr|xchg/map|xchg/log|xchg/retry|brigades|budgets'});", 'bud routes')

rep("   бригады 3.49: GET/PUT /api/v1/brigades (общий справочник бригад, файл ${path.basename(BRIG_FILE)})`);",
    "   бригады 3.49: GET/PUT /api/v1/brigades (общий справочник бригад, файл ${path.basename(BRIG_FILE)}); роли и квота PT_BRIG_QUOTA 3.55`);\n"
    "  console.log(`   бюджеты 3.53: GET/PUT /api/v1/budgets (лимита ФОТ, файл ${path.basename(BUD_FILE)})`);", 'boot log 35x')

io.open(p, 'w', encoding='utf-8').write(s)
print('server patched 3.53/3.55: %d bytes' % len(s))
