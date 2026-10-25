/* WFM 3.62 · smoke — подписи приказов и реестр */
import { boot, mkOk } from './harness.mjs';
const file = process.argv[2] || 'План-табель-WFM-3.62.html';
const { APP, W, $, errors, downloads } = await boot(file);
const { ok, section, report } = mkOk();

section('Подпись и сверка');
const text = 'ПРИКАЗ № 1/ОД\nТестовый текст приказа для подписи.';
const rec = await W.orderSign(text, '1/ОД', 'Тестовый шаблон');
ok(rec && /^[0-9a-f]{64}$/.test(rec.hash), 'SHA-256 hex64: ' + rec.hash.slice(0, 12) + '…');
ok(await W.orderVerify(rec) === true, 'сверка подписи: корректна');
rec.text += ' ПОДМЕНА';
ok(await W.orderVerify(rec) === false, 'после подмены текста подпись не сходится');
rec.text = text;
ok(await W.orderVerify(rec) === true, 'возврат текста восстанавливает сверку');
ok(APP.state.orders.length === 1 && APP.state.orders[0].by, 'реестр в каноне: запись с автором');

section('Реестр в UI');
W.showTab('rep');
W.renderOrdersRegistry();
ok($('ordersRegBox') && /1\/ОД/.test($('ordersRegBox').innerHTML), 'реестр: номер и хеш видны');
ok($('ordersRegBox').querySelectorAll('[data-ordv]').length === 1 && $('ordersRegBox').querySelectorAll('[data-ordd]').length === 1, 'кнопки «✔ сверить» и «⤓ текст»');
$('ordersRegBox').querySelector('[data-ordd]').click();
ok(downloads.some(d => /prikaz-podpisan-/.test(d.name) && d.content === text), 'выгрузка подписанного текста');

section('Конструктор: кнопка подписи');
W.openOrderConstructor();
ok(!!$('ocSign'), 'конструктор: «✍ Подписать в реестр»');
$('ocSign').click();
await new Promise(r => setTimeout(r, 250));
ok(APP.state.orders.length === 2, 'подпись из конструктора добавила запись');
ok(/ПРИКАЗ №/.test(APP.state.orders[0].text), 'в реестр попал отрeндеренный текст с плейсхолдерами');
W.closeModal();
ok(APP.state.log.some(r => r.action === 'Приказ подписан в реестр'), 'аудит подписи');
W.showHelp();
ok(/Новое в версии 3\.62/.test($('modalBox').textContent) && /SHA-256/.test($('modalBox').textContent), 'справка: блок 3.62');
W.closeModal();
ok(errors.length === 0, 'нет рантайм-ошибок' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
process.exit(report(file));
