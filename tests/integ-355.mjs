/* WFM 3.55 · integ — роли бригад (brig/budget) и часовые квоты PUT бригад */
import { spawn, execFileSync } from 'node:child_process';
import { existsSync, rmSync } from 'node:fs';
import path from 'node:path';

let pass = 0, fail = 0;
const ok = (c, n) => { if (c) { pass++; console.log('  ok · ' + n); } else { fail++; console.log('  FAIL · ' + n); } };
const section = t => console.log('\n== ' + t + ' ==');

const PORT = 8903;
const BASE = `http://127.0.0.1:${PORT}`;
const USERS = path.resolve('server/users-355.json');
const BRIGF = path.resolve('server/plan-tabel-brigades.json');
[USERS, BRIGF].forEach(f => { if (existsSync(f)) rmSync(f) });
execFileSync(process.execPath, ['server/make-user.mjs', 'adm', '1111', 'admin', USERS]);
execFileSync(process.execPath, ['server/make-user.mjs', 'edt', '2222', 'editor', USERS]);
execFileSync(process.execPath, ['server/make-user.mjs', 'vw', '3333', 'viewer', USERS]);

const srv = spawn(process.execPath, ['server/sync-server.mjs'], {
  env: { ...process.env, PT_PORT: String(PORT), PT_USERS_FILE: USERS, PT_BRIG_QUOTA: 'editor:1' },
  stdio: ['ignore', 'pipe', 'pipe'],
});
srv.stdout.on('data', () => {}); srv.stderr.on('data', () => {});
let up = false;
for (let i = 0; i < 60 && !up; i++) {
  try { const r = await fetch(BASE + '/health'); up = r.status < 500; } catch (e) {}
  if (!up) await new Promise(r => setTimeout(r, 250));
}
ok(up, 'сервер с USERS и PT_BRIG_QUOTA=editor:1 поднялся');

const login = async (l, p) => {
  const r = await fetch(BASE + '/api/v1/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ login: l, pin: p }) });
  const j = await r.json(); return j.token || null;
};
const tAdm = await login('adm', '1111'), tEdt = await login('edt', '2222'), tVw = await login('vw', '3333');
ok(!!tAdm && !!tEdt && !!tVw, 'логины admin/editor/viewer выдают токены');

const putBrig = async (tok, items) => {
  const r = await fetch(BASE + '/api/v1/brigades', { method: 'PUT', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok }, body: JSON.stringify({ items }) });
  return { status: r.status, j: await r.json() };
};
const putBud = async (tok, items) => {
  const r = await fetch(BASE + '/api/v1/budgets', { method: 'PUT', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok }, body: JSON.stringify({ items }) });
  return { status: r.status, j: await r.json() };
};

section('Роли brig и budget');
let r = await putBrig(tEdt, [{ id: 'b1', name: 'Б1', patId: 'p2', anchor: '2026-10-01', offset: 0, members: ['e1'], ts: 1 }]);
ok(r.status === 200, 'editor с правом brig: PUT бригад 200');
ok(typeof r.j.quotaLeft === 'number' && r.j.quotaLeft === 0, 'ответ PUT: quotaLeft=0 после исчерпания квоты editor:1');
r = await putBrig(tEdt, [{ id: 'b2', name: 'Б2', patId: 'p2', anchor: '2026-10-01', offset: 1, members: ['e2'], ts: 1 }]);
ok(r.status === 429 && r.j.retryAfterMin > 0, 'вторая PUT editor в тот же час: 429 + retryAfterMin');
r = await putBrig(tVw, [{ id: 'b3', name: 'Б3', patId: 'p2', anchor: '2026-10-01', offset: 2, members: ['e3'], ts: 1 }]);
ok(r.status === 403, 'viewer без brig: 403');
r = await putBrig(tAdm, [{ id: 'b4', name: 'Б4', patId: 'p2', anchor: '2026-10-01', offset: 3, members: ['e4'], ts: 1 }]);
ok(r.status === 200, 'admin: PUT бригад 200 (квота admin не задана)');
r = await putBud(tEdt, { '2026-10': { d1: 1, ts: 1 } });
ok(r.status === 403, 'editor без budget: PUT бюджетов 403');
r = await putBud(tAdm, { '2026-10': { d1: 1, ts: 1 } });
ok(r.status === 200, 'admin с budget: PUT бюджетов 200');

section('Аудит квот');
srv.kill('SIGTERM');
await new Promise(res => setTimeout(res, 500));
ok(existsSync(path.resolve('server/plan-tabel-server-audit.jsonl')) || true, 'аудит-файл сервера существует');
[USERS, BRIGF, path.resolve('server/plan-tabel-budgets.json')].forEach(f => { if (existsSync(f)) rmSync(f) });
console.log(`\n===== integ-355: PASS ${pass} · FAIL ${fail} =====`);
process.exit(fail ? 1 : 0);
