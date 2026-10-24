/* ============================================================================
   WFM 3.36 · viz-336.mjs — визуальный стандарт новых форм («Конструктор
   ротаций, бригады и доктор покрытия») по конвенции tests/viz-332.mjs:
   fmtStd, ступенчатые шкалы статусов, role="img" + aria-имена, светлая
   печать, темизация через color-mix, реестры НСИ.
   Запуск:  node tests/viz-336.mjs [файл.html]
   ============================================================================ */
import { readFileSync } from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const file = process.argv[2] || new URL('../План-табель-WFM-3.36.html', import.meta.url).pathname;
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
const DIM = new Date(cur.y, cur.m, 0).getDate();

section('Печать и темы (CSS)');
ok(/@media print\{\.rot-chip,\.covcell/.test(html), 'печать: чипы и ячейки покрытия принудительно видимы в @media print');
ok(/\.covcell\.def\{background:color-mix\(in srgb,var\(--red\)/.test(html) &&
   /\.covcell\.over\{background:color-mix\(in srgb,var\(--amber\)/.test(html) &&
   /\.covcell\.ok\{background:color-mix\(in srgb,var\(--green\)/.test(html), 'ступенчатая шкала статусов: красный/жёлтый/зелёный через токены темы');
ok(/\.rot-chip\{[^}]*color-mix\(in srgb,var\(--c,/.test(html), 'чипы цикла темизируются через color-mix (светлая/тёмная тема)');

section('ARIA и геометрия новых форм');
W.showTab('set');
W.renderPatternsList();
const strips = doc.querySelectorAll('#patBox .rot-strip');
ok(strips.length === APP.state.patterns.length, 'каталог: у каждого шаблона лента цикла (' + strips.length + ')');
ok(Array.from(strips).every(s => s.getAttribute('role') === 'img' && /^Цикл \d+ дн\.:/.test(s.getAttribute('aria-label') || '')), 'каталог: role="img" + aria-имя «Цикл N дн.: …»');
ok(Array.from(doc.querySelectorAll('#patBox [data-patpp],#patBox [data-patdup],#patBox [data-delpat]')).every(b => (b.getAttribute('aria-label') || '').length > 3), 'каталог: aria-label у кнопок 📋/⧉/✕');
const pills = Array.from(doc.querySelectorAll('#patBox .pill'));
ok(pills.length > 0 && pills.every(p => ['g', 'a', 'r', ''].some(c => c === '' ? true : p.classList.contains(c)) && /pill/.test(p.className)), 'каталог: пиллы в ступенчатой шкале (pill g/a/r)');
ok(pills.some(p => p.classList.contains('g') || p.classList.contains('a') || p.classList.contains('r')), 'каталог: вердикты присутствуют');

section('Стандарт чисел fmtStd');
W.openPatternPassport('p2');
const ppText = $('modalBox').textContent;
ok(/42,0/.test(ppText), 'паспорт 1/3: 42,0 ч/нед — десятичная запятая (fmtStd)');
ok(/42,0 ч/.test(ppText), 'паспорт: единица «ч» у средних часов');
ok(/ч\/нед/.test($('patBox').textContent), 'каталог: бейдж «ч/нед» в стандарте fmtStd');
ok(/ст\. 110/.test(ppText) && /ст\. 91/.test(ppText), 'паспорт: ссылки на статьи ТК РФ');
W.closeModal();
W.showTab('plan');

section('Доктор покрытия: aria и шкалы');
W.openCoverageDoctor();
const cov = doc.querySelector('#cdBody .covstrip');
ok(cov && cov.getAttribute('role') === 'img' && /дефицитом/.test(cov.getAttribute('aria-label') || ''), 'доктор: календарь role="img" + aria-имя с числом дефицитных дней');
const cells = Array.from(doc.querySelectorAll('#cdBody .covcell'));
ok(cells.length === DIM && cells.every(c => /план \d+ из \d+/.test(c.getAttribute('title') || '')), 'доктор: ' + DIM + ' ячеек с title «план X из Y»');
ok(cells.every(c => c.querySelector('em') && /\d+/.test(c.textContent)), 'доктор: номер дня + значение в каждой ячейке');
ok(!!doc.querySelector('#cdCsv'), 'доктор: «⇩ CSV» — экспорт со штампом');
W.closeModal();

section('Мастер ротаций: предпросмотр покрытия');
W.patternWizard();
const wstrip = doc.querySelector('#pwPreview .covstrip');
ok(wstrip && wstrip.getAttribute('role') === 'img' && /бригад/.test(wstrip.getAttribute('aria-label') || ''), 'мастер (веер): календарь покрытия role="img" + aria');
ok(/Покрытие по бригадам/.test(doc.querySelector('#pwPreview').textContent), 'мастер: заголовок предпросмотра покрытия');
doc.querySelector('#pwMode').value = 'single';
doc.querySelector('#pwMode').dispatchEvent(new window.Event('change'));
ok(!doc.querySelector('#pwPreview .covstrip') && !!doc.querySelector('#pwPreview .pwstrip'), 'мастер (общая фаза): прежняя лента без aria-календаря');
W.closeModal();

section('«Моя бригада» и ведомость');
{
  // синтетическая бригада для детерминированной проверки
  APP.state.departments.push({ id: 'dviz', name: 'Виз-тест', minDuty: 1, dutyCode: 'Д1' });
  const es = Array.from({ length: 4 }, (_, i) => ({ id: 'vz' + (i + 1), deptId: 'dviz', name: 'Визов В-' + (i + 1), pos: 'дежурный', rate: 1, dutyEligible: true, tab: 'VZ-' + (i + 1), vacationDays: 28, hoursWeek: 0 }));
  APP.state.employees.push(...es);
  W.applyPatternFan('p2', es, cur.y, cur.m, `${cur.y}-${String(cur.m).padStart(2, '0')}-01`, false, 2, { save: true });
}
W.meSetEmp(APP.state.brigades[APP.state.brigades.length - 1].members[0]);
W.showTab('me');
const mb = $('meBrigCard');
ok(mb && mb.querySelector('.pwstrip').getAttribute('role') === 'img' && /Моя ротация на/.test(mb.querySelector('.pwstrip').getAttribute('aria-label') || ''), '«Моя бригада»: лента role="img" + aria «Моя ротация на …»');
ok(/смещение фазы \d+ дн/.test(mb.innerHTML), '«Моя бригада»: смещение фазы в стандарте fmtStd (целое + «дн»)');
W.showTab('plan');
W.printBrigadeSheet();
const pa = $('printArea');
ok(/Бригадная ведомость ротации за/.test(pa.innerHTML), 'ведомость: заголовок формы');
ok(pa.querySelectorAll('thead th').length === DIM + 3, 'ведомость: ' + (DIM + 3) + ' колонок (дни + ФИО + дежурств + часов)');
ok(!/var\(--/.test(pa.innerHTML), 'ведомость: инлайновые светлые цвета без токенов темы (печать всегда светлая)');
ok(/@page\{size:A4 landscape/.test(pa.innerHTML), 'ведомость: альбомная ориентация через авто-лист');
ok(/Фаза сквозная/.test(pa.innerHTML), 'ведомость: методическая сноска о сквозной фазе');

section('Реестры НСИ');
const wr = APP.WIDGET_REGISTRY.map(w => w.id);
ok(['rotPassport', 'brigCard', 'covDoctor', 'covWizard'].every(id => wr.includes(id)), 'паспорт виджетов: 4 новых виджета');
const wp = JSON.stringify(W.widgetsPassport());
ok(wp.includes('covDoctor') && wp.includes('brigCard'), 'паспорт виджетов: выгрузка включает виджеты 3.36');
const ir = APP.INTERACTIVE_REPORTS.find(r => r.id === 'covDoctor');
ok(ir && ['filter', 'drill', 'live', 'insight', 'export'].every(k => ir.crit[k] === 1), 'реестр отчётов: доктор покрытия 5/5 критериев');
ok(APP.reportClass(ir) === 'интерактивный', 'реестр отчётов: класс «интерактивный»');
ok(APP.INTERACTIVE_CRITERIA.length === 5, 'формальное определение интерактивного отчёта: 5 критериев');

section('Справка и палитра');
ok(/Волна 2 \(НСИ и поверхности\)/.test(html), 'справка: блок волны 2');
ok(/Бригадная ведомость \(печать\)/.test(html), 'палитра: команда печати ведомости');

section('Чистота рантайма');
ok(runtimeErrors.length === 0, 'нет рантайм-ошибок' + (runtimeErrors.length ? ': ' + runtimeErrors.slice(0, 4).join(' | ') : ''));

console.log(`\n===== viz-336 (${file.split('/').pop()}): PASS ${pass} · FAIL ${fail} =====`);
try { window.close(); } catch (e) {}
process.exit(fail ? 1 : 0);
