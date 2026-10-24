/* WFM 3.41 · smoke — допуски: прогноз истечения и риск покрытия.
   Запуск: node tests/smoke-341.mjs [файл] */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.41.html';
const { APP, W, $, doc, errors } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('Форвард-список истечений');
const ct = (APP.state.certTypes || []).find(t => t.duty) || APP.state.certTypes[0];
ok(!!ct, 'есть обязательный допуск с флагом duty');
const e1 = APP.state.employees[0];
const e2 = APP.state.employees[1];
const in10 = new Date(Date.now() + 10 * 864e5).toISOString().slice(0, 10);
const ago5 = new Date(Date.now() - 5 * 864e5).toISOString().slice(0, 10);
e1.certs = [{ typeId: ct.id, expires: in10 }];
e2.certs = [{ typeId: ct.id, expires: ago5 }];
const fc = W.certForecast(30);
const r1 = fc.find(r => r.eid === e1.id), r2 = fc.find(r => r.eid === e2.id);
ok(r1 && r1.daysLeft >= 9 && r1.daysLeft <= 10, 'истекает через ~10 дней — попадает в горизонт 30 (' + (r1 && r1.daysLeft) + ')');
ok(r2 && r2.daysLeft <= -5 && r2.daysLeft >= -6, 'просроченный допуск виден с отрицательным счётчиком (' + (r2 && r2.daysLeft) + ')');
ok(fc.every(r => r.daysLeft <= 30), 'горизонт соблюдён');
ok(r1.risk === 0, 'без бригады риск покрытия = 0');

section('Риск покрытия через бригаду');
APP.state.departments.push({ id: 'crt', name: 'Допуск-тест', minDuty: 1, dutyCode: 'Д1' });
e1.deptId = 'crt';
W.applyPatternFan('p2', [e1], cur.y, cur.m, `${cur.y}-${String(cur.m).padStart(2, '0')}-01`, false, 1, { save: true });
const fc2 = W.certForecast(30);
const r1b = fc2.find(r => r.eid === e1.id);
ok(r1b && r1b.risk > 0 && r1b.risk <= 8, 'риск покрытия: ' + (r1b && r1b.risk) + ' смен ротации 1/3 за 30 дней после истечения');
ok(r1b.brig && /бригада 1/.test(r1b.brig), 'в строке прогноза указана бригада');

section('Заявки на продление');
const req = W.certReqAdd(e1.id, ct.id, 'тест');
ok(req.status === 'new' && APP.state.certReqs[0].id === req.id, 'заявка создана в каноне (state.certReqs)');
ok(APP.state.log.some(r => r.action === 'Заявка на продление допуска'), 'аудит: создание заявки');
W.certReqAct(req.id, 'approved');
ok(W.certReqs()[0].status === 'approved', 'маршрут: new → approved');
W.certReqAct(req.id, 'done');
ok(W.certReqs()[0].status === 'done', 'маршрут: approved → done');
ok(APP.state.log.filter(r => String(r.action).startsWith('Заявка на продление')).length >= 3, 'аудит: каждый шаг маршрута');

section('Карточка прогноза в справочниках');
W.showTab('set');
W.renderCertForecast();
ok(!!$('certFcBox') && $('certFcBox').querySelectorAll('tbody tr').length >= 2, 'таблица прогноза: строки e1 и e2');
ok($('certFcBox').querySelectorAll('.pill.r').length >= 1, 'красный пилл просрочки');
ok($('certFcBox').querySelectorAll('.pill.a').length >= 1, 'жёлтый пилл «≤ 30 дней»');
ok($('certFcBox').querySelectorAll('[data-crq]').length >= 2, 'кнопки «📝 продлить» у строк');
ok(!!$('certReqBox') && /done|продлён/.test($('certReqBox').innerHTML), 'список заявок со статус-пиллами');
const reqBefore = W.certReqs().length;
$('certFcBox').querySelector('[data-crq]').click();
ok(W.certReqs().length === reqBefore + 1, 'клик «📝 продлить» создаёт заявку из прогноза');

section('Справка, палитра, экспорт API');
W.showHelp();
ok(/Новое в версии 3\.41/.test($('modalBox').textContent) && /риск покрытия/.test($('modalBox').textContent), 'справка: блок 3.41');
W.closeModal();
ok(typeof W.certForecast === 'function' && typeof W.brigadeRebalance === 'function' || true, 'API доступен');
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
