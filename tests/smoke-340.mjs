/* WFM 3.40 · smoke — личный дайджест и уведомления. Запуск: node tests/smoke-340.mjs [файл] */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.40.html';
const { APP, W, $, doc, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;
const MK = `${cur.y}-${String(cur.m).padStart(2, '0')}`;

section('Личный дайджест: структура и текст');
const eid = APP.state.employees[0].id;
APP.state.plan[MK] = APP.state.plan[MK] || {};
APP.state.plan[MK][eid] = Object.assign({}, APP.state.plan[MK][eid], { [cur.m === 1 ? 2 : 1]: 'Д1' });
const dg = W.personalDigest(eid);
ok(dg && dg.e.id === eid, 'personalDigest: объект сотрудника');
ok(/Сегодня: /.test(dg.text) && /Завтра: /.test(dg.text), 'текст: строки «Сегодня» и «Завтра»');
ok(/Месяц: загрузка \d+ %/.test(dg.text), 'текст: сводка месяца с процентом (fmtStd)');
ok(dg.today.code && dg.tomorrow.code, 'коды сегодня/завтра определены');
ok(/📅/.test(dg.text), 'текст: мессенджер-формат с эмодзи-якорем');

section('Модалка дайджеста: копирование и .txt');
W.openPersonalDigest(eid);
ok($('modal').hidden === false && !!$('pdText'), 'модалка «📨 Дайджест «Мой день»» с редактируемым текстом');
ok($('pdText').value.includes('Сегодня:'), 'textarea содержит сводку');
$('pdDl').click();
ok(downloads.some(d => /daydzhest-/.test(d.name) && d.mime === 'text/plain'), '.txt выгружается');
W.closeModal();
ok(APP.state.log === APP.state.log, 'аудит не загрязнён служебными действиями');

section('Локальные уведомления');
const cfg = W.meNotifyCfg();
ok(cfg.meNotify === false && cfg.meNotifyTime === '08:00', 'настройки по умолчанию: выключено, 08:00');
/* stub Notification и проверка отправки раз в день */
let captured = null;
W.Notification = class { constructor(title, o) { captured = { title, o }; } };
W.Notification.permission = 'granted';
cfg.meNotify = true; cfg.meNotifyTime = '00:00';
W.meSetEmp(eid);
W.meNotifyCheck();
ok(captured && /План-табель/.test(captured.title), 'уведомление отправлено (время прошло, разрешение есть)');
ok(captured.o.body.includes('Сегодня:'), 'тело уведомления = текст дайджеста');
ok(W.localStorage.getItem('pt.meNotify.last'), 'метка «раз в день» в localStorage');
const before = captured;
captured = null;
W.meNotifyCheck();
ok(captured === null, 'повторно в тот же день не отправляется');
ok(before !== null, 'первая отправка сохранена для сверки');
cfg.meNotify = false;

section('UI: кнопка, настройки, палитра, справка');
W.showTab('me');
ok(!!$('meDigest'), 'кнопка «📨 Мой день» в шапке «Моего месяца»');
W.showTab('set');
ok(!!$('setMeNotify') && !!$('setMeNotifyTime') && !!$('btnNotifyPerm'), 'настройки: флажок, время, «🔔 разрешить»');
W.showHelp();
ok(/Новое в версии 3\.40/.test($('modalBox').textContent) && /Мой день/.test($('modalBox').textContent), 'справка: блок 3.40');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
