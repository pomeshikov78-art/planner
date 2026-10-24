#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.53: серверный контур бюджетов — GET/PUT /api/v1/budgets (PT_BUDGET_FILE,
права staff/admin/budget, merge по месяцам с last-write-wins по ts, аудит, WS)."""
import io, sys
p = sys.argv[1] if len(sys.argv) > 1 else 'server/sync-server.mjs'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL [%s]: %d' % (label, n))
    s = s.replace(old, new, 1)

rep("const persistBrig=()=>save(BRIG_FILE,BRIG).catch(()=>{});",
    "const persistBrig=()=>save(BRIG_FILE,BRIG).catch(()=>{});\n"
    "/* ===== 3.53: общий справочник лимитов ФОТ (GET/PUT /api/v1/budgets) ===== */\n"
    "const BUDG_FILE=path.resolve(E('PT_BUDGET_FILE')||path.join(__dirname,'plan-tabel-budgets.json'));\n"
    "let BUDG=await j(BUDG_FILE,{items:{},ts:0,by:''});\n"
    "if(!BUDG||typeof BUDG.items!=='object'||Array.isArray(BUDG.items))BUDG={items:{},ts:0,by:''};\n"
    "const persistBudg=()=>save(BUDG_FILE,BUDG).catch(()=>{});", 'budg state')

rep("    return sendJ(200,{ok:1,saved:touched,total:BRIG.items.length,ts:BRIG.ts,by:BRIG.by});\n  }",
    "    return sendJ(200,{ok:1,saved:touched,total:BRIG.items.length,ts:BRIG.ts,by:BRIG.by});\n  }\n"
    "  /* ===== 3.53: лимиты ФОТ по подразделениям и месяцам ===== */\n"
    "  if(p==='/api/v1/budgets'&&req.method==='GET'){\n"
    "    return sendJ(200,{ok:1,items:BUDG.items,ts:BUDG.ts||0,by:BUDG.by||'',total:Object.keys(BUDG.items).length});\n"
    "  }\n"
    "  if(p==='/api/v1/budgets'&&(req.method==='PUT'||req.method==='POST')){\n"
    "    if(USERS&&!can(AU,'staff')&&!can(AU,'admin')&&!can(AU,'budget'))return sendJ(403,{err:'нужны права staff, admin или budget'});\n"
    "    if(!m.items||typeof m.items!=='object'||Array.isArray(m.items))return sendJ(400,{err:'ожидается {items:{\"YYYY-MM\":{deptId:лимит|null}}}'});\n"
    "    const mks=Object.keys(m.items);\n"
    "    if(mks.length>240)return sendJ(400,{err:'слишком много месяцев (максимум 240)'});\n"
    "    const errors=[];let touched=0;\n"
    "    mks.forEach(mk=>{\n"
    "      if(!/^\\d{4}-\\d{2}$/.test(mk)){errors.push({mk,err:'формат месяца YYYY-MM'});return}\n"
    "      const lim=m.items[mk];\n"
    "      if(!lim||typeof lim!=='object'||Array.isArray(lim)){errors.push({mk,err:'ожидается объект лимитов по подразделениям'});return}\n"
    "      const deps=Object.keys(lim);\n"
    "      if(deps.length>100){errors.push({mk,err:'слишком много подразделений (максимум 100)'});return}\n"
    "      const rec={limits:{},ts:+lim.ts||now(),by:AU.login||'api'};\n"
    "      deps.forEach(did=>{\n"
    "        if(did==='ts'||did==='by')return;\n"
    "        const v=lim[did];\n"
    "        if(v!==null&&(typeof v!=='number'||!isFinite(v)||v<0)){errors.push({mk,dept:did,err:'лимит — число ≥ 0 или null'});return}\n"
    "        rec.limits[String(did).slice(0,40)]=v;\n"
    "      });\n"
    "      const ex=BUDG.items[mk];\n"
    "      if(ex&&(ex.ts||0)>rec.ts)return;   /* last-write-wins по ts месяца */\n"
    "      BUDG.items[mk]=rec;touched++;\n"
    "    });\n"
    "    if(errors.length)return sendJ(400,{ok:0,errors});\n"
    "    BUDG.ts=now();BUDG.by=AU.login||'api';\n"
    "    await persistBudg();\n"
    "    broadcast({type:'budgets',ts:BUDG.ts,by:BUDG.by,total:Object.keys(BUDG.items).length});\n"
    "    await audit('budgets','лимита ФОТ: месяцев обновлено '+touched+' из '+Object.keys(BUDG.items).length,{login:AU.login});\n"
    "    return sendJ(200,{ok:1,saved:touched,total:Object.keys(BUDG.items).length,ts:BUDG.ts,by:BUDG.by});\n"
    "  }", 'budg routes')

rep("   бригады 3.49: GET/PUT /api/v1/brigades (общий справочник бригад, файл ${path.basename(BRIG_FILE)})`);",
    "   бригады 3.49: GET/PUT /api/v1/brigades (общий справочник бригад, файл ${path.basename(BRIG_FILE)})`);\n"
    "  console.log(`   бюджеты 3.53: GET/PUT /api/v1/budgets (лимита ФОТ, файл ${path.basename(BUDG_FILE)})`);", 'budg boot log')
io.open(p, 'w', encoding='utf-8').write(s)
print('server 3.53 patched')
