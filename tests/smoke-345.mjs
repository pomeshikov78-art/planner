/* WFM 3.45 · smoke — доступность, волна 2 */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.45.html';
const { APP, W, $, doc, errors, html } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('Skip-link, aria-live, role=grid');
ok(!!$('skipLink') && /Пропустить к навигации/.test($('skipLink').textContent), 'skip-link создан и подписан');
ok($('skipLink').className.includes('skip-link'), 'skip-link: класс с оффлоком до фокуса');
ok($('toastBox').getAttribute('aria-live') === 'polite' && $('toastBox').getAttribute('role') === 'status', 'тосты: aria-live=polite + role=status');
W.showTab('plan');
W.a11yPatch();
const pt = $('tblWrap').querySelector('table.pt');
ok(pt && pt.getAttribute('role') === 'grid' && new RegExp(cur.y).test(pt.getAttribute('aria-label')), 'сетка плана: role=grid + aria-имя с месяцем/годом');
W.showTab('duty');
W.a11yPatch();
const dt = $('dutyWrap').querySelector('table');
ok(dt && dt.getAttribute('role') === 'grid', 'сетка дежурств: role=grid');

section('Высокий контраст');
ok(/html\[data-contrast="hc"\]/.test(html), 'CSS высокого контраста в сборке');
W.setUiPref('contrast', true);
W.applyUi();
ok(doc.documentElement.dataset.contrast === 'hc', 'dataset.contrast=hc после включения');
W.showTab('set');
ok($('setContrast') && $('setContrast').checked === true, 'флажок в «Интерфейсе» синхронизирован');
$('setContrast').checked = false;
$('setContrast').dispatchEvent(new W.Event('change'));
ok(doc.documentElement.dataset.contrast !== 'hc', 'выключение снимает режим');
ok(!!W.uiPrefs, 'контраст хранится персонально (uiPrefs), не в каноне');

section('Карта клавиатурных сокращений');
ok(APP.SHORTCUTS.length >= 14, 'реестр SHORTCUTS: ≥ 14 сочетаний (' + APP.SHORTCUTS.length + ')');
W.openShortcuts();
ok($('modal').hidden === false && $('modalBox').querySelectorAll('tbody tr').length === APP.SHORTCUTS.length, 'модалка карты: строк = числу сочетаний');
ok(/Ctrl\+K/.test($('modalBox').textContent) && /F7/.test($('modalBox').textContent), 'карта: ключевые сочетания на месте');
W.closeModal();

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.45/.test($('modalBox').textContent) && /Высокий контраст/.test($('modalBox').textContent), 'справка: блок 3.45');
W.closeModal();
ok(/Карта клавиатурных сокращений/.test(html) && /Высокий контраст: вкл\/выкл/.test(html), 'палитра: команды a11y');
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
