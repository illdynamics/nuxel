#!/usr/bin/env node
// A45.1 Penguin unlock regression harness.
//
// These are MOCKED, OFFLINE checks of the shipped launcher sources.  They prove
// the gesture/state/controller logic; they do NOT prove that phoc/Wayland,
// WebKitGTK or the panel changed.  The live USB integration run is separate and
// is recorded in the acceptance report.
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '../../..');
const LOCKS_JS = path.join(ROOT, 'pwa/nuxel-home/js/lockscreen.js');
const APP_JS = path.join(ROOT, 'pwa/nuxel-home/js/app.js');
const INDEX_HTML = path.join(ROOT, 'pwa/nuxel-home/index.html');
const BUTTON_MANAGER_C = path.join(ROOT, 'tools/s10plus/a45/nuxel-button-manager.c');

let checks = 0;
let failures = 0;
function check(name, condition, detail) {
  checks++;
  console.log((condition ? 'PASS ' : 'FAIL ') + '[MOCK] ' + name +
              (condition || detail === undefined ? '' : '  ' + detail));
  if (!condition) failures++;
}

function classList() {
  const set = new Set();
  return {
    add(...names) { names.forEach(n => set.add(n)); },
    remove(...names) { names.forEach(n => set.delete(n)); },
    contains(name) { return set.has(name); },
    values() { return Array.from(set); },
  };
}

function target() {
  const handlers = {};
  return {
    handlers,
    addEventListener(type, fn) { (handlers[type] = handlers[type] || []).push(fn); },
    removeEventListener(type, fn) {
      handlers[type] = (handlers[type] || []).filter(h => h !== fn);
    },
    dispatch(type, event) {
      (handlers[type] || []).slice().forEach(fn => fn(event || {}));
      return true;
    },
  };
}

function element(id, top, size) {
  const el = target();
  el.id = id;
  el.hidden = false;
  el.textContent = '';
  el.style = {};
  el.classList = classList();
  el._top = top === undefined ? 0 : top;
  el._size = size === undefined ? 118 : size;
  el.getBoundingClientRect = function () {
    return { top: this._top, left: 0, width: this._size, height: this._size };
  };
  el.setPointerCapture = function (pointerId) { this.captured = pointerId; };
  el.releasePointerCapture = function (pointerId) {
    this.releasedCapture = pointerId;
    if (this.captured === pointerId) this.captured = null;
  };
  return el;
}

function makeHarness(options) {
  options = options || {};
  const timers = [];
  const intervals = [];
  let timerSeq = 1;

  const els = {
    lockscreen: element('lockscreen'),
    'lockscreen-handle': element('lockscreen-handle', 579, 118),
    'lockscreen-handle-wrap': element('lockscreen-handle-wrap', 579, 118),
    'lockscreen-hint': element('lockscreen-hint'),
    'lockscreen-time': element('lockscreen-time'),
    'lockscreen-date': element('lockscreen-date'),
    'lockscreen-battery': element('lockscreen-battery'),
    launcher: element('launcher'),
  };
  const documentTarget = target();
  const doc = Object.assign(documentTarget, {
    hidden: false,
    body: { dataset: {} },
    activeElement: null,
    getElementById(id) { return els[id] || null; },
    querySelectorAll() { return []; },
    elementFromPoint() { return els.lockscreen.hidden ? els.launcher : els['lockscreen-handle']; },
    dispatchEvent() { return true; },
  });

  const hostCalls = [];
  const hostState = { wlfb: options.wlfb || 'DISPLAY_ON', unlockResult: options.unlockResult || { ok: true, action: 'unlock' } };
  const host = options.host || {
    available: options.hostAvailable !== false,
    action(action) {
      hostCalls.push(action);
      if (action === 'unlock') return Promise.resolve(hostState.unlockResult);
      return Promise.resolve({ ok: true, action: action });
    },
    statusRead(name) {
      hostCalls.push('status:' + name);
      return Promise.resolve({ ok: true, text: hostState.wlfb });
    },
  };

  const sandbox = {
    console: options.quiet ? { log() {}, warn() {}, error() {} } : console,
    document: doc,
    navigator: { vibrate() {} },
    location: { search: options.search || '?boot=os' },
    webkit: undefined,
    NuxelHost: host,
    Promise, Date, Object, Number, String, Math, JSON, RegExp, Error,
    URLSearchParams,
    setTimeout(fn, ms) {
      const id = timerSeq++;
      timers.push({ id, fn, ms });
      return id;
    },
    clearTimeout(id) {
      const i = timers.findIndex(t => t.id === id);
      if (i >= 0) timers.splice(i, 1);
    },
    setInterval(fn, ms) {
      const id = timerSeq++;
      intervals.push({ id, fn, ms });
      return id;
    },
    clearInterval(id) {
      const i = intervals.findIndex(t => t.id === id);
      if (i >= 0) intervals.splice(i, 1);
    },
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.addEventListener = documentTarget.addEventListener;
  sandbox.removeEventListener = documentTarget.removeEventListener;
  sandbox.dispatch = documentTarget.dispatch;
  documentTarget.handlers = documentTarget.handlers;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(LOCKS_JS, 'utf8'), sandbox, { filename: 'lockscreen.js' });
  if (options.withApp) {
    vm.runInContext(fs.readFileSync(APP_JS, 'utf8'), sandbox, { filename: 'app.js' });
  }

  async function microtasks() {
    for (let i = 0; i < 8; i++) await Promise.resolve();
  }
  async function flushTimers(max) {
    max = max || 20;
    for (let i = 0; i < max && timers.length; i++) {
      const t = timers.shift();
      t.fn();
      await microtasks();
    }
  }
  async function flushIntervals() {
    (intervals.slice()).forEach(i => i.fn());
    await microtasks();
  }

  return {
    sandbox, els, doc, host, hostState, hostCalls, timers, intervals,
    microtasks, flushTimers, flushIntervals,
  };
}

function makeController(ls, mode) {
  const requests = [];
  const controller = {
    requests,
    unlockFromLockscreen(instance, request) {
      requests.push(request);
      if (instance !== ls) return Promise.resolve({ ok: false, error: 'inactive-lockscreen' });
      if (!instance.acceptGestureUnlock(request)) {
        return Promise.resolve({ ok: false, error: 'invalid-or-replayed-gesture' });
      }
      if (mode === 'error') return Promise.resolve({ ok: false, error: 'backend-unlock-failed' });
      if (mode === 'reject') return Promise.reject(new Error('backend exploded'));
      return Promise.resolve({ ok: true, state: 'UNLOCKED' });
    },
  };
  return controller;
}

async function gesture(h, options) {
  options = options || {};
  const handle = h.els['lockscreen-handle'];
  const id = options.pointerId || 7;
  const startY = options.startY === undefined ? 547 : options.startY;
  const points = options.points || [startY];
  const base = { isTrusted: true, pointerId: id, button: 0, clientX: 180 };
  handle.dispatch('pointerdown', Object.assign({}, base, { clientY: startY }));
  for (const y of points) {
    h.sandbox.dispatch('pointermove', Object.assign({}, base, { clientY: y }));
  }
  if (options.cancel) {
    h.sandbox.dispatch('pointercancel', Object.assign({}, base, { clientY: points[points.length - 1] }));
  } else if (options.releaseOutside) {
    h.sandbox.dispatch('pointerup', Object.assign({}, base, { clientY: points[points.length - 1] }));
  } else {
    handle.dispatch('pointerup', Object.assign({}, base, { clientY: points[points.length - 1] }));
  }
  await h.microtasks();
  await h.flushTimers();
}

(async function main() {
  // 1. A small drag does not unlock.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    await gesture(h, { points: [520] }); // 27 px up, threshold ~167
    check('small drag remains locked', ls.isLocked() === true && h.els.lockscreen.hidden === false);
    check('small drag sends zero unlock requests', h.sandbox.nuxel.requests.length === 0);
    check('small drag snaps back to rest', h.els['lockscreen-handle'].style.transform === 'translateY(0)');
  }

  // 2. A sufficient upward drag unlocks.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    await gesture(h, { points: [500, 450, 400, 350, 300] }); // 247 px up
    check('sufficient upward drag requests unlock once', h.sandbox.nuxel.requests.length === 1);
    check('sufficient upward drag dismisses lockscreen', ls.isLocked() === false && h.els.lockscreen.hidden === true);
    check('request carries viewport-pixel distance and threshold',
          h.sandbox.nuxel.requests[0].distance === 247 && h.sandbox.nuxel.requests[0].threshold === 167,
          JSON.stringify(h.sandbox.nuxel.requests[0]));
    check('threshold is physically reachable above the resting lockhead',
          ls._effectiveThreshold() > 0 && ls._effectiveThreshold() <= ls.baseTop - 24,
          JSON.stringify({ threshold: ls._effectiveThreshold(), baseTop: ls.baseTop }));
  }

  // 2b. A coalesced swipe with no pointermove still evaluates the release point.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    const handle = h.els['lockscreen-handle'];
    const id = 11;
    handle.dispatch('pointerdown', { isTrusted: true, pointerId: id, button: 0, clientX: 180, clientY: 547 });
    handle.dispatch('pointerup', { isTrusted: true, pointerId: id, button: 0, clientX: 180, clientY: 300 });
    await h.microtasks();
    await h.flushTimers();
    check('release coordinate alone can complete a coalesced swipe', h.sandbox.nuxel.requests.length === 1 && ls.isLocked() === false);
  }

  // 3. Release outside the original lockhead hitbox still completes.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    await gesture(h, { points: [500, 400, 300], releaseOutside: true });
    check('release outside the icon bounds still unlocks', h.sandbox.nuxel.requests.length === 1 && ls.isLocked() === false);
    check('release outside dismisses the overlay', h.els.lockscreen.hidden === true);
  }

  // 4. Pointer cancellation does not unlock.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    await gesture(h, { points: [450, 350, 250], cancel: true });
    check('pointercancel never requests unlock', h.sandbox.nuxel.requests.length === 0);
    check('pointercancel remains locked and returns to rest',
          ls.isLocked() === true && h.els.lockscreen.hidden === false &&
          h.els['lockscreen-handle'].style.transform === 'translateY(0)');
  }

  // 4b. Losing capture before release is a cancellation, not an unlock.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    const handle = h.els['lockscreen-handle'];
    const base = { isTrusted: true, pointerId: 7, button: 0, clientX: 180, clientY: 250 };
    handle.dispatch('pointerdown', Object.assign({}, base, { clientY: 547 }));
    h.sandbox.dispatch('pointermove', base);
    handle.dispatch('lostpointercapture', base);
    await h.microtasks();
    await h.flushTimers();
    check('lostpointercapture never requests unlock', h.sandbox.nuxel.requests.length === 0);
    check('lostpointercapture remains locked and returns to rest',
          ls.isLocked() === true && h.els.lockscreen.hidden === false && ls.state === 'IDLE');
  }

  // 5. Downward movement does not unlock.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    await gesture(h, { points: [600, 650, 700] });
    check('downward movement never requests unlock', h.sandbox.nuxel.requests.length === 0);
    check('downward movement remains locked', ls.isLocked() === true && h.els.lockscreen.hidden === false);
  }

  // 6. A tap without an upward drag does not unlock.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    await gesture(h, { points: [547] });
    check('tap without drag never requests unlock', h.sandbox.nuxel.requests.length === 0);
    check('tap remains locked', ls.isLocked() === true && h.els.lockscreen.hidden === false);
  }

  // 7. Only one unlock request occurs per gesture.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    const handle = h.els['lockscreen-handle'];
    const base = { isTrusted: true, pointerId: 7, button: 0, clientX: 180, clientY: 300 };
    handle.dispatch('pointerdown', Object.assign({}, base, { clientY: 547 }));
    h.sandbox.dispatch('pointermove', base);
    handle.dispatch('pointerup', base);
    h.sandbox.dispatch('pointerup', base);
    handle.dispatch('lostpointercapture', base);
    h.sandbox.dispatch('pointercancel', base);
    handle.dispatch('pointerup', base);
    await h.microtasks();
    await h.flushTimers();
    check('duplicate release/cancel events produce exactly one request', h.sandbox.nuxel.requests.length === 1,
          h.sandbox.nuxel.requests.length);
  }

  // 8. Backend unlock errors do not falsely hide the lockscreen.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'error');
    ls.show('test');
    await gesture(h, { points: [400, 300] });
    check('backend error keeps the lockscreen mounted', h.els.lockscreen.hidden === false && ls.isLocked() === true);
    check('backend error returns the handle to rest', h.els['lockscreen-handle'].style.transform === 'translateY(0)');
    check('backend error leaves state IDLE for a retry', ls.state === 'IDLE', ls.state);
  }

  // 9. Successful backend acknowledgement dismisses the lockscreen.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('test');
    await gesture(h, { points: [400, 300] });
    check('successful acknowledgement hides the overlay and clears locked',
          h.els.lockscreen.hidden === true && ls.isLocked() === false && ls.state === 'UNLOCKED');
  }

  // 10. Locked state blocks interaction with ordinary applications.
  // 11. Unlocked session restores application input.
  // 12. The next Power-button lock still works.
  {
    const h = makeHarness({ withApp: true });
    const Home = h.sandbox.NuxelHome;
    class TestHome extends Home { _init() {} }
    const home = new TestHome();
    home.components = {};
    home._closeOverlays = () => {};
    home._inputTrace = () => {};
    let desktop = 0;
    h.sandbox.launcher = {
      currentPage: 2,
      mainDesktop() { desktop++; this.currentPage = 0; },
      closeDrawer() {}, exitEditMode() {},
    };
    let keyboardHide = 0;
    h.sandbox.NuxelTouchKeyboard = { hide() { keyboardHide++; }, show() {} };
    const ls = new h.sandbox.NuxelLockscreen();
    home.lockscreen = ls;
    h.sandbox.nuxel = home;
    ls.show('boot');

    home.home();
    check('locked state blocks Home/application interaction', desktop === 0, desktop);

    await gesture(h, { points: [400, 300] });
    check('gesture handoff reaches the launcher controller and dismisses',
          h.els.lockscreen.hidden === true && home._isLocked() === false,
          JSON.stringify({ hidden: h.els.lockscreen.hidden, locked: home._isLocked() }));
    check('native host unlock action was requested', h.hostCalls.indexOf('unlock') >= 0, h.hostCalls.join(','));

    home.home();
    check('unlocked session restores application interaction', desktop === 1, desktop);

    home._lock('power');
    check('next Power-button lock re-shows the lockscreen', home._isLocked() === true && h.els.lockscreen.hidden === false);
    check('Power-button lock still asks for panel off', h.hostCalls.filter(x => x === 'screen-off').length >= 1);
    check('Power-button lock hides the keyboard', keyboardHide >= 1);
  }

  // 13/14. Display-off re-locks; wake shows the lockscreen again.
  {
    const h = makeHarness({ withApp: true });
    const Home = h.sandbox.NuxelHome;
    class TestHome extends Home { _init() {} }
    const home = new TestHome();
    home.components = {};
    home._closeOverlays = () => {};
    home._inputTrace = () => {};
    const ls = new h.sandbox.NuxelLockscreen();
    home.lockscreen = ls;
    h.sandbox.nuxel = home;
    ls.show('boot');
    h.hostState.wlfb = 'FRAMES_OK total=100 display=on owner=nuxel-wl-fb';
    home._watchDisplayForLock();
    await h.microtasks(); // initial ON read

    h.hostState.wlfb = 'FRAMES_OK total=101 display=off owner=nuxel-wl-fb';
    await h.flushIntervals();
    check('real bridge display=off transition re-locks the session',
          home._isLocked() === true && h.els.lockscreen.hidden === false);

    h.hostState.wlfb = 'FRAMES_OK total=102 display=on owner=nuxel-wl-fb';
    await h.flushIntervals();
    check('subsequent wake keeps the lockscreen visible', home._isLocked() === true && h.els.lockscreen.hidden === false);

    // A stale OFF sample immediately after unlock must not re-lock.
    home._unlock('test');
    h.hostState.wlfb = 'FRAMES_OK total=103 display=off owner=nuxel-wl-fb';
    await h.flushIntervals();
    check('stale OFF after unlock does not immediately re-lock', home._isLocked() === false && h.els.lockscreen.hidden === true);

    // After the panel is observed ON again, the next OFF transition locks.
    h.hostState.wlfb = 'FRAMES_OK total=104 display=on owner=nuxel-wl-fb';
    await h.flushIntervals();
    h.hostState.wlfb = 'FRAMES_OK total=105 display=off owner=nuxel-wl-fb';
    await h.flushIntervals();
    check('next real display-off after wake locks again', home._isLocked() === true && h.els.lockscreen.hidden === false);

    const bm = fs.readFileSync(BUTTON_MANAGER_C, 'utf8');
    check('native idle timeout default is still 60000 ms', /idle_timeout_ms\s*=\s*60000/.test(bm));
    check('native idle timeout still reads screen-timeout.json', /IDLE_CFG/.test(bm) && /screen-timeout\.json/.test(bm));
    check('native timeout still emits IDLE_SCREEN_OFF', /IDLE_SCREEN_OFF/.test(bm));
  }

  // 15. Repeated lock/unlock cycles do not accumulate duplicate handlers.
  {
    const h = makeHarness({ withApp: true });
    const Home = h.sandbox.NuxelHome;
    class TestHome extends Home { _init() {} }
    const home = new TestHome();
    home.components = {};
    home._closeOverlays = () => {};
    home._inputTrace = () => {};
    const ls = new h.sandbox.NuxelLockscreen();
    home.lockscreen = ls;
    h.sandbox.nuxel = home;
    const handle = h.els['lockscreen-handle'];
    const downBefore = (handle.handlers.pointerdown || []).length;
    const winUpBefore = (h.doc.handlers.pointerup || []).length;
    for (let i = 0; i < 5; i++) {
      ls.show('cycle');
      await gesture(h, { points: [400, 300], pointerId: 20 + i });
      home._lock('cycle');
    }
    check('pointerdown handler count stays at one', (handle.handlers.pointerdown || []).length === downBefore,
          (handle.handlers.pointerdown || []).length);
    check('window pointerup handler count does not grow', (h.doc.handlers.pointerup || []).length === winUpBefore,
          (h.doc.handlers.pointerup || []).length);
    check('five cycles still issue exactly five unlock requests', h.hostCalls.filter(x => x === 'unlock').length === 5,
          h.hostCalls.filter(x => x === 'unlock').length);
  }

  // 16. Keyboard focus is usable after unlock (offline proxy; live check separate).
  {
    const h = makeHarness({ withApp: true });
    const Home = h.sandbox.NuxelHome;
    class TestHome extends Home { _init() {} }
    const home = new TestHome();
    home.components = {};
    home._closeOverlays = () => {};
    home._inputTrace = () => {};
    let focused = 0;
    const input = { focus() { focused++; h.doc.activeElement = input; } };
    h.sandbox.NuxelTouchKeyboard = { hide() {}, show() {} };
    const ls = new h.sandbox.NuxelLockscreen();
    home.lockscreen = ls;
    h.sandbox.nuxel = home;
    ls.show('boot');
    await gesture(h, { points: [400, 300] });
    input.focus();
    check('no lockscreen overlay remains after unlock', h.els.lockscreen.hidden === true);
    check('elementFromPoint reaches the launcher after unlock', h.doc.elementFromPoint(180, 300) === h.els.launcher);
    check('an application element can take focus after unlock', focused === 1 && h.doc.activeElement === input);
  }

  // 17. Cold boot still begins at the lockscreen.
  {
    const h = makeHarness();
    const ls = new h.sandbox.NuxelLockscreen();
    h.sandbox.nuxel = makeController(ls, 'ok');
    ls.show('boot');
    check('cold boot leaves the lockscreen mounted and locked', h.els.lockscreen.hidden === false && ls.isLocked() === true);

    const index = fs.readFileSync(INDEX_HTML, 'utf8');
    check('boot gate still keys on ?boot=os', /get\('boot'\)\s*!==\s*'os'/.test(index));
    check('lockscreen script uses the A45.1 cache-busting revision', /lockscreen\.js\?v=a451/.test(index));
    check('app controller uses the A45.1 cache-busting revision', /app\.js\?v=a451/.test(index));
  }

  console.log('\nNOTE: all checks above are MOCKED/OFFLINE.  Wayland/phoc/WebKitGTK');
  console.log('      integration and the physical panel are verified only by the live');
  console.log('      USB run and the owner acceptance test.\n');
  console.log(failures === 0 ? 'ALL PASS (' + checks + '/' + checks + ')' : failures + ' FAILURES (' + checks + ' checks)');
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => {
  console.error('HARNESS ERROR', err && err.stack || err);
  process.exit(2);
});
