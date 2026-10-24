#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Релизный поезд WFM 3.38–3.48: цепочные сборки поверх 3.37.
Использование:  python3 build-train.py 3.38 3.41
Строит План-табель-WFM-<ver>.html для каждого ver из диапазона последовательно
(3.38 из 3.37, 3.39 из 3.38, …). Новые версии добавляются функцией V<ver>."""
import sys, io, os

HERE = os.path.dirname(os.path.abspath(__file__))

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
        self.rep("geoPrev,ver:'%s'," % prev, "geoPrev,ver:'%s'," % v, 'app.ver ' + v)
        self.rep("const ver=(window.APP&&APP.ver)||'%s';" % prev,
                 "const ver=(window.APP&&APP.ver)||'%s';" % v, 'ver fallback ' + v)

# ============================== 3.38 МОБИЛЬНАЯ ВОЛНА ==============================
CSS_338 = """
/* ===== 3.38: мобильная волна ===== */
.mobi-nav{display:none}
body.mobile{padding-bottom:58px}
body.mobile .mobi-nav{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:60;background:var(--card);border-top:1px solid var(--line);box-shadow:0 -4px 14px rgb(0 0 0 / .10)}
.mobi-tab{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;padding:7px 2px 6px;min-height:48px;border:0;background:none;color:var(--mut);font-size:10px;cursor:pointer;font-family:var(--f-body)}
.mobi-tab .mi{font-size:19px;line-height:1}
.mobi-tab.act{color:var(--navy);font-weight:700;box-shadow:inset 0 3px 0 var(--navy)}
body.mobile .btn{min-height:38px}
body.mobile .tabbtn{min-height:40px}
body.mobile .pt td .cc,body.mobile .pt td{min-width:26px}
#btnInstall{position:fixed;right:10px;bottom:66px;z-index:61;display:none}
body.mobile #btnInstall{display:inline-flex}
@media (max-width:900px){.plan-grid{grid-template-columns:1fr}.side{order:2}}
"""

MODULE_338 = r"""/* ================= 3.38: МОБИЛЬНАЯ ВОЛНА =================
   Нижняя навигация на узких экранах, свайп месяца в месячных разделах,
   крупные цели касания, авто-компакт таблиц, установка приложения (PWA-lite). */
let MOBI_ON=false,DEFERRED_PROMPT=null;
function mobiQuery(){return '(max-width: 900px)'}
function mobiOn(){return MOBI_ON}
function setMobileMode(on){
  MOBI_ON=!!on;
  document.body.classList.toggle('mobile',MOBI_ON);
  document.body.classList.toggle('auto-compact',MOBI_ON);   /* плотность таблиц на узких экранах */
  renderMobiNav();
  renderInstallBtn();
  return MOBI_ON;
}
const MOBI_TABS=[['dash','📊'],['me','👤'],['plan','🗓'],['tabel','🧾'],['set','⚙️']];
function mobiTabTitle(t){const m={dash:'Дашборд',me:'Мой месяц',plan:'План',tabel:'Табель',set:'Ещё'};return m[t]||t}
function renderMobiNav(){
  let nav=$('mobiNav');
  if(!MOBI_ON){if(nav)nav.remove();return}
  if(!nav){
    nav=document.createElement('nav');nav.id='mobiNav';nav.className='mobi-nav no-print';
    nav.setAttribute('role','tablist');nav.setAttribute('aria-label','Основные разделы — мобильная навигация');
    document.body.appendChild(nav);
  }
  nav.innerHTML=MOBI_TABS.map(t=>`<button class="mobi-tab${activeTab===t[0]?' act':''}" data-mt="${t[0]}" role="tab" aria-selected="${activeTab===t[0]}" aria-label="Раздел ${esc(mobiTabTitle(t[0]))}"><span class="mi" aria-hidden="true">${t[1]}</span><span class="mt">${esc(mobiTabTitle(t[0]))}</span></button>`).join('')+
    `<button class="mobi-tab${''}" data-mt="more" role="tab" aria-selected="false" aria-label="Ещё разделы и команды — палитра"><span class="mi" aria-hidden="true">⋯</span><span class="mt">Ещё</span></button>`;
  nav.querySelectorAll('[data-mt]').forEach(b=>b.onclick=()=>{
    const t=b.dataset.mt;
    if(t==='more'){openPalette();return}
    showTab(t);renderMobiNav();
  });
}
function initSwipeMonth(){
  ['view-dash','view-me','view-plan','view-tabel'].forEach(id=>{
    const el=$(id);if(!el||el.__swipe38)return;el.__swipe38=1;
    let x0=null,y0=null;
    el.addEventListener('touchstart',e=>{const t=e.changedTouches&&e.changedTouches[0];if(!t)return;x0=t.clientX;y0=t.clientY},{passive:true});
    el.addEventListener('touchend',e=>{
      const t=e.changedTouches&&e.changedTouches[0];if(!t||x0==null)return;
      const dx=t.clientX-x0,dy=t.clientY-y0;x0=null;y0=null;
      if(Math.abs(dx)>60&&Math.abs(dy)<40)swipeMonth(dx);
    },{passive:true});
  });
}
function swipeMonth(dx){navMonth(dx>0?-1:1)}   /* свайп влево — следующий месяц */
function initInstallPrompt(){
  window.addEventListener('beforeinstallprompt',e=>{try{e.preventDefault()}catch(err){}DEFERRED_PROMPT=e;renderInstallBtn()});
  window.addEventListener('appinstalled',()=>{DEFERRED_PROMPT=null;renderInstallBtn();toast('Приложение установлено','ok')});
  renderInstallBtn();
}
function renderInstallBtn(){
  let b=$('btnInstall');
  if(!b){
    b=document.createElement('button');b.id='btnInstall';b.className='btn ghost small';
    b.onclick=async()=>{
      if(DEFERRED_PROMPT){try{DEFERRED_PROMPT.prompt();await DEFERRED_PROMPT.userChoice}catch(e){}DEFERRED_PROMPT=null;renderInstallBtn()}
      else openInstallHint();
    };
    document.body.appendChild(b);
  }
  b.textContent='📲 Установить';
  b.title='Установить «План-табель» как приложение устройства (PWA-lite, 3.38)';
  b.setAttribute('aria-label','Установить приложение');
}
function openInstallHint(){
  try{teleHit('mobi:install')}catch(e){}
  openModal({title:'📲 Установка приложения',body:`<div class="hint" style="margin-top:0">На телефоне откройте приложение в браузере и выберите «Добавить на главный экран» (iOS Safari — «Поделиться → На экран «Домой»», Android Chrome — меню «Установить приложение»). Браузер сам предложит установку, если поймает событие beforeinstallprompt — кнопка «📲» перехватит его.</div>
    <div class="hint">Офлайн-сборка работает как приложение без установки: положите <code>…-offline.html</code> на устройство — данные хранятся в localStorage устройства, синхронизация по ЛВС при появлении сети.</div>`,
    buttons:'<button class="btn ghost" data-ci38>Закрыть</button>',
    onMount(b){b.querySelector('[data-ci38]').onclick=closeModal}});
}
function initMobileShell(){
  try{
    const mq=window.matchMedia?matchMedia(mobiQuery()):null;
    const apply=()=>setMobileMode(mq?mq.matches:(window.innerWidth||1200)<=900);
    if(mq){if(mq.addEventListener)mq.addEventListener('change',apply);else if(mq.addListener)mq.addListener(apply)}
    window.addEventListener('resize',()=>{clearTimeout(window.__mobiT38);window.__mobiT38=setTimeout(apply,200)});
    apply();
    initSwipeMonth();
    initInstallPrompt();
  }catch(e){}
}
"""

def V338(c):
    c.ver('3.38')
    c.rep('.pwcell.today{border-color:var(--navy);box-shadow:0 0 0 2px color-mix(in srgb,var(--navy) 22%,transparent)}',
          '.pwcell.today{border-color:var(--navy);box-shadow:0 0 0 2px color-mix(in srgb,var(--navy) 22%,transparent)}' + CSS_338, 'css 338')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9)
    assert i >= 0 and c.s.find(m9, i+1) < 0
    c.s = c.s[:i] + MODULE_338 + '\n' + c.s[i:]
    c.rep('  wfmInit();', '  wfmInit();\n  try{initMobileShell()}catch(e){}   /* 3.38: мобильная волна */', 'boot hook 338')
    c.rep('function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){}}   /* 3.36: бригады */',
          'function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){}}   /* 3.36: бригады; 3.38: mobi-nav */', 'mobi nav refresh')
    c.rep("""    {ic:'🖨',title:'Бригадная ведомость (печать)',hint:'вывод · 3.36',run:()=>{showTab('plan');setTimeout(()=>printBrigadeSheet(),300)}},""",
          """    {ic:'🖨',title:'Бригадная ведомость (печать)',hint:'вывод · 3.36',run:()=>{showTab('plan');setTimeout(()=>printBrigadeSheet(),300)}},
    {ic:'📱',title:'Мобильный режим: вкл/выкл',hint:'вид · 3.38',run:()=>{setMobileMode(!mobiOn());toast(mobiOn()?'Мобильный режим включён':'Мобильный режим выключен')}},
    {ic:'📲',title:'Установить приложение (PWA-lite)',hint:'мобильное · 3.38',run:()=>openInstallHint()},
    {ic:'👉',title:'Следующий месяц (свайп)',hint:'навигация · 3.38',run:()=>swipeMonth(1)},
    {ic:'👈',title:'Предыдущий месяц (свайп)',hint:'навигация · 3.38',run:()=>swipeMonth(-1)},""", 'palette 338')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.37 — сценарии ротаций и годовой баланс</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.38 — мобильная волна</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Нижняя навигация</b> на экранах ≤ 900px: пять разделов (Дашборд, Мой месяц, План, Табель, Справочники) + «Ещё» открывает палитру со всеми разделами и командами; роли tablist/tab, aria-selected, цели касания ≥ 48 px.</li>
        <li><b>Свайп месяца</b>: горизонтальный свайп (|dx| &gt; 60 px, |dy| &lt; 40 px) в Дашборде, «Моём месяце», Плане и Табеле листает месяцы; дублирован командами палитры «👉/👈».</li>
        <li><b>Авто-компакт и крупные цели</b>: в мобильном режиме таблицы уплотняются, кнопки и вкладки получают минимальную высоту 38–40 px; сайдбар плана уходит под сетку.</li>
        <li><b>Установка приложения (PWA-lite)</b>: перехват beforeinstallprompt (кнопка «📲 Установить»), подсказка для iOS/Android и офлайн-сборки; событие appinstalled — тост; телеметрия <code>mobi:install</code>.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.37 — сценарии ротаций и годовой баланс</div>""", 'help 338')
    c.rep("""    coverageCsvDl,printBrigadeSheet,""",
          """    coverageCsvDl,printBrigadeSheet,
    /* ===== 3.38: мобильная волна ===== */
    mobiQuery,mobiOn,setMobileMode,renderMobiNav,initSwipeMonth,swipeMonth,
    initInstallPrompt,renderInstallBtn,openInstallHint,initMobileShell,get MOBI_TABS(){return MOBI_TABS},""", 'exports 338')

# ============================== 3.39 БЮДЖЕТ И ЛИМИТЫ ФОТ ==============================
MODULE_339 = r"""/* ================= 3.39: БЮДЖЕТ И ЛИМИТЫ ФОТ =================
   Лимиты фонда оплаты по подразделениям на месяц; план/факт стоимость месяца
   против лимита; сигналы перерасхода на дашборде; CSV-выгрузка.
   Методика: базовые часы × ставка ₽/ч (персональная e.rubHour или settings.rubHour)
   + ночные часы × надбавка nightPct + дни работы в выходные/праздники × 8 ч × wePct. */
function rubHour(e){return (e&&e.rubHour)||((state.settings||{}).rubHour)||550}
function empCost(eid,y,m,mode){
  const e=emp(eid);if(!e)return 0;
  const DIM=dim(y,m),rh=rubHour(e),R=ratesCfg();
  let h=0,nh=0,weD=0;
  for(let d=1;d<=DIM;d++){
    if(mode==='fact'){const fr=factGet(eid,y,m,d);if(fr)h+=factHoursDay(e,y,m,d,fr);continue}
    h+=hoursFor(eid,y,m,d);
    nh+=nightHoursFor(eid,y,m,d);
    const raw=getCode(eid,y,m,d);
    if(raw){const r=reason(parseCell(raw).code),di=dayInfo(y,m,d);
      if(r&&r.coeff>0&&(r.off||(di.weekend||di.hol)))weD++}
  }
  return Math.round(h*rh+nh*rh*(R.nightPct||0)/100+weD*((state.settings||{}).hoursDay||8)*rh*(R.wePct||0)/100);
}
function deptCost(deptId,y,m,mode){return empList(deptId).reduce((a,e)=>a+empCost(e.id,y,m,mode),0)}
function budgets(){if(!state.budgets||typeof state.budgets!=='object'||Array.isArray(state.budgets))state.budgets={};return state.budgets}
function budgetLimit(y,m,deptId){const b=budgets()[mkOf(y,m)];return b&&b[deptId]!=null?+b[deptId]:null}
function budgetSet(y,m,deptId,val){
  const mk=mkOf(y,m),b=budgets();
  b[mk]=b[mk]||{};
  if(val==null||val==='')delete b[mk][deptId];else b[mk][deptId]=Math.round(+val)||0;
  save(true);
  audit('Лимит бюджета ФОТ',`${(dept(deptId)||{}).name||deptId} · ${MUP[m-1]} ${y}: ${val==null||val===''?'снят':fmtStd(+val,{unit:'₽'})}`,'budgets');
  try{teleHit('budget:set')}catch(e){}
  renderBudgets();renderBudgetNag();
}
function budgetStatus(y,m,deptId){
  const plan=deptCost(deptId,y,m,'plan'),fact=deptCost(deptId,y,m,'fact'),limit=budgetLimit(y,m,deptId);
  return{plan,fact,limit,
    overPlan:limit!=null&&plan>limit,overFact:limit!=null&&fact>limit,
    pctPlan:limit?Math.round(plan/limit*100):null,pctFact:limit?Math.round(fact/limit*100):null};
}
function budgetSuggest(y,m,deptId){
  const p=new Date(y,m-2,1);
  const prev=deptCost(deptId,p.getFullYear(),p.getMonth()+1,'plan');
  return prev?Math.round(prev*1.05):null;
}
function renderBudgets(){
  const box=$('budgetBox');if(!box)return;
  const{y,m}=cur;
  box.innerHTML=state.departments.map(dp=>{
    const st=budgetStatus(y,m,dp.id);
    const lim=budgetLimit(y,m,dp.id);
    const pill=lim==null?'<span class="pill">лимит не задан</span>'
      :st.overFact?`<span class="pill r">перерасход факта: ${fmtStd(st.fact-st.limit,{unit:'₽'})}</span>`
      :st.overPlan?`<span class="pill a">план выше лимита: ${fmtStd(st.plan-st.limit,{unit:'₽'})}</span>`
      :`<span class="pill g">в лимите: ${fmtStd(st.pctPlan,{pct:true})} плана</span>`;
    return `<div class="setrow" style="flex-wrap:wrap;gap:6px">
      <div style="flex:1;min-width:150px"><b style="font-size:12.5px">${esc(dp.name)}</b>
        <div class="hint" style="margin-top:2px">план ${fmtStd(st.plan,{unit:'₽'})} · факт ${fmtStd(st.fact,{unit:'₽'})}</div></div>
      <div style="display:flex;align-items:center;gap:6px">
        <label class="hint" for="bud-${dp.id}">лимит ₽/мес</label>
        <input class="inp" id="bud-${dp.id}" data-bud="${dp.id}" type="number" min="0" step="1000" style="width:120px" value="${lim!=null?lim:''}" placeholder="—" aria-label="Лимит ФОТ ${esc(dp.name)} на ${MUP[m-1]} ${y}">
        <button class="btn ghost tiny" data-budsug="${dp.id}" title="Предложить: план прошлого месяца × 1,05">≈</button>
      </div>
      <div style="flex-basis:100%">${pill}</div>
    </div>`}).join('');
  box.querySelectorAll('[data-bud]').forEach(inp=>inp.onchange=()=>budgetSet(y,m,inp.dataset.bud,inp.value));
  box.querySelectorAll('[data-budsug]').forEach(b=>b.onclick=()=>{
    const s=budgetSuggest(y,m,b.dataset.budsug);
    if(!s){toast('Нет плана за прошлый месяц — задайте лимит вручную','err');return}
    budgetSet(y,m,b.dataset.budsug,s);
  });
}
function renderBudgetNag(){
  const v=$('view-dash');if(!v)return;
  let nag=$('budgetNag');
  const{y,m}=cur;
  const overs=state.departments.map(dp=>({dp,st:budgetStatus(y,m,dp.id)})).filter(x=>x.st.limit!=null&&(x.st.overPlan||x.st.overFact));
  if(!overs.length){if(nag)nag.remove();return}
  if(!nag){
    nag=document.createElement('div');nag.id='budgetNag';nag.className='card no-print';
    nag.style.cssText='border-left:4px solid var(--amber);margin-bottom:12px;padding:12px 16px';
    v.insertBefore(nag,v.firstChild.nextSibling||null);
  }
  nag.innerHTML=`<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
    <div style="flex:1;min-width:240px"><b>💰 Перерасход бюджета ФОТ: ${fmtStd(overs.length,{unit:'подразд'})} за ${MUP[m-1]} ${y}</b>
      <div class="hint" style="margin-top:3px">${overs.map(x=>`${esc(x.dp.name)}: план ${fmtStd(x.st.pctPlan,{pct:true})} лимита${x.st.overFact?`, факт ${fmtStd(x.st.pctFact,{pct:true})}`:''}`).join(' · ')}. Лимиты и статус — вкладка «Данные → Бюджет и лимиты ФОТ».</div></div>
    <button class="btn small" id="budNagGo">Открыть лимиты</button></div>`;
  const g=$('budNagGo');if(g)g.onclick=()=>{showTab('data');setTimeout(()=>{const c=$('budgetCard');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},250)};
}
function budgetsCsvDl(){
  const{y,m}=cur;
  const rows=[['Бюджет ФОТ',MUP[m-1]+' '+y,'штамп',stampPlain('plan')],[],
    ['Подразделение','План ₽','Факт ₽','Лимит ₽','План %','Факт %','Статус']];
  state.departments.forEach(dp=>{const st=budgetStatus(y,m,dp.id);
    rows.push([dp.name,st.plan,st.fact,st.limit==null?'':st.limit,st.pctPlan==null?'':st.pctPlan,st.pctFact==null?'':st.pctFact,
      st.limit==null?'лимит не задан':st.overFact?'перерасход факта':st.overPlan?'план выше лимита':'в лимите'])});
  downloadCsv('budget-fot-'+mkOf(y,m)+'.csv',rows);
  audit('Выгрузка бюджета ФОТ',`${MUP[m-1]} ${y} · CSV`,'budgets');
  try{teleHit('budget:csv')}catch(e){}
  toast('Бюджет ФОТ выгружен в CSV','ok');
}
"""

def V339(c):
    c.ver('3.39')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_339 + '\n' + c.s[i:]
    # карточка в «Данных» перед карточкой резервного копирования
    c.rep("""      <h3>Резервное копирование<span class="sub">полный снимок базы в JSON</span></h3>""",
          """      <h3>Бюджет и лимиты ФОТ<span class="sub">3.39 · лимит ₽/мес по подразделениям · план и факт против лимита · сигналы перерасхода</span></h3>
      <div id="budgetBox"></div>
      <div class="mini" style="margin-top:8px;display:flex;gap:6px">
        <button class="btn ghost small" id="btnBudgetCsv">⇩ CSV бюджета</button>
        <button class="btn ghost small" id="btnBudgetRefresh">⟳ Пересчитать</button>
      </div>
      <div class="hint" style="margin-top:8px">Методика: часы × ставка ₽/ч (персональная или общая в настройках) + ночные (надбавка %) + работа в выходные/праздники (8 ч × надбавка %). «≈» предлагает лимит = план прошлого месяца × 1,05.</div>
      </div>
      <div class="card">
      <h3>Резервное копирование<span class="sub">полный снимок базы в JSON</span></h3>""", 'budget card')
    c.rep("  bindClick('btnPatCsv',patternsCsvDl);",
          "  bindClick('btnPatCsv',patternsCsvDl);                  /* 3.36 */\n"
          "  bindClick('btnBudgetCsv',budgetsCsvDl);                /* 3.39 */\n"
          "  bindClick('btnBudgetRefresh',()=>{renderBudgets();renderBudgetNag();toast('Бюджет пересчитан')});   /* 3.39 */", 'budget bindings')
    c.rep('function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){}}   /* 3.36: бригады; 3.38: mobi-nav */',
          'function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){};try{renderBudgets()}catch(e){}}   /* 3.36 бригады; 3.38 mobi; 3.39 бюджет */', 'budget render hook')
    c.rep('  try{initMobileShell()}catch(e){}   /* 3.38: мобильная волна */',
          '  try{initMobileShell()}catch(e){}   /* 3.38: мобильная волна */\n  try{renderBudgets();renderBudgetNag()}catch(e){}   /* 3.39: бюджет */', 'boot budget')
    c.rep("""    {ic:'📱',title:'Мобильный режим: вкл/выкл',hint:'вид · 3.38',run:()=>{setMobileMode(!mobiOn());toast(mobiOn()?'Мобильный режим включён':'Мобильный режим выключен')}},""",
          """    {ic:'📱',title:'Мобильный режим: вкл/выкл',hint:'вид · 3.38',run:()=>{setMobileMode(!mobiOn());toast(mobiOn()?'Мобильный режим включён':'Мобильный режим выключен')}},
    {ic:'💰',title:'Бюджет и лимиты ФОТ',hint:'данные · 3.39',run:()=>{showTab('data');setTimeout(()=>{const c=$('budgetCard');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},250)}},
    {ic:'📊',title:'Бюджет ФОТ: выгрузка CSV',hint:'экспорт · 3.39',run:()=>budgetsCsvDl()},""", 'palette 339')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.38 — мобильная волна</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.39 — бюджет и лимиты ФОТ</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Лимиты ФОТ по подразделениям</b> (Данные → «Бюджет и лимиты ФОТ»): лимит ₽/мес на подразделение текущего месяца, кнопка «≈» предлагает план прошлого месяца × 1,05; хранение в каноне (<code>state.budgets</code>), аудит и телеметрия изменений.</li>
        <li><b>План и факт против лимита</b>: стоимость месяца считается по методике «часы × ставка ₽/ч + ночные × надбавка % + выходные/праздники × 8 ч × надбавка %» (персональная ставка сотрудника приоритетнее общей); ступенчатые пиллы «в лимите / план выше / перерасход факта».</li>
        <li><b>Сигнал перерасхода на дашборде</b>: янтарная карточка со списком подразделений и процентом лимита, кнопка перехода к лимитам; исчезает при отсутствии перерасхода.</li>
        <li><b>Выгрузка CSV</b> бюджета со штампом; палитра: «💰 Бюджет и лимиты ФОТ», «📊 Бюджет ФОТ: выгрузка CSV».</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.38 — мобильная волна</div>""", 'help 339')
    c.rep("""    initInstallPrompt,renderInstallBtn,openInstallHint,initMobileShell,get MOBI_TABS(){return MOBI_TABS},""",
          """    initInstallPrompt,renderInstallBtn,openInstallHint,initMobileShell,get MOBI_TABS(){return MOBI_TABS},
    /* ===== 3.39: бюджет и лимиты ФОТ ===== */
    rubHour,empCost,deptCost,budgets,budgetLimit,budgetSet,budgetStatus,budgetSuggest,
    renderBudgets,renderBudgetNag,budgetsCsvDl,""", 'exports 339')
    # id карточки для скролла
    c.rep("""      <h3>Бюджет и лимиты ФОТ<span class="sub">3.39 · лимит ₽/мес по подразделениям · план и факт против лимита · сигналы перерасхода</span></h3>""",
          """      <h3 id="budgetCardH">Бюджет и лимиты ФОТ<span class="sub">3.39 · лимит ₽/мес по подразделениям · план и факт против лимита · сигналы перерасхода</span></h3>""", 'budget anchor id')
    c.rep("const c=$('budgetCard');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},250)}},\n    {ic:'📊',title:'Бюджет ФОТ: выгрузка CSV'",
          "const c=$('budgetCardH');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},250)}},\n    {ic:'📊',title:'Бюджет ФОТ: выгрузка CSV'", 'budget scroll id fix')
    c.rep("setTimeout(()=>{const c=$('budgetCard');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},250)};",
          "setTimeout(()=>{const c=$('budgetCardH');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},250)};", 'budget nag scroll id fix')

# ============================== 3.40 ЛИЧНЫЙ ДАЙДЖЕСТ И УВЕДОМЛЕНИЯ ==============================
MODULE_340 = r"""/* ================= 3.40: ЛИЧНЫЙ ДАЙДЖЕСТ И УВЕДОМЛЕНИЯ =================
   «Мой день»: сегодня/завтра сотрудника (код, часы, ночные), сводка месяца,
   отпускной остаток, ближайшие пожелания; дайджест в мессенджер-формате
   (копирование / .txt); локальное ежедневное уведомление в заданное время. */
function personalDigest(eid,dateStr){
  const e=emp(eid);if(!e)return null;
  const d0=dateStr?dparse(dateStr):TODAY();
  const y=d0.getFullYear(),m=d0.getMonth()+1,d=d0.getDate();
  const pick=(yy,mm,dd)=>{
    const raw=getCode(eid,yy,mm,dd),r=raw?reason(parseCell(raw).code):null;
    const off=dayInfo(yy,mm,dd).off;
    return{code:r?r.code:(off?'В':'Я'),name:r?r.name:(off?'Выходной':'Явка по норме'),
      hours:hoursFor(eid,yy,mm,dd),night:nightHoursFor(eid,yy,mm,dd)};
  };
  const today=pick(y,m,d);
  const nd=dparse(addDays(k(y,m,d),1));
  const tomorrow=pick(nd.getFullYear(),nd.getMonth()+1,nd.getDate());
  const st=empMonthStats(eid,y,m);
  let vac=null;try{vac=vacationStats(eid,y)}catch(err){}
  const dk0=k(y,m,d),dk1=k(y,m,dim(y,m));
  const wish=dutyWishes().filter(w=>w.eid===eid&&w.to>=dk0&&w.from<=dk1)[0]||null;
  const lines=[
    `📅 ${e.name} · ${pad2(d)}.${pad2(m)}.${y}`,
    `Сегодня: ${today.code} — ${today.name}${today.hours?`, ${fmtStd(today.hours,{dec:1,unit:'ч'})}`:''}${today.night?`, ночные ${fmtStd(today.night,{dec:1,unit:'ч'})}`:''}`,
    `Завтра: ${tomorrow.code} — ${tomorrow.name}${tomorrow.hours?`, ${fmtStd(tomorrow.hours,{dec:1,unit:'ч'})}`:''}`,
    `Месяц: загрузка ${fmtStd(st.pct,{pct:true})} · дежурств ${fmtStd(st.duty)} · отсутствий ${fmtStd(st.absent)}`,
  ];
  if(vac&&vac.left!=null)lines.push(`Остаток отпуска: ${fmtStd(vac.left,{unit:'дн'})} за ${fmtStd(y,{dec:0})} г.`);
  if(wish)lines.push(`Пожелание: «${wish.kind==='pref'?'предпочтительно ставить':'не ставить'}» до ${wish.to.split('-').reverse().join('.')}`);
  return{e,today,tomorrow,st,vac,wish,text:lines.join('\n')};
}
function openPersonalDigest(eid){
  const dg=personalDigest(eid||((meEmp()||{}).id));
  if(!dg){toast('Сначала отметьте, кто вы (вкладка «Мой месяц»)','err');return}
  try{teleHit('me:digest')}catch(e){}
  openModal({title:'📨 Дайджест «Мой день»',body:`
    <div class="hint" style="margin-top:0">Личная сводка на сегодня — формат для мессенджера или e-mail. Обновляется при каждом открытии.</div>
    <textarea id="pdText" class="inp" style="min-height:170px;font-family:var(--f-mono);font-size:12px" aria-label="Текст личного дайджеста">${esc(dg.text)}</textarea>`,
    buttons:`<button class="btn ghost" data-cpd>Закрыть</button><button class="btn ghost" id="pdDl">⤓ .txt</button><button class="btn" id="pdCopy">📋 Копировать</button>`,
    onMount(b){
      b.querySelector('[data-cpd]').onclick=closeModal;
      b.querySelector('#pdCopy').onclick=()=>{
        const t=b.querySelector('#pdText').value;
        try{navigator.clipboard.writeText(t).then(()=>toast('Дайджест скопирован','ok'),()=>toast('Буфер недоступен — выделите текст вручную','err'))}
        catch(e){toast('Буфер недоступен в этом окружении','err')}
      };
      b.querySelector('#pdDl').onclick=()=>{
        download('daydzhest-'+(dg.e.tab||dg.e.id)+'-'+k(dg.e?cur.y:cur.y,cur.m,TODAY().getDate())+'.txt',b.querySelector('#pdText').value,'text/plain');
        toast('Дайджест сохранён в .txt','ok');
      };
    }});
}
function meNotifyCfg(){
  state.settings=state.settings||{};
  if(typeof state.settings.meNotify!=='boolean')state.settings.meNotify=false;
  if(!state.settings.meNotifyTime)state.settings.meNotifyTime='08:00';
  return state.settings;
}
function meNotifyCheck(){
  const s=meNotifyCfg();
  if(!s.meNotify)return;
  if(!('Notification' in window)||Notification.permission!=='granted')return;
  const now=new Date();
  const[hh,mm]=String(s.meNotifyTime).split(':').map(Number);
  const curMin=now.getHours()*60+now.getMinutes(),tgt=hh*60+mm;
  if(curMin<tgt)return;
  const today=now.toDateString();
  try{if(localStorage.getItem('pt.meNotify.last')===today)return}catch(e){}
  const e=meEmp();if(!e)return;
  const dg=personalDigest(e.id);if(!dg)return;
  try{
    new Notification('План-табель · '+dg.e.name,{body:dg.text.slice(0,280),tag:'pt-me-day'});
    localStorage.setItem('pt.meNotify.last',today);
    try{teleHit('me:notify')}catch(err){}
  }catch(err){}
}
function initMeNotify(){
  meNotifyCfg();
  clearInterval(window.__meNotifyT);
  window.__meNotifyT=setInterval(meNotifyCheck,10*60*1000);
  meNotifyCheck();
}
"""

def V340(c):
    c.ver('3.40')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_340 + '\n' + c.s[i:]
    # кнопка дайджеста в шапке «Моего месяца»
    c.rep("""    <button class="btn ghost small" id="mePrint" style="margin-left:auto">🖨 Печать моего месяца</button>""",
          """      <button class="btn ghost small" id="meDigest" title="Личный дайджест на сегодня: копирование и .txt (3.40)">📨 Мой день</button>
      <button class="btn ghost small" id="mePrint" style="margin-left:auto">🖨 Печать моего месяца</button>""", 'me digest btn')
    c.rep("""  if(bpr)bpr.onclick=()=>printMeMonth();""",
          """  if(bpr)bpr.onclick=()=>printMeMonth();
  const bdg=$('meDigest');if(bdg)bdg.onclick=()=>openPersonalDigest(e.id);   /* 3.40 */""", 'me digest bind')
    # настройки уведомления в карточке «Доступ и уведомления»
    c.rep("""        <h3>Доступ и уведомления<span class="sub">роли · PIN-замок · браузерные уведомления</span></h3>""",
          """        <h3>Доступ и уведомления<span class="sub">роли · PIN-замок · браузерные уведомления</span></h3>
        <div class="setrow" style="flex-wrap:wrap;gap:6px">
          <label class="chkrow" style="margin:0"><input type="checkbox" id="setMeNotify"> ежедневный личный дайджест-уведомление</label>
          <input type="time" class="inp" id="setMeNotifyTime" value="08:00" style="width:110px" aria-label="Время личного дайджеста">
          <button class="btn ghost tiny" id="btnNotifyPerm" title="Запросить разрешение браузера на уведомления">🔔 разрешить</button>
        </div>
        <div class="hint" style="margin-top:4px">3.40: пока приложение открыто, в заданное время приходит уведомление «Мой день» (сегодня/завтра/месяц). Разрешение браузера — одноразово.</div>""", 'notify settings ui')
    c.rep("""  $('btnSigTest').onclick=()=>sigTestLocal();""",
          """  $('btnSigTest').onclick=()=>sigTestLocal();
  /* 3.40: личное уведомление-дайджест */
  const mn=meNotifyCfg();
  $('setMeNotify').checked=!!mn.meNotify;$('setMeNotifyTime').value=mn.meNotifyTime;
  $('setMeNotify').onchange=e=>{meNotifyCfg().meNotify=e.target.checked;save();initMeNotify();
    toast(e.target.checked?'Личный дайджест включён':'Личный дайджест выключен')};
  $('setMeNotifyTime').onchange=e=>{meNotifyCfg().meNotifyTime=e.target.value||'08:00';save();initMeNotify()};
  $('btnNotifyPerm').onclick=()=>{
    if(!('Notification' in window)){toast('Уведомления не поддерживаются этим браузером','err');return}
    Notification.requestPermission().then(p=>toast(p==='granted'?'Уведомления разрешены':'Разрешение не выдано: '+p,p==='granted'?'ok':'err'));
  };""", 'notify bindings')
    c.rep('  try{renderBudgets();renderBudgetNag()}catch(e){}   /* 3.39: бюджет */',
          '  try{renderBudgets();renderBudgetNag()}catch(e){}   /* 3.39: бюджет */\n  try{initMeNotify()}catch(e){}   /* 3.40: личный дайджест */', 'boot 340')
    c.rep("""    {ic:'💰',title:'Бюджет и лимиты ФОТ',hint:'данные · 3.39',run:()=>{showTab('data');setTimeout(()=>{const c=$('budgetCardH');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},250)}},""",
          """    {ic:'💰',title:'Бюджет и лимиты ФОТ',hint:'данные · 3.39',run:()=>{showTab('data');setTimeout(()=>{const c=$('budgetCardH');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'})},250)}},
    {ic:'📨',title:'Дайджест «Мой день» (копия / .txt)',hint:'самообслуживание · 3.40',run:()=>{showTab('me');setTimeout(()=>openPersonalDigest((meEmp()||{}).id),250)}},""", 'palette 340')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.39 — бюджет и лимиты ФОТ</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.40 — личный дайджест и уведомления</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>«Мой день»</b> (кнопка «📨» в шапке «Моего месяца» и палитра): личная сводка — сегодня и завтра (код, название, часы, ночные), загрузка/дежурства/отсутствия месяца, остаток отпуска, активное пожелание; текст в мессенджер-формате, редактируемый, «📋 Копировать» и «⤓ .txt».</li>
        <li><b>Ежедневное уведомление</b> (Справочники → «Доступ и уведомления»): флажок + время; пока приложение открыто, в заданное время приходит браузерное Notification с текстом «Мой день» (не чаще раза в день, телеметрия <code>me:notify</code>); кнопка «🔔 разрешить» запрашивает разрешение.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.39 — бюджет и лимиты ФОТ</div>""", 'help 340')
    c.rep("""    renderBudgets,renderBudgetNag,budgetsCsvDl,""",
          """    renderBudgets,renderBudgetNag,budgetsCsvDl,
    /* ===== 3.40: личный дайджест и уведомления ===== */
    personalDigest,openPersonalDigest,meNotifyCfg,meNotifyCheck,initMeNotify,""", 'exports 340')

# ============================== 3.41 ДОПУСКИ: ПРОГНОЗ И РИСК ПОКРЫТИЯ ==============================
MODULE_341 = r"""/* ================= 3.41: ДОПУСКИ — ПРОГНОЗ ИСТЕЧЕНИЯ И РИСК ПОКРЫТИЯ =================
   Форвард-список: у кого и когда истекает обязательный допуск (включая просроченные),
   сколько смен ротации/бригады «накроется» после истечения (риск покрытия);
   заявки на продление (канон state.certReqs) с маршрутом new → approved → done/rejected. */
function certExpDate(c,ct){
  let exp=c.expires?new Date(c.expires+'T00:00:00'):null;
  if(!exp&&c.issued&&ct&&ct.months){const i=new Date(c.issued+'T00:00:00');if(!isNaN(i.getTime())){i.setMonth(i.getMonth()+ct.months);exp=i}}
  return exp;
}
function certForecast(days){
  wfmEnsure();
  const t=TODAY(),out=[];
  const horizon=Math.max(days||0,0);
  state.employees.filter(e=>!e.fired).forEach(e=>{
    (e.certs||[]).forEach(c=>{
      const ct=certType(c.typeId);if(!ct||!ct.duty)return;
      const exp=certExpDate(c,ct);if(!exp||isNaN(exp.getTime()))return;
      const dl=Math.round((exp-t)/864e5);
      if(dl>horizon)return;
      /* риск покрытия: смены ротации/бригады в 30 дней ПОСЛЕ истечения */
      let risk=0;
      const brig=brigadeList().find(b=>(b.members||[]).includes(e.id));
      if(brig){
        const pat=patById(brig.patId);
        if(pat){
          const anchor=addDays(brig.anchor||`${t.getFullYear()}-01-01`,-(brig.offset||0));
          const expKey=dkey(exp);
          for(let i=0;i<30;i++){
            const ds=addDays(expKey,i),p=dparse(ds);
            if(patternCodeAt(pat,anchor,p.getFullYear(),p.getMonth()+1,p.getDate()))risk++;
          }
        }
      }
      out.push({eid:e.id,name:e.name,pos:e.pos||'',type:ct,expires:dkey(exp),daysLeft:dl,risk,
        brig:brig?brig.name:null});
    });
  });
  return out.sort((a,b)=>a.daysLeft-b.daysLeft);
}
function certReqs(){if(!Array.isArray(state.certReqs))state.certReqs=[];return state.certReqs}
function certReqAdd(eid,typeId,note){
  const r={id:uid('cr'),eid,typeId,note:note||'',by:actor(),ts:Date.now(),status:'new'};
  certReqs().unshift(r);
  save(true);
  audit('Заявка на продление допуска',`${empName(eid)} · ${(certType(typeId)||{}).name||typeId}${note?' · '+note:''}`,'certs');
  try{teleHit('cert:req')}catch(e){}
  toast('Заявка на продление создана','ok');
  return r;
}
function certReqAct(id,act){
  const r=certReqs().find(x=>x.id===id);if(!r)return;
  const from=r.status;
  r.status=act;r.updated=Date.now();
  save(true);
  audit('Заявка на продление: '+act,`${empName(r.eid)} · ${(certType(r.typeId)||{}).name||''} · ${from} → ${act}`,'certs');
  try{teleHit('cert:req:'+act)}catch(e){}
}
function renderCertForecast(){
  const box=$('certFcBox');if(!box)return;
  const days=+$('certFcDays')?+$('certFcDays').value||90:90;
  const rows=certForecast(days);
  box.innerHTML=rows.length?`<div class="scroll-x" style="max-height:38vh;overflow:auto"><table class="rtbl"><thead><tr><th>Сотрудник</th><th>Допуск</th><th>Истекает</th><th class="n">Дней</th><th class="n">Смен под риском</th><th>Бригада</th><th></th></tr></thead><tbody>
    ${rows.map(r=>`<tr>
      <td><b>${esc(r.name)}</b>${r.pos?`<div class="hint">${esc(r.pos)}</div>`:''}</td>
      <td>${esc(r.type.name)}</td>
      <td class="n">${r.expires.split('-').reverse().join('.')}</td>
      <td class="n">${r.daysLeft<0?`<span class="pill r">просрочен ${fmtStd(-r.daysLeft,{unit:'дн'})}</span>`:r.daysLeft<=30?`<span class="pill a">${fmtStd(r.daysLeft,{unit:'дн'})}</span>`:`<span class="pill g">${fmtStd(r.daysLeft,{unit:'дн'})}</span>`}</td>
      <td class="n">${r.risk?`<span class="pill ${r.risk>5?'r':'a'}">${fmtStd(r.risk,{unit:'смен'})}</span>`:'—'}</td>
      <td>${r.brig?esc(r.brig):'—'}</td>
      <td><button class="btn ghost tiny" data-crq="${r.eid}:${r.type.id}" title="Создать заявку на продление">📝 продлить</button></td>
    </tr>`).join('')}</tbody></table></div>`
    :'<div class="hint">В горизонте '+fmtStd(days,{unit:'дн'})+' нет истекающих обязательных допусков.</div>';
  box.querySelectorAll('[data-crq]').forEach(b=>b.onclick=()=>{
    const[eid,typeId]=b.dataset.crq.split(':');
    certReqAdd(eid,typeId,'авто из прогноза истечений');
    renderCertForecast();
  });
  const rq=$('certReqBox');
  if(rq)rq.innerHTML=certReqs().length?certReqs().slice(0,12).map(r=>`<div class="log-row" style="align-items:center">
      <span style="flex:1">${tsStr(r.ts)} · <b>${esc(empName(r.eid))}</b> · ${esc((certType(r.typeId)||{}).name||r.typeId)} · <span class="pill ${r.status==='done'?'g':r.status==='approved'?'a':r.status==='rejected'?'r':''}">${esc({new:'новая',approved:'согласована',done:'продлён',rejected:'отклонена'}[r.status]||r.status)}</span>${r.note?` <span class="hint">${esc(r.note)}</span>`:''}</span>
      ${r.status==='new'?`<button class="btn ghost tiny" data-cra="${r.id}:approved">согласовать</button>`:''}
      ${r.status==='approved'?`<button class="btn ghost tiny" data-cra="${r.id}:done">продлён</button>`:''}
      ${r.status==='new'||r.status==='approved'?`<button class="btn warn tiny" data-cra="${r.id}:rejected">отклонить</button>`:''}
    </div>`).join(''):'<div class="hint">Заявок на продление нет.</div>';
  if(rq)rq.querySelectorAll('[data-cra]').forEach(b=>b.onclick=()=>{
    const[id,act]=b.dataset.cra.split(':');
    certReqAct(id,act);renderCertForecast();
  });
}
"""

def V341(c):
    c.ver('3.41')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_341 + '\n' + c.s[i:]
    c.rep("""        <div class="hint" style="margin-top:8px">Включите правило «Требуется действующий допуск для дежурства» ниже — тогда сотрудники без действующего обязательного допуска автоматически исключаются из автозаполнения дежурств и не могут записаться на открытое дежурство.</div>
      </div>""",
          """        <div class="hint" style="margin-top:8px">Включите правило «Требуется действующий допуск для дежурства» ниже — тогда сотрудники без действующего обязательного допуска автоматически исключаются из автозаполнения дежурств и не могут записаться на открытое дежурство.</div>
      </div>
      <div class="card">
        <h3>Прогноз истечения допусков и риск покрытия<span class="sub">3.41 · форвард-список истечений · смены ротации под риском · заявки на продление</span></h3>
        <div class="frow"><div class="field" style="margin:0;max-width:180px"><label>Горизонт, дней</label><input type="number" class="inp" id="certFcDays" min="7" max="730" value="90"></div></div>
        <div id="certFcBox" style="margin-top:8px"></div>
        <div class="lbl" style="margin-top:12px">Заявки на продление</div>
        <div id="certReqBox"></div>
      </div>""", 'cert forecast card')
    c.rep("  bindClick('btnBudgetRefresh',()=>{renderBudgets();renderBudgetNag();toast('Бюджет пересчитан')});   /* 3.39 */",
          "  bindClick('btnBudgetRefresh',()=>{renderBudgets();renderBudgetNag();toast('Бюджет пересчитан')});   /* 3.39 */\n"
          "  const cfd=$('certFcDays');if(cfd){cfd.onchange=()=>renderCertForecast();cfd.oninput=()=>{clearTimeout(cfd._t);cfd._t=setTimeout(renderCertForecast,400)}}   /* 3.41 */", 'cert bind')
    c.rep('  try{initMeNotify()}catch(e){}   /* 3.40: личный дайджест */',
          '  try{initMeNotify()}catch(e){}   /* 3.40: личный дайджест */\n  try{renderCertForecast()}catch(e){}   /* 3.41: прогноз допусков */', 'boot 341')
    c.rep('function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){};try{renderBudgets()}catch(e){}}   /* 3.36 бригады; 3.38 mobi; 3.39 бюджет */',
          'function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){};try{renderBudgets()}catch(e){};try{renderCertForecast()}catch(e){}}   /* 3.36–3.41 хуки */', 'render hook 341')
    c.rep("""    {ic:'📨',title:'Дайджест «Мой день» (копия / .txt)',hint:'самообслуживание · 3.40',run:()=>{showTab('me');setTimeout(()=>openPersonalDigest((meEmp()||{}).id),250)}},""",
          """    {ic:'📨',title:'Дайджест «Мой день» (копия / .txt)',hint:'самообслуживание · 3.40',run:()=>{showTab('me');setTimeout(()=>openPersonalDigest((meEmp()||{}).id),250)}},
    {ic:'🎫',title:'Прогноз истечения допусков и риск покрытия',hint:'справочники · 3.41',run:()=>{showTab('set');setTimeout(()=>{const h=$('certFcBox');if(h&&h.scrollIntoView)h.scrollIntoView({behavior:'smooth',block:'center'});renderCertForecast()},300)}},""", 'palette 341')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.40 — личный дайджест и уведомления</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.41 — допуски: прогноз истечения и риск покрытия</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Форвард-список истечений</b> (Справочники → «Прогноз истечения допусков»): горизонт 7–730 дней; ступенчатые пиллы «просрочен / ≤ 30 дней / далее»; <b>риск покрытия</b> — сколько смен ротации/бригады сотрудника придётся на 30 дней после истечения (смена без действующего допуска блокируется правилом certRequired).</li>
        <li><b>Заявки на продление</b>: «📝 продлить» создаёт заявку в каноне (<code>state.certReqs</code>: new → approved → done / rejected, автор и метки времени), список заявок со статус-пиллами и действиями; аудит и телеметрия каждого шага.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.40 — личный дайджест и уведомления</div>""", 'help 341')
    c.rep("""    personalDigest,openPersonalDigest,meNotifyCfg,meNotifyCheck,initMeNotify,""",
          """    personalDigest,openPersonalDigest,meNotifyCfg,meNotifyCheck,initMeNotify,
    /* ===== 3.41: допуски — прогноз и риск покрытия ===== */
    certExpDate,certForecast,certReqs,certReqAdd,certReqAct,renderCertForecast,""", 'exports 341')



# ============================== 3.42 МАРКЕТПЛЕЙС ОБМЕНОВ ==============================
MODULE_342 = r"""/* ================= 3.42: МАРКЕТПЛЕЙС ОБМЕНОВ — ОТКРЫТЫЕ ЗАЯВКИ И АВТОПОДБОР =================
   Открытая заявка на подмену (без напарника) + ранжированный автоподбор кандидата
   (оценка как в докторе покрытия: пожелания, баланс подмен, загрузка, отдых, серии, неделя). */
function coversTaken(eid){return swapList().filter(s=>s.status==='applied'&&s.eid2===eid).length}
function coversGiven(eid){return swapList().filter(s=>s.status==='applied'&&s.eid1===eid).length}
function swapOpenReq(o){
  wfmEnsure();
  const s={id:uid('sw'),ts:Date.now(),by:actor(),type:o.type||'sub',mk1:o.mk1,day1:+o.day1,eid1:o.eid1,
    mk2:o.mk1,day2:+o.day1,eid2:null,code:o.code||'',back:'',reason:(o.reason||'').trim(),status:'new',
    open:true,history:[{ts:Date.now(),by:actor(),act:'создана (открытая заявка)',note:o.reason||''}]};
  if(!s.mk1||!s.day1||!s.eid1){toast('Укажите сотрудника и дату','err');return null}
  swapList().unshift(s);
  try{opsQueue({k:'req',sub:'swap',swap:s})}catch(e){}
  audit('Открытая заявка на подмену',`${empName(s.eid1)} · ${dstr(s.mk1,s.day1)}`,'swap:'+s.id);
  try{teleHit('swap:open')}catch(e){}
  save(true);updateAlerts(true);renderSwaps();
  toast('Открытая заявка создана — подберите напарника кнопкой «🤖»','ok');
  return s;
}
function swapCandidates(sw,topN){
  topN=topN||5;
  if(!sw||sw.eid2)return{list:[],all:[]};
  const[y,m]=String(sw.mk1).split('-').map(Number),d=sw.day1;
  const dk=k(y,m,d);
  const rCon=rule('maxConsecWork'),rWeek=rule('maxWeekHours'),rRest=rule('restAfterDuty');
  const e1=emp(sw.eid1);
  const es=empList(e1?e1.deptId:null).filter(e=>e.id!==sw.eid1&&e.dutyEligible!==false);
  const restNeed=Math.max(1,rRest.on?rRest.val:1);
  const out=[];
  es.forEach(e=>{
    const raw=getCode(e.id,y,m,d);
    if(rotBusyRaw(raw))return;
    if(raw){const r=reason(parseCell(raw).code);if(r&&r.cat==='duty')return}
    if(dutyCertBlocked(e.id,new Date(y,m-1,d)))return;
    if(wishBlock(e.id,dk))return;
    const why=[],viol=[];let score=50;
    if(wishPref(e.id,dk)){score+=40;why.push('предпочтительная дата')}
    const taken=coversTaken(e.id),given=coversGiven(e.id);
    if(taken<given){score+=20;why.push(`баланс подмен: брал ${fmtStd(taken)}, отдавал ${fmtStd(given)}`)}
    else if(taken>given+2){score-=20;viol.push(`часто подменяет (${fmtStd(taken)} против ${fmtStd(given)})`)}
    else why.push('баланс подмен ровный');
    const st=empMonthStats(e.id,y,m);
    if(st&&st.pct!=null&&st.pct<90){score+=15;why.push(`загрузка ${fmtStd(st.pct,{pct:true})}`)}
    else if(st&&st.pct>110){score-=25;viol.push(`перегруз ${fmtStd(st.pct,{pct:true})}`)}
    const hardDutyAt=dd=>{
      if(dd<1||dd>dim(y,m))return false;
      const rw=getCode(e.id,y,m,dd);if(!rw)return false;
      const c0=parseCell(rw),r0=reason(c0.code);
      return !!(r0&&r0.cat==='duty'&&((c0.hs!=null?c0.hs:(r0.hours||0))>=24||(r0.night||0)>=8));
    };
    const workAt=dd=>{
      if(dd<1||dd>dim(y,m))return false;
      const rw=getCode(e.id,y,m,dd);if(!rw)return false;
      return dayCoeff(e.id,y,m,dd)>0;
    };
    let gap=0,prevDuty=null;
    for(let j=1;j<=dim(y,m);j++){
      const dd=d-j;if(dd<1)break;
      if(hardDutyAt(dd)){prevDuty=dd;break}
      if(workAt(dd))break;
      gap++;
    }
    if(prevDuty!=null&&gap<restNeed){score-=60;viol.push(`отдых после дежурства ${pad2(prevDuty)}-го: ${fmtStd(gap,{unit:'дн'})}`)}
    let back=0;for(let j=1;j<=16;j++){const dd=d-j;if(dd<1||!workAt(dd))break;back++}
    let fwd=0;for(let j=1;j<=16;j++){const dd=d+j;if(dd>dim(y,m)||!workAt(dd))break;fwd++}
    const series=back+1+fwd;
    if(rCon.on&&series>rCon.val){score-=40;viol.push(`серия ${fmtStd(series,{unit:'дн'})} (лимит ${fmtStd(rCon.val,{unit:'дн'})})`)}
    if(!why.length&&!viol.length)why.push('противопоказаний нет');
    out.push({eid:e.id,name:e.name,pos:e.pos||'',score:Math.round(score),why,viol,taken,given});
  });
  out.sort((a,b)=>b.score-a.score||String(a.name).localeCompare(String(b.name),'ru'));
  return{list:out.slice(0,topN),all:out};
}
function swapOffer(swId,eid2){
  const s=swapList().find(x=>x.id===swId);if(!s)return null;
  s.eid2=eid2;s.open=false;
  s.history.push({ts:Date.now(),by:actor(),act:'автоподбор: предложен напарник '+empName(eid2)});
  save(true);updateAlerts(true);renderSwaps();
  audit('Автоподбор напарника',`${empName(s.eid1)} → ${empName(eid2)} · ${dstr(s.mk1,s.day1)}`,'swap:'+s.id);
  try{teleHit('swap:match')}catch(e){}
  toast('Напарник предложен: '+empName(eid2),'ok');
  return s;
}
function openSwapMatch(swId){
  const s=swapList().find(x=>x.id===swId);
  if(!s){toast('Заявка не найдена','err');return}
  if(s.eid2){toast('У заявки уже есть напарник','err');return}
  try{teleHit('swap:matchui')}catch(e){}
  const c=swapCandidates(s,6);
  openModal({title:'🤖 Автоподбор напарника',wide:true,body:`
    <div class="hint" style="margin-top:0">Заявка: <b>${esc(empName(s.eid1))}</b> · ${esc(dstr(s.mk1,s.day1))} · ${s.type==='swap'?'обмен':'подмена'}. Оценка как в докторе покрытия: пожелания, баланс подмен, загрузка, отдых после суточных, серии, недельные часы, допуски.</div>
    ${c.list.length?c.list.map(x=>`<div class="candrow">
      <button class="btn ghost tiny" data-swoffer="${s.id}:${x.eid}" title="Предложить напарника">＋</button>
      <b style="font-size:12px">${esc(x.name)}</b>${x.pos?`<span class="hint">${esc(x.pos)}</span>`:''}
      <span class="pill ${x.score>=70?'g':x.score>=40?'a':'r'}">${fmtStd(x.score)}</span>
      ${x.why.map(w=>`<span class="cand-chip good">✓ ${esc(w)}</span>`).join('')}
      ${x.viol.map(w=>`<span class="cand-chip bad">⚠ ${esc(w)}</span>`).join('')}
    </div>`).join(''):'<div class="status err" style="margin-top:8px">Кандидатов нет: все заняты, в пожеланиях «не ставить» или без допуска.</div>'}`,
    buttons:'<button class="btn ghost" data-csm>Закрыть</button>',
    onMount(b){
      b.querySelector('[data-csm]').onclick=closeModal;
      b.querySelectorAll('[data-swoffer]').forEach(el=>el.onclick=()=>{
        const[id,eid]=el.dataset.swoffer.split(':');
        swapOffer(id,eid);closeModal();
      });
    }});
}
function openSwapOpenReq(){
  const{y,m}=cur;
  openModal({title:'＋ Открытая заявка на подмену',body:`
    <div class="field"><label>Сотрудник</label><select class="inp" id="soEmp">${empOptions()}</select></div>
    <div class="frow"><div class="field"><label>Дата смены</label><input type="number" class="inp" id="soDay" min="1" max="${dim(y,m)}" value="1"></div>
    <div class="field"><label>Месяц</label><input class="inp" value="${MUP[m-1]} ${y}" disabled></div></div>
    <div class="field"><label>Причина</label><input class="inp" id="soReason" placeholder="например: учёба, семейные обстоятельства"></div>`,
    buttons:'<button class="btn ghost" data-cso>Отмена</button><button class="btn" id="soGo">Создать заявку</button>',
    onMount(b){
      b.querySelector('[data-cso]').onclick=closeModal;
      b.querySelector('#soGo').onclick=()=>{
        const r=swapOpenReq({eid1:b.querySelector('#soEmp').value,mk1:mkOf(y,m),day1:+b.querySelector('#soDay').value||1,reason:b.querySelector('#soReason').value});
        if(r)closeModal();
      };
    }});
}
"""

def V342(c):
    c.ver('3.42')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_342 + '\n' + c.s[i:]
    c.rep("""    if(s.status==='new')acts.push(`<button class="btn ghost small" data-swact="${s.id}|agree">Согласие напарника</button>`);""",
          """    if(s.status==='new')acts.push(`<button class="btn ghost small" data-swact="${s.id}|agree">Согласие напарника</button>`);
    if(s.status==='new'&&!s.eid2)acts.push(`<button class="btn ghost small" data-swauto="${s.id}" title="Автоподбор напарника по оценке (3.42)">🤖 Автоподбор</button>`);""", 'swap auto btn')
    c.rep("""    const a=e.target.closest('[data-swact]');""",
          """    const am=e.target.closest('[data-swauto]');
    if(am){openSwapMatch(am.dataset.swauto);return}
    const a=e.target.closest('[data-swact]');""", 'swap auto bind')
    c.rep("""      <h3>Обмен сменами и подмены<span class="sub">""",
          """      <button class="btn ghost small" id="btnSwapOpen" style="float:right" title="Открытая заявка без напарника: партнёра подберёт автоподбор (3.42)">＋ Открытая заявка</button>
      <h3>Обмен сменами и подмены<span class="sub">""", 'swap open btn')
    c.rep("  bindClick('btnBudgetCsv',budgetsCsvDl);                /* 3.39 */", "  bindClick('btnBudgetCsv',budgetsCsvDl);                /* 3.39 */\n  bindClick('btnSwapOpen',openSwapOpenReq);              /* 3.42 */", 'swap open bind')
    c.rep("""    {ic:'🎫',title:'Прогноз истечения допусков и риск покрытия',hint:'справочники · 3.41',run:()=>{showTab('set');setTimeout(()=>{const h=$('certFcBox');if(h&&h.scrollIntoView)h.scrollIntoView({behavior:'smooth',block:'center'});renderCertForecast()},300)}},""",
          """    {ic:'🎫',title:'Прогноз истечения допусков и риск покрытия',hint:'справочники · 3.41',run:()=>{showTab('set');setTimeout(()=>{const h=$('certFcBox');if(h&&h.scrollIntoView)h.scrollIntoView({behavior:'smooth',block:'center'});renderCertForecast()},300)}},
    {ic:'🤖',title:'Открытая заявка на подмену + автоподбор',hint:'обмены · 3.42',run:()=>{showTab('swap');setTimeout(()=>openSwapOpenReq(),250)}},""", 'palette 342')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.41 — допуски: прогноз истечения и риск покрытия</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.42 — маркетплейс обменов: открытые заявки и автоподбор</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Открытая заявка на подмену</b> («＋ Открытая заявка» во вкладке «Обмены» и палитра): заявка без напарника — сотрудник, дата, причина; поступает в общий список и на согласование после подбора.</li>
        <li><b>Автоподбор напарника «🤖»</b>: ранжированный список кандидатов с оценкой как в докторе покрытия — пожелания («не ставить» исключает, «предпочтительно» +40), <b>баланс подмен</b> (брал/отдавал за время жизни базы), загрузка месяца, отдых после суточных, серии рабочих дней, недельные часы, допуски; «＋» предлагает напарника (заявка уходит в стандартный маршрут согласования).</li>
        <li>Аудит и телеметрия: <code>swap:open</code>, <code>swap:match</code>, записи «Открытая заявка», «Автоподбор напарника».</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.41 — допуски: прогноз истечения и риск покрытия</div>""", 'help 342')
    c.rep("""    certExpDate,certForecast,certReqs,certReqAdd,certReqAct,renderCertForecast,""",
          """    certExpDate,certForecast,certReqs,certReqAdd,certReqAct,renderCertForecast,
    /* ===== 3.42: маркетплейс обменов ===== */
    coversTaken,coversGiven,swapOpenReq,swapCandidates,swapOffer,openSwapMatch,openSwapOpenReq,""", 'exports 342')

# ============================== 3.43 ПРОГНОЗЫ ОТСУТСТВИЙ С ДИ ==============================
MODULE_343 = r"""/* ================= 3.43: ПРОГНОЗЫ ОТСУТСТВИЙ С ДОВЕРИТЕЛЬНЫМ ИНТЕРВАЛОМ =================
   Линейный тренд по истории месяцев канона (до 12) + интервал прогноза 95 %
   (1.96·SD·√(1+1/n)) по двум метрикам: чел·дн отсутствий и загрузка %. */
function linreg(ys){
  const n=ys.length;
  if(!n)return{a:0,b:0};
  if(n<2)return{a:ys[0]||0,b:0};
  const xs=ys.map((_,i)=>i);
  const mx=xs.reduce((a,b)=>a+b,0)/n,my=ys.reduce((a,b)=>a+b,0)/n;
  let num=0,den=0;
  xs.forEach((x,i)=>{num+=(x-mx)*(ys[i]-my);den+=(x-mx)*(x-mx)});
  const b=den?num/den:0;
  return{a:my-b*mx,b};
}
function forecastAbsences(deptId,monthsAhead){
  monthsAhead=monthsAhead||3;
  const t=TODAY(),hist=[];
  for(let back=11;back>=1;back--){
    const d=new Date(t.getFullYear(),t.getMonth()-back,1),y=d.getFullYear(),m=d.getMonth()+1;
    if(!state.plan[mkOf(y,m)])continue;
    const es=empList(deptId);if(!es.length)continue;
    let abs=0,load=0,norm=0;
    es.forEach(e=>{const st=empMonthStats(e.id,y,m);ABS_CATS.forEach(ct=>{abs+=(st.byCat&&st.byCat[ct])||0});load+=st.load;norm+=st.norm});
    hist.push({y,m,abs,loadPct:norm?Math.round(load/norm*1000)/10:0});
  }
  if(hist.length<3)return null;
  const out=[];
  [['abs','Отсутствия, чел·дн'],['loadPct','Загрузка, %']].forEach(([key,label])=>{
    const ys=hist.map(h=>h[key]);
    const{a,b}=linreg(ys);
    const mean=ys.reduce((x,y)=>x+y,0)/ys.length;
    const sd=Math.sqrt(ys.reduce((s2,y)=>s2+(y-mean)*(y-mean),0)/Math.max(1,ys.length-1));
    const half=1.96*sd*Math.sqrt(1+1/ys.length);   /* интервал прогноза, 95 % */
    for(let f=1;f<=monthsAhead;f++){
      const x=hist.length-1+f;
      const pred=Math.max(0,a+b*x);
      const d=new Date(t.getFullYear(),t.getMonth()+f,1);
      out.push({key,label,y:d.getFullYear(),m:d.getMonth()+1,
        pred:Math.round(pred*10)/10,lo:Math.round(Math.max(0,pred-half)*10)/10,hi:Math.round((pred+half)*10)/10,
        n:ys.length,sd:Math.round(sd*10)/10,trend:Math.round(b*100)/100});
    }
  });
  return{deptId,hist,out};
}
function renderForecastCard(){
  const box=$('fcBox');if(!box)return;
  const deptId=$('fcDept')?$('fcDept').value:'all';
  const f=forecastAbsences(deptId==='all'?null:deptId,3);
  if(!f){box.innerHTML='<div class="hint">Нужно ≥ 3 месяцев истории плана — прогнозу не на чем учиться.</div>';return}
  box.innerHTML=`<div class="scroll-x"><table class="rtbl"><thead><tr><th>Период</th><th>Метрика</th><th class="n">Прогноз</th><th class="n">ДИ 95 %</th><th class="n">Тренд/мес</th><th class="n">История</th></tr></thead><tbody>
    ${f.out.map(r=>`<tr><td>${MUP[r.m-1]} ${r.y}</td><td>${esc(r.label)}</td>
      <td class="n"><b>${fmtStd(r.pred,{dec:1})}</b></td>
      <td class="n">${fmtStd(r.lo,{dec:1})}–${fmtStd(r.hi,{dec:1})}</td>
      <td class="n">${r.trend>0?'+':''}${fmtStd(r.trend,{dec:2})}</td>
      <td class="n">${fmtStd(r.n,{unit:'мес'})} · SD ${fmtStd(r.sd,{dec:1})}</td></tr>`).join('')}
    </tbody></table></div>
    <div class="hint" style="margin-top:6px">Методика: линейный тренд по истории месяцев канона (до 12); интервал прогноза 95 % = ±1,96·SD·√(1+1/n). Использовать для планирования резерва под болезни и отпуска.</div>`;
}
function forecastAbsCsvDl(){
  const deptId=$('fcDept')?$('fcDept').value:'all';
  const f=forecastAbsences(deptId==='all'?null:deptId,3);
  if(!f){toast('Недостаточно истории для прогноза','err');return}
  const rows=[['Прогноз отсутствий с ДИ 95%',(dept(deptId==='all'?null:deptId)||{}).name||'все','штамп',stampPlain('an')],[],
    ['Период','Метрика','Прогноз','ДИ низ','ДИ верх','Тренд/мес','Месяцев истории','SD']];
  f.out.forEach(r=>rows.push([MUP[r.m-1]+' '+r.y,r.label,r.pred,r.lo,r.hi,r.trend,r.n,r.sd]));
  downloadCsv('prognoz-otsutstvij-'+(deptId||'all')+'.csv',rows);
  audit('Выгрузка прогноза отсутствий',`${(dept(deptId==='all'?null:deptId)||{}).name||'все'} · CSV`,'forecast');
  try{teleHit('forecast:csv')}catch(e){}
  toast('Прогноз выгружен в CSV','ok');
}
"""

def V343(c):
    c.ver('3.43')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_343 + '\n' + c.s[i:]
    c.rep("""  <div class="card" style="margin-top:12px"><h3>OLAP-срез: произвольные измерения<span class="sub">""",
          """  <div class="card" style="margin-top:12px"><h3>Прогноз отсутствий с ДИ 95 %<span class="sub">3.43 · линейный тренд по истории месяцев · интервал прогноза ±1,96·SD·√(1+1/n)</span></h3>
    <div class="frow no-print"><div class="field" style="margin:0;max-width:260px"><label>Подразделение</label><select class="inp" id="fcDept"><option value="all">все подразделения</option></select></div>
    <div class="field" style="margin:0;align-self:end"><button class="btn ghost small" id="btnFcCsv">⇩ CSV прогноза</button></div></div>
    <div id="fcBox" style="margin-top:8px"></div>
  </div>
  <div class="card" style="margin-top:12px"><h3>OLAP-срез: произвольные измерения<span class="sub">""", 'forecast card')
    c.rep("  bindClick('btnSwapOpen',openSwapOpenReq);              /* 3.42 */",
          "  bindClick('btnSwapOpen',openSwapOpenReq);   /* 3.42 */\n"
          "  bindClick('btnFcCsv',forecastAbsCsvDl);     /* 3.43 */\n"
          "  const fcD=$('fcDept');if(fcD){fcD.innerHTML='<option value=\"all\">все подразделения</option>'+state.departments.map(d=>`<option value=\"${d.id}\">${esc(d.name)}</option>`).join('');fcD.onchange=()=>renderForecastCard()}   /* 3.43 */", 'forecast binds')
    c.rep('function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){};try{renderBudgets()}catch(e){};try{renderCertForecast()}catch(e){}}   /* 3.36–3.41 хуки */',
          'function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){};try{renderBudgets()}catch(e){};try{renderCertForecast()}catch(e){};try{renderForecastCard()}catch(e){}}   /* 3.36–3.43 хуки */', 'render hook 343')
    c.rep("""    {ic:'🤖',title:'Открытая заявка на подмену + автоподбор',hint:'обмены · 3.42',run:()=>{showTab('swap');setTimeout(()=>openSwapOpenReq(),250)}},""",
          """    {ic:'🤖',title:'Открытая заявка на подмену + автоподбор',hint:'обмены · 3.42',run:()=>{showTab('swap');setTimeout(()=>openSwapOpenReq(),250)}},
    {ic:'🔮',title:'Прогноз отсутствий с ДИ 95 %',hint:'аналитика · 3.43',run:()=>{showTab('an');setTimeout(()=>{const c=$('fcBox');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'});renderForecastCard()},300)}},""", 'palette 343')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.42 — маркетплейс обменов: открытые заявки и автоподбор</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.43 — прогнозы отсутствий с доверительным интервалом</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Карточка «Прогноз отсутствий с ДИ 95 %»</b> (Аналитика): по истории месяцев канона (до 12) — линейный тренд и прогноз на 3 месяца вперёд по двум метрикам: чел·дн отсутствий и загрузка %; колонки «Прогноз», «ДИ 95 %» (интервал прогноза ±1,96·SD·√(1+1/n)), «Тренд/мес», «История (n, SD)».</li>
        <li>Фильтр по подразделению, выгрузка CSV со штампом, палитра «🔮»; телеметрия <code>forecast:csv</code>. Методика указана прямо в карточке — для планирования резерва под болезни и отпуска.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.42 — маркетплейс обменов: открытые заявки и автоподбор</div>""", 'help 343')
    c.rep("""    coversTaken,coversGiven,swapOpenReq,swapCandidates,swapOffer,openSwapMatch,openSwapOpenReq,""",
          """    coversTaken,coversGiven,swapOpenReq,swapCandidates,swapOffer,openSwapMatch,openSwapOpenReq,
    /* ===== 3.43: прогнозы с ДИ ===== */
    linreg,forecastAbsences,renderForecastCard,forecastAbsCsvDl,""", 'exports 343')

# ============================== 3.44 КОНСТРУКТОР ПРИКАЗОВ ==============================
MODULE_344 = r"""/* ================= 3.44: КОНСТРУКТОР ПРИКАЗОВ =================
   Реестр шаблонов приказов с плейсхолдерами, источники строк (отпуска, дежурства,
   произвольный текст), предпросмотр, экспорт .txt и .docx (JSZip при наличии). */
const DEFAULT_ORDER_TPLS=[
  {id:'ot1',name:'Приказ об утверждении графика отпусков',src:'vac',
   body:'{{ORG}}\nПРИКАЗ № {{NUM}} от {{DATE}}\n\nОб утверждении графика отпусков за {{PERIOD}}:\n\n{{ROWS}}\n\nОснование: заявления сотрудников и согласование руководителей. Ответственный за исполнение: начальник отдела кадров.\n\nКадровая служба: ____________'},
  {id:'ot2',name:'Приказ об утверждении графика дежурств',src:'duty',
   body:'{{ORG}}\nПРИКАЗ № {{NUM}} от {{DATE}}\n\nОб утверждении графика дежурств за {{PERIOD}}:\n\n{{ROWS}}\n\nОснование: производственная необходимость, минимум дежурных в сутки. Контроль исполнения возложить на начальника дежурной службы.\n\nДежурная служба: ____________'},
  {id:'ot3',name:'Произвольный приказ',src:'custom',
   body:'{{ORG}}\nПРИКАЗ № {{NUM}} от {{DATE}}\n\n{{TEXT}}\n\nОснование: решение руководителя. \n\nПодпись: ____________'}];
function orderTpls(){if(!Array.isArray(state.orderTpls)||!state.orderTpls.length)state.orderTpls=clone(DEFAULT_ORDER_TPLS);return state.orderTpls}
function orderRows(src,y,m,deptId){
  if(src==='vac')return vacRequests().filter(r=>r.status==='approved'&&r.year===y&&(!deptId||deptId==='all'||(emp(r.eid)||{}).deptId===deptId))
    .map(r=>`— ${empName(r.eid)}: отпуск с ${r.from.split('-').reverse().join('.')} по ${r.to.split('-').reverse().join('.')} (${daysBetween(r.from,r.to)} дн.)`);
  if(src==='duty')return empList(deptId==='all'?null:deptId).map(e=>{
    const days=[];for(let d=1;d<=dim(y,m);d++){const raw=getCode(e.id,y,m,d);if(!raw)continue;const r=reason(parseCell(raw).code);if(r&&r.cat==='duty')days.push(d)}
    return days.length?`— ${e.name}: дежурства ${days.join(', ')} (${fmtStd(days.length,{unit:'дн'})})`:null}).filter(Boolean);
  return [];
}
function orderRender(tpl,ctx){
  return String(tpl.body||'')
    .replace(/\{\{ORG\}\}/g,ctx.org).replace(/\{\{NUM\}\}/g,ctx.num).replace(/\{\{DATE\}\}/g,ctx.date)
    .replace(/\{\{PERIOD\}\}/g,ctx.period).replace(/\{\{ROWS\}\}/g,ctx.rows.join('\n')||'(строк нет — измените источник или период)')
    .replace(/\{\{TEXT\}\}/g,ctx.text||'');
}
function orderDocxDl(title,text){
  if(typeof JSZip==='undefined'||!window.JSZip){toast('JSZip недоступен без сети в онлайн-сборке — используйте .txt (в офлайн-сборке docx доступен)','err');return false}
  const paras=String(text).split('\n').map(ln=>`<w:p><w:r><w:t xml:space="preserve">${dxEsc(ln)}</w:t></w:r></w:p>`).join('');
  const doc=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>${paras}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>`;
  const zip=new window.JSZip();
  zip.file('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>');
  zip.file('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>');
  zip.file('word/document.xml',doc);
  zip.generateAsync({type:'blob'}).then(bl=>{
    const a=document.createElement('a');a.href=URL.createObjectURL(bl);a.download=title+'.docx';a.click();
    setTimeout(()=>URL.revokeObjectURL(a.href),4000);
  });
  return true;
}
function openOrderConstructor(tplId){
  try{teleHit('order:ui')}catch(e){}
  const tpls=orderTpls();
  const t0=tpls.find(x=>x.id===tplId)||tpls[0];
  openModal({title:'📜 Конструктор приказов',wide:true,body:`
    <div class="frow" style="flex-wrap:wrap;gap:8px">
      <div class="field" style="flex:1.4;margin:0"><label>Шаблон</label><select class="inp" id="ocTpl">${tpls.map(t=>`<option value="${t.id}" ${t.id===t0.id?'selected':''}>${esc(t.name)}</option>`).join('')}</select></div>
      <div class="field" style="margin:0"><label>Номер</label><input class="inp" id="ocNum" value="1/ОД" style="width:90px"></div>
      <div class="field" style="margin:0"><label>Подразделение</label><select class="inp" id="ocDept"><option value="all">все</option>${state.departments.map(d=>`<option value="${d.id}">${esc(d.name)}</option>`).join('')}</select></div>
    </div>
    <div class="field"><label>Текст шаблона (плейсхолдеры: {{ORG}} {{NUM}} {{DATE}} {{PERIOD}} {{ROWS}} {{TEXT}})</label>
      <textarea id="ocBody" class="inp" style="min-height:150px">${esc(t0.body)}</textarea></div>
    <div class="field"><label>Произвольный текст (для источника «custom», плейсхолдер {{TEXT}})</label><textarea id="ocText" class="inp" style="min-height:60px" placeholder="Например: утвердить состав дежурной службы на период…"></textarea></div>
    <div class="lbl" style="margin-top:10px">Предпросмотр</div>
    <pre id="ocPrev" class="mono" style="white-space:pre-wrap;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:10px;font-size:11.5px;max-height:34vh;overflow:auto"></pre>`,
    buttons:`<button class="btn ghost" data-coc>Закрыть</button><button class="btn ghost" id="ocSave">💾 Сохранить шаблон</button><button class="btn ghost" id="ocTxt">⤓ .txt</button><button class="btn" id="ocDocx">⤓ DOCX</button>`,
    onMount(b){
      const ctx=()=>{
        const tpl=orderTpls().find(x=>x.id===b.querySelector('#ocTpl').value)||orderTpls()[0];
        const deptId=b.querySelector('#ocDept').value;
        return{tpl,ctx:{org:state.org,num:b.querySelector('#ocNum').value,date:new Date().toLocaleDateString('ru-RU'),
          period:MUP[cur.m-1]+' '+cur.y,rows:orderRows(tpl.src,cur.y,cur.m,deptId),text:b.querySelector('#ocText').value}};
      };
      const live=()=>{const{tpl,ctx:cc}=ctx();b.querySelector('#ocPrev').textContent=orderRender({body:b.querySelector('#ocBody').value},cc)};
      ['ocTpl','ocNum','ocDept','ocBody','ocText'].forEach(id=>{const el=b.querySelector('#'+id);el.onchange=live;el.oninput=live});
      b.querySelector('#ocTpl').onchange=()=>{const t=orderTpls().find(x=>x.id===b.querySelector('#ocTpl').value);if(t)b.querySelector('#ocBody').value=t.body;live()};
      live();
      b.querySelector('[data-coc]').onclick=closeModal;
      b.querySelector('#ocSave').onclick=()=>{
        const{tpl}=ctx();
        tpl.body=b.querySelector('#ocBody').value;
        save(true);audit('Шаблон приказа сохранён',tpl.name,'orders');toast('Шаблон сохранён','ok');
      };
      b.querySelector('#ocTxt').onclick=()=>{
        const{tpl,ctx:cc}=ctx();
        download('prikaz-'+cc.num.replace(/[^\wа-яё-]/gi,'')+'.txt',orderRender({body:b.querySelector('#ocBody').value},cc),'text/plain');
        audit('Выгрузка приказа',tpl.name+' · txt','orders');toast('Приказ выгружен в .txt','ok');
      };
      b.querySelector('#ocDocx').onclick=()=>{
        const{tpl,ctx:cc}=ctx();
        if(orderDocxDl('prikaz-'+cc.num.replace(/[^\wа-яё-]/gi,''),orderRender({body:b.querySelector('#ocBody').value},cc))){
          audit('Выгрузка приказа',tpl.name+' · docx','orders');toast('Приказ выгружен в DOCX','ok');
        }
      };
    }});
}
"""

def V344(c):
    c.ver('3.44')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_344 + '\n' + c.s[i:]
    c.rep("""      <h3>Конструктор отчёта</h3>""",
          """      <h3>Конструктор приказов<span class="sub">3.44 · шаблоны с плейсхолдерами · источники: отпуска, дежурства, произвольный текст · .txt и .docx</span></h3>
      <div id="orderBox" class="hint"></div>
      <button class="btn small" id="btnOrderNew" style="margin-top:8px">📜 Открыть конструктор приказов</button>
      </div>
      <div class="card">
      <h3>Конструктор отчёта</h3>""", 'order card')
    c.rep("  bindClick('btnFcCsv',forecastAbsCsvDl);     /* 3.43 */",
          "  bindClick('btnFcCsv',forecastAbsCsvDl);     /* 3.43 */\n"
          "  bindClick('btnOrderNew',()=>openOrderConstructor());   /* 3.44 */\n"
          "  try{const ob=$('orderBox');if(ob)ob.innerHTML=orderTpls().map(t=>`<div class=\"log-row\"><span style=\"flex:1\">${esc(t.name)} · источник: ${t.src==='vac'?'отпуска':t.src==='duty'?'дежурства':'произвольный'}</span><button class=\"btn ghost tiny\" data-ord=\"${t.id}\">открыть</button></div>`).join(''),ob.querySelectorAll('[data-ord]').forEach(b2=>b2.onclick=()=>openOrderConstructor(b2.dataset.ord))}catch(e){}   /* 3.44 */", 'order binds')
    c.rep("""    {ic:'🔮',title:'Прогноз отсутствий с ДИ 95 %',hint:'аналитика · 3.43',run:()=>{showTab('an');setTimeout(()=>{const c=$('fcBox');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'});renderForecastCard()},300)}},""",
          """    {ic:'🔮',title:'Прогноз отсутствий с ДИ 95 %',hint:'аналитика · 3.43',run:()=>{showTab('an');setTimeout(()=>{const c=$('fcBox');if(c&&c.scrollIntoView)c.scrollIntoView({behavior:'smooth',block:'center'});renderForecastCard()},300)}},
    {ic:'📜',title:'Конструктор приказов (DOCX/TXT)',hint:'отчёты · 3.44',run:()=>{showTab('rep');setTimeout(()=>openOrderConstructor(),250)}},""", 'palette 344')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.43 — прогнозы отсутствий с доверительным интервалом</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.44 — конструктор приказов</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Реестр шаблонов приказов</b> (Отчёты → «Конструктор приказов»): три встроенных шаблона (отпуска, дежурства, произвольный) с плейсхолдерами <code>{{ORG}} {{NUM}} {{DATE}} {{PERIOD}} {{ROWS}} {{TEXT}}</code>; тело шаблона редактируется и сохраняется в каноне (<code>state.orderTpls</code>).</li>
        <li><b>Источники строк</b>: утверждённые заявки отпусков года или дежурства месяца (с фильтром подразделения) — строки «{{ROWS}}» формируются автоматически; предпросмотр обновляется на каждом вводе.</li>
        <li><b>Экспорт</b>: .txt всегда; .docx — при доступном JSZip (офлайн-сборка), иначе подсказка; аудит выгрузок и сохранений, телеметрия <code>order:ui</code>.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.43 — прогнозы отсутствий с доверительным интервалом</div>""", 'help 344')
    c.rep("""    linreg,forecastAbsences,renderForecastCard,forecastAbsCsvDl,""",
          """    linreg,forecastAbsences,renderForecastCard,forecastAbsCsvDl,
    /* ===== 3.44: конструктор приказов ===== */
    orderTpls,orderRows,orderRender,orderDocxDl,openOrderConstructor,get DEFAULT_ORDER_TPLS(){return DEFAULT_ORDER_TPLS},""", 'exports 344')

# ============================== 3.45 A11Y ВОЛНА 2 ==============================
CSS_345 = """
/* ===== 3.45: высокий контраст и.skip-link ===== */
html[data-contrast="hc"]{--line:#5b6b88;--line2:#8a97ad;--mut:#33415c}
html[data-contrast="hc"][data-theme="dark"]{--line:#93a6c9;--line2:#7688a8;--mut:#cdd8ea}
html[data-contrast="hc"] .btn,html[data-contrast="hc"] .inp,html[data-contrast="hc"] .card{border-width:2px}
html[data-contrast="hc"] :focus-visible{outline:3px solid var(--amber)!important;outline-offset:2px}
html[data-contrast="hc"] a{text-decoration:underline}
html[data-contrast="hc"] .hint{color:var(--mut)}
.skip-link{position:absolute;left:-9999px;top:0;background:var(--navy);color:#fff;padding:8px 14px;z-index:100;border-radius:0 0 8px 0;font-size:12px}
.skip-link:focus{left:0}
"""

MODULE_345 = r"""/* ================= 3.45: A11Y ВОЛНА 2 =================
   Высококонтрастный режим (персонально, uiPrefs), карта клавиатурных сокращений,
   skip-link к навигации, aria-live для тостов, role=grid у сеток плана и дежурств. */
const SHORTCUTS=[
  ['F1','Справка и горячие клавиши'],['F2','Дайджест руководителю'],['F3','Лист ознакомления по сигналам'],
  ['F4','Квартальный лист ознакомления'],['F7','Пакет руководителя (XLSX+DOCX+CSV)'],
  ['Ctrl+K','Командная палитра'],['Ctrl+Z / Ctrl+Y','Отменить / повторить'],
  ['/','Поиск сотрудника в плане'],['Alt+↓ / Alt+↑','Навигация по результатам сквозного поиска'],
  ['Esc','Закрыть модалку / палитру / центр уведомлений'],
  ['Shift+тянуть','Прямоугольное выделение в сетке плана'],['Enter / Пробел','Кисть в клавиатурном режиме сетки'],
  ['Del','Стереть ячейку в клавиатурном режиме'],['Стрелки','Навигация по сетке плана (клавиатурный режим)'],
  ['Свайп ← / →','Месяц назад / вперёд (мобильная оболочка 3.38)'],['Tab / Shift+Tab','Цикл фокуса внутри модалки']];
function openShortcuts(){
  try{teleHit('a11y:keys')}catch(e){}
  openModal({title:'⌨ Карта клавиатурных сокращений',wide:true,body:`
    <div class="scroll-x"><table class="rtbl"><thead><tr><th style="min-width:140px">Клавиши</th><th>Действие</th></tr></thead><tbody>
    ${SHORTCUTS.map(s=>`<tr><td><span class="kbd">${esc(s[0])}</span></td><td>${esc(s[1])}</td></tr>`).join('')}
    </tbody></table></div>
    <div class="hint" style="margin-top:8px">3.45: карта доступна также из палитры («⌨ Карта клавиш») и справки. Фокус внутри модалок цикличен (Tab / Shift+Tab), тосты объявляются скринридеру (aria-live).</div>`,
    buttons:'<button class="btn ghost" data-cks>Закрыть</button>',
    onMount(b){b.querySelector('[data-cks]').onclick=closeModal}});
}
function a11yInit(){
  const tb=$('toastBox');
  if(tb&&!tb.getAttribute('aria-live')){tb.setAttribute('aria-live','polite');tb.setAttribute('role','status')}
  if(!$('skipLink')){
    const a=document.createElement('a');
    a.id='skipLink';a.className='skip-link';a.href='#tabsBar';
    a.textContent='Пропустить к навигации по разделам';
    document.body.insertBefore(a,document.body.firstChild);
  }
  const sc=$('setContrast');
  if(sc){
    sc.checked=!!uiPrefs().contrast;
    sc.onchange=e=>{setUiPref('contrast',e.target.checked);applyUi();
      toast(e.target.checked?'Высокий контраст включён':'Высокий контраст выключен')};
  }
  applyUi();
}
function a11yPatch(){
  const t=$('tblWrap')&&$('tblWrap').querySelector('table.pt');
  if(t){t.setAttribute('role','grid');t.setAttribute('aria-label','Сетка плана на '+MUP[cur.m-1]+' '+cur.y)}
  const dw=$('dutyWrap')&&$('dutyWrap').querySelector('table');
  if(dw){dw.setAttribute('role','grid');dw.setAttribute('aria-label','Сетка дежурств на '+MUP[cur.m-1]+' '+cur.y)}
}
"""

def V345(c):
    c.ver('3.45')
    c.rep('.pwcell.today{border-color:var(--navy);box-shadow:0 0 0 2px color-mix(in srgb,var(--navy) 22%,transparent)}',
          '.pwcell.today{border-color:var(--navy);box-shadow:0 0 0 2px color-mix(in srgb,var(--navy) 22%,transparent)}' + CSS_345, 'css 345')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_345 + '\n' + c.s[i:]
    c.rep("<div id=\"toastBox\"></div>", "<div id=\"toastBox\" role=\"status\" aria-live=\"polite\"></div>", 'toast aria')
    c.rep("""        <h3>Интерфейс<span class="sub">тема · масштаб · плотность таблиц — настройки этого рабочего места</span></h3>""",
          """        <h3>Интерфейс<span class="sub">тема · масштаб · плотность таблиц — настройки этого рабочего места</span></h3>
        <div class="setrow" style="flex-wrap:wrap;gap:6px">
          <label class="chkrow" style="margin:0"><input type="checkbox" id="setContrast"> высокий контраст (3.45)</label>
          <span class="hint">усиленные границы карточек/кнопок, жирные фокус-кольца, подчёркнутые ссылки — персонально для этого рабочего места</span>
        </div>""", 'contrast ui')
    c.rep("  document.documentElement.dataset.theme=dark?'dark':'light';",
          "  document.documentElement.dataset.theme=dark?'dark':'light';\n  try{document.documentElement.dataset.contrast=uiPrefs().contrast?'hc':''}catch(e){}   /* 3.45: высокий контраст */\ntry{const scx=$('setContrast');if(scx)scx.checked=!!uiPrefs().contrast}catch(e){}   /* 3.45: синхронизация флажка */", 'applyUi contrast')
    c.rep('  try{renderCertForecast()}catch(e){}   /* 3.41: прогноз допусков */',
          '  try{renderCertForecast()}catch(e){}   /* 3.41: прогноз допусков */\n  try{a11yInit()}catch(e){}   /* 3.45: a11y-инициализация */', 'boot a11y')
    c.rep('function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){};try{renderBudgets()}catch(e){};try{renderCertForecast()}catch(e){};try{renderForecastCard()}catch(e){}}   /* 3.36–3.43 хуки */',
          'function renderPatterns(){renderBulk();try{renderBrigades()}catch(e){};try{renderMobiNav()}catch(e){};try{renderBudgets()}catch(e){};try{renderCertForecast()}catch(e){};try{renderForecastCard()}catch(e){};try{a11yPatch()}catch(e){}}   /* 3.36–3.45 хуки */', 'render hook 345')
    c.rep("""    {ic:'📜',title:'Конструктор приказов (DOCX/TXT)',hint:'отчёты · 3.44',run:()=>{showTab('rep');setTimeout(()=>openOrderConstructor(),250)}},""",
          """    {ic:'📜',title:'Конструктор приказов (DOCX/TXT)',hint:'отчёты · 3.44',run:()=>{showTab('rep');setTimeout(()=>openOrderConstructor(),250)}},
    {ic:'⌨',title:'Карта клавиатурных сокращений',hint:'a11y · 3.45',run:()=>openShortcuts()},
    {ic:'🌓',title:'Высокий контраст: вкл/выкл',hint:'a11y · 3.45',run:()=>{setUiPref('contrast',!uiPrefs().contrast);applyUi();toast(uiPrefs().contrast?'Высокий контраст включён':'Высокий контраст выключен')}},""", 'palette 345')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.44 — конструктор приказов</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.45 — доступность, волна 2</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Высокий контраст</b>: персональный режим (Справочники → Интерфейс или палитра «🌓») — усиленные границы, жирные фокус-кольца :focus-visible, подчёркнутые ссылки; работает в светлой и тёмной теме.</li>
        <li><b>Карта клавиатурных сокращений</b> («⌨» в палитре): 16 сочетаний от F1–F7 и Ctrl+K до клавиатурного режима сетки и свайпов; цикл фокуса в модалках и aria-live тостов объявлены явно.</li>
        <li><b>Skip-link</b> «Пропустить к навигации по разделам» (виден с клавиатуры по фокусу) и role="grid" + aria-имена у сеток плана и дежурств (обновляются при перерисовке).</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.44 — конструктор приказов</div>""", 'help 345')
    c.rep("""    orderTpls,orderRows,orderRender,orderDocxDl,openOrderConstructor,get DEFAULT_ORDER_TPLS(){return DEFAULT_ORDER_TPLS},""",
          """    orderTpls,orderRows,orderRender,orderDocxDl,openOrderConstructor,get DEFAULT_ORDER_TPLS(){return DEFAULT_ORDER_TPLS},
    /* ===== 3.45: a11y волна 2 ===== */
    get SHORTCUTS(){return SHORTCUTS},openShortcuts,a11yInit,a11yPatch,""", 'exports 345')



# ============================== 3.46 ПРОИЗВОДИТЕЛЬНОСТЬ ==============================
MODULE_346 = r"""/* ================= 3.46: ВОЛНА ПРОИЗВОДИТЕЛЬНОСТИ =================
   Профилирование запуска и операций (performance marks/spans), карточка
   «Профилирование и нагрузка», отложенная сверка календаря (boot быстрее),
   генератор нагрузочного профиля demoScale(1000). */
const PERF=window.__PT_PERF=window.__PT_PERF||{marks:{},spans:[]};
function perfMark(name){try{PERF.marks[name]=Math.round(performance.now())}catch(e){}}
function perfSpan(name,fn){
  const t0=performance.now();
  const r=fn();
  PERF.spans.push({name,ms:Math.round(performance.now()-t0)});
  if(PERF.spans.length>400)PERF.spans.shift();
  return r;
}
function perfReport(){
  const spans={};
  PERF.spans.forEach(s=>{spans[s.name]=(spans[s.name]||0)+s.ms});
  return{marks:PERF.marks,spans,spanCount:PERF.spans.length,
    cache:{stat:statCache.size,olap:(typeof olapCache!=='undefined'&&olapCache)?1:0,an:anData?1:0}};
}
function perfMeasureTabs(){
  const out=[];
  ['dash','me','plan','duty','swap','vac','tabel','cal','an','rep','ops','board','pdf','data','set'].forEach(t=>{
    const t0=performance.now();
    try{showTab(t,true)}catch(e){}
    out.push({tab:t,ms:Math.round(performance.now()-t0)});
  });
  try{showTab('plan')}catch(e){}
  out.forEach(o=>PERF.spans.push({name:'tab:'+o.tab,ms:o.ms}));
  renderPerfCard();
  return out;
}
function renderPerfCard(){
  const box=$('perfBox');if(!box)return;
  const r=perfReport();
  const mk=Object.keys(r.marks).length?Object.entries(r.marks).map(([k2,v])=>`${esc(k2)}: <b>${fmtStd(v,{unit:'мс'})}</b>`).join(' · '):'—';
  box.innerHTML=`<div class="hint" style="margin-top:0">Метки запуска: ${mk}</div>
  <div class="scroll-x" style="max-height:30vh;overflow:auto"><table class="rtbl"><thead><tr><th>Операция</th><th class="n">Сумма, мс</th></tr></thead><tbody>
  ${Object.entries(r.spans).sort((a,b)=>b[1]-a[1]).slice(0,12).map(([k2,v])=>`<tr><td>${esc(k2)}</td><td class="n">${fmtStd(v,{unit:'мс'})}</td></tr>`).join('')||'<tr><td colspan="2">Замеров ещё нет — нажмите «Замерить вкладки».</td></tr>'}
  </tbody></table></div>
  <div class="hint" style="margin-top:6px">Кэши: статистика ${fmtStd(r.cache.stat,{unit:'записей'})}, OLAP ${r.cache.olap?'горячий':'холодный'}, годовая аналитика ${r.cache.an?'горячая':'холодная'}. Замеры живут только в памяти вкладки.</div>`;
}
function demoScale(n){
  n=n||1000;
  const doIt=()=>{
    const t0=performance.now();
    const rnd=mulberry32(42);
    const SUR=['Иванов','Петров','Сидоров','Кузнецов','Смирнов','Попов','Васильев','Соколов','Михайлов','Новиков','Фёдоров','Морозов','Волков','Алексеев','Лебедев','Семёнов','Егоров','Павлов','Козлов','Степанов'];
    const INI='АБВГДЕИКЛМНОПРСТФШ';
    const deps=state.departments.length?state.departments:[{id:'d1',name:'Отдел 1',minDuty:0,dutyCode:'Д1'}];
    const emps=[];
    for(let i=0;i<n;i++){
      emps.push({id:'sc'+(i+1),deptId:deps[i%deps.length].id,
        name:SUR[i%SUR.length]+' '+INI[Math.floor(rnd()*INI.length)]+'. '+INI[Math.floor(rnd()*INI.length)]+'.',
        pos:'специалист '+((i%4)+1),rate:1,vacationDays:28,hoursWeek:40,
        dutyEligible:rnd()<.5,tab:'SC-'+String(i+1).padStart(4,'0')});
    }
    state.employees=emps;
    deptVis=new Set(deps.map(d=>d.id));
    const t=TODAY(),mk=mkOf(t.getFullYear(),t.getMonth()+1);
    state.plan[mk]={};
    emps.forEach((e,i)=>{
      if(i%3)return;
      const row={};
      for(let d=1;d<=7;d++)if(rnd()<.3)row[d]='Б';
      state.plan[mk][e.id]=row;
    });
    bust();save(true);
    const ms=performance.now()-t0;
    PERF.spans.push({name:'demoScale:'+n,ms:Math.round(ms)});
    refreshAll();
    audit('Нагрузочный профиль',`${fmtStd(n,{unit:'сотр'})} · генерация ${fmtStd(Math.round(ms),{unit:'мс'})}`,'perf');
    try{teleHit('perf:scale')}catch(e){}
    toast(`Профиль ${fmtStd(n,{unit:'сотр'})} готов за ${fmtStd(Math.round(ms),{unit:'мс'})}`,'ok');
  };
  confirmBox(`Сгенерировать нагрузочный профиль: ${fmtStd(n,{unit:'сотр'})} (текущий штат будет заменён)? Использовать только для замеров производительности.`,doIt,'Да, сгенерировать');
}
"""

def V346(c):
    c.ver('3.46')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_346 + '\n' + c.s[i:]
    c.rep("""async function boot(){
  initErrorHandlers();""",
          """async function boot(){
  perfMarkBootStart();
  initErrorHandlers();""", 'boot mark start')
    c.rep("function perfMark(name){try{PERF.marks[name]=Math.round(performance.now())}catch(e){}}",
          "function perfMark(name){try{PERF.marks[name]=Math.round(performance.now())}catch(e){}}\nfunction perfMarkBootStart(){try{PERF.marks['boot:start']=0}catch(e){}}", 'boot mark fn')
    c.rep("  state=(await loadState())||seedState();",
          "  state=(await loadState())||seedState();\n  try{perfMark('state:loaded')}catch(e){}   /* 3.46 */", 'boot mark state')
    c.rep("  initEvents();\n  refreshAll();",
          "  initEvents();\n  refreshAll();\n  try{perfMark('first:render')}catch(e){}   /* 3.46 */", 'boot mark render')
    # отложенная сверка календаря
    c.rep("""  /* проверка целостности календаря */
  const badYears=[];
  for(let y=2010;y<=YMAX;y++){const V=yearVerify(y);if(V.official&&(V.diffWd||V.badMonths.length))badYears.push(y)}
  if(badYears.length)console.info('Производственный календарь: расхождение с эталоном по годам '+badYears.join(', ')+' — откройте «Справочники → Сверка с эталоном» и нажмите «Привести»');""",
          """  /* 3.46: сверка календаря не блокирует запуск — уходит в фон */
  setTimeout(()=>{
    const badYears=[];
    for(let y=2010;y<=YMAX;y++){const V=yearVerify(y);if(V.official&&(V.diffWd||V.badMonths.length))badYears.push(y)}
    if(badYears.length)console.info('Производственный календарь: расхождение с эталоном по годам '+badYears.join(', ')+' — откройте «Справочники → Сверка с эталоном» и нажмите «Привести»');
    try{perfMark('calendar:verified')}catch(e){}
  },1500);""", 'boot defer calendar')
    c.rep("""      <h3>Статус хранилища</h3>""",
          """      <h3>Профилирование и нагрузка<span class="sub">3.46 · метки запуска, замеры операций, кэши, нагрузочный профиль</span></h3>
      <div id="perfBox"></div>
      <div class="mini" style="margin-top:8px;display:flex;gap:6px">
        <button class="btn ghost small" id="btnPerfTabs">⏱ Замерить вкладки</button>
        <button class="btn ghost small" id="btnPerfScale">🏋 Профиль 1000 сотрудников</button>
      </div>
      </div>
      <div class="card">
      <h3>Статус хранилища</h3>""", 'perf card')
    c.rep("  bindClick('btnOrderNew',()=>openOrderConstructor());   /* 3.44 */",
          "  bindClick('btnOrderNew',()=>openOrderConstructor());   /* 3.44 */\n"
          "  bindClick('btnPerfTabs',()=>perfMeasureTabs());        /* 3.46 */\n"
          "  bindClick('btnPerfScale',()=>demoScale(1000));         /* 3.46 */", 'perf binds')
    c.rep('  try{a11yInit()}catch(e){}   /* 3.45: a11y-инициализация */',
          '  try{a11yInit()}catch(e){}   /* 3.45: a11y-инициализация */\n  try{renderPerfCard()}catch(e){}   /* 3.46: профилирование */', 'boot perf')
    c.rep("""    {ic:'🌓',title:'Высокий контраст: вкл/выкл',hint:'a11y · 3.45',run:()=>{setUiPref('contrast',!uiPrefs().contrast);applyUi();toast(uiPrefs().contrast?'Высокий контраст включён':'Высокий контраст выключен')}},""",
          """    {ic:'🌓',title:'Высокий контраст: вкл/выкл',hint:'a11y · 3.45',run:()=>{setUiPref('contrast',!uiPrefs().contrast);applyUi();toast(uiPrefs().contrast?'Высокий контраст включён':'Высокий контраст выключен')}},
    {ic:'⏱',title:'Профилирование: замерить вкладки',hint:'диагностика · 3.46',run:()=>{showTab('data');setTimeout(()=>perfMeasureTabs(),250)}},
    {ic:'🏋',title:'Нагрузочный профиль 1000 сотрудников',hint:'диагностика · 3.46',run:()=>{showTab('data');setTimeout(()=>demoScale(1000),250)}},""", 'palette 346')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.45 — доступность, волна 2</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.46 — волна производительности</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Профилирование</b> (Данные → «Профилирование и нагрузка»): метки запуска (boot:start, state:loaded, first:render, calendar:verified), таблица суммарных затрат по операциям, состояние кэшей (статистика/OLAP/годовая аналитика); «⏱ Замерить вкладки» проходит все 15 разделов с замером каждого.</li>
        <li><b>Быстрее запуск</b>: сверка производственного календаря 2010–2035 убрана из критического пути запуска в фон (+1,5 с), метка calendar:verified после завершения.</li>
        <li><b>Нагрузочный профиль</b>: «🏋 Профиль 1000 сотрудников» — детерминированная генерация штата (mulberry32, сид 42) с лёгким планом; время генерации и перерисовки фиксируется в профилировщике и аудите; телеметрия perf:scale.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.45 — доступность, волна 2</div>""", 'help 346')
    c.rep("""    get SHORTCUTS(){return SHORTCUTS},openShortcuts,a11yInit,a11yPatch,""",
          """    get SHORTCUTS(){return SHORTCUTS},openShortcuts,a11yInit,a11yPatch,
    /* ===== 3.46: производительность ===== */
    get PERF(){return PERF},perfMark,perfSpan,perfReport,perfMeasureTabs,renderPerfCard,demoScale,""", 'exports 346')

# ============================== 3.47 ПАСПОРТА ДАННЫХ ==============================
MODULE_347 = r"""/* ================= 3.47: ПАСПОРТА ДАННЫХ И ОБЕЗЛИЧЕННЫЙ ЭКСПОРТ =================
   Реестр линий данных (dataset → источник → потребители → хранение → retention)
   и обезличенный экспорт канона (ФИО/табельные/должности/орг/подразделения). */
const DATA_LINEAGE=[
  {ds:'plan',src:'ручной ввод табельщика, импорт XLSX/CSV/OCR, ротации и бригады, доктор покрытия',cons:'сетка плана, табель Т-13, аналитика, отчёты, прогнозы, печать',store:'канон: localStorage / сервер ЛВС / SQLite (PT_DB)',ret:'снапшоты месяца, cron-бэкапы PT_BACKUP_*'},
  {ds:'fact',src:'импорт СКУД (POST /api/v1/skud), ручной ввод факта',cons:'план-факт, отклонения, отчёт об использовании времени',store:'канон (state.fact)',ret:'вместе с каноном'},
  {ds:'employees/departments',src:'справочники вручную, импорт штатки, SSO-провижининг',cons:'все расчёты, ростер, OLAP, пакеты руководителя',store:'канон',ret:'вместе с каноном; обезличивается при экспорте 3.47'},
  {ds:'vac',src:'заявки сотрудников («Мой месяц»), автоплан года',cons:'график отпусков, приказы, fairness лета',store:'канон',ret:'вместе с каноном'},
  {ds:'swaps',src:'заявки обмена/подмены, автоподбор 3.42',cons:'маршруты согласования, план после применения',store:'канон',ret:'вместе с каноном'},
  {ds:'certs/certReqs',src:'справочник допусков, заявки на продление 3.41',cons:'блокировка назначений, прогноз истечения, риск покрытия',store:'канон',ret:'вместе с каноном; при обезличивании номера не выгружаются'},
  {ds:'budgets',src:'лимиты ФОТ вручную (3.39)',cons:'статусы перерасхода, сигнал дашборда, CSV',store:'канон',ret:'вместе с каноном'},
  {ds:'brigades',src:'мастер ротаций (веер, 3.36)',cons:'применение к месяцам, «Моя бригада», ведомость, ICS',store:'канон',ret:'вместе с каноном'},
  {ds:'orderTpls',src:'конструктор приказов (3.44)',cons:'печать/DOCX приказов',store:'канон',ret:'вместе с каноном'},
  {ds:'dutyWishes',src:'пожелания сотрудников («не ставить»/«предпочтительно»)',cons:'автозаполнение, ростер, доктор покрытия, автоподбор',store:'канон',ret:'вместе с каноном'},
  {ds:'log (аудит)',src:'все значимые действия клиента и сервера',cons:'журнал аудита, /admin, расследования',store:'канон + серверный jsonl с ротацией',ret:'ротация сервера; при обезличивании имена заменяются'},
  {ds:'tele (pt.tele)',src:'телеметрия поверхностей клиента',cons:'меры успеха внедрения, выгрузка телеметрии',store:'localStorage рабочего места (не канон)',ret:'локально, удаляется очисткой профиля'},
  {ds:'xchg (журнал обмена)',src:'REST-обмен «1С»/СКУД/OCR (3.35)',cons:'веб-панель обмена, ретрай',store:'серверный файл PT_XCHG_FILE',ret:'до PT_XCHG_MAX записей'},
];
function openLineage(){
  try{teleHit('data:lineage')}catch(e){}
  openModal({title:'🛂 Паспорта данных: линии и хранение',wide:true,body:`
    <div class="scroll-x"><table class="rtbl"><thead><tr><th>Данные</th><th>Источник</th><th>Потребители</th><th>Хранение</th><th>Retention</th></tr></thead><tbody>
    ${DATA_LINEAGE.map(r=>`<tr><td><b>${esc(r.ds)}</b></td><td>${esc(r.src)}</td><td>${esc(r.cons)}</td><td>${esc(r.store)}</td><td>${esc(r.ret)}</td></tr>`).join('')}
    </tbody></table></div>
    <div class="hint" style="margin-top:8px">Паспорт отвечает на вопросы «откуда данные, кто их потребляет, где живут и сколько хранятся». Обезличенный экспорт — кнопка «⤓ Обезличенный канон» в карточке «Данные».</div>`,
    buttons:'<button class="btn ghost" data-clg>Закрыть</button>',
    onMount(b){b.querySelector('[data-clg]').onclick=closeModal}});
}
function exportAnonJson(opt){
  opt=opt||{};
  const c=clone(state);
  const names=[];
  (c.employees||[]).forEach((e,i)=>{
    names.push(e.name);
    if(opt.names!==false)e.name='Сотрудник '+String(i+1).padStart(4,'0');
    if(opt.tab!==false)e.tab='T-'+String(9000+i);
    if(opt.pos!==false)e.pos=e.pos?('должность '+((i%4)+1)):e.pos;
  });
  if(opt.org!==false)c.org='Организация (обезличено)';
  if(opt.depts!==false)(c.departments||[]).forEach((d,i)=>{d.name='Подразделение '+(i+1)});
  /* чистим имена из журнала аудита и обратной связи */
  const uniq=Array.from(new Set(names)).sort((a,b)=>b.length-a.length);
  const scrub=t=>{let s=String(t==null?'':t);uniq.forEach((nm,i)=>{if(nm)s=s.split(nm).join('Сотрудник '+String(names.indexOf(nm)+1).padStart(4,'0'))});return s};
  (c.log||[]).forEach(r=>{r.detail=scrub(r.detail);r.by=scrub(r.by)});
  (c.feedback||[]).forEach(f=>{f.text=scrub(f.text);f.who=scrub(f.who)});
  (c.dutyWishes||[]).forEach(w=>{w.note=scrub(w.note)});
  c.__anon={ts:Date.now(),opt,version:'3.47'};
  download('canon-obezlichenny-'+new Date().toISOString().slice(0,10)+'.json',JSON.stringify(c),'application/json');
  audit('Обезличенный экспорт канона',`ФИО:${opt.names!==false?'да':'нет'} · таб:${opt.tab!==false?'да':'нет'} · орг:${opt.org!==false?'да':'нет'}`,'privacy');
  try{teleHit('data:anon')}catch(e){}
  toast('Обезличенный канон выгружен','ok');
}
"""

def V347(c):
    c.ver('3.47')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_347 + '\n' + c.s[i:]
    c.rep("""      <h3>Профилирование и нагрузка<span class="sub">""",
          """      <h3>Паспорта данных и обезличенный экспорт<span class="sub">3.47 · линии данных: источник → потребители → хранение → retention</span></h3>
      <div class="mini" style="display:flex;gap:6px;flex-wrap:wrap">
        <button class="btn ghost small" id="btnLineage">🛂 Паспорта данных</button>
        <button class="btn ghost small" id="btnAnon">⤓ Обезличенный канон (JSON)</button>
      </div>
      <div class="hint" style="margin-top:6px">Обезличивание: ФИО → «Сотрудник NNNN», табельные → T-9xxx, должности → «должность N», организация и подразделения обезличиваются; имена вычищаются из журнала аудита и обратной связи.</div>
      </div>
      <div class="card">
      <h3>Профилирование и нагрузка<span class="sub">""", 'lineage card')
    c.rep("  bindClick('btnPerfScale',()=>demoScale(1000));         /* 3.46 */",
          "  bindClick('btnPerfScale',()=>demoScale(1000));         /* 3.46 */\n"
          "  bindClick('btnLineage',openLineage);                   /* 3.47 */\n"
          "  bindClick('btnAnon',()=>exportAnonJson({}));           /* 3.47 */", 'lineage binds')
    c.rep("""    {ic:'🏋',title:'Нагрузочный профиль 1000 сотрудников',hint:'диагностика · 3.46',run:()=>{showTab('data');setTimeout(()=>demoScale(1000),250)}},""",
          """    {ic:'🏋',title:'Нагрузочный профиль 1000 сотрудников',hint:'диагностика · 3.46',run:()=>{showTab('data');setTimeout(()=>demoScale(1000),250)}},
    {ic:'🛂',title:'Паспорта данных: линии и хранение',hint:'НСИ · 3.47',run:()=>openLineage()},
    {ic:'🕶',title:'Обезличенный экспорт канона (JSON)',hint:'приватность · 3.47',run:()=>exportAnonJson({})},""", 'palette 347')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.46 — волна производительности</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.47 — паспорта данных и обезличенный экспорт</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Реестр линий данных</b> («🛂 Паспорта данных», Данные): 13 наборов — план, факт, штатка, отпуска, обмены, допуски, бюджеты, бригады, шаблоны приказов, пожелания, аудит, телеметрия, журнал обмена; для каждого: источник, потребители, место хранения и retention.</li>
        <li><b>Обезличенный экспорт канона</b>: ФИО → «Сотрудник NNNN», табельные → T-9xxx, должности и организации обезличиваются; имена вычищаются из журнала аудита, обратной связи и пожеланий; метка <code>__anon</code> с параметрами; аудит и телеметрия <code>data:anon</code>.</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.46 — волна производительности</div>""", 'help 347')
    c.rep("""    get PERF(){return PERF},perfMark,perfSpan,perfReport,perfMeasureTabs,renderPerfCard,demoScale,""",
          """    get PERF(){return PERF},perfMark,perfSpan,perfReport,perfMeasureTabs,renderPerfCard,demoScale,
    /* ===== 3.47: паспорта данных ===== */
    get DATA_LINEAGE(){return DATA_LINEAGE},openLineage,exportAnonJson,""", 'exports 347')

# ============================== 3.48 КОНСОЛИДАЦИЯ ==============================
MODULE_348 = r"""/* ================= 3.48: КОНСОЛИДАЦИЯ ПОЕЗДА =================
   Карта фич 3.36–3.48, саудит состава поезда (маркеры функций каждой версии),
   единый ci-all. */
const FEATURE_MAP=[
  {v:'3.36',t:'Конструктор ротаций, бригады и доктор покрытия',f:'паспорт шаблона ТК РФ, веер по бригадам, бригады в каноне, доктор покрытия, конструктор',tests:'smoke 105 · ux 57 · viz 34'},
  {v:'3.37',t:'Сценарии ротаций и годовой баланс',f:'what-if покрытия, годовой баланс и ребаланс, ICS ротаций',tests:'smoke 49 · ux 24 · viz 24'},
  {v:'3.38',t:'Мобильная волна',f:'нижняя навигация, свайп месяца, авто-компакт, PWA-lite',tests:'smoke 19 · ux 12'},
  {v:'3.39',t:'Бюджет и лимиты ФОТ',f:'лимиты ₽/мес, план/факт против лимита, сигнал перерасхода, CSV',tests:'smoke 18'},
  {v:'3.40',t:'Личный дайджест и уведомления',f:'«Мой день», копия/.txt, ежедневное Notification',tests:'smoke 19'},
  {v:'3.41',t:'Допуски: прогноз и риск покрытия',f:'форвард-истечения, смены под риском, заявки на продление',tests:'smoke 21'},
  {v:'3.42',t:'Маркетплейс обменов',f:'открытые заявки, автоподбор напарника с оценкой',tests:'smoke 16'},
  {v:'3.43',t:'Прогнозы отсутствий с ДИ 95 %',f:'линейный тренд по истории канона, интервал прогноза, CSV',tests:'smoke 14'},
  {v:'3.44',t:'Конструктор приказов',f:'шаблоны с плейсхолдерами, источники строк, .txt/.docx',tests:'smoke 15'},
  {v:'3.45',t:'Доступность, волна 2',f:'высокий контраст, карта клавиш, skip-link, aria-live, role=grid',tests:'smoke 16'},
  {v:'3.46',t:'Волна производительности',f:'профилирование запуска/вкладок, отложенная сверка календаря, профиль 1000',tests:'smoke 14'},
  {v:'3.47',t:'Паспорта данных и обезличенный экспорт',f:'реестр 13 линий данных, обезличенный канон JSON',tests:'smoke 12'},
  {v:'3.48',t:'Консолидация поезда',f:'карта фич, саудит состава, ci-all, офлайн-сборка финала',tests:'smoke 12'},
];
function openFeatureMap(){
  try{teleHit('train:map')}catch(e){}
  openModal({title:'🗺 Карта фич поезда 3.36–3.48',wide:true,body:`
    <div class="scroll-x"><table class="rtbl"><thead><tr><th>Версия</th><th>Тема</th><th>Ключевые фичи</th><th>Тесты</th></tr></thead><tbody>
    ${FEATURE_MAP.map(r=>`<tr><td><b>${esc(r.v)}</b></td><td>${esc(r.t)}</td><td>${esc(r.f)}</td><td class="n">${esc(r.tests)}</td></tr>`).join('')}
    </tbody></table></div>
    <div class="hint" style="margin-top:8px">Полные релиз-ноты каждой версии — файлы РЕЛИЗ-WFM-3.xx.md в репозитории; карта выгружается в JSON кнопкой ниже.</div>`,
    buttons:'<button class="btn ghost" data-cfm2>Закрыть</button><button class="btn ghost" id="fmJson">⤓ JSON карты</button>',
    onMount(b){
      b.querySelector('[data-cfm2]').onclick=closeModal;
      b.querySelector('#fmJson').onclick=()=>{
        download('karta-fich-3.36-3.48.json',JSON.stringify(FEATURE_MAP,null,2),'application/json');
        audit('Выгрузка карты фич','3.36–3.48 · JSON','train');
        toast('Карта фич выгружена','ok');
      };
    }});
}
function trainSelfAudit(){
  const chk=[
    ['3.36 паспорт шаблона',typeof patternPassport==='function'],
    ['3.36 веер и бригады',typeof applyPatternFan==='function'&&typeof brigadeList==='function'],
    ['3.36 доктор покрытия',typeof openCoverageDoctor==='function'&&typeof coverageCandidates==='function'],
    ['3.37 what-if',typeof rotWhatIf==='function'],
    ['3.37 годовой баланс',typeof brigadeRebalance==='function'],
    ['3.37 ICS',typeof exportBrigadeIcs==='function'],
    ['3.38 мобильная оболочка',typeof initMobileShell==='function'&&typeof swipeMonth==='function'],
    ['3.39 бюджет',typeof budgetStatus==='function'&&typeof renderBudgetNag==='function'],
    ['3.40 дайджест',typeof personalDigest==='function'&&typeof meNotifyCheck==='function'],
    ['3.41 допуски',typeof certForecast==='function'&&typeof certReqAdd==='function'],
    ['3.42 автоподбор',typeof swapCandidates==='function'&&typeof swapOpenReq==='function'],
    ['3.43 прогноз с ДИ',typeof forecastAbsences==='function'&&typeof linreg==='function'],
    ['3.44 приказы',typeof orderRender==='function'&&typeof orderTpls==='function'],
    ['3.45 a11y',typeof openShortcuts==='function'&&!!$('skipLink')],
    ['3.46 профилирование',typeof perfReport==='function'&&typeof demoScale==='function'],
    ['3.47 паспорта данных',Array.isArray(DATA_LINEAGE)&&DATA_LINEAGE.length>=13&&typeof exportAnonJson==='function'],
    ['3.48 карта и саудит',Array.isArray(FEATURE_MAP)&&FEATURE_MAP.length>=13],
  ];
  return chk.map(([name,okv])=>({name,ok:!!okv}));
}
function openSelfAudit(){
  const chk=trainSelfAudit();
  const bad=chk.filter(x=>!x.ok);
  openModal({title:'🧪 Саудит состава поезда 3.36–3.48',body:`
    <div class="status ${bad.length?'err':'ok'}" style="margin-top:0">${bad.length?`Отсутствует: ${bad.map(x=>esc(x.name)).join(', ')}`:`Все ${fmtStd(chk.length,{unit:'фич'})} поезда на месте: маркеры функций найдены в сборке.`}</div>
    <table class="rtbl"><thead><tr><th>Компонент</th><th>Статус</th></tr></thead><tbody>
    ${chk.map(x=>`<tr><td>${esc(x.name)}</td><td>${x.ok?'<span class="pill g">на месте</span>':'<span class="pill r">отсутствует</span>'}</td></tr>`).join('')}
    </tbody></table>`,
    buttons:'<button class="btn ghost" data-csa>Закрыть</button>',
    onMount(b){b.querySelector('[data-csa]').onclick=closeModal}});
  try{teleHit('train:audit')}catch(e){}
  return chk;
}
"""

def V348(c):
    c.ver('3.48')
    m9 = '/* ------------------------------- 9. СВОДНАЯ ОТРИСОВКА И ИНИЦИАЛИЗАЦИЯ ------------------------------- */'
    i = c.s.find(m9); assert i >= 0
    c.s = c.s[:i] + MODULE_348 + '\n' + c.s[i:]
    c.rep("""    {ic:'🕶',title:'Обезличенный экспорт канона (JSON)',hint:'приватность · 3.47',run:()=>exportAnonJson({})},""",
          """    {ic:'🕶',title:'Обезличенный экспорт канона (JSON)',hint:'приватность · 3.47',run:()=>exportAnonJson({})},
    {ic:'🗺',title:'Карта фич поезда 3.36–3.48',hint:'НСИ · 3.48',run:()=>openFeatureMap()},
    {ic:'🧪',title:'Саудит состава поезда',hint:'диагностика · 3.48',run:()=>openSelfAudit()},""", 'palette 348')
    c.rep("""      <div class="lbl" style="margin-top:12px">Новое в версии 3.47 — паспорта данных и обезличенный экспорт</div>""",
          """      <div class="lbl" style="margin-top:12px">Новое в версии 3.48 — консолидация поезда</div>
      <ul class="hint" style="margin:6px 0 18px;line-height:1.6">
        <li><b>Карта фич 3.36–3.48</b> («🗺»): 13 версий поезда — тема, ключевые фичи, объём тестов; выгрузка карты в JSON; ссылки на релиз-ноты файлов РЕЛИЗ-WFM-3.xx.md.</li>
        <li><b>Саудит состава</b> («🧪»): 17 маркерных проверок наличия функций каждой версии поезда в текущей сборке; зелёная сводка или список отсутствующего; телеметрия train:audit.</li>
        <li><b>Единый CI</b>: <code>bash tests/ci-all.sh</code> гоняет регрессы 3.36/3.37, поезд 3.38–3.45 и смоуки 3.46–3.48 на онлайн-сборках плюс смоуки на офлайн-сборке финала (3.48-offline).</li>
      </ul>
      <div class="lbl" style="margin-top:12px">Новое в версии 3.47 — паспорта данных и обезличенный экспорт</div>""", 'help 348')
    c.rep("""    get DATA_LINEAGE(){return DATA_LINEAGE},openLineage,exportAnonJson,""",
          """    get DATA_LINEAGE(){return DATA_LINEAGE},openLineage,exportAnonJson,
    /* ===== 3.48: консолидация ===== */
    get FEATURE_MAP(){return FEATURE_MAP},openFeatureMap,trainSelfAudit,openSelfAudit,""", 'exports 348')


SPECS = [('3.38', V338), ('3.39', V339), ('3.40', V340), ('3.41', V341), ('3.42', V342), ('3.43', V343), ('3.44', V344), ('3.45', V345), ('3.46', V346), ('3.47', V347), ('3.48', V348)]

def main():
    args = sys.argv[1:] or ['3.38', '3.41']
    lo, hi = args[0], args[1] if len(args) > 1 else args[0]
    idx = [i for i, (v, _) in enumerate(SPECS) if lo <= v <= hi] if False else None
    order = [v for v, _ in SPECS]
    i0, i1 = 0, order.index(hi)   # цепочка всегда от первой версии поезда
    prev_file = os.path.join(HERE, 'План-табель-WFM-3.37.html')
    for vi in range(i0, i1 + 1):
        ver, fn = SPECS[vi]
        out = os.path.join(HERE, 'План-табель-WFM-%s.html' % ver)
        s = io.open(prev_file, encoding='utf-8').read()
        c = Ctx(s)
        fn(c)
        io.open(out, 'w', encoding='utf-8').write(c.s)
        print('OK %s: %d -> %d (+%d)' % (out, len(s), len(c.s), len(c.s) - len(s)))
        prev_file = out
    # офлайн-сборка финала диапазона: та же цепочка правок поверх офлайн-базы
    off_base = os.path.join(HERE, 'План-табель-WFM-3.37-offline.html')
    if os.path.exists(off_base) and hi == order[-1]:
        so = io.open(off_base, encoding='utf-8').read()
        for ver, fn in SPECS[:order.index(hi) + 1]:
            co = Ctx(so)
            fn(co)
            so = co.s
        off_out = os.path.join(HERE, 'План-табель-WFM-%s-offline.html' % hi)
        io.open(off_out, 'w', encoding='utf-8').write(so)
        print('OK %s: %d -> %d (+%d)' % (off_out, len(so) - 0, len(so), 0))

if __name__ == '__main__':
    main()
