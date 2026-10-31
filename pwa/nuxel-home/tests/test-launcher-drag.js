// PWNAGE-44000 Home drag pointer-lifecycle regression test.
// Drives the REAL Launcher methods (not a reimplementation) with a DOM-light
// harness: long-press fires once, movement cancels it, pointer capture is owned
// by the stable grid, secondary contacts are ignored, and cancel rolls back.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}
const src = fs.readFileSync(path.join(__dirname, '../js/launcher.js'), 'utf8');
const classSrc = src.slice(src.indexOf('class Launcher'), src.lastIndexOf("document.addEventListener('DOMContentLoaded'"));

const grid = {
  captured: null,
  setPointerCapture(id) { this.captured = id; },
  releasePointerCapture(id) { if (this.captured === id) this.captured = null; },
};
const sandbox = {
  console: { log() {}, warn() {} },
  document: {
    getElementById: id => id === 'app-grid' ? grid : null,
    documentElement: grid,
    addEventListener() {}, querySelectorAll() { return []; },
    body: { classList: { add() {}, remove() {} } },
    elementFromPoint() { return null; },
  },
  window: { PointerEvent: true, innerWidth: 360 },
  localStorage: { getItem() { return null; }, setItem() {} },
  setTimeout, clearTimeout, Date, Math, JSON, Object, Number, String, Array, Set,
};
sandbox.window = Object.assign(sandbox.window, sandbox);
vm.createContext(sandbox);
vm.runInContext(classSrc + '\nthis.__Launcher = Launcher;', sandbox);

function makeLauncher() {
  const l = Object.create(sandbox.__Launcher.prototype);
  Object.assign(l, {
    longPressTimer: null, hasMoved: false, dragTarget: null, dragState: 'IDLE',
    pressedPointer: null, dragStartX: 0, dragStartY: 0, dragStartTime: 0,
    lastPointerX: 0, lastPointerY: 0, isDragging: false, pointerCaptureEl: null,
    _capturedPointer: null, drawerOpen: false, drawerHold: false, editMode: false,
    settings: { homeLocked: false }, starts: 0, ends: 0,
    _enterEditMode() {}, _selectForEdit() {},
    _startDrag(item, e) { this.starts++; this._capturePointer(e.pointerId); },
    _endDrag() { this.ends++; this.isDragging = false; },
    _lockedNotice() {},
  });
  return l;
}
function item() {
  return { dataset: { appId: 'app.test' }, closest(sel) { return sel === '.app-item' ? this : null; } };
}
function ev(x, y, id, extra) {
  const target = item();
  return Object.assign({ pointerId: id, isPrimary: true, button: 0, clientX: x, clientY: y,
    target: { closest(sel) { return sel === '.app-item' ? target : null; } } }, extra || {});
}
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

(async () => {
  const l = makeLauncher();
  l._onPointerDown(ev(10, 10, 1));
  check('primary press enters PRESS_PENDING', l.dragState === 'PRESS_PENDING' && l.pressedPointer === 1);
  await wait(480);
  check('stationary 450ms hold starts exactly one drag', l.starts === 1 && l.isDragging === false);
  check('pointer capture is taken on the stable grid', grid.captured === 1);
  l._cancelPointer(1);
  check('cancel releases pointer capture', grid.captured === null && l.pressedPointer === null);

  const m = makeLauncher();
  m._onPointerDown(ev(10, 10, 1));
  m._onPointerMove(ev(30, 10, 1));
  await wait(480);
  check('movement before the hold cancels the timer', m.starts === 0 && m.hasMoved === true);

  const s = makeLauncher();
  s._onPointerDown(ev(10, 10, 1));
  s._onPointerDown(ev(50, 50, 2));
  await wait(480);
  check('secondary contact does not cancel or hijack the primary', s.starts === 1 && s.pressedPointer === 1);

  const c = makeLauncher();
  c.isDragging = true; c.pressedPointer = 1; c.dragTarget = item();
  c._onPointerUp(ev(10, 10, 2));
  check('secondary pointerup cannot end the primary drag', c.ends === 0 && c.isDragging === true);
  c._onPointerUp(ev(10, 10, 1));
  check('primary pointerup ends the drag exactly once', c.ends === 1 && c.isDragging === false);

  const r = makeLauncher();
  r.isDragging = true; r.pressedPointer = 1; r.dragTarget = item();
  r._cancelPointer(1);
  check('pointercancel rolls back through _endDrag(cancelled) once', r.ends === 1 && r.pressedPointer === null);

  check('lostpointercapture is bound', src.indexOf("addEventListener('lostpointercapture'") >= 0);
  check('drag hit-testing uses elementFromPoint', src.indexOf('document.elementFromPoint(e.clientX, e.clientY)') >= 0);
  check('single pointer source (no second drag framework)', (src.match(/class Launcher/g) || []).length === 1);
  process.exit(failures ? 1 : 0);
})();
