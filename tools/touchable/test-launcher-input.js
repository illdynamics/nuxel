// Exercise the existing launcher event handlers, including dock hit targets.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const listeners = {};
const calls = [];
const sandbox = {
    document: { addEventListener(name, fn) { (listeners[name] ||= []).push(fn); } },
    window: { PointerEvent: function () {} },
    appRegistry: { launchApp(id) { calls.push(id); } },
    localStorage: { getItem() { return null; }, setItem() {} },
    setTimeout() { return 1; }, clearTimeout() {}, Date, console,
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../pwa/nuxel-home/js/launcher.js'), 'utf8') + '\nthis.LauncherClass=Launcher;', sandbox);
const proto = sandbox.LauncherClass.prototype;
const launcher = Object.create(proto);
Object.assign(launcher, { hasMoved: false, isDragging: false, dragTarget: null });
launcher._bindPointerEvents();
const item = (id, dock = false) => ({ dataset: { appId: id },
    closest(selector) { return selector === '.app-item' ? this : selector === '#dock-items' && dock ? {} : null; } });
const grid = item('nuxel-settings'), dock = item('nuxel-dialer', true);
const child = { closest(selector) { return grid.closest(selector); } };
function emit(kind, target, extra = {}) {
    const event = { target, clientX: 100, clientY: 200, pointerId: 1, isPrimary: true,
        button: 0, detail: 1, preventDefault() {}, ...extra };
    (listeners[kind] || []).forEach(fn => fn(event));
}
function tap(target) { emit('pointerdown', target); emit('pointerup', target); }
function test(label, fn) {
    calls.length = 0;
    try { fn(); console.log('PASS ' + label); }
    catch (err) { console.error('FAIL ' + label + ': ' + err.message); process.exitCode = 1; }
    if (launcher._cancelPointer) launcher._cancelPointer();
    launcher.dragTarget = null; launcher.hasMoved = false; launcher.isDragging = false;
}
test('grid child hit invokes the registered app once', () => { tap(child); assert.deepEqual(calls, ['nuxel-settings']); });
test('dock taps open their app', () => { tap(dock); assert.deepEqual(calls, ['nuxel-dialer']); });
test('cancel then release never opens an app', () => {
    emit('pointerdown', grid); emit('pointercancel', grid); emit('pointerup', grid); assert.equal(calls.length, 0);
});
test('release over a different icon does not launch', () => {
    emit('pointerdown', grid); emit('pointerup', dock); assert.equal(calls.length, 0);
});
test('motion is not a tap', () => {
    emit('pointerdown', grid); emit('pointermove', grid, { clientX: 180 }); emit('pointerup', grid); assert.equal(calls.length, 0);
});
test('secondary contact cannot release primary tap', () => {
    emit('pointerdown', grid); emit('pointerup', grid, { pointerId: 2, isPrimary: false }); assert.equal(calls.length, 0);
});
test('repeated taps reopen the same app without duplicate compatibility click', () => {
    for (let i = 0; i < 5; i++) { tap(grid); emit('click', grid); }
    assert.equal(calls.length, 5);
});
test('keyboard activation opens focused dock item', () => {
    emit('keydown', dock, { key: 'Enter' }); assert.deepEqual(calls, ['nuxel-dialer']);
});
