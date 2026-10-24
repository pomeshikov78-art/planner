/* ============================================================================
   WFM 3.37 · ux-337.mjs — Chromium-UX «Сценарии ротаций и годовой баланс»:
   видимость (computed style + геометрия + elementFromPoint), E2E what-if →
   мастер, ребаланс с подтверждением, ICS-скачивания. Скриншоты → shots-337/
   Запуск:  HOME=/tmp node tests/ux-337.mjs [файл.html]
   ============================================================================ */
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const file = process.argv[2] || path.join(here, '..', 'План-табель-WFM-3.37.html');
const shots = path.join(here, '..', 'shots-337');
mkdirSync(shots, { recursive: true });

let pass = 0, fail = 0;
const ok = (cond, name) => {
  if (cond) { pass++; console.log('  ok · ' + name); }
  else { fail++; console.log('FAIL · ' + name); }
};
const section = t => console.log('\n== ' + t + ' ==');

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, acceptDownloads: true });
const page = await ctx.newPage();
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(String(e && e.message || e)));

await page.goto('file://' + path.resolve(file), { waitUntil: 'domcontentloaded', timeout: 90000 });
await page.waitForFunction(() => window.APP && window.APP.state && (window.APP.state.employees || []).length > 0, null, { timeout: 60000 });
ok(true, 'приложение 3.37 загрузилось (file://)');
const closeAnyModal = async () => page.evaluate(() => { try { closeModal(); } catch (e) {} });
await page.waitForTimeout(1200);
await closeAnyModal();
await page.waitForSelector('#modal', { state: 'hidden' });

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

section('Подготовка: бригады на синтетическом отделе');
await page.evaluate(() => {
  APP.state.departments.push({ id: 'uxw', name: 'UX-what-if', minDuty: 2, dutyCode: 'Д1' });
  const es = Array.from({ length: 8 }, (_, i) => ({
    id: 'uw' + (i + 1), deptId: 'uxw', name: 'Вифов В-' + String(i + 1).padStart(2, '0'), pos: 'дежурный',
    rate: 1, dutyEligible: true, tab: 'UXW-' + String(i + 1).padStart(2, '0'), vacationDays: 28, hoursWeek: 0 }));
  APP.state.employees.push(...es);
  applyPatternFan('p2', es, APP.cur.y, APP.cur.m, `${APP.cur.y}-${String(APP.cur.m).padStart(2, '0')}-01`, false, 2, { save: true });
  APP.showTab('plan');
});
await page.waitForTimeout(400);
ok(await isVisible('#btnRotWhatIf'), 'кнопка «🧮 What-if» видна в карточке «Бригады»');
ok(await isVisible('#btnBrigYear'), 'кнопка «⚖ Годовой баланс» видна');
ok(await isVisible('#btnBrigIcs'), 'кнопка «⤓ ICS ротации бригад» видна');

section('What-if: таблица сценариев → принятие в мастер');
await closeAnyModal();
await page.click('#btnRotWhatIf');
await page.waitForSelector('#wiBody tbody tr', { state: 'visible' });
await page.selectOption('#wiDept', 'uxw');
await page.waitForTimeout(450);
ok(await isVisible('#wiBody table'), 'what-if: таблица сценариев видна');
const rowCount = await page.$$eval('#wiBody tbody tr', els => els.length);
ok(rowCount === 4, 'what-if: 4 сценария (B=1..4)');
ok(await page.$$eval('#wiBody .pill.g', els => els.length) > 0, 'what-if: пилл оптимума');
await shot('11-whatif');
const bestB = await page.evaluate(() => {
  const sim = rotWhatIf('p2', 'uxw', { need: 2 });
  return sim.best ? sim.best.B : -1;
});
await page.click(`#wiBody [data-wigo="${bestB}"]`);
await page.waitForSelector('#pwMode', { state: 'visible' });
await page.waitForTimeout(450);   /* пресет ставится через 160 мс после открытия мастера */
ok((await page.inputValue('#pwBrig')) === String(bestB), '«принять»: мастер открыт с бригадами = ' + bestB);
ok((await page.inputValue('#pwDept')) === 'uxw', '«принять»: мастер открыт с подразделением what-if');
await closeAnyModal();
await page.waitForSelector('#modal', { state: 'hidden' });

section('Годовой баланс: конфликты с пожеланиями и ребаланс');
await page.evaluate(() => {
  const b = APP.state.brigades[0];
  APP.state.dutyWishes = APP.state.dutyWishes || [];
  APP.state.dutyWishes.push({ eid: b.members[0], kind: 'no', from: APP.cur.y + '-05-02', to: APP.cur.y + '-05-06' });
});
await closeAnyModal();
await page.click('#btnBrigYear');
await page.waitForSelector('#byBody tbody tr', { state: 'visible' });
ok(await isVisible('#byBody table'), 'баланс: таблица бригад за год видна');
const blocksBefore = await page.evaluate(() => brigadeYearSim(APP.cur.y).blocks);
ok(blocksBefore >= 1, 'баланс: конфликты с «не ставить» видны (' + blocksBefore + ')');
ok(await page.$$eval('#byBody .pill.r', els => els.length) > 0, 'баланс: красный пилл конфликтов');
await shot('12-brig-year');
await page.click('#byGo');
await page.waitForSelector('#cfmYes', { state: 'visible' });
const cfmText = await page.textContent('#modalBox');
ok(/Конфликты с «не ставить»/.test(cfmText) && /→/.test(cfmText), 'ребаланс: подтверждение со сравнением «до → после»');
await page.click('#cfmYes');
await page.waitForSelector('#byBody tbody tr', { state: 'visible' });
const blocksAfter = await page.evaluate(() => brigadeYearSim(APP.cur.y).blocks);
ok(blocksAfter < blocksBefore, 'ребаланс применён: конфликты ' + blocksBefore + ' → ' + blocksAfter);
await closeAnyModal();
await page.waitForSelector('#modal', { state: 'hidden' });

section('ICS-скачивания');
const year = await page.evaluate(() => APP.cur.y);
{
  const [download] = await Promise.all([page.waitForEvent('download'), page.click('#btnBrigIcs')]);
  ok(download.suggestedFilename() === 'brigady-rotacii-' + year + '.ics', 'ICS бригад: имя файла ' + download.suggestedFilename());
}
{
  await page.evaluate(() => { meSetEmp(APP.state.brigades[0].members[0]); APP.showTab('me'); });
  await page.waitForSelector('#meBrigIcs', { state: 'visible', timeout: 8000 });
  ok(await isVisible('#meBrigIcs'), '«Моя бригада»: кнопка «⤓ ICS моей ротации» видна');
  const [download] = await Promise.all([page.waitForEvent('download'), page.click('#meBrigIcs')]);
  ok(/^rotaciya-.*\.ics$/.test(download.suggestedFilename()), 'личный ICS: имя ' + download.suggestedFilename());
}

section('Палитра и справка');
await page.keyboard.press('Control+k');
await page.waitForSelector('#palInp', { state: 'visible' });
await page.fill('#palInp', 'what-if');
await page.waitForTimeout(250);
ok(/What-if ротации/.test(await page.textContent('#palList')), 'палитра: «What-if ротации»');
await page.fill('#palInp', 'годовой баланс');
await page.waitForTimeout(250);
ok(/Годовой баланс бригад/.test(await page.textContent('#palList')), 'палитра: «Годовой баланс бригад»');
await page.fill('#palInp', 'ICS моей');
await page.waitForTimeout(250);
ok(/ICS моей ротации/.test(await page.textContent('#palList')), 'палитра: «ICS моей ротации»');
await page.keyboard.press('Escape');
await page.evaluate(() => showHelp());
await page.waitForSelector('#modalBox', { state: 'visible' });
ok(/Новое в версии 3\.37/.test(await page.textContent('#modalBox')), 'справка: блок 3.37');
await closeAnyModal();

section('Чистота рантайма');
ok(pageErrors.length === 0, 'нет pageerror за прогон' + (pageErrors.length ? ': ' + pageErrors.slice(0, 4).join(' | ') : ''));

await browser.close();
console.log(`\n===== ux-337 (${path.basename(file)}): PASS ${pass} · FAIL ${fail} =====`);
process.exit(fail ? 1 : 0);
