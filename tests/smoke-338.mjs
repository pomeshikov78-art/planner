/* WFM 3.38 · smoke — мобильная волна. Запуск: node tests/smoke-338.mjs [файл] */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.38.html';
const { APP, W, $, doc, errors } = await boot(file, { mobile: true });
const { ok, section, report } = mkOk();

section('Мобильный режим включён медиа-условием');
ok(W.mobiOn() === true, 'matchMedia (max-width:900px) → мобильный режим на старте');
ok(doc.body.classList.contains('mobile') && doc.body.classList.contains('auto-compact'), 'body.mobile + auto-compact');
const nav = $('mobiNav');
ok(nav && nav.getAttribute('role') === 'tablist', 'mobi-nav: role=tablist');
ok(nav.querySelectorAll('.mobi-tab').length === 6, 'mobi-nav: 5 разделов + «Ещё»');
ok(nav.querySelectorAll('[role="tab"][aria-selected]').length === 6, 'mobi-nav: роли tab и aria-selected');
ok(nav.querySelector('[data-mt="dash"].act') !== null, 'mobi-nav: активна текущая вкладка (дашборд)');

section('Навигация касаниями');
nav.querySelector('[data-mt="tabel"]').click();
ok($('view-tabel').hidden === false && $('mobiNav').querySelector('[data-mt="tabel"].act') !== null, 'тап по «Табель» переключает раздел и подсветку');
nav.querySelector('[data-mt="more"]').click();
ok($('palOvl') && $('palOvl').hidden === false, '«Ещё» открывает палитру со всеми разделами');
W.closePalette();
W.setMobileMode(false);
ok(!W.mobiOn() && !$('mobiNav') && !doc.body.classList.contains('mobile'), 'выключение: mobi-nav удалён, классы сняты');
W.setMobileMode(true);
ok(!!$('mobiNav'), 'включение: mobi-nav снова в DOM');

section('Свайп месяца');
const m0 = APP.cur.m;
W.swipeMonth(-60);
ok(APP.cur.m === (m0 === 12 ? 1 : m0 + 1), 'свайп влево → следующий месяц');
W.swipeMonth(80);
ok(APP.cur.m === m0, 'свайп вправо → возврат');
/* синтетические touch-события на view-plan */
W.showTab('plan');
const vp = $('view-plan');
const t1 = new W.Event('touchstart'); t1.changedTouches = [{ clientX: 300, clientY: 400 }];
const t2 = new W.Event('touchend'); t2.changedTouches = [{ clientX: 120, clientY: 410 }];
vp.dispatchEvent(t1); vp.dispatchEvent(t2);
ok(APP.cur.m === (m0 === 12 ? 1 : m0 + 1), 'touch-свайп по плану листает месяц (|dx|>60, |dy|<40)');
const m1 = APP.cur.m;
const t3 = new W.Event('touchstart'); t3.changedTouches = [{ clientX: 300, clientY: 400 }];
const t4 = new W.Event('touchend'); t4.changedTouches = [{ clientX: 280, clientY: 500 }];
vp.dispatchEvent(t3); vp.dispatchEvent(t4);
ok(APP.cur.m === m1, 'вертикальный свайп не листает месяц');

section('Установка приложения');
ok(!!$('btnInstall'), 'кнопка «📲 Установить» создана initMobileShell');
W.openInstallHint();
ok($('modal').hidden === false && /Добавить на главный экран/.test($('modalBox').textContent), 'подсказка установки: iOS/Android/offline');
W.closeModal();

section('Справка, палитра, экспорт API');
W.showHelp();
ok(/Новое в версии 3\.38/.test($('modalBox').textContent) && /Свайп месяца/.test($('modalBox').textContent), 'справка: блок 3.38');
W.closeModal();
ok(typeof W.initMobileShell === 'function' && typeof W.renderMobiNav === 'function' && typeof W.swipeMonth === 'function', 'API 3.38 экспортирован');
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));

process.exit(report(file));
