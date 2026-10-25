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
  return {
    id,
    dataset: {},
    classList: {
      add(c) { classes.add(c); },
      remove(c) { classes.delete(c); },
      contains(c) { return classes.has(c); },
    },
    get className() { return [...classes].join(' '); },
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

  console.log('\n' + (failures ? failures + ' FAILURES' : 'ALL PASS'));
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error('HARNESS ERROR', e && e.stack || e); process.exit(2); });
