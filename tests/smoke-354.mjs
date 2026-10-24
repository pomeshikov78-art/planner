/* WFM 3.54 · smoke — офлайн-кэш полных публикаций */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.54.html';
const { APP, W, $, errors } = await boot(file);
const { ok, section, report } = mkOk();

section('Флаг отложенной публикации офлайн');
W.pubPendingSet(false);   /* boot сам вызывает save() офлайн — снимаем флаг после бутстрапа */
ok(W.pubPendingGet() === false, 'флаг сброшен после подготовки');
W.save(true);   /* wsOn()===false в jsdom, роль editor → флаг ставится */
ok(W.pubPendingGet() === true, 'save() офлайн ставит pt.pub.pending');
ok($('pubPendingPill') && $('pubPendingPill').style.display !== 'none' && /публикация ждёт сети/.test($('pubPendingPill').textContent), 'пилл «📦 публикация ждёт сети» виден');

section('Воспроизведение при появлении сети');
ok(W.pubPendingFlush() === 0, 'без сети flush не отправляет (0) и сохраняет флаг');
ok(W.pubPendingGet() === true, 'флаг остался после неудачной попытки');
let published = 0;
const realPub = W.wsPublish, realOn = W.wsOn, realAct = W.opsActive;
W.wsOn = () => true; W.opsActive = () => true;
W.wsPublish = () => { published++; };
ok(W.pubPendingFlush() === 1, 'при сети flush отправляет публикацию');
ok(published === 1, 'wsPublish вызван ровно один раз');
ok(W.pubPendingGet() === false && $('pubPendingPill').style.display === 'none', 'флаг и пилл сброшены после отправки');
ok(APP.state.log.some(r => r.action === 'Полная публикация после офлайна'), 'аудит: отложенная публикация');
W.wsPublish = realPub; W.wsOn = realOn; W.opsActive = realAct;

section('Повторный офлайн и палитра');
W.save(true);
ok(W.pubPendingGet() === true, 'новый офлайн-сейв снова ставит флаг');
W.pubPendingSet(false);
ok(W.pubPendingGet() === false && $('pubPendingPill').style.display === 'none', 'pubPendingSet(false) снимает флаг и пилл');
W.showHelp();
ok(/Новое в версии 3\.54/.test($('modalBox').textContent) && /отложенная полная публикация/i.test($('modalBox').textContent), 'справка: блок 3.54');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
