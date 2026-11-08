#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3.63–3.65 поверх канонической цепочки main (3.62):
   3.63 ICS round-trip (двусторонняя синхронизация: дифф собственного
        экспорта с планом — изменения/удаления/добавления, защита отсутствий),
   3.64 одобрение обменов бригадиром (опц. шаг маршрута, settings.leadApprove),
   3.65 панель бригадира в «Моём месяце» (сводка бригады для роли lead)."""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))

MODULE_363 = r"""/* ================= 3.63: ICS ROUND-TRIP (ДВУСТОРОННЯЯ СИНХРОНИЗАЦИЯ) =================
   Собственные экспорты несут стабильные UID: ротации «бригада-сотрудник-ГГГГ-ММ-ДД@plantabel»
   (3.37/3.61), месячный план «сотрудник-ГГГГММДД-N@plantabel» (3.21). Round-trip
   сравнивает .ics, вернувшийся из внешнего календаря, с текущим планом и строит
   кандидаты: chg — код смены в календаре отличается от плана; del — смена ротации
   убрана в календаре (месяц покрыт экспортом, но события нет); add — стороннее
   событие с кодом причины либо восстановление собственной смены. Отсутствия
   (отпуск/больничный/командировка/учебный/неявка) защищены от перезаписи и
   удаления даже по собственным UID; удаления по умолчанию не отмечены. Чистая
   математика: icsOwnUid / icsRoundTripDiff / icsApplyRoundTrip. */
function icsOwnUid(uid){
  const s=String(uid||'').trim();
  let m=s.match(/^([^-@]+)-([^-@]+)-(\d{4}-\d{2}-\d{2})@plantabel$/i);
  if(m)return{kind:'rot',brigId:m[1],eid:m[2],dk:m[3]};
  m=s.match(/^([^-@]+)-(\d{8})-(\d+)@plantabel$/i);
  if(m)return{kind:'month',eid:m[1],start:m[2],run:+m[3]};
  return null;
}
function empBrigade(eid){return brigadeList().find(b=>(b.members||[]).includes(eid))||null}
function brigAnchorYear(b,year){return addDays(b.anchor||`${year}-01-01`,-(b.offset||0))}
function icsCellAbsent(eid,y,m,d){
  const raw=getCode(eid,y,m,d);
  return !!raw&&rotBusyRaw(raw);
}
function icsRoundTripDiff(evs){
  const rows=[];
  const seen={};
  const addRow=r=>{const key=r.act+'|'+r.eid+'|'+r.dk;if(!seen[key]){seen[key]=1;rows.push(r)}};
  const own={};      /* eid|dk -> 1: собственные события, присутствующие в файле */
  const covered={};  /* eid -> {«y-m»:1}: месяцы, покрытые собственным экспортом */
  (evs||[]).forEach(ev=>{
    const o=icsOwnUid(ev.uid);
    if(o&&o.kind==='rot'){
      const[y,m,d]=o.dk.split('-').map(Number);
      own[o.eid+'|'+o.dk]=1;
      (covered[o.eid]=covered[o.eid]||{})[y+'-'+m]=1;
      const b=brigadeList().find(x=>x.id===o.brigId);
      const pat=b?patById(b.patId):null;
      const raw=getCode(o.eid,y,m,d);
      let exp=raw?parseCell(raw).code:null;
      if(exp==null&&b&&pat)exp=patternCodeAt(pat,brigAnchorYear(b,y),y,m,d)||null;
      const got=ev.code;
      if(!got)return;
      if(exp&&got!==exp&&!icsCellAbsent(o.eid,y,m,d))
        addRow({act:'chg',eid:o.eid,dk:o.dk,y,m,d,from:exp,to:got,src:'собственный экспорт'});
      else if(!exp&&!icsCellAbsent(o.eid,y,m,d))
        addRow({act:'add',eid:o.eid,dk:o.dk,y,m,d,from:null,to:got,src:'собственный экспорт: восстановление смены'});
      return;
    }
    /* стороннее событие — кандидат отметки в плане (правила импорта 3.58) */
    const e=icsMatchEmp(ev.summary);
    if(!e||!ev.code||!reason(ev.code)||!ev.allDay)return;
    const d0=dparse(ev.start.k),d1=dparse(ev.end.k);
    for(let dt=new Date(d0);dt<=d1;dt.setDate(dt.getDate()+1)){
      const y=dt.getFullYear(),m=dt.getMonth()+1,d=dt.getDate();
      if(getCode(e.id,y,m,d))continue;   /* занятые ячейки не трогаем */
      addRow({act:'add',eid:e.id,dk:k(y,m,d),y,m,d,from:null,to:ev.code,src:'сторонний календарь'});
    }
  });
  /* удалённые во внешнем календаре смены: месяц покрыт экспортом, события нет,
     а в плане по-прежнему код ротации (не отсутствие и не дежурство) */
  Object.keys(covered).forEach(eid=>{
    Object.keys(covered[eid]).forEach(ym=>{
      const[y,m]=ym.split('-').map(Number);
      const b=empBrigade(eid),pat=b?patById(b.patId):null;
      if(!b||!pat)return;
      const anchor=brigAnchorYear(b,y);
      for(let d=1;d<=dim(y,m);d++){
        const dk=k(y,m,d);
        if(own[eid+'|'+dk])continue;
        const pc=patternCodeAt(pat,anchor,y,m,d);
        if(!pc)continue;
        const raw=getCode(eid,y,m,d);
        if(!raw||parseCell(raw).code!==pc)continue;   /* ячейка не от ротации — не трогаем */
        if(icsCellAbsent(eid,y,m,d))continue;
        if(wishBlock(eid,dk))continue;                /* пожелание «не ставить»: в экспорте и не было */
        addRow({act:'del',eid,dk,y,m,d,from:pc,to:null,src:'удалено в календаре'});
      }
    });
  });
  rows.sort((a,b)=>a.dk<b.dk?-1:a.dk>b.dk?1:(a.eid<b.eid?-1:1));
  return rows;
}
function icsApplyRoundTrip(rows){
  let applied=0;
  const sel=(rows||[]).filter(Boolean);
  if(!sel.length)return{applied:0};
  if(!guardRole('edit','применение ICS round-trip'))return{applied:0};
  pushUndo('ICS round-trip');
  sel.forEach(r=>{
    if(r.act==='del')setCellRaw(r.eid,r.y,r.m,r.d,null);
    else setCellRaw(r.eid,r.y,r.m,r.d,r.to);
    applied++;
  });
  if(applied){
    bust();save(true);refreshAll();
    const nChg=sel.filter(r=>r.act==='chg').length,nDel=sel.filter(r=>r.act==='del').length,nAdd=sel.filter(r=>r.act==='add').length;
    audit('ICS round-trip синхронизация',fmtStd(applied,{unit:'ячеек'})+': изменений '+fmtStd(nChg)+', удалений '+fmtStd(nDel)+', добавлений '+fmtStd(nAdd),'ics');
    try{teleHit('ics:roundtrip')}catch(e){}
  }
  return{applied};
}
function icsRoundTripHtml(rows){
  if(!rows||!rows.length)return '<div class="status ok" style="margin-top:8px">🔁 Расхождений с планом нет: календарь соответствует канону (или в файле нет событий с кодами).</div>';
  const ACT={chg:'изменение',del:'удаление',add:'добавление'};
  return '<div class="scroll-x" style="max-height:34vh;overflow:auto;margin-top:8px"><table class="rtbl"><thead><tr><th></th><th>Дата</th><th>Сотрудник</th><th>Действие</th><th>было → станет</th><th>Источник</th></tr></thead><tbody>'+
    rows.slice(0,200).map((r,i)=>'<tr><td><input type="checkbox" data-rt="'+i+'"'+(r.act==='del'?'':' checked')+' title="'+(r.act==='del'?'удаление: отметьте осознанно':'')+'"></td><td class="n">'+r.dk.split('-').reverse().join('.')+'</td><td>'+esc(empName(r.eid))+'</td><td><span class="pill '+(r.act==='del'?'r':r.act==='chg'?'a':'g')+'">'+ACT[r.act]+'</span></td><td>'+(r.from?'<b>'+esc(r.from)+'</b> → ':'')+(r.to?'<b>'+esc(r.to)+'</b>':'<span class="hint">очистить</span>')+'</td><td class="hint">'+esc(r.src)+'</td></tr>').join('')+
    '</tbody></table></div>'+
    '<div class="hint" style="margin-top:6px">Кандидатов: '+fmtStd(rows.length,{unit:'шт'})+(rows.length>200?' (показаны первые 200)':'')+'. Удаления по умолчанию не отмечены — проверьте, что смену действительно сняли во внешнем календаре. Отсутствия защищены от перезаписи и удаления.</div>';
}
"""

MODULE_364 = r"""/* ================= 3.64: ОДОБРЕНИЕ ОБМЕНОВ БРИГАДИРОМ =================
   Необязательный шаг маршрута (флажок «одобрение бригадиром» в карточке обменов,
   канон state.settings.leadApprove, по умолчанию выключен — прежний маршрут не
   меняется): после согласия напарника заявка с участием сотрудника бригады, у
   которой есть бригадир (3.59), переходит в статус «lead_review»; бригадир
   подтверждает (★) или отклоняет — затем обычное решение руководителя.
   Действия пишутся в историю заявки, аудит и телеметрию (swap:lead). */
function leadApproveOn(){return !!(state.settings&&state.settings.leadApprove)}
function empBrigLead(eid){
  const b=empBrigade(eid);
  return b?brigLead(b):null;
}
function swapNeedsLead(s){
  if(!leadApproveOn()||!s||s.leadOk)return false;
  if(s.status!=='new'&&s.status!=='agreed'&&s.status!=='lead_review')return false;
  return !!(empBrigLead(s.eid1)||empBrigLead(s.eid2));
}
"""

MODULE_365 = r"""/* ================= 3.65: ПАНЕЛЬ БРИГАДИРА («МОЙ МЕСЯЦ») =================
   Для сотрудника с ролью lead (3.59) в «Моём месяце» появляется сводная карточка
   бригады: дежурят / отсутствуют / на ротации сегодня и состав (KPI), полоса
   «неделя: дежурных по дням», активные заявки бригады (включая ожидающие
   ★-подтверждения — 3.64) и быстрые действия (обмены, ведомость). Чистая
   математика — leadPanelData(brigId,y,m,d0). */
function leadPanelData(brigId,y,m,d0){
  const b=brigadeList().find(x=>x.id===brigId);
  if(!b)return null;
  const pat=patById(b.patId);
  const anchor=pat?brigAnchorYear(b,y):null;
  const mem=(b.members||[]).map(eid=>emp(eid)).filter(e=>e&&!e.fired);
  const d=d0||1;
  let duty=0,absent=0,rot=0;
  mem.forEach(e=>{
    const raw=getCode(e.id,y,m,d);
    const r=raw?reason(parseCell(raw).code):null;
    if(r&&ABS_CATS.indexOf(r.cat)>=0)absent++;
    else if(r&&r.cat==='duty')duty++;
    else if(pat&&anchor&&patternCodeAt(pat,anchor,y,m,d))rot++;
  });
  const week=[];
  for(let i=0;i<7;i++){
    const dt=new Date(y,m-1,d+i);
    const yy=dt.getFullYear(),mm=dt.getMonth()+1,dd=dt.getDate();
    let wd=0,wa=0;
    mem.forEach(e=>{
      const raw=getCode(e.id,yy,mm,dd);
      const r=raw?reason(parseCell(raw).code):null;
      if(r&&ABS_CATS.indexOf(r.cat)>=0)wa++;
      else if(r&&r.cat==='duty')wd++;
    });
    week.push({d:dd,dk:k(yy,mm,dd),duty:wd,absent:wa,off:dayInfo(yy,mm,dd).off});
  }
  const mset={};mem.forEach(e=>{mset[e.id]=1});
  const sw=swapList().filter(s=>(s.status==='new'||s.status==='agreed'||s.status==='lead_review')&&(mset[s.eid1]||mset[s.eid2]));
  return{brig:b,year:y,month:m,day:d,members:mem.length,duty,absent,rot,week,swaps:sw,leadPending:sw.filter(s=>s.status==='lead_review')};
}
function leadPanelHtml(LP){
  const days=LP.week.map(w=>'<span class="pwcell'+(w.off?' off':'')+'" title="'+w.dk.split('-').reverse().join('.')+': дежурных '+fmtStd(w.duty)+', отсутствуют '+fmtStd(w.absent)+'"><em>'+w.d+'</em>'+fmtStd(w.duty)+'</span>').join('');
  const sw=LP.swaps.slice(0,3).map(s=>'<div class="log-row"><span>'+(s.type==='swap'?'⇄':'→')+' '+esc(empName(s.eid1))+' / '+esc(empName(s.eid2))+' · '+esc(dstr(s.mk1,s.day1))+'</span><span class="pill '+(SWAP_BADGE[s.status]||'')+'">'+esc(SWAP_STATUS[s.status]||s.status)+'</span></div>').join('');
  return '<div class="card" id="meLeadCard"><h3>Панель бригадира<span class="sub">3.65 · бригада «'+esc(LP.brig.name)+'» · '+fmtStd(LP.day)+' '+esc(MUP[LP.month-1])+' '+fmtStd(LP.year)+'</span></h3>'+
    '<div class="kpis" style="margin:8px 0">'+
      '<div class="kpi" style="--kc:var(--green)"><div class="kv">'+fmtStd(LP.duty)+'</div><div class="kt">дежурят сегодня</div></div>'+
      '<div class="kpi" style="--kc:var(--red)"><div class="kv">'+fmtStd(LP.absent)+'</div><div class="kt">отсутствуют</div></div>'+
      '<div class="kpi"><div class="kv">'+fmtStd(LP.rot)+'</div><div class="kt">на ротации</div></div>'+
      '<div class="kpi"><div class="kv">'+fmtStd(LP.members)+'</div><div class="kt">человек в бригаде</div></div>'+
    '</div>'+
    '<div class="lbl">Неделя: дежурных по дням</div>'+
    '<div class="pwstrip" style="margin-top:4px" role="img" aria-label="Дежурных по дням на неделю вперёд">'+days+'</div>'+
    '<div class="lbl" style="margin-top:10px">Заявки бригады'+(LP.leadPending.length?' · <span class="pill a">ждут вашего ★-подтверждения: '+fmtStd(LP.leadPending.length)+'</span>':'')+'</div>'+
    (sw||'<div class="hint">Активных заявок с участием бригады нет.</div>')+
    '<div class="mini" style="margin-top:8px;display:flex;gap:6px"><button class="btn ghost small" id="meLeadSwaps">⇄ Открыть обмены</button><button class="btn ghost small" id="meLeadVed" title="Печать бригадной ведомости (3.36)">🖨 Ведомость бригады</button></div>'+
  '</div>';
}
"""

def V363(c):
    c.ver('3.63')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_363 + '\n' + c.s[i:]
    c.rep("""    '<div id="icsPrev" style="margin-top:8px">'+(evs?icsPreviewHtml(evs):'<div class="hint">Выберите файл — события появятся здесь.</div>')+'</div>',
    buttons:'<button class="btn ghost" data-cics>Закрыть</button><button class="btn" id="icsApply">✔ Применить к плану</button>',""",
          """    '<div id="icsPrev" style="margin-top:8px">'+(evs?icsPreviewHtml(evs):'<div class="hint">Выберите файл — события появятся здесь.</div>')+'</div>'+
    '<div class="mini" style="margin-top:8px;display:flex;gap:6px"><button class="btn ghost small" id="icsRt" title="Сравнить собственные экспорты в файле с текущим планом (3.63)">🔁 Round-trip: дифф с планом</button></div><div id="icsRtBox"></div>',
    buttons:'<button class="btn ghost" data-cics>Закрыть</button><button class="btn ghost" id="icsRtApply" hidden>✔ Применить выбранное (round-trip)</button><button class="btn" id="icsApply">✔ Применить к плану</button>',""", 'rt modal ui')
    c.rep("""      let curEvs=evs||[];
      b.querySelector('[data-cics]').onclick=closeModal;
      b.querySelector('#icsFile').onchange=async e=>{
        const f=e.target.files&&e.target.files[0];if(!f)return;
        const txt=await f.text();
        curEvs=parseIcs(txt)||[];
        b.querySelector('#icsPrev').innerHTML=icsPreviewHtml(curEvs);
      };""",
          """      let curEvs=evs||[];
      let rtRows=[];   /* 3.63: кандидаты round-trip */
      b.querySelector('[data-cics]').onclick=closeModal;
      b.querySelector('#icsFile').onchange=async e=>{
        const f=e.target.files&&e.target.files[0];if(!f)return;
        const txt=await f.text();
        curEvs=parseIcs(txt)||[];
        b.querySelector('#icsPrev').innerHTML=icsPreviewHtml(curEvs);
        rtRows=[];b.querySelector('#icsRtBox').innerHTML='';b.querySelector('#icsRtApply').hidden=true;   /* 3.63 */
      };
      b.querySelector('#icsRt').onclick=()=>{   /* 3.63: round-trip */
        rtRows=icsRoundTripDiff(curEvs);
        b.querySelector('#icsRtBox').innerHTML=icsRoundTripHtml(rtRows);
        b.querySelector('#icsRtApply').hidden=!rtRows.length;
        try{teleHit('ics:rtdiff')}catch(e){}
      };
      b.querySelector('#icsRtApply').onclick=()=>{
        const sel=[];
        b.querySelector('#icsRtBox').querySelectorAll('[data-rt]').forEach(cb=>{if(cb.checked&&rtRows[+cb.dataset.rt])sel.push(rtRows[+cb.dataset.rt])});
        if(!sel.length){toast('Round-trip: не выбрано ни одной строки','err');return}
        const res=icsApplyRoundTrip(sel);
        if(res.applied){toast('Round-trip: применено '+fmtStd(res.applied,{unit:'ячеек'}),'ok');closeModal();}
        else toast('Round-trip: не применено (нет прав или изменений)','err');
      };""", 'rt modal binds')
    c.rep("""    {ic:'📥',title:'Импорт ICS: внешние календари',hint:'импорт · 3.58',run:()=>{showTab('plan');setTimeout(()=>openIcsImport(),250)}},""",
          """    {ic:'📥',title:'Импорт ICS: внешние календари',hint:'импорт · 3.58',run:()=>{showTab('plan');setTimeout(()=>openIcsImport(),250)}},
    {ic:'🔁',title:'ICS round-trip: дифф экспорта с планом',hint:'импорт · 3.63',run:()=>{showTab('plan');setTimeout(()=>openIcsImport(),250)}},""", 'palette 363')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.62 — подписи приказов и реестр</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.63 — ICS round-trip (двусторонняя синхронизация)</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>«🔁 Round-trip: дифф с планом»</b> в модалке импорта ICS: файл из внешнего календаря сравнивается с текущим планом по стабильным UID собственных экспортов («бригада-сотрудник-дата@plantabel»).</li>
        <li>Три класса кандидатов: <b>изменение</b> (код смены в календаре отличается от плана), <b>удаление</b> (смена ротации убрана в календаре — месяц покрыт экспортом, но событие отсутствует; по умолчанию не отмечено), <b>добавление</b> (сторонние события с кодом причины и восстановление собственных смен).</li>
        <li>«✔ Применить выбранное (round-trip)» переносит отмеченные строки в план (undo, аудит «ICS round-trip синхронизация», телеметрия <code>ics:rtdiff</code> / <code>ics:roundtrip</code>); отсутствия (отпуск/больничный/командировка/учебный/неявка) защищены от перезаписи и удаления даже по собственным UID.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.62 — подписи приказов и реестр</div>""", 'help 363')
    c.rep("""    diffStates,pubSnapState,pubSnapDiffLocal,pubSnapDiffServer,diffRenderHtml,""",
          """    diffStates,pubSnapState,pubSnapDiffLocal,pubSnapDiffServer,diffRenderHtml,
    /* ===== 3.63: ICS round-trip ===== */
    icsOwnUid,empBrigade,brigAnchorYear,icsCellAbsent,icsRoundTripDiff,icsApplyRoundTrip,icsRoundTripHtml,""", 'exports 363')

def V364(c):
    c.ver('3.64')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_364 + '\n' + c.s[i:]
    c.rep("""const SWAP_STATUS={new:'Ожидает согласия напарника',agreed:'Согласовано напарником · ждёт руководителя',applied:'Применено к плану',rejected:'Отклонено',cancelled:'Отозвано'};
const SWAP_BADGE={new:'a',agreed:'a',applied:'g',rejected:'r',cancelled:''};""",
          """const SWAP_STATUS={new:'Ожидает согласия напарника',agreed:'Согласовано напарником · ждёт руководителя',lead_review:'Согласовано · ждёт бригадира (★)',applied:'Применено к плану',rejected:'Отклонено',cancelled:'Отозвано'};
const SWAP_BADGE={new:'a',agreed:'a',lead_review:'a',applied:'g',rejected:'r',cancelled:''};""", 'swap status maps')
    c.rep("""  if(act==='agree'){s.status='agreed';s.history.push({ts:Date.now(),by:actor(),act:'согласовано напарником'});audit('Согласие на обмен',`${empName(s.eid2)} · ${dstr(s.mk1,s.day1)}`,'swap:'+s.id);try{opsQueue({k:'req',sub:'swap',swap:s})}catch(e){}save(true);renderSwaps();updateAlerts(true);toast('Напарник согласовал — заявка направлена руководителю','ok');return}
  if(act==='approve'){
    const iss=swapCheck(s).filter(i=>i.sev==='crit');""",
          """  if(act==='agree'){s.status=swapNeedsLead(s)?'lead_review':'agreed';s.history.push({ts:Date.now(),by:actor(),act:'согласовано напарником'});audit('Согласие на обмен',`${empName(s.eid2)} · ${dstr(s.mk1,s.day1)}`,'swap:'+s.id);try{opsQueue({k:'req',sub:'swap',swap:s})}catch(e){}save(true);renderSwaps();updateAlerts(true);toast(s.status==='lead_review'?'Напарник согласовал — ждём подтверждения бригадира (★)':'Напарник согласовал — заявка направлена руководителю','ok');return}
  /* 3.64: шаг бригадира */
  if(act==='leadok'){s.leadOk=true;s.leadBy=actor();s.leadAt=Date.now();if(s.status==='lead_review')s.status='agreed';s.history.push({ts:Date.now(),by:actor(),act:'подтверждено бригадиром'});audit('Бригадир подтвердил обмен',`${empName(s.eid1)} ⇄ ${empName(s.eid2)} · ${dstr(s.mk1,s.day1)}`,'swap:'+s.id);try{opsQueue({k:'req',sub:'swap',swap:s})}catch(e){}try{teleHit('swap:lead')}catch(e){}save(true);renderSwaps();updateAlerts(true);toast('Бригадир подтвердил — заявка направлена руководителю','ok');return}
  if(act==='leadno'){s.status='rejected';s.rejectNote=note||'отклонено бригадиром';s.history.push({ts:Date.now(),by:actor(),act:'отклонено бригадиром',note:note||''});audit('Бригадир отклонил обмен',`${empName(s.eid1)} ⇄ ${empName(s.eid2)}${note?' · '+note:''}`,'swap:'+s.id,{sev:'warn'});try{opsQueue({k:'req',sub:'swap',swap:s})}catch(e){}save(true);renderSwaps();updateAlerts(true);toast('Бригадир отклонил заявку');return}
  if(act==='approve'){
    if(swapNeedsLead(s)){toast('Требуется подтверждение бригадира (★) — 3.64','err');try{audit('Обмен заблокирован до подтверждения бригадира',`${empName(s.eid1)} ⇄ ${empName(s.eid2)}`,'swap:'+s.id,{sev:'warn'})}catch(e){}renderSwaps();return}
    const iss=swapCheck(s).filter(i=>i.sev==='crit');""", 'swap act lead')
    c.rep("""  if(f==='active')L=L.filter(s=>s.status==='new'||s.status==='agreed');""",
          """  if(f==='active')L=L.filter(s=>s.status==='new'||s.status==='agreed'||s.status==='lead_review');""", 'swap active filter')
    c.rep("""  const kpi=`<div class="kpis" style="margin-bottom:10px">
      <div class="kpi"><div class="kv">${stat.filter(s=>s.status==='new').length}</div><div class="kt">ожидают согласия напарника</div></div>""",
          """  const leadKpi=(leadApproveOn()||stat.some(s=>s.status==='lead_review'))?`<div class="kpi" style="--kc:var(--amber)"><div class="kv">${stat.filter(s=>s.status==='lead_review').length}</div><div class="kt">ждут бригадира (★)</div></div>`:'';   /* 3.64 */
  const kpi=`<div class="kpis" style="margin-bottom:10px">
      <div class="kpi"><div class="kv">${stat.filter(s=>s.status==='new').length}</div><div class="kt">ожидают согласия напарника</div></div>
      ${leadKpi}""", 'swap kpi lead')
    c.rep("""    if(s.status==='new'||s.status==='agreed'){
      acts.push(`<button class="btn small" data-swact="${s.id}|approve">Применить к плану</button>`);
      acts.push(`<button class="btn warn small" data-swact="${s.id}|reject">Отклонить</button>`);
      acts.push(`<button class="btn ghost small" data-swact="${s.id}|cancel">Отозвать</button>`);
    }else acts.push(`<button class="btn ghost tiny" data-swact="${s.id}|del">Удалить из истории</button>`);""",
          """    if(s.status==='lead_review'){   /* 3.64: шаг бригадира */
      acts.push(`<button class="btn small" data-swact="${s.id}|leadok" title="Подтверждение бригадира — шаг 3.64">★ Подтвердить бригадиром</button>`);
      acts.push(`<button class="btn warn small" data-swact="${s.id}|leadno">Отклонено бригадиром</button>`);
      acts.push(`<button class="btn ghost small" data-swact="${s.id}|cancel">Отозвать</button>`);
    }else if(s.status==='new'||s.status==='agreed'){
      acts.push(`<button class="btn small" data-swact="${s.id}|approve">Применить к плану</button>`);
      acts.push(`<button class="btn warn small" data-swact="${s.id}|reject">Отклонить</button>`);
      acts.push(`<button class="btn ghost small" data-swact="${s.id}|cancel">Отозвать</button>`);
    }else acts.push(`<button class="btn ghost tiny" data-swact="${s.id}|del">Удалить из истории</button>`);""", 'swap acts lead')
    c.rep("""        <div class="field" style="margin:0"><label>Сотрудник</label><select id="swapEmp" class="inp"></select></div>
      </div>
      <div id="swapBox"></div>""",
          """        <div class="field" style="margin:0"><label>Сотрудник</label><select id="swapEmp" class="inp"></select></div>
        <label class="chkrow" style="margin:0;align-self:flex-end" title="3.64: после согласия напарника обмен подтверждает бригадир (★), если у участника есть бригада с бригадиром"><input type="checkbox" id="leadApproveChk"> одобрение бригадиром</label>
      </div>
      <div id="swapBox"></div>""", 'lead toggle ui')
    c.rep("""  bind('swapFilter','change',renderSwaps);
  bind('swapEmp','change',()=>{if($('swapFilter').value==='emp')renderSwaps()});""",
          """  bind('swapFilter','change',renderSwaps);
  bind('swapEmp','change',()=>{if($('swapFilter').value==='emp')renderSwaps()});
  const lac=$('leadApproveChk');   /* 3.64: одобрение бригадиром */
  if(lac){lac.checked=!!(state.settings&&state.settings.leadApprove);lac.onchange=()=>{state.settings=state.settings||{};state.settings.leadApprove=lac.checked;save(true);renderSwaps();try{audit('Одобрение обменов бригадиром '+(lac.checked?'включено':'выключено'),'settings.leadApprove='+lac.checked,'swap')}catch(e){}toast(lac.checked?'Одобрение обменов бригадиром включено (3.64)':'Одобрение бригадиром выключено','ok')};}""", 'lead toggle bind')
    c.rep("""    {ic:'🔁',title:'ICS round-trip: дифф экспорта с планом',hint:'импорт · 3.63',run:()=>{showTab('plan');setTimeout(()=>openIcsImport(),250)}},""",
          """    {ic:'🔁',title:'ICS round-trip: дифф экспорта с планом',hint:'импорт · 3.63',run:()=>{showTab('plan');setTimeout(()=>openIcsImport(),250)}},
    {ic:'🔰',title:'Одобрение обменов бригадиром (вкл/выкл)',hint:'обмены · 3.64',run:()=>{showTab('swap');setTimeout(()=>{const c=$('leadApproveChk');if(c&&c.onchange){c.checked=!c.checked;c.onchange()}},300)}},""", 'palette 364')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.63 — ICS round-trip (двусторонняя синхронизация)</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.64 — одобрение обменов бригадиром</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Флажок «одобрение бригадиром»</b> в карточке «Обмен сменами и подмены» (канон <code>state.settings.leadApprove</code>, по умолчанию выключен — прежний маршрут «создана → согласие напарника → решение руководителя → применено» не меняется).</li>
        <li>Когда включён: после согласия напарника заявка с участием сотрудника бригады, у которой есть бригадир (3.59), получает статус <b>«Согласовано · ждёт бригадира (★)»</b>; «Применить к плану» блокируется до подтверждения (с записью в аудит).</li>
        <li>Действия <b>«★ Подтвердить бригадиром»</b> и <b>«Отклонено бригадиром»</b>: запись в историю заявки и аудит, телеметрия <code>swap:lead</code>; KPI «ждут бригадира (★)» в списке заявок; статус виден в фильтре «Требующие решения».</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.63 — ICS round-trip (двусторонняя синхронизация)</div>""", 'help 364')
    c.rep("""    swapList,swapById,addSwap,swapCheck,swapApply,swapAct,renderSwaps,swapEditor,""",
          """    swapList,swapById,addSwap,swapCheck,swapApply,swapAct,renderSwaps,swapEditor,
    /* ===== 3.64: одобрение обменов бригадиром ===== */
    leadApproveOn,empBrigLead,swapNeedsLead,""", 'exports 364')

def V365(c):
    c.ver('3.65')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_365 + '\n' + c.s[i:]
    c.rep("""      const mi=$('meBrigIcs');if(mi)mi.onclick=()=>exportMyRotIcs();""",
          """      const mi=$('meBrigIcs');if(mi)mi.onclick=()=>exportMyRotIcs();
      /* 3.65: панель бригадира — сводка бригады для роли lead */
      if((myBr.roles||{})[e.id]==='lead'){
        try{
          const nowD=new Date();
          const d0=(nowD.getFullYear()===y&&nowD.getMonth()+1===m)?nowD.getDate():1;
          const LP=leadPanelData(myBr.id,y,m,d0);
          if(LP){
            box.insertAdjacentHTML('afterbegin',leadPanelHtml(LP));
            const gs=$('meLeadSwaps');if(gs)gs.onclick=()=>{showTab('swap');setTimeout(()=>{const f=$('swapFilter');if(f)f.value='active';renderSwaps();const sb=$('swapBox');if(sb&&sb.scrollIntoView)sb.scrollIntoView({behavior:'smooth',block:'start'})},250)};
            const gv=$('meLeadVed');if(gv)gv.onclick=()=>printBrigadeSheet();
            try{teleHit('lead:panel')}catch(e2){}
          }
        }catch(e2){}
      }""", 'lead panel ui')
    c.rep("""    {ic:'🔰',title:'Одобрение обменов бригадиром (вкл/выкл)',hint:'обмены · 3.64',run:()=>{showTab('swap');setTimeout(()=>{const c=$('leadApproveChk');if(c&&c.onchange){c.checked=!c.checked;c.onchange()}},300)}},""",
          """    {ic:'🔰',title:'Одобрение обменов бригадиром (вкл/выкл)',hint:'обмены · 3.64',run:()=>{showTab('swap');setTimeout(()=>{const c=$('leadApproveChk');if(c&&c.onchange){c.checked=!c.checked;c.onchange()}},300)}},
    {ic:'👷',title:'Панель бригадира («Мой месяц»)',hint:'самообслуживание · 3.65',run:()=>{showTab('me');setTimeout(()=>{const c=$('meLeadCard');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},300)}},""", 'palette 365')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.64 — одобрение обменов бригадиром</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.65 — панель бригадира</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>«Мой месяц» → «Панель бригадира»</b>: карточка для сотрудника с ролью lead (3.59) — KPI «дежурят сегодня / отсутствуют / на ротации / человек в бригаде» и полоса «неделя: дежурных по дням».</li>
        <li><b>Заявки бригады</b>: активные обмены и подмены с участием бригады со статусами, счётчик «ждут вашего ★-подтверждения» (3.64); кнопки «⇄ Открыть обмены» (переход на вкладку с фильтром «Требующие решения») и «🖨 Ведомость бригады» (печать 3.36).</li>
        <li>Чистая математика <code>leadPanelData(brigId,y,m,d0)</code> доступна тестам; телеметрия <code>lead:panel</code>.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.64 — одобрение обменов бригадиром</div>""", 'help 365')
    c.rep("""    /* ===== 3.64: одобрение обменов бригадиром ===== */
    leadApproveOn,empBrigLead,swapNeedsLead,""",
          """    /* ===== 3.64: одобрение обменов бригадиром ===== */
    leadApproveOn,empBrigLead,swapNeedsLead,
    /* ===== 3.65: панель бригадира ===== */
    leadPanelData,leadPanelHtml,""", 'exports 365')

SPECS = [('3.63', V363), ('3.64', V364), ('3.65', V365)]

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
    fns = [V363, V364, V365]
    chain = [('План-табель-WFM-3.62.html', 'План-табель-WFM-3.63.html'),
             ('План-табель-WFM-3.63.html', 'План-табель-WFM-3.64.html'),
             ('План-табель-WFM-3.64.html', 'План-табель-WFM-3.65.html'),
             ('План-табель-WFM-3.62-offline.html', 'План-табель-WFM-3.63-offline.html'),
             ('План-табель-WFM-3.63-offline.html', 'План-табель-WFM-3.64-offline.html'),
             ('План-табель-WFM-3.64-offline.html', 'План-табель-WFM-3.65-offline.html')]
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
