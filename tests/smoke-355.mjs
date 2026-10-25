/* WFM 3.55 · smoke — роли бригад (клиент) */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.55.html';
const { APP, W, $, errors } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('Роли: данные и уникальность бригадира');
APP.state.departments.push({ id: 'rol', name: 'Роли-тест', minDuty: 1, dutyCode: 'Д1' });
const es = Array.from({ length: 4 }, (_, i) => ({ id: 'rl' + (i + 1), deptId: 'rol', name: 'Ролев Р-' + (i + 1), pos: '', rate: 1, dutyEligible: true, tab: 'RL-' + (i + 1), vacationDays: 28, hoursWeek: 0 }));
APP.state.employees.push(...es);
W.applyPatternFan('p2', es, cur.y, cur.m, `${cur.y}-01-01`, false, 2, { save: true });
const b = APP.state.brigades[0];
const m0 = b.members[0], m1 = b.members[1];
W.brigSetRole(b.id, m0, 'lead');
W.brigSetRole(b.id, m1, 'lead');
ok(W.brigLead(b) === m1 && W.brigRole(b, m0) === 'member', 'бригадир уникален: второй lead снимает первого');
ok(b.ts > 0, 'изменение роли обновляет ts для серверного merge');
ok(W.brigItems()[0].roles && W.brigItems()[0].roles[m1] === 'lead', 'brigItems отдаёт roles на сервер');

section('UI: карточка и модалка ролей');
W.showTab('plan');
W.renderBrigades();
ok(/бригадир: Ролев Р-/.test($('brigBox').innerHTML), 'пилл бригадира в карточке');
ok($('brigBox').querySelectorAll('[data-brigrole]').length === APP.state.brigades.length, 'кнопка «★» у каждой бригады');
W.openBrigRolePicker(b.id);
ok($('modal').hidden === false && $('modalBox').querySelectorAll('input[name="brl"]').length === b.members.length + 1, 'модалка ролей: участники + «без бригадира» (' + (b.members.length + 1) + ')');
ok($('modalBox').querySelector('input[name="brl"][value="' + m1 + '"]').checked === true, 'текущий бригадир отмечен');
$('modalBox').querySelector('input[name="brl"][value=""]').checked = true;
$('brSave').click();
ok(W.brigLead(APP.state.brigades[0]) === null, '«без бригадира» снимает роль');
ok(APP.state.log.some(r => r.action === 'Роль в бригаде'), 'аудит: роли бригады');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.55/.test($('modalBox').textContent) && /бригадир/.test($('modalBox').textContent), 'справка: блок 3.55');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
