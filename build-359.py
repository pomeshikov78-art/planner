#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.59 «Роли бригад (бригадир) и офлайн-снапшот отложенной публикации».
Надстройка над канонической цепочкой main (3.58): клиент 3.58→3.59,
офлайн 3.58→3.59, сервер: валидация roles в PUT /api/v1/brigades."""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

MODULE_359 = r"""/* ================= 3.59: РОЛИ БРИГАД (БРИГАДИР) И ОФЛАЙН-СНАПШОТ ПУБЛИКАЦИИ =================
   1) Роли внутри бригады: b.roles {eid:'lead'|'member'}; бригадир уникален; «★» в
      карточке бригад открывает пикер; роль уходит на сервер в составе справочника,
      сервер отбрасывает ключи вне members и лишних lead.
   2) Офлайн-снапшот канона: при отложенной полной публикации (флаг 3.54) дополнительно
      сохраняется gzip-снимок канона (pt.pub.snap) — страховка от потери устройства до
      реконнекта; при реконнекте снимок сверяется (audit) и очищается после доставки. */
function brigRole(b,eid){return (b&&b.roles&&b.roles[eid])||'member'}
function brigLead(b){
  if(!b||!b.roles)return null;
  return Object.keys(b.roles).find(x=>b.roles[x]==='lead')||null;
}
function brigSetRole(brigId,eid,role){
  const b=brigadeList().find(x=>x.id===brigId);
  if(!b)return;
  b.roles=b.roles||{};
  if(!role||role==='member')delete b.roles[eid];
  else{
    b.roles[eid]=role;
    if(role==='lead')Object.keys(b.roles).forEach(id=>{if(id!==eid&&b.roles[id]==='lead')delete b.roles[id]});
  }
  b.ts=Date.now();
  save(true);
  try{renderBrigades()}catch(e){}
  audit('Роль в бригаде',`${b.name}: ${empName(eid)} → ${role==='lead'?'бригадир':'член бригады'}`,'brigades');
  try{teleHit('brig:role')}catch(e){}
}
function openBrigRolePicker(brigId){
  const b=brigadeList().find(x=>x.id===brigId);
  if(!b){toast('Бригада не найдена','err');return}
  const members=(b.members||[]).map(id=>emp(id)).filter(e=>e);
  if(!members.length){toast('В бригаде нет сотрудников','err');return}
  try{teleHit('brig:roleui')}catch(e){}
  openModal({title:'★ Роли бригады «'+esc(b.name)+'»',body:`
    <div class="hint" style="margin-top:0">Бригадир — один: отметка звёздочкой. Роль видна в карточке бригад, ведомости и ICS-сводках; сервер принимает роли только для участников бригады.</div>
    ${members.map(e=>`<label class="chkrow" style="padding:4px 0"><input type="radio" name="brl359" value="${e.id}" ${brigLead(b)===e.id?'checked':''}> <b>${esc(e.name)}</b>${brigLead(b)===e.id?' <span class="pill g">бригадир</span>':''}</label>`).join('')}
    <label class="chkrow" style="padding:4px 0"><input type="radio" name="brl359" value="" ${brigLead(b)?'':'checked'}> без бригадира</label>`,
    buttons:'<button class="btn ghost" data-cbr359>Отмена</button><button class="btn" id="brSave359">💾 Сохранить роли</button>',
    onMount(bb){
      bb.querySelector('[data-cbr359]').onclick=closeModal;
      bb.querySelector('#brSave359').onclick=()=>{
        const sel=bb.querySelector('input[name="brl359"]:checked');
        const eid=sel?sel.value:'';
        (b.members||[]).forEach(id=>{if(brigRole(b,id)==='lead')brigSetRole(brigId,id,'member')});
        if(eid)brigSetRole(brigId,eid,'lead');
        closeModal();
        toast(eid?'Бригадир: '+empName(eid)+' (бригада «'+b.name+'»)':'Бригада «'+b.name+'» без бригадира','ok');
      };
    }});
}
/* ---- офлайн-снапшот канона для отложенной публикации ---- */
function pubSnapKey(){return 'pt.pub.snap'}
async function pubSnapSave(){
  try{
    const json=JSON.stringify(state);
    let gz=null;
    try{gz=await gzCompress(json)}catch(e){}
    localStorage.setItem(pubSnapKey(),JSON.stringify({ts:Date.now(),by:actor(),bytes:json.length,gz:gz||null,data:gz?null:json}));
    pubSnapBadge();
    audit('Офлайн-снапшот канона сохранён','ожидает реконнекта (3.59)','ops');
    try{teleHit('pub:snap')}catch(e){}
    return true;
  }catch(e){return false}
}
function pubSnapLoad(){try{return JSON.parse(localStorage.getItem(pubSnapKey())||'null')}catch(e){return null}}
function pubSnapClear(){try{localStorage.removeItem(pubSnapKey())}catch(e){}pubSnapBadge()}
function pubSnapBadge(){
  const s=pubSnapLoad();
  const el=$('pubSnapPill');
  if(el){el.style.display=s?'':'none';if(s)el.textContent='📦 снимок '+new Date(s.ts).toLocaleDateString('ru-RU')}
  return !!s;
}
function openPubSnap(){
  const s=pubSnapLoad();
  if(!s){toast('Офлайн-снапшот канона не сохранён','ok');return}
  openModal({title:'📦 Офлайн-снапшот канона',body:`
    <div class="status" style="margin-top:0">Сохранён: <b>${new Date(s.ts).toLocaleString('ru-RU')}</b> · ${esc(s.by||'')} · размер канона ${fmtStd(Math.round((s.bytes||0)/1024),{unit:'КБ'})}${s.gz?' · gzip':''}.</div>
    <div class="hint">Снапшот — страховка отложенной публикации (3.54): если устройство потеряется до реконнекта, снимок канона останется в localStorage и его можно выгрузить и импортировать на другом рабочем месте. После успешной доставки публикации снимок очищается автоматически.</div>`,
    buttons:'<button class="btn ghost" data-cps359>Закрыть</button><button class="btn ghost" id="psDl359">⤓ Выгрузить снимок</button><button class="btn warn" id="psDel359">✕ Очистить</button>',
    onMount(b){
      b.querySelector('[data-cps359]').onclick=closeModal;
      b.querySelector('#psDl359').onclick=async()=>{
        let json=s.data;
        if(!json&&s.gz){try{json=await gzDecompress(s.gz)}catch(e){}}
        if(!json){toast('Снимок повреждён','err');return}
        download('pub-snap-'+new Date(s.ts).toISOString().slice(0,10)+'.json',json,'application/json');
        audit('Выгрузка офлайн-снапshotа'.replace('shot','сн'),new Date(s.ts).toLocaleString('ru-RU'),'ops');
        toast('Снимок выгружен','ok');
      };
      b.querySelector('#psDel359').onclick=()=>{pubSnapClear();closeModal();toast('Снапшот очищен')};
    }});
}
"""

def patch_client(src):
    c_src = src
    def rep(old, new, label):
        nonlocal c_src
        n = c_src.count(old)
        if n != 1: raise SystemExit('ANCHOR FAIL [%s]: %d' % (label, n))
        c_src = c_src.replace(old, new, 1)
    # версии
    rep('<title>План-табель служебной деятельности · WFM 3.58</title>',
        '<title>План-табель служебной деятельности · WFM 3.59</title>', 'title')
    rep("geoPrev,ver:'3.58',", "geoPrev,ver:'3.59',", 'ver')
    rep("const ver=(window.APP&&APP.ver)||'3.58';", "const ver=(window.APP&&APP.ver)||'3.59';", 'ver fallback')
    # модуль перед секцией 9
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c_src.find(m9); assert i >= 0 and c_src.find(m9, i+1) < 0, 'marker 9'
    c_src = c_src[:i] + MODULE_359 + '\n' + c_src[i:]
    # бригада: кнопка ★ и пилл бригадира
    rep("""      <button class="x" data-brigdel="${b.id}" title="Удалить бригаду">✕</button>""",
        """      <button class="x" data-brigrole="${b.id}" title="Роли бригады: бригадир (3.59)" aria-label="Роли бригады">★</button>
      <button class="x" data-brigdel="${b.id}" title="Удалить бригаду">✕</button>""", 'star btn')
    rep("""${names.length?`: ${esc(names.slice(0,3).join(', '))}${names.length>3?'…':''}`:''}</div>""",
        """${names.length?`: ${esc(names.slice(0,3).join(', '))}${names.length>3?'…':''}`:''}${brigLead(b)?` · <span class="pill g">бригадир: ${esc(empName(brigLead(b)))}</span>`:''}</div>""", 'lead pill')
    rep("""  box.querySelectorAll('[data-brigdel]').forEach(x=>x.onclick=()=>{""",
        """  box.querySelectorAll('[data-brigrole]').forEach(x=>x.onclick=()=>openBrigRolePicker(x.dataset.brigrole));   /* 3.59 */
  box.querySelectorAll('[data-brigdel]').forEach(x=>x.onclick=()=>{""", 'star bind')
    rep("""function brigItems(){
  return brigadeList().map(b=>({id:b.id,name:b.name,patId:b.patId,anchor:b.anchor||'',
    offset:b.offset||0,members:b.members||[],ts:b.ts||0}));
}""",
        """function brigItems(){
  return brigadeList().map(b=>({id:b.id,name:b.name,patId:b.patId,anchor:b.anchor||'',
    offset:b.offset||0,members:b.members||[],roles:b.roles||{},ts:b.ts||0}));   /* 3.59: roles */
}""", 'brigItems roles')
    # снапшот в офлайн-хуке save()
    rep("""pubPendingSetTrue354()}catch(e){}   /* 3.54: офлайн-флаг полной публикации */""",
        """pubPendingSetTrue354()}catch(e){}   /* 3.54: офлайн-флаг полной публикации */
  try{if(typeof wsOn==='function'&&!wsOn())pubSnapSave()}catch(e){}   /* 3.59: офлайн-снапшот канона */""", 'snap hook')
    # реконнект: сверка и очистка снапшота
    rep("""try{if(opsCacheLoad().length)setTimeout(()=>opsCacheReplay(),400);opsCacheBadge()}catch(e){}   /* 3.51: реконнект воспроизводит офлайн-очередь */""",
        """try{if(opsCacheLoad().length)setTimeout(()=>opsCacheReplay(),400);opsCacheBadge()}catch(e){}   /* 3.51: реконнект воспроизводит офлайн-очередь */
    try{pubSnapBadge();const sn359=pubSnapLoad();if(sn359)setTimeout(()=>{if(!pubPendingGet()){pubSnapClear();try{audit('Офлайн-снапшот очищен','публикация доставлена (3.59)','ops')}catch(e){}}},2500)}catch(e){}   /* 3.59 */""", 'snap onopen')
    # пилл снапшота в шапке
    rep("""<span class="pill a" id="pubPendingPill" style="margin-left:6px;display:none" title="3.54: полная публикация канона отложена до появления сети"></span>""",
        """<span class="pill a" id="pubPendingPill" style="margin-left:6px;display:none" title="3.54: полная публикация канона отложена до появления сети"></span><span class="pill" id="pubSnapPill" style="margin-left:6px;display:none;cursor:help" title="3.59: офлайн-снапшот канона — страховка отложенной публикации"></span>""", 'snap pill')
    # палитра
    rep("""    {ic:'❓',title:'Справка и горячие клавиши',hint:'F1',run:()=>showHelp()}""",
        """    {ic:'★',title:'Роли бригады: бригадир',hint:'планирование · 3.59',run:()=>{showTab('plan');setTimeout(()=>{const b=brigadeList()[0];if(b)openBrigRolePicker(b.id);else toast('Бригад нет','err')},250)}},
    {ic:'📦',title:'Офлайн-снапшот канона: показать/выгрузить',hint:'синхронизация · 3.59',run:()=>openPubSnap()},
    {ic:'❓',title:'Справка и горячие клавиши',hint:'F1',run:()=>showHelp()}""", 'palette 359')
    # справка
    rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.58 — импорт ICS (внешние календари)</div>""",
        """      <div class="lbl" style="margin-top:12px">Новое в версии 3.59 — роли бригад (бригадир) и офлайн-снапшот публикации</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Бригадир</b>: «★» у бригады — пикер ролей (один бригадир на бригаду, хранится в <code>b.roles</code>, метка ts для серверного merge); пилл «бригадир: …» в карточке; роль передаётся на сервер в составе справочника бригад.</li>
        <li><b>Сервер</b>: PUT /api/v1/brigades валидирует <code>roles</code> — ключи только из members, значения lead/member, второй lead понижается до member.</li>
        <li><b>Офлайн-снапшот канона</b>: при отложенной полной публикации (3.54) дополнительно сохраняется gzip-снимок канона (<code>pt.pub.snap</code>) — страховка потери устройства до реконнекта; пилл «📦 снимок …» в шапке, модалка «📦» с выгрузкой снимка JSON и очисткой; после доставки публикации снимок очищается автоматически (аудит обоих событий).</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.58 — импорт ICS (внешние календари)</div>""", 'help 359')
    # экспорт APP
    rep("""    get FEATURE_MAP(){return FEATURE_MAP},openFeatureMap,trainSelfAudit,openSelfAudit,""",
        """    get FEATURE_MAP(){return FEATURE_MAP},openFeatureMap,trainSelfAudit,openSelfAudit,
    /* ===== 3.59: роли бригад и офлайн-снапшот ===== */
    brigRole,brigLead,brigSetRole,openBrigRolePicker,
    pubSnapKey,pubSnapSave,pubSnapLoad,pubSnapClear,pubSnapBadge,openPubSnap,""", 'exports 359')
    return c_src

def patch_server(src):
    t = src
    def rep(old, new, label):
        nonlocal t
        n = t.count(old)
        if n != 1: raise SystemExit('SRV ANCHOR FAIL [%s]: %d' % (label, n))
        t = t.replace(old, new, 1)
    rep("""        members:Array.isArray(it.members)?it.members.slice(0,200).map(x=>String(x).slice(0,40)):[],
        ts:+it.ts||now()};""",
        """        members:Array.isArray(it.members)?it.members.slice(0,200).map(x=>String(x).slice(0,40)):[],
        ts:+it.ts||now()};
      /* 3.59: роли бригады — только участники, значения lead|member, бригадир один */
      const roles359={};
      if(it.roles&&typeof it.roles==='object')Object.entries(it.roles).slice(0,200).forEach(([eid359,rl359])=>{
        if(rec.members.includes(String(eid359))&&(rl359==='lead'||rl359==='member'))roles359[String(eid359)]=rl359});
      const leads359=Object.keys(roles359).filter(x=>roles359[x]==='lead');
      leads359.slice(1).forEach(x=>{roles359[x]='member'});
      rec.roles=roles359;""", 'roles validation')
    return t

def main():
    on = os.path.join(HERE, 'План-табель-WFM-3.58.html')
    of = os.path.join(HERE, 'План-табель-WFM-3.58-offline.html')
    out_on = os.path.join(HERE, 'План-табель-WFM-3.59.html')
    out_of = os.path.join(HERE, 'План-табель-WFM-3.59-offline.html')
    for src, dst in ((on, out_on), (of, out_of)):
        s = io.open(src, encoding='utf-8').read()
        s = patch_client(s)
        io.open(dst, 'w', encoding='utf-8').write(s)
        print('OK %s -> %s (%d bytes)' % (os.path.basename(src), os.path.basename(dst), len(s)))
    sp = os.path.join(HERE, 'server/sync-server.mjs')
    s = io.open(sp, encoding='utf-8').read()
    if 'roles359' not in s:
        s = patch_server(s)
        io.open(sp, 'w', encoding='utf-8').write(s)
        print('OK server patched (roles 3.59)')
    else:
        print('server already patched')

if __name__ == '__main__':
    main()
