#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.56: серверный скан покрытия — GET /api/v1/coverage?y=&m=&dept=&need=&mode="""
import io, sys
p = sys.argv[1] if len(sys.argv) > 1 else 'server/sync-server.mjs'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL [%s]: %d' % (label, n))
    s = s.replace(old, new, 1)

rep("  /* ===== 3.49: серверный контур бригад ротаций ===== */",
    "  /* ===== 3.56: серверный скан покрытия по канону ===== */\n"
    "  if(p==='/api/v1/coverage'&&req.method==='GET'){\n"
    "    const st=canonDecode(CANON);\n"
    "    if(!st)return sendJ(409,{err:'на сервере нет канона — сначала полная публикация'});\n"
    "    const y=+(u.searchParams.get('y')||0),m=+(u.searchParams.get('m')||0);\n"
    "    if(!y||!m||m<1||m>12)return sendJ(400,{err:'ожидается ?y=YYYY&m=M'});\n"
    "    const deptId=String(u.searchParams.get('dept')||'');\n"
    "    const mode=u.searchParams.get('mode')==='work'?'work':'duty';\n"
    "    const dp=(st.departments||[]).find(x=>x.id===deptId)||null;\n"
    "    let need=+(u.searchParams.get('need')||0);\n"
    "    if(!need&&dp)need=dp.minDuty||0;\n"
    "    const es=(st.employees||[]).filter(e=>!e.fired&&(!deptId||e.deptId===deptId));\n"
    "    const mk3=`${y}-${String(m).padStart(2,'0')}`,DIM=new Date(y,m,0).getDate();\n"
    "    const pm=st.plan&&st.plan[mk3]||{};\n"
    "    const reasons=st.reasons||[];\n"
    "    const days=[];let defDays=0,worst=0;\n"
    "    for(let d=1;d<=DIM;d++){\n"
    "      let plan=0;\n"
    "      es.forEach(e=>{\n"
    "        const raw=pm[e.id]&&pm[e.id][d];if(!raw)return;\n"
    "        const code=String(raw).split('/')[0];\n"
    "        const r=reasons.find(x=>x.code===code);\n"
    "        if(!r)return;\n"
    "        const hit=mode==='duty'?r.cat==='duty':(r.coeff>0&&r.cat!=='off');\n"
    "        if(hit)plan++;\n"
    "      });\n"
    "      const deficit=Math.max(0,need-plan);\n"
    "      if(deficit>0){defDays++;worst=Math.max(worst,deficit)}\n"
    "      days.push({d,plan,need,deficit});\n"
    "    }\n"
    "    return sendJ(200,{ok:1,y,m,dept:deptId,need,mode,days,defDays,worst,counter:CANON?CANON.counter:0,ts:now()});\n"
    "  }\n"
    "  /* ===== 3.49: серверный контур бригад ротаций ===== */", 'coverage route')

rep("   бюджеты 3.53: GET/PUT /api/v1/budgets (лимита ФОТ, файл ${path.basename(BUDG_FILE)})`);",
    "   бюджеты 3.53: GET/PUT /api/v1/budgets (лимита ФОТ, файл ${path.basename(BUDG_FILE)})`);\n"
    "  console.log(`   покрытие 3.56: GET /api/v1/coverage?y=&m=&dept=&need=&mode= (скан по канону сервера)`);", 'coverage boot log')
io.open(p, 'w', encoding='utf-8').write(s)
print('server 3.56 patched')
