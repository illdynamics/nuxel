import { makeEnv } from './harness.js';

const BASE = new URL('../pwa/nuxel-home/js/', import.meta.url).href;

async function load(env, file) {
  const src = await Deno.readTextFile(new URL(BASE + file));
  // Evaluate in the fake window: the scripts are IIFEs taking `window`.
  const fn = new Function('window', 'document', 'console', 'fetch', 'URL',
    src + '\n//# sourceURL=' + file);
  fn(env.window, env.doc, env.window.console, env.window.fetch, URL);
}

let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra === undefined ? '' : ' :: ' + JSON.stringify(extra)));
  if (!cond) failures++;
}

async function scenario(mode, opts) {
  const env = makeEnv(Object.assign({ mode }, opts || {}));
  const w = env.window;
  const realLock = env.window.__realSecurityLock ? null : null;
  await load(env, 'security-lock.js');
  await load(env, 'lockscreen.js');
  // Prove the real module answered (not a test double).
  if (env.window.NuxelSecurityLock && !env.window.NuxelSecurityLock.unlockSwipe) throw new Error('real security-lock.js not loaded');
  await load(env, 'lockscreen-auth.js');
  check(mode + ': NuxelLockscreen exported', typeof w.NuxelLockscreen === 'function');
  const ls = new w.NuxelLockscreen();
  // emulate a boot lock: the element is visible and the session is locked
  // the page's #lockscreen is the live element
  ls.el = env.els.get('lockscreen');
  ls.handle = env.els.get('lockscreen-handle');
  ls.wrap = env.els.get('lockscreen-handle-wrap');
  ls.hint = env.els.get('lockscreen-hint');
  ls.el.hidden = false;
  ls._bound = false;
  ls.gesture = null; ls.state = 'IDLE'; ls.locked = false;
  ls._bindHandle();
  ls.show('boot');
  await new Promise((r) => setTimeout(r, 0)); // flush show()'s promises
  // Simulate the app.js controller pieces that decide swipe behaviour.
  // Extract the REAL app.js controller helpers (single realm: evaluated in
  // the fake window) so this test runs the shipping code, not a copy.
  const appSrc = await Deno.readTextFile(new URL(BASE + 'app.js'));
  function extractMethod(src, name) {
    const i = src.indexOf('    ' + name + '(');
    if (i < 0) throw new Error('method not found: ' + name);
    const b = src.indexOf('{', i);
    let d = 0, e = -1;
    for (let k = b; k < src.length; k++) {
      if (src[k] === '{') d++;
      else if (src[k] === '}') { d--; if (d === 0) { e = k + 1; break; } }
    }
    return src.slice(i + 4, e).trim();
  }
  const parts = ['_resolveLockMode', 'applySecurityModeChange', 'unlockFromLockscreen', 'completeCredentialUnlock']
    .map((n) => extractMethod(appSrc, n)).join(',\n');
  const NuxelHome = new Function('window', 'return ({' + parts + '});')(w);
  NuxelHome.lockscreen = ls;
  NuxelHome._lastLockMode = null;
  NuxelHome._inputTrace = () => {};
  NuxelHome._setNavDock = () => {};
  NuxelHome._enterHomeAfterUnlock = function () { this.wentHome = true; };
  NuxelHome._unlock = function () { ls.hide(); this.wentHome = true; return { ok: true }; };
  const home = NuxelHome;
  // gesture through the real drag state machine
  // Provide the app.js helpers on the fake window so the extracted method
  // resolves them exactly like the page does.
  w.__resolveLockMode = NuxelHome._resolveLockMode.bind(NuxelHome);
  w.__inputTrace = NuxelHome._inputTrace.bind(NuxelHome);
  w.__setNavDock = NuxelHome._setNavDock.bind(NuxelHome);
  w.__enterHomeAfterUnlock = NuxelHome._enterHomeAfterUnlock.bind(NuxelHome);
  w.__unlock = NuxelHome._unlock.bind(NuxelHome);

  const handle = env.els.get('lockscreen-handle');
  const down = handle.listeners['pointerdown'][0];
  down({ isTrusted: true, pointerId: 1, button: 0, clientX: 180, clientY: 690, preventDefault() {} });
  handle.listeners['pointermove'][0]({ isTrusted: true, pointerId: 1, clientX: 180, clientY: 420 });
  handle.listeners['pointerup'][0]({ isTrusted: true, pointerId: 1, clientX: 180, clientY: 400 });
  for (let i = 0; i < 10; i++) await new Promise((r) => setTimeout(r, 0));
  return { env, ls, home };
}

// 1. swipe mode: the swipe unlocks directly
{
  const { ls, home, env } = await scenario('swipe');
  check('swipe: session unlocked by the swipe', env.state.locked === false, env.state.calls);
  check('swipe: lockscreen hidden', env.els.get('lockscreen').hidden === true);
  check('swipe: Home transition ran', home.wentHome === true, home.unlockReason);
  check('swipe: handle visible on the glass', env.els.get('lockscreen-handle-wrap').hidden !== true);
}
// 2. pin mode: swipe reveals keypad, does NOT unlock
{
  const { ls, home, env } = await scenario('pin');
  check('pin: still locked after swipe', env.state.locked === true, env.state.calls);
  check('pin: keypad visible', !!(ls.auth && ls.auth.isVisible()) && env.els.get('lockscreen-pinpad').hidden === false && env.els.get('lockscreen-auth').hidden === false, { vis: ls.auth && ls.auth.isVisible(), padHidden: env.els.get('lockscreen-pinpad').hidden, authHidden: env.els.get('lockscreen-auth').hidden });
  check('pin: handle still on the glass (always swipe first)', env.els.get('lockscreen-handle-wrap').hidden !== true);
  check('pin: no unlock happened', home.wentHome !== true);
  // wrong pin refused
  ls.auth.enterPin('1234'); for (let i = 0; i < 5; i++) await new Promise((r) => setTimeout(r, 0));
  check('pin: wrong PIN keeps locked', env.state.locked === true);
  // correct pin unlocks
  ls.auth.enterPin('3838'); for (let i = 0; i < 5; i++) await new Promise((r) => setTimeout(r, 0));
  check('pin: 3838 unlocks', env.state.locked === false);
  check('pin: lockscreen hidden after code', env.els.get('lockscreen').hidden === true);
}
// 3. pattern mode: swipe reveals the pattern centred, PIN fallback works
{
  const { ls, home, env } = await scenario('pattern', { pinFallbackSet: true });
  check('pattern: still locked after swipe', env.state.locked === true);
  const pat = env.els.get('lockscreen-pattern');
  const pad = env.els.get('lockscreen-pinpad');
  check('pattern: matrix visible', pat.hidden === false, pat.hidden);
  check('pattern: keypad hidden until PIN pressed', pad.hidden === true);
  check('pattern: mode class for centred backdrop', env.els.get('lockscreen').classList.contains('lockscreen-mode-pattern'), { cls: env.els.get('lockscreen').className, cred: env.els.get('lockscreen').classList.contains('lockscreen-credentialed'), vis: ls.auth.isVisible(), mode: ls.mode });
  ls.auth.showPinFallback();
  check('pattern: PIN button reveals keypad', pad.hidden === false);
  ls.auth.enterPin('3838'); for (let i = 0; i < 5; i++) await new Promise((r) => setTimeout(r, 0));
  check('pattern: PIN fallback 3838 unlocks', env.state.locked === false && env.state.calls.some((c) => c[1] === 'unlock'), env.state.calls.filter((c) => c[1] === 'unlock'));
}
// 4. fingerprint mode with provider + pin fallback
{
  const { ls, env } = await scenario('fingerprint', { fpReady: true, fpEnrolled: true });
  check('fp: still locked after swipe', env.state.locked === true);
  check('fp: scanner visible', env.els.get('lockscreen-fingerprint').hidden === false);
  check('fp: swiping did not unlock', env.state.locked === true && env.state.calls.every((c) => c[1] !== 'unlock' || c[0] === 'host'));
  ls.auth.showPinFallback();
  check('fp: PIN button goes to pin screen', env.els.get('lockscreen-pinpad').hidden === false);
}
console.log(failures === 0 ? '\nALL PASS' : '\n' + failures + ' FAILURE(S)');
if (failures) Deno.exit(1);
