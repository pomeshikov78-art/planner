# ============================== 3.56 СЕРВЕРНЫЙ СКАН ПОКРЫТИЯ ==============================
MODULE_356 = r"""/* ================= 3.56: СЕРВЕРНЫЙ СКАН ПОКРЫТИЯ =================
   GET /api/v1/coverage — скан дефицитов по канону СЕРВЕРА (не локальному):
   доктор покрытия умеет сверять локальную картину с серверной и подменять
   календарь дефицитов серверным (при расхождении канона). */
async function coverageScanServer(y,m,deptId,opt){
  opt=opt||{};
  if(!/^https?:$/.test(location.protocol))return{err:'доступно при работе по HTTP (сервер ЛВС)'};
  const q=new URLSearchParams({y:String(y),m:String(m)});
  if(deptId&&deptId!=='all')q.set('dept',deptId);
  if(opt.need!=null)q.set('need',String(opt.need));
  if(opt.mode)q.set('mode',opt.mode);
  try{
    const r=await fetch('api/v1/coverage?'+q.toString()+(wsToken()?'&token='+encodeURIComponent(wsToken()):''),{cache:'no-store'});
    const j=await r.json();
    if(!j.ok)return{err:j.err||('HTTP '+r.status)};
    try{teleHit('coverage:server')}catch(e){}
    return j;
  }catch(e){return{err:'сервер ЛВС недоступен: '+String(e.message||e).slice(0,100)}}
}
"""

def V356(c):
    c.ver('3.56')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_356 + '\n' + c.s[i:]
    c.rep("""      b.querySelector('#cdCsv').onclick=()=>coverageCsvDl(scan);   /* 3.36: экспорт скана */""",
          """      b.querySelector('#cdCsv').onclick=()=>coverageCsvDl(scan);   /* 3.36: экспорт скана */
      const srvBtn=b.querySelector('#cdSrv');
      if(srvBtn)srvBtn.onclick=async()=>{   /* 3.56: сверка с каноном сервера */
        srvBtn.disabled=true;
        const j=await coverageScanServer(cur.y,cur.m,scan?scan.deptId:null,{need:scan?scan.need:1,mode:scan?scan.mode:'duty'});
        srvBtn.disabled=false;
        const line=b.querySelector('#cdSrvLine');
        if(!line)return;
        if(j.err){line.innerHTML=`<span class="pill r">сервер: ${esc(j.err)}</span>`;return}
        const loc=scan?scan.defDays.length:0;
        line.innerHTML=`<span class="pill ${j.defDays===loc?'g':'a'}">канон сервера №${fmtStd(j.counter)}: дефицитных ${fmtStd(j.defDays,{unit:'дн'})} · локально ${fmtStd(loc,{unit:'дн'})}</span>`+
          (j.defDays!==loc?` <button class="btn ghost tiny" id="cdUseSrv">показать серверный календарь</button>`:'');
        const ub=b.querySelector('#cdUseSrv');
        if(ub)ub.onclick=()=>{
          scan.days=j.days.map(x=>Object.assign({},x,{over:Math.max(0,x.plan-x.need)}));
          scan.defDays=j.days.filter(x=>x.deficit>0);
          scan.worst=j.worst;scan.source='server';
          redraw();
          toast('Календарь покрытия заменён серверным (канон №'+j.counter+')','ok');
        };
      };""", 'doctor server btn')
    c.rep("""      <div class="field" style="margin:0"><label>Код назначения</label><select class="inp" id="cdCode" aria-label="Код назначения">""",
          """      <div class="field" style="margin:0"><label>Сверка</label><button class="btn ghost small" id="cdSrv" title="Скан покрытия по канону сервера (3.56)">⇩ скан сервера</button></div>
      <div class="field" style="margin:0"><label>Код назначения</label><select class="inp" id="cdCode" aria-label="Код назначения">""", 'doctor srv button html')
    c.rep("""    <div id="cdBody" style="margin-top:10px"></div>`,""",
          """    <div id="cdSrvLine" class="hint" style="margin-top:6px"></div>
    <div id="cdBody" style="margin-top:10px"></div>`,""", 'doctor srv line')
    c.rep("""    {ic:'🧿',title:'OLAP бригад и покрытия: бригада × месяц',hint:'аналитика · 3.52',run:()=>{showTab('an');setTimeout(()=>{const c=$('brigolapBox');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'});renderBrigOlap()},300)}},""",
          """    {ic:'🧿',title:'OLAP бригад и покрытия: бригада × месяц',hint:'аналитика · 3.52',run:()=>{showTab('an');setTimeout(()=>{const c=$('brigolapBox');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'});renderBrigOlap()},300)}},
    {ic:'🛰',title:'Скан покрытия по канону сервера',hint:'синхронизация · 3.56',run:()=>{showTab('plan');setTimeout(()=>{openCoverageDoctor();setTimeout(()=>{const b=$('cdSrv');if(b)b.click()},350)},250)}},""", 'palette 356')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.55 — серверные роли бригад и квоты PUT</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.56 — серверный скан покрытия</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Сервер</b>: <code>GET /api/v1/coverage?y=&amp;m=&amp;dept=&amp;need=&amp;mode=</code> — скан дефицитов по канону сервера (SQLite/JSON): план по дням, дефицит против минимума подразделения или параметра, режим «дежурства/все явки», номер канона в ответе; без канона — 409 с подсказкой опубликовать базу.</li>
        <li><b>Доктор покрытия</b>: кнопка «⇩ скан сервера» — сверка локальной картины с серверной (пилл «канон сервера №N: дефицитных X · локально Y»); при расхождении — «показать серверный календарь» заменяет календарь дефицитов серверным; телеметрия <code>coverage:server</code>, палитра «🛰».</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.55 — серверные роли бригад и квоты PUT</div>""", 'help 356')
    c.rep("""    budgetsTsGet,budgetsTsSet,budgetItemsOut,budgetsPush,budgetsPull,""",
          """    budgetsTsGet,budgetsTsSet,budgetItemsOut,budgetsPush,budgetsPull,
    /* ===== 3.56: серверный скан покрытия ===== */
    coverageScanServer,""", 'exports 356')

# ============================== 3.57 ОПЕРАТИВНОЕ ТАБЛО ==============================
MODULE_357 = r"""/* ================= 3.57: ОПЕРАТИВНОЕ ТАБЛО «СЕГОДНЯ НА ДЕЖУРСТВЕ» =================
   Карточка на дашборде: сегодня/завтра по подразделениям с минимумом и бригадам
   (кто дежурит, покрытие против минимума, отсутствующие); печатная форма
   «Оперативная сводка дежурств» (F8); серверный cron-дайджест дополнен дефицитами. */
function dutyTodayData(dateShift){
  const t=TODAY();
  const d0=new Date(t.getFullYear(),t.getMonth(),t.getDate()+(dateShift||0));
  const y=d0.getFullYear(),m=d0.getMonth()+1,d=d0.getDate();
  const dk=k(y,m,d);
  const deps=state.departments.filter(dp=>(dp.minDuty||0)>0).map(dp=>{
    const on=empList(dp.id).filter(e=>{
      const raw=getCode(e.id,y,m,d);if(!raw)return false;
      const r=reason(parseCell(raw).code);return !!(r&&r.cat==='duty');
    });
    const abs=empList(dp.id).filter(e=>{
      const raw=getCode(e.id,y,m,d);if(!raw)return false;
      const r=reason(parseCell(raw).code);return !!(r&&(r.cat==='vac'||r.cat==='sick'||r.cat==='trip'));
    });
    return{dp,on:on.map(e=>({id:e.id,name:e.name,code:(reason(parseCell(getCode(e.id,y,m,d))).code||{}).code})),abs:abs.length,
      deficit:Math.max(0,dp.minDuty-on.length)};
  });
  const brigs=brigadeList().filter(b=>patById(b.patId)).map(b=>{
    const pat=patById(b.patId);
    const anchor=addDays(b.anchor||`${y}-01-01`,-(b.offset||0));
    const c=patternCodeAt(pat,anchor,y,m,d);
    if(!c)return null;
    const members=(b.members||[]).map(id=>emp(id)).filter(e=>e&&!e.fired&&!wishBlock(e.id,dk));
    return members.length?{b,code:c,members:members.map(e=>e.name)}:null;
  }).filter(Boolean);
  return{y,m,d,wd:WD[d0.getDay()],deps,brigs};
}
function renderDutyToday(){
  const v=$('view-dash');if(!v)return;
  let card=$('dutyTodayCard');
  if(!card){
    card=document.createElement('div');card.id='dutyTodayCard';card.className='card no-print';
    card.style.cssText='margin-bottom:12px';
    const first=v.querySelector('.card,.kpis,.dgrid');
    v.insertBefore(card,first||v.firstChild);
  }
  const t0=dutyTodayData(0),t1=dutyTodayData(1);
  const line=dd=>dd.deps.map(x=>`${esc(x.dp.name)}: <b>${fmtStd(x.on.length)}</b>/${fmtStd(x.dp.minDuty)}${x.deficit?` <span class="pill r">−${fmtStd(x.deficit)}</span>`:` <span class="pill g">ок</span>`}${x.abs?` <span class="hint">отсутствуют ${fmtStd(x.abs)}</span>`:''}`).join(' · ')||'<span class="hint">подразделений с минимумом нет</span>';
  const brigLine=dd=>dd.brigs.length?dd.brigs.map(x=>`${esc(x.b.name)} (${esc(x.code)}): ${esc(x.members.slice(0,4).join(', '))}${x.members.length>4?'…':''}`).join(' · '):'<span class="hint">бригады сегодня не дежурят</span>';
  card.innerHTML=`<h3>🛎 Сегодня на дежурстве<span class="sub">3.57 · ${pad2(t0.d)}.${pad2(t0.m)}.${t0.y} ${esc(t0.wd)} · оперативное табло покрытия</span></h3>
    <div class="hint" style="margin-top:2px"><b>Сегодня:</b> ${line(t0)}</div>
    <div class="hint" style="margin-top:4px"><b>Завтра:</b> ${line(t1)}</div>
    <div class="hint" style="margin-top:4px"><b>Бригады сегодня:</b> ${brigLine(t0)}</div>
    <div class="mini" style="margin-top:8px;display:flex;gap:6px"><button class="btn ghost small" id="btnDutyRoster">🖨 Оперативная сводка (F8)</button></div>`;
  const b=$('btnDutyRoster');if(b)b.onclick=()=>printDutyRoster();
}
function printDutyRoster(days){
  days=days||7;
  const t0=dutyTodayData(0);
  let rows='';
  for(let i=0;i<days;i++){
    const dd=dutyTodayData(i);
    rows+=`<tr><td><b>${pad2(dd.d)}.${pad2(dd.m)}</b> ${esc(dd.wd)}</td>
      <td>${dd.deps.map(x=>`${esc(x.dp.name)}: ${esc(x.on.map(o=>o.name.split(' ')[0]).join(', ')||'—')} (${fmtStd(x.on.length)}/${fmtStd(x.dp.minDuty)}${x.deficit?', дефицит '+fmtStd(x.deficit):''})`).join('<br>')||'—'}</td>
      <td>${dd.brigs.map(x=>`${esc(x.b.name)} (${esc(x.code)}): ${fmtStd(x.members.length,{unit:'чел'})}`).join('<br>')||'—'}</td></tr>`;
  }
  $('printArea').innerHTML='<style>@page{size:A4 landscape;margin:8mm}</style><h1>'+esc(state.org)+'</h1>'+
    '<div class="ph-sub">Оперативная сводка дежурств на '+fmtStd(days,{unit:'дн'})+' с '+pad2(t0.d)+'.'+pad2(t0.m)+'.'+t0.y+' · сформировано '+esc(stampPlain('dash'))+'</div>'+
    '<table><thead><tr><th style="min-width:70px">Дата</th><th>Подразделения (ФИО дежурных, покрытие/минимум)</th><th>Бригады на дежурстве</th></tr></thead><tbody>'+rows+'</tbody></table>'+
    '<div class="pnote">Дефицит считается против минимума подразделения; бригады — по фазам ротации с учётом пожеланий «не ставить».</div>';
  const keep=$('printHead').innerHTML;
  $('printHead').innerHTML=`<h1>${esc(state.org)}</h1>`;
  try{window.print()}catch(err){}
  setTimeout(()=>{$('printArea').innerHTML='';$('printHead').innerHTML=keep},600);
  try{teleHit('duty:roster')}catch(e){}
  audit('Печать оперативной сводки дежурств',`${fmtStd(days,{unit:'дн'})} с ${pad2(t0.d)}.${pad2(t0.m)}.${t0.y}`,'duty');
  toast('Оперативная сводка отправлена на печать','ok');
}
"""

def V357(c):
    c.ver('3.57')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_357 + '\n' + c.s[i:]
    c.rep("function renderDash(){", "function renderDash(){\n  try{renderDutyToday()}catch(e){}   /* 3.57: оперативное табло */", 'dash hook')
    c.rep("    if(e.key==='F7'){e.preventDefault();try{mgrPackAll()}catch(err){}return}   /* 3.23: пакет руководителя */",
          "    if(e.key==='F7'){e.preventDefault();try{mgrPackAll()}catch(err){}return}   /* 3.23: пакет руководителя */\n"
          "    if(e.key==='F8'){e.preventDefault();try{printDutyRoster()}catch(err){}return}   /* 3.57: оперативная сводка дежурств */", 'F8 hotkey')
    c.rep("""    {ic:'🛰',title:'Скан покрытия по канону сервера',hint:'синхронизация · 3.56',run:()=>{showTab('plan');setTimeout(()=>{openCoverageDoctor();setTimeout(()=>{const b=$('cdSrv');if(b)b.click()},350)},250)}},""",
          """    {ic:'🛰',title:'Скан покрытия по канону сервера',hint:'синхронизация · 3.56',run:()=>{showTab('plan');setTimeout(()=>{openCoverageDoctor();setTimeout(()=>{const b=$('cdSrv');if(b)b.click()},350)},250)}},
    {ic:'🛎',title:'Оперативная сводка дежурств (печать, F8)',hint:'вывод · 3.57',run:()=>printDutyRoster()},""", 'palette 357')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.56 — серверный скан покрытия</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.57 — оперативное табло и сводка дежурств</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Карточка «🛎 Сегодня на дежурстве»</b> на дашборде: сегодня и завтра по каждому подразделению с минимумом — дежурные/минимум, дефицит (красный пилл), отсутствующие; отдельно — бригады, дежурящие сегодня (с учётом пожеланий «не ставить»).</li>
        <li><b>«🖨 Оперативная сводка (F8)»</b>: печатная форма на 7 дней вперёд (альбомная, светлая): дата, ФИО дежурных и покрытие/минимум по подразделениям, бригады на дежурстве; аудит и телеметрия <code>duty:roster</code>; горячая клавиша F8 и палитра «🛎».</li>
        <li><b>Сервер</b>: cron-дайджест (PT_DIGEST_CRON) дополнен секцией «Дефициты покрытия 7 дней: подразделение: N дн.» по канону сервера — попадает в чат, PT_DIGEST_OUT и webhook.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.56 — серверный скан покрытия</div>""", 'help 357')
    c.rep("""    coverageScanServer,""",
          """    coverageScanServer,
    /* ===== 3.57: оперативное табло ===== */
    dutyTodayData,renderDutyToday,printDutyRoster,""", 'exports 357')

# ============================== 3.58 ИМПОРТ ICS ==============================
MODULE_358 = r"""/* ================= 3.58: ИМПОРТ ICS (ВНЕШНИЕ КАЛЕНДАРИ) =================
   Парсер RFC 5545 (unfolding, экранирование, DTSTART DATE и DATE-TIME),
   распознавание собственных экспортов («КОД · ФИО (бригада)»), применение
   событий к плану как отметок с защитой отсутствий. */
function icsUnfold(txt){
  return String(txt||'').replace(/\r\n[ \t]/g,'').replace(/\r/g,'').replace(/\n[ \t]/g,'');
}
function icsUnescape(s){
  return String(s||'').replace(/\\([;,])/g,'$1').replace(/\\[nN]/g,'\n').replace(/\\\\/g,'\\');
}
function parseIcs(txt){
  const t=icsUnfold(txt);
  if(!/BEGIN:VCALENDAR/i.test(t))return null;
  const events=[];
  const blocks=t.split('BEGIN:VEVENT').slice(1);
  blocks.forEach(bl=>{
    const body=bl.split('END:VEVENT')[0]||'';
    const get=re=>{const m=body.match(re);return m?m[1]:null};
    const ds=get(/DTSTART(?:;[^:]*)?:(\S+)/);
    const de=get(/DTEND(?:;[^:]*)?:(\S+)/);
    const sum=get(/SUMMARY:([^\n]*)/);
    const uid=get(/UID:([^\n]*)/);
    if(!ds)return;
    const parseDt=v=>{
      const m=String(v).match(/^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2}))?/);
      if(!m)return null;
      return{k:m[1]+'-'+m[2]+'-'+m[3],allDay:!/T/.test(String(v)),y:+m[1],m:+m[2],d:+m[3]};
    };
    const st=parseDt(ds),en=de?parseDt(de):null;
    if(!st)return;
    const codeMatch=icsUnescape(sum||'').match(/^([A-ZА-Я0-9]{1,4})\s·\s/);
    events.push({uid:uid||'',summary:icsUnescape(sum||''),start:st,end:en||st,allDay:st.allDay,
      code:codeMatch?codeMatch[1]:null});
  });
  return events;
}
function icsMatchEmp(summary){
  const m=String(summary||'').match(/·\s*([^()]+?)\s*\(/);
  if(!m)return null;
  const nm=m[1].trim().toLowerCase();
  return state.employees.find(e=>!e.fired&&String(e.name).toLowerCase()===nm)||
         state.employees.find(e=>!e.fired&&String(e.name).toLowerCase().indexOf(nm.split(' ')[0])===0)||null;
}
function icsPreviewHtml(evs){
  if(!evs||!evs.length)return '<div class="status err" style="margin-top:0">Событий не найдено (нет VEVENT).</div>';
  return '<div class="scroll-x" style="max-height:38vh;overflow:auto"><table class="rtbl"><thead><tr><th>Дата</th><th>Событие</th><th>Код</th><th>Сотрудник</th></tr></thead><tbody>'+
    evs.slice(0,120).map(ev=>{
      const e=icsMatchEmp(ev.summary);
      return '<tr><td class="n">'+ev.start.k.split('-').reverse().join('.')+(ev.end.k!==ev.start.k?' → '+ev.end.k.split('-').reverse().join('.'):'')+'</td><td>'+esc(ev.summary.slice(0,60))+'</td><td>'+(ev.code?'<span class="pill">'+esc(ev.code)+'</span>':'—')+'</td><td>'+(e?esc(e.name):'<span class="hint">не сопоставлен</span>')+'</td></tr>';
    }).join('')+
    '</tbody></table></div>'+
    '<div class="hint" style="margin-top:6px">Событий: '+fmtStd(evs.length,{unit:'шт'})+(evs.length>120?' (показаны первые 120)':'')+'; применятся только целодневные события с кодом из справочника и сопоставленным сотрудником.</div>';
}
function icsApplyToPlan(evs){
  let applied=0,skipped=0;
  if(!guardRole('edit','применение событий ICS к плану'))return{applied:0,skipped:0};
  pushUndo('импорт ICS');
  (evs||[]).forEach(ev=>{
    if(!ev.code||!reason(ev.code))return;
    const e=icsMatchEmp(ev.summary);
    if(!e)return;
    const d0=dparse(ev.start.k);
    const d1=ev.allDay?dparse(ev.end.k):d0;
    for(let d=new Date(d0);d<=d1;d.setDate(d.getDate()+1)){
      const y=d.getFullYear(),m=d.getMonth()+1,dd=d.getDate();
      const raw=getCode(e.id,y,m,dd);
      if(rotBusyRaw(raw)){skipped++;continue}
      if(raw){const r=reason(parseCell(raw).code);if(r&&r.cat==='duty'){skipped++;continue}}
      setCellRaw(e.id,y,m,dd,ev.code);applied++;
    }
  });
  if(applied){bust();save(true);refreshAll();
    audit('Импорт ICS в план',fmtStd(applied,{unit:'ячеек'})+' применено, '+fmtStd(skipped,{unit:'дн'})+' пропущено','plan:'+mkOf(cur.y,cur.m));}
  return{applied,skipped};
}
function openIcsImport(text){
  try{teleHit('ics:import')}catch(e){}
  const evs=text?parseIcs(text):null;
  openModal({title:'📥 Импорт ICS: внешние календари',wide:true,body:
    '<div class="hint" style="margin-top:0">Файл .ics (RFC 5545): события разбираются с учётом переносов строк и экранирования; собственные экспорты ротаций распознаются по заголовку «КОД · ФИО (бригада)» и сопоставляются сотрудникам. Целодневные события применяются к плану как отметки кода (отсутствия и дежурства не перезаписываются).</div>'+
    '<div class="field"><label>Файл .ics</label><input type="file" id="icsFile" accept=".ics,text/calendar"></div>'+
    '<div id="icsPrev" style="margin-top:8px">'+(evs?icsPreviewHtml(evs):'<div class="hint">Выберите файл — события появятся здесь.</div>')+'</div>',
    buttons:'<button class="btn ghost" data-cics>Закрыть</button><button class="btn" id="icsApply">✔ Применить к плану</button>',
    onMount(b){
      let curEvs=evs||[];
      b.querySelector('[data-cics]').onclick=closeModal;
      b.querySelector('#icsFile').onchange=async e=>{
        const f=e.target.files&&e.target.files[0];if(!f)return;
        const txt=await f.text();
        curEvs=parseIcs(txt)||[];
        b.querySelector('#icsPrev').innerHTML=icsPreviewHtml(curEvs);
      };
      b.querySelector('#icsApply').onclick=()=>{
        const res=icsApplyToPlan(curEvs);
        if(res.applied)toast('ICS: применено '+fmtStd(res.applied,{unit:'событий'})+(res.skipped?', пропущено '+fmtStd(res.skipped,{unit:'дн'})+' (отсутствия/дежурства/нет кода)':''),'ok');
        else toast('ICS: нечего применить — нет целодневных событий с кодом и сопоставленным сотрудником','err');
        closeModal();
      };
    }});
}
"""

def V358(c):
    c.ver('3.58')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_358 + '\n' + c.s[i:]
    c.rep("""        <button class="btn ghost small" id="btnCovDoc" title="Доктор покрытия: дефициты по дням и умные рекомендации (3.36)">🩺 Покрытие</button>""",
          """        <button class="btn ghost small" id="btnCovDoc" title="Доктор покрытия: дефициты по дням и умные рекомендации (3.36)">🩺 Покрытие</button>
        <button class="btn ghost small" id="btnIcsImport" title="Импорт событий .ics (RFC 5545) с применением к плану (3.58)">📥 Импорт ICS</button>""", 'ics button plan toolbar')
    c.rep("  bindClick('btnCovDoc',openCoverageDoctor);                                        /* 3.36: доктор покрытия */",
          "  bindClick('btnCovDoc',openCoverageDoctor);                                        /* 3.36: доктор покрытия */\n"
          "  bindClick('btnIcsImport',()=>openIcsImport());                                    /* 3.58: импорт ICS */", 'ics bind')
    c.rep("""    {ic:'🛎',title:'Оперативная сводка дежурств (печать, F8)',hint:'вывод · 3.57',run:()=>printDutyRoster()},""",
          """    {ic:'🛎',title:'Оперативная сводка дежурств (печать, F8)',hint:'вывод · 3.57',run:()=>printDutyRoster()},
    {ic:'📥',title:'Импорт ICS: внешние календари',hint:'импорт · 3.58',run:()=>{showTab('plan');setTimeout(()=>openIcsImport(),250)}},""", 'palette 358')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.57 — оперативное табло и сводка дежурств</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.58 — импорт ICS (внешние календари)</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Парсер RFC 5545</b>: unfolding строк, экранирование запятых/точек с запятой/переносов, DTSTART/DTEND в формах DATE и DATE-TIME, несколько VEVENT; кнопка «📥 Импорт ICS» в тулбаре «Планирования» и палитра.</li>
        <li><b>Распознавание собственных экспортов</b>: заголовок события «КОД · ФИО (бригада)» (формат экспорта 3.37) даёт код причины и сотрудника; предпросмотр таблицы событий до применения.</li>
        <li><b>Применение к плану</b>: целодневные события с известным кодом и сопоставленным сотрудником ставятся отметками (диапазоны DTSTART–DTEND включительно); отсутствия и уже стоящие дежурства не перезаписываются; undo-стек, аудит, телеметрия <code>ics:import</code>.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.57 — оперативное табло и сводка дежурств</div>""", 'help 358')
    c.rep("""    dutyTodayData,renderDutyToday,printDutyRoster,""",
          """    dutyTodayData,renderDutyToday,printDutyRoster,
    /* ===== 3.58: импорт ICS ===== */
    icsUnfold,icsUnescape,parseIcs,icsMatchEmp,openIcsImport,icsPreviewHtml,icsApplyToPlan,""", 'exports 358')
