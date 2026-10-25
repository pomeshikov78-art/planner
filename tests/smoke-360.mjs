/* WFM 3.60 · smoke — снапшот-дифф канона */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.60.html';
const { APP, W, $, errors } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur, MK = `${cur.y}-${String(cur.m).padStart(2, '0')}`;

section('Снапшот и локальные правки');
await W.pubSnapSave();
ok(W.pubSnapLoad() !== null, 'снапшот сохранён');
const eid = APP.state.employees[0].id;
W.window.__ptRoleBypass = 1;
W.setCellRaw(eid, cur.y, cur.m, 3, 'Я');
W.setCellRaw(eid, cur.y, cur.m, 4, 'Б');
APP.state.employees.push({ id: 'diff1', deptId: APP.state.departments[0].id, name: 'Диффов Д. Д.', pos: '', rate: 1, vacationDays: 28, hoursWeek: 40, tab: 'DF-1' });
const d = await W.pubSnapDiffLocal();
ok(d && d.cellsAdd >= 2, 'дифф: добавленных ячеек ≥ 2 (' + (d && d.cellsAdd) + ')');
ok(d.months.some(m => m.mk === MK), 'дифф: месяц правок в списке');
ok(d.dicts.some(x => x.label === 'штатка' && x.b === x.a + 1), 'дифф: справочник «штатка» +1');
ok(d.counterA != null && d.counterB != null, 'counter канона: было → стало');

section('Модалка снапшота с диффами');
W.openPubSnap();
ok(!!$('psDiffLocal') && !!$('psDiffSrv'), 'кнопки «🔍 Дифф с текущим» и «🌐 Дифф с сервером»');
await (async () => { $('psDiffLocal').click(); await new Promise(r => setTimeout(r, 300)); })();
ok(/Снимок ↔ текущий канон/.test($('psDiff').textContent) && /ячеек добавлено/.test($('psDiff').textContent), 'локальный дифф отрисован');
ok($('psDiff').querySelectorAll('tbody tr').length >= 1, 'таблица месяцев с правками');
ok($('psDiff').querySelectorAll('.pill.a').length >= 1, 'пиллы изменённых справочников');
await (async () => { $('psDiffSrv').click(); await new Promise(r => setTimeout(r, 300)); })();
ok(/офлайн|сервер недоступен|нет канона|Снимок ↔ канон сервера/.test($('psDiff').textContent), 'серверный дифф деградирует с подсказкой (jsdom без HTTP-сервера)');
W.closeModal();
ok(APP.state.log.some(r => r.action === 'Снапшот-дифф (локально)'), 'аудит локального диффа');

section('diffStates напрямую');
const dd = W.diffStates({ plan: { '2026-01': { e1: { 1: 'Я' } } }, employees: [1, 2] },
  { plan: { '2026-01': { e1: { 1: 'Я', 2: 'Б' } } }, employees: [1, 2, 3] });
ok(dd.cellsAdd === 1 && dd.cellsChg === 0 && dd.dicts.length === 1, 'diffStates: чистая математика');
W.pubSnapClear();
ok(await W.pubSnapDiffLocal() === null, 'без снапшота дифф = null');
W.showHelp();
ok(/Новое в версии 3\.60/.test($('modalBox').textContent), 'справка: блок 3.60');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
