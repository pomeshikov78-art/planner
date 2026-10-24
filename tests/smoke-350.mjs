/* WFM 3.50 · smoke — OLAP бюджета */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.50.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur, MK = `${cur.y}-${String(cur.m).padStart(2, '0')}`;

section('Данные и рендер среза');
W.budgetSet(cur.y, cur.m, 'd1', 10);   /* заведомо перерасход */
W.budgetSet(cur.y, cur.m, 'd4', 100000000);
W.showTab('an');
W.renderBudgetOlap();
const box = $('bolapBox');
ok(box && box.querySelectorAll('tbody tr').length === APP.state.departments.length, 'строки = числу подразделений');
ok(box.querySelectorAll('tbody tr')[0].querySelectorAll('td').length === 14, '14 колонок: 12 месяцев + имя + год');
ok(box.querySelector('table').getAttribute('role') === 'table' && /OLAP бюджета/.test(box.querySelector('table').getAttribute('aria-label')), 'aria-имя таблицы');
ok(box.querySelectorAll('[data-bolap]').length === APP.state.departments.length * 12, 'drill-ячейки: 12 на подразделение');
ok(box.querySelectorAll('tbody tr')[0].querySelectorAll('td').length === 14, 'строка подразделения: 14 ячеек');

section('Меры и drill-click');
$('bolapMeas').value = 'pct';
$('bolapMeas').dispatchEvent(new W.Event('change'));
ok(/% лимита/.test(box.querySelector('table').getAttribute('aria-label')), 'смена меры отражается в aria-имени');
$('bolapMeas').value = 'dev';
$('bolapMeas').dispatchEvent(new W.Event('change'));
ok(box.querySelectorAll('td[style*="var(--red)"]').length > 0, 'мера «план − лимит»: положительные отклонения красные');
const mBefore = cur.m;
box.querySelector('[data-bolap="3"]').click();
ok(APP.cur.m === 4 && APP.cur.y === cur.y, 'drill-click по апрелю открывает месяц 4');
W.showTab('an');

section('CSV и реестры');
W.budgetOlapCsvDl();
ok(downloads.some(d => /olap-budget-/.test(d.name) && /Факт % лимита/.test(d.content)), 'CSV OLAP бюджета со всеми мерами');
ok(APP.WIDGET_REGISTRY.some(w => w.id === 'bolap'), 'виджет bolap в паспорте виджетов');
ok(APP.reportClass(APP.INTERACTIVE_REPORTS.find(x => x.id === 'bolap')) === 'интерактивный', 'bolap — интерактивный отчёт 5/5');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.50/.test($('modalBox').textContent) && /OLAP бюджета/.test($('modalBox').textContent), 'справка: блок 3.50');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
