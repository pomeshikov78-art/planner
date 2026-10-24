#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка WFM 3.37 «Сценарии ротаций и годовой баланс».
Вход: сборки 3.36; выход: План-табель-WFM-3.37.html + -offline.
Фичи: what-if «бригады против покрытия», годовой баланс бригад с
ребалансировкой по пожеланиям, ICS-экспорт ротаций."""
import sys, io

MODULE_337 = r"""/* ================= 3.37: СЦЕНАРИИ РОТАЦИЙ И ГОДОВОЙ БАЛАНС =================
   1) what-if «бригады против покрытия»: модель B бригад из состава отдела —
      покрытие мин/макс, дефицитные дни, нагрузка на человека, оптимальный вариант;
   2) годовой баланс бригад: дежурства за год, конфликты с пожеланиями «не ставить»,
      попадания в «предпочтительно», SD нагрузки; ребалансировка обменами между
      бригадами (план не трогает — только состав бригад);
   3) ICS-экспорт ротаций: бригады или личная ротация сотрудника в календарь. */

/* ---- what-if: B бригад из состава — покрытие и нагрузка ---- */
function rotWhatIf(patId,deptId,opt){
  opt=opt||{};
  const pat=patById(patId);if(!pat)return null;
  const pp=patternPassport(pat);if(!pp||!pp.work)return null;
  const need=opt.need!=null?+opt.need:((dept(deptId)||{}).minDuty||1);
  const es=empList(deptId).filter(e=>!e.fired&&(opt.eligible===false||e.dutyEligible!==false));
  const S=es.length,N=pp.N;
  if(!S)return null;
  const y=opt.y||cur.y,m=opt.m||cur.m,DIM=dim(y,m);
  const base=`${y}-${pad2(m)}-01`;
  const rows=[];
  for(let B=1;B<=Math.min(S,N);B++){
    const offs=fanOffsets(N,B);
    const sizes=Array.from({length:B},(_,i)=>Math.floor(S/B)+((S%B)>i?1:0));
    let covMin=Infinity,covMax=0;
    for(let i=0;i<N;i++){
      let c=0;
      offs.forEach((o,bi)=>{if(patternIsWork(pp.seq[(i+o)%N]))c+=sizes[bi]});
      covMin=Math.min(covMin,c);covMax=Math.max(covMax,c);
    }
    let defDays=0;
    for(let d=1;d<=DIM;d++){
      const idx=patternIndex(pat,base,y,m,d);
      let c=0;
      offs.forEach((o,bi)=>{if(patternIsWork(pp.seq[(idx+o)%N]))c+=sizes[bi]});
      if(c<need)defDays++;
    }
    rows.push({B,size:sizes[0],sizes,covMin,covMax,defDays,feasible:covMin>=need,
      dutyPerPerson:Math.round(pp.work/N*DIM*10)/10,
      hoursPerson:Math.round(pp.hoursMonth*10)/10});
  }
  const best=rows.filter(r=>r.feasible).sort((a,b)=>(a.covMax-need)-(b.covMax-need)||a.B-b.B)[0]||null;
  return{pat,pp,need,deptId,S,N,rows,best,y,m,staffNeed:Math.ceil(need*pp.N/pp.work)};
}
function whatIfCsvDl(sim){
  if(!sim){toast('Нет данных сценария','err');return}
  const rows=[['What-if ротации',sim.pat.name,(dept(sim.deptId)||{}).name||'',MUP[sim.m-1]+' '+sim.y,'минимум в сутки',sim.need,'штамп',stampPlain('plan')],[],
    ['Бригад','Размер бригады','Покрытие мин','Покрытие макс','Дефицитных дней','Дежурств на чел.','Часов на чел./мес','Без дефицита']];
  sim.rows.forEach(r=>rows.push([r.B,r.size,r.covMin,r.covMax,r.defDays,r.dutyPerPerson,r.hoursPerson,r.feasible?'да':'нет']));
  downloadCsv('chto-esli-rotaciya-'+(sim.deptId||'all')+'-'+mkOf(sim.y,sim.m)+'.csv',rows);
  audit('Выгрузка what-if',`${sim.pat.name} · ${(dept(sim.deptId)||{}).name||''} · CSV`,'whatif');
  try{teleHit('rot:whatif:csv')}catch(e){}
  toast('What-if выгружен в CSV','ok');
}
function openWizardPreset(o){
  o=o||{};
  patternWizard();
  setTimeout(()=>{
    const b=$('modalBox');if(!b)return;
    /* сначала шаблон/отдел (их change пересчитывает авто-бригады), затем бригада/минимум */
    if(o.patId){const el=b.querySelector('#pwPat');if(el)el.value=o.patId}
    if(o.deptId){const el=b.querySelector('#pwDept');if(el)el.value=o.deptId}
    ['pwPat','pwDept'].forEach(id=>{
      const el=b.querySelector('#'+id);if(el)el.dispatchEvent(new Event('change'))});
    if(o.brig){const el=b.querySelector('#pwBrig');if(el)el.value=o.brig}
    if(o.need!=null){const el=b.querySelector('#pwNeed');if(el)el.value=o.need}
    ['pwNeed','pwBrig'].forEach(id=>{
      const el=b.querySelector('#'+id);if(el)el.dispatchEvent(new Event('change'))});
  },160);
}
function openRotWhatIf(){
  try{teleHit('rot:whatif')}catch(e){}
  if(!state.departments.length){toast('Нет подразделений','err');return}
  const depOpts=state.departments.map(d=>`<option value="${d.id}">${esc(d.name)}${d.minDuty?` · мин ${d.minDuty}/сут`:''}</option>`).join('');
  const patOpts=(state.patterns||[]).map(p=>`<option value="${p.id}">${esc(p.name)} · ${esc(p.seq)}</option>`).join('');
  openModal({title:'🧮 What-if ротации: бригады против покрытия',wide:true,body:`
    <div class="frow" style="flex-wrap:wrap;gap:8px">
      <div class="field" style="flex:1.4;margin:0"><label>Шаблон ротации</label><select class="inp" id="wiPat" aria-label="Шаблон для сценария">${patOpts}</select></div>
      <div class="field" style="flex:1;margin:0"><label>Подразделение</label><select class="inp" id="wiDept" aria-label="Подразделение сценария">${depOpts}</select></div>
      <div class="field" style="margin:0"><label>Минимум в сутки</label><input type="number" class="inp" id="wiNeed" min="0" max="50" value="1" style="max-width:88px" aria-label="Минимум покрытия в сутки"></div>
    </div>
    <div id="wiBody" style="margin-top:10px"></div>`,
    buttons:`<button class="btn ghost" data-cwi>Закрыть</button><button class="btn ghost" id="wiCsv" title="Таблица сценариев в CSV со штампом">⇩ CSV</button>`,
    onMount(b){
      let sim=null;
      const redraw=()=>{
        sim=rotWhatIf(b.querySelector('#wiPat').value,b.querySelector('#wiDept').value,{need:+b.querySelector('#wiNeed').value||0});
        const box=b.querySelector('#wiBody');
        if(!sim||!sim.rows.length){box.innerHTML='<div class="status err" style="margin-top:0">Нет сотрудников в подразделении или шаблон пуст.</div>';return}
        box.innerHTML=`<div style="margin-top:4px">${sim.best
          ?`<span class="pill g">оптимум: ${fmtStd(sim.best.B,{unit:'бриг'})} — покрытие ${fmtStd(sim.best.covMin)}–${fmtStd(sim.best.covMax)} при минимуме ${fmtStd(sim.need)} без дефицита</span>`
          :`<span class="pill r">варианта без дефицита нет — нужен штат ≥ ${fmtStd(sim.staffNeed,{unit:'чел'})} или другой шаблон</span>`}
          <span class="pill">штат: ${fmtStd(sim.S,{unit:'чел'})}</span>
          <span class="pill" title="Цикл / рабочих дней × минимум">нужно человек на минимум ${fmtStd(sim.need)}: ${fmtStd(sim.staffNeed,{unit:'чел'})}</span></div>
        <div class="scroll-x" style="max-height:44vh;overflow:auto;margin-top:8px"><table class="rtbl" role="table" aria-label="Сценарии числа бригад"><thead><tr><th class="n">Бригад</th><th class="n">Размер бригады</th><th class="n">Покрытие мин–макс</th><th class="n">Дефицитных дней в месяце</th><th class="n">Дежурств на чел.</th><th class="n">Часов на чел./мес</th><th></th></tr></thead><tbody>
        ${sim.rows.map(r=>`<tr${sim.best&&r.B===sim.best.B?' style="background:color-mix(in srgb,var(--green) 9%,var(--card))"':''}>
          <td class="n"><b>${fmtStd(r.B)}</b></td><td class="n">${fmtStd(r.size,{unit:'чел'})}</td>
          <td class="n">${fmtStd(r.covMin)}–${fmtStd(r.covMax)}</td>
          <td class="n">${r.defDays?`<span class="pill r">${fmtStd(r.defDays,{unit:'дн'})}</span>`:`<span class="pill g">0</span>`}</td>
          <td class="n">${fmtStd(r.dutyPerPerson,{dec:1})}</td><td class="n">${fmtStd(r.hoursPerson,{dec:1})}</td>
          <td>${r.feasible?`<button class="btn ghost tiny" data-wigo="${r.B}" title="Открыть мастер ротаций с этими параметрами">принять</button>`:''}</td></tr>`).join('')}
        </tbody></table></div>
        <div class="hint" style="margin-top:8px">Модель: состав делится на B бригад round-robin, смещения фаз ⌊i·цикл/B⌋; покрытие суток = сумма размеров дежурящих бригад; нагрузка на человека определяется только шаблоном. «Принять» открывает мастер ротаций с готовыми параметрами.</div>`;
        box.querySelectorAll('[data-wigo]').forEach(el=>el.onclick=()=>{
          const B=+el.dataset.wigo;
          closeModal();
          openWizardPreset({patId:sim.pat.id,deptId:sim.deptId,brig:B,need:sim.need});
        });
      };
      b.querySelector('[data-cwi]').onclick=closeModal;
      b.querySelector('#wiCsv').onclick=()=>whatIfCsvDl(sim);
      ['wiPat','wiDept','wiNeed'].forEach(id=>{
        const el=b.querySelector('#'+id);
        el.onchange=redraw;
        el.oninput=()=>{clearTimeout(el._t);el._t=setTimeout(redraw,350)};
      });
      if(state.settings.dutyDept)b.querySelector('#wiDept').value=state.settings.dutyDept;
      const dp0=dept(state.settings.dutyDept||'');
      if(dp0&&dp0.minDuty)b.querySelector('#wiNeed').value=dp0.minDuty;
      redraw();
    }});
}

/* ---- годовой баланс бригад и ребалансировка по пожеланиям ---- */
function brigadeYearSim(year){
  const bl=brigadeList().filter(b=>patById(b.patId));
  const brigades=[];const all=[];
  bl.forEach(b=>{
    const pat=patById(b.patId);
    const anchor=addDays(b.anchor||`${year}-01-01`,-(b.offset||0));
    const rows=(b.members||[]).map(id=>emp(id)).filter(e=>e&&!e.fired).map(e=>{
      let days=0,blocks=0,pref=0;
      for(let m=1;m<=12;m++)for(let d=1;d<=dim(year,m);d++){
        const c=patternCodeAt(pat,anchor,year,m,d);if(!c)continue;
        const dk=k(year,m,d);
        if(wishBlock(e.id,dk)){blocks++;continue}   /* ротация ставит в «не ставить» — конфликт */
        if(wishPref(e.id,dk))pref++;
        days++;
      }
      const r={eid:e.id,name:e.name,days,blocks,pref};
      all.push(r);return r;
    });
    brigades.push({brig:b,rows});
  });
  const mean=all.length?all.reduce((a,r)=>a+r.days,0)/all.length:0;
  const sd=all.length?Math.sqrt(all.reduce((a,r)=>a+(r.days-mean)*(r.days-mean),0)/all.length):0;
  const blocks=all.reduce((a,r)=>a+r.blocks,0);
  return{year,brigades,all,mean:Math.round(mean*10)/10,sd:Math.round(sd*10)/10,blocks,
    cost:Math.round(blocks*10+sd*10)/10};
}
function brigadeYearCsvDl(sim){
  if(!sim){toast('Нет данных','err');return}
  const rows=[['Годовой баланс бригад',String(sim.year),'среднее дежурств',sim.mean,'SD',sim.sd,'конфликтов с пожеланиями',sim.blocks,'штамп',stampPlain('plan')],[],
    ['Бригада','Сотрудник','Смещение фазы, дн','Дежурств за год','Конфликтов с «не ставить»','Попаданий в «предпочтительно»']];
  sim.brigades.forEach(g=>g.rows.forEach(r=>rows.push([g.brig.name,r.name,g.brig.offset||0,r.days,r.blocks,r.pref])));
  downloadCsv('brigady-god-'+sim.year+'.csv',rows);
  audit('Выгрузка годового баланса бригад',`${sim.year} · CSV`,'brigades');
  try{teleHit('rot:year:csv')}catch(e){}
  toast('Годовой баланс выгружен в CSV','ok');
}
function brigadeRebalance(year){
  const bl=brigadeList().filter(b=>patById(b.patId));
  if(bl.length<2)return null;
  const phases=bl.map(b=>({pat:patById(b.patId),anchor:addDays(b.anchor||`${year}-01-01`,-(b.offset||0))}));
  const eids=[];
  bl.forEach(b=>(b.members||[]).forEach(id=>{if(!eids.includes(id))eids.push(id)}));
  const emps=eids.map(id=>emp(id)).filter(e=>e&&!e.fired);
  if(emps.length!==eids.length)return null;
  const assign=eids.map(id=>bl.findIndex(b=>(b.members||[]).includes(id)));
  if(assign.some(a=>a<0))return null;
  /* матрица: сотрудник × бригада = дежурства/конфликты за год (не зависит от остальных) */
  const M=emps.map(e=>phases.map(p=>{
    let days=0,blocks=0,pref=0;
    for(let m=1;m<=12;m++)for(let d=1;d<=dim(year,m);d++){
      const c=patternCodeAt(p.pat,p.anchor,year,m,d);if(!c)continue;
      const dk=k(year,m,d);
      if(wishBlock(e.id,dk)){blocks++;continue}
      if(wishPref(e.id,dk))pref++;
      days++;
    }
    return{days,blocks,pref};
  }));
  const costOf=a=>{
    let blocks=0;const days=[];
    a.forEach((bi,i)=>{const c=M[i][bi];blocks+=c.blocks;days.push(c.days)});
    const mean=days.reduce((x,y)=>x+y,0)/days.length;
    const sd=Math.sqrt(days.reduce((x,y)=>x+(y-mean)*(y-mean),0)/days.length);
    return{blocks,sd:Math.round(sd*10)/10,total:Math.round(blocks*10+sd*10)/10};
  };
  const before=costOf(assign);
  let curC=before,moves=0;
  for(let pass=0;pass<3;pass++){
    let improved=false;
    for(let i=0;i<emps.length;i++)for(let j=i+1;j<emps.length;j++){
      if(assign[i]===assign[j])continue;
      const ti=assign[i];assign[i]=assign[j];assign[j]=ti;
      const c1=costOf(assign);
      if(c1.total<curC.total-1e-9){curC=c1;moves++;improved=true}
      else{assign[j]=assign[i];assign[i]=ti}
    }
    if(!improved)break;
  }
  return{year,eids,emps,assign,before,after:curC,moves};
}
function brigadeRebalanceApply(res,year){
  if(!res||!res.moves)return 0;
  const bl=brigadeList();
  bl.forEach(b=>{b.members=[]});
  res.eids.forEach((id,i)=>{const b=bl[res.assign[i]];if(b)b.members.push(id)});
  save(true);
  try{renderBrigades()}catch(e){}
  audit('Ребалансировка бригад',`${year}: обменов ${res.moves} · конфликты с пожеланиями ${res.before.blocks} → ${res.after.blocks} · SD нагрузки ${res.before.sd} → ${res.after.sd}`,'brigades');
  try{teleHit('rot:rebalance')}catch(e){}
  toast(`Ребаланс: обменов ${res.moves} · конфликты ${res.before.blocks} → ${res.after.blocks} · SD ${res.before.sd} → ${res.after.sd}`,'ok');
  return res.moves;
}
function openBrigadeYear(year0){
  try{teleHit('rot:year')}catch(e){}
  const bl=brigadeList();
  if(!bl.length){toast('Сохранённых бригад нет — создайте в мастере ротаций','err');return}
  const y0=year0||cur.y;
  openModal({title:'⚖ Бригады: годовой баланс и пожелания',wide:true,body:`
    <div class="frow">
      <div class="field" style="margin:0;max-width:140px"><label>Год</label><select class="inp" id="byYear" aria-label="Год баланса">${Array.from({length:YMAX-YMIN+1},(_,i)=>YMIN+i).map(v=>`<option ${v===y0?'selected':''}>${v}</option>`).join('')}</select></div>
      <div class="hint" style="align-self:flex-end;padding-bottom:6px">Дежурства и конфликты с пожеланиями «не ставить» считаются по фазам бригад за год без записи в план.</div>
    </div>
    <div id="byBody" style="margin-top:10px"></div>`,
    buttons:`<button class="btn ghost" data-cby>Закрыть</button><button class="btn ghost" id="byCsv" title="Годовой баланс по сотрудникам в CSV">⇩ CSV</button><button class="btn" id="byGo" title="Обмены сотрудниками между бригадами: меньше конфликтов с пожеланиями, ровнее годовая нагрузка">⚖ Ребалансировать</button>`,
    onMount(b){
      let sim=null;
      const redraw=()=>{
        const year=+b.querySelector('#byYear').value;
        sim=brigadeYearSim(year);
        const box=b.querySelector('#byBody');
        if(!sim.brigades.length){box.innerHTML='<div class="status" style="margin-top:0">Нет бригад с существующими шаблонами.</div>';return}
        box.innerHTML=`<div style="margin-top:4px"><span class="pill">среднее дежурств на человека: ${fmtStd(sim.mean,{dec:1})}</span>
          <span class="pill ${sim.sd>4?'a':'g'}" title="Среднеквадратичное отклонение дежурств за год по составу">разброс (SD): ${fmtStd(sim.sd,{dec:1})}</span>
          <span class="pill ${sim.blocks?'r':'g'}">конфликтов с «не ставить»: ${fmtStd(sim.blocks,{unit:'сл'})}</span></div>
        <div class="scroll-x" style="max-height:42vh;overflow:auto;margin-top:8px"><table class="rtbl" role="table" aria-label="Годовой баланс бригад"><thead><tr><th>Бригада</th><th>Фаза</th><th class="n">Состав</th><th class="n">Дежурств на чел. (мин–макс)</th><th class="n">Конфликтов с «не ставить»</th><th class="n">Попаданий в «предпочтительно»</th></tr></thead><tbody>
        ${sim.brigades.map(g=>{
          const ds=g.rows.map(r=>r.days),blks=g.rows.reduce((a,r)=>a+r.blocks,0),prf=g.rows.reduce((a,r)=>a+r.pref,0);
          return `<tr><td><b>${esc(g.brig.name)}</b></td><td>${fmtStd(g.brig.offset||0,{unit:'дн'})}</td><td class="n">${fmtStd(g.rows.length,{unit:'чел'})}</td>
          <td class="n">${ds.length?fmtStd(Math.min.apply(null,ds))+'–'+fmtStd(Math.max.apply(null,ds)):'—'}</td>
          <td class="n">${blks?`<span class="pill r">${fmtStd(blks)}</span>`:`<span class="pill g">0</span>`}</td>
          <td class="n">${prf?`<span class="pill g">${fmtStd(prf)}</span>`:fmtStd(0)}</td></tr>`}).join('')}
        </tbody></table></div>
        <div class="hint" style="margin-top:8px">Ребалансировка меняет только состав бригад (обмены сотрудниками между фазами), снижая конфликты с пожеланиями «не ставить» и разброс годовой нагрузки; отметки плана не трогаются.</div>`;
      };
      b.querySelector('[data-cby]').onclick=closeModal;
      b.querySelector('#byYear').onchange=redraw;
      b.querySelector('#byCsv').onclick=()=>brigadeYearCsvDl(sim);
      b.querySelector('#byGo').onclick=()=>{
        const year=+b.querySelector('#byYear').value;
        const res=brigadeRebalance(year);
        if(!res){toast('Ребаланс недоступен: бригад меньше двух или есть сотрудники вне бригад','err');return}
        if(!res.moves){toast('Текущий состав уже оптимален для '+year+' по пожеланиям и балансу','ok');return}
        confirmBox(`Обменять сотрудников между бригадами: ${fmtStd(res.moves,{unit:'обм'})}.<br>Конфликты с «не ставить»: <b>${fmtStd(res.before.blocks)} → ${fmtStd(res.after.blocks)}</b>; разброс нагрузки (SD): <b>${fmtStd(res.before.sd,{dec:1})} → ${fmtStd(res.after.sd,{dec:1})}</b>.<br>Отметки плана не изменяются — только состав бригад в общей базе.`,()=>{
          brigadeRebalanceApply(res,year);
          closeModal();
          openBrigadeYear(year);
        },'Да, ребалансировать');
      };
      redraw();
    }});
}

/* ---- ICS-экспорт ротаций ---- */
function exportBrigadeIcs(brigIds,year,name,onlyEid){
  const bl=brigadeList().filter(b=>brigIds.includes(b.id));
  if(!bl.length){toast('Бригады не найдены','err');return 0}
  const stamp=new Date().toISOString().replace(/[-:]/g,'').split('.')[0]+'Z';
  const L=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//PlanTabel//RU','CALSCALE:GREGORIAN',
    'X-WR-CALNAME:'+state.org+' · ротации бригад '+year];
  let n=0;
  bl.forEach(b=>{
    const pat=patById(b.patId);if(!pat)return;
    const anchor=addDays(b.anchor||`${year}-01-01`,-(b.offset||0));
    (b.members||[]).forEach(eid=>{
      if(onlyEid&&eid!==onlyEid)return;
      const e=emp(eid);if(!e)return;
      for(let m=1;m<=12;m++)for(let d=1;d<=dim(year,m);d++){
        const c=patternCodeAt(pat,anchor,year,m,d);if(!c)continue;
        const dk=k(year,m,d);
        if(wishBlock(eid,dk))continue;   /* пожелание «не ставить» — событие не публикуется */
        const nd=addDays(dk,1);
        L.push('BEGIN:VEVENT',
          `UID:${b.id}-${eid}-${dk}@plantabel`,
          'DTSTAMP:'+stamp,
          'DTSTART;VALUE=DATE:'+dk.split('-').join(''),
          'DTEND;VALUE=DATE:'+nd.split('-').join(''),
          `SUMMARY:${esc(c)} · ${e.name} (${b.name})`,
          'DESCRIPTION:'+(reason(c)?esc(reason(c).name):''),
          'END:VEVENT');
        n++;
      }
    });
  });
  L.push('END:VCALENDAR');
  download(name+'.ics',L.join('\r\n'),'text/calendar');
  audit('Экспорт ротаций в ICS',`${year} · бригад ${bl.length}${onlyEid?' · личный':''} · событий ${n}`,'brigades');
  try{teleHit('rot:ics')}catch(e){}
  toast('ICS выгружен: событий '+n+' — откройте в календаре','ok');
  return n;
}
function exportMyRotIcs(){
  const e=meEmp();
  if(!e){toast('Сначала отметьте, кто вы (вкладка «Мой месяц»)','err');return 0}
  const b=brigadeList().find(x=>(x.members||[]).includes(e.id));
  if(!b){toast('Вы не входите ни в одну сохранённую бригаду','err');return 0}
  const y=+(meMk().slice(0,4))||cur.y;
  return exportBrigadeIcs([b.id],y,'rotaciya-'+(e.tab||e.id)+'-'+y,e.id);
}

"""

def build(path):
    with io.open(path, 'r', encoding='utf-8') as f:
        s = f.read()
    orig = len(s)

    def rep(old, new, label):
        nonlocal s
        n = s.count(old)
        if n != 1:
            raise SystemExit('ANCHOR FAIL [%s] in %s: %d' % (label, path, n))
        s = s.replace(old, new, 1)

    # версии
    rep('<title>План-табель служебной деятельности · WFM 3.36</title>',
        '<title>План-табель служебной деятельности · WFM 3.37</title>', 'title')
    rep("geoPrev,ver:'3.36',", "geoPrev,ver:'3.37',", 'app.ver')
    rep("const ver=(window.APP&&APP.ver)||'3.36';",
        "const ver=(window.APP&&APP.ver)||'3.37';", 'ver fallback')

    # карточка бригад: кнопки годового баланса, ICS и what-if
    rep("""        <button class="btn ghost small wide" id="btnBrigPrint" style="margin-top:6px" hidden>🖨 Бригадная ведомость (печать)</button>""",
        """        <button class="btn ghost small wide" id="btnBrigPrint" style="margin-top:6px" hidden>🖨 Бригадная ведомость (печать)</button>
        <button class="btn ghost small wide" id="btnBrigYear" style="margin-top:6px" hidden>⚖ Годовой баланс и пожелания</button>
        <button class="btn ghost small wide" id="btnBrigIcs" style="margin-top:6px" hidden>⤓ ICS ротации бригад (год)</button>
        <button class="btn ghost small wide" id="btnRotWhatIf" title="Сценарии: сколько бригад нужно при минимуме N (3.37)">🧮 What-if: бригады против покрытия</button>""", 'brig card buttons')

    # renderBrigades: видимость и биндинги новых кнопок
    rep("""  const bp=$('btnBrigPrint');if(bp){bp.hidden=!bl.length;bp.onclick=()=>printBrigadeSheet()}""",
        """  const bp=$('btnBrigPrint');if(bp){bp.hidden=!bl.length;bp.onclick=()=>printBrigadeSheet()}
  const by=$('btnBrigYear');if(by){by.hidden=!bl.length;by.onclick=()=>openBrigadeYear()}
  const bi=$('btnBrigIcs');if(bi){bi.hidden=!bl.length;bi.onclick=()=>exportBrigadeIcs(bl.map(x=>x.id),cur.y,'brigady-rotacii-'+cur.y)}
  const bw=$('btnRotWhatIf');if(bw)bw.onclick=()=>openRotWhatIf();""", 'brig bindings')

    # «Моя бригада»: кнопка личного ICS
    rep('''        <div class="hint" style="margin-top:6px">Цикл продолжается через границу месяца без сбоя: фаза считается от даты-якоря бригады. Состав бригады обновляет табельщик.</div></div>`);''',
        '''        <div class="hint" style="margin-top:6px">Цикл продолжается через границу месяца без сбоя: фаза считается от даты-якоря бригады. Состав бригады обновляет табельщик.</div>
        <div class="mini" style="margin-top:8px;display:flex;gap:6px"><button class="btn ghost small" id="meBrigIcs" title="Личная ротация за год в календарь (ICS)">⤓ ICS моей ротации</button></div></div>`);
      const mi=$('meBrigIcs');if(mi)mi.onclick=()=>exportMyRotIcs();''', 'me ics button')

    # модуль 3.37 перед секцией 9
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = s.find(m9)
    if i < 0 or s.find(m9, i+1) >= 0: raise SystemExit('marker 9 fail')
    s = s[:i] + MODULE_337 + '\n' + s[i:]

    # палитра
    rep("""    {ic:'🖨',title:'Бригадная ведомость (печать)',hint:'вывод · 3.36',run:()=>{showTab('plan');setTimeout(()=>printBrigadeSheet(),300)}},""",
        """    {ic:'🖨',title:'Бригадная ведомость (печать)',hint:'вывод · 3.36',run:()=>{showTab('plan');setTimeout(()=>printBrigadeSheet(),300)}},
    {ic:'🧮',title:'What-if ротации: бригады против покрытия',hint:'планирование · 3.37',run:()=>{showTab('plan');setTimeout(()=>openRotWhatIf(),250)}},
    {ic:'⚖',title:'Годовой баланс бригад и ребалансировка',hint:'планирование · 3.37',run:()=>{showTab('plan');setTimeout(()=>openBrigadeYear(),250)}},
    {ic:'📅',title:'ICS моей ротации на год',hint:'самообслуживание · 3.37',run:()=>{showTab('me');setTimeout(()=>exportMyRotIcs(),300)}},""", 'palette 337')

    # справка 3.37
    rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.36 — конструктор ротаций, бригады и доктор покрытия</div>""",
        """      <div class="lbl" style="margin-top:12px">Новое в версии 3.37 — сценарии ротаций и годовой баланс</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>What-if «бригады против покрытия»</b> («🧮» в карточке «Бригады» и палитра): таблица сценариев B = 1…min(штат, цикл) — покрытие мин/макс в сутки, дефицитные дни месяца, дежурства и часы на человека; подсветка оптимума (без дефицита, минимальный избыток), строка «нужно человек на минимум N» (цикл / рабочих × N); «принять» открывает мастер ротаций с готовыми параметрами; выгрузка сценариев в CSV со штампом.</li>
        <li><b>Годовой баланс бригад</b> («⚖»): по фазам бригад за год считаются дежурства на человека (мин–макс по составу), конфликты с пожеланиями «не ставить» (ротация ставит смену в запрещённую дату) и попадания в «предпочтительно»; сводка: среднее, разброс (SD), конфликты. <b>Ребалансировка</b> — жадные обмены сотрудниками между бригадами (до 3 проходов, состав и размеры сохраняются), снижают конфликты и SD; меняет только <code>state.brigades</code>, отметки плана не трогает; отчёт по сотрудникам — в CSV.</li>
        <li><b>ICS-экспорт ротаций</b>: «⤓ ICS ротации бригад (год)» в карточке «Бригады» и «⤓ ICS моей ротации» в «Мой месяц → Моя бригада» (а также палитра) — событийный календарь VCALENDAR/VEVENT (целодневные события на каждую смену, UID стабилен, SUMMARY «код · ФИО (бригада)»); даты, попавшие в пожелание «не ставить», не публикуются.</li>
        <li><b>НСИ и телеметрия</b>: виджеты <code>rotWhatIf</code> и <code>brigYear</code> в паспорте виджетов; what-if и годовой баланс — интерактивные отчёты 5/5 в реестре; счётчики pt.tele: <code>rot:whatif</code>, <code>rot:whatif:csv</code>, <code>rot:year</code>, <code>rot:year:csv</code>, <code>rot:rebalance</code>, <code>rot:ics</code>.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.36 — конструктор ротаций, бригады и доктор покрытия</div>""", 'help 337')

    # реестры НСИ
    rep("""  {id:'covWizard',tab:'plan',name:'Мастер ротаций: предпросмотр покрытия',form:'календарь покрытия по дням (веер по бригадам) с подсветкой дефицита',source:'канон: state.patterns, минимум подразделения'}
];""",
        """  {id:'covWizard',tab:'plan',name:'Мастер ротаций: предпросмотр покрытия',form:'календарь покрытия по дням (веер по бригадам) с подсветкой дефицита',source:'канон: state.patterns, минимум подразделения'},
  {id:'rotWhatIf',tab:'plan',name:'What-if ротации: бригады против покрытия',form:'таблица сценариев B бригад: покрытие мин/макс, дефицит, нагрузка; оптимум подсвечен',source:'канон: state.patterns, штат подразделения, минимум'},
  {id:'brigYear',tab:'plan',name:'Годовой баланс бригад',form:'таблица бригад за год: дежурства мин–макс, конфликты с пожеланиями, SD; ребалансировка',source:'канон: state.brigades, пожелания, производственный календарь'}
];""", 'widget registry 337')
    rep("""  {id:'covDoctor',name:'Доктор покрытия',tab:'plan',crit:{filter:1,drill:1,live:1,insight:1,export:1},note:'3.36: фильтры подразделения/минимума/режима, детализация до кандидата и дня, живой пересчёт, вывод-календарь дефицитов, экспорт CSV со штампом'}];""",
        """  {id:'covDoctor',name:'Доктор покрытия',tab:'plan',crit:{filter:1,drill:1,live:1,insight:1,export:1},note:'3.36: фильтры подразделения/минимума/режима, детализация до кандидата и дня, живой пересчёт, вывод-календарь дефицитов, экспорт CSV со штампом'},
  {id:'rotWhatIf',name:'What-if ротации',tab:'plan',crit:{filter:1,drill:1,live:1,insight:1,export:1},note:'3.37: фильтры шаблон/подразделение/минимум, детализация до сценария B, живой пересчёт, оптимум-вывод, CSV со штампом'},
  {id:'brigYear',name:'Годовой баланс бригад',tab:'plan',crit:{filter:1,drill:1,live:1,insight:1,export:1},note:'3.37: фильтр-год, детализация до бригады и сотрудника, живой пересчёт, вывод по конфликтам/SD, CSV, действие-ребаланс'}];""", 'interactive 337')

    # экспорт APP
    rep("""    coverageCsvDl,printBrigadeSheet,""",
        """    coverageCsvDl,printBrigadeSheet,
    /* ===== 3.37: сценарии ротаций и годовой баланс ===== */
    rotWhatIf,whatIfCsvDl,openWizardPreset,openRotWhatIf,
    brigadeYearSim,brigadeYearCsvDl,brigadeRebalance,brigadeRebalanceApply,openBrigadeYear,
    exportBrigadeIcs,exportMyRotIcs,""", 'app exports 337')

    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(s)
    print('OK %s: %d -> %d (+%d)' % (path, orig, len(s), len(s)-orig))

if __name__ == '__main__':
    for p in sys.argv[1:]:
        build(p)
