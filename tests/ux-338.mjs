/* WFM 3.38 · ux — мобильная волна в Chromium (эмуляция телефона).
   Запуск: HOME=/tmp node tests/ux-338.mjs [файл] */
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const file = process.argv[2] || path.join(here, '..', 'План-табель-WFM-3.38.html');
const shots = path.join(here, '..', 'shots-338');
mkdirSync(shots, { recursive: true });
let pass = 0, fail = 0;
const ok = (c, n) => { if (c) { pass++; console.log('  ok · ' + n); } else { fail++; console.log('FAIL · ' + n); } };

const browser = await chromium.launch({ headless: true });
const pageErrors = [];

/* --- мобильный контекст --- */
const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
const page = await mctx.newPage();
page.on('pageerror', e => pageErrors.push('m: ' + (e.message || e)));
await page.goto('file://' + path.resolve(file), { waitUntil: 'domcontentloaded', timeout: 90000 });
await page.waitForFunction(() => window.APP && window.APP.state && (window.APP.state.employees || []).length > 0, null, { timeout: 60000 });
await page.waitForTimeout(1200);
await page.evaluate(() => { try { closeModal(); } catch (e) {} });

const isVisible = async sel => page.evaluate(async s => {
  const el = document.querySelector(s); if (!el) return false;
  el.scrollIntoView({ block: 'center', behavior: 'instant' });
  await new Promise(r => setTimeout(r, 60));
  const cs = getComputedStyle(el);
  if (cs.display === 'none' || cs.visibility === 'hidden') return false;
  const r = el.getBoundingClientRect();
  return r.width >= 2 && r.height >= 2;
}, sel);

ok(await isVisible('#mobiNav'), 'мобильный вьюпорт: нижняя навигация видна');
const tabs = await page.$$eval('#mobiNav .mobi-tab', els => els.length);
ok(tabs === 6, 'mobi-nav: 5 разделов + «Ещё» (' + tabs + ')');
const h = await page.$eval('#mobiNav .mobi-tab', el => el.getBoundingClientRect().height);
ok(h >= 44, 'цель касания ≥ 44 px (' + Math.round(h) + ')');
await page.tap('#mobiNav [data-mt="me"]');
await page.waitForTimeout(300);
ok(await page.evaluate(() => document.getElementById('view-me').hidden === false), 'тап «Мой месяц» переключает раздел');
ok(await page.$eval('#mobiNav [data-mt="me"]', el => el.classList.contains('act')), 'подсветка активной вкладки');
/* свайп месяца тач-событиями */
const m0 = await page.evaluate(() => APP.cur.m);
await page.evaluate(() => {
  const el = document.getElementById('view-me');
  const mk = (type, x, y) => {
    const t = new Touch({ identifier: 1, target: el, clientX: x, clientY: y });
    return new TouchEvent(type, { touches: type === 'touchend' ? [] : [t], changedTouches: [t], bubbles: true, cancelable: true });
  };
  el.dispatchEvent(mk('touchstart', 320, 500));
  el.dispatchEvent(mk('touchend', 120, 510));
});
await page.waitForTimeout(300);
ok(await page.evaluate(m => APP.cur.m === m, m0 === 12 ? 1 : m0 + 1), 'свайп влево листает месяц');
ok(await isVisible('#btnInstall'), 'кнопка «📲 Установить» видна в мобильном режиме');
await page.screenshot({ path: path.join(shots, '01-mobile.png') }); ok(true, 'скриншот: 01-mobile.png');
await mctx.close();

/* --- десктоп: навигации нет --- */
const dctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const dpage = await dctx.newPage();
dpage.on('pageerror', e => pageErrors.push('d: ' + (e.message || e)));
await dpage.goto('file://' + path.resolve(file), { waitUntil: 'domcontentloaded', timeout: 90000 });
await dpage.waitForFunction(() => window.APP && window.APP.state, null, { timeout: 60000 });
await dpage.waitForTimeout(1000);
await dpage.evaluate(() => { try { closeModal(); } catch (e) {} });
ok(await dpage.evaluate(() => !document.getElementById('mobiNav')), 'десктоп: нижней навигации нет');
ok(await dpage.evaluate(() => !document.body.classList.contains('mobile')), 'десктоп: body без класса mobile');
await dpage.screenshot({ path: path.join(shots, '02-desktop.png') }); ok(true, 'скриншот: 02-desktop.png');
await dctx.close();

ok(pageErrors.length === 0, 'нет pageerror' + (pageErrors.length ? ': ' + pageErrors.slice(0, 3).join(' | ') : ''));
await browser.close();
console.log(`\n===== ux-338 (${path.basename(file)}): PASS ${pass} · FAIL ${fail} =====`);
process.exit(fail ? 1 : 0);
