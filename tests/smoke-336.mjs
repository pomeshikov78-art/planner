/* ============================================================================
   WFM 3.36 · smoke-336.mjs — jsdom-смоук «Конструктор ротаций, бригады и
   доктор покрытия» (по конвенции тестов 3.19+: поведение и видимость,
   а не флаги). Запуск:  node tests/smoke-336.mjs [файл.html]
   ============================================================================ */
import { readFileSync } from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const file = process.argv[2] || new URL('../План-табель-WFM-3.36.html', import.meta.url).pathname;
let pass = 0, fail = 0;
const ok = (cond, name) => {
  if (cond) { pass++; console.log('  ok · ' + name); }
  else { fail++; console.log('  FAIL · ' + name); }
};
const section = t => console.log('\n== ' + t + ' ==');

const html = readFileSync(file, 'utf8');
const runtimeErrors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => {
  const msg = String(e && e.message || e);
  if (/Not implemented|Could not parse CSS|getContext/i.test(msg)) return; // штатный шум jsdom
  runtimeErrors.push(msg);
});

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  url: 'http://127.0.0.1/',
  virtualConsole: vc,
});
const { window } = dom;
window.matchMedia = window.matchMedia || (q => ({ matches: false, media: q, onchange: null,
  addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent() { return false } }));
window.ResizeObserver = window.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };
window.IntersectionObserver = window.IntersectionObserver || class { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } };
window.WebSocket = window.WebSocket || class { constructor() { this.readyState = 0 } send() {} close() { this.readyState = 3 } addEventListener() {} removeEventListener() {} };
window.BroadcastChannel = window.BroadcastChannel || class { constructor() {} postMessage() {} close() {} addEventListener() {} };
window.addEventListener('error', e => runtimeErrors.push('window.onerror: ' + (e.message || e.error)));
if (!window.crypto || !window.crypto.subtle) {
  const { webcrypto } = await import('node:crypto');
  try { Object.defineProperty(window, 'crypto', { value: webcrypto, configurable: true }); } catch (e) {}
}

/* ждём boot(): APP.state готов */
const APP = await (async () => {
  const t0 = Date.now();
  while (Date.now() - t0 < 30000) {
    if (window.APP && window.APP.state && window.APP.state.employees && window.APP.state.employees.length) return window.APP;
    await new Promise(r => setTimeout(r, 100));
  }
  throw new Error('APP не инициализирован за 30 с: ' + runtimeErrors.join(' | '));
})();
const $ = id => window.document.getElementById(id);
const W = window; // все top-level функции приложения доступны как свойства window
const doc = window.document;
const cur = APP.cur;
const MK = `${cur.y}-${String(cur.m).padStart(2, '0')}`;
const anchor = `${MK}-01`;

section('Версия и бутстрап');
ok(APP.ver === '3.36', 'APP.ver === 3.36');
ok(doc.title.includes('3.36'), '<title> содержит 3.36');
ok(APP.state.departments.length === 4 && APP.state.employees.length === 50, 'сид: 4 подразделения, 50 сотрудников');
ok(runtimeErrors.length === 0, 'нет рантайм-ошибок при загрузке' + (runtimeErrors.length ? ': ' + runtimeErrors.slice(0, 3).join(' | ') : ''));

section('Примитивы шаблонов (patternSeq / patternHours / patternIsWork / rotBusyRaw)');
ok(JSON.stringify(W.patternSeq({ seq: ' Д1, в ,В,д3 ' })) === '["Д1","В","В","Д3"]', 'patternSeq: trim/upper/фильтр');
ok(W.patternHours('Д1') === 24 && W.patternHours('Д2') === 12 && W.patternHours('В') === 0, 'patternHours: Д1=24, Д2=12, В=0');
ok(W.patternIsWork('Я') === true && W.patternIsWork('Д1') === true && W.patternIsWork('В') === false && W.patternIsWork('ОГ') === false, 'patternIsWork: Я/Д1 — работа, В/ОГ — отдых');
ok(W.rotBusyRaw('О') === true && W.rotBusyRaw('Б') === true && W.rotBusyRaw('К') === true && W.rotBusyRaw('Я') === false && W.rotBusyRaw(null) === false, 'rotBusyRaw: отсутствия неприкосновенны, работа — нет');

section('Паспорт шаблона (комплаенс ТК РФ)');
const pp13 = W.patternPassport({ name: '1/3', seq: 'Д1,В,В,В' });
ok(pp13 && pp13.N === 4 && pp13.work === 1 && pp13.offs === 3, 'паспорт 1/3: цикл 4, 1 рабочий, 3 выходных');
ok(Math.abs(pp13.hoursWeek - 42) < 1e-9, 'паспорт 1/3: средняя неделя 42 ч (24/4×7)');
ok(pp13.peoplePerPost === 4, 'паспорт 1/3: 4 человека на круглосуточный пост');
ok(pp13.maxConsec === 1 && pp13.maxRestRun === 3 && pp13.restHours === 72, 'паспорт 1/3: серии и отдых (72 ч ≥ 42)');
ok(pp13.verdict === 'ok', 'паспорт 1/3: вердикт «соответствует нормам»');
const ppBad = W.patternPassport({ name: 'плохой', seq: 'Д1,Д2,В' });
ok(ppBad && ppBad.verdict === 'bad', 'паспорт «Д1,Д2,В»: вердикт «не соответствует» (нет отдыха после суточных)');
ok(ppBad.issues.some(i => i.sev === 'crit' && /отдых/i.test(i.text)), 'паспорт: критическое замечание про отдых после дежурства');
const ppOver = W.patternPassport({ name: 'перебор', seq: 'Д2,Д2,Д2,Д2,Д2,Д2,Д2' });
ok(ppOver && ppOver.issues.some(i => i.sev === 'crit' && /неделю/i.test(i.text)), 'паспорт 7×12 ч: неделя 84 ч — крит выше лимита 48');
const pp5 = W.patternPassport(APP.state.patterns.find(p => p.id === 'p5'));
ok(pp5 && pp5.pyatidnevka === true && pp5.verdict !== 'bad', 'паспорт «пятидневка Я×5»: особый режим, вердикт не «не соответствует»');
const ppWrap = W.patternPassport({ name: 'закольцовка', seq: 'Д2,В,В,Д2,Д2' });
ok(ppWrap && ppWrap.maxConsec === 3, 'паспорт: серия с закольцовкой цикла (2 в конце + 1 в начале = 3)');
ok(W.patternPassport({ name: 'пустой', seq: '' }) === null, 'паспорт пустого шаблона → null');

section('Вердикт-пиллы и ленты');
ok(/соответствует нормам/.test(W.passportVerdictPill(pp13)) && /не соответствует/.test(W.passportVerdictPill(ppBad)), 'passportVerdictPill: ok/bad');
ok(/rot-chip/.test(W.rotStripHtml(['Д1', 'В', 'В'])) && /Д1/.test(W.rotStripHtml(['Д1'])), 'rotStripHtml: чипы цикла');
ok(typeof W.rotChipHtml('НЕТУТАКОГОКОДА') === 'string', 'rotChipHtml не падает на неизвестном коде');

section('Веер по бригадам (fanOffsets / brigadesRecommend)');
ok(JSON.stringify(W.fanOffsets(4, 2)) === '[0,2]', 'fanOffsets(4,2) = [0,2]');
ok(JSON.stringify(W.fanOffsets(4, 4)) === '[0,1,2,3]', 'fanOffsets(4,4) = [0,1,2,3]');
ok(JSON.stringify(W.fanOffsets(6, 4)) === '[0,1,3,4]', 'fanOffsets(6,4) = [0,1,3,4]');
ok(W.fanOffsets(4, 6).length === 6, 'fanOffsets: бригад больше цикла — 6 смещений (с повторами)');
const recD4 = W.brigadesRecommend(APP.state.patterns.find(p => p.id === 'p2'), 'd4');
ok(recD4 === 8, 'brigadesRecommend: 1/3 при минимуме 2/сутки → 8 бригад');
ok(W.brigadesRecommend(APP.state.patterns.find(p => p.id === 'p2'), 'd1') === 4, 'brigadesRecommend: минимум 1 → 4 бригады');
const sGroups = W.splitBrigades([{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }, { id: 5 }], 2);
ok(sGroups.length === 2 && sGroups[0].length === 3 && sGroups[1].length === 2, 'splitBrigades: round-robin 3+2');

section('Конструктор ротаций (buildSeqFromParams)');
ok(JSON.stringify(W.buildSeqFromParams({ wCode: 'Д2', work: 2, rest: 2, rCode: 'В' })) === '["Д2","Д2","В","В"]', '2/2 день');
ok(JSON.stringify(W.buildSeqFromParams({ wCode: 'Д2', wCode2: 'Д3', alt: true, work: 4, rest: 2, rCode: 'ОГ' })) === '["Д2","Д3","Д2","Д3","ОГ","ОГ"]', 'чередование день/ночь 4+2');
ok(W.pcAutoName({ wCode: 'Д2', wCode2: 'Д3', alt: true, work: 4, rest: 2 }) === 'Д2/Д3 · 4/2', 'pcAutoName');

section('Применение веера: чистый отдел, детерминированное покрытие');
/* синтетический отдел без отсутствий: 8 человек, шаблон 1/3, 4 бригады → ровно 2 дежурных в сутки */
APP.state.departments.push({ id: 'dtest', name: 'Тест-ротация', minDuty: 2, dutyCode: 'Д1' });
const es8 = Array.from({ length: 8 }, (_, i) => ({
  id: 't' + (i + 1), deptId: 'dtest', name: 'Тестовый Т-' + pad(i + 1), pos: 'дежурный',
  rate: 1, dutyEligible: true, tab: 'TST-' + pad(i + 1), vacationDays: 28, hoursWeek: 0 }));
function pad(n) { return String(n).padStart(2, '0') }
APP.state.employees.push(...es8);
const resFan = W.applyPatternFan('p2', es8, cur.y, cur.m, anchor, false, 4, { save: true });
const DIM = new Date(cur.y, cur.m, 0).getDate();
ok(resFan && resFan.n === 2 * DIM, 'applyPatternFan: проставлено ' + (resFan && resFan.n) + ' отметок (ровно 2 дежурных × ' + DIM + ' дн.)');
ok(resFan.groups.length === 4 && resFan.groups.every((g, i) => g.offset === i) && resFan.groups.every(g => g.members.length === 2), 'applyPatternFan: 4 бригады по 2 человека, смещения 0..3');
ok(Array.isArray(APP.state.brigades) && APP.state.brigades.length === 4, 'state.brigades: 4 сохранённые бригады (канон)');
ok(APP.state.brigades.every(b => b.patId === 'p2' && b.anchor === anchor && Array.isArray(b.members)), 'бригады: patId/anchor/members');
const scanT = W.coverageScan(cur.y, cur.m, 'dtest', { need: 2, mode: 'duty', code: 'Д1' });
ok(scanT.days.every(x => x.plan === 2), 'веер 4×2 чел.: каждый день ровно 2 дежурных (без дыр и излишков)');
ok(scanT.defDays.length === 0 && scanT.overDays.length === 0, 'скан: дефицита и избытка нет');

section('Карточка «Бригады» (renderBrigades)');
W.showTab('plan');
W.renderBrigades();
const brigBox = $('brigBox');
ok(brigBox && /бригада 1/i.test(brigBox.innerHTML), 'brigBox: бригада 1 видна');
ok($('brigCount') && $('brigCount').textContent === '4', 'brigCount = 4');
ok($('btnBrigApplyAll') && $('btnBrigApplyAll').hidden === false, 'кнопка «Применить все бригады» видна');
ok(brigBox.querySelectorAll('[data-briggo]').length === 4 && brigBox.querySelectorAll('[data-brigdel]').length === 4, 'у каждой бригады кнопки «▶ На месяц» и «✕»');

section('Повторное применение бригады к другому месяцу (сквозная фаза)');
const brig1 = APP.state.brigades[0];
const nm = cur.m === 12 ? 1 : cur.m + 1, ny = cur.m === 12 ? cur.y + 1 : cur.y;
const nApply = W.applyBrigadeToMonth(brig1.id, ny, nm);
ok(nApply === Math.ceil(new Date(ny, nm, 0).getDate() / 4) * brig1.members.length, 'applyBrigadeToMonth: ' + nApply + ' отметок в следующем месяце');
const mkNext = `${ny}-${pad(nm)}`;
const DIMn = new Date(ny, nm, 0).getDate();
let full = 0;
for (let d = 1; d <= DIMn; d++) {
  const cnt = brig1.members.filter(id => ((APP.state.plan[mkNext] || {})[id] || {})[d] === 'Д1').length;
  if (cnt === brig1.members.length) full++;
}
ok(full === Math.ceil(DIMn / 4), 'сквозная фаза: оба члена бригады дежурят каждый 4-й день (' + full + ' = ⌈' + DIMn + '/4⌉)');

section('Веер на реальных данных: отсутствия сохраняются');
const esD2 = APP.state.employees.filter(e => e.deptId === 'd2' && !e.fired);
const busyBefore = {};
esD2.forEach(e => {
  const row = (APP.state.plan[MK] || {})[e.id] || {};
  Object.keys(row).forEach(d => { if (W.rotBusyRaw(row[d])) busyBefore[e.id + '|' + d] = row[d]; });
});
const resD2 = W.applyPatternFan('p2', esD2, cur.y, cur.m, anchor, false, 4, { save: false });
ok(resD2 && resD2.n > 0, 'applyPatternFan на отделе с данными: ' + (resD2 && resD2.n) + ' отметок');
let kept = 0, total = Object.keys(busyBefore).length;
Object.keys(busyBefore).forEach(kk => {
  const [eid, d] = kk.split('|');
  if (((APP.state.plan[MK] || {})[eid] || {})[d] === busyBefore[kk]) kept++;
});
ok(total > 0 && kept === total, 'все ' + total + ' ячеек с отсутствиями (О/Б/К/У/ДО/НН/ПР) сохранены без изменений');
ok(APP.state.brigades.length === 4, 'save:false — бригады не дублируются');

section('Доктор покрытия: скан, кандидаты, применение, undo');
const scanD4 = W.coverageScan(cur.y, cur.m, 'd4', { need: 6, mode: 'duty', code: 'Д1' });
ok(scanD4.defDays.length > 0, 'дежурная служба при минимуме 6/сутки: дефицит (' + scanD4.defDays.length + ' дн.)');
ok(scanD4.worst >= 1, 'худший дефицит ≥ 1');
const defDay = scanD4.defDays[0];
const cands = W.coverageCandidates(scanD4, defDay.d, 5);
ok(cands.list.length > 0, 'кандидаты найдены (' + cands.list.length + ' из ' + cands.all.length + ')');
ok(cands.list.every(c => typeof c.score === 'number' && c.name && Array.isArray(c.why) && Array.isArray(c.viol)), 'структура кандидата: score/name/why/viol');
ok(cands.all.every((c, i) => i === 0 || cands.all[i - 1].score >= c.score), 'сортировка по оценке (убывание)');
/* жёсткие исключения: отсутствующие в этот день не попадают в список */
const busyIds = APP.state.employees.filter(e => e.deptId === 'd4')
  .filter(e => W.rotBusyRaw(((APP.state.plan[MK] || {})[e.id] || {})[defDay.d]))
  .map(e => e.id);
ok(cands.all.every(c => !busyIds.includes(c.eid)), 'отсутствующие (отпуск/больничный/командировка) исключены (' + busyIds.length + ' чел. в этот день)');
/* пожелание «не ставить» */
const wishEid = cands.all.length ? cands.all[0].eid : APP.state.employees.find(e => e.deptId === 'd4').id;
APP.state.dutyWishes = APP.state.dutyWishes || [];
const dk = `${MK}-${pad(defDay.d)}`;
APP.state.dutyWishes.push({ eid: wishEid, kind: 'no', from: dk, to: dk });
const cands2 = W.coverageCandidates(scanD4, defDay.d, 50);
ok(!cands2.all.some(c => c.eid === wishEid), 'пожелание «не ставить» жёстко исключает кандидата');
APP.state.dutyWishes.pop();
/* пожелание «предпочтительно» поднимает кандидата */
APP.state.dutyWishes.push({ eid: wishEid, kind: 'pref', from: dk, to: dk });
const cands3 = W.coverageCandidates(scanD4, defDay.d, 50);
const cPref = cands3.all.find(c => c.eid === wishEid);
const cBase = cands.all.find(c => c.eid === wishEid);
ok(cPref && (!cBase || cPref.score > cBase.score) && cPref.why.some(w => /предпочт/i.test(w)), 'пожелание «предпочтительно ставить» повышает оценку (+40) и видно в причинах');
APP.state.dutyWishes.pop();
/* применение рекомендации и аудит */
const best = cands.list[0];
const cellBefore = (((APP.state.plan[MK] || {})[best.eid] || {})[defDay.d]) || null;
const nApplied = W.coverageApply(scanD4, [{ d: defDay.d, eid: best.eid, code: 'Д1' }]);
ok(nApplied === 1, 'coverageApply: назначена 1 отметка');
ok((((APP.state.plan[MK] || {})[best.eid] || {})[defDay.d]) === 'Д1', 'ячейка плана = Д1 (' + best.name + ', ' + defDay.d + '-е; было ' + cellBefore + ')');
ok(APP.state.log.some(r => r.action === 'Доктор покрытия'), 'аудит: запись «Доктор покрытия»');
ok(APP.state.log.some(r => r.action === 'Ротация по бригадам'), 'аудит: запись «Ротация по бригадам»');
/* отмена через общий стек undo */
W.undo();
const cellAfterUndo = (((APP.state.plan[MK] || {})[best.eid] || {})[defDay.d]) || null;
ok(cellAfterUndo === cellBefore, 'undo откатывает назначение доктора (было ' + cellBefore + ' → стало ' + cellAfterUndo + ')');

section('Модальные окна 3.36');
W.openCoverageDoctor();
ok($('modal') && $('modal').hidden === false, 'модалка доктора открыта');
ok(!!doc.querySelector('#cdBody .covstrip'), 'доктор: календарь покрытия (.covstrip) отрисован');
ok(doc.querySelectorAll('#cdBody .covcell').length >= 28, 'доктор: ≥ 28 ячеек-дней (' + doc.querySelectorAll('#cdBody .covcell').length + ')');
ok(!!doc.querySelector('#cdApplyAll') && !!doc.querySelector('#cdDept') && !!doc.querySelector('#cdNeed') && !!doc.querySelector('#cdMode') && !!doc.querySelector('#cdCode'), 'доктор: контролы (dept/need/mode/code/applyAll)');
/* смена подразделения на дежурную службу с большим минимумом → таблица рекомендаций */
doc.querySelector('#cdDept').value = 'd4';
doc.querySelector('#cdDept').dispatchEvent(new window.Event('change'));
doc.querySelector('#cdNeed').value = '6';
doc.querySelector('#cdNeed').dispatchEvent(new window.Event('change'));
ok(doc.querySelectorAll('#cdBody .candrow').length > 0, 'доктор: рекомендации по дефицитным дням отрисованы (' + doc.querySelectorAll('#cdBody .candrow').length + ' строк)');
ok(doc.querySelectorAll('#cdBody [data-cdgo]').length > 0, 'доктор: кнопки «＋» назначения у кандидатов');
W.closeModal();
ok($('modal').hidden === true, 'модалка доктора закрыта');
W.patternWizard();
ok(!!doc.querySelector('#pwMode') && !!doc.querySelector('#pwBrig') && !!doc.querySelector('#pwSaveBrig'), 'мастер: режим веера, бригады, сохранение');
ok(doc.querySelector('#pwMode').value === 'fan', 'мастер: веер по умолчанию');
ok(!!doc.querySelector('#pwPreview .covstrip'), 'мастер (веер): предпросмотр покрытия');
doc.querySelector('#pwMode').value = 'single';
doc.querySelector('#pwMode').dispatchEvent(new window.Event('change'));
ok(!!doc.querySelector('#pwPreview .pwstrip') && $('pwBrigWrap').style.display === 'none', 'мастер (общая фаза): прежний предпросмотр, бригады скрыты');
ok(!!doc.querySelector('#pwPp'), 'мастер: кнопка «📋 Паспорт шаблона»');
W.closeModal();
W.openPatternConstructor();
ok(!!doc.querySelector('#pcW') && !!doc.querySelector('#pcNw') && !!doc.querySelector('#pcPrev .rot-strip'), 'конструктор: контролы и живая лента цикла');
doc.querySelector('#pcName').value = 'Тест-ротация 2/2';
doc.querySelector('#pcW').value = 'Д2';
doc.querySelector('#pcNw').value = '2';
doc.querySelector('#pcNr').value = '2';
doc.querySelector('#pcNw').dispatchEvent(new window.Event('input'));
const patCountBefore = APP.state.patterns.length;
doc.querySelector('#pcSave').click();
ok(APP.state.patterns.length === patCountBefore + 1, 'конструктор: шаблон сохранён');
const newPat = APP.state.patterns[APP.state.patterns.length - 1];
ok(newPat && newPat.name === 'Тест-ротация 2/2' && newPat.seq === 'Д2,Д2,В,В', 'конструктор: name/seq = «Тест-ротация 2/2» · Д2,Д2,В,В');
ok(APP.state.log.some(r => r.action === 'Конструктор ротации'), 'аудит: запись «Конструктор ротации»');
APP.state.patterns = APP.state.patterns.filter(p => p.id !== newPat.id);
W.openPatternPassport('p2');
ok($('modal').hidden === false && /Паспорт шаблона ротации/.test($('modalBox').innerHTML), 'паспорт: модалка открыта');
ok(/ст\. 110/.test($('modalBox').innerHTML) && /rtbl/.test($('modalBox').innerHTML), 'паспорт: таблица метрик и ссылка на ст. 110');
W.closeModal();
W.openAllPassports();
ok(doc.querySelectorAll('#modalBox tbody tr').length === APP.state.patterns.length, 'сводные паспорта: строк = числу шаблонов');
W.closeModal();

section('Каталог 2.0 (Справочники)');
W.showTab('set');
W.renderPatternsList();
const patBox = $('patBox');
ok(patBox.querySelectorAll('.rot-chip').length > 10, 'каталог: цветные чипы цикла (' + patBox.querySelectorAll('.rot-chip').length + ')');
ok(patBox.querySelectorAll('[data-patpp]').length === APP.state.patterns.length, 'каталог: у каждого шаблона кнопка «📋»');
ok(patBox.querySelectorAll('[data-patdup]').length === APP.state.patterns.length, 'каталог: у каждого шаблона кнопка «⧉»');
ok(/соответствует|внимания|не соответствует|пустой/.test(patBox.innerHTML), 'каталог: вердикты соответствия');
ok(!!$('btnPatConstruct') && !!$('btnPatPpAll') && !!$('btnPatJson') && !!$('btnPatCsv'), 'каталог: кнопки конструктора/паспортов/экспорта');
const nBefore = APP.state.patterns.length;
patBox.querySelector('[data-patdup]').click();
ok(APP.state.patterns.length === nBefore + 1 && /\(копия\)/.test(APP.state.patterns[APP.state.patterns.length - 1].name), 'каталог: дублирование «⧉»');
APP.state.patterns.pop();
W.renderPatternsList();

section('Справка, палитра, тулбар');
W.showHelp();
ok(/Новое в версии 3\.36/.test($('modalBox').innerHTML), 'справка: блок «Новое в версии 3.36»');
ok(/Доктор покрытия/.test($('modalBox').innerHTML) && /[Вв]еер по бригадам/.test($('modalBox').innerHTML), 'справка: фичи 3.36 описаны');
W.closeModal();
ok(html.includes('Доктор покрытия: дефициты и рекомендации') && html.includes('Конструктор ротации: шаблон из параметров'), 'палитра: команды 3.36 в исходнике');
W.showTab('plan');
ok(!!$('btnCovDoc') && /Доктор покрытия/.test($('btnCovDoc').title), 'тулбар планирования: кнопка «🩺 Покрытие»');
ok(!!$('btnPatPassport'), 'сайдбар: кнопка «📋 Паспорт шаблона»');
ok(!!$('brigCard') && !!$('brigBox'), 'сайдбар: карточка «Бригады»');

section('Волна 2: CSV покрытия, бригадная ведомость, «Моя бригада», реестры НСИ');
window.URL.createObjectURL = window.URL.createObjectURL || (() => 'blob:stub');
window.URL.revokeObjectURL = window.URL.revokeObjectURL || (() => {});
const scanCsv = W.coverageScan(cur.y, cur.m, 'dtest', { need: 2, mode: 'duty', code: 'Д1' });
W.coverageCsvDl(scanCsv);
ok(APP.state.log.some(r => r.action === 'Выгрузка покрытия'), 'coverageCsvDl: аудит «Выгрузка покрытия»');
W.printBrigadeSheet();
const pa = $('printArea');
ok(pa && /Бригадная ведомость ротации/.test(pa.innerHTML), 'printBrigadeSheet: ведомость в printArea');
ok(pa.querySelectorAll('table thead th').length === curDays2() + 3, 'ведомость: колонок = дни + ФИО + дежурств + часов (' + pa.querySelectorAll('table thead th').length + ')');
function curDays2() { return new Date(cur.y, cur.m, 0).getDate() }
ok(/Дежурств/.test(pa.innerHTML) && /Часов/.test(pa.innerHTML), 'ведомость: итоги дежурств и часов');
ok(!/var\(--navy2\)|var\(--ink\)|var\(--card\)/.test(pa.innerHTML), 'ведомость: светлая печать без токенов тёмной темы');
ok(/бригада 1/i.test(pa.innerHTML), 'ведомость: заголовки бригад');
const memId = APP.state.brigades[0].members[0];
W.meSetEmp(memId);
W.showTab('me');
ok(!!$('meBrigCard'), '«Мой месяц»: карточка «Моя бригада»');
ok($('meBrigCard') && $('meBrigCard').querySelector('.pwstrip[role="img"]') !== null, '«Моя бригада»: лента ротации с role="img" и aria-именем');
ok($('meBrigCard') && /смещение фазы/.test($('meBrigCard').innerHTML) && /якорь/.test($('meBrigCard').innerHTML), '«Моя бригада»: смещение фазы и якорь');
ok(APP.WIDGET_REGISTRY.some(w => w.id === 'covDoctor') && APP.WIDGET_REGISTRY.some(w => w.id === 'brigCard') &&
   APP.WIDGET_REGISTRY.some(w => w.id === 'rotPassport') && APP.WIDGET_REGISTRY.some(w => w.id === 'covWizard'), 'паспорт виджетов: 4 виджета 3.36');
const ir = APP.INTERACTIVE_REPORTS.find(r => r.id === 'covDoctor');
ok(ir && APP.reportClass(ir) === 'интерактивный' && ir.crit.export === 1, 'реестр отчётов: доктор покрытия — интерактивный 5/5');
const tele = JSON.parse(window.localStorage.getItem('pt.tele') || '{}');
ok(tele['covdoctor'] > 0 && tele['rot:fan'] > 0 && tele['rot:brigade'] > 0 && tele['covdoctor:apply'] > 0 && tele['rot:construct'] > 0, 'телеметрия: счётчики новых поверхностей (pt.tele)');
W.showTab('plan');
W.renderBrigades();
ok($('btnBrigPrint') && $('btnBrigPrint').hidden === false, 'карточка бригад: кнопка «🖨 Бригадная ведомость» активна');

section('Чистота рантайма');
ok(runtimeErrors.length === 0, 'нет рантайм-ошибок за весь прогон' + (runtimeErrors.length ? ': ' + runtimeErrors.slice(0, 5).join(' | ') : ''));

console.log(`\n===== smoke-336 (${file.split('/').pop()}): PASS ${pass} · FAIL ${fail} =====`);
try { window.close(); } catch (e) {}
process.exit(fail ? 1 : 0);
