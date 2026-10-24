/* WFM 3.58 · smoke — импорт ICS */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.58.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur, Y = cur.y;

section('Парсер RFC 5545');
const folded = 'BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:u1\r\nDTSTART;VALUE=DATE:2026110\r\n 5\r\nDTEND;VALUE=DATE:20261107\r\nSUMMARY:Отпуск\\, служебный\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nUID:u2\r\nDTSTART:20261108T090000Z\r\nSUMMARY:Встреча\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n';
const evs = W.parseIcs(folded);
ok(evs && evs.length === 2, 'два события распознаны');
ok(evs[0].start.k === '2026-11-05' && evs[0].allDay === true, 'unfolding: DTSTART 20261105 (DATE)');
ok(evs[0].end.k === '2026-11-07', 'DTEND разобран');
ok(evs[0].summary === 'Отпуск, служебный', 'экранированная запятая развернута');
ok(evs[1].allDay === false && evs[1].start.k === '2026-11-08', 'DATE-TIME: allDay=false');
ok(W.parseIcs('BEGIN:VEVENT\r\nEND:VEVENT') === null, 'без VCALENDAR — null');

section('Распознавание собственного экспорта 3.37');
APP.state.departments.push({ id: 'ics', name: 'ICS-тест', minDuty: 1, dutyCode: 'Д1' });
const es = Array.from({ length: 4 }, (_, i) => ({ id: 'ic' + (i + 1), deptId: 'ics', name: 'Иксов И-' + (i + 1), pos: '', rate: 1, dutyEligible: true, tab: 'ICS-' + (i + 1), vacationDays: 28, hoursWeek: 0 }));
APP.state.employees.push(...es);
W.applyPatternFan('p2', es, Y, cur.m, `${Y}-01-01`, false, 2, { save: true });
W.exportBrigadeIcs(APP.state.brigades.map(b => b.id), Y, 'ics-roundtrip');
const cap = downloads[downloads.length - 1];
const back = W.parseIcs(cap.content);
ok(back.length > 100, 'round-trip: событий ' + back.length);
ok(back.every(e => e.code === 'Д1'), 'round-trip: код Д1 из SUMMARY');
ok(back.slice(0, 20).every(e => W.icsMatchEmp(e.summary)), 'round-trip: сотрудники сопоставляются по «КОД · ФИО (бригада)»');

section('Применение к плану с защитой');
const target = APP.state.employees.find(e => e.deptId === 'd1');
const d1 = 8, d2 = 9;
APP.state.plan[`${Y}-${String(cur.m).padStart(2, '0')}`][target.id] = { [d2]: 'Б' };
const mkDate = d => `${Y}${String(cur.m).padStart(2, '0')}${String(d).padStart(2, '0')}`;
const custom = 'BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:c1\r\nDTSTART;VALUE=DATE:' + mkDate(d1) + '\r\nDTEND;VALUE=DATE:' + mkDate(d1) + '\r\nSUMMARY:О · ' + target.name + ' (внеш)\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nUID:c2\r\nDTSTART;VALUE=DATE:' + mkDate(d2) + '\r\nDTEND;VALUE=DATE:' + mkDate(d2) + '\r\nSUMMARY:О · ' + target.name + ' (внеш)\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n';
const cev = W.parseIcs(custom);
const res = W.icsApplyToPlan(cev);
ok(res.applied === 1 && res.skipped === 1, 'применено 1 (пустая ячейка), пропущено 1 (больничный)');
ok((APP.state.plan[`${Y}-${String(cur.m).padStart(2, '0')}`][target.id][d1] || '') === 'О', 'ячейка получила код О');
ok(APP.state.log.some(r => r.action === 'Импорт ICS в план'), 'аудит импорта');
W.openIcsImport(custom);
ok($('modal').hidden === false && !!$('icsFile') && /Событий: 2/.test($('icsPrev').textContent), 'модалка импорта: предпросмотр 2 событий');
W.closeModal();
ok(!!$('btnIcsImport'), 'кнопка «📥 Импорт ICS» в тулбаре планирования');
W.showHelp();
ok(/Новое в версии 3\.58/.test($('modalBox').textContent) && /RFC 5545/.test($('modalBox').textContent), 'справка: блок 3.58');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
