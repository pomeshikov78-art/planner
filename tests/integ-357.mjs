/* WFM 3.57 · integ — cron-дайджест с секцией дефицитов покрытия (webhook) */
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { writeFileSync, rmSync, existsSync } from 'node:fs';
import zlib from 'node:zlib';

let pass = 0, fail = 0;
const ok = (c, n) => { if (c) { pass++; console.log('  ok · ' + n); } else { fail++; console.log('  FAIL · ' + n); } };

const PORT = 8907, HOOK = 8908;
const CANON = '/tmp/canon-357.json';
if (existsSync(CANON)) rmSync(CANON);

/* канон: отдел с минимумом 2 и полным отсутствием дежурств на 7 дней вперёд */
const t = new Date();
const plan = {};
for (let i = 0; i < 10; i++) {
  const d = new Date(t.getFullYear(), t.getMonth(), t.getDate() + i);
  const mk = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  plan[mk] = plan[mk] || {};
  plan[mk].e1 = plan[mk].e1 || {};
  plan[mk].e1[d.getDate()] = 'Я';
}
const state = {
  org: 'Тест', version: 2,
  departments: [{ id: 'd1', name: 'Служба дежурная', minDuty: 2, dutyCode: 'Д1' }],
  employees: [{ id: 'e1', deptId: 'd1', name: 'Один О.', fired: false }],
  reasons: [
    { code: 'Д1', cat: 'duty', coeff: 2, hmode: 'fixed', hours: 24 },
    { code: 'Я', cat: 'work', coeff: 1, hmode: 'day' },
  ],
  plan, vac: [],
};
writeFileSync(CANON, JSON.stringify({ counter: 3, ts: Date.now(), by: 'test', org: 'Тест', gz: 'GZ1:' + zlib.gzipSync(Buffer.from(JSON.stringify(state), 'utf8')).toString('base64') }));

/* webhook-приёмник */
let hookText = null;
const hook = createServer((req, res) => {
  let b = '';
  req.on('data', c => { b += c });
  req.on('end', () => { try { hookText = JSON.parse(b).text } catch (e) {} res.end('ok'); });
});
await new Promise(r => hook.listen(HOOK, r));

const fire = new Date(Date.now() + 60000);
const hhmm = String(fire.getHours()).padStart(2, '0') + ':' + String(fire.getMinutes()).padStart(2, '0');
const srv = spawn(process.execPath, ['server/sync-server.mjs'], {
  env: { ...process.env, PT_PORT: String(PORT), PT_CANON: CANON, PT_DIGEST_CRON: hhmm, PT_DIGEST_WEBHOOK: `http://127.0.0.1:${HOOK}/hook` },
  stdio: ['ignore', 'pipe', 'pipe'],
});
srv.stdout.on('data', () => {}); srv.stderr.on('data', () => {});
let up = false;
for (let i = 0; i < 60 && !up; i++) { try { const r = await fetch(`http://127.0.0.1:${PORT}/health`); up = r.status < 500; } catch (e) {} if (!up) await new Promise(r => setTimeout(r, 250)); }
ok(up, 'сервер с cron-дайджестом поднят');

console.log('  … ожидание срабатывания cron (до 100 с)');
for (let i = 0; i < 100 && !hookText; i++) await new Promise(r => setTimeout(r, 1000));
ok(!!hookText, 'webhook получил дайджест');
ok(/Дайджест/.test(hookText || ''), 'текст дайджеста стандартный');
ok(/Дефициты покрытия 7 дней: Служба дежурная: 7 дн\./.test(hookText || ''), 'секция дефицитов покрытия: 7 дней из 7');

srv.kill('SIGTERM'); hook.close();
if (existsSync(CANON)) rmSync(CANON);
console.log(`\n===== integ-357: PASS ${pass} · FAIL ${fail} =====`);
process.exit(fail ? 1 : 0);
