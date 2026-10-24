/* WFM 3.47 · smoke — паспорта данных и обезличенный экспорт */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.47.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();

section('Реестр линий данных');
ok(APP.DATA_LINEAGE.length >= 13, 'реестр: ≥ 13 линий данных (' + APP.DATA_LINEAGE.length + ')');
ok(APP.DATA_LINEAGE.every(r => r.ds && r.src && r.cons && r.store && r.ret), 'у каждой линии: набор/источник/потребители/хранение/retention');
ok(APP.DATA_LINEAGE.some(r => r.ds === 'plan') && APP.DATA_LINEAGE.some(r => r.ds === 'brigades'), 'линии plan и brigades на месте');
W.openLineage();
ok($('modal').hidden === false && $('modalBox').querySelectorAll('tbody tr').length === APP.DATA_LINEAGE.length, 'модалка паспортов: строк = числу линий');
W.closeModal();

section('Обезличенный экспорт');
const realName = APP.state.employees[0].name;
W.audit('Тест-имя', 'проверка скраба: ' + realName, 'privacy-test');
W.exportAnonJson({});
const cap = downloads[downloads.length - 1];
ok(/canon-obezlichenny-.*\.json/.test(cap.name) && cap.mime === 'application/json', 'имя и mime обезличенного канона');
const c = JSON.parse(cap.content);
ok(c.employees[0].name === 'Сотрудник 0001' && c.employees[0].tab === 'T-9000', 'ФИО → Сотрудник NNNN, табельный → T-9xxx');
ok(c.org === 'Организация (обезличено)' && c.departments[0].name === 'Подразделение 1', 'орг и подразделения обезличены');
ok(c.employees[0].pos && /должность/.test(c.employees[0].pos), 'должности обезличены');
ok(!cap.content.includes(realName), 'реальные имена отсутствуют во всём payload (включая журнал)');
ok(c.log.some(r => /проверка скраба: Сотрудник 0001/.test(r.detail)), 'журнал аудита: имя заменено на псевдоним');
ok(c.__anon && c.__anon.version === '3.47', 'метка __anon с версией');
ok(Object.keys(c.plan).length === Object.keys(APP.state.plan).length, 'структура плана сохранена (ключи месяцев)');
ok(APP.state.log.some(r => r.action === 'Обезличенный экспорт канона'), 'аудит: обезличенный экспорт');
ok(APP.state.employees[0].name === realName, 'рабочий канон не изменён экспортом');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.47/.test($('modalBox').textContent) && /Обезличенный экспорт/.test($('modalBox').textContent), 'справка: блок 3.47');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
