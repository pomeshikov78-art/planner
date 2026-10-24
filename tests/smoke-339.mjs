/* WFM 3.39 · smoke — бюджет и лимиты ФОТ. Запуск: node tests/smoke-339.mjs [файл] */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.39.html';
const { APP, W, $, doc, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;
const MK = `${cur.y}-${String(cur.m).padStart(2, '0')}`;

section('Методика стоимости');
APP.state.departments.push({ id: 'bud', name: 'Бюджет-тест', minDuty: 0, dutyCode: 'Д1' });
const e1 = { id: 'b1', deptId: 'bud', name: 'Бюджетов Б. Б.', pos: 'спец', rate: 1, dutyEligible: true, tab: 'BUD-1', vacationDays: 28, hoursWeek: 40, rubHour: 1000 };
APP.state.employees.push(e1);
APP.state.plan[MK] = APP.state.plan[MK] || {};
APP.state.plan[MK]['b1'] = { 1: 'Я', 2: 'Д1' };
const R = W.ratesCfg();
/* ФОТ месяца: все будни по норме (явки по умолчанию) + явные отметки + ночные надбавки */
const wd = W.monthNorm(cur.y, cur.m).wd;
const expH = (wd - 2) * 8 + 8 + 24;   /* будни без отметок + Я(8) + Д1(24) */
const expCost = Math.round(expH * 1000 + 8 * 1000 * (R.nightPct || 0) / 100);
ok(W.empCost('b1', cur.y, cur.m, 'plan') === expCost, 'empCost: будни по норме + отметки + ночные×надбавка (' + expCost + ' ₽)');
ok(W.rubHour({}) === (APP.state.settings.rubHour || 550), 'rubHour: персональная ставка приоритетнее общей');
ok(W.deptCost('bud', cur.y, cur.m, 'plan') === expCost, 'deptCost: сумма по составу');

section('Лимиты и статусы');
ok(W.budgetLimit(cur.y, cur.m, 'bud') === null, 'лимит по умолчанию не задан');
W.budgetSet(cur.y, cur.m, 'bud', 1000);
let st = W.budgetStatus(cur.y, cur.m, 'bud');
ok(st.limit === 1000 && st.overPlan && st.overFact === false, 'лимит 1000 ₽: план выше лимита, факта нет');
ok(st.pctPlan === Math.round(expCost / 10), 'pctPlan = план/лимит×100');
W.budgetSet(cur.y, cur.m, 'bud', 10 * expCost);
st = W.budgetStatus(cur.y, cur.m, 'bud');
ok(!st.overPlan && !st.overFact && st.pctPlan === 10, 'лимит ×10: «в лимите»');
ok(APP.state.budgets[MK].bud === 10 * expCost, 'канон: state.budgets[месяц][отдел]');
ok(APP.state.log.some(r => r.action === 'Лимит бюджета ФОТ'), 'аудит: «Лимит бюджета ФОТ»');
const sug = W.budgetSuggest(cur.y, cur.m, 'd1');
ok(sug == null || sug > 0, 'budgetSuggest: план прошлого месяца × 1,05 или null');

section('Карточка и сигнал перерасхода');
W.showTab('data');
W.renderBudgets();
ok($('budgetBox') && $('budgetBox').querySelectorAll('[data-bud]').length === APP.state.departments.length, 'карточка: инпут лимита на каждое подразделение');
W.budgetSet(cur.y, cur.m, 'bud', 10);
W.showTab('dash');
W.renderBudgetNag();
ok(!!$('budgetNag') && /Перерасход бюджета ФОТ/.test($('budgetNag').innerHTML), 'дашборд: янтарный сигнал перерасхода');
W.budgetSet(cur.y, cur.m, 'bud', null);
W.renderBudgetNag();
ok(!$('budgetNag'), 'сигнал исчез после снятия лимита');

section('Выгрузка CSV');
W.budgetsCsvDl();
ok(downloads.length > 0 && /budget-fot-/.test(downloads[downloads.length - 1].name), 'CSV бюджета: имя файла');
ok(/Подразделение/.test(downloads[downloads.length - 1].content), 'CSV: шапка таблицы');
ok(APP.state.log.some(r => r.action === 'Выгрузка бюджета ФОТ'), 'аудит: выгрузка бюджета');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.39/.test($('modalBox').textContent) && /лимиты ФОТ/i.test($('modalBox').textContent), 'справка: блок 3.39');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
