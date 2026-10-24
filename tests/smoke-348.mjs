/* WFM 3.48 · smoke — консолидация поезда */
import { boot, mkOk } from './harness.mjs';
import { existsSync } from 'node:fs';
import path from 'node:path';
const file = process.argv[2] || 'План-табель-WFM-3.48.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();

section('Карта фич поезда');
ok(APP.FEATURE_MAP.length === 13, 'карта: 13 версий поезда (3.36–3.48)');
ok(APP.FEATURE_MAP[0].v === '3.36' && APP.FEATURE_MAP[12].v === '3.48', 'диапазон карты: 3.36 → 3.48');
ok(APP.FEATURE_MAP.every(r => r.t && r.f && r.tests), 'у каждой версии: тема, фичи, тесты');
W.openFeatureMap();
ok($('modal').hidden === false && $('modalBox').querySelectorAll('tbody tr').length === 13, 'модалка карты: 13 строк');
$('fmJson').click();
ok(downloads.some(d => /karta-fich-3\.36-3\.48\.json/.test(d.name)), 'JSON карты выгружается');
W.closeModal();

section('Саудит состава поезда');
const chk = W.trainSelfAudit();
ok(chk.length === 17, 'саудит: 17 маркерных проверок');
ok(chk.every(x => x.ok), 'все компоненты поезда на месте: ' + chk.filter(x => x.ok).length + '/17');
W.openSelfAudit();
ok($('modal').hidden === false && $('modalBox').querySelectorAll('.pill.g').length === 17, 'модалка саудита: 17 зелёных пиллов');
W.closeModal();

section('Инфраструктура поезда');
ok(existsSync(path.resolve(process.cwd(), 'tests/ci-all.sh')), 'tests/ci-all.sh существует');
ok(existsSync(path.resolve(process.cwd(), 'build-train.py')), 'build-train.py существует');
ok(existsSync(path.resolve(process.cwd(), 'План-табель-WFM-3.48-offline.html')), 'офлайн-сборка финала поезда существует');

section('Справка и палитра');
W.showHelp();
ok(/Новое в версии 3\.48/.test($('modalBox').textContent) && /Карта фич/.test($('modalBox').textContent), 'справка: блок 3.48');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
