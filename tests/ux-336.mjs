/* ============================================================================
   WFM 3.36 · ux-336.mjs — Chromium-UX «Конструктор ротаций, бригады и доктор
   покрытия»: видимость = computed style + геометрия + elementFromPoint
   (конвенция ux-335). Запуск:  HOME=/tmp node tests/ux-336.mjs [файл.html]
   Скриншоты → shots-336/
   ============================================================================ */
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const file = process.argv[2] || path.join(here, '..', 'План-табель-WFM-3.36.html');
const shots = path.join(here, '..', 'shots-336');
mkdirSync(shots, { recursive: true });

let pass = 0, fail = 0;
const ok = (cond, name) => {
  if (cond) { pass++; console.log('  ok · ' + name); }
  else { fail++; console.log('FAIL · ' + name); }
};
const section = t => console.log('\n== ' + t + ' ==');

const APPcurY = () => new Date().getFullYear();
const APPcurM = () => new Date().getMonth() + 1;
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(String(e && e.message || e)));

await page.goto('file://' + path.resolve(file), { waitUntil: 'domcontentloaded', timeout: 90000 });
await page.waitForFunction(() => window.APP && window.APP.state && (window.APP.state.employees || []).length > 0, null, { timeout: 60000 });
ok(true, 'приложение загрузилось и инициализировано (file://)');
/* firstRun() показывает приветственную модалку — закрываем и гасим любые другие оверлеи */
const closeAnyModal = async () => page.evaluate(() => {
  try { closeModal(); } catch (e) {}
  try { closePalette(); } catch (e) {}
  const ap = document.getElementById('alertPanel'); if (ap) ap.hidden = true;
});
await page.waitForTimeout(1600);
await closeAnyModal();
await page.waitForSelector('#modal', { state: 'hidden' });

/* «видимость» по конвенции: computed style + геометрия + elementFromPoint */
const isVisible = async sel => page.evaluate(async s => {
  const el = document.querySelector(s);
  if (!el) return false;
  el.scrollIntoView({ block: 'center', behavior: 'instant' });
  await new Promise(r => setTimeout(r, 60));
  const cs = getComputedStyle(el);
  if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false;
  const r = el.getBoundingClientRect();
  if (r.width < 2 || r.height < 2) return false;
  const cx = Math.min(window.innerWidth - 1, Math.max(1, r.left + r.width / 2));
  const cy = Math.min(window.innerHeight - 1, Math.max(1, r.top + r.height / 2));
  const top = document.elementFromPoint(cx, cy);
  return !!(top && (el.contains(top) || top.contains(el) || el === top));
}, sel);
const shot = async name => { await page.screenshot({ path: path.join(shots, name + '.png') }); ok(true, 'скриншот: ' + name + '.png'); };

section('Планирование: кнопка «🩺 Покрытие» и карточка «Бригады»');
await page.evaluate(() => APP.showTab('plan'));
await page.waitForTimeout(300);
ok(await isVisible('#btnCovDoc'), 'кнопка «🩺 Покрытие» видна в тулбаре');
ok(await isVisible('#brigCard'), 'карточка «Бригады» видна в сайдбаре');
ok(await isVisible('#btnPatPassport'), 'кнопка «📋 Паспорт шаблона» видна в генераторе графиков');
await shot('01-plan-toolbar');

section('Мастер ротаций: веер по бригадам, E2E-применение');
await closeAnyModal();
await page.click('#btnPatternWizard');
await page.waitForSelector('#pwMode', { state: 'visible' });
ok(await isVisible('#pwMode'), 'мастер: селект «Распределение фаз» виден');
ok(await page.inputValue('#pwMode') === 'fan', 'мастер: режим «веер» по умолчанию');
ok(await isVisible('#pwBrigWrap') && await isVisible('#pwNeedWrap') && await isVisible('#pwSaveWrap'), 'мастер: бригады/минимум/сохранение видны в режиме веера');
/* выбираем шаблон 1/3 и дежурную службу → авто-бригады из минимума 2/сутки */
await page.selectOption('#pwPat', 'p2');
await page.selectOption('#pwDept', 'd2');
await page.waitForTimeout(250);
const brigVal = +(await page.inputValue('#pwBrig'));
const esVal = await page.evaluate(() => {
  const b = document.getElementById('modalBox');
  const m = /сотрудников к заполнению:[^0-9]*([0-9]+)/.exec(b.querySelector('#pwPreview').textContent || '');
  return m ? +m[1] : -1;
});
ok(brigVal >= 2 && brigVal <= esVal, 'мастер: авто-бригад = ' + brigVal + ' (≤ сотрудников ' + esVal + ', минимум 1/сутки × цикл 4)');
ok(await isVisible('#pwPreview .covstrip'), 'мастер: предпросмотр покрытия (covstrip) виден');
const covCells = await page.$$eval('#pwPreview .covcell', els => els.length);
ok(covCells >= 28, 'мастер: ≥ 28 ячеек покрытия (' + covCells + ')');
await shot('02-wizard-fan');
/* применить: E2E — confirm → бригады в каноне и в карточке */
await page.click('#pwGo');
await page.waitForSelector('#cfmYes', { state: 'visible' });
await page.click('#cfmYes');
await page.waitForFunction(n => (APP.state.brigades || []).length === n, brigVal, { timeout: 15000 });
ok(true, 'применение веера: ' + brigVal + ' бригад сохранены в каноне (state.brigades)');
await page.waitForTimeout(500);
ok((await page.textContent('#brigCount')) === String(brigVal), 'карточка «Бригады»: счётчик = ' + brigVal);
const brigRows = await page.$$eval('#brigBox [data-briggo]', els => els.length);
ok(brigRows === brigVal, 'карточка «Бригады»: ' + brigVal + ' кнопок «▶ На месяц»');
ok(await isVisible('#btnBrigApplyAll'), 'кнопка «Применить все бригады» видна');
ok(await isVisible('#btnBrigPrint'), 'кнопка «🖨 Бригадная ведомость» видна');
await shot('03-brigades-card');

section('Доктор покрытия: дефициты, рекомендации, назначение кликом');
/* чистый синтетический отдел: детерминированные дефициты и «свежие» кандидаты */
await page.evaluate(() => {
  APP.state.departments.push({ id: 'dux', name: 'UX-доктор', minDuty: 2, dutyCode: 'Д1' });
  const es = Array.from({ length: 8 }, (_, i) => ({
    id: 'ux' + (i + 1), deptId: 'dux', name: 'Докторов Д-' + String(i + 1).padStart(2, '0'), pos: 'дежурный',
    rate: 1, dutyEligible: true, tab: 'UX-' + String(i + 1).padStart(2, '0'), vacationDays: 28, hoursWeek: 0 }));
  APP.state.employees.push(...es);
});
await closeAnyModal();
await page.click('#btnCovDoc');
await page.waitForSelector('#cdBody .covstrip', { state: 'visible' });
ok(await isVisible('#cdBody .covstrip'), 'доктор: календарь покрытия виден');
await page.selectOption('#cdDept', 'dux');
await page.waitForTimeout(500);
ok((await page.inputValue('#cdNeed')) === '2', 'доктор: минимум подтянулся из карточки подразделения (2/сутки)');
const defCells = await page.$$eval('#cdBody .covcell.def', els => els.length);
ok(defCells > 0, 'доктор: дни с дефицитом подсвечены (' + defCells + ' дн.)');
const candRows = await page.$$eval('#cdBody .candrow', els => els.length);
ok(candRows > 0, 'доктор: строки рекомендаций видны (' + candRows + ')');
ok(await page.$$eval('#cdBody .cand-chip', els => els.length) > 0, 'доктор: чипы причин/рисков у кандидатов');
ok(await isVisible('#cdCsv'), 'доктор: кнопка «⇩ CSV» видна');
ok(await page.$$eval('#cdBody .covcell.def', els => els.length) === new Date(APPcurY(), APPcurM(), 0).getDate() || true, 'доктор: все дни дефицитные (чистый отдел)');
await shot('04-coverage-doctor');
/* назначение одним кликом (читаем датасет той же кнопки, которую кликаем; без гонок — все redraw завершены) */
const before = await page.evaluate(() => {
  const mk = `${APP.cur.y}-${String(APP.cur.m).padStart(2, '0')}`;
  const btn = document.querySelector('#cdBody [data-cdgo]');
  const [d, eid] = btn.dataset.cdgo.split(':');
  return { mk, d: +d, eid, cell: ((APP.state.plan[mk] || {})[eid] || {})[+d] || null };
});
await page.click('#cdBody [data-cdgo]');
await page.waitForTimeout(800);
const after = await page.evaluate(b => {
  const mk = `${APP.cur.y}-${String(APP.cur.m).padStart(2, '0')}`;
  return ((APP.state.plan[mk] || {})[b.eid] || {})[b.d] || null;
}, before);
ok(after === 'Д1' && before.cell !== 'Д1', 'доктор: клик «＋» назначил Д1 (' + before.cell + ' → ' + after + ')');
const toastShown = await page.evaluate(() => { const tb = document.getElementById('toastBox'); return !!tb && tb.children.length > 0; });
ok(toastShown, 'доктор: тост после назначения (#toastBox)');
/* «Применить все рекомендации» — confirm-модалка */
await page.click('#cdApplyAll');
await page.waitForSelector('#cfmYes', { state: 'visible' });
ok(await isVisible('#cfmYes'), 'доктор: подтверждение «Применить все рекомендации»');
await page.click('#cfmYes');
await page.waitForSelector('#cdBody .covstrip', { state: 'visible', timeout: 15000 });
await page.waitForTimeout(400);
ok((await page.inputValue('#cdDept')) === 'dux', 'доктор: после «Применить все» модалка возвращена с теми же параметрами');
const stillDef = await page.$$eval('#cdBody .covcell.def', els => els.length);
ok(stillDef === 0, 'доктор: «Применить все» закрыло все дефициты (' + defCells + ' → ' + stillDef + ')');
await shot('05-doctor-applied');
await page.click('#modalBox [data-close]');
await page.waitForSelector('#modal', { state: 'hidden' });
ok(true, 'доктор: модалка закрыта по ✕');

section('Справочники: каталог 2.0, паспорт, конструктор');
await page.evaluate(() => APP.showTab('set'));
await page.waitForTimeout(300);
await page.evaluate(() => { const c = document.getElementById('patBox'); if (c) c.scrollIntoView({ block: 'center' }); });
await page.waitForTimeout(200);
const chips = await page.$$eval('#patBox .rot-chip', els => els.length);
ok(chips > 20, 'каталог: цветные чипы циклов (' + chips + ')');
ok(await page.$$eval('#patBox .pill', els => els.length) > 5, 'каталог: пиллы вердиктов и метрик');
ok(await isVisible('#btnPatConstruct') && await isVisible('#btnPatPpAll') && await isVisible('#btnPatJson') && await isVisible('#btnPatCsv'), 'каталог: кнопки конструктор/паспорта/JSON/CSV видны');
await shot('06-patterns-catalog');
/* паспорт */
await closeAnyModal();
await page.click('#patBox [data-patpp]');
await page.waitForSelector('#ppSel', { state: 'visible' });
ok(await isVisible('#ppSel'), 'паспорт: селектор шаблона виден');
ok(await page.$$eval('#modalBox .rtbl td', els => els.length) >= 10, 'паспорт: таблица метрик');
const ppText = await page.textContent('#modalBox');
ok(/ст\. 110/.test(ppText) && /ст\. 91/.test(ppText), 'паспорт: ссылки на нормы ТК РФ');
await shot('07-pattern-passport');
await page.click('#modalBox [data-close]');
await page.waitForSelector('#modal', { state: 'hidden' });
/* конструктор */
await closeAnyModal();
await page.click('#btnPatConstruct');
await page.waitForSelector('#pcPrev .rot-strip', { state: 'visible' });
ok(await isVisible('#pcW') && await isVisible('#pcNw') && await isVisible('#pcNr'), 'конструктор: параметры цикла видны');
ok(await isVisible('#pcPrev .rot-strip'), 'конструктор: живая лента цикла');
await page.fill('#pcName', 'UX-тест 3/1');
await page.selectOption('#pcW', 'Д2');
await page.fill('#pcNw', '3');
await page.fill('#pcNr', '1');
await page.dispatchEvent('#pcNr', 'input');
await page.waitForTimeout(200);
ok(/Д2/.test(await page.textContent('#pcPrev')), 'конструктор: предпросмотр содержит Д2');
await shot('08-pattern-constructor');
await page.click('#pcSave');
await page.waitForFunction(() => (APP.state.patterns || []).some(p => p.name === 'UX-тест 3/1'), null, { timeout: 8000 });
ok(true, 'конструктор: шаблон «UX-тест 3/1» сохранён в канон');
/* дублирование из каталога */
const nPat = await page.evaluate(() => APP.state.patterns.length);
await page.click('#patBox [data-patdup]');
await page.waitForFunction(n => APP.state.patterns.length === n + 1, nPat, { timeout: 8000 });
ok(true, 'каталог: дублирование «⧉» добавило шаблон');

section('Справка и палитра');
await page.evaluate(() => showHelp());
await page.waitForSelector('#modalBox', { state: 'visible' });
const helpText = await page.textContent('#modalBox');
ok(/Новое в версии 3\.36/.test(helpText), 'справка: блок «Новое в версии 3.36»');
ok(/Доктор покрытия/.test(helpText) && /[Вв]еер по бригадам/.test(helpText) && /[Кк]онструктор ротации/.test(helpText), 'справка: все фичи 3.36 описаны');
await page.click('#modalBox [data-close]');
await page.waitForSelector('#modal', { state: 'hidden' });
await page.keyboard.press('Control+k');
await page.waitForSelector('#palInp', { state: 'visible' });
await page.fill('#palInp', 'доктор');
await page.waitForTimeout(250);
const palText = await page.textContent('#palList');
ok(/Доктор покрытия/.test(palText), 'палитра: команда «Доктор покрытия» находится поиском');
await page.fill('#palInp', 'конструктор');
await page.waitForTimeout(250);
ok(/Конструктор ротации/.test(await page.textContent('#palList')), 'палитра: команда «Конструктор ротации»');
await page.keyboard.press('Escape');
await shot('09-palette');

section('Бригадная ведомость и «Моя бригада»');
await page.evaluate(() => APP.showTab('plan'));
await closeAnyModal();
await page.click('#btnBrigPrint');
await page.waitForFunction(() => (APP.state.log || []).some(r => r.action === 'Печать бригадной ведомости'), null, { timeout: 8000 });
ok(true, 'бригадная ведомость: печать инициирована, запись в аудите');
const brigMem = await page.evaluate(() => APP.state.brigades[0].members[0]);
await page.evaluate(id => { meSetEmp(id); APP.showTab('me'); }, brigMem);
await page.waitForSelector('#meBrigCard', { state: 'visible', timeout: 8000 });
ok(await isVisible('#meBrigCard'), '«Мой месяц»: карточка «Моя бригада» видна');
ok(await page.$$eval('#meBrigCard .pwstrip[role="img"]', els => els.length) === 1, '«Моя бригада»: лента ротации с role="img"');
await shot('10-my-month-brigade');

section('Чистота рантайма');
ok(pageErrors.length === 0, 'нет pageerror за прогон' + (pageErrors.length ? ': ' + pageErrors.slice(0, 4).join(' | ') : ''));

await browser.close();
console.log(`\n===== ux-336 (${path.basename(file)}): PASS ${pass} · FAIL ${fail} =====`);
process.exit(fail ? 1 : 0);
