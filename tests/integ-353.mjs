/* WFM 3.53 · integ — серверный контур бюджетов: живой сервер + клиентский merge */
import { spawn } from 'node:child_process';
import { existsSync, rmSync } from 'node:fs';
import path from 'node:path';
import { boot, mkOk } from './harness.mjs';

const { ok, section, report } = mkOk();
const PORT = 8901;
const BASE = `http://127.0.0.1:${PORT}`;
const BUDG_FILE = path.resolve('server/plan-tabel-budgets.json');
if (existsSync(BUDG_FILE)) rmSync(BUDG_FILE);

const srv = spawn(process.execPath, ['server/sync-server.mjs'], { env: { ...process.env, PT_PORT: String(PORT) }, stdio: ['ignore', 'pipe', 'pipe'] });
srv.stdout.on('data', () => {}); srv.stderr.on('data', () => {});
let up = false;
for (let i = 0; i < 60 && !up; i++) {
  try { const r = await fetch(BASE + '/health'); up = r.status < 500; } catch (e) {}
  if (!up) await new Promise(r => setTimeout(r, 250));
}
ok(up, 'сервер поднялся на :' + PORT);

const jput = async items => { const r = await fetch(BASE + '/api/v1/budgets', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items }) }); return { status: r.status, j: await r.json() }; };
const jget = async () => { const r = await fetch(BASE + '/api/v1/budgets'); return { status: r.status, j: await r.json() }; };

section('PUT/GET /api/v1/budgets');
let r = await jput({ '2026-10': { d1: 500000, d4: 900000, ts: 100 } });
ok(r.status === 200 && r.j.saved === 1, 'PUT: месяц сохранён');
r = await jget();
ok(r.j.items['2026-10'].limits.d1 === 500000, 'GET: лимит читается');
r = await jput({ '2026-10': { d1: 600000, ts: 200 }, '2026-11': { d1: null, ts: 200 } });
ok(r.j.saved === 2 && r.j.total === 2, 'merge: 2 месяца, total 2');
r = await jget();
ok(r.j.items['2026-10'].limits.d1 === 600000 && r.j.items['2026-11'].limits.d1 === null, 'обновление и null-лимит');
r = await jput({ '2026-10': { d1: 1, ts: 50 } });
ok(r.j.saved === 0, 'старый ts не перетирает месяц');
r = await jput({ '2026-13': { d1: 1, ts: 1 } });
ok(r.status === 400, '400 на месяц 2026-13');
r = await jput({ '2026-10': { d1: -5, ts: 999 } });
ok(r.status === 400, '400 на отрицательный лимит');

section('Клиентский merge (jsdom против живого сервера)');
const { APP, W } = await boot('План-табель-WFM-3.53.html', { url: BASE + '/' });
W.budgetSet(APP.cur.y, APP.cur.m, 'd1', 123456);
const pushed = await W.budgetsPush();
ok(pushed >= 1, 'budgetsPush: месяцев выгружено ' + pushed);
r = await jget();
const mk = `${APP.cur.y}-${String(APP.cur.m).padStart(2, '0')}`;
ok(r.j.items[mk] && r.j.items[mk].limits.d1 === 123456, 'на сервере лимит клиента');
/* серверная версия новее → pull перезаписывает */
await jput({ [mk]: { d1: 777000, ts: Date.now() + 5000 } });
const ch = await W.budgetsPull();
ok(ch >= 1 && W.budgetLimit(APP.cur.y, APP.cur.m, 'd1') === 777000, 'budgetsPull: более новый ts сервера применился');
/* серверная версия старше → не перетирает */
await jput({ [mk]: { d1: 1, ts: 1 } });
const ch2 = await W.budgetsPull();
ok(ch2 === 0 && W.budgetLimit(APP.cur.y, APP.cur.m, 'd1') === 777000, 'старый ts сервера игнорируется');

srv.kill('SIGTERM');
if (existsSync(BUDG_FILE)) rmSync(BUDG_FILE);
process.exit(report('integ-353'));
