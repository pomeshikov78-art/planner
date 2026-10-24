#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.55: серверный контур — роль бригад (perm brig) и часовые квоты PUT бригад
(PT_BRIG_QUOTA='editor:60,tab:120'; 429 при исчерпании, аудит brig-quota)."""
import io, sys
p = sys.argv[1] if len(sys.argv) > 1 else 'server/sync-server.mjs'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL [%s]: %d' % (label, n))
    s = s.replace(old, new, 1)

rep("""const ROLE_PERM={
  admin:{admin:1,edit:1,staff:1,import:1,sign:1,chat:1},
  hr:{edit:1,staff:1,import:1,sign:1,chat:1},
  editor:{edit:1,sign:1,chat:1},
  tab:{edit:1,planOnly:1,chat:1},
  viewer:{chat:0}
};""",
"""const ROLE_PERM={
  admin:{admin:1,edit:1,staff:1,import:1,sign:1,chat:1,brig:1,budget:1},
  hr:{edit:1,staff:1,import:1,sign:1,chat:1,brig:1,budget:1},
  editor:{edit:1,sign:1,chat:1,brig:1},
  tab:{edit:1,planOnly:1,chat:1,brig:1},
  viewer:{chat:0}
};""", 'role perm brig/budget')

rep("(E('PT_QUOTA')||'').split(',').forEach(p=>{const[k,v]=p.split(':');if(k&&+v>0)QUOTAS[k.trim()]=+v});",
    "(E('PT_QUOTA')||'').split(',').forEach(p=>{const[k,v]=p.split(':');if(k&&+v>0)QUOTAS[k.trim()]=+v});\n"
    "/* ===== 3.55: часовые квоты PUT /api/v1/brigades по ролям ===== */\n"
    "const BRIG_QUOTAS={};\n"
    "(E('PT_BRIG_QUOTA')||'').split(',').forEach(p=>{const[k,v]=p.split(':');if(k&&+v>0)BRIG_QUOTAS[k.trim()]=+v});\n"
    "const BRIG_QUOTA_USED={};\n"
    "const brigHourKey=()=>Math.floor(now()/3600000);\n"
    "function brigQuotaLeft(role){\n"
    "  const q=BRIG_QUOTAS[role||''];if(!q)return Infinity;\n"
    "  const used=BRIG_QUOTA_USED[(role||'')+':'+brigHourKey()]||0;\n"
    "  return Math.max(0,q-used);\n"
    "}\n"
    "function brigQuotaUse(role){BRIG_QUOTA_USED[(role||'')+':'+brigHourKey()]=(BRIG_QUOTA_USED[(role||'')+':'+brigHourKey()]||0)+1}", 'brig quota fns')

rep("    if(USERS&&!can(AU,'staff')&&!can(AU,'admin'))return sendJ(403,{err:'нужны права ведения справочников (staff) или администратора'});\n    if(!Array.isArray(m.items))return sendJ(400,{err:'ожидается {items:[{id,name,patId,anchor,offset,members,ts?}]}'});",
    "    if(USERS&&!can(AU,'staff')&&!can(AU,'admin')&&!can(AU,'brig'))return sendJ(403,{err:'нужны права brig, staff или администратора'});\n"
    "    if(brigQuotaLeft(AU.role||'anon')===0){\n"
    "      await audit('brig-quota','превышена часовая квота PUT бригад для роли '+(AU.role||'anon'),{login:AU.login});\n"
    "      return sendJ(429,{err:'часовая квота PUT бригад исчерпана',retryAfterMin:60-new Date().getMinutes()});\n"
    "    }\n"
    "    if(!Array.isArray(m.items))return sendJ(400,{err:'ожидается {items:[{id,name,patId,anchor,offset,members,ts?}]}'});", 'brig quota gate')

rep("    BRIG={items:Object.values(byId),ts:now(),by:AU.login||'api'};\n    await persistBrig();",
    "    brigQuotaUse(AU.role||'anon');\n    BRIG={items:Object.values(byId),ts:now(),by:AU.login||'api'};\n    await persistBrig();", 'brig quota use')

rep("    return sendJ(200,{ok:1,saved:touched,total:BRIG.items.length,ts:BRIG.ts,by:BRIG.by});",
    "    return sendJ(200,{ok:1,saved:touched,total:BRIG.items.length,ts:BRIG.ts,by:BRIG.by,quotaLeft:brigQuotaLeft(AU.role||'anon')===Infinity?null:brigQuotaLeft(AU.role||'anon')});", 'brig quota left in response')

rep("     PT_BRIG_FILE=plan-tabel-brigades.json 3.49: общий справочник бригад ротаций",
    "     PT_BRIG_FILE=plan-tabel-brigades.json 3.49: общий справочник бригад ротаций\n"
    "     PT_BRIG_QUOTA='editor:60,tab:120'        3.55: часовые квоты PUT /api/v1/brigades по ролям\n"
    "     PT_BUDGET_FILE=plan-tabel-budgets.json 3.53: общий справочник лимитов ФОТ", 'env doc 355')
io.open(p, 'w', encoding='utf-8').write(s)
print('server 3.55 patched')
