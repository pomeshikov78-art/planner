/* ============================================================================
   WFM 3.37 · viz-337.mjs — визуальный стандарт форм 3.37 (конвенция viz-332/333):
   fmtStd, ступенчатые пиллы, role/aria таблиц и лент, светлая печать, НСИ-реестры.
   Запуск:  node tests/viz-337.mjs [файл.html]
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
let dl = null;
window.download = (name, content, mime) => { dl = { name, content, mime }; };
if (!window.crypto || !window.crypto.subtle) {
  const { webcrypto } = await import('node:crypto');
  try { Object.defineProperty(window, 'crypto', { value: webcrypto, configurable: true }); } catch (e) {}
}
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
const doc = window.document;
const cur = APP.cur;
for (let i = 0; i < 40; i++) {
  if (/Добро пожаловать/.test(($('modalBox') || {}).innerHTML || '')) { W.closeModal(); break; }
  await new Promise(r => setTimeout(r, 100));
}
await new Promise(r => setTimeout(r, 300));
if (/Добро пожаловать/.test(($('modalBox') || {}).innerHTML || '')) W.closeModal();

/* синтетический отдел и бригады для детерминированных проверок */
APP.state.departments.push({ id: 'vzw', name: 'Виз-337', minDuty: 2, dutyCode: 'Д1' });
const es = Array.from({ length: 8 }, (_, i) => ({ id: 'vw' + (i + 1), deptId: 'vzw', name: 'Визов В-' + (i + 1), pos: 'дежурный', rate: 1, dutyEligible: true, tab: 'VZW-' + (i + 1), vacationDays: 28, hoursWeek: 0 }));
APP.state.employees.push(...es);
W.applyPatternFan('p2', es, cur.y, cur.m, `${cur.y}-${String(cur.m).padStart(2, '0')}-01`, false, 4, { save: true });

section('What-if: стандарт чисел и aria');
W.openRotWhatIf();
doc.querySelector('#wiPat').value = 'p2';
doc.querySelector('#wiPat').dispatchEvent(new window.Event('change'));
W.showTab('plan');
const wiTbl = doc.querySelector('#wiBody table');
ok(wiTbl && wiTbl.getAttribute('role') === 'table' && /Сценарии числа бригад/.test(wiTbl.getAttribute('aria-label') || ''), 'what-if: таблица role="table" + aria-имя');
const wiText = doc.querySelector('#wiBody').textContent;
ok(/182,6/.test(wiText), 'what-if: часы на чел./мес = 182,6 (fmtStd, запятая)');
const DIMv = new Date(cur.y, cur.m, 0).getDate();
const expDuty = (Math.round(0.25 * DIMv * 10) / 10).toFixed(1).replace('.', ',');
ok(wiText.includes(expDuty), 'what-if: дежурств на чел. = ' + expDuty + ' (fmtStd, запятая)');
ok(doc.querySelectorAll('#modalBox select[aria-label]').length >= 2, 'what-if: aria-label у селектов шаблон/подразделение');
ok(doc.querySelectorAll('#wiBody .pill.g').length > 0 && doc.querySelectorAll('#wiBody .pill.r, #wiBody .pill.g').length > 0, 'what-if: ступенчатые пиллы оптимума/дефицита');
W.closeModal();

section('Годовой баланс: aria и шкалы');
W.openBrigadeYear();
const byTbl = doc.querySelector('#byBody table');
ok(byTbl && byTbl.getAttribute('role') === 'table' && /Годовой баланс бригад/.test(byTbl.getAttribute('aria-label') || ''), 'баланс: таблица role="table" + aria-имя');
const byText = doc.querySelector('#byBody').textContent;
ok(/среднее дежурств на человека: \d+,\d/.test(byText), 'баланс: среднее с десятичной запятой');
ok(/разброс \(SD\): \d+,\d/.test(byText), 'баланс: SD с десятичной запятой');
ok(/\d+ дн/.test(byText), 'баланс: фазы бригад в стандарте fmtStd («N дн»)');
ok(doc.querySelectorAll('#byBody .pill').length >= 3, 'баланс: сводные пиллы (среднее/SD/конфликты)');
W.closeModal();

section('ICS: RFC 5545 и экранирование');
dl = null;
W.exportBrigadeIcs(APP.state.brigades.map(b => b.id), cur.y, 'viz-rot');
ok(dl && dl.mime === 'text/calendar', 'ICS: mime text/calendar');
ok(dl.content.split('\r\n').length > 100, 'ICS: CRLF-строки');
ok(/BEGIN:VCALENDAR\r\nVERSION:2\.0\r\nPRODID:-\/\/PlanTabel\/\/RU/.test(dl.content), 'ICS: обязательные свойства календаря');
ok((dl.content.match(/BEGIN:VEVENT/g) || []).length === (dl.content.match(/END:VEVENT/g) || []).length, 'ICS: VEVENT сбалансированы');
ok(/SUMMARY:Д1 · Визов/.test(dl.content), 'ICS: SUMMARY «код · ФИО»');
ok(!/[<>]/.test(dl.content.replace(/&lt;|&gt;/g, '')), 'ICS: экранирование угловых скобок в текстах');

section('НСИ, телеметрия, справка, палитра');
ok(APP.WIDGET_REGISTRY.some(w => w.id === 'rotWhatIf') && APP.WIDGET_REGISTRY.some(w => w.id === 'brigYear'), 'паспорт виджетов: rotWhatIf, brigYear');
ok(['rotWhatIf', 'brigYear'].every(id => APP.reportClass(APP.INTERACTIVE_REPORTS.find(r => r.id === id)) === 'интерактивный'), 'реестр отчётов: оба 5/5');
const wp = JSON.stringify(W.widgetsPassport());
ok(wp.includes('rotWhatIf') && wp.includes('brigYear'), 'JSON-паспорт виджетов включает формы 3.37');
const tele = JSON.parse(window.localStorage.getItem('pt.tele') || '{}');
ok(tele['rot:whatif'] > 0 && tele['rot:year'] > 0 && tele['rot:ics'] > 0, 'телеметрия: rot:whatif / rot:year / rot:ics');
ok(/Новое в версии 3\.37/.test(html) && /What-if «бригады против покрытия»/.test(html), 'справка: блок 3.37 с what-if');
ok(/What-if ротации: бригады против покрытия/.test(html) && /Годовой баланс бригад и ребалансировка/.test(html) && /ICS моей ротации на год/.test(html), 'палитра: три команды 3.37');
W.showHelp();
ok(/Ребалансировка/.test($('modalBox').textContent), 'справка: ребалансировка описана');
W.closeModal();

section('Чистота рантайма');
ok(runtimeErrors.length === 0, 'нет рантайм-ошибок' + (runtimeErrors.length ? ': ' + runtimeErrors.slice(0, 4).join(' | ') : ''));

console.log(`\n===== viz-337 (${file.split('/').pop()}): PASS ${pass} · FAIL ${fail} =====`);
try { window.close(); } catch (e) {}
process.exit(fail ? 1 : 0);
