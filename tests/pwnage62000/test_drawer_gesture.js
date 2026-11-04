#!/usr/bin/env node
'use strict';
/* PWNAGE-62000: the app drawer must open even when WebKit cancels the pointer
 * stream as the vertical swipe becomes a native scroll.  The touch fallback is
 * the regression guard for the reported "drawer does not open" state. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '../..');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond || extra === undefined ? '' : '  ' + extra));
  if (!cond) failures++;
}
function target(classes) {
  const set = new Set((classes || '').split(/\s+/).filter(Boolean));
  return {
    closest(sel) {
      const parts = sel.split(',').map(s => s.trim());
      for (const p of parts) {
        if (p.startsWith('.') && set.has(p.slice(1))) return this;
        if (p.startsWith('#') && set.has(p.slice(1))) return this;
      }
      return null;
    },
  };
}
const listeners = {};
const bodyClasses = new Set();
const sandbox = {
  console: { log() {}, warn() {}, error() {} },
  performance: { now: () => 1000 },
  setTimeout, clearTimeout,
  document: {
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    body: { classList: { contains: c => bodyClasses.has(c) } },
    body: { classList: { contains: c => bodyClasses.has(c) } },
  },
  window: {},
};
let qsOpened = 0;
sandbox.window = {
  launcher: { drawerOpen: false, opened: 0, openDrawer() { this.opened++; this.drawerOpen = true; } },
  qs: { open() { qsOpened++; } },
  nuxel: { appSession: { state: 'CLOSED' } },
};
sandbox.window.document = sandbox.document;
sandbox.window.performance = sandbox.performance;
const src = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/gestures.js'), 'utf8');
vm.runInNewContext(src, sandbox, { filename: 'gestures.js' });
function fire(type, ev) { (listeners[type] || []).forEach(fn => fn(ev)); }
const empty = target('');
const t = { identifier: 7, clientX: 180, clientY: 700 };
fire('pointerdown', { isPrimary: true, pointerId: 7, clientX: 180, clientY: 700,
                      target: empty });
fire('pointercancel', { pointerId: 7 });
fire('touchstart', { target: empty, changedTouches: [t] });
fire('touchend', { changedTouches: [{ identifier: 7, clientX: 180, clientY: 560 }] });
check('upward touch swipe opens the app drawer after pointercancel',
      sandbox.window.launcher.opened === 1, 'opened=' + sandbox.window.launcher.opened);

// Closing and re-opening must not inherit the previous gesture's consumed flag
// (a pure-touch WebKit stream has no pointerup to reset it).
sandbox.window.launcher.drawerOpen = false;
fire('touchstart', { target: empty, changedTouches: [t] });
fire('touchend', { changedTouches: [{ identifier: 7, clientX: 180, clientY: 560 }] });
check('a second touch swipe still opens the drawer',
      sandbox.window.launcher.opened === 2, 'opened=' + sandbox.window.launcher.opened);

// An app icon is a normal origin for the upward drawer swipe.  The travel
// gate (>= 56 px) still keeps a tap from opening the drawer.
sandbox.window.launcher.drawerOpen = false;
sandbox.window.launcher.opened = 0;
fire('touchstart', { target: target('app-item'), changedTouches: [t] });
fire('touchend', { changedTouches: [{ identifier: 7, clientX: 180, clientY: 500 }] });
check('upward swipe starting on an app icon opens the drawer',
      sandbox.window.launcher.opened === 1, 'opened=' + sandbox.window.launcher.opened);

// A tap on an app icon must remain a tap.
sandbox.window.launcher.drawerOpen = false;
sandbox.window.launcher.opened = 0;
fire('touchstart', { target: target('app-item'), changedTouches: [t] });
fire('touchend', { changedTouches: [{ identifier: 7, clientX: 181, clientY: 695 }] });
check('short tap on an app icon does not open the drawer',
      sandbox.window.launcher.opened === 0, 'opened=' + sandbox.window.launcher.opened);

// A drawer already open must treat the swipe as scrolling, never re-open.
sandbox.window.launcher.drawerOpen = true;
fire('touchstart', { target: empty, changedTouches: [t] });
fire('touchend', { changedTouches: [{ identifier: 7, clientX: 180, clientY: 500 }] });
check('swipe inside an open drawer is a scroll, not a second open',
      sandbox.window.launcher.opened === 0, 'opened=' + sandbox.window.launcher.opened);

// The status bar marks the top-edge pull as handled; the release fallback must
// not apply it a second time (compact -> expanded in one swipe).
sandbox.window.launcher.drawerOpen = false;
fire('pointerdown', { isPrimary: true, pointerId: 9, clientX: 180, clientY: 12, target: empty });
sandbox.window.__nuxelQsGestureConsumed = true;  // status bar fired on move
fire('pointerup', { pointerId: 9, clientX: 180, clientY: 180, target: empty });
check('status-bar-handled top pull is not applied twice',
      qsOpened === 0, 'qsOpened=' + qsOpened);

console.log(failures ? failures + ' FAILURES' : 'ALL PASS');
process.exit(failures ? 1 : 0);
