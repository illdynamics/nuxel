// Startup/persistence regression: no Settings visit is required for the cutout.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const src = fs.readFileSync(path.join(__dirname, '../../../../pwa/nuxel-home/js/safe-zones.js'), 'utf8');
const statusSrc = fs.readFileSync(path.join(__dirname, '../../../../pwa/nuxel-home/js/status-bar.js'), 'utf8');

async function boot({doc, reject = false, ua = 'Nuxel S10+', width = 360,
                     withStatus = false, delayHost = false} = {}) {
  const events = [];
  const listeners = {};
  const frames = [];
  const observed = new Set();
  let resizeCallback, releaseHost;
  function listen(target, type, cb) { (listeners[target + type] ||= []).push(cb); }
  function dispatch(target, event) {
    for (const cb of listeners[target + event.type] || []) cb(event);
  }
  const attrs = {};
  const right = {className: 'status-right', style: {},
    getBoundingClientRect() { return {left: 300, right: 360, width: 60}; }};
  const bar = {clientWidth: width, offsetWidth: width,
    setAttribute(k, v) { attrs[k] = v; },
    querySelectorAll() { return [right]; },
    querySelector(s) { return s === '.status-right' ? right : null; }};
  let saved;
  const win = {navigator: {userAgent: ua}, devicePixelRatio: 2,
    localStorage: {getItem() { return null; }, setItem() {}},
    document: {readyState: 'complete', getElementById() { return bar; },
      addEventListener(type, cb) { listen('document:', type, cb); },
      dispatchEvent(e) { dispatch('document:', e); }},
    addEventListener(type, cb) { listen('window:', type, cb); },
    dispatchEvent(e) { events.push(e); dispatch('window:', e); },
    requestAnimationFrame(cb) { frames.push(cb); },
    setInterval() {}, setTimeout() {}, console,
    ResizeObserver: class {
      constructor(cb) { resizeCallback = cb; }
      observe(el) { observed.add(el); }
    },
    CustomEvent: class { constructor(type, opts) { this.type = type; this.detail = opts.detail; } },
    NuxelHost: {available: true,
      configGet() {
        if (reject) return Promise.reject(new Error('host offline'));
        const result = {ok: !!doc, text: doc && JSON.stringify(doc)};
        return delayHost ? new Promise(resolve => { releaseHost = () => resolve(result); }) : Promise.resolve(result);
      },
      configSet(name, text) { saved = JSON.parse(text); return Promise.resolve({ok: true}); }}
  };
  win.window = win;
  vm.runInNewContext(src, win);
  if (withStatus) {
    vm.runInNewContext(statusSrc + '\nwindow.TestStatusBar = StatusBar;', win);
    const status = Object.create(win.TestStatusBar.prototype);
    // Stub hardware providers, retaining the real initialization, layout
    // scheduling, event listeners and ResizeObserver registration.
    for (const name of Object.getOwnPropertyNames(win.TestStatusBar.prototype)) {
      if (name !== '_init' && name !== '_applySafeZones' && name !== 'constructor') status[name] = () => {};
    }
    status._init();
  }
  await new Promise(resolve => setImmediate(resolve));
  function paint() { while (frames.length) frames.shift()(); }
  paint();
  return {win, bar, right, attrs, events, observed, paint,
    resize: () => resizeCallback(), releaseHost: () => releaseHost(), saved: () => saved};
}

(async () => {
  const fresh = await boot();
  assert.equal(fresh.attrs['data-safezone-blocked'], '9,10');
  assert.equal(fresh.right.style.transform, 'translateX(-84px)');
  assert.equal(fresh.events.at(-1).type, 'nuxel:safezones-changed');
  const persisted = JSON.parse(JSON.stringify(fresh.win.NuxelSafeZones.state));
  const saved = await boot({doc: persisted});
  assert.equal(saved.attrs['data-safezone-profile'], 's10plus');
  assert.equal(saved.attrs['data-safezone-blocked'], '9,10');
  const none = await boot({doc: {...persisted, profile: 'none'}});
  assert.equal(none.attrs['data-safezone-blocked'], '');
  const desktop = await boot({ua: 'desktop'});
  assert.equal(desktop.attrs['data-safezone-profile'], 'none');
  const offline = await boot({reject: true});
  assert.equal(offline.attrs['data-safezone-blocked'], '9,10');
  const hidden = await boot({doc: persisted, width: 0});
  hidden.bar.clientWidth = hidden.bar.offsetWidth = 360;
  hidden.win.NuxelSafeZones.applyLayout();
  assert.equal(hidden.right.style.transform, 'translateX(-84px)');
  saved.win.NuxelSafeZones.previewZones([9, 10], 'portrait', 'custom');
  await new Promise(resolve => saved.win.NuxelSafeZones.commitPreview(resolve));
  const custom = await boot({doc: saved.saved()});
  assert.equal(custom.attrs['data-safezone-profile'], 'custom');
  assert.equal(custom.attrs['data-safezone-blocked'], '9,10');
  assert.equal(custom.right.style.transform, 'translateX(-84px)');
  const delayed = await boot({doc: persisted, withStatus: true, delayHost: true, width: 0});
  delayed.releaseHost();
  await new Promise(resolve => setImmediate(resolve));
  delayed.paint();
  assert.equal(delayed.attrs['data-safezone-blocked'], '9,10');
  delayed.bar.clientWidth = delayed.bar.offsetWidth = 360;
  delayed.win.document.dispatchEvent({type: 'nuxel:lockscreen-hidden'});
  delayed.paint();
  assert.equal(delayed.right.style.transform, 'translateX(-84px)', 'unlock must lay out without a Settings visit');
  assert(delayed.observed.has(delayed.bar) && delayed.observed.has(delayed.right));
  delayed.bar.clientWidth = delayed.bar.offsetWidth = 400;
  delayed.resize();
  delayed.paint();
  assert.equal(delayed.right.style.transform, 'translateX(-52px)', 'size changes must remeasure');
  delayed.win.NuxelSafeZones.applyPreset('none');
  delayed.win.dispatchEvent({type: 'nuxel:safezones-changed'});
  delayed.paint();
  assert.equal(delayed.right.style.transform, '', 'window change event must reach StatusBar');
  console.log('PASS safe-zone startup, delayed host, offline fallback, explicit none, unlock, resize, change events and persisted custom zones');
})().catch(error => { console.error(error); process.exitCode = 1; });
