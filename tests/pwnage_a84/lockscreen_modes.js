#!/usr/bin/env node
/* A84 lockscreen behaviour: the lockhead is ALWAYS on the glass, and the lock
 * mode decides what swiping it does.
 *
 * Real DOM (jsdom) + the shipped lockscreen.js / lockscreen-auth.js, with a
 * deterministic #lockscreen-auth mock so the panel markup is known exactly.
 * Every unlock verdict is recorded so "the credential panel re-verified a
 * gesture that already opened it" would fail loudly.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../..');
let JSDOM;
try { JSDOM = require('jsdom').JSDOM; } catch (e) { JSDOM = require('/tmp/jsdomtest/node_modules/jsdom').JSDOM; }

let checks = 0; let failures = 0;
function check(name, cond, detail) {
  checks++;
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond || detail === undefined ? '' : '  ' + detail));
  if (!cond) failures++;
}

const LOCKS = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/lockscreen.js'), 'utf8');
const AUTH = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/lockscreen-auth.js'), 'utf8');
const CSS = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/css/lockscreen.css'), 'utf8');
const HTML = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/index.html'), 'utf8');
const APP = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/app.js'), 'utf8');
const SETJS = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-apps/settings/pwange45000-settings.js'), 'utf8');
const SETHTML = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-apps/settings/index.html'), 'utf8');

const VW = 360; const VH = 760;
const PANEL = { width: 300, height: 240 };   // test pin keypad box

function mkDom(opts) {
  const dom = new JSDOM('<!doctype html><html><body></body></html>', {
    runScripts: 'outside-only', pretendToBeVisual: true,
  });
  const w = dom.window;
  w.innerWidth = VW; w.innerHeight = VH;
  w.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  w.PointerEvent = class PointerEvent extends w.MouseEvent {
    constructor(t, o) {
      super(t, Object.assign({ bubbles: true, cancelable: true }, o || {}));
      this.pointerId = (o || {}).pointerId;
      this.pointerType = (o || {}).pointerType || 'touch';
    }
  };
  const d = w.document;
  const make = (id, parent, cls) => {
    const el = d.createElement('div');
    el.id = id; if (cls) el.className = cls; parent.appendChild(el); return el;
  };
  const root = make('lockscreen', d.body, 'lockscreen');
  make('lockscreen-time', root); make('lockscreen-date', root); make('lockscreen-battery', root);
  const wrap = make('lockscreen-handle-wrap', root, 'lockscreen-handle-wrap');
  const handle = make('lockscreen-handle', wrap, 'lockscreen-handle');
  const hint = make('lockscreen-hint', wrap, 'lockscreen-hint');
  const auth = make('lockscreen-auth', root, 'lockscreen-auth');
  auth.hidden = true;
  const pad = make('lockscreen-pinpad', auth);
  const pat = make('lockscreen-pattern', auth);
  const fp = make('lockscreen-fingerprint', auth);
  const fb = make('lockscreen-pin-fallback', auth);
  fb.hidden = true;
  make('lockscreen-auth-error', auth);
  make('lockscreen-auth-title', auth); make('lockscreen-auth-hint', auth);
  make('lockscreen-fingerprint-status', auth); make('lockscreen-fingerprint-ring', auth);

  const geo = { handle: { top: 566, size: 110 }, panel: null };
  // jsdom has no layout: give the JS what the CSS guarantees.
  wrap.getBoundingClientRect = () => ({ left: (VW - geo.handle.size) / 2, top: geo.handle.top,
    width: geo.handle.size, height: geo.handle.size, right: (VW + geo.handle.size) / 2,
    bottom: geo.handle.top + geo.handle.size });
  handle.getBoundingClientRect = wrap.getBoundingClientRect;
  auth.getBoundingClientRect = () => {
    if (auth.hidden || auth.classList.contains('lockscreen-auth-closed') || !geo.panel) {
      return { left: 0, top: VH, width: VW, height: 0, right: VW, bottom: VH };
    }
    return { left: (VW - PANEL.width) / 2, top: geo.panel.top, width: PANEL.width,
      height: PANEL.height, right: (VW + PANEL.width) / 2, bottom: geo.panel.top + PANEL.height };
  };
  [pad, pat, fp, fb].forEach((el) => {
    el.getBoundingClientRect = () => {
      const b = auth.getBoundingClientRect();
      return { left: b.left, top: b.top, width: b.width, height: b.height, right: b.right, bottom: b.bottom };
    };
  });
  // jsdom ignores synthetic events (isTrusted=false, non-configurable) and
  // refuses Proxies.  For THIS DOM-level suite only, drop the script-gesture
  // guard: the trust rule itself is covered by the vm-based A45 harness, which
  // builds its own event objects.  No other assertion changes.
  const LOCK_SRC = LOCKS.replace(/if \(e && e\.isTrusted === false\) return;/g, '/* trusted: jsdom has no trusted events */');
  w.__dispatch = function trustedDispatch(node, ev) { return node.dispatchEvent(ev); };

  // deterministic #lockscreen-auth surface.  NOTE: jsdom has global `surface`
  // and `status` elements, which shadow same-named helpers - never use those names.
  const STATUS = (opts && opts.status) || {};
  function MockAuth(options) {
    this.opts = options || {};
    this.opts.status = STATUS;
    this.el = auth; this.pinpad = pad; this.patternEl = pat; this.fpEl = fp; this.pinFallback = fb;
    this.titleEl = d.getElementById('lockscreen-auth-title'); this.hintEl = d.getElementById('lockscreen-auth-hint');
    this.errorEl = d.getElementById('lockscreen-auth-error'); this.trail = null; this.fpRing = d.getElementById('lockscreen-fingerprint-ring');
    this.fpStatus = d.getElementById('lockscreen-fingerprint-status');
    this.mode = 'swipe'; this.effectiveMode = 'swipe';
    this.panelOpen = false; this.status = null; this.pin = ''; this.busy = false;
    this.verdicts = [];
  }
  MockAuth.prototype._notify = function (prev) {
    if (this.opts.onModeChange) this.opts.onModeChange(this.effectiveMode, this, prev);
  };
  MockAuth.prototype._setPanelOpen = function (open) {
    this.panelOpen = !!open;
    this.el.classList.toggle('lockscreen-auth-closed', !this.panelOpen);
    this._showSurfaces(this.effectiveMode);
    if (this.opts.onPanelMode) this.opts.onPanelMode(this.panelOpen, this.effectiveMode);
  };
  MockAuth.prototype._showMode = function (mode, o) {
    o = o || {}; const prev = this.effectiveMode; this.effectiveMode = mode;
    this._notify(prev);
    this._showSurfaces(mode);
    if (mode === 'swipe') {
      this.el.hidden = true; this.panelOpen = false;
      return;
    }
    this.el.hidden = false;
    this.patternEl.hidden = mode !== 'pattern';
    this.pinpad.hidden = mode !== 'pin';
    this.fpEl.hidden = mode !== 'fingerprint';
    this.pinFallback.hidden = mode === 'pin';
    this._setPanelOpen(o.open === true);
  };
  MockAuth.prototype._showSurfaces = function (mode) {
    /* Mirrors the real _paintSurfaces: a closed panel paints NO surface. */
    const open = mode !== 'swipe' && this.panelOpen;
    this.patternEl.hidden = !(open && mode === 'pattern');
    this.pinpad.hidden = !(open && mode === 'pin');
    this.fpEl.hidden = !(open && mode === 'fingerprint');
  };
  MockAuth.prototype.cancelToLockhead = function () { this._setPanelOpen(false); };
  MockAuth.prototype.show = function () {
    this.panelOpen = false;
    const st = (this.opts.status || {});
    this.status = st;
    const mode = st.mode || 'swipe';
    this.mode = mode;
    this.effectiveMode = mode;
    const fp = st.fingerprint || {};
    const usable = !!(fp.provider_ready && fp.enrolled && st.pin_fallback_set);
    this._showMode(mode === 'unlock' ? 'swipe' : (mode === 'fingerprint' && !usable ? 'pin' : mode));
    return Promise.resolve(st);
  };
  MockAuth.prototype.hide = function () { this.el.hidden = true; };
  MockAuth.prototype.isVisible = function () { return !this.el.hidden; };
  MockAuth.prototype.isPanelOpen = function () { return !this.el.hidden && !!this.panelOpen; };
  MockAuth.prototype.openPanel = function () {
    if (this.effectiveMode === 'swipe') return false;
    if (this.effectiveMode === 'fingerprint') {
      const f = (this.status && this.status.fingerprint) || {};
      if (!(f.provider_ready && f.enrolled)) {
        if (this.status && this.status.pin_fallback_set) { this.showPinFallback(); return true; }
        this._setPanelOpen(true); return true;
      }
    }
    this._setPanelOpen(true); return true;
  };
  MockAuth.prototype.closePanel = function () { if (this.effectiveMode !== 'swipe') this._setPanelOpen(false); };
  MockAuth.prototype.showPinFallback = function () {
    if (this.effectiveMode === 'pin' && this.isPanelOpen()) return;
    this._showMode('pin', { open: true });
  };
  MockAuth.prototype.enterPin = function (value) {   // simulate a verified keypad submit
    this.verdicts.push(String(value));
    if (String(value) !== String(this.opts.pin || '3838')) return Promise.resolve({ success: false, error: 'invalid_credential' });
    const res = { success: true, unlocked: true, via: 'pin' };
    return Promise.resolve(this.opts.onUnlock ? this.opts.onUnlock({ via: 'pin', result: res }) : res);
  };
  MockAuth.prototype.constructor = { name: "MockLockscreenAuth" };
  w.NuxelLockscreenAuth = MockAuth;

  const hostCalls = [];
  const unlockCalls = [];
  w.NuxelHost = {
    available: true,
    action(a) { hostCalls.push(a); if (a === 'unlock') unlockCalls.push(a); return Promise.resolve({ ok: true }); },
    statusRead(n) {
      if (n === 'battery-capacity') return Promise.resolve({ ok: true, text: '80' });
      if (n === 'battery-status') return Promise.resolve({ ok: true, text: 'Discharging' });
      return Promise.resolve({ ok: true, text: 'DISPLAY_ON' });
    },
  };
  w.nuxelDiag = null;
  // The DOM stub above models the auth manager's contract exactly (panel
  // visibility, mode callbacks, panel open/close); the REAL auth file's key
  // handling is covered by the jsdom keypad harness + the A80 suite.
  w.eval(LOCK_SRC);
  return { dom, w, d, geo, els: { root, wrap, handle, hint, auth, pad, pat, fp, fb }, hostCalls, unlockCalls,
           PointerEvent: w.PointerEvent };
}

/** Boot a lockscreen in *mode* with an auth-honest controller. */
async function boot(mode, opts) {
  opts = opts || {};
  // NOTE: merges the status deeply here; a shallow Object.assign(..., opts)
  // replaced the whole status with opts.status and silently reset the mode.
  const status = Object.assign({ mode, locked: true, pin_fallback_set: true,
    fingerprint: { provider_ready: false, enrolled: false } }, opts.status || {});
  const h = mkDom(Object.assign({}, opts, { status }));
  const ctl = {
    direct: [], panelRequests: [], credentialUnlocks: [],
    unlockFromLockscreen(instance, request) {
      this.panelRequests.push(request);
      if (!instance.acceptGestureUnlock(request)) return Promise.resolve({ ok: false, error: 'invalid-or-replayed-gesture' });
      if (!request.direct) return Promise.resolve({ ok: false, error: 'credential-required' });
      this.direct.push(request);
      h.w.NuxelHost.action('unlock');
      instance.hide();
      return Promise.resolve({ ok: true, state: 'UNLOCKED' });
    },
    completeCredentialUnlock(instance, request) {
      if (!(request && request.result && request.result.unlocked === true)) {
        return Promise.resolve({ ok: false, error: 'credential-not-verified' });
      }
      this.credentialUnlocks.push(request.via);
      h.w.NuxelHost.action('unlock');   // Home._commitVerifiedUnlock does this
      instance.hide();
      return Promise.resolve({ ok: true, state: 'UNLOCKED' });
    },
  };
  h.w.nuxel = ctl;
  const ls = new h.w.NuxelLockscreen();
  h.ls = ls; h.ctl = ctl;
  ls.show('test');
  await flush(h.w);
  return h;
}
function flush(w) { return new Promise((r) => setTimeout(r, 0)); }
function swipe(h, startY, endY) {
  const ev = (t, y) => new h.PointerEvent(t, { bubbles: true, cancelable: true, pointerId: 1, button: 0, clientX: 180, clientY: y });
  h.w.__dispatch(h.els.handle, ev('pointerdown', startY));
  h.w.__dispatch(h.w, ev('pointermove', (startY + endY) / 2));
  h.w.__dispatch(h.w, ev('pointermove', endY));
  h.w.__dispatch(h.w, ev('pointerup', endY));
  return flush(h.w);
}
function tap(h, y) {
  const ev = (t) => new h.PointerEvent(t, { bubbles: true, cancelable: true, pointerId: 2, button: 0, clientX: 180, clientY: y });
  h.w.__dispatch(h.els.handle, ev('pointerdown'));
  h.w.__dispatch(h.w, ev('pointerup'));
  return flush(h.w);
}

(async () => {
  // ---------------------------------------------------------------- swipe --
  {
    const h = await boot('swipe');
    check('swipe: lockhead mounted and visible', h.els.root.hidden === false && h.els.wrap.hidden === false && !h.ls.handle.hidden);
    check('swipe: auth panel not shown', h.els.auth.hidden === true);
    check('swipe: hint tells the owner to swipe up', /swipe up to unlock/.test(h.els.hint.textContent));
    await swipe(h, 620, 400);
    check('swipe: a full swipe unlocks directly', h.ctl.direct.length === 1 && h.ls.isLocked() === false);
    check('swipe: exactly one host unlock action', h.unlockCalls.length === 1);
    check('swipe: gesture marked direct', h.ctl.direct[0].direct === true && h.ctl.direct[0].route === 'unlock');
  }
  {
    const h = await boot('unlock');   // Settings calls "unlock directly" this
    check('unlock preset renders as swipe with the lockhead', h.els.auth.hidden === true && h.els.wrap.hidden === false);
    await swipe(h, 620, 400);
    check('unlock preset also unlocks on one swipe', h.ctl.direct.length === 1 && h.ls.isLocked() === false);
  }

  // ---------------------------------------------------------------- PIN -----
  {
    const h = await boot('pin');
    check('pin: lockhead STILL visible (never hidden)', h.els.wrap.hidden === false && h.els.root.hidden === false);
    // The stub's pinpad is never [hidden]; what must hold is that the panel is
    // CLOSED (CSS hides the whole panel and JS paints no surface) - checked via
    // the real auth contract below and by the CSS rule.
    check('pin: keypad surface not painted before the panel opens', h.ls.auth.isPanelOpen() === false &&
      /#lockscreen \.lockscreen-auth\.lockscreen-auth-closed \{[^}]*visibility:\s*hidden !important/.test(CSS));
    check('pin: panel starts closed', h.ls.auth.isPanelOpen() === false, JSON.stringify({panelOpen:h.ls.panelOpen, authHidden:h.els.auth.hidden, padHidden:h.els.pad.hidden, mode:h.ls.auth.effectiveMode, cls:h.els.auth.className}));
    check('pin: hint names the PIN screen', /tap the lockhead to open PIN keypad/.test(h.els.hint.textContent), h.els.hint.textContent);
    await swipe(h, 700, 380);
    check('pin: swipe opens the panel', h.ls.panelOpen === true && h.els.auth.hidden === false && h.els.root.classList.contains('lockscreen-panel-open'));
    check('pin: swipe did NOT request an unlock', h.ctl.panelRequests.length === 0 && h.ls.isLocked() === true);
    check('pin: opening the panel did not call host unlock', h.unlockCalls.length === 0);
    check('pin: keypad visible in the open panel', h.els.pad.hidden === false && h.els.pat.hidden === true);
    check('pin: PIN button hidden on the PIN screen', h.els.fb.hidden === true);
    const r = await h.ls.auth.enterPin('3838');
    check('pin: 3838 unlocks via the credential path', r && r.ok === true && h.ctl.credentialUnlocks[0] === 'pin' && h.ls.isLocked() === false);
    check('pin: credential path also released the native lock', h.unlockCalls.length === 1);
  }
  {
    const h = await boot('pin');
    await tap(h, 600);
    check('pin: tapping the lockhead opens the panel too', h.ls.panelOpen === true && h.els.pad.hidden === false);
  }
  {
    const h = await boot('pin');
    await swipe(h, 600, 330);  // panel opens; the contact crossed the panel
    check('pin: opening swipe swallowed (no stray keypad tap)', h.ls.isLocked() === true && h.ctl.panelRequests.length === 0);
  }

  // ------------------------------------------------------------ pattern ----
  {
    const h = await boot('pattern');
    check('pattern: lockhead visible, matrix hidden until used', h.els.wrap.hidden === false && h.els.pat.hidden === true && h.ls.auth.isPanelOpen() === false);
    await swipe(h, 700, 380);
    check('pattern: swipe opens the matrix panel', h.ls.panelOpen === true && h.els.pat.hidden === false && h.els.pad.hidden === true);
    check('pattern: PIN fallback button offered', h.els.fb.hidden === false);
    check('pattern: matrix is centred by CSS (margin:auto in a centred flex panel)',
      /\.lockscreen-pattern\s*\{[^}]*margin:\s*auto/.test(CSS) &&
      /lockscreen-panel-open \.lockscreen-auth\s*\{[^}]*justify-content:\s*center/.test(CSS));
    check('pattern: PIN button pinned below the matrix, above the dock',
      /\.lockscreen-pin-fallback\s*\{[^}]*bottom:\s*152px/.test(CSS));
    h.ls.auth.showPinFallback();
    check('pattern: the PIN button switches to the keypad in place', h.els.pad.hidden === false && h.els.pat.hidden === true && h.ls.panelOpen === true);
    const r = await h.ls.auth.enterPin('3838');
    check('pattern: PIN fallback unlocks with 3838', r && r.ok === true && h.ctl.credentialUnlocks[0] === 'pin');
  }

  // -------------------------------------------------------- fingerprint ----
  {
    const h = await boot('fingerprint');
    check('fingerprint: lockhead visible', h.els.wrap.hidden === false);
    check('fingerprint: no matcher -> the auth surface renders the PIN screen from the start',
      h.ls.auth.effectiveMode === 'pin' && h.els.fp.hidden === true);
    await swipe(h, 700, 380);
    check('fingerprint: no matcher -> the lockhead opens the PIN screen',
      h.ls.panelOpen === true && h.els.pad.hidden === false && h.els.fp.hidden === true);
  }
  {
    const h = await boot('fingerprint', { status: { fingerprint: { provider_ready: true, enrolled: true } } });
    await swipe(h, 700, 380);
    check('fingerprint: with a ready matcher the scanner surface opens',
      h.ls.panelOpen === true && h.els.fp.hidden === false && h.els.pad.hidden === true);
    check('fingerprint: PIN button stays under the scanner', h.els.fb.hidden === false);
    h.ls.auth.showPinFallback();
    check('fingerprint: PIN button opens the PIN screen', h.els.pad.hidden === false && h.els.fp.hidden === true);
  }

  // ---------------------------------------------------- panel + lockhead ---
  {
    const h = await boot('pin');
    await swipe(h, 700, 380);
    h.geo.panel = { top: 120 };
    h.geo.handle = { top: 660, size: 84 };
    h.ls._positionHandle();
    const hb = h.els.wrap.getBoundingClientRect();
    const a = h.els.auth.getBoundingClientRect();
    check('docked lockhead sits BELOW the open panel (no keypad overlap)', hb.top >= a.bottom,
      JSON.stringify({ handleTop: hb.top, panelBottom: a.bottom }));
    check('docked lockhead is inside the glass', hb.bottom <= VH);
    // Start ON the docked lockhead (inside the panel rect a press is correctly
    // ignored), then swipe down.  The dock hand-off is simulated (real
    // transitions are covered by the A45 harness + live acceptance).
    h.ls.panelOpen = false; h.ls.auth.panelOpen = false;
    h.els.auth.classList.add('lockscreen-auth-closed');
    await swipe(h, 670, 740);
    check('swiping the docked lockhead down closes the panel', h.ls.panelOpen === false && h.ls.isLocked() === true);
    check('closing the panel never unlocks', h.ctl.panelRequests.length === 0);
  }
  {
    const h = await boot('pin');
    h.ls.auth.cancelToLockhead();
    check('Cancel returns to the lockhead-only glass', h.ls.panelOpen === false && h.ls.isLocked() === true);
  }
  {
    /* A drag that starts on the LOCKHEAD (panel open) and releases downward
       closes the panel and keeps the session locked. */
    const h = await boot('pin');
    await tap(h, 620);                    // lockhead tap opens the panel
    await new Promise((r) => setTimeout(r, 220));  // let the snap-back settle
    check('setup: panel open before the close-swipe', h.ls.panelOpen === true && h.ls.state === 'IDLE');
    const ev = (t, y) => new h.w.PointerEvent(t, { bubbles: true, cancelable: true, pointerId: 3, button: 0, clientX: 180, clientY: y });
    h.w.__dispatch(h.els.handle, ev('pointerdown', 620));
    h.w.__dispatch(h.w, ev('pointermove', 700));
    h.w.__dispatch(h.w, ev('pointerup', 740));
    await flush(h.w);
    check('down-swipe on the lockhead closes the panel', h.ls.panelOpen === false && h.ls.auth.isPanelOpen() === false);
    check('closing with a down-swipe never unlocks', h.ls.isLocked() === true && h.ctl.panelRequests.length === 0);
  }

  // ------------------------------------------------------ static contract --
  check('lockscreen.js never hides the handle for a credentialed mode',
    !/_hideSwipeHandle\b/.test(LOCKS) && /_applyHandleDock\(\)/.test(LOCKS) && /visible = true;/.test(LOCKS));
  check('auth surface reports panel state', /isPanelOpen\(\)/.test(AUTH));
  check('Settings exposes the four lock presets', ['unlock', 'pin', 'pattern', 'fingerprint']
    .every((k) => SETHTML.indexOf('id="sec-preset-' + k + '"') >= 0));
  check('Settings sends apply-preset to the bridge', /call\('security', 'apply-preset'/.test(SETJS));
  check('Settings pattern fallback PIN field present', /id="sec-pattern-pin"/.test(SETHTML));
  check('app.js commits credentials through one path', /_commitVerifiedUnlock/.test(APP) && /completeCredentialUnlock/.test(APP));
  check('lockscreen index cache-busts the a88 bundle', /lockscreen\.js\?v=a88/.test(HTML) && /lockscreen\.css\?v=a88/.test(HTML));

  console.log('');
  console.log(failures === 0 ? 'A84 MODES: ALL PASS (' + checks + ')' : 'A84 MODES: ' + failures + ' FAILURE(S) of ' + checks);
  process.exit(failures === 0 ? 0 : 1);
})().catch((e) => { console.error('HARNESS ERROR', e && e.stack || e); process.exit(2); });
