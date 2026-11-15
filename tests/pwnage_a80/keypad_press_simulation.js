const fs = require('fs');
let JSDOM;
try { JSDOM = require('jsdom').JSDOM; }
catch (e) { JSDOM = require('/tmp/jsdomtest/node_modules/jsdom').JSDOM; }
const REPO = require('path').resolve(__dirname, '../..');
const src = fs.readFileSync(REPO + '/pwa/nuxel-home/js/lockscreen-auth.js', 'utf8');
const ids = ['lockscreen-auth','lockscreen-pattern','lockscreen-pattern-svg','lockscreen-pattern-trail',
  'lockscreen-pattern-dots','lockscreen-pinpad','lockscreen-pin-display','lockscreen-fingerprint',
  'lockscreen-fingerprint-status','lockscreen-fingerprint-ring','lockscreen-fingerprint-art',
  'lockscreen-pin-fallback','lockscreen-auth-title','lockscreen-auth-hint','lockscreen-auth-error'];
const idsSet = ids.filter(i => i !== 'lockscreen-pinpad');
let digits = '';
let html = '<!doctype html><html><body>' + idsSet.map(i => `<div id="${i}"></div>`).join('');
html += '<div id="lockscreen-pinpad"><div class="lockscreen-pin-grid">';
for (let i = 0; i <= 9; i++) html += `<button class="lockscreen-key" data-pin="${i}">${i}</button>`;
html += '</div><button class="lockscreen-key" id="lockscreen-pin-enter">Unlock</button>';
html += '<button class="lockscreen-key" id="lockscreen-pin-del">del</button></div></body></html>';

function run(label, simulate) {
  const dom = new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  if (!w.PointerEvent) w.PointerEvent = class PointerEvent extends w.MouseEvent { constructor(t, o) { super(t, o); Object.assign(this, { pointerId: (o||{}).pointerId, pointerType: (o||{}).pointerType }); } };
  if (!w.TouchEvent) w.TouchEvent = class TouchEvent extends w.Event {};
  w.NuxelSecurityLock = { call: (ns, verb, p) => { if (verb === 'unlock') digits = (p && p.secret) || ''; return Promise.resolve({ success: false }); } };
  w.eval(src);
  const auth = new w.NuxelLockscreenAuth({});
  auth.effectiveMode = 'pin';
  /* A88: the keyboard path only claims a real PIN panel that is open. */
  auth.panelOpen = true;
  const key = w.document.querySelector('[data-pin="3"]');
  simulate(w, key, auth);
  // the no-release fallback fires at 500 ms; give every case 650 ms
  return new Promise(r => setTimeout(() => r(auth.pin), 650));
}

(async () => {
  const cases = {
    // the exact sequence that produced "33" on the device
    'full touch press (pointerdown,touchstart,pointerup,touchend,click)': (w,k,a) => {
      k.dispatchEvent(new w.PointerEvent('pointerdown',{bubbles:true,pointerId:1,pointerType:'touch'}));
      k.dispatchEvent(new w.TouchEvent('touchstart',{bubbles:true}));
      k.dispatchEvent(new w.PointerEvent('pointerup',{bubbles:true,pointerId:1,pointerType:'touch'}));
      k.dispatchEvent(new w.TouchEvent('touchend',{bubbles:true}));
      k.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
    },
    // retargeted contact ids per press (the old dedup key)
    'press with pointerId 2147483647': (w,k,a) => {
      k.dispatchEvent(new w.PointerEvent('pointerdown',{bubbles:true,pointerId:2147483647,pointerType:'touch'}));
      k.dispatchEvent(new w.PointerEvent('pointerup',{bubbles:true,pointerId:2147483647,pointerType:'touch'}));
      k.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
    },
    'click only (trusted tap)': (w,k) => k.dispatchEvent(new w.MouseEvent('click',{bubbles:true})),
    // an input path that never delivers click/touchend/pointerup at all
            'keydown only (keyboard)': (w,k,a) => { a.pin = ''; w.dispatchEvent(new w.KeyboardEvent('keydown',{key:'3',bubbles:true})); },
  };
  let fail = 0;
  for (const [n, f] of Object.entries(cases)) {
    const pin = await run(n, f);
    const expect = n.startsWith('click only') || n.startsWith('full') || n.startsWith('press') || n.startsWith('pointer') ? '3' : '3';
    const ok = pin === expect;
    if (!ok) fail++;
    console.log((ok ? 'PASS ' : 'FAIL ') + n + ' -> pin="' + pin + '" (expected "' + expect + '")');
  }
  // two quick physical presses must be two digits
  const dom = new JSDOM(html, { runScripts: 'outside-only' });
  const w = dom.window;
  w.PointerEvent = class PointerEvent extends w.MouseEvent { constructor(t, o) { super(t, o); Object.assign(this, { pointerId: (o||{}).pointerId, pointerType: (o||{}).pointerType }); } };
  w.TouchEvent = class TouchEvent extends w.Event {};
  w.NuxelSecurityLock = { call: () => Promise.resolve({success:false}) };
  w.eval(src);
  const a = new w.NuxelLockscreenAuth({}); a.effectiveMode = 'pin';
  const k = w.document.querySelector('[data-pin="5"]');
  for (let i = 0; i < 2; i++) {
    k.dispatchEvent(new w.PointerEvent('pointerdown',{bubbles:true,pointerId:i,pointerType:'touch'}));
    k.dispatchEvent(new w.TouchEvent('touchstart',{bubbles:true}));
    k.dispatchEvent(new w.PointerEvent('pointerup',{bubbles:true,pointerId:i,pointerType:'touch'}));
    k.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
    await new Promise(r => setTimeout(r, 120));
  }
  const two = a.pin === '55'; if (!two) fail++;
  console.log((two ? 'PASS ' : 'FAIL ') + 'two quick presses -> pin="' + a.pin + '" (expected "55")');
  // a press that is held and then released WITHOUT a click must not count
  const held = await (async () => {
    const dom = new JSDOM(html, { runScripts: 'outside-only' });
    const w = dom.window;
    w.PointerEvent = class PointerEvent extends w.MouseEvent { constructor(t, o) { super(t, o); Object.assign(this, { pointerId: (o||{}).pointerId, pointerType: (o||{}).pointerType }); } };
    w.TouchEvent = class TouchEvent extends w.Event {};
    w.NuxelSecurityLock = { call: () => Promise.resolve({success:false}) };
    w.eval(src);
    const a = new w.NuxelLockscreenAuth({}); a.effectiveMode = 'pin';
    const k = w.document.querySelector('[data-pin="5"]');
    k.dispatchEvent(new w.PointerEvent('pointerdown',{bubbles:true,pointerId:0,pointerType:'touch'}));
    k.dispatchEvent(new w.TouchEvent('touchstart',{bubbles:true}));
    await new Promise(r => setTimeout(r, 450));           // finger held > fallback
    k.dispatchEvent(new w.PointerEvent('pointerup',{bubbles:true,pointerId:0,pointerType:'touch'}));
    k.dispatchEvent(new w.TouchEvent('touchend',{bubbles:true}));
    k.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));   // release counts once
    await new Promise(r => setTimeout(r, 50));
    return a.pin;
  })();
  const heldOk = held === '5'; if (!heldOk) fail++;
  console.log((heldOk ? 'PASS ' : 'FAIL ') + 'held press then release -> pin="' + held + '" (expected "5")');
  console.log(fail ? 'HARNESS: ' + fail + ' FAILURE(S)' : 'HARNESS: ALL PASS');
  process.exit(fail ? 1 : 0);
})();
