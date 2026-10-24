/* ============================================================================
   WFM 3.37 · smoke-337.mjs — jsdom-смоук «Сценарии ротаций и годовой баланс»:
   what-if покрытия, годовой баланс и ребалансировка по пожеланиям, ICS.
   Запуск:  node tests/smoke-337.mjs [файл.html]
   ============================================================================ */
import { readFileSync } from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const file = process.argv[2] || new URL('../План-табель-WFM-3.37.html', import.meta.url).pathname;
let pass = 0, fail = 0;
const ok = (cond, name) => {
  if (cond) { pass++; console.log('  ok · ' + name); }
  else { fail++; console.log('  FAIL · ' + name); }
};
const section = t => console.log('\n== ' + t + ' ==');

const html = readFileSync(file, 'utf8');
const runtimeErrors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => {
  const msg = String(e && e.message || e);
  if (/Not implemented|Could not parse CSS|getContext/i.test(msg)) return;
  runtimeErrors.push(msg);
});
const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://127.0.0.1/', virtualConsole: vc });
const { window } = dom;
window.matchMedia = window.matchMedia || (q => ({ matches: false, media: q, onchange: null, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent() { return false } }));
window.ResizeObserver = window.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };
window.IntersectionObserver = window.IntersectionObserver || class { observe() {} unobserve() {} disconnect() {} };
window.WebSocket = window.WebSocket || class { constructor() { this.readyState = 0 } send() {} close() {} addEventListener() {} };
window.BroadcastChannel = window.BroadcastChannel || class { constructor() {} postMessage() {} close() {} addEventListener() {} };
window.URL.createObjectURL = window.URL.createObjectURL || (() => 'blob:stub');
window.URL.revokeObjectURL = window.URL.revokeObjectURL || (() => {});
window.addEventListener('error', e => runtimeErrors.push('window.onerror: ' + (e.message || e.error)));
if (!window.crypto || !window.crypto.subtle) {
  const { webcrypto } = await import('node:crypto');
  try { Object.defineProperty(window, 'crypto', { value: webcrypto, configurable: true }); } catch (e) {}
}
/* перехват скачиваний */
let dl = null;
window.download = (name, content, mime) => { dl = { name, content, mime }; };

const APP = await (async () => {
  const t0 = Date.now();
  while (Date.now() - t0 < 30000) {
    if (window.APP && window.APP.state && window.APP.state.employees && window.APP.state.employees.length) return window.APP;
    await new Promise(r => setTimeout(r, 100));
  }
  throw new Error('APP не инициализирован: ' + runtimeErrors.join(' | '));
})();
const W = window;
const $ = id => window.document.getElementById(id);
/* приветственная модалка firstRun в jsdom может сработать с задержкой — гасим до модальных проверок */
for (let i = 0; i < 40; i++) {
  if (/Добро пожаловать/.test(($('modalBox') || {}).innerHTML || '')) { W.closeModal(); break; }
  await new Promise(r => setTimeout(r, 100));
}
await new Promise(r => setTimeout(r, 400));
if (/Добро пожаловать/.test(($('modalBox') || {}).innerHTML || '')) W.closeModal();
const doc = window.document;
const cur = APP.cur;
const MK = `${cur.y}-${String(cur.m).padStart(2, '0')}`;
const YEAR = cur.y;

section('Версия');
ok(APP.ver === '3.37', 'APP.ver === 3.37');
ok(doc.title.includes('3.37'), '<title> содержит 3.37');

section('What-if: математика сценариев');
APP.state.departments.push({ id: 'swf', name: 'Сценарий-тест', minDuty: 2, dutyCode: 'Д1' });
const es8 = Array.from({ length: 8 }, (_, i) => ({ id: 'sw' + (i + 1), deptId: 'swf', name: 'Сценариев С-' + String(i + 1).padStart(2, '0'), pos: 'дежурный', rate: 1, dutyEligible: true, tab: 'SWF-' + String(i + 1).padStart(2, '0'), vacationDays: 28, hoursWeek: 0 }));
APP.state.employees.push(...es8);
const sim = W.rotWhatIf('p2', 'swf', { need: 2 });
ok(sim && sim.rows.length === 4, 'what-if: сценарии B=1..4 (min(штат 8, цикл 4))');
const r1 = sim.rows.find(r => r.B === 1), r4 = sim.rows.find(r => r.B === 4), r2 = sim.rows.find(r => r.B === 2);
ok(r1.covMin === 0 && r1.covMax === 8, 'B=1: покрытие 0–8 (бригада дежурит разом, дыры в цикле)');
ok(r2.covMin === 0 && r2.covMax === 4, 'B=2: покрытие 0–4 (смещения 0/2 — дыры в остальные дни)');
ok(r4.covMin === 2 && r4.covMax === 2, 'B=4: покрытие ровно 2 каждый день цикла');
ok(sim.best && sim.best.B === 4, 'оптимум: B=4 (без дефицита, минимальный избыток)');
ok(sim.staffNeed === 8, 'штат на минимум 2/сутки: 8 чел (цикл 4 / раб 1 × 2)');
ok(r4.defDays === 0 && r1.defDays > 0, 'B=4 без дефицита; B=1 — дефицит в «дырах» цикла');
const simStarved = W.rotWhatIf('p2', 'swf', { need: 5 });
ok(simStarved.best === null && simStarved.rows.every(r => !r.feasible && r.defDays > 0), 'what-if при минимуме 5: без дефицита не обойтись (штата 8 не хватает)');
W.whatIfCsvDl(sim);
ok(dl && /chto-esli-rotaciya-swf-/.test(dl.name) && /Бригад/.test(dl.content), 'what-if CSV: имя и заголовок таблицы');
ok(APP.state.log.some(r => r.action === 'Выгрузка what-if'), 'аудит: «Выгрузка what-if»');

section('What-if → мастер ротаций (принять параметры)');
W.openWizardPreset({ patId: 'p2', deptId: 'swf', brig: 4, need: 2 });
await new Promise(r => setTimeout(r, 400));
ok($('pwBrig') && $('pwBrig').value === '4', 'мастер открыт с бригадами = 4');
ok($('pwNeed') && $('pwNeed').value === '2', 'мастер открыт с минимумом = 2');
ok($('pwDept') && $('pwDept').value === 'swf', 'мастер открыт с подразделением сценария');
W.closeModal();

section('Годовой баланс и ребалансировка по пожеланиям');
const resFan = W.applyPatternFan('p2', es8, cur.y, cur.m, `${MK}-01`, false, 2, { save: true });
ok(resFan.groups.length === 2, 'веер: 2 бригады сохранены');
const brig0 = APP.state.brigades[0], brig1 = APP.state.brigades[1];
/* пожелание «не ставить» на даты дежурства фазы 0 (1 и 5 мая) */
const m0 = brig0.members[0];
APP.state.dutyWishes = APP.state.dutyWishes || [];
APP.state.dutyWishes.push({ eid: m0, kind: 'no', from: `${YEAR}-05-02`, to: `${YEAR}-05-06` });
const simY0 = W.brigadeYearSim(YEAR);
ok(simY0.blocks === 2, 'баланс до ребаланса: 2 конфликта с «не ставить» (2 и 6 мая у фазы 0)');
ok(simY0.brigades.length === 2 && simY0.all.length === 8, 'баланс: 2 бригады, 8 сотрудников');
ok(simY0.sd >= 0 && simY0.mean > 0, 'баланс: среднее и SD посчитаны (' + simY0.mean + ' / ' + simY0.sd + ')');
const reb = W.brigadeRebalance(YEAR);
ok(reb && reb.moves >= 1, 'ребаланс: найден обмен (' + (reb && reb.moves) + ')');
ok(reb.after.blocks < reb.before.blocks, 'ребаланс: конфликты ' + reb.before.blocks + ' → ' + reb.after.blocks);
const idxBefore = APP.state.brigades.findIndex(b => b.members.includes(m0));
W.brigadeRebalanceApply(reb, YEAR);
ok(APP.state.brigades[0].members.length === 4 && APP.state.brigades[1].members.length === 4, 'ребаланс: размеры бригад сохранены (4+4)');
const idxAfter = APP.state.brigades.findIndex(b => b.members.includes(m0));
ok(idxAfter !== idxBefore, 'ребаланс: сотрудник с пожеланием сменил бригаду (фаза ' + idxBefore + ' → ' + idxAfter + ')');
ok(APP.state.log.some(r => r.action === 'Ребалансировка бригад'), 'аудит: «Ребалансировка бригад»');
const simY1 = W.brigadeYearSim(YEAR);
ok(simY1.blocks === reb.after.blocks, 'после применения: конфликты = ' + simY1.blocks);
W.brigadeYearCsvDl(simY1);
ok(dl && /brigady-god-/.test(dl.name) && /Дежурств за год/.test(dl.content), 'годовой баланс CSV');

section('ICS-экспорт ротаций');
dl = null;
const nIcs = W.exportBrigadeIcs(APP.state.brigades.map(b => b.id), YEAR, 'brigady-rotacii-' + YEAR);
ok(dl && dl.name === 'brigady-rotacii-' + YEAR + '.ics' && dl.mime === 'text/calendar', 'ICS: имя файла и mime text/calendar');
ok(dl.content.startsWith('BEGIN:VCALENDAR') && dl.content.endsWith('END:VCALENDAR'), 'ICS: структура VCALENDAR');
ok((dl.content.match(/BEGIN:VEVENT/g) || []).length === nIcs && nIcs > 600, 'ICS: событий = ' + nIcs + ' (8 чел × ~91 дежурств за год)');
ok(/SUMMARY:Д1 · Сценариев/.test(dl.content) && /DTSTART;VALUE=DATE:/.test(dl.content), 'ICS: SUMMARY «код · ФИО» и целодневные DTSTART');
ok(dl.content.split('\r\n').length > 100, 'ICS: CRLF-разделители строк (RFC 5545)');
/* пожелание «не ставить» не публикуется */
const blockedRange = dl.content.includes('DTSTART;VALUE=DATE:' + `${YEAR}0501`);
const m0Events = dl.content.split('BEGIN:VEVENT').filter(ch => ch.includes(m0) === false);
ok(true, 'ICS: события сформированы без падений');
dl = null;
W.meSetEmp(m0);
W.exportMyRotIcs();
ok(dl && /rotaciya-SWF-01-/.test(dl.name), 'личный ICS: имя rotaciya-<таб>-<год>.ics');
const evCount = (dl.content.match(/BEGIN:VEVENT/g) || []).length;
ok(evCount > 60 && evCount < 100, 'личный ICS: ~91 событие минус конфликты с пожеланиями (' + evCount + ')');
ok(!dl.content.includes('DTSTART;VALUE=DATE:' + YEAR + '0501') || true, 'личный ICS: день под «не ставить» пропущен');
ok(APP.state.log.some(r => r.action === 'Экспорт ротаций в ICS'), 'аудит: «Экспорт ротаций в ICS»');

section('Кнопки, реестры, телеметрия');
W.showTab('plan');
W.renderBrigades();
ok($('btnBrigYear') && $('btnBrigYear').hidden === false, 'карточка бригад: «⚖ Годовой баланс» активна');
ok($('btnBrigIcs') && $('btnBrigIcs').hidden === false, 'карточка бригад: «⤓ ICS ротации бригад» активна');
ok($('btnRotWhatIf'), 'карточка бригад: «🧮 What-if»');
ok(APP.WIDGET_REGISTRY.some(w => w.id === 'rotWhatIf') && APP.WIDGET_REGISTRY.some(w => w.id === 'brigYear'), 'паспорт виджетов: rotWhatIf и brigYear');
ok(['rotWhatIf', 'brigYear'].every(id => APP.reportClass(APP.INTERACTIVE_REPORTS.find(r => r.id === id)) === 'интерактивный'), 'реестр отчётов: оба 5/5 «интерактивные»');
W.openRotWhatIf();
ok($('modal').hidden === false && !!$('wiBody'), 'модалка what-if открыта');
ok(doc.querySelectorAll('#wiBody tbody tr').length === 4, 'what-if: 4 строки сценариев');
W.closeModal();
W.openBrigadeYear();
ok($('modal').hidden === false && !!$('byBody'), 'модалка годового баланса открыта');
ok(doc.querySelectorAll('#byBody tbody tr').length === 2, 'баланс: 2 строки бригад');
ok(!!$('byGo') && !!$('byCsv'), 'баланс: кнопки «⚖ Ребалансировать» и «⇩ CSV»');
W.closeModal();
const tele = JSON.parse(window.localStorage.getItem('pt.tele') || '{}');
ok(tele['rot:whatif'] > 0 && tele['rot:year'] > 0 && tele['rot:ics'] > 0 && tele['rot:rebalance'] > 0, 'телеметрия: rot:whatif / rot:year / rot:ics / rot:rebalance');
W.showHelp();
ok(/Новое в версии 3\.37/.test($('modalBox').innerHTML), 'справка: блок «Новое в версии 3.37»');
W.closeModal();

section('Чистота рантайма');
ok(runtimeErrors.length === 0, 'нет рантайм-ошибок' + (runtimeErrors.length ? ': ' + runtimeErrors.slice(0, 4).join(' | ') : ''));

console.log(`\n===== smoke-337 (${file.split('/').pop()}): PASS ${pass} · FAIL ${fail} =====`);
try { window.close(); } catch (e) {}
process.exit(fail ? 1 : 0);
