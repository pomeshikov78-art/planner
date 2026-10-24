/* WFM 3.42 · smoke — маркетплейс обменов: открытые заявки и автоподбор */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.42.html';
const { APP, W, $, errors } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur, MK = `${cur.y}-${String(cur.m).padStart(2, '0')}`;

section('Открытая заявка');
const e1 = APP.state.employees.find(e => e.deptId === 'd4' && e.dutyEligible);
const req = W.swapOpenReq({ eid1: e1.id, mk1: MK, day1: 10, reason: 'учёба' });
ok(req && req.eid2 === null && req.open === true && req.status === 'new', 'открытая заявка: без напарника, статус new');
ok(APP.state.log.some(r => r.action === 'Открытая заявка на подмену'), 'аудит: открытая заявка');
W.renderSwaps();
ok($('swapBox').innerHTML.includes('data-swauto="' + req.id), 'список обменов: кнопка «🤖 Автоподбор» у открытой заявки');

section('Автоподбор: кандидаты и оценка');
const c = W.swapCandidates(req, 5);
ok(c.list.length > 0 && c.list.every(x => x.eid !== e1.id), 'кандидаты есть, заявитель исключён');
ok(c.list.every((x, i) => i === 0 || c.list[i - 1].score >= x.score), 'сортировка по оценке');
ok(c.list.every(x => Array.isArray(x.why) && Array.isArray(x.viol) && typeof x.taken === 'number'), 'структура: why/viol/баланс подмен');
const busy = APP.state.employees.filter(e => e.deptId === e1.deptId && W.rotBusyRaw(((APP.state.plan[MK] || {})[e.id] || {})[10])).map(e => e.id);
ok(c.all.every(x => !busy.includes(x.eid)), 'отсутствующие в день смены исключены');
APP.state.dutyWishes = APP.state.dutyWishes || [];
APP.state.dutyWishes.push({ eid: c.all[0].eid, kind: 'no', from: `${MK}-10`, to: `${MK}-10` });
const c2 = W.swapCandidates(req, 50);
ok(!c2.all.some(x => x.eid === c.all[0].eid), '«не ставить» в день смены исключает кандидата');
APP.state.dutyWishes.pop();

section('Оффер напарника и маршрут');
const off = W.swapOffer(req.id, c.list[0].eid);
ok(off && off.eid2 === c.list[0].eid && off.open === false, 'оффер: напарник установлен, заявка закрыта для подбора');
ok(APP.state.log.some(r => r.action === 'Автоподбор напарника'), 'аудит: автоподбор');
ok(req.history.some(h => /автоподбор/.test(h.act)), 'история заявки: шаг автоподбора');
ok(W.coversTaken(c.list[0].eid) === 0, 'ledger подмен: применённых пока нет (заявка не применена к плану)');

section('UI: модалки и кнопка открытой заявки');
W.openSwapOpenReq();
ok($('modal').hidden === false && !!$('soEmp') && !!$('soDay'), 'модалка открытой заявки: сотрудник/дата/причина');
W.closeModal();
const req2 = W.swapOpenReq({ eid1: e1.id, mk1: MK, day1: 12 });
W.openSwapMatch(req2.id);
ok($('modal').hidden === false && doc0().querySelectorAll('[data-swoffer]').length > 0, 'модалка автоподбора: список с кнопками «＋»');
function doc0() { return W.document }
W.closeModal();

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.42/.test($('modalBox').textContent) && /Автоподбор напарника/.test($('modalBox').textContent), 'справка: блок 3.42');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
