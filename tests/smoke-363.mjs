/* WFM 3.63 · smoke — ICS round-trip (двусторонняя синхронизация) */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.63.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur, Y = cur.y, M = cur.m;
const mk = `${Y}-${String(M).padStart(2, '0')}`;

section('Формат UID собственных экспортов');
const o1 = W.icsOwnUid('bx1-e9-2026-05-07@plantabel');
ok(o1 && o1.kind === 'rot' && o1.brigId === 'bx1' && o1.eid === 'e9' && o1.dk === '2026-05-07', 'rot-UID: бригада / сотрудник / дата');
const o2 = W.icsOwnUid('e9-20260507-2@plantabel');
ok(o2 && o2.kind === 'month' && o2.eid === 'e9' && o2.run === 2, 'month-UID месячного экспорта');
ok(W.icsOwnUid('whatever-123@gmail.com') === null, 'чужой UID → null');

section('Данные: бригада, экспорт, чистый round-trip');
APP.state.departments.push({ id: 'rt63', name: 'RT-63', minDuty: 1, dutyCode: 'Д1' });
const es = Array.from({ length: 4 }, (_, i) => ({ id: 'rt63e' + i, deptId: 'rt63', name: 'Ротаци Р-' + i, pos: '', rate: 1, dutyEligible: true, tab: 'RT63-' + i, vacationDays: 28, hoursWeek: 0 }));
APP.state.employees.push(...es);
W.applyPatternFan('p2', es, Y, M, `${Y}-01-01`, false, 2, { save: true });
const b = APP.state.brigades.find(x => (x.members || []).includes('rt63e0'));
const eid0 = b.members[0];
W.exportBrigadeIcs([b.id], Y, 'rt63-export');
const cap = downloads[downloads.length - 1];
ok(cap && /BEGIN:VCALENDAR/.test(cap.content), 'экспорт бригады в ICS выполнен');
const evs0 = W.parseIcs(cap.content);
const ownM = evs0.filter(e => e.uid.startsWith(b.id + '-' + eid0 + '-') && e.uid.includes('-' + mk + '-'));
ok(ownM.length >= 7, 'в текущем месяце достаточно собственных событий (' + ownM.length + ')');
ok(W.icsRoundTripDiff(evs0).length === 0, 'чистый round-trip: расхождений с планом нет');

section('Дифф: изменение, удаление, добавление');
const evChg = ownM[2], evDel = ownM[4], evProt = ownM[6];
let tampered = cap.content
  .split('BEGIN:VEVENT')
  .map(ch => ch.includes('UID:' + evChg.uid + '\r') ? ch.replace('SUMMARY:Д1', 'SUMMARY:Я') : ch)
  .filter(ch => !ch.includes('UID:' + evDel.uid + '\r'))
  .join('BEGIN:VEVENT');
const x = { id: 'rt63x', deptId: 'rt63', name: 'Внешнев В-1', pos: '', rate: 1, dutyEligible: true, tab: 'RT63-X', vacationDays: 28, hoursWeek: 0 };
APP.state.employees.push(x);
const dext = 2, mkD = d => `${Y}${String(M).padStart(2, '0')}${String(d).padStart(2, '0')}`;
tampered = tampered.replace('END:VCALENDAR',
  'BEGIN:VEVENT\r\nUID:ext-63-1\r\nDTSTART;VALUE=DATE:' + mkD(dext) + '\r\nDTEND;VALUE=DATE:' + mkD(dext) + '\r\nSUMMARY:О · Внешнев В-1 (внеш)\r\nEND:VEVENT\r\nEND:VCALENDAR');
const rows = W.icsRoundTripDiff(W.parseIcs(tampered));
const rChg = rows.find(r => r.act === 'chg'), rDel = rows.find(r => r.act === 'del'), rAdd = rows.find(r => r.act === 'add');
ok(rows.length === 3, 'ровно 3 кандидата (chg + del + add), получено ' + rows.length);
ok(rChg && rChg.eid === eid0 && rChg.dk === evChg.start.k && rChg.from === 'Д1' && rChg.to === 'Я', 'chg: код календаря Д1 → Я, источник «собственный экспорт»');
ok(rDel && rDel.eid === eid0 && rDel.dk === evDel.start.k && rDel.from === 'Д1' && rDel.to === null, 'del: смена ротации убрана в календаре');
ok(rAdd && rAdd.eid === 'rt63x' && rAdd.dk === mk + '-02' && rAdd.to === 'О', 'add: стороннее событие с кодом О');

section('Защита отсутствий');
const tampered2 = tampered.split('BEGIN:VEVENT')
  .map(ch => ch.includes('UID:' + evProt.uid + '\r') ? ch.replace('SUMMARY:Д1', 'SUMMARY:Я') : ch)
  .join('BEGIN:VEVENT');
const pd = +evProt.start.k.split('-')[2];
APP.state.plan[mk] = APP.state.plan[mk] || {};
const rowE = APP.state.plan[mk];
const prevP = (rowE[eid0] || {})[pd];
rowE[eid0] = Object.assign({}, rowE[eid0], { [pd]: 'Б' });
const rows2 = W.icsRoundTripDiff(W.parseIcs(tampered2));
ok(!rows2.some(r => r.eid === eid0 && r.dk === evProt.start.k), 'больничный защищён: кандидат на этот день не создан');
if (prevP === undefined) delete rowE[eid0][pd]; else rowE[eid0][pd] = prevP;

section('UI модалки: дифф и применение выбранного');
W.openIcsImport(tampered);
ok($('modal').hidden === false && !!$('icsRt'), 'модалка импорта: кнопка «🔁 Round-trip: дифф с планом»');
$('icsRt').click();
const rbox = $('icsRtBox');
ok(/Кандидатов: 3/.test(rbox.textContent), 'дифф в модалке: «Кандидатов: 3»');
const cbs = [...rbox.querySelectorAll('[data-rt]')];
ok(cbs.length === 3, 'три строки с чекбоксами');
ok(cbs.filter(cb => !cb.checked).length === 1, 'удаление по умолчанию не отмечено');
ok($('icsRtApply').hidden === false, 'кнопка «✔ Применить выбранное» видна');
$('icsRtApply').click();
await new Promise(r => setTimeout(r, 120));
ok($('modal').hidden === true, 'модалка закрыта после применения');
const cellOf = (eid, d) => (((APP.state.plan[mk] || {})[eid]) || {})[d];
ok(cellOf(eid0, +evChg.start.k.split('-')[2]) === 'Я', 'chg применён: ячейка = Я');
ok(cellOf('rt63x', dext) === 'О', 'add применён: ячейка = О');
ok(cellOf(eid0, +evDel.start.k.split('-')[2]) === 'Д1', 'del не отмечен — ячейка не тронута');
ok(APP.state.log.some(r => r.action === 'ICS round-trip синхронизация'), 'аудит round-trip');

section('Применение математикой и справка');
const res = W.icsApplyRoundTrip([rDel]);
ok(res.applied === 1 && !cellOf(eid0, +evDel.start.k.split('-')[2]), 'icsApplyRoundTrip: удаление очищает ячейку');
W.showHelp();
ok(/Новое в версии 3\.63/.test($('modalBox').textContent) && /round-trip/i.test($('modalBox').textContent), 'справка: блок 3.63');
W.closeModal();
ok(APP.ver === '3.63', 'APP.ver === 3.63');
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
