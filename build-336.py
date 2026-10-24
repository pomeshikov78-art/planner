#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка WFM 3.36 «Конструктор ротаций, бригады и доктор покрытия».
Применяет одинаковые правки к онлайн- и офлайн-сборке (код приложения в них идентичен)."""
import sys, io

def build(path):
    with io.open(path, 'r', encoding='utf-8') as f:
        s = f.read()
    orig_len = len(s)

    def rep(old, new, label):
        nonlocal s
        n = s.count(old)
        if n != 1:
            raise SystemExit('ANCHOR FAIL [%s] in %s: found %d occurrences' % (label, path, n))
        s = s.replace(old, new, 1)

    def span(start_marker, end_marker, new, label, include_end=False):
        nonlocal s
        i = s.find(start_marker)
        if i < 0: raise SystemExit('SPAN START FAIL [%s] in %s' % (label, path))
        if s.find(start_marker, i+1) >= 0: raise SystemExit('SPAN START AMBIGUOUS [%s] in %s' % (label, path))
        j = s.find(end_marker, i)
        if j < 0: raise SystemExit('SPAN END FAIL [%s] in %s' % (label, path))
        s = s[:i] + new + (s[j:] if not include_end else s[j:])

    # ---- R1: заголовок ----
    rep('<title>План-табель служебной деятельности · WFM 3.35</title>',
        '<title>План-табель служебной деятельности · WFM 3.36</title>', 'title')

    # ---- R2: версия в экспорте APP ----
    rep("geoPrev,ver:'3.35',", "geoPrev,ver:'3.36',", 'app.ver')

    # ---- R3: фолбэк версии в докладе ----
    rep("const ver=(window.APP&&APP.ver)||'3.35';",
        "const ver=(window.APP&&APP.ver)||'3.36';", 'slides ver fallback')

    # ---- R4: CSS ----
    rep(".pwcell.today{border-color:var(--navy);box-shadow:0 0 0 2px color-mix(in srgb,var(--navy) 22%,transparent)}",
        """.pwcell.today{border-color:var(--navy);box-shadow:0 0 0 2px color-mix(in srgb,var(--navy) 22%,transparent)}
/* ===== 3.36: конструктор ротаций, бригады и доктор покрытия ===== */
.rot-chip{display:inline-block;min-width:22px;text-align:center;border:1px solid color-mix(in srgb,var(--c,var(--slate)) 45%,var(--line));border-radius:4px;background:color-mix(in srgb,var(--c,var(--slate)) 14%,var(--card));color:var(--c,var(--slate));font-family:var(--f-mono);font-size:10px;line-height:17px;padding:0 4px;margin:1px}
.rot-chip.rest{opacity:.62}
.rot-strip{flex-basis:100%;display:flex;flex-wrap:wrap;gap:1px;margin-top:3px}
.rot-badges{flex-basis:100%;display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.patrow{align-content:flex-start;row-gap:2px}
.covstrip{display:flex;flex-wrap:wrap;gap:2px;margin-top:8px}
.covcell{min-width:27px;text-align:center;border:1px solid var(--line);border-radius:4px;background:var(--card);font-family:var(--f-mono);font-size:11px;padding:1px 2px;line-height:1.35}
.covcell em{display:block;font-style:normal;font-size:8.5px;color:var(--mut)}
.covcell.ok{background:color-mix(in srgb,var(--green) 13%,var(--card));border-color:color-mix(in srgb,var(--green) 40%,var(--line))}
.covcell.def{background:color-mix(in srgb,var(--red) 14%,var(--card));border-color:color-mix(in srgb,var(--red) 55%,var(--line));color:var(--red);font-weight:700}
.covcell.over{background:color-mix(in srgb,var(--amber) 16%,var(--card));border-color:color-mix(in srgb,var(--amber) 50%,var(--line))}
.covcell.we{opacity:.72}
.covcell.today{box-shadow:0 0 0 2px color-mix(in srgb,var(--navy) 30%,transparent)}
.candrow{display:flex;align-items:center;gap:6px;padding:3px 0;border-bottom:1px dashed var(--line2);flex-wrap:wrap}
.candrow:last-child{border-bottom:0}
.cand-chip{display:inline-block;border:1px solid var(--line);border-radius:10px;padding:0 7px;font-size:10.5px;color:var(--mut);margin:1px 0}
.cand-chip.good{color:var(--green);border-color:color-mix(in srgb,var(--green) 40%,var(--line))}
.cand-chip.bad{color:var(--red);border-color:color-mix(in srgb,var(--red) 45%,var(--line))}
#brigBox .setrow{border-bottom:1px dashed var(--line2);padding:4px 0}
@media print{.rot-chip,.covcell{border:1px solid #aaa!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}""", 'css')

    # ---- R5: кнопка «Доктор покрытия» в тулбаре планирования ----
    rep('<button class="btn ghost small" id="btnSubst" title="Подбор замещающего для отсутствующего сотрудника">🔄 Замещающий</button>',
        '<button class="btn ghost small" id="btnSubst" title="Подбор замещающего для отсутствующего сотрудника">🔄 Замещающий</button>\n        <button class="btn ghost small" id="btnCovDoc" title="Доктор покрытия: дефициты по дням и умные рекомендации (3.36)">🩺 Покрытие</button>', 'toolbar covdoc')

    # ---- R6+R7: кнопка паспорта + карточка «Бригады» в сайдбаре ----
    rep("""        <button class="btn ghost small wide" id="btnAddIntl">+ Международные ротации (Pitman, 24/48, 48/96, Kelly, ДНОВ)</button>
        <div class="hint" style="margin-top:8px">Сквозная фаза устраняет сбой ротации 1-го числа: цикл продолжается от даты-якоря. Мировая практика — Vector Scheduling, InTime, aTurnos, Kelio.</div>
      </div>""",
        """        <button class="btn ghost small wide" id="btnAddIntl">+ Международные ротации (Pitman, 24/48, 48/96, Kelly, ДНОВ)</button>
        <button class="btn ghost small wide" id="btnPatPassport" title="Паспорт выбранного шаблона: проверка цикла против норм ТК РФ (3.36)">📋 Паспорт шаблона (ТК РФ)</button>
        <div class="hint" style="margin-top:8px">Сквозная фаза устраняет сбой ротации 1-го числа: цикл продолжается от даты-якоря. Мировая практика — Vector Scheduling, InTime, aTurnos, Kelio. 3.36: паспорт проверяет среднюю неделю, серии и отдых (ст. 91, 96, 100, 110 ТК РФ).</div>
      </div>
      <div class="card" id="brigCard">
        <div class="lbl">Бригады · сохранённые ротации <span class="pill" id="brigCount">0</span></div>
        <div id="brigBox"></div>
        <button class="btn ghost small wide" id="btnBrigApplyAll" style="margin-top:6px" hidden>▶ Применить все бригады к месяцу</button>
        <button class="btn ghost small wide" id="btnBrigPrint" style="margin-top:6px" hidden>🖨 Бригадная ведомость (печать)</button>
        <div class="hint" style="margin-top:6px">3.36: бригады создаёт мастер ротаций в режиме «веер по бригадам» — фазы разведены для ровного покрытия суток. Состав хранится в общей базе и синхронизируется по ЛВС.</div>
      </div>""", 'sidebar passport+brigades')

    # ---- R8: справочники — кнопки конструктора/паспортов/экспорта ----
    rep("""        <div class="addform"><input type="text" id="newPatName" placeholder="Название" style="flex:1"><input type="text" id="newPatSeq" placeholder="Я,Я,В,В или Д1,Д1,О,О" style="flex:1.4"><button class="btn small" id="btnAddPat">Добавить</button></div>
        <div class="hint" style="margin-top:8px">Последовательность кодов через запятую; «В» — выходной (пустая ячейка). Применяется в генераторе графиков на вкладке «Планирование».</div>""",
        """        <div class="addform"><input type="text" id="newPatName" placeholder="Название" style="flex:1"><input type="text" id="newPatSeq" placeholder="Я,Я,В,В или Д1,Д1,О,О" style="flex:1.4"><button class="btn small" id="btnAddPat">Добавить</button></div>
        <div class="mini" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px">
          <button class="btn ghost small" id="btnPatConstruct" title="Собрать цикл из параметров «N рабочих / M выходных» с живой проверкой ТК">➕ Конструктор ротации</button>
          <button class="btn ghost small" id="btnPatPpAll" title="Сводная таблица: все шаблоны с вердиктом соответствия">📋 Паспорта всех шаблонов</button>
          <button class="btn ghost small" id="btnPatJson" title="Каталог шаблонов с паспортами (JSON)">⤓ JSON</button>
          <button class="btn ghost small" id="btnPatCsv" title="Каталог шаблонов с паспортами (CSV)">⇩ CSV</button>
        </div>
        <div class="hint" style="margin-top:8px">Последовательность кодов через запятую; «В» — выходной (пустая ячейка). Применяется в генераторе графиков на вкладке «Планирование». 3.36: цветная лента цикла и бейджи соответствия у каждого шаблона; «📋» — паспорт с проверкой против норм ТК РФ (ст. 91, 96, 100, 110) и включённых правил комплаенса.</div>""", 'settings buttons')

    # ---- R9: renderPatternsList — каталог 2.0 ----
    span('function renderPatternsList(){', 'function renderHolidays(){',
        """function renderPatternsList(){
  /* 3.36: каталог 2.0 — цветная лента цикла, вердикт ТК, бейджи метрик, дубль и паспорт */
  const box=$('patBox');if(!box)return;
  box.innerHTML=(state.patterns||[]).map(p=>{
    const pp=patternPassport(p),seq=patternSeq(p);
    return `
    <div class="setrow patrow">
      <input type="text" data-patname="${p.id}" value="${esc(p.name)}" style="flex:1;min-width:120px" aria-label="Название шаблона: ${esc(p.name)}">
      <input type="text" data-patseq="${p.id}" value="${esc(p.seq)}" style="flex:1.2;min-width:140px;font-family:var(--f-mono)" aria-label="Последовательность кодов: ${esc(p.seq)}">
      ${passportVerdictPill(pp)}
      <button class="x" data-patpp="${p.id}" title="Паспорт: проверка цикла против норм ТК РФ" aria-label="Паспорт шаблона ${esc(p.name)}">📋</button>
      <button class="x" data-patdup="${p.id}" title="Дублировать шаблон" aria-label="Дублировать шаблон ${esc(p.name)}">⧉</button>
      <button class="x" data-delpat="${p.id}" title="Удалить" aria-label="Удалить шаблон ${esc(p.name)}">✕</button>
      ${rotStripHtml(seq)}
      ${pp?`<span class="rot-badges">
        <span class="pill" title="Длина цикла: рабочих / выходных">цикл ${fmtStd(pp.N,{unit:'дн'})}: ${fmtStd(pp.work,{unit:'раб'})} / ${fmtStd(pp.offs,{unit:'вых'})}</span>
        <span class="pill" title="Средние часы за неделю (норма ${fmtStd(pp.norm,{unit:'ч'})})">${fmtStd(pp.hoursWeek,{dec:1,unit:'ч/нед'})}</span>
        <span class="pill" title="Самая длинная серия рабочих дней (с закольцовкой цикла)">серия ${fmtStd(pp.maxConsec,{unit:'дн'})}</span>
        ${pp.peoplePerPost>1?`<span class="pill" title="Сколько человек нужно, чтобы круглосуточно закрывать один пост">${fmtStd(pp.peoplePerPost,{dec:1,unit:'чел/пост'})}</span>`:''}
        ${pp.nightShifts?`<span class="pill" title="Ночные смены в цикле">🌙 ${fmtStd(pp.nightShifts,{unit:'шт'})} · ${fmtStd(pp.nightPct,{dec:0,pct:true})} ч</span>`:''}
        <span class="pill" title="Штат для покрытия поста: цикл / рабочие дни">${fmtStd(pp.dutyDays,{unit:'деж'})}</span>
      </span>`:''}
    </div>`}).join('')||'<div class="hint">Шаблонов нет.</div>';
}
""", 'renderPatternsList')

    # ---- R10: renderPatterns тянет бригады ----
    rep('function renderPatterns(){renderBulk()}',
        "function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){}}   /* 3.36: бригады */", 'renderPatterns')

    # ---- R11: обработчики patBox + биндинги кнопок справочника ----
    span("  $('patBox').addEventListener('change',e=>{", '/* --- горячие клавиши --- */',
        """  $('patBox').addEventListener('change',e=>{
    const t=e.target,id=t.dataset.patname||t.dataset.patseq;
    const p=(state.patterns||[]).find(x=>x.id===id);if(!p)return;
    if(t.dataset.patname)p.name=t.value.trim()||p.name;
    if(t.dataset.patseq)p.seq=t.value.trim().toUpperCase()||p.seq;
    save();renderPatternsList();renderBulk();   /* 3.36: пересчёт ленты и бейджей паспорта */
  });
  $('patBox').addEventListener('click',e=>{
    /* 3.36: каталог 2.0 — паспорт, дублирование, удаление */
    const t=e.target.closest?e.target.closest('button'):null;if(!t)return;
    if(t.dataset.patpp){openPatternPassport(t.dataset.patpp);return}
    if(t.dataset.patdup){
      const p=(state.patterns||[]).find(x=>x.id===t.dataset.patdup);if(!p)return;
      const cp=clone(p);cp.id=uid('p');cp.name=p.name+' (копия)';
      state.patterns.push(cp);save();renderPatternsList();renderBulk();
      audit('Дублирование шаблона ротации',cp.name,'patterns');toast('Шаблон дублирован: «'+cp.name+'»','ok');return}
    const id=t.dataset.delpat;if(!id)return;
    const p=(state.patterns||[]).find(x=>x.id===id);
    state.patterns=state.patterns.filter(x=>x.id!==id);save();renderPatternsList();renderBulk();
    audit('Удаление шаблона ротации',(p&&p.name)||id,'patterns');toast('Шаблон удалён')});
  $('btnAddPat').onclick=()=>{
    const n=$('newPatName').value.trim(),s=$('newPatSeq').value.trim().toUpperCase();
    if(!n||!s){toast('Укажите название и последовательность','err');return}
    /* 3.36: предупреждение о кодах, которых нет в справочнике причин */
    const miss=s.split(',').map(x=>x.trim()).filter(x=>x&&x!=='В'&&!reason(x));
    state.patterns=state.patterns||[];state.patterns.push({id:uid('p'),name:n,seq:s});
    $('newPatName').value='';$('newPatSeq').value='';save();renderPatternsList();renderBulk();
    audit('Добавление шаблона ротации',n+' · '+s,'patterns');
    if(miss.length)toast('Шаблон добавлен, но кодов нет в справочнике: '+miss.join(', ')+' — применение заблокировано до их добавления','err');
    else toast('Шаблон добавлен','ok')};
  /* 3.36: конструктор, сводные паспорта и экспорт каталога шаблонов */
  bindClick('btnPatConstruct',openPatternConstructor);
  bindClick('btnPatPpAll',openAllPassports);
  bindClick('btnPatJson',patternsJsonDl);
  bindClick('btnPatCsv',patternsCsvDl);
  """, 'patBox handlers')

    # ---- R12: мастер ротаций — веер по бригадам ----
    span('function patternWizard(){', 'function resolvePwEmps(b){',
        """function patternWizard(){
  /* 3.36: режим «веер по бригадам» — фазы распределяются по бригадам для ровного покрытия суток */
  const depOpts='<option value="all">все подразделения</option>'+state.departments.map(d=>`<option value="${d.id}">${esc(d.name)}${d.minDuty?` (мин ${d.minDuty}/сут)`:''}</option>`).join('');
  const patOpts=(state.patterns||[]).map(p=>`<option value="${p.id}">${esc(p.name)} · ${esc(p.seq)}${p.intl?' ['+esc(p.intl)+']':''}</option>`).join('');
  openModal({title:'Мастер ротаций (сквозная фаза · бригады)',wide:true,
    body:`<div class="hint" style="margin-top:0">Ротация рассчитывается от <b>даты-якоря</b>, поэтому цикл продолжается через границу месяца без сбоя фазы. 3.36: режим <b>«веер по бригадам»</b> разводит фазу (смещение i-й бригады = ⌊i·цикл/бригад⌋) — покрытие суток ровное, «дыр» без дежурных нет. Перед применением убедитесь, что в справочнике причин есть все коды шаблона.</div>
      <div class="frow">
        <div class="field" style="flex:2"><label>Шаблон ротации</label><select class="inp" id="pwPat">${patOpts}</select></div>
        <div class="field"><label>Подразделение</label><select class="inp" id="pwDept">${depOpts}</select></div>
      </div>
      <div class="frow">
        <div class="field"><label>Период заполнения</label><select class="inp" id="pwMk">${(()=>{const o=[];for(let i=-1;i<=6;i++){const d=new Date(cur.y,cur.m-1+i,1);o.push(`<option value="${mkOf(d.getFullYear(),d.getMonth()+1)}"${i===0?' selected':''}>${MUP[d.getMonth()]} ${d.getFullYear()}</option>`)}return o.join('')})()}</select></div>
        <div class="field"><label>Дата-якорь ротации</label><input type="date" class="inp" id="pwAnchor" value="${new Date().toISOString().slice(0,10)}"></div>
        <div class="field"><label>Месяцев вперёд</label><input type="number" class="inp" id="pwMonths" min="1" max="12" value="1"></div>
      </div>
      <div class="frow">
        <div class="field"><label>Распределение фаз</label><select class="inp" id="pwMode">
          <option value="fan">Веер по бригадам (ровное покрытие)</option>
          <option value="single">Общая фаза (всем одинаковый цикл)</option>
        </select></div>
        <div class="field" id="pwBrigWrap"><label>Бригад</label><input type="number" class="inp" id="pwBrig" min="1" max="40" value="2"></div>
        <div class="field" id="pwNeedWrap"><label>Минимум в сутки (покрытие)</label><input type="number" class="inp" id="pwNeed" min="0" max="50" value="1"></div>
      </div>
      <label class="chkrow" id="pwSaveWrap"><input type="checkbox" id="pwSaveBrig" checked> сохранить бригады для повторного применения (карточка «Бригады» на «Планировании»)</label>
      <label class="chkrow"><input type="checkbox" id="pwKeep"> не перезаписывать занятые ячейки (отпуска, командировки, больничные)</label>
      <label class="chkrow"><input type="checkbox" id="pwElig" checked> только сотрудники, допущенные к дежурствам</label>
      <label class="chkrow"><input type="checkbox" id="pwCert" checked> исключить сотрудников с просроченным обязательным допуском</label>
      <div class="field"><label>Или конкретные сотрудники (через запятую — таб. № или ФИО)</label><input class="inp" id="pwNames" placeholder="Т-1, Иванов, Петров"></div>
      <div class="status" id="pwPreview">Предпросмотр ротации появится здесь.</div>`,
    buttons:`<button class="btn ghost" data-c2>Отмена</button><button class="btn ghost" id="pwPp" title="Проверить цикл против норм ТК РФ">📋 Паспорт шаблона</button><button class="btn ghost" id="pwAdd">+ Добавить международные ротации</button><button class="btn" id="pwGo">Применить</button>`,
    onMount(b){
      b.querySelector('[data-c2]').onclick=closeModal;
      b.querySelector('#pwAdd').onclick=()=>{addIntlPatterns();closeModal();setTimeout(patternWizard,120)};
      b.querySelector('#pwPp').onclick=()=>{const id=b.querySelector('#pwPat').value;if(id)openPatternPassport(id)};
      const syncMode=()=>{
        const fan=b.querySelector('#pwMode').value==='fan';
        b.querySelector('#pwBrigWrap').style.display=fan?'':'none';
        b.querySelector('#pwNeedWrap').style.display=fan?'':'none';
        b.querySelector('#pwSaveWrap').style.display=fan?'':'none';
      };
      const autoBrig=()=>{
        const pat=patById(b.querySelector('#pwPat').value);
        const depId=b.querySelector('#pwDept').value;
        const dp=depId==='all'?null:dept(depId);
        b.querySelector('#pwNeed').value=(dp&&dp.minDuty)||1;
        if(pat){
          const es=resolvePwEmps(b);
          const rec=brigadesRecommend(pat,depId==='all'?null:depId);
          b.querySelector('#pwBrig').value=clamp(Math.min(rec,Math.max(1,es.length)),1,40);
        }
      };
      const prev=()=>{
        syncMode();
        const pat=patById(b.querySelector('#pwPat').value);
        const anchor=b.querySelector('#pwAnchor').value;
        const mk=b.querySelector('#pwMk').value,y=+mk.slice(0,4),m=+mk.slice(5,7),DIM=dim(y,m);
        if(!pat){b.querySelector('#pwPreview').textContent='Шаблон не выбран';return}
        const seq=patternSeq(pat);
        const miss=seq.filter(c=>c!=='В'&&c!==''&&!reason(c));
        const fan=b.querySelector('#pwMode').value==='fan';
        const brig=clamp(+b.querySelector('#pwBrig').value||1,1,40);
        const need=clamp(+b.querySelector('#pwNeed').value||0,0,50);
        const es=resolvePwEmps(b);
        const pp=patternPassport(pat);
        let cells='',fanHtml='';
        if(fan){
          const offs=fanOffsets(seq.length,brig);
          const anchors=offs.map(o=>addDays(anchor||mk+'-01',-o));
          let defDays=0,zeroDays=0;
          for(let d=1;d<=Math.min(DIM,31);d++){
            let cov=0;
            anchors.forEach(a=>{if(patternCodeAt(pat,a,y,m,d))cov++});
            const di=dayInfo(y,m,d);
            const cls=cov<need?'def':(need&&cov>need?'over':'ok');
            if(cov<need)defDays++;
            if(!cov)zeroDays++;
            cells+=`<span class="covcell ${cls}${di.off?' we':''}${isToday(y,m,d)?' today':''}" title="День ${d}: ${cov} из ${need}"><em>${d}</em>${cov}</span>`;
          }
          fanHtml=`<div style="margin-top:8px"><b>Покрытие по бригадам</b> (${brig} бриг. · смещения фаз ${offs.join(', ')})
            ${defDays?`<span class="pill r" style="margin-left:6px">дней ниже минимума: ${fmtStd(defDays,{unit:'дн'})}</span>`:'<span class="pill g" style="margin-left:6px">дефицита нет</span>'}
            ${zeroDays?` <span class="pill a">без отметок: ${fmtStd(zeroDays,{unit:'дн'})}</span>`:''}
            ${es.length<brig?` <span class="pill r">сотрудников (${fmtStd(es.length,{unit:'чел'})}) меньше, чем бригад (${brig})</span>`:''}</div>
            <div class="covstrip" role="img" aria-label="Предпросмотр покрытия по дням: ${brig} бригад, минимум ${need} в сутки, дней с дефицитом ${defDays}">${cells}</div>
            <div class="hint" style="margin-top:4px">Предпросмотр не учитывает уже заполненные ячейки (флажок «не перезаписывать» может снизить фактическое покрытие).</div>`;
        }else{
          for(let d=1;d<=Math.min(DIM,31);d++){
            const di=dayInfo(y,m,d),c=patternCodeAt(pat,anchor,y,m,d);
            cells+=`<span class="pwcell${di.off?' off':''}${isToday(y,m,d)?' today':''}"><em>${d}</em>${c?esc(c):'·'}</span>`;
          }
        }
        b.querySelector('#pwPreview').innerHTML=`<b>${esc(pat.name)}</b> · цикл ${fmtStd(seq.length,{unit:'дн'})} ${passportVerdictPill(pp)} · сотрудников к заполнению: <b>${fmtStd(es.length,{unit:'чел'})}</b>${miss.length?`<div class="status err" style="margin-top:6px">В справочнике нет кодов: <b>${esc(miss.join(', '))}</b> — добавьте их, иначе ротация не применится.</div>`:''}
          ${fan?'':`<div class="pwstrip" style="margin-top:8px">${cells}</div>`}
          ${fanHtml}
          <div class="hint" style="margin-top:6px">Якорь ${esc(anchor||'—')}: фаза цикла на 1-е число периода = ${fmtStd(patternIndex(pat,anchor,y,m,1)+1)}-й элемент последовательности. При смене месяца цикл продолжится без сбоя.</div>`;
      };
      b.querySelector('#pwPat').onchange=()=>{autoBrig();prev()};
      b.querySelector('#pwDept').onchange=()=>{autoBrig();prev()};
      ['pwMk','pwAnchor','pwMonths','pwElig','pwCert','pwNames','pwKeep','pwMode','pwBrig','pwNeed','pwSaveBrig'].forEach(id=>{
        const el=b.querySelector('#'+id);if(el){el.onchange=prev;el.oninput=prev}
      });
      autoBrig();prev();
      b.querySelector('#pwGo').onclick=()=>{
        const patId=b.querySelector('#pwPat').value,anchor=b.querySelector('#pwAnchor').value,
              keep=b.querySelector('#pwKeep').checked,nm=+b.querySelector('#pwMonths').value||1,
              fan=b.querySelector('#pwMode').value==='fan',
              brig=clamp(+b.querySelector('#pwBrig').value||2,1,40),
              saveBrig=b.querySelector('#pwSaveBrig').checked,
              es=resolvePwEmps(b);
        if(!es.length){toast('Нет сотрудников для заполнения','err');return}
        const pat=patById(patId);
        if(!pat){toast('Шаблон не найден','err');return}
        const mk0=b.querySelector('#pwMk').value,y0=+mk0.slice(0,4),m0=+mk0.slice(5,7);
        if(fan&&es.length<brig){toast(`Сотрудников (${es.length}) меньше, чем бригад (${brig}) — уменьшите число бригад или снимите фильтры`,'err');return}
        confirmBox(`${fan?`Применить ротацию «${esc(pat.name)}» <b>веером по бригадам</b>`:`Применить ротацию «${esc(pat.name)}»`} к ${fmtStd(es.length,{unit:'чел'})} на ${fmtStd(nm,{unit:'мес'})} начиная с ${MUP[m0-1]} ${y0}?${fan?`<br>Бригад: ${brig} · смещения фаз: ${fanOffsets(patternSeq(pat).length,brig).join(', ')}. Отсутствия (отпуск, больничный, командировка) сохраняются всегда.`:''}`,()=>{
          for(let i=0;i<nm;i++){
            const d=new Date(y0,m0-1+i,1);
            if(fan)applyPatternFan(patId,es,d.getFullYear(),d.getMonth()+1,anchor,keep,brig,{save:saveBrig&&i===0});
            else applyPatternAnchored(patId,es.map(e=>e.id),d.getFullYear(),d.getMonth()+1,anchor,keep);
          }
          closeModal();
        });
      };
    }});
}
""", 'patternWizard')

    # ---- R13: биндинги планирования ----
    rep("  bindClick('btnPatternWizard',patternWizard);",
        """  bindClick('btnPatternWizard',patternWizard);
  bindClick('btnCovDoc',openCoverageDoctor);                                        /* 3.36: доктор покрытия */
  bindClick('btnPatPassport',()=>openPatternPassport(($('patSel')||{}).value));     /* 3.36: паспорт шаблона из генератора */
  bindClick('btnBrigApplyAll',()=>applyAllBrigades(cur.y,cur.m));                   /* 3.36: все бригады на месяц */""", 'plan bindings')

    # ---- R14: основной модуль 3.36 ----
    span('/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */',
         '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */',
        MODULE_336 + '\n', 'module 3.36', include_end=True)

    # ---- R14b: «Мой месяц» — карточка «Моя бригада» ----
    rep("  box.querySelectorAll('[data-meack]').forEach(b=>b.onclick=()=>sigAckSend(b.dataset.meack));",
        "  /* 3.36: «Моя бригада» — сотрудник видит свою ротацию со сквозной фазой */\n"
        "  try{\n"
        "    const myBr=brigadeList().find(b=>(b.members||[]).includes(e.id));\n"
        "    const myPat=myBr?patById(myBr.patId):null;\n"
        "    if(myBr&&myPat){\n"
        "      const myAnchor=addDays(myBr.anchor||`${y}-${pad2(m)}-01`,-(myBr.offset||0));\n"
        "      const DIMm=dim(y,m);\n"
        "      let myCells='';\n"
        "      for(let d=1;d<=DIMm;d++){\n"
        "        const c=patternCodeAt(myPat,myAnchor,y,m,d),di=dayInfo(y,m,d);\n"
        "        const mine=getCode(e.id,y,m,d);\n"
        "        myCells+=`<span class=\"pwcell${di.off?' off':''}${isToday(y,m,d)?' today':''}\" title=\"${d} ${WD[di.wd]}: ${c?esc(c):'выходной'}${mine?' · отметка: '+esc(mine):''}\"><em>${d}</em>${c?esc(c):'·'}</span>`;\n"
        "      }\n"
        "      box.insertAdjacentHTML('afterbegin',`<div class=\"card\" id=\"meBrigCard\"><h3>Моя бригада<span class=\"sub\">3.36 · ротация со сквозной фазой от якоря</span></h3>\n"
        "        <div class=\"hint\" style=\"margin-top:0\"><b>${esc(myBr.name)}</b> · шаблон «${esc(myPat.name)}» (${esc(myPat.seq)}) · смещение фазы ${fmtStd(myBr.offset||0,{unit:'дн'})} · якорь ${esc(myBr.anchor||'—')} · состав: ${fmtStd((myBr.members||[]).length,{unit:'чел'})}</div>\n"
        "        <div class=\"pwstrip\" style=\"margin-top:8px\" role=\"img\" aria-label=\"Моя ротация на ${MUP[m-1]} ${y}: цикл ${esc(myPat.seq)}\">${myCells}</div>\n"
        "        <div class=\"hint\" style=\"margin-top:6px\">Цикл продолжается через границу месяца без сбоя: фаза считается от даты-якоря бригады. Состав бригады обновляет табельщик.</div></div>`);\n"
        "    }\n"
        "  }catch(err){}\n"
        "  box.querySelectorAll('[data-meack]').forEach(b=>b.onclick=()=>sigAckSend(b.dataset.meack));", 'me brigade')

    # ---- R14c: паспорт виджетов — виджеты 3.36 ----
    rep("  {id:'repMatrix',tab:'rep',name:'Каталог форм',form:'матрица «тип сообщения → формы»',source:'константа каталога REPORT_FORM_MATRIX'}\n];",
        "  {id:'repMatrix',tab:'rep',name:'Каталог форм',form:'матрица «тип сообщения → формы»',source:'константа каталога REPORT_FORM_MATRIX'},\n"
        "  {id:'rotPassport',tab:'set',name:'Паспорт шаблона ротации',form:'таблица метрик цикла + вердикт ТК РФ со списком замечаний',source:'канон: state.patterns, reasons, rules'},\n"
        "  {id:'brigCard',tab:'plan',name:'Бригады · сохранённые ротации',form:'список: состав, смещение фазы, применение к месяцу, печать ведомости',source:'канон: state.brigades, план открытого месяца'},\n"
        "  {id:'covDoctor',tab:'plan',name:'Доктор покрытия',form:'календарь дефицитов + рекомендации с оценкой, причинами и рисками',source:'канон: план открытого месяца, правила, пожелания, допуски'},\n"
        "  {id:'covWizard',tab:'plan',name:'Мастер ротаций: предпросмотр покрытия',form:'календарь покрытия по дням (веер по бригадам) с подсветкой дефицита',source:'канон: state.patterns, минимум подразделения'}\n];", 'widget registry')

    # ---- R14d: реестр интерактивных отчётов — доктор покрытия 5/5 ----
    rep("  {id:'mgrSlides',name:'Доклад-презентация руководителя',tab:'rep',crit:{filter:0,drill:0,live:1,insight:1,export:1},note:'печатная форма — статичная'}];",
        "  {id:'mgrSlides',name:'Доклад-презентация руководителя',tab:'rep',crit:{filter:0,drill:0,live:1,insight:1,export:1},note:'печатная форма — статичная'},\n"
        "  {id:'covDoctor',name:'Доктор покрытия',tab:'plan',crit:{filter:1,drill:1,live:1,insight:1,export:1},note:'3.36: фильтры подразделения/минимума/режима, детализация до кандидата и дня, живой пересчёт, вывод-календарь дефицитов, экспорт CSV со штампом'}];", 'interactive reports')

    # ---- R15: палитра ----
    rep("    {ic:'❓',title:'Справка и горячие клавиши',hint:'F1',run:()=>showHelp()}",
        """    {ic:'🩺',title:'Доктор покрытия: дефициты и рекомендации',hint:'планирование · 3.36',run:()=>{showTab('plan');setTimeout(()=>openCoverageDoctor(),250)}},
    {ic:'⚙',title:'Мастер ротаций: фазы и бригады',hint:'планирование · 3.36',run:()=>{showTab('plan');setTimeout(()=>patternWizard(),250)}},
    {ic:'📋',title:'Паспорта шаблонов ротаций (нормы ТК РФ)',hint:'справочники · 3.36',run:()=>{showTab('set');setTimeout(()=>openAllPassports(),300)}},
    {ic:'➕',title:'Конструктор ротации: шаблон из параметров N/M',hint:'справочники · 3.36',run:()=>{showTab('set');setTimeout(()=>openPatternConstructor(),300)}},
    {ic:'👥',title:'Бригады: сохранённые ротации на месяц',hint:'планирование · 3.36',run:()=>{showTab('plan');setTimeout(()=>{const c=$('brigCard');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:systemMotionOk()?'smooth':'auto',block:'center'})},320)}},
    {ic:'🖨',title:'Бригадная ведомость (печать)',hint:'вывод · 3.36',run:()=>{showTab('plan');setTimeout(()=>printBrigadeSheet(),300)}},
    {ic:'❓',title:'Справка и горячие клавиши',hint:'F1',run:()=>showHelp()}""", 'palette')

    # ---- R16: справка «Новое в версии 3.36» ----
    rep('      <div class="lbl" style="margin-top:12px">Новое в версии 3.35 — коннектор «1С», веб-панель обмена, UX-волна</div>',
        """      <div class="lbl" style="margin-top:12px">Новое в версии 3.36 — конструктор ротаций, бригады и доктор покрытия</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Паспорт шаблона ротации</b>: каталог «Справочники → Шаблоны сменных графиков» — цветная лента цикла, вердикт «соответствует нормам / требует внимания / не соответствует», средние часы за неделю и месяц, серии работы и отдыха с закольцовкой цикла, дежурства и ночные, сколько человек закрывают один пост круглосуточно; проверка против норм ТК РФ (ст. 91 — 40-часовая неделя, ст. 96 — ночная работа, ст. 100 — сменный режим, ст. 110 — 42 часа непрерывного отдыха) и включённых правил комплаенса; «📋 Паспорта всех шаблонов» — сводная таблица; кнопка «📋 Паспорт шаблона» в генераторе графиков и в мастере ротаций.</li>
        <li><b>Веер по бригадам</b>: мастер ротаций («⚙») распределяет фазу между N бригадами — смещение i-й бригады ⌊i·цикл/бригад⌋; предпросмотр — календарь покрытия по дням с подсветкой дефицита; число бригад предлагается автоматически из минимума подразделения (мин/сутки × цикл / рабочих дней в цикле).</li>
        <li><b>Бригады в общей базе</b> (<code>state.brigades</code>): сохранённый состав (карточка «Бригады» на «Планировании») — применение к любому месяцу в один клик со сквозной фазой от якоря; отсутствия (отпуск, больничный, командировка) сохраняются всегда; синхронизируется по ЛВС вместе с каноном.</li>
        <li><b>Доктор покрытия</b> («Планирование → 🩺 Покрытие»): календарь дефицитов дня против минимума (дежурства или все явки), рекомендации с оценкой: пожелания («не ставить» — жёсткое исключение, «предпочтительно» — приоритет +40), справедливость (дежурства против среднего по отделу), загрузка месяца, отдых после суточных/ночных, серии рабочих дней и недельные часы против правил, допуски; назначение по одному или «✔ Применить все рекомендации» (оценка ≥ 40); все правки идут через операционный протокол и доступны к отмене (Ctrl+Z).</li>
        <li><b>Конструктор ротации</b>: генерация цикла из параметров «N рабочих / M выходных» с чередованием день/ночь, живой проверкой норм до сохранения; каталог — дублирование «⧉», экспорт JSON/CSV с паспортами; предупреждение о неизвестных кодах при добавлении шаблона.</li>
        <li><b>Волна 2 (НСИ и поверхности)</b>: доктор покрытия — интерактивный отчёт по 5 критериям с выгрузкой CSV со штампом («⇩ CSV»); виджеты 3.36 внесены в паспорт виджетов и реестр отчётов; телеметрия использования новых поверхностей (pt.tele); «Мой месяц» — карточка «Моя бригада» с лентой личной ротации; «🖨 Бригадная ведомость» — печатная форма «бригады × дни месяца» (альбомная, светлая, итоги дежурств и часов).</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.35 — коннектор «1С», веб-панель обмена, UX-волна</div>""", 'help 3.36')

    # ---- R17: экспорт APP ----
    rep("    get T13_CODES(){return T13_REASONS.map(t=>t.code)},",
        """    get T13_CODES(){return T13_REASONS.map(t=>t.code)},
    /* ===== 3.36: конструктор ротаций, бригады и доктор покрытия ===== */
    patternSeq,patById,patternHours,patternIsWork,rotBusyRaw,patternPassport,passportVerdictPill,passportIssuesHtml,
    rotChipHtml,rotStripHtml,openPatternPassport,openAllPassports,openPatternConstructor,buildSeqFromParams,pcAutoName,
    fanOffsets,brigadesRecommend,splitBrigades,applyPatternFan,brigadeList,renderBrigades,applyBrigadeToMonth,applyAllBrigades,
    coverageScan,coverageCandidates,coverageApply,openCoverageDoctor,patternsJsonDl,patternsCsvDl,
    coverageCsvDl,printBrigadeSheet,""", 'APP exports')

    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(s)
    print('OK %s: %d -> %d bytes (+%d)' % (path, orig_len, len(s), len(s)-orig_len))


MODULE_336 = r"""/* ================= 3.36: КОНСТРУКТОР РОТАЦИЙ, БРИГАДЫ И ДОКТОР ПОКРЫТИЯ =================
   Тема релиза — «умное планирование»:
   1) паспорт шаблона — проверка цикла против норм ТК РФ (ст. 91/96/100/110) и правил комплаенса;
   2) веер по бригадам — мастер ротаций разводит фазы (смещение i = ⌊i·цикл/бригад⌋) для ровного покрытия;
   3) бригады в каноне (state.brigades) — повторное применение из месяца в месяц одним кликом;
   4) доктор покрытия — дефициты по дням и рекомендации с оценкой (пожелания, справедливость,
      загрузка, отдых после суточных, серии, недельные часы, допуски);
   5) конструктор ротаций и каталог 2.0 — лента цикла, дубли, экспорт JSON/CSV.
   Все записи плана идут через setCellRaw → операционный протокол 3.18; отмена — общий стек undo. */

/* ---- базовые примитивы шаблонов ---- */
function patternSeq(pat){return String((pat&&pat.seq)||'').split(',').map(s=>s.trim().toUpperCase()).filter(Boolean)}
function patById(id){return (state.patterns||[]).find(p=>p.id===id)||null}
function patternHours(code){
  const r=reason(code);if(!r||r.hmode==='none')return 0;
  if(r.hmode==='fixed')return r.hours||0;
  return (state.settings&&state.settings.hoursDay)||8;
}
function patternIsWork(code){const r=reason(code);return !!(r&&r.coeff>0&&patternHours(code)>0)}
/* отсутствие, которое ротация/доктор не имеют права трогать */
function rotBusyRaw(raw){
  if(!raw)return false;
  const r=reason(parseCell(raw).code);
  return !!(r&&(r.cat==='vac'||r.cat==='sick'||r.cat==='trip'||r.cat==='study'||r.cat==='unpaid'||r.cat==='absent'));
}

/* ---- паспорт: комплаенс цикла против ТК РФ и правил ---- */
function patternPassport(pat){
  const seq=patternSeq(pat);if(!seq.length)return null;
  const N=seq.length;
  const norm=((state.settings||{}).hoursWeek)||40;
  const rCon=rule('maxConsecWork'),rWeek=rule('maxWeekHours'),rRest=rule('restAfterDuty'),rDuty=rule('maxDutyMonth');
  const workFlags=seq.map(c=>patternIsWork(c));
  let hoursCycle=0,work=0,dutyDays=0,nightShifts=0,nightH=0;
  seq.forEach((c,i)=>{
    if(!workFlags[i])return;
    const r=reason(c),h=patternHours(c);
    hoursCycle+=h;work++;
    if(r.cat==='duty')dutyDays++;
    if((r.night||0)>0){nightShifts++;nightH+=Math.min(r.night,h)}
  });
  /* серии с закольцовкой: ротация периодична, поэтому считаем по двум кругам */
  const runMax=flags=>{
    if(flags.every(x=>x))return N;
    if(flags.every(x=>!x))return 0;
    let best=0,curLen=0;
    for(let i=0;i<2*N;i++){curLen=flags[i%N]?curLen+1:0;if(curLen>best)best=curLen}
    return best;
  };
  const maxConsec=runMax(workFlags);
  const maxRestRun=runMax(workFlags.map(x=>!x));
  /* «пятидневка» (Я×5 без выходных в цикле) — неделя = сумма часов цикла:
     шаблон применяется только на будни, выходные проставляются по производственному календарю */
  const pyatidnevka=work===N&&N<=5&&seq.every(c=>c==='Я');
  const weekBase=pyatidnevka?hoursCycle:hoursCycle/N*7;
  const hoursWeek=weekBase;
  const hoursMonth=weekBase/7*30.44;
  const dutyMonth=dutyDays/N*30.44;
  const nightPct=hoursCycle>0?nightH/hoursCycle*100:0;
  const restHours=maxRestRun*24;
  const issues=[];
  if(!work)issues.push({sev:'crit',text:'В цикле нет рабочих дней — шаблон проставляет только выходные'});
  if(rWeek.on&&hoursWeek>rWeek.val)issues.push({sev:'crit',text:`Средняя неделя ${fmtStd(hoursWeek,{dec:1})} ч — выше правила «максимум часов за неделю» (${fmtStd(rWeek.val,{unit:'ч'})})`});
  else if(norm&&hoursWeek>norm*1.2)issues.push({sev:'warn',text:`Переработка относительно нормальной недели ${fmtStd(norm,{unit:'ч'})}: +${fmtStd(hoursWeek/norm*100-100,{dec:0})}% (ст. 91 ТК РФ)`});
  if(norm&&work&&hoursWeek<norm*0.8&&!pyatidnevka)issues.push({sev:'info',text:`Недоработка относительно нормальной недели: ${fmtStd(hoursWeek,{dec:1,unit:'ч'})} из ${fmtStd(norm,{unit:'ч'})} — суммированный учёт или неполная ставка`});
  if(rCon.on&&maxConsec>rCon.val)issues.push({sev:'warn',text:`Серии работы до ${fmtStd(maxConsec,{unit:'дн'})} подряд — выше предела правила (${fmtStd(rCon.val,{unit:'дн'})})`});
  /* отдых после суточного/ночного дежурства (правило restAfterDuty + ст. 110 ТК РФ) */
  const needRest=Math.max(1,rRest.on?rRest.val:1);
  let noRest=0;
  for(let i=0;i<N;i++){
    if(!workFlags[i])continue;
    const c=seq[i],r=reason(c);
    if(!r||r.cat!=='duty')continue;
    const hard=(patternHours(c)>=24)||(r.night||0)>=8;   /* суточное или ночное дежурство */
    if(!hard)continue;
    let gap=0;
    for(let j=1;j<=N;j++){if(workFlags[(i+j)%N])break;gap++}
    if(gap<needRest)noRest++;
  }
  if(noRest)issues.push({sev:'crit',text:`После суточного/ночного дежурства нет полноценного отдыха в ${noRest} сл. цикла (норма правила — ${fmtStd(needRest,{unit:'дн'})}; ст. 110 ТК РФ — еженедельный непрерывный отдых не менее 42 ч)`});
  if(pyatidnevka)issues.push({sev:'info',text:'Режим «пятидневка»: в последовательности нет выходных — применяйте шаблон только на будни (массовое заполнение «только будни месяца»), выходные проставляются по производственному календарю'});
  else if(!maxRestRun)issues.push({sev:'crit',text:'В цикле нет выходных дней'});
  else if(restHours<42)issues.push({sev:'warn',text:`Самый длинный отдых в цикле — ${fmtStd(maxRestRun,{unit:'дн'})} (${fmtStd(restHours,{unit:'ч'})}): меньше 42 ч еженедельного непрерывного отдыха (ст. 110 ТК РФ)`});
  if(rDuty.on&&dutyMonth>rDuty.val)issues.push({sev:'warn',text:`≈ ${fmtStd(dutyMonth,{dec:1})} дежурств в месяц на человека — выше предела правила (${fmtStd(rDuty.val,{unit:'шт'})})`});
  if(nightPct>30)issues.push({sev:'info',text:`Доля ночных часов ${fmtStd(nightPct,{dec:0})}% — высокая (ст. 96 ТК РФ: сокращение на 1 ч, доплата не ниже 20%)`});
  const verdict=issues.some(x=>x.sev==='crit')?'bad':issues.some(x=>x.sev==='warn')?'warn':'ok';
  const allDuty24=work>0&&seq.every(c=>!patternIsWork(c)||(reason(c).cat==='duty'&&patternHours(c)>=24));
  const kind=!work?'пустой':pyatidnevka?'пятидневка':allDuty24?'суточное':(nightShifts?'сменное (с ночными)':'сменное');
  return{N,work,offs:N-work,hoursCycle,hoursWeek,hoursMonth,dutyDays,dutyMonth,nightShifts,nightPct,
    maxConsec,maxRestRun,restHours,norm,peoplePerPost:work?N/work:0,issues,verdict,kind,seq,pyatidnevka};
}
function passportVerdictPill(pp){
  if(!pp)return '<span class="pill r" title="Последовательность пуста">пустой шаблон</span>';
  const m={ok:['g','✓ соответствует нормам'],warn:['a','⚠ требует внимания'],bad:['r','✕ не соответствует']};
  const v=m[pp.verdict]||m.warn;
  return `<span class="pill ${v[0]}" title="Проверка цикла против норм ТК РФ (ст. 91, 96, 100, 110) и включённых правил комплаенса">${v[1]}</span>`;
}
function passportIssuesHtml(pp){
  if(!pp)return '';
  if(!pp.issues.length)return '<div class="status" style="margin-top:8px">✓ Нарушений нет: цикл укладывается в нормы ТК РФ и включённые правила комплаенса.</div>';
  return pp.issues.map(i=>`<div class="status ${i.sev==='crit'?'err':''}" style="margin-top:6px;border-left:3px solid ${i.sev==='crit'?'var(--red)':i.sev==='warn'?'var(--amber)':'var(--blue)'};padding-left:8px">
    ${i.sev==='crit'?'✕':i.sev==='warn'?'⚠':'ℹ'} ${esc(i.text)}</div>`).join('');
}
/* цветная лента цикла */
function rotChipHtml(code){
  const r=reason(code);
  const col=r?r.color:'var(--slate)';
  const rest=!patternIsWork(code);
  return `<span class="rot-chip${rest?' rest':''}" style="--c:${col}" title="${esc(code)}${r?' — '+esc(r.name):' — нет в справочнике причин'}">${esc(code||'·')}</span>`;
}
function rotStripHtml(seq){
  if(!seq||!seq.length)return '';
  return `<span class="rot-strip" role="img" aria-label="Цикл ${seq.length} дн.: ${esc(seq.join(', '))}">${seq.slice(0,31).map(rotChipHtml).join('')}${seq.length>31?`<span class="rot-chip rest">+${fmtStd(seq.length-31)}</span>`:''}</span>`;
}
function openPatternPassport(patId){
  try{teleHit('rot:passport')}catch(e){}
  const pat=patById(patId)||(state.patterns||[])[0];
  if(!pat){toast('Шаблонов ротаций нет — добавьте в справочниках','err');return}
  const pp=patternPassport(pat);
  openModal({title:'📋 Паспорт шаблона ротации',wide:true,body:`
    <div class="frow" style="align-items:flex-end">
      <div class="field" style="flex:1;margin:0"><label>Шаблон</label><select class="inp" id="ppSel" aria-label="Выбор шаблона">${(state.patterns||[]).map(p=>`<option value="${p.id}" ${p.id===pat.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></div>
      <div style="padding-bottom:4px">${passportVerdictPill(pp)}${pat.intl?` <span class="pill">${esc(pat.intl)}</span>`:''}</div>
    </div>
    ${pp?rotStripHtml(pp.seq):''}
    ${pp?`<table class="rtbl" style="margin-top:10px"><tbody>
      <tr><td>Цикл</td><td class="n">${fmtStd(pp.N,{unit:'дн'})} (${fmtStd(pp.work,{unit:'раб'})} / ${fmtStd(pp.offs,{unit:'вых'})})</td>
          <td>Тип</td><td>${esc(pp.kind)}</td></tr>
      <tr><td>Средние часы в неделю</td><td class="n">${fmtStd(pp.hoursWeek,{dec:1,unit:'ч'})}${pp.norm?` <span class="hint">(норма ${fmtStd(pp.norm,{unit:'ч'})}, отклонение ${pp.norm?fmtStd(pp.hoursWeek/pp.norm*100-100,{dec:0}):'—'}%)</span>`:''}</td>
          <td>Средние часы в месяц</td><td class="n">${fmtStd(pp.hoursMonth,{dec:1,unit:'ч'})}</td></tr>
      <tr><td>Макс. серия работы</td><td class="n">${fmtStd(pp.maxConsec,{unit:'дн'})}</td>
          <td>Макс. отдых подряд</td><td class="n">${fmtStd(pp.maxRestRun,{unit:'дн'})} (${fmtStd(pp.restHours,{unit:'ч'})} · ст. 110 требует ≥ 42)</td></tr>
      <tr><td>Дежурств в цикле</td><td class="n">${fmtStd(pp.dutyDays,{unit:'шт'})} (≈ ${fmtStd(pp.dutyMonth,{dec:1})} в месяц)</td>
          <td>Ночные смены</td><td class="n">${fmtStd(pp.nightShifts,{unit:'шт'})} · ${fmtStd(pp.nightPct,{dec:0})}% ночных часов</td></tr>
      <tr><td>Штат на круглосуточный пост</td><td class="n">${fmtStd(pp.peoplePerPost,{dec:1,unit:'чел'})}</td>
          <td>Покрытие поста (доля цикла)</td><td class="n">${fmtStd(pp.N?pp.work/pp.N:0,{dec:2})}</td></tr>
    </tbody></table>${passportIssuesHtml(pp)}
    <div class="hint" style="margin-top:10px">Методика: средняя неделя = Σ часов цикла / длина цикла × 7 (часы дня — из справочника причин: фиксированные или «часы в дне» настроек); для «пятидневки» (Я×5) неделя = сумма часов цикла — выходные проставляются по производственному календарю; серии и отдых считаются с закольцовкой цикла — ротация периодична; проверка против включённых правил «Контроль норм» (Справочники) и норм ТК РФ — ст. 91 (40-часовая неделя), ст. 96 (ночная работа), ст. 100 (сменный режим), ст. 110 (42 часа непрерывного отдыха в неделю).</div>`
    :'<div class="status err" style="margin-top:8px">Последовательность шаблона пуста или не содержит кодов.</div>'}`,
    buttons:`<button class="btn ghost" data-cpp>Закрыть</button><button class="btn ghost" id="ppWizard" title="Открыть мастер ротаций с этим шаблоном">⚙ В мастер ротаций</button>`,
    onMount(b){
      b.querySelector('[data-cpp]').onclick=closeModal;
      b.querySelector('#ppSel').onchange=e=>{closeModal();setTimeout(()=>openPatternPassport(e.target.value),80)};
      b.querySelector('#ppWizard').onclick=()=>{closeModal();setTimeout(()=>patternWizard(),120)};
    }});
}
function openAllPassports(){
  const pats=state.patterns||[];
  if(!pats.length){toast('Шаблонов нет','err');return}
  const rows=pats.map(p=>{const pp=patternPassport(p);
    return `<tr><td>${esc(p.name)}</td><td style="font-family:var(--f-mono);font-size:11px">${esc(p.seq)}</td>
      <td class="n">${pp?fmtStd(pp.hoursWeek,{dec:1}):'—'}</td><td class="n">${pp?fmtStd(pp.maxConsec):'—'}</td>
      <td class="n">${pp&&pp.peoplePerPost>1?fmtStd(pp.peoplePerPost,{dec:1}):'—'}</td>
      <td>${passportVerdictPill(pp)}</td><td><button class="btn ghost tiny" data-pp="${p.id}">Паспорт</button></td></tr>`}).join('');
  openModal({title:'📋 Паспорта шаблонов ротаций — сводка',wide:true,
    body:`<div class="scroll-x"><table class="rtbl"><thead><tr><th>Шаблон</th><th>Последовательность</th><th class="n">ч/нед</th><th class="n">макс. серия</th><th class="n">чел/пост</th><th>Вердикт</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="hint" style="margin-top:8px"><b>Соответствует нормам</b> — цикл укладывается в нормы ТК РФ и включённые правила комплаенса; <b>требует внимания</b> — есть предупреждения (переработка, короткий отдых, много дежурств); <b>не соответствует</b> — критические нарушения (неделя выше жёсткого лимита, нет отдыха после суточных). «чел/пост» — сколько человек нужно, чтобы один пост был закрыт круглосуточно.</div>`,
    buttons:'<button class="btn ghost" data-cpa>Закрыть</button>',
    onMount(b){
      b.querySelector('[data-cpa]').onclick=closeModal;
      b.querySelectorAll('[data-pp]').forEach(x=>x.onclick=()=>{closeModal();setTimeout(()=>openPatternPassport(x.dataset.pp),80)});
    }});
}

/* ---- конструктор ротаций: цикл из параметров N рабочих / M выходных ---- */
function buildSeqFromParams(p){
  const work=clamp(Math.round(+p.work||0),0,20),rest=clamp(Math.round(+p.rest||0),0,40);
  const wCode=String(p.wCode||'Д1').toUpperCase(),rCode=String(p.rCode||'В').toUpperCase();
  const alt=p.alt&&p.wCode2?String(p.wCode2).toUpperCase():null;
  const w=[];
  for(let i=0;i<work;i++)w.push(alt&&i%2?alt:wCode);
  return w.concat(Array.from({length:rest},()=>rCode));
}
function pcAutoName(p){
  const a=p.alt&&p.wCode2?'/'+String(p.wCode2).toUpperCase():'';
  return `${String(p.wCode||'').toUpperCase()}${a} · ${p.work}/${p.rest}`;
}
function openPatternConstructor(){
  try{teleHit('rot:construct')}catch(e){}
  const rs=state.reasons||[];
  const workRs=rs.filter(r=>r.coeff>0&&r.hmode!=='none');
  const wOpts=workRs.map(r=>`<option value="${esc(r.code)}"${r.code==='Д1'?' selected':''}>${esc(r.code)} — ${esc(r.name)}${r.hours?` (${r.hours} ч)`:''}</option>`).join('');
  const aOpts='<option value="" selected>— нет —</option>'+workRs.map(r=>`<option value="${esc(r.code)}">${esc(r.code)} — ${esc(r.name)}</option>`).join('');
  const rOpts=rs.filter(r=>r.cat==='off'||r.hmode==='none').map(r=>`<option value="${esc(r.code)}"${r.code==='В'?' selected':''}>${esc(r.code)} — ${esc(r.name)}</option>`).join('')||'<option value="В" selected>В — Выходной</option>';
  openModal({title:'➕ Конструктор ротации',wide:true,body:`
    <div class="hint" style="margin-top:0">Шаблон — повторяющийся цикл кодов «N рабочих / M выходных». Фаза считается от якоря в мастере ротаций; паспорт сразу проверяет цикл против норм ТК РФ. Чередование «день/ночь» даёт ДНОВ-подобные графики (Д2,Д3,Д2,Д3,…).</div>
    <div class="frow" style="flex-wrap:wrap;gap:8px">
      <div class="field" style="flex:1.6;margin:0"><label>Название</label><input class="inp" id="pcName" placeholder="Суточное 1/3"></div>
      <div class="field" style="margin:0"><label>Код рабочих дней</label><select class="inp" id="pcW">${wOpts}</select></div>
      <div class="field" style="margin:0"><label>Чередовать с (день/ночь)</label><select class="inp" id="pcW2">${aOpts}</select></div>
      <div class="field" style="margin:0"><label>Код выходных</label><select class="inp" id="pcR">${rOpts}</select></div>
      <div class="field" style="margin:0"><label>Рабочих</label><input type="number" class="inp" id="pcNw" min="0" max="20" value="1" style="max-width:76px"></div>
      <div class="field" style="margin:0"><label>Выходных</label><input type="number" class="inp" id="pcNr" min="0" max="40" value="3" style="max-width:76px"></div>
    </div>
    <div id="pcPrev" style="margin-top:10px"></div>`,
    buttons:`<button class="btn ghost" data-cpc>Отмена</button><button class="btn" id="pcSave">💾 Сохранить шаблон</button>`,
    onMount(b){
      b.querySelector('[data-cpc]').onclick=closeModal;
      const params=()=>({
        wCode:b.querySelector('#pcW').value,wCode2:b.querySelector('#pcW2').value,rCode:b.querySelector('#pcR').value,
        work:+b.querySelector('#pcNw').value||0,rest:+b.querySelector('#pcNr').value||0,alt:!!b.querySelector('#pcW2').value});
      const live=()=>{
        const p=params(),seq=buildSeqFromParams(p);
        const pp=seq.length?patternPassport({name:'предпросмотр',seq:seq.join(',')}):null;
        b.querySelector('#pcPrev').innerHTML=seq.length&&pp?`${rotStripHtml(seq)}
          <div style="margin-top:8px">${passportVerdictPill(pp)} <span class="pill">цикл ${fmtStd(pp.N,{unit:'дн'})}</span> <span class="pill">${fmtStd(pp.hoursWeek,{dec:1,unit:'ч/нед'})}</span> <span class="pill">${fmtStd(pp.hoursMonth,{dec:0,unit:'ч/мес'})}</span>${pp.peoplePerPost>1?` <span class="pill">${fmtStd(pp.peoplePerPost,{dec:1,unit:'чел/пост'})}</span>`:''}</div>
          ${passportIssuesHtml(pp)}
          <div class="hint" style="margin-top:6px">Последовательность: <code>${esc(seq.join(','))}</code>${b.querySelector('#pcName').value.trim()?'':' · название подставится автоматически: «'+esc(pcAutoName(p))+'»'}</div>`
          :'<div class="status err" style="margin-top:0">Укажите число рабочих или выходных дней.</div>';
      };
      ['pcW','pcW2','pcR','pcNw','pcNr','pcName'].forEach(id=>{const el=b.querySelector('#'+id);el.onchange=live;el.oninput=live});
      live();
      b.querySelector('#pcSave').onclick=()=>{
        const p=params(),seq=buildSeqFromParams(p);
        if(!seq.length||!seq.some(c=>patternIsWork(c))){toast('В цикле нет рабочих дней','err');return}
        const miss=seq.filter(c=>c!=='В'&&!reason(c));
        if(miss.length){toast('Неизвестные коды: '+miss.join(', '),'err');return}
        const name=(b.querySelector('#pcName').value||'').trim()||pcAutoName(p);
        if((state.patterns||[]).some(x=>x.name===name)){toast('Шаблон «'+name+'» уже есть — выберите другое название','err');return}
        state.patterns=state.patterns||[];
        state.patterns.push({id:uid('p'),name,seq:seq.join(',')});
        save(true);renderPatternsList();renderBulk();
        audit('Конструктор ротации',`${name} · ${seq.join(',')}`,'patterns',{after:seq.join(',')});
        closeModal();toast('Шаблон добавлен: «'+name+'»','ok');
      };
    }});
}
function patternsJsonDl(){
  const pats=state.patterns||[];
  if(!pats.length){toast('Шаблонов нет','err');return}
  const data=pats.map(p=>{const pp=patternPassport(p);
    return{id:p.id,name:p.name,seq:p.seq,intl:p.intl||null,
      passport:pp?{cycle:pp.N,work:pp.work,off:pp.offs,hoursWeek:Math.round(pp.hoursWeek*10)/10,
        hoursMonth:Math.round(pp.hoursMonth*10)/10,maxConsec:pp.maxConsec,maxRestDays:pp.maxRestRun,
        dutyDays:pp.dutyDays,nightShifts:pp.nightShifts,nightPct:Math.round(pp.nightPct*10)/10,
        peoplePerPost:Math.round(pp.peoplePerPost*100)/100,kind:pp.kind,verdict:pp.verdict,
        issues:pp.issues.map(i=>({sev:i.sev,text:i.text}))}:null}});
  download('shablony-rotacij-'+new Date().toISOString().slice(0,10)+'.json',JSON.stringify(data,null,2),'application/json');
  audit('Экспорт шаблонов ротаций',`${data.length} шт · JSON (с паспортами)`,'patterns');
  toast('Каталог шаблонов выгружен в JSON','ok');
}
function patternsCsvDl(){
  const pats=state.patterns||[];
  if(!pats.length){toast('Шаблонов нет','err');return}
  const rows=[['Название','Последовательность','Международный','Цикл дн','Рабочих','Выходных','ч/нед','ч/мес','Макс серия дн','Макс отдых дн','Дежурств в цикле','Ночных смен','Ночные %','чел/пост','Вердикт','Замечания']];
  pats.forEach(p=>{const pp=patternPassport(p);
    rows.push([p.name,p.seq,p.intl||'',pp?pp.N:'',pp?pp.work:'',pp?pp.offs:'',
      pp?Math.round(pp.hoursWeek*10)/10:'',pp?Math.round(pp.hoursMonth*10)/10:'',
      pp?pp.maxConsec:'',pp?pp.maxRestRun:'',pp?pp.dutyDays:'',pp?pp.nightShifts:'',
      pp?Math.round(pp.nightPct*10)/10:'',pp?Math.round(pp.peoplePerPost*100)/100:'',
      pp?(pp.verdict==='ok'?'соответствует':pp.verdict==='warn'?'требует внимания':'не соответствует'):'',
      pp?pp.issues.map(i=>(i.sev==='crit'?'✕ ':i.sev==='warn'?'⚠ ':'ℹ ')+i.text).join(' | '):''])});
  downloadCsv('shablony-rotacij-'+new Date().toISOString().slice(0,10)+'.csv',rows);
  audit('Экспорт шаблонов ротаций',`${pats.length} шт · CSV`,'patterns');
  toast('Каталог шаблонов выгружен в CSV','ok');
}

/* ---- веер по бригадам: равномерное покрытие ---- */
function fanOffsets(N,brig){
  brig=clamp(Math.round(brig)||1,1,60);
  const out=[];
  for(let i=0;i<brig;i++)out.push(Math.floor(i*N/brig));
  return out;
}
function brigadesRecommend(pat,deptId){
  const pp=patternPassport(pat);
  if(!pp||!pp.work)return 2;
  const dp=deptId?dept(deptId):null;
  const need=Math.max(1,(dp&&dp.minDuty)||1);
  return clamp(Math.ceil(need*pp.N/pp.work),1,40);
}
function splitBrigades(es,brig){
  const g=Array.from({length:brig},()=>[]);
  es.forEach((e,i)=>g[i%brig].push(e));
  return g;
}
function brigadeList(){
  if(!state.brigades||!Array.isArray(state.brigades))state.brigades=[];
  return state.brigades;
}
function applyPatternFan(patId,es,y,m,anchor,keep,brig,opt){
  opt=opt||{};
  const pat=patById(patId);
  if(!pat){toast('Шаблон не найден','err');return{n:0,groups:[]}}
  if(!guardRole('edit','применение ротации по бригадам'))return{n:0,groups:[]};
  const pp=patternPassport(pat);
  if(!pp){toast('Шаблон пуст','err');return{n:0,groups:[]}}
  const miss=pp.seq.filter(c=>c!=='В'&&!reason(c));
  if(miss.length){toast('Неизвестные коды в шаблоне: '+miss.join(', ')+'. Добавьте их в справочник причин.','err');return{n:0,groups:[]}}
  if(!es||!es.length){toast('Нет сотрудников','err');return{n:0,groups:[]}}
  const base=anchor||`${y}-${pad2(m)}-01`;
  const offs=fanOffsets(pp.N,brig);
  const groups=splitBrigades(es,offs.length).map((mem,i)=>({
    name:(opt.names&&opt.names[i])||`${pat.name} · бригада ${i+1}`,
    offset:offs[i],anchor:addDays(base,-offs[i]),members:mem.map(e=>e.id)}));
  const DIM=dim(y,m);
  const doIt=()=>{
    WFM_BYPASS=1;let n=0;
    try{
      pushUndo('ротация по бригадам «'+pat.name+'» '+MUP[m-1]+' '+y);
      groups.forEach(g=>{
        g.members.forEach(eid=>{
          for(let d=1;d<=DIM;d++){
            const raw=getCode(eid,y,m,d);
            if(keep&&raw)continue;
            if(rotBusyRaw(raw))continue;   /* 3.36: отсутствия сохраняются независимо от флага keep */
            const c=patternCodeAt(pat,g.anchor,y,m,d);
            setCellRaw(eid,y,m,d,c);
            if(c)n++;
          }
        });
      });
    }finally{WFM_BYPASS=0}
    if(opt.save!==false){
      const bl=brigadeList();
      groups.forEach(g=>{
        const rec={name:g.name,patId:pat.id,anchor:base,offset:g.offset,members:g.members};
        const ex=bl.find(x=>x.name===g.name&&x.patId===pat.id);
        if(ex)Object.assign(ex,rec);else bl.push(Object.assign({id:uid('b')},rec));
      });
    }
    bust();save(true);refreshAll();
    audit('Ротация по бригадам',`${pat.name} · ${offs.length} бриг. · ${es.length} чел. · ${MUP[m-1]} ${y} · якорь ${base} · ${n} ячеек`,`plan:${mkOf(y,m)}`,{after:pat.seq,brigades:offs.length,offsets:offs});
    try{teleHit('rot:fan')}catch(e){}
    toast(`Ротация «${pat.name}»: ${offs.length} бриг. · ${n} отметок · смещения фаз ${offs.join('/')}`,'ok');
    return{n,groups};
  };
  if(isClosed(y,m)){guardRun(y,m,`применение ротации по бригадам «${pat.name}»`,doIt);return{n:0,groups}}
  return doIt();
}
function renderBrigades(){
  const box=$('brigBox');if(!box)return;
  const bl=brigadeList();
  const cnt=$('brigCount');if(cnt)cnt.textContent=String(bl.length);
  const all=$('btnBrigApplyAll');if(all)all.hidden=!bl.length;
  const bp=$('btnBrigPrint');if(bp){bp.hidden=!bl.length;bp.onclick=()=>printBrigadeSheet()}
  box.innerHTML=bl.length?bl.map(b=>{
    const pat=patById(b.patId);
    const names=(b.members||[]).map(id=>{const e=emp(id);return e&&!e.fired?e.name:null}).filter(Boolean);
    return `<div class="setrow" style="flex-wrap:wrap">
      <div style="flex:1;min-width:150px">
        <b style="font-size:12.5px">${esc(b.name)}</b>
        <div class="hint" style="margin-top:2px">${pat?esc(pat.name):'— шаблон удалён —'} · смещение фазы ${fmtStd(b.offset||0,{unit:'дн'})} · ${fmtStd(names.length,{unit:'чел'})}${names.length?`: ${esc(names.slice(0,3).join(', '))}${names.length>3?'…':''}`:''}</div>
      </div>
      <button class="btn ghost tiny" data-briggo="${b.id}" title="Заполнить текущий месяц со сквозной фазой (отсутствия сохраняются)">▶ На месяц</button>
      <button class="x" data-brigdel="${b.id}" title="Удалить бригаду">✕</button>
    </div>`}).join(''):'<div class="hint">Сохранённых бригад нет — создайте в мастере «⚙ Мастер ротаций» (режим «веер по бригадам», флажок «сохранить бригады»).</div>';
  box.querySelectorAll('[data-briggo]').forEach(x=>x.onclick=()=>{
    const b=brigadeList().find(v=>v.id===x.dataset.briggo);if(!b)return;
    confirmBox(`Применить бригаду «${esc(b.name)}» на ${MUP[cur.m-1]} ${cur.y}? Отсутствия (отпуск, больничный, командировка) сохранятся, рабочие отметки и дежурства будут перезаписаны по шаблону со сквозной фазой от якоря ${esc(b.anchor||'—')}.`,
      ()=>applyBrigadeToMonth(b.id,cur.y,cur.m),'Да, применить');
  });
  box.querySelectorAll('[data-brigdel]').forEach(x=>x.onclick=()=>{
    const b=brigadeList().find(v=>v.id===x.dataset.brigdel);if(!b)return;
    confirmBox(`Удалить бригаду «${esc(b.name)}»? Отметки в плане останутся без изменений.`,()=>{
      state.brigades=brigadeList().filter(v=>v.id!==b.id);
      save(true);renderBrigades();
      audit('Удаление бригады',b.name,'brigades');
      toast('Бригада удалена');
    },'Удалить');
  });
}
function applyBrigadeToMonth(brigId,y,m){
  const b=brigadeList().find(x=>x.id===brigId);
  if(!b){toast('Бригада не найдена','err');return 0}
  const pat=patById(b.patId);
  if(!pat){toast('Шаблон бригады удалён из справочника','err');return 0}
  if(!guardRole('edit','применение бригады к месяцу'))return 0;
  const anchor=addDays(b.anchor||`${y}-${pad2(m)}-01`,-(b.offset||0));
  const es=(b.members||[]).map(id=>emp(id)).filter(e=>e&&!e.fired);
  if(!es.length){toast('В бригаде нет активных сотрудников','err');return 0}
  const DIM=dim(y,m);
  const doIt=()=>{
    WFM_BYPASS=1;let n=0;
    try{
      pushUndo('бригада «'+b.name+'» на '+MUP[m-1]+' '+y);
      es.forEach(e=>{
        for(let d=1;d<=DIM;d++){
          const raw=getCode(e.id,y,m,d);
          if(rotBusyRaw(raw))continue;   /* отсутствия неприкосновенны */
          const c=patternCodeAt(pat,anchor,y,m,d);
          setCellRaw(e.id,y,m,d,c);
          if(c)n++;
        }
      });
    }finally{WFM_BYPASS=0}
    bust();save(true);refreshAll();
    audit('Применение бригады',`${b.name} · ${MUP[m-1]} ${y} · ${es.length} чел. · ${n} ячеек`,`plan:${mkOf(y,m)}`);
    try{teleHit('rot:brigade')}catch(e){}
    toastUndo(`Бригада «${b.name}»: ${n} отметок за ${MUP[m-1]} ${y}`);
    return n;
  };
  if(isClosed(y,m)){guardRun(y,m,`применение бригады «${b.name}»`,doIt);return 0}
  return doIt();
}
function applyAllBrigades(y,m){
  const bl=brigadeList();
  if(!bl.length){toast('Сохранённых бригад нет','err');return}
  confirmBox(`Применить все бригады (${bl.length}) на ${MUP[m-1]} ${y}? Отсутствия (отпуск, больничный, командировка) сохранятся.`,()=>{
    if(!guardRole('edit','применение всех бригад'))return;
    let n=0;
    bl.forEach(b=>{n+=applyBrigadeToMonth(b.id,y,m)||0});
    audit('Применение всех бригад',`${bl.length} бриг. · ${MUP[m-1]} ${y} · ${n} ячеек`,`plan:${mkOf(y,m)}`);
  },'Да, применить все');
}

/* ---- доктор покрытия: дефициты и рекомендации ---- */
function coverageScan(y,m,deptId,opt){
  opt=opt||{};
  const dp=dept(deptId)||{};
  const need=opt.need!=null?+opt.need:(dp.minDuty||0);
  const mode=opt.mode||'duty';
  const code=String(opt.code||dp.dutyCode||'Д1').toUpperCase();
  const es=empList(deptId);
  const DIM=dim(y,m),days=[];
  for(let d=1;d<=DIM;d++){
    let plan=0;const on=[];
    es.forEach(e=>{
      const raw=getCode(e.id,y,m,d);if(!raw)return;
      const r=reason(parseCell(raw).code);if(!r)return;
      const hit=mode==='duty'?r.cat==='duty':(r.coeff>0&&r.cat!=='off');
      if(hit){plan++;on.push(e.id)}
    });
    days.push({d,wd:new Date(y,m-1,d).getDay(),plan,need,deficit:Math.max(0,need-plan),over:Math.max(0,plan-need),on});
  }
  return{y,m,deptId,need,mode,code,days,DIM,es,
    defDays:days.filter(x=>x.deficit>0),overDays:days.filter(x=>x.over>0),
    worst:days.reduce((a,x)=>Math.max(a,x.deficit),0)};
}
function coverageCandidates(scan,d,topN){
  topN=topN||3;
  const{y,m,mode}=scan,DIM=scan.DIM;
  const dk=k(y,m,d);
  const rCon=rule('maxConsecWork'),rWeek=rule('maxWeekHours'),rRest=rule('restAfterDuty'),rFair=rule('fairDev');
  const newR=reason(scan.code),newH=patternHours(scan.code);
  const hardNew=!!(newR&&newR.cat==='duty'&&(newH>=24||(newR.night||0)>=8));
  const es=empList(scan.deptId).filter(e=>e.dutyEligible!==false);
  /* дежурства за месяц — компонент справедливости */
  const dCnt={};let dSum=0;
  es.forEach(e=>{let c=0;
    for(let dd=1;dd<=DIM;dd++){const raw=getCode(e.id,y,m,dd);if(!raw)continue;const r=reason(parseCell(raw).code);if(r&&r.cat==='duty')c++}
    dCnt[e.id]=c;dSum+=c});
  const avgDuty=es.length?dSum/es.length:0;
  const restNeed=Math.max(1,rRest.on?rRest.val:1);
  const out=[];
  es.forEach(e=>{
    const raw=getCode(e.id,y,m,d);
    if(rotBusyRaw(raw))return;                                  /* отпуск/больничный/командировка — не кандидат */
    if(raw){const r0=reason(parseCell(raw).code);
      if(r0&&(mode==='duty'?r0.cat==='duty':(r0.coeff>0&&r0.cat!=='off')))return}   /* уже учтён в этот день */
    if(dutyCertBlocked(e.id,new Date(y,m-1,d)))return;          /* нет обязательного допуска */
    if(wishBlock(e.id,dk))return;                               /* пожелание «не ставить» */
    const why=[],viol=[];let score=50;
    if(wishPref(e.id,dk)){score+=40;why.push('предпочтительная дата')}
    const dc=dCnt[e.id]||0;
    if(avgDuty>0.01){
      if(dc<avgDuty){score+=Math.min(25,Math.round((avgDuty-dc)*8));why.push(`дежурств ${fmtStd(dc)} при среднем ${fmtStd(avgDuty,{dec:1})}`)}
      else if(rFair.on&&dc>avgDuty*(1+rFair.val/100)){score-=25;viol.push(`перебор дежурств: ${fmtStd(dc)} при среднем ${fmtStd(avgDuty,{dec:1})}`)}
    }else if(dc===0&&dSum>0){score+=10;why.push('в этом месяце дежурств ещё не было')}
    const st=empMonthStats(e.id,y,m);
    if(st&&st.pct!=null&&!isNaN(st.pct)){
      if(st.pct<90){score+=15;why.push(`загрузка ${fmtStd(st.pct,{pct:true})} — есть ресурс`)}
      else if(st.pct>110){score-=25;viol.push(`уже перегружен (${fmtStd(st.pct,{pct:true})} нормы)`)}
    }
    /* явные отметки: серии и недели считаем только по проставленным кодам (пусто = не назначен) */
    const hardDutyAt=dd=>{
      if(dd<1||dd>DIM)return false;
      const rw=getCode(e.id,y,m,dd);if(!rw)return false;
      const c0=parseCell(rw),r0=reason(c0.code);
      return !!(r0&&r0.cat==='duty'&&((c0.hs!=null?c0.hs:(r0.hours||0))>=24||(r0.night||0)>=8));
    };
    const workAt=dd=>{
      if(dd<1||dd>DIM)return false;
      const rw=getCode(e.id,y,m,dd);if(!rw)return false;
      return dayCoeff(e.id,y,m,dd)>0;
    };
    let gap=0,prevDutyDay=null;
    for(let j=1;j<=DIM;j++){
      const dd=d-j;if(dd<1)break;
      if(hardDutyAt(dd)){prevDutyDay=dd;break}
      if(workAt(dd))break;   /* работа прерывает цепочку отдыха — более ранние дежурства нас не касаются */
      gap++;
    }
    if(prevDutyDay!=null&&gap<restNeed){score-=60;viol.push(`отдых после дежурства ${pad2(prevDutyDay)}-го — ${fmtStd(gap,{unit:'дн'})} (норма ${fmtStd(restNeed,{unit:'дн'})})`)}
    if(hardNew){
      let g2=0,nextWork=null;
      for(let j=1;j<=restNeed+1;j++){
        const dd=d+j;if(dd>DIM)break;
        if(workAt(dd)){nextWork=dd;break}
        g2++;
      }
      if(nextWork!=null&&g2<restNeed){score-=30;viol.push(`после суточных ${pad2(nextWork)}-го уже стоит работа — отдых ${fmtStd(g2,{unit:'дн'})} < ${fmtStd(restNeed,{unit:'дн'})}`)}
    }
    let back=0;for(let j=1;j<=16;j++){const dd=d-j;if(dd<1||!workAt(dd))break;back++}
    let fwd=0;for(let j=1;j<=16;j++){const dd=d+j;if(dd>DIM||!workAt(dd))break;fwd++}
    const series=back+1+fwd;
    if(rCon.on&&series>rCon.val){score-=40;viol.push(`серия работы ${fmtStd(series,{unit:'дн'})} подряд (лимит ${fmtStd(rCon.val,{unit:'дн'})})`)}
    if(rWeek.on&&newH>0){
      const wd=(new Date(y,m-1,d).getDay()+6)%7;   /* пн = 0 */
      let weekH=newH;
      for(let j=-wd;j<=6-wd;j++){
        const dd=d+j;if(dd<1||dd>DIM||j===0)continue;
        const rw=getCode(e.id,y,m,dd);if(rw)weekH+=hoursFor(e.id,y,m,dd);
      }
      if(weekH>rWeek.val){score-=30;viol.push(`неделя станет ≈ ${fmtStd(weekH,{unit:'ч'})} (лимит ${fmtStd(rWeek.val,{unit:'ч'})})`)}
    }
    if(!why.length&&!viol.length)why.push('противопоказаний нет');   /* 3.36: базовый кандидат без рисков */
    out.push({eid:e.id,name:e.name,pos:e.pos||'',score:Math.round(score),why,viol});
  });
  out.sort((a,b)=>b.score-a.score||String(a.name).localeCompare(String(b.name),'ru'));
  return{list:out.slice(0,topN),all:out,avgDuty};
}
function coverageApply(scan,picks){
  if(!picks||!picks.length){toast('Применять нечего','err');return 0}
  if(!guardRole('edit','применение рекомендаций покрытия'))return 0;
  const{y,m,code,deptId}=scan;
  const doIt=()=>{
    let n=0,skip=0;
    pushUndo('доктор покрытия · '+MUP[m-1]+' '+y);
    picks.forEach(p=>{
      const raw=getCode(p.eid,y,m,p.d);
      if(rotBusyRaw(raw)){skip++;return}   /* отсутствие появилось, пока доктор был открыт */
      setCellRaw(p.eid,y,m,p.d,p.code||code);n++;
    });
    bust();save(true);refreshAll();
    audit('Доктор покрытия',`${(dept(deptId)||{}).name||'—'} · ${MUP[m-1]} ${y} · назначено ${n}${skip?`, отклонено ${skip} (отсутствие)`:''} · код ${code}`,`plan:${mkOf(y,m)}`,{picks:n});
    try{teleHit('covdoctor:apply')}catch(e){}
    toastUndo(`Доктор покрытия: назначено ${fmtStd(n)}${skip?` · пропущено ${fmtStd(skip)} (появились отсутствия)`:''}`);
    return n;
  };
  if(isClosed(y,m)){guardRun(y,m,'применение рекомендаций покрытия',doIt);return 0}
  return doIt();
}
function openCoverageDoctor(preset){
  preset=preset||{};
  const dep0=preset.deptId||(state.settings&&state.settings.dutyDept)||((state.departments[0]||{}).id)||null;
  if(!state.departments.length){toast('Нет подразделений — добавьте в справочниках','err');return}
  openModal({title:'🩺 Доктор покрытия — дефициты и рекомендации',wide:true,
    body:`
    <div class="frow" style="flex-wrap:wrap;gap:8px">
      <div class="field" style="flex:1.5;margin:0"><label>Подразделение · период ${MUP[cur.m-1]} ${cur.y}</label><select class="inp" id="cdDept" aria-label="Подразделение">
        ${state.departments.map(d=>`<option value="${d.id}" ${d.id===dep0?'selected':''}>${esc(d.name)}${d.minDuty?` · мин ${d.minDuty}/сут`:''}</option>`).join('')}
      </select></div>
      <div class="field" style="margin:0"><label>Минимум в сутки</label><input type="number" class="inp" id="cdNeed" min="0" max="50" value="1" style="max-width:88px" aria-label="Минимум дежурных в сутки"></div>
      <div class="field" style="margin:0"><label>Учитывать</label><select class="inp" id="cdMode" aria-label="Что считать покрытием">
        <option value="duty">дежурства</option><option value="work">все явки (коэф &gt; 0)</option>
      </select></div>
      <div class="field" style="margin:0"><label>Код назначения</label><select class="inp" id="cdCode" aria-label="Код назначения">
        ${state.reasons.filter(r=>r.cat==='duty'||(r.cat==='work'&&r.coeff>0)).map(r=>`<option value="${esc(r.code)}">${esc(r.code)} — ${esc(r.name)}</option>`).join('')}
      </select></div>
    </div>
    <div id="cdBody" style="margin-top:10px"></div>`,
    buttons:`<button class="btn ghost" data-ccd>Закрыть</button><button class="btn ghost" id="cdCsv" title="Выгрузить скан покрытия и рекомендации в CSV со штампом">⇩ CSV</button><button class="btn" id="cdApplyAll" title="Назначить лучших кандидатов (оценка ≥ 40) на все дни с дефицитом">✔ Применить все рекомендации</button>`,
    onMount(b){
      let scan=null;
      try{teleHit('covdoctor')}catch(e){}   /* 3.36: телеметрия использования */
      const redraw=()=>{
        const depId=b.querySelector('#cdDept').value;
        scan=coverageScan(cur.y,cur.m,depId,{
          need:+b.querySelector('#cdNeed').value||0,
          mode:b.querySelector('#cdMode').value,
          code:b.querySelector('#cdCode').value});
        const box=b.querySelector('#cdBody');
        const cells=scan.days.map(x=>{
          const di=dayInfo(cur.y,cur.m,x.d);
          const cls=x.deficit?'def':(x.over?'over':'ok');
          return `<span class="covcell ${cls}${di.off?' we':''}${isToday(cur.y,cur.m,x.d)?' today':''}" title="${x.d} ${WD[x.wd]}: план ${x.plan} из ${x.need}"><em>${x.d}</em>${x.deficit?'−'+fmtStd(x.deficit):fmtStd(x.plan)}</span>`;
        }).join('');
        let html=(isClosed(cur.y,cur.m)?'<div class="status err" style="margin-top:0">Период ЗАКРЫТ — рекомендации не применяются. Откройте период в «Данных» либо используйте обход с основанием.</div>':'')+
          `<div style="margin-top:6px">${scan.defDays.length
            ?`<span class="pill r">дней с дефицитом: ${fmtStd(scan.defDays.length,{unit:'дн'})} из ${fmtStd(scan.DIM,{unit:'дн'})}</span> <span class="pill">худший дефицит: −${fmtStd(scan.worst)}</span>`
            :`<span class="pill g">покрытие достаточное все ${fmtStd(scan.DIM,{unit:'дн'})}</span>`}
            ${scan.overDays.length?` <span class="pill a">избыток: ${fmtStd(scan.overDays.length,{unit:'дн'})}</span>`:''}
            <span class="pill">минимум: ${fmtStd(scan.need)}/сут · ${scan.mode==='duty'?'дежурства':'явки'}</span></div>
          <div class="covstrip" role="img" aria-label="Покрытие по дням месяца ${MUP[cur.m-1]} ${cur.y}: дней с дефицитом ${scan.defDays.length} из ${scan.DIM}">${cells}</div>`;
        if(!scan.need){
          box.innerHTML=html+'<div class="status" style="margin-top:8px">Укажите «минимум в сутки» — норматив подразделения (заполняется в карточке подразделения: «мин дежурных») или заданное вручную значение.</div>';
          return;
        }
        if(!scan.defDays.length){
          box.innerHTML=html+(scan.overDays.length?`<div class="hint" style="margin-top:8px">В ${fmtStd(scan.overDays.length,{unit:'дн'})} план выше минимума — проверьте обоснованность избытка (стоимость переработок).</div>`:'');
          return;
        }
        html+='<div class="scroll-x" style="max-height:44vh;overflow:auto;margin-top:10px"><table class="rtbl"><thead><tr><th>Дата</th><th class="n">план / мин</th><th>Рекомендации: оценка · причины · риски</th><th></th></tr></thead><tbody>';
        scan.defDays.forEach(x=>{
          const cands=coverageCandidates(scan,x.d,x.deficit+2);
          const di=dayInfo(cur.y,cur.m,x.d);
          const rows=cands.list.length?cands.list.map(c=>`
            <div class="candrow">
              <button class="btn ghost tiny" data-cdgo="${x.d}:${c.eid}" title="Назначить «${esc(c.name)}» на ${pad2(x.d)} ${esc(WD[x.wd])}" aria-label="Назначить ${esc(c.name)} на ${x.d} число">＋</button>
              <b style="font-size:12px">${esc(c.name)}</b>${c.pos?`<span class="hint">${esc(c.pos)}</span>`:''}
              <span class="pill ${c.score>=70?'g':c.score>=40?'a':'r'}" title="Оценка рекомендации: 50 база, бонусы за пожелание/справедливость/ресурс, штрафы за риски">${fmtStd(c.score)}</span>
              ${c.why.map(w=>`<span class="cand-chip good">✓ ${esc(w)}</span>`).join('')}
              ${c.viol.map(w=>`<span class="cand-chip bad">⚠ ${esc(w)}</span>`).join('')}
            </div>`).join(''):'<span class="hint">Кандидатов нет: все заняты, в пожеланиях «не ставить» или без допуска.</span>';
          html+=`<tr>
            <td><b>${pad2(x.d)} ${WD[x.wd]}</b>${di.off?'<div class="hint">выходной/праздник</div>':''}</td>
            <td class="n"><span class="pill r">${fmtStd(x.plan)} / ${fmtStd(x.need)}</span></td>
            <td>${rows}</td>
            <td class="n">${cands.list.length&&cands.list[0].score>=40?`<button class="btn ghost tiny" data-cdbest="${x.d}" title="Назначить лучшего кандидата">✔ лучшего</button>`:''}</td>
          </tr>`;
        });
        html+='</tbody></table></div>';
        html+=`<div class="hint" style="margin-top:8px">Оценка: 50 — база; «предпочтительно ставить» +40; дежурств меньше среднего по отделу — до +25; загрузка &lt; 90 % — +15; перебор дежурств / короткий отдых после суточных / длинная серия / превышение недельных часов — штрафы. Жёсткие исключения: отпуск, больничный, командировка, «не ставить», отсутствие обязательного допуска, уже учтён в этот день. Серии и недельные часы считаются по явным отметкам плана.</div>`;
        box.innerHTML=html;
        box.querySelectorAll('[data-cdgo]').forEach(el=>el.onclick=()=>{
          const pr=el.dataset.cdgo.split(':');
          if(coverageApply(scan,[{d:+pr[0],eid:pr[1],code:scan.code}]))redraw();
        });
        box.querySelectorAll('[data-cdbest]').forEach(el=>el.onclick=()=>{
          const d=+el.dataset.cdbest;
          const c=coverageCandidates(scan,d,1).list[0];
          if(!c){toast('Кандидатов нет','err');return}
          if(coverageApply(scan,[{d,eid:c.eid,code:scan.code}]))redraw();
        });
      };
      b.querySelector('[data-ccd]').onclick=closeModal;
      b.querySelector('#cdCsv').onclick=()=>coverageCsvDl(scan);   /* 3.36: экспорт скана */
      b.querySelector('#cdDept').onchange=()=>{
        const dp=dept(b.querySelector('#cdDept').value);
        if(dp){b.querySelector('#cdNeed').value=dp.minDuty||1;if(dp.dutyCode)b.querySelector('#cdCode').value=dp.dutyCode}
        redraw();
      };
      ['cdNeed','cdMode','cdCode'].forEach(id=>{
        const el=b.querySelector('#'+id);
        el.onchange=redraw;
        el.oninput=()=>{clearTimeout(el._cdt);el._cdt=setTimeout(redraw,400)};
      });
      b.querySelector('#cdApplyAll').onclick=()=>{
        if(!scan||!scan.defDays.length){toast('Дней с дефицитом нет','ok');return}
        const picks=[];let skipped=0;
        scan.defDays.forEach(x=>{
          const list=coverageCandidates(scan,x.d,x.deficit+2).list;
          let need=x.deficit;
          list.forEach(c=>{
            if(need<=0||c.score<40)return;
            if(picks.some(p=>p.eid===c.eid&&p.d===c.d))return;
            picks.push({d:x.d,eid:c.eid,code:scan.code});need--;
          });
          if(need>0)skipped++;
        });
        if(!picks.length){toast('Кандидатов с оценкой ≥ 40 нет — дни останутся дефицитными,смотрите таблицу индивидуально','err');return}
        const dayN=new Set(picks.map(p=>p.d)).size;
        confirmBox(`Назначить ${fmtStd(picks.length,{unit:'чел'})} в ${fmtStd(dayN,{unit:'дн'})} (оценка ≥ 40, код ${esc(scan.code)})?${skipped?` Дней без подходящих кандидатов: ${fmtStd(skipped,{unit:'дн'})} — останутся дефицитными.`:''}`,()=>{
          coverageApply(scan,picks);
          /* confirmBox перехватывает единственную модалку — возвращаем доктора с теми же параметрами */
          openCoverageDoctor({deptId:scan.deptId,need:scan.need,mode:scan.mode,code:scan.code});
        },'Да, назначить');
      };
      const dp0=dept(dep0);
      if(dp0){
        if(dp0.minDuty)b.querySelector('#cdNeed').value=dp0.minDuty;
        if(dp0.dutyCode)b.querySelector('#cdCode').value=dp0.dutyCode;
      }
      if(preset.need!=null)b.querySelector('#cdNeed').value=preset.need;
      if(preset.mode)b.querySelector('#cdMode').value=preset.mode;
      if(preset.code)b.querySelector('#cdCode').value=preset.code;
      redraw();
    }});
}

/* ---- волна 2: экспорт скана покрытия и печатная бригадная ведомость ---- */
PRINT_WIDE.add('brig');   /* 3.36: ведомость широкая — альбомная ориентация в авто-режиме */
function coverageCsvDl(scan){
  if(!scan){toast('Нет данных для выгрузки — откройте доктора покрытия','err');return}
  const dp=(dept(scan.deptId)||{});
  const rows=[['Покрытие по дням · '+(dp.name||'—'),MUP[scan.m-1]+' '+scan.y,'минимум в сутки',scan.need,
    'учёт',scan.mode==='duty'?'дежурства':'все явки','код назначения',scan.code,'штамп',stampPlain('plan')],[]];
  rows.push(['Дата','День недели','План','Минимум','Дефицит','Избыток','В покрытии (ФИО)']);
  scan.days.forEach(x=>rows.push([pad2(x.d),WD[x.wd],x.plan,x.need,x.deficit||'',x.over||'',
    x.on.map(id=>empName(id)).join('; ')]));
  if(scan.defDays.length){
    rows.push([]);
    rows.push(['Рекомендации доктора покрытия (топ по оценке)']);
    rows.push(['Дата','№','Кандидат','Оценка','Причины (бонусы)','Риски (штрафы)']);
    scan.defDays.forEach(x=>{
      coverageCandidates(scan,x.d,3).list.forEach((c,i)=>rows.push(
        [pad2(x.d)+' '+WD[x.wd],i+1,c.name,c.score,c.why.join('; '),c.viol.join('; ')]));
    });
  }
  downloadCsv('pokrytie-'+(scan.deptId||'all')+'-'+mkOf(scan.y,scan.m)+'.csv',rows);
  audit('Выгрузка покрытия',`${dp.name||'—'} · ${MUP[scan.m-1]} ${scan.y} · CSV · дней ${scan.DIM}, дефицитных ${scan.defDays.length}`,'coverage');
  try{teleHit('covdoctor:csv')}catch(e){}
  toast('Покрытие выгружено в CSV','ok');
}
function printBrigadeSheet(){
  const bl=brigadeList();
  if(!bl.length){toast('Сохранённых бригад нет — создайте в мастере ротаций','err');return}
  const{y,m}=cur,DIM=dim(y,m);
  const head='<tr><th style="min-width:150px">Бригада / сотрудник</th>'+
    Array.from({length:DIM},(_,i)=>`<th class="n">${i+1}</th>`).join('')+
    '<th class="n">Дежурств</th><th class="n">Часов</th></tr>';
  let rows='';
  bl.forEach(b=>{
    const pat=patById(b.patId);
    rows+=`<tr><td colspan="${DIM+3}" style="background:#eef1f7;font-weight:700">${esc(b.name)}${pat?` · шаблон «${esc(pat.name)}» (${esc(pat.seq)}) · смещение фазы ${fmtStd(b.offset||0,{unit:'дн'})} · якорь ${esc(b.anchor||'—')}`:''}</td></tr>`;
    (b.members||[]).forEach(eid=>{
      const e=emp(eid);if(!e)return;
      let cnt=0,hh=0,td='';
      for(let d=1;d<=DIM;d++){
        const raw=getCode(eid,y,m,d),c=raw?parseCell(raw).code:'';
        const r=raw?reason(c):null,di=dayInfo(y,m,d);
        if(r&&r.cat==='duty'){cnt++;hh+=hoursFor(eid,y,m,d)}
        td+=`<td class="n" style="${di.off?'background:#fdf0ef;':''}${r&&r.cat==='duty'?'font-weight:700':''}">${esc(c||'')}</td>`;
      }
      rows+=`<tr><td>${esc(e.name)}${e.pos?' · '+esc(e.pos):''}</td>${td}<td class="n"><b>${cnt}</b></td><td class="n">${fmt1(hh)}</td></tr>`;
    });
  });
  /* 34 колонки — всегда альбомно, независимо от пользовательской настройки ориентации */
  $('printArea').innerHTML='<style>@page{size:A4 landscape;margin:8mm}</style>'+`<h1>${esc(state.org)}</h1>
    <div class="ph-sub">Бригадная ведомость ротации за ${MUP[m-1]} ${y} г. · бригад: ${bl.length} · сформировано ${esc(stampPlain('plan'))}</div>
    <table><thead>${head}</thead><tbody>${rows}</tbody></table>
    <div class="pnote">Фаза сквозная: цикл продолжается от даты-якоря через границу месяца. Отсутствия (отпуск, больничный, командировка) приоритетнее шаблона бригады. Дежурств и часов — итоги месяца по явным отметкам.</div>`;
  const keep=$('printHead').innerHTML;
  $('printHead').innerHTML=`<h1>${esc(state.org)}</h1>`;
  try{window.print()}catch(err){}
  setTimeout(()=>{$('printArea').innerHTML='';$('printHead').innerHTML=keep},600);
  try{teleHit('rot:brigprint')}catch(e){}
  audit('Печать бригадной ведомости',`${MUP[m-1]} ${y} · бригад ${bl.length}`,'brigades');
  toast('Бригадная ведомость отправлена на печать','ok');
}

"""

    # sanity: the span() for module inserts before the section-9 comment
    # (span with identical start/end markers + include_end keeps the marker)

if __name__ == '__main__':
    for p in sys.argv[1:]:
        build(p)
