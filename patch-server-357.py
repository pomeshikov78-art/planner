#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.57: cron-дайджест получает секцию дефицитов покрытия на 7 дней."""
import io, sys
p = sys.argv[1] if len(sys.argv) > 1 else 'server/sync-server.mjs'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL [%s]: %d' % (label, n))
    s = s.replace(old, new, 1)

rep("""  const vacRev=st&&Array.isArray(st.vac)?st.vac.filter(r=>r.status==='review').length:0;""",
    """  /* 3.57: дефициты покрытия на ближайшие 7 дней по канону сервера */
  let covTxt=' Покрытие: дефицитов нет.';
  if(st&&st.departments&&st.reasons&&st.plan){
    const defs=[];
    st.departments.filter(dp=>(dp.minDuty||0)>0).forEach(dp=>{
      const es=(st.employees||[]).filter(e=>!e.fired&&e.deptId===dp.id);
      let bad=0;
      for(let i2=0;i2<7;i2++){
        const dd2=new Date(d.getTime()+i2*864e5);
        const mk3=`${dd2.getFullYear()}-${String(dd2.getMonth()+1).padStart(2,'0')}`;
        let plan=0;
        es.forEach(e=>{
          const row=st.plan[mk3]&&st.plan[mk3][e.id];
          const code=row?String(row[dd2.getDate()]||'').split('/')[0]:'';
          const r=st.reasons.find(x=>x.code===code);
          if(r&&r.cat==='duty')plan++;
        });
        if(plan<dp.minDuty)bad++;
      }
      if(bad)defs.push(dp.name+': '+bad+' дн.');
    });
    if(defs.length)covTxt=' Дефициты покрытия 7 дней: '+defs.join('; ')+'.';
  }
  const vacRev=st&&Array.isArray(st.vac)?st.vac.filter(r=>r.status==='review').length:0;""", 'digest coverage')

rep("""клиентов ${WSS.clients.size}.`;""",
    """клиентов ${WSS.clients.size}.${covTxt}`;""", 'digest text')
io.open(p, 'w', encoding='utf-8').write(s)
print('server 3.57 patched')
