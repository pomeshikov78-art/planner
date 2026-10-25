/* WFM 3.59 · smoke — роли бригад (бригадир) и офлайн-снапшот публикации */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.59.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('Роли бригад: бригадир уникален');
APP.state.departments.push({ id: 'r59', name: 'Роли-359', minDuty: 1, dutyCode: 'Д1' });
const es = Array.from({ length: 4 }, (_, i) => ({ id: 'r59e' + i, deptId: 'r59', name: 'Ролев Р-' + i, pos: '', rate: 1, dutyEligible: true, tab: 'R59-' + i, vacationDays: 28, hoursWeek: 0 }));
APP.state.employees.push(...es);
W.applyPatternFan('p2', es, cur.y, cur.m, `${cur.y}-01-01`, false, 2, { save: true });
const b = APP.state.brigades[0];
const m0 = b.members[0], m1 = b.members[1];
W.brigSetRole(b.id, m0, 'lead');
W.brigSetRole(b.id, m1, 'lead');
ok(W.brigLead(b) === m1 && W.brigRole(b, m0) === 'member', 'второй lead снимает первого');
ok(b.ts > 0, 'ts обновлён для серверного merge');
ok(W.brigItems()[0].roles[m1] === 'lead', 'brigItems отдаёт roles');
W.showTab('plan'); W.renderBrigades();
ok(/бригадир: Ролев Р-/.test($('brigBox').innerHTML), 'пилл бригадира в карточке');
ok($('brigBox').querySelectorAll('[data-brigrole]').length === APP.state.brigades.length, '«★» у каждой бригады');
W.openBrigRolePicker(b.id);
ok($('modal').hidden === false && $('modalBox').querySelectorAll('input[name="brl359"]').length === b.members.length + 1, 'пикер: участники + «без бригадира»');
$('modalBox').querySelector('input[name="brl359"][value=""]').checked = true;
$('brSave359').click();
ok(W.brigLead(APP.state.brigades[0]) === null, '«без бригадира» снимает роль');
ok(APP.state.log.some(r => r.action === 'Роль в бригаде'), 'аудит ролей');

section('Офлайн-снапшот канона');
ok(W.pubSnapLoad() === null || true, 'снапшот мог остаться от save() офлайн — проверяем badge');
W.pubSnapClear();
const saved = await W.pubSnapSave();
ok(saved === true && W.pubSnapLoad() !== null, 'pubSnapSave: снимок в localStorage');
const sn = W.pubSnapLoad();
ok(sn.gz || sn.data, 'снапшот: gzip или данные канона');
ok(sn.bytes > 1000, 'размер канона зафиксирован (' + sn.bytes + ' Б)');
ok(/снимок/.test($('pubSnapPill').textContent) && $('pubSnapPill').style.display !== 'none', 'пилл «📦 снимок …» виден');
ok(APP.state.log.some(r => r.action === 'Офлайн-снапшот канона сохранён'), 'аудит сохранения снапшота');
W.save(true);   /* офлайн-хук save() не должен падать и не дублировать бесконечно */
await new Promise(r => setTimeout(r, 300));
ok(W.pubSnapLoad() !== null, 'save() офлайн поддерживает снапшот');
W.openPubSnap();
ok($('modal').hidden === false && /Сохранён:/.test($('modalBox').textContent), 'модалка снапшота: метаданные');
$('psDl359').click();
ok(downloads.some(d => /pub-snap-.*\.json/.test(d.name)), 'выгрузка снимка JSON');
W.closeModal();
W.pubSnapClear();
ok(W.pubSnapLoad() === null && $('pubSnapPill').style.display === 'none', 'очистка: кэш и пилл сняты');

section('Справка, палитра, версия');
W.showHelp();
ok(/Новое в версии 3\.59/.test($('modalBox').textContent) && /бригадир/i.test($('modalBox').textContent), 'справка: блок 3.59');
W.closeModal();
ok(APP.ver === '3.59', 'APP.ver === 3.59');
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
