/* WFM 3.52 · smoke — OLAP бригад и покрытия */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.52.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur, Y = cur.y;

section('Данные и рендер среза');
APP.state.departments.push({ id: 'bol', name: 'OLAP-тест', minDuty: 1, dutyCode: 'Д1' });
const es = Array.from({ length: 4 }, (_, i) => ({ id: 'ol' + (i + 1), deptId: 'bol', name: 'Олапов О-' + (i + 1), pos: 'дежурный', rate: 1, dutyEligible: true, tab: 'OL-' + (i + 1), vacationDays: 28, hoursWeek: 0 }));
APP.state.employees.push(...es);
W.applyPatternFan('p2', es, cur.y, cur.m, `${Y}-${String(cur.m).padStart(2, '0')}-01`, false, 2, { save: true });
/* конфликт: пожелание «не ставить» в день дежурства фазы 0 */
APP.state.dutyWishes = APP.state.dutyWishes || [];
APP.state.dutyWishes.push({ eid: APP.state.brigades[0].members[0], kind: 'no', from: `${Y}-05-02`, to: `${Y}-05-06` });
W.showTab('an');
W.renderBrigOlap();
const box = $('brigolapBox');
ok(box && box.querySelectorAll('tbody tr').length === 2, 'строки = числу бригад (2)');
ok(box.querySelectorAll('tbody tr')[0].querySelectorAll('td').length === 14, '14 колонок: 12 месяцев + бригада + год');
ok(box.querySelector('table').getAttribute('role') === 'table' && /OLAP бригад/.test(box.querySelector('table').getAttribute('aria-label')), 'aria-имя таблицы');
const ol = W.brigOlap(Y);
const mayCell = ol.rows[0].cells[4];
ok(mayCell.conflicts >= 1 || ol.rows[1].cells[4].conflicts >= 1, 'конфликты с «не ставить» в мае посчитаны');
ok(ol.rows.every(r => r.T.duty > 0 && r.T.daysOn > 0), 'чел·дн и дни выхода > 0 у обеих бригад');
ok(Math.abs(ol.rows[0].T.hours - ol.rows[0].T.duty * 24) < 1e-6, 'часы = чел·дн × 24 (суточное дежурство)');

section('Меры, drill, CSV, реестры');
$('brigolapMeas').value = 'conflicts';
$('brigolapMeas').dispatchEvent(new W.Event('change'));
ok(box.querySelector('td[style*="var(--red)"]') !== null, 'мера «конфликты»: красная подсветка');
ok(/Конфликты с «не ставить»/.test(box.querySelector('table').getAttribute('aria-label')), 'aria отражает выбранную меру');
box.querySelector('[data-brigolap]').click();
ok($('modal').hidden === false && /годовой баланс/i.test($('modalBox').textContent), 'drill-click открывает годовой баланс бригады');
W.closeModal();
W.brigOlapCsvDl();
ok(downloads.some(d => /olap-brigad-/.test(d.name) && /Чел·дн дежурств/.test(d.content)), 'CSV OLAP бригад');
ok(APP.WIDGET_REGISTRY.some(w => w.id === 'brigolap') && APP.reportClass(APP.INTERACTIVE_REPORTS.find(x => x.id === 'brigolap')) === 'интерактивный', 'НСИ: виджет и отчёт 5/5');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.52/.test($('modalBox').textContent) && /бригада × месяц/.test($('modalBox').textContent), 'справка: блок 3.52');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
