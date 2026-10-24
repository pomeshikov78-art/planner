/* WFM 3.46 · smoke — волна производительности */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.46.html';
const { APP, W, $, errors } = await boot(file);
const { ok, section, report } = mkOk();

section('Метки запуска и отложенная сверка');
const marks0 = { ...APP.PERF.marks };
ok(marks0['boot:start'] === 0 && marks0['state:loaded'] >= 0 && marks0['first:render'] > 0, 'метки boot:start / state:loaded / first:render');
ok(marks0['calendar:verified'] === undefined, 'сверка календаря не в критическом пути запуска');
await new Promise(r => setTimeout(r, 2200));
ok(APP.PERF.marks['calendar:verified'] >= 0, 'сверка календаря завершилась в фоне (метка появилась)');

section('Карточка профилирования');
W.showTab('data');
W.renderPerfCard();
ok($('perfBox') && /Метки запуска/.test($('perfBox').textContent) && /state:loaded/.test($('perfBox').textContent), 'карточка: метки запуска');
ok(/Кэши:/.test($('perfBox').textContent), 'карточка: состояние кэшей');
const tabs = W.perfMeasureTabs();
ok(tabs.length === 15 && tabs.every(t => typeof t.ms === 'number' && t.ms >= 0), 'замер 15 вкладок выполнен');
ok(APP.PERF.spans.some(s => s.name === 'tab:plan'), 'спаны: tab:plan записан');
ok($('perfBox').textContent.includes('tab:'), 'карточка: таблица операций после замера');

section('Нагрузочный профиль 1000');
W.demoScale(1000);
ok($('cfmYes'), 'demoScale: подтверждение');
$('cfmYes').click();
ok(APP.state.employees.length === 1000, 'штат 1000 сотрудников сгенерирован');
const t0 = Date.now();
W.renderPlanTable();
const msRender = Date.now() - t0;
ok(msRender < 8000, 'renderPlanTable на 1000 сотрудников: ' + msRender + ' мс (< 8000)');
const t1 = Date.now();
W.coverageScan(APP.cur.y, APP.cur.m, 'd1', { need: 1, mode: 'duty' });
const msScan = Date.now() - t1;
ok(msScan < 5000, 'coverageScan на 1000 сотрудников: ' + msScan + ' мс (< 5000)');
ok(APP.state.log.some(r => r.action === 'Нагрузочный профиль'), 'аудит: нагрузочный профиль');
ok(APP.PERF.spans.some(s => s.name === 'demoScale:1000'), 'профилировщик: спан demoScale:1000');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.46/.test($('modalBox').textContent) && /Профилирование/.test($('modalBox').textContent), 'справка: блок 3.46');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
