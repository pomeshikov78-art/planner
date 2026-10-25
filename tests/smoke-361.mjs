/* WFM 3.61 · smoke — бригадир в ведомости, ICS и «Моём месяце» */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.61.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('Бригада с бригадиром');
APP.state.departments.push({ id: 'l61', name: 'Бригадир-тест', minDuty: 1, dutyCode: 'Д1' });
const es = Array.from({ length: 4 }, (_, i) => ({ id: 'l61e' + i, deptId: 'l61', name: 'Бригадиров Б-' + i, pos: '', rate: 1, dutyEligible: true, tab: 'L61-' + i, vacationDays: 28, hoursWeek: 0 }));
APP.state.employees.push(...es);
W.applyPatternFan('p2', es, cur.y, cur.m, `${cur.y}-01-01`, false, 2, { save: true });
const b = APP.state.brigades[0];
W.brigSetRole(b.id, b.members[0], 'lead');

section('Печатная ведомость');
W.showTab('plan');
W.printBrigadeSheet();
ok(/бригадир: Бригадиров Б-/.test($('printArea').innerHTML), 'ведомость: шапка бригады с бригадиром');
ok(/Сформировано|сформировано/.test($('printArea').innerHTML), 'ведомость: штамп');

section('ICS с ролью');
downloads.length = 0;
W.exportBrigadeIcs(APP.state.brigades.map(x => x.id), cur.y, 'l61-ics');
const ics = downloads[downloads.length - 1].content;
const leadEvents = ics.split('BEGIN:VEVENT').filter(ch => ch.includes(b.members[0]));
ok(leadEvents.length > 10 && leadEvents.every(ch => ch.includes('(бригадир)')), 'события бригадира помечены в SUMMARY');
const otherEvents = ics.split('BEGIN:VEVENT').filter(ch => ch.includes(b.members[1]));
ok(otherEvents.length > 10 && otherEvents.every(ch => !ch.includes('(бригадир)')), 'события членов бригады без суффикса');

section('«Мой месяц»: пилл бригадира');
W.meSetEmp(b.members[0]);
W.showTab('me');
ok(/вы — бригадир/.test(($('meBrigCard') || {}).innerHTML || ''), 'пилл «вы — бригадир» у lead');
W.meSetEmp(b.members[1]);
W.showTab('me');
ok(!/вы — бригадир/.test(($('meBrigCard') || {}).innerHTML || ''), 'у обычного участника пилла нет');
W.showHelp();
ok(/Новое в версии 3\.61/.test($('modalBox').textContent), 'справка: блок 3.61');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
