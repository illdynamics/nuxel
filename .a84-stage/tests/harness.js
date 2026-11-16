// Shared fake DOM + platform used to run the REAL lock code in Deno.
export function makeEnv(opts) {
  opts = opts || {};
  const els = new Map();
  function mkEl(id) {
    const classes = new Set();
    const e = {
      id, hidden: false, textContent: '', innerHTML: '', style: { setProperty(){}, removeProperty(){} },
      dataset: {}, attrs: {}, listeners: {}, children: [],
      classList: {
        add: (...c) => c.forEach((x) => classes.add(x)),
        remove: (...c) => c.forEach((x) => classes.delete(x)),
        toggle: (c, on) => { const v = on === undefined ? !classes.has(c) : !!on; v ? classes.add(c) : classes.delete(c); return v; },
        contains: (c) => classes.has(c),
      },
      addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); },
      removeEventListener() {}, setAttribute(k, v) { this.attrs[k] = String(v); },
      removeAttribute(k) { delete this.attrs[k]; }, getAttribute(k) { return this.attrs[k] ?? null; },
      appendChild(c) { this.children.push(c); return c; },
      querySelectorAll() { return this.children; },
      getBoundingClientRect() { return { x: 0, y: 0, left: 0, top: 0, width: 300, height: 300 }; },
      contains() { return false; }, closest() { return null; }, focus() {}, blur() {},
      setPointerCapture() {}, releasePointerCapture() {},
      scrollIntoView() {},
    };
    Object.defineProperty(e, 'className', { get: () => [...classes].join(' '), set: (v) => { classes.clear(); String(v).split(/\s+/).filter(Boolean).forEach((c) => classes.add(c)); } });
    return e;
  }
  const IDS = ['lockscreen','lockscreen-handle','lockscreen-handle-wrap','lockscreen-hint','lockscreen-time','lockscreen-date',
    'lockscreen-battery','lockscreen-touch-warning','lockscreen-touch-warning-detail','lockscreen-auth','lockscreen-auth-title',
    'lockscreen-auth-hint','lockscreen-auth-error','lockscreen-pattern','lockscreen-pattern-dots','lockscreen-pattern-trail',
    'lockscreen-pinpad','lockscreen-pin-display','lockscreen-fingerprint','lockscreen-fingerprint-status',
    'lockscreen-fingerprint-ring','lockscreen-fingerprint-art','lockscreen-pin-fallback','lockscreen-auth-switch'];
  IDS.forEach((id) => els.set(id, mkEl(id)));
  const body = mkEl('body'), docRoot = mkEl('html');
  body.classList = mkEl('x').classList;
  const docListeners = {};
  const winListeners = {};
  const doc = {
    getElementById: (id) => els.get(id) || null,
    querySelectorAll: () => [],
    addEventListener(t, fn) { (docListeners[t] = docListeners[t] || []).push(fn); },
    removeEventListener() {},
    createElement: (tag) => mkEl('new-' + tag),
    body, documentElement: docRoot,
    dispatchEvent() {}, activeElement: null,
  };
  const window = {
    innerWidth: 360, innerHeight: 760,
    document: doc, console: { log() {}, warn() {}, error() {} },
    setTimeout: (fn) => { setTimeout(fn, 0); return 1; }, clearTimeout() {},
    setInterval: () => 1, clearInterval() {},
    addEventListener(t, fn) { (winListeners[t] = winListeners[t] || []).push(fn); },
    removeEventListener() {},
    requestAnimationFrame: (fn) => { fn(); return 1; },
    matchMedia: () => ({ matches: false }),
    location: { origin: 'http://127.0.0.1:8000', pathname: '/pwa/nuxel-home/index.html', search: '' },
    history: { replaceState() {} },
    navigator: {},
    Promise: Promise,
    CustomEvent: null,
    getSelection: () => null,
    webkit: undefined,
  };
  doc.defaultView = window;
  window.window = window;
  window.globalThis = window;
  // bridge simulation
  const state = { mode: opts.mode || 'swipe', locked: true, pin_fallback_set: opts.pinFallbackSet !== false,
    fingerprint: { provider_ready: !!opts.fpReady, enrolled: !!opts.fpEnrolled, blocker: 'synthetic' },
    success: true, calls: [] };
  const serverPin = opts.pin || '3838';
  // Production-shape bridge client: the credential path posts security RPCs
  // through this session-aware client, so the test must exercise it too.
  function rpc(ns, verb, p) {
    state.calls.push([ns, verb, p]);
    if (ns === 'security' && verb === 'status') return Promise.resolve(Object.assign({}, state));
    if (ns === 'security' && verb === 'unlock') {
      const ok = state.mode === 'swipe' ? true : String(p.secret) === serverPin;
      if (ok) state.locked = false;
      return Promise.resolve(ok ? { success: true, unlocked: !state.locked, locked: state.locked }
                               : { success: false, error: 'invalid_credential', locked: true });
    }
    if (ns === 'security' && verb === 'lock') { state.locked = true; return Promise.resolve({ success: true }); }
    if (ns === 'fingerprint') return Promise.resolve({ success: true, ready: !!state.fingerprint.provider_ready });
    return Promise.resolve({ success: true });
  }
  window.NuxelBridge = { call: (ns, verb, p) => rpc(ns, verb, p) };
  // Home's lowercase session client is what security-lock.js prefers in prod.
  window.bridge = { call: (ns, verb, p) => rpc(ns, verb, p) };
  window.securityBootstrap = {
    status() { return Promise.resolve(Object.assign({}, state)); },
    lock(reason) { state.locked = true; state.calls.push(['lock', reason]); return Promise.resolve({ success: true }); },
    unlockSwipe() {
      state.calls.push(['unlockSwipe']);
      if (state.mode !== 'swipe') return Promise.resolve({ ok: false, error: 'credential-required-on-lockscreen', mode: state.mode });
      if (!state.locked) return Promise.resolve({ ok: true, state: 'UNLOCKED' });
      state.locked = false; return Promise.resolve({ ok: true, state: 'UNLOCKED', via: 'swipe' });
    },
    verifyUnlock() { return Promise.resolve(state.locked ? { ok: false } : { ok: true }); },
    setMode(mode) { state.mode = mode; state.locked = true; return Promise.resolve({ success: true }); },
    call: (ns, verb, p) => rpc(ns, verb, p),
  };
  window.NuxelHost = { available: true, action: (a) => { state.calls.push(['host', a]); return Promise.resolve({ ok: true }); },
    statusRead: () => Promise.resolve({ ok: false }) };
  window.CustomEvent = class { constructor(t, o) { this.type = t; this.detail = (o || {}).detail; } };
  window.Promise = Promise;
  // Intervals are inert in the harness (no real clocks); timeouts are real.
  window.setInterval = () => 0;
  window.clearInterval = () => {};
  window.fetch = (url, o) => {
    let body = {}; try { body = JSON.parse((o && o.body) || '{}'); } catch (e) {}
    return rpc(body.namespace, body.verb, body.params).then((r) => ({ ok: true, json: () => Promise.resolve({ result: r }) }));
  };
  window.__serverState = state;
  return { window, doc, els, state, docListeners, winListeners, mkEl };
}
