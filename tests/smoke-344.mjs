/* WFM 3.44 · smoke — конструктор приказов */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.44.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();
const cur = APP.cur;

section('Реестр шаблонов и источники строк');
ok(W.orderTpls().length === 3, 'три встроенных шаблона (отпуска/дежурства/произвольный)');
APP.state.vac = APP.state.vac || [];
APP.state.vac.push({ id: 'vr1', eid: APP.state.employees[0].id, year: cur.y, from: `${cur.y}-07-01`, to: `${cur.y}-07-14`, status: 'approved', history: [] });
const rowsVac = W.orderRows('vac', cur.y, cur.m, 'all');
ok(rowsVac.length === 1 && /отпуск с 01\.07/.test(rowsVac[0]), 'источник «отпуска»: строка утверждённой заявки');
APP.state.plan[`${cur.y}-${String(cur.m).padStart(2, '0')}`][APP.state.employees[1].id] = { 5: 'Д1' };
const rowsDuty = W.orderRows('duty', cur.y, cur.m, 'all');
ok(rowsDuty.some(r => /дежурства 5/.test(r)), 'источник «дежурства»: строка со списком дней');

section('Рендер плейсхолдеров и модалка');
const tpl = W.orderTpls()[0];
const rendered = W.orderRender(tpl, { org: 'ОРГ', num: '7/ОД', date: '01.01.2026', period: 'Июль 2026', rows: rowsVac, text: '' });
ok(/ОРГ/.test(rendered) && /7\/ОД/.test(rendered) && !/\{\{/.test(rendered), 'плейсхолдеры подставлены, нераскрытых нет');
W.openOrderConstructor();
ok($('modal').hidden === false && !!$('ocBody') && !!$('ocPrev'), 'модалка конструктора: тело и предпросмотр');
ok(/ПРИКАЗ №/.test($('ocPrev').textContent), 'предпросмотр: шапка приказа');
$('ocNum').value = '42/ОД';
$('ocNum').dispatchEvent(new W.Event('input'));
ok(/42\/ОД/.test($('ocPrev').textContent), 'предпросмотр живой: номер обновился');
$('ocTxt').click();
ok(downloads.some(d => /prikaz-42ОД\.txt|prikaz-.*\.txt/.test(d.name) && /ПРИКАЗ/.test(d.content)), '.txt выгружается с текстом приказа');
$('ocBody').value = $('ocBody').value + '\nДОБАВКА 3.44';
$('ocSave').click();
ok(W.orderTpls()[0].body.includes('ДОБАВКА 3.44'), 'шаблон сохранён в канон (state.orderTpls)');
ok(APP.state.log.some(r => r.action === 'Шаблон приказа сохранён'), 'аудит: сохранение шаблона');
ok(W.orderDocxDl('t', 'текст') === false, 'без JSZip docx вежливо отклоняется (онлайн-сборка без сети)');
W.closeModal();

section('Карточка в отчётах, справка, палитра');
W.showTab('rep');
ok($('orderBox') && /Приказ об утверждении графика отпусков/.test($('orderBox').innerHTML), 'карточка: реестр шаблонов со ссылками «открыть»');
ok(!!$('btnOrderNew'), 'кнопка «📜 Открыть конструктор приказов»');
W.showHelp();
ok(/Новое в версии 3\.44/.test($('modalBox').textContent) && /плейсхолдера/i.test($('modalBox').textContent), 'справка: блок 3.44');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
