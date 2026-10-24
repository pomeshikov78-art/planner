/* WFM 3.51 · smoke — мобильный офлайн-кэш операций */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.51.html';
const { APP, W, $, errors } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('Кэш: добавление и индикатор');
ok(W.opsCacheLoad().length === 0, 'кэш пуст на старте');
W.opsCacheAdd({ k: 'plan', eid: 'e1', y: cur.y, m: cur.m, d: 1, code: 'Я' });
ok(W.opsCacheLoad().length === 1, 'opsCacheAdd пишет в localStorage');
ok($('opsCachePill') && /очередь: 1/.test($('opsCachePill').textContent), 'пилл «📴 очередь: 1 оп» в шапке');
W.opsQueue({ k: 'plan', eid: 'e1', y: cur.y, m: cur.m, d: 2, code: 'Я' });   /* ws выключен → в кэш */
ok(W.opsCacheLoad().length === 2, 'opsQueue офлайн зеркалит операцию в кэш');
ok(/очередь: 2/.test($('opsCachePill').textContent), 'пилл обновился до 2');

section('Воспроизведение очереди');
const realActive = W.opsActive;
W.opsActive = () => true;   /* имитируем реконнект */
const qBefore = W.eval('OPS.q.length');
const n = W.opsCacheReplay();
ok(n === 2, 'replay: 2 операции воспроизведены через opsQueue');
ok(W.opsCacheLoad().length === 0, 'кэш очищен при воспроизведении');
ok(W.eval('OPS.q.length') === qBefore + 2, 'операции встали в очередь протокола (дедупликация по разным ячейкам)');
ok(APP.state.log.some(r => r.action === 'Воспроизведение офлайн-очереди'), 'аудит: воспроизведение');
W.opsActive = realActive;

section('Зеркало при сбое отправки и очистка');
W.eval('OPS.q.push({k:"plan",eid:"e9",y:2030,m:1,d:1,code:"Я"})');
W.opsFlush();   /* wsOn() === false → зеркало в кэш */
ok(W.opsCacheLoad().length === W.eval('OPS.q.length') && W.opsCacheLoad().length >= 1, 'opsFlush офлайн: очередь зеркалирована в кэш');
W.opsCacheClear();
ok(W.opsCacheLoad().length === 0 && $('opsCachePill').style.display === 'none', 'очистка: кэш пуст, пилл скрыт');
W.eval('OPS.q.length=0');

section('Справка, палитра, экспорт API');
W.showHelp();
ok(/Новое в версии 3\.51/.test($('modalBox').textContent) && /офлайн-кэш/i.test($('modalBox').textContent), 'справка: блок 3.51');
W.closeModal();
ok(typeof W.opsCacheReplay === 'function' && typeof W.opsCacheBadge === 'function', 'API 3.51 экспортирован');
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
