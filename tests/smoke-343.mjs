/* WFM 3.43 · smoke — прогнозы отсутствий с ДИ 95 % */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.43.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('История для прогноза');
/* добавляем 6 месяцев истории с варьирующимися отсутствиями */
const t = new Date();
for (let back = 9; back >= 3; back--) {
  const d = new Date(t.getFullYear(), t.getMonth() - back, 1), y = d.getFullYear(), m = d.getMonth() + 1;
  const mk = `${y}-${String(m).padStart(2, '0')}`;
  APP.state.plan[mk] = APP.state.plan[mk] || {};
  APP.state.employees.slice(0, 10).forEach((e, i) => {
    const n = 2 + ((back + i) % 4);
    APP.state.plan[mk][e.id] = APP.state.plan[mk][e.id] || {};
    for (let dd = 3; dd < 3 + n; dd++) APP.state.plan[mk][e.id][dd] = 'Б';
  });
}
const lr = W.linreg([1, 2, 3]);
ok(Math.abs(lr.b - 1) < 1e-9 && Math.abs(lr.a - 1) < 1e-9, 'linreg([1,2,3]): a=1, b=1');
const f = W.forecastAbsences(null, 3);
ok(f && f.hist.length >= 6, 'история: ≥ 6 месяцев (' + (f && f.hist.length) + ')');
ok(f.out.length === 6, 'прогноз: 2 метрики × 3 месяца = 6 строк');
ok(f.out.every(r => r.lo <= r.pred && r.pred <= r.hi), 'ДИ охватывает прогноз (lo ≤ pred ≤ hi)');
ok(f.out.every(r => r.n === f.hist.length && r.sd >= 0), 'n и SD проставлены');
const abs = f.out.filter(r => r.key === 'abs');
ok(abs.length === 3 && abs.every(r => r.hi > r.pred || r.sd === 0), 'интервал прогноза шире точки при SD > 0');

section('Карточка в аналитике и CSV');
W.showTab('an');
W.renderForecastCard();
ok($('fcBox') && $('fcBox').querySelectorAll('tbody tr').length === 6, 'карточка: 6 строк прогноза');
ok(/ДИ 95 %/.test($('fcBox').textContent) && /Тренд/.test($('fcBox').textContent), 'карточка: колонки ДИ и тренда');
ok(/–/.test($('fcBox').textContent), 'карточка: интервал через тире (fmtStd)');
$('fcDept').value = 'd4';
$('fcDept').dispatchEvent(new W.Event('change'));
ok($('fcBox').querySelectorAll('tbody tr').length === 6, 'фильтр по подразделению пересчитывает');
W.forecastAbsCsvDl();
ok(downloads.some(d => /prognoz-otsutstvij-/.test(d.name)), 'CSV прогноза: имя файла');
ok(APP.state.log.some(r => r.action === 'Выгрузка прогноза отсутствий'), 'аудит: выгрузка прогноза');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.43/.test($('modalBox').textContent) && /1,96/.test($('modalBox').textContent), 'справка: блок 3.43 с методикой ДИ');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
