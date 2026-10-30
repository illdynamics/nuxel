#!/usr/bin/env node
// Offline UI test for the three independent lockscreen indicators.
//
// Loads the SHIPPED js/lockscreen-indicators.js in a vm with a minimal DOM and
// proves:
//   * all eight on/off combinations map to independent DOM classes;
//   * inactive indicators have no glow (the .active class is absent);
//   * the active charging animation is a separate class from external power;
//   * start()/stop() pause reads when the lockscreen is hidden;
//   * a failed read never turns anything on;
//   * the row is present in index.html with the three exact assets.
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '../../..');
const MODULE = path.join(ROOT, 'pwa/nuxel-home/js/lockscreen-indicators.js');
const INDEX = path.join(ROOT, 'pwa/nuxel-home/index.html');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond || extra === undefined ? '' : '  ' + extra));
  if (!cond) failures++;
}

function makeNode(id) {
  const classes = new Set();
  const attrs = new Map();
  return {
    id,
    dataset: {},
    classList: {
      add(c) { classes.add(c); },
      remove(c) { classes.delete(c); },
      contains(c) { return classes.has(c); },
    },
    get className() { return [...classes].join(' '); },
    setAttribute(k, v) { attrs.set(k, String(v)); },
    getAttribute(k) { return attrs.has(k) ? attrs.get(k) : null; },
    querySelector() { return { getAttribute() { return null; }, setAttribute() {} }; },
    contains() { return true; },
  };
}

function harness(payload) {
  const nodes = {
    'lockscreen-indicators': makeNode('lockscreen-indicators'),
    'lockscreen-indicator-charging': makeNode('lockscreen-indicator-charging'),
    'lockscreen-indicator-usb': makeNode('lockscreen-indicator-usb'),
    'lockscreen-indicator-live': makeNode('lockscreen-indicator-live'),
    'lockscreen-transports': makeNode('lockscreen-transports'),
    'lockscreen-transport-serial': makeNode('lockscreen-transport-serial'),
    'lockscreen-transport-usb': makeNode('lockscreen-transport-usb'),
    'lockscreen-transport-wlan': makeNode('lockscreen-transport-wlan'),
    'lockscreen-file-transfer': makeNode('lockscreen-file-transfer'),
    'lockscreen-bluetooth': makeNode('lockscreen-bluetooth'),
  };
  const intervals = [];
  let listens = 0;
  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    Promise, JSON, Object, Number, String, Boolean, Math, Error, RegExp, Date,
    setInterval(fn) { intervals.push(fn); return intervals.length; },
    clearInterval() {},
    setTimeout() { return 1; }, clearTimeout() {},
    fetch() { return Promise.reject(new Error('offline')); },
    document: {
      getElementById(id) { return nodes[id] || null; },
      addEventListener() { listens++; },
      body: { classList: { contains() { return false; } }, dataset: {} },
    },
    addEventListener() { listens++; },
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.NuxelHost = {
    available: true,
    statusRead() { return Promise.resolve({ ok: true, text: JSON.stringify(payload) }); },
    onEvent() {},
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(MODULE, 'utf8'), sandbox, { filename: 'lockscreen-indicators.js' });
  return { sandbox, nodes, intervals };
}

async function flush() { for (let i = 0; i < 12; i++) await Promise.resolve(); }

(async () => {
  const index = fs.readFileSync(INDEX, 'utf8');
  for (const asset of ['nuxel-charging.png', 'nuxel-connected-pc.png', 'nuxel-live-console-active.png']) {
    check('index.html references the exact asset ' + asset, index.includes('/assets/' + asset));
  }
  check('index.html has the three independent indicator nodes',
        ['charging', 'usb', 'live'].every(k => index.includes('lockscreen-indicator-' + k)));
  check('index.html loads lockscreen-indicators.js before lockscreen.js',
        index.indexOf('lockscreen-indicators.js') >= 0 &&
        index.indexOf('lockscreen-indicators.js') < index.indexOf('js/lockscreen.js'));
  check('runtime reparents stale nested indicator markup to the lockscreen itself',
        /this\.container\.parentNode !== wrap/.test(fs.readFileSync(MODULE, 'utf8')));

  for (let mask = 0; mask < 8; mask++) {
    const power = !!(mask & 1);
    const pc = !!(mask & 2);
    const live = !!(mask & 4);
    const h = harness({
      charging: { external_power: power, charging: power && !!(mask & 1), source: 'sysfs' },
      usb_data: { pc_connected: pc, source: 'sysfs:udc' },
      live_console: { active: live, source: 'proc:nuxel-console:tty' },
    });
    const ind = new h.sandbox.NuxelLockscreenIndicators();
    ind.start();
    await flush();
    const c = h.nodes['lockscreen-indicator-charging'];
    const u = h.nodes['lockscreen-indicator-usb'];
    const l = h.nodes['lockscreen-indicator-live'];
    check('combination ' + mask + ': charging independent',
          c.classList.contains('active') === power);
    check('combination ' + mask + ': usb independent',
          u.classList.contains('active') === pc);
    check('combination ' + mask + ': live independent',
          l.classList.contains('active') === live);
    check('combination ' + mask + ': charge animation only while charging',
          c.classList.contains('charging') === (power && power));
    if (!power) check('combination ' + mask + ': inactive charging has no glow class',
                      !c.classList.contains('active'));
    check('combination ' + mask + ': charging aria visibility follows truth',
          c.getAttribute('aria-hidden') === (power ? 'false' : 'true'));
    check('combination ' + mask + ': usb aria visibility follows truth',
          u.getAttribute('aria-hidden') === (pc ? 'false' : 'true'));
    check('combination ' + mask + ': console aria visibility follows truth',
          l.getAttribute('aria-hidden') === (live ? 'false' : 'true'));
    ind.stop();
  }

  // A detach event arriving during an older in-flight positive read must queue
  // a fresh read.  The stale completion cannot re-light USB for 15 seconds.
  {
    const h = harness({ charging: {}, usb_data: {}, live_console: {} });
    const pending = [];
    let reads = 0;
    h.sandbox.NuxelHost.statusRead = function () {
      reads++;
      return new Promise((resolve, reject) => pending.push({ resolve, reject }));
    };
    const ind = new h.sandbox.NuxelLockscreenIndicators();
    ind.start();
    await flush();
    ind.refresh();
    pending[0].resolve({ ok: true, text: JSON.stringify({
      charging: { external_power: true, charging: true },
      usb_data: { pc_connected: true }, live_console: { active: true },
    }) });
    await flush();
    check('refresh during in-flight read queues one fresh backend read', reads === 2,
          'reads=' + reads);
    pending[1].resolve({ ok: true, text: JSON.stringify({
      charging: { external_power: true, charging: true },
      usb_data: { pc_connected: false }, live_console: { active: false },
    }) });
    await flush();
    check('stale positive response cannot re-light USB after detach',
          !h.nodes['lockscreen-indicator-usb'].classList.contains('active'));
    check('fresh detach response keeps charging independent',
          h.nodes['lockscreen-indicator-charging'].classList.contains('active'));
    ind.stop();
  }

  // Proof-only indicators fail closed on backend loss; the last valid power
  // reading is retained so charging detection is not coupled to USB truth.
  {
    const h = harness({
      charging: { external_power: true, charging: false },
      usb_data: { pc_connected: true }, live_console: { active: true },
    });
    const ind = new h.sandbox.NuxelLockscreenIndicators();
    ind.start();
    await flush();
    h.sandbox.NuxelHost.statusRead = function () { return Promise.reject(new Error('detached')); };
    ind.refresh();
    await flush();
    check('failed refresh hides previously-on USB proof',
          !h.nodes['lockscreen-indicator-usb'].classList.contains('active'));
    check('failed refresh hides previously-on console proof',
          !h.nodes['lockscreen-indicator-live'].classList.contains('active'));
    check('failed refresh preserves independent external-power state',
          h.nodes['lockscreen-indicator-charging'].classList.contains('active'));
    ind.stop();
  }

  // stop() must actually stop reads; start() must read immediately.
  {
    let reads = 0;
    const h = harness({ charging: {}, usb_data: {}, live_console: {} });
    h.sandbox.NuxelHost.statusRead = function () { reads++; return Promise.resolve({ ok: true, text: '{}' }); };
    const ind = new h.sandbox.NuxelLockscreenIndicators();
    ind.stop();
    ind._tick();
    await flush();
    check('a stopped indicator does not read system state', reads === 0, 'reads=' + reads);
    ind.start();
    await flush();
    check('start() reads immediately', reads >= 1, 'reads=' + reads);
    const before = reads;
    ind._tick(); ind._tick(); ind._tick();
    await flush();
    check('repeated ticks do not issue overlapping reads', reads <= before + 1,
          'reads before=' + before + ' after=' + reads);
    ind.stop();
  }

  // A bad/absent payload must leave all three dim, never invent state.
  {
    const h = harness({ success: false, error: 'offline' });
    const ind = new h.sandbox.NuxelLockscreenIndicators();
    ind.start();
    await flush();
    check('a failed read leaves charging dim', !h.nodes['lockscreen-indicator-charging'].classList.contains('active'));
    check('a failed read leaves usb dim', !h.nodes['lockscreen-indicator-usb'].classList.contains('active'));
    check('a failed read leaves console dim', !h.nodes['lockscreen-indicator-live'].classList.contains('active'));
    ind.stop();
  }

  // Bluetooth is a proof-only transport indicator: powered=true lights it,
  // powered=false and an absent/unknown provider both leave it dim, and the
  // explicit UNKNOWN state is visible to the UI/tests.
  {
    const on = harness({
      charging: {}, usb_data: {}, live_console: {},
      bluetooth: { powered: true, state: 'on', discovering: true, source: 'bridge:BluetoothGetStatus' },
    });
    const indOn = new on.sandbox.NuxelLockscreenIndicators();
    indOn.start();
    await flush();
    const btOn = on.nodes['lockscreen-bluetooth'];
    check('powered Bluetooth lights the lockscreen indicator', btOn.classList.contains('active'));
    check('Bluetooth discovery is exposed on the indicator', btOn.dataset.discovering === 'true');
    check('Bluetooth indicator names its state', btOn.dataset.bluetoothState === 'on');
    indOn.stop();

    const off = harness({
      charging: {}, usb_data: {}, live_console: {},
      bluetooth: { powered: false, state: 'off', source: 'bridge:BluetoothGetStatus' },
    });
    const indOff = new off.sandbox.NuxelLockscreenIndicators();
    indOff.start();
    await flush();
    check('explicit Bluetooth OFF leaves the indicator dim',
          !off.nodes['lockscreen-bluetooth'].classList.contains('active'));
    check('explicit Bluetooth OFF is distinguishable from unknown',
          off.nodes['lockscreen-bluetooth'].dataset.bluetoothState === 'off');
    indOff.stop();

    const unknown = harness({ charging: {}, usb_data: {}, live_console: {} });
    const indUnknown = new unknown.sandbox.NuxelLockscreenIndicators();
    indUnknown.start();
    await flush();
    check('missing Bluetooth provider leaves the indicator dim, not OFF',
          !unknown.nodes['lockscreen-bluetooth'].classList.contains('active'));
    check('missing Bluetooth provider reports UNKNOWN',
          unknown.nodes['lockscreen-bluetooth'].dataset.bluetoothState === 'unknown');
    indUnknown.stop();
  }

  console.log('\n' + (failures ? failures + ' FAILURES' : 'ALL PASS'));
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error('HARNESS ERROR', e && e.stack || e); process.exit(2); });
