'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const code = fs.readFileSync(path.join(__dirname, '..', '..', 'pwa', 'nuxel-home', 'js', 'apps.js'), 'utf8');
const listeners = {};
const document = {
  readyState: 'complete',
  hidden: false,
  addEventListener: (k, fn) => { listeners[k] = fn; },
  removeEventListener: () => {},
  dispatchEvent: () => {},
  querySelectorAll: () => [],
  getElementById: () => null,
  body: { classList: { add() {}, remove() {}, contains() { return false; } } },
};
const storage = new Map();
const localStorage = {
  getItem: (k) => storage.has(k) ? storage.get(k) : null,
  setItem: (k, v) => storage.set(k, String(v)),
  removeItem: (k) => storage.delete(k),
};
const window = {
  addEventListener: () => {},
  location: { hash: '', origin: 'http://127.0.0.1:8000' },
  innerWidth: 360,
  innerHeight: 760,
};
window.window = window;
const ctx = {
  window,
  document,
  localStorage,
  console,
  CustomEvent: class { constructor(type, opts) { this.type = type; this.detail = opts && opts.detail; } },
  performance: { now: () => Date.now() },
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  URLSearchParams,
  fetch: async () => ({ ok: false, json: async () => ({}) }),
};
window.localStorage = localStorage;
vm.createContext(ctx);
vm.runInContext(code, ctx);

const origin = window.NuxelIconOrigin;
if (typeof origin !== 'function') throw new Error('NuxelIconOrigin not exported');

const cases = [
  [{ id: 'nuxel-dialer', type: 'native' }, 'nuxel'],
  [{ id: 'org.nuxel.Clock', type: 'pwa' }, 'nuxel'],
  [{ id: 'org.nuxel.Browser', type: 'native', native_binary: '/usr/lib/nuxel/x.py' }, 'nuxel'],
  [{ id: 'org.gnome.FileRoller', type: 'native', desktop_entry: 'shell/config/x.desktop' }, 'gtk'],
  [{ id: 'org.gnome.SystemMonitor', type: 'native', native_binary: '/usr/bin/gnome-system-monitor' }, 'gtk'],
  [{ id: 'org.mozilla.firefox', type: 'native', flatpak_id: 'org.mozilla.firefox', iconAsset: 'http://127.0.0.1:8080/api/v1/flatpak/icon/org.mozilla.firefox' }, 'flatpak'],
  [{ id: 'com.stremio.Stremio', type: 'native', install_source: 'flatpak:system' }, 'flatpak'],
  [{ id: 'org.example.Unknown', type: 'web' }, 'pwa'],
];
for (const [app, want] of cases) {
  const got = origin(app);
  if (got !== want) throw new Error(JSON.stringify(app) + ' expected ' + want + ' got ' + got);
}
// A GTK app must never receive the Nuxel decorative pack as its rendered icon.
if (typeof window.NuxelAppIcon === 'function') {
  const html = window.NuxelAppIcon({ id: 'org.gnome.Loupe', type: 'native', desktop_entry: 'x', icon: '🖼️' });
  if (html.includes('/nuxel-applications-icon-pack/')) throw new Error('GTK app received Nuxel icon pack');
  if ((html.match(/<img/g) || []).length !== 1) throw new Error('icon renderer must create exactly one image');
  const native = window.NuxelAppIcon({ id: 'nuxel-dialer', type: 'native' });
  if (!native.includes('/nuxel-applications-icon-pack/')) throw new Error('native Nuxel icon lost its custom artwork');
}
console.log('icon policy OK');
