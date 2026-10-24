/* ============================================================================
   WFM · tests/harness.mjs — общий бут-харнес jsdom для смоуков релизного
   поезда 3.38+. Использование:
     import { boot, mkOk } from './harness.mjs';
     const { APP, W, $, doc, errors } = await boot('План-табель-WFM-3.38.html');
     const { ok, section, report } = mkOk();
   ============================================================================ */
import { readFileSync } from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';
import path from 'node:path';

export async function boot(fileRel, opts = {}) {
  const file = path.resolve(process.cwd(), fileRel);
  const html = readFileSync(file, 'utf8');
  const runtimeErrors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => {
    const msg = String((e && e.message) || e);
    if (/Not implemented|Could not parse CSS|getContext/i.test(msg)) return;
    runtimeErrors.push(msg);
  });
  const dom = new JSDOM(html, {
    runScripts: 'dangerously', pretendToBeVisual: true,
    url: (opts && opts.url) || 'http://127.0.0.1/', virtualConsole: vc,
  });
  const { window } = dom;
  let mmMatches = false;
  if (opts && opts.mobile) mmMatches = true;
  window.matchMedia = window.matchMedia || (q => ({
    matches: /max-width/.test(q) ? mmMatches : false, media: q, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
    dispatchEvent() { return false; },
  }));
  window.ResizeObserver = window.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };
  window.IntersectionObserver = window.IntersectionObserver || class { observe() {} unobserve() {} disconnect() {} };
  window.WebSocket = window.WebSocket || class { constructor() { this.readyState = 0 } send() {} close() {} addEventListener() {} };
  window.BroadcastChannel = window.BroadcastChannel || class { constructor() {} postMessage() {} close() {} addEventListener() {} };
  const baseUrl = (opts && opts.url) || 'http://127.0.0.1/';
  if (!window.fetch) {
    window.fetch = (u, o) => fetch(new URL(u, baseUrl).href, o);
  }
  window.URL.revokeObjectURL = window.URL.revokeObjectURL || (() => {});
  window.addEventListener('error', e => runtimeErrors.push('window.onerror: ' + (e.message || e.error)));
  /* перехват скачиваний */
  const downloads = [];
  window.download = (name, content, mime) => { downloads.push({ name, content, mime }); };
  if (!window.crypto || !window.crypto.subtle) {
    const { webcrypto } = await import('node:crypto');
    try { Object.defineProperty(window, 'crypto', { value: webcrypto, configurable: true }); } catch (e) {}
  }
  const t0 = Date.now();
  let APP = null;
  while (Date.now() - t0 < 30000) {
    if (window.APP && window.APP.state && window.APP.state.employees && window.APP.state.employees.length) { APP = window.APP; break; }
    await new Promise(r => setTimeout(r, 100));
  }
  if (!APP) throw new Error('APP не инициализирован: ' + runtimeErrors.join(' | '));
  const W = window;
  const $ = id => window.document.getElementById(id);
  /* гасим приветственную модалку firstRun (в jsdom таймер может запаздывать) */
  for (let i = 0; i < 40; i++) {
    if (/Добро пожаловать/.test(($('modalBox') || {}).innerHTML || '')) { W.closeModal(); break; }
    await new Promise(r => setTimeout(r, 100));
  }
  await new Promise(r => setTimeout(r, 300));
  if (/Добро пожаловать/.test(($('modalBox') || {}).innerHTML || '')) W.closeModal();
  return { APP, W, $, doc: window.document, window, errors: runtimeErrors, downloads, html };
}

export function mkOk() {
  let pass = 0, fail = 0;
  const ok = (cond, name) => {
    if (cond) { pass++; console.log('  ok · ' + name); }
    else { fail++; console.log('  FAIL · ' + name); }
  };
  const section = t => console.log('\n== ' + t + ' ==');
  const report = file => {
    console.log(`\n===== ${path.basename(file)}: PASS ${pass} · FAIL ${fail} =====`);
    return fail;
  };
  return { ok, section, report };
}
