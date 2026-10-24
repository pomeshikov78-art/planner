/* WFM 3.56 · smoke — клиентская сверка с серверным сканом */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.56.html';
const { APP, W, $, errors } = await boot(file);
const { ok, section, report } = mkOk();

section('Клиентская обвязка серверного скана');
ok(typeof W.coverageScanServer === 'function', 'coverageScanServer экспортирована');
const err = await W.coverageScanServer(APP.cur.y, APP.cur.m, 'd1', { need: 1 });
ok(err && typeof err.err === 'string', 'без живого сервера: аккуратная ошибка в .err');
W.openCoverageDoctor();
ok(!!$('cdSrv') && !!$('cdSrvLine'), 'доктор: кнопка «⇩ скан сервера» и строка сверки');
$('cdSrv').click();
await new Promise(r => setTimeout(r, 600));
ok(/сервер:/.test($('cdSrvLine').textContent), 'строка сверки показывает ошибку доступа (file:// без сервера)');
W.closeModal();
W.showHelp();
ok(/Новое в версии 3\.56/.test($('modalBox').textContent) && /api\/v1\/coverage/.test($('modalBox').textContent), 'справка: блок 3.56 с endpoint');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
