/* WFM 3.56 · integ — серверный скан покрытия GET /api/v1/coverage */
import { spawn } from 'node:child_process';
import { writeFileSync, rmSync, existsSync } from 'node:fs';
import zlib from 'node:zlib';

let pass = 0, fail = 0;
const ok = (c, n) => { if (c) { pass++; console.log('  ok · ' + n); } else { fail++; console.log('  FAIL · ' + n); } };
const section = t => console.log('\n== ' + t + ' ==');

const PORT = 8905;
const BASE = `http://127.0.0.1:${PORT}`;
const CANON = '/tmp/canon-356.json';
if (existsSync(CANON)) rmSync(CANON);

section('Без канона — 409');
let srv = spawn(process.execPath, ['server/sync-server.mjs'], { env: { ...process.env, PT_PORT: String(PORT), PT_CANON: CANON }, stdio: ['ignore', 'pipe', 'pipe'] });
srv.stdout.on('data', () => {}); srv.stderr.on('data', () => {});
const waitUp = async () => { for (let i = 0; i < 60; i++) { try { const r = await fetch(BASE + '/health'); if (r.status < 500) return true; } catch (e) {} await new Promise(r => setTimeout(r, 250)); } return false; };
ok(await waitUp(), 'сервер поднят');
let r = await fetch(`${BASE}/api/v1/coverage?y=2026&m=10&dept=d1&need=1`);
ok(r.status === 409, 'без канона: 409 с подсказкой');
srv.kill('SIGTERM'); await new Promise(res => setTimeout(res, 600));

section('Сид канона и скан покрытия');
const y = 2026, m = 10, DIM = 31;
const state = {
  org: 'Тест', version: 2,
  departments: [{ id: 'd1', name: 'Служба', minDuty: 1, dutyCode: 'Д1' }],
  employees: [
    { id: 'e1', deptId: 'd1', name: 'Один О.', fired: false },
    { id: 'e2', deptId: 'd1', name: 'Два Д.', fired: false },
  ],
  reasons: [
    { code: 'Д1', cat: 'duty', coeff: 2, hmode: 'fixed', hours: 24 },
    { code: 'Я', cat: 'work', coeff: 1, hmode: 'day' },
    { code: 'В', cat: 'off', coeff: 0, hmode: 'none' },
  ],
  plan: { '2026-10': { e1: { 1: 'Д1', 5: 'Д1' }, e2: { 5: 'Д1' } } },
  vac: [],
};
const gz = 'GZ1:' + zlib.gzipSync(Buffer.from(JSON.stringify(state), 'utf8')).toString('base64');
writeFileSync(CANON, JSON.stringify({ counter: 7, ts: Date.now(), by: 'test', org: 'Тест', gz }));
srv = spawn(process.execPath, ['server/sync-server.mjs'], { env: { ...process.env, PT_PORT: String(PORT), PT_CANON: CANON }, stdio: ['ignore', 'pipe', 'pipe'] });
srv.stdout.on('data', () => {}); srv.stderr.on('data', () => {});
ok(await waitUp(), 'сервер с каноном поднят');
r = await fetch(`${BASE}/api/v1/coverage?y=${y}&m=${m}&dept=d1&need=1`);
let j = await r.json();
ok(j.ok === 1 && j.counter === 7, 'скан: ok, номер канона 7');
ok(j.days.length === DIM, 'дней в месяце: ' + DIM);
ok(j.days[0].plan === 1 && j.days[0].deficit === 0, '1-е: план 1, дефицита нет');
ok(j.days[4].plan === 2 && j.days[4].deficit === 0, '5-е: план 2 (оба сотрудника)');
ok(j.defDays === DIM - 2 && j.worst === 1, 'дефицитных дней ' + j.defDays + ', худший 1');
r = await fetch(`${BASE}/api/v1/coverage?y=${y}&m=${m}&dept=d1&need=3`);
j = await r.json();
ok(j.days[4].deficit === 1 && j.worst === 3, 'need=3: худший дефицит 3');
r = await fetch(`${BASE}/api/v1/coverage?y=${y}&m=13`);
ok(r.status === 400, '400 на месяц 13');
r = await fetch(`${BASE}/api/v1/coverage?y=${y}`);
ok(r.status === 400, '400 без m');
srv.kill('SIGTERM');
if (existsSync(CANON)) rmSync(CANON);
console.log(`\n===== integ-356: PASS ${pass} · FAIL ${fail} =====`);
process.exit(fail ? 1 : 0);
