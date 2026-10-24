/* WFM 3.57 · smoke — оперативное табло и сводка дежурств */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.57.html';
const { APP, W, $, errors } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('Табло «Сегодня на дежурстве»');
const es = APP.state.employees.filter(e => e.deptId === 'd4' && e.dutyEligible !== false).slice(0, 4);
const t0 = new Date();
const todayKey = `${t0.getFullYear()}-${String(t0.getMonth() + 1).padStart(2, '0')}-${String(t0.getDate()).padStart(2, '0')}`;
W.applyPatternFan('p2', es, cur.y, cur.m, todayKey, false, 2, { save: true });  /* якорь = сегодня */
W.showTab('dash');
W.renderDutyToday();
const card = $('dutyTodayCard');
ok(card && /Сегодня на дежурстве/.test(card.innerHTML), 'карточка табло на дашборде');
ok(/Сегодня:/.test(card.innerHTML) && /Завтра:/.test(card.innerHTML), 'строки сегодня/завтра');
ok(/Дежурная служба/.test(card.innerHTML), 'подразделение с минимумом в строке покрытия');
ok(/1\/2|2\/2|0\/2|дефицит|−/.test(card.innerHTML) || /ок/.test(card.innerHTML), 'пиллы покрытия/дефицита');
ok(/Бригады сегодня:/.test(card.innerHTML) && /Суточное дежурство 1\/3/.test(card.innerHTML), 'бригада с якорем сегодня дежурит и видна');

section('Печать оперативной сводки (F8)');
W.printDutyRoster(7);
const pa = $('printArea');
ok(/Оперативная сводка дежурств на 7 дн/.test(pa.innerHTML), 'заголовок сводки на 7 дней');
ok(pa.querySelectorAll('tbody tr').length === 7, '7 строк-дней');
ok(/@page\{size:A4 landscape/.test(pa.innerHTML), 'альбомная ориентация');
ok(APP.state.log.some(r => r.action === 'Печать оперативной сводки дежурств'), 'аудит печати');
const nAudit = APP.state.log.filter(r => r.action === 'Печать оперативной сводки дежурств').length;
W.document.dispatchEvent(new W.KeyboardEvent('keydown', { key: 'F8', bubbles: true, cancelable: true }));
ok(APP.state.log.filter(r => r.action === 'Печать оперативной сводки дежурств').length === nAudit + 1, 'F8 вызывает сводку');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.57/.test($('modalBox').textContent) && /Сегодня на дежурстве/.test($('modalBox').textContent), 'справка: блок 3.57');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
