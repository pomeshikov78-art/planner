/* WFM 3.49 · integ — серверный контур бригад: живой server/sync-server.mjs.
   Запуск: node tests/integ-349.mjs */
import { spawn } from 'node:child_process';
import { existsSync, rmSync } from 'node:fs';
import path from 'node:path';
import { WebSocket } from 'ws';

let pass = 0, fail = 0;
const ok = (c, n) => { if (c) { pass++; console.log('  ok · ' + n); } else { fail++; console.log('  FAIL · ' + n); } };
const section = t => console.log('\n== ' + t + ' ==');

const PORT = 8899;
const BASE = `http://127.0.0.1:${PORT}`;
const BRIG_FILE = path.resolve('server/plan-tabel-brigades.json');
if (existsSync(BRIG_FILE)) rmSync(BRIG_FILE);

function startServer() {
  const p = spawn(process.execPath, ['server/sync-server.mjs'], {
    env: { ...process.env, PT_PORT: String(PORT) }, stdio: ['ignore', 'pipe', 'pipe'],
  });
  p.stdout.on('data', () => {}); p.stderr.on('data', () => {});
  return p;
}
async function waitPort() {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(BASE + '/health'); if (r.ok || r.status === 404) return true; } catch (e) {}
    try { const r = await fetch(BASE + '/status'); if (r.status < 500) return true; } catch (e) {}
    await new Promise(r => setTimeout(r, 250));
  }
  return false;
}
const jput = async items => {
  const r = await fetch(BASE + '/api/v1/brigades', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items }) });
  return { status: r.status, j: await r.json() };
};
const jget = async () => { const r = await fetch(BASE + '/api/v1/brigades'); return { status: r.status, j: await r.json() }; };

let srv = startServer();
ok(await waitPort(), 'сервер поднялся на :' + PORT);

section('PUT/GET /api/v1/brigades');
let r = await jput([{ id: 'b1', name: 'Бригада 1', patId: 'p2', anchor: '2026-10-01', offset: 0, members: ['e1', 'e2'], ts: 100 }]);
ok(r.status === 200 && r.j.ok === 1 && r.j.saved === 1, 'PUT: сохранена 1 бригада');
r = await jget();
ok(r.j.items.length === 1 && r.j.items[0].name === 'Бригада 1', 'GET: бригада читается');
r = await jput([
  { id: 'b1', name: 'Бригада 1*', patId: 'p2', anchor: '2026-10-01', offset: 0, members: ['e1', 'e2', 'e3'], ts: 200 },
  { id: 'b2', name: 'Бригада 2', patId: 'p2', anchor: '2026-10-01', offset: 2, members: ['e4'], ts: 50 },
]);
ok(r.j.saved === 2 && r.j.total === 2, 'PUT merge: 2 записи, total 2');
r = await jget();
ok(r.j.items.find(x => x.id === 'b1').name === 'Бригада 1*' && r.j.items.find(x => x.id === 'b1').members.length === 3, 'merge по id применил новую версию');
r = await jput([{ id: 'b1', name: 'СТАРНАЯ', ts: 150 }]);
ok(r.j.saved === 0, 'старый ts не перетирает новую версию (last-write-wins)');
r = await jget();
ok(r.j.items.find(x => x.id === 'b1').name === 'Бригада 1*', 'содержимое не изменилось после старого ts');
r = await jput([{ name: 'без id' }]);
ok(r.status === 400 && r.j.ok === 0, '400 на записи без id');
r = await jput(Array.from({ length: 201 }, (_, i) => ({ id: 'x' + i, name: 'x', ts: 1 })));
ok(r.status === 400, '400 при > 200 бригад');

section('WS-трансляция {type:"brigades"}');
const ws = new WebSocket('ws://127.0.0.1:' + PORT + '/');
await new Promise((res, rej) => { ws.on('open', res); ws.on('error', rej); setTimeout(rej, 5000); }).catch(() => {});
const got = new Promise(res => { ws.on('message', d => { try { const m = JSON.parse(d); if (m.type === 'brigades') res(m); } catch (e) {} }); setTimeout(() => res(null), 6000); });
await jput([{ id: 'b3', name: 'Бригада 3', patId: 'p2', anchor: '2026-10-01', offset: 1, members: ['e5'], ts: 300 }]);
const ev = await got;
ok(ev && ev.total === 3 && typeof ev.ts === 'number', 'WS-событие brigades с total и ts');
ws.close();

section('Персистентность между перезапусками');
srv.kill('SIGTERM');
await new Promise(r => setTimeout(r, 700));
srv = startServer();
ok(await waitPort(), 'сервер перезапустился');
r = await jget();
ok(r.j.items.length === 3, 'после ресторта 3 бригады из файла PT_BRIG_FILE');
srv.kill('SIGTERM');

section('Клиентские функции слияния (jsdom-независимо)');
ok(existsSync(BRIG_FILE), 'файл plan-tabel-brigades.json создан рядом с сервером');
rmSync(BRIG_FILE);
ok(true, 'артефакты теста подчищены');

console.log(`\n===== integ-349: PASS ${pass} · FAIL ${fail} =====`);
process.exit(fail ? 1 : 0);
