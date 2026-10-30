// PWNAGE-41000 Quick Settings Wi-Fi tri-state regression tests.
//
// The tile must distinguish radio ON from network CONNECTED and must never
// turn a missing/unavailable bridge field into a false OFF.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '../../..');
const SRC = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/qs.js'), 'utf8');

let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}

// Extract the class without running the DOMContentLoaded factory.  This keeps
// the test focused on the state mapping that caused the live false-OFF.
const classSrc = SRC.slice(SRC.indexOf('class QuickSettings'), SRC.lastIndexOf('document.addEventListener'));

function loadWithBridge(phoneStatus) {
  const wifi = {
    dataset: {}, title: '', label: { innerHTML: '' },
    addEventListener() {},
    querySelector(sel) { return sel === '.qs-label' ? this.label : null; },
  };
  const elements = { 'qs-wifi': wifi };
  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    document: {
      getElementById(id) { return elements[id] || null; },
      querySelectorAll() { return []; },
      addEventListener() {},
      dispatchEvent() {},
      body: { appendChild() {} },
      createElement() { return { style: {}, appendChild() {}, addEventListener() {} }; },
    },
    CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
    setTimeout, clearTimeout, setInterval, clearInterval,
    navigator: {},
    bridge: {
      getPhoneStatus: async () => phoneStatus,
      call: async () => ({ success: false, offline: true }),
      requestCapability: async () => true,
    },
    NuxelSettings: null,
  };
  sandbox.__diag = [];
  sandbox.webkit = { messageHandlers: { nuxelDiag: { postMessage: (m) => sandbox.__diag.push(m) } } };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(classSrc + '\nthis.__QuickSettings = QuickSettings;', sandbox);
  const qs = new sandbox.__QuickSettings();
  return { qs, wifi, diag: sandbox.__diag };
}

function tick() {
  // _syncState awaits getPhoneStatus; one turn is enough because the fake is
  // already resolved.
  return new Promise((resolve) => setTimeout(resolve, 0));
}

(async () => {
  // Explicit ON, link connected.
  {
    const { qs, wifi, diag } = loadWithBridge({ network: { wifi_enabled: true, wifi_connected: true, wifi_state: 'connected' } });
    await tick();
    check('explicit enabled + connected renders ON', wifi.dataset.enabled === 'true', wifi.dataset.enabled);
    check('connected link is distinct from radio ON', wifi.dataset.connected === 'true', wifi.dataset.connected);
    check('tile title names radio ON', /Wi-Fi radio: ON/.test(wifi.title), wifi.title);
    check('QS emits state-only radio/link evidence', diag.includes('QS_WIFI radio=ON link=CONNECTED'), JSON.stringify(diag));
    check('QS evidence contains no network identity', !/SSID|192\.|password/i.test(diag.join(' ')), JSON.stringify(diag));
  }

  // Radio ON, no network: the tile must stay ON, not OFF.
  {
    const { qs, wifi } = loadWithBridge({ network: { wifi_enabled: true, wifi_connected: false, wifi_state: 'enabled_disconnected' } });
    await tick();
    check('enabled radio without a link stays ON', wifi.dataset.enabled === 'true', wifi.dataset.enabled);
    check('enabled radio without a link is marked disconnected', wifi.dataset.connected === 'false', wifi.dataset.connected);
    check('label distinguishes on/not-connected', /WiFi<br>on/.test(wifi.label.innerHTML), wifi.label.innerHTML);
  }

  // Genuine NetworkManager disabled state: OFF.
  {
    const { qs, wifi } = loadWithBridge({ network: { wifi_enabled: false, wifi_connected: false, wifi_state: 'disabled' } });
    await tick();
    check('genuine disabled state renders OFF', wifi.dataset.enabled === 'false', wifi.dataset.enabled);
    check('genuine disabled state is not checking', !/checking/.test(wifi.label.innerHTML), wifi.label.innerHTML);
  }

  // Missing bridge/report: UNKNOWN, never false.
  {
    const { qs, wifi } = loadWithBridge({ success: false, unavailable: true, network: {} });
    await tick();
    check('missing wifi_enabled renders UNKNOWN', wifi.dataset.enabled === 'unknown', wifi.dataset.enabled);
    check('missing wifi_enabled is labelled checking', /checking/.test(wifi.label.innerHTML), wifi.label.innerHTML);
    check('missing wifi_enabled is not OFF', wifi.dataset.enabled !== 'false', wifi.dataset.enabled);
  }

  // Rejected/unavailable status object: still UNKNOWN.
  {
    const { qs, wifi } = loadWithBridge({ success: false });
    await tick();
    check('absent network object renders UNKNOWN', wifi.dataset.enabled === 'unknown', wifi.dataset.enabled);
  }

  // Pure state mapper: a transient generic connected:false is not radio OFF.
  {
    const mapper = loadWithBridge({ network: {} });
    const Radio = mapper.qs.constructor.wifiRadioState;
    check('radio mapper rejects generic connected:false', Radio({ connected: false }) === null);
    check('radio mapper accepts explicit false', Radio({ wifi_enabled: false }) === false);
    check('radio mapper accepts enabled_disconnected', Radio({ wifi_state: 'enabled_disconnected' }) === true);
  }

  // Bluetooth tri-state: the same "unknown is not off" rule, with the verified
  // S10+ path (hci0 + powered BlueZ adapter) rendered ON.
  {
    const mapper = loadWithBridge({ network: {} });
    const BT = mapper.qs.constructor.bluetoothRadioState;
    check('BT mapper accepts powered adapter', BT({ state: 'on', powered: true }) === true);
    check('BT mapper accepts discovery as ON', BT({ state: 'discovering', powered: true }) === true);
    check('BT mapper accepts explicit OFF', BT({ state: 'off', powered: false }) === false);
    check('BT mapper keeps a missing Powered property UNKNOWN', BT({ state: 'unknown' }) === null);
    check('BT mapper keeps a missing adapter UNKNOWN', BT({ adapter_present: false }) === null);
    check('BT mapper keeps a provider failure UNKNOWN', BT(null) === null);
  }

  // The top status bar uses the same provider.  Exercise the real
  // status-bar.js with a small DOM so the Bluetooth indicator cannot regress to
  // a fabricated OFF or a permanently hidden glyph.
  {
    const vm = require('vm');
    const sbSrc = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/status-bar.js'), 'utf8');
    function el(tag) {
      return {
        tagName: tag, textContent: '', innerHTML: '', hidden: false, title: '',
        dataset: {}, style: { setProperty() {} }, children: [],
        classList: { add() {}, remove() {}, contains() { return false; } },
        replaceChildren(...c) { this.children = c; },
        appendChild(c) { this.children.push(c); return c; },
        setAttribute(k, v) { this[k] = v; },
        addEventListener() {}, removeEventListener() {},
        querySelector() { return null; },
      };
    }
    const bar = el('div');
    bar.clientWidth = 360;
    const ids = {};
    for (const id of ['status-time', 'status-signal', 'status-wifi', 'status-bluetooth',
                      'status-battery', 'status-battery-pct', 'status-bar']) {
      ids[id] = el('span');
    }
    ids['status-bar'] = bar;
    const sbDoc = {
      readyState: 'complete', body: el('body'),
      getElementById(id) { return ids[id] || null; },
      querySelector() { return null; }, querySelectorAll() { return []; },
      createElement(t) { return el(t); },
      addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
    };
    const sbWindow = { addEventListener() {}, removeEventListener() {}, devicePixelRatio: 2,
                       innerWidth: 360, innerHeight: 760 };
    const sbSandbox = {
      console: { log() {}, warn() {}, error() {} }, document: sbDoc, window: sbWindow,
      CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
      setInterval() { return 0; }, clearInterval() {}, setTimeout() { return 0; }, clearTimeout() {},
      requestAnimationFrame() { return 0; }, localStorage: { getItem() { return null; }, setItem() {} },
      Promise,
      bridge: { call: async () => ({ success: true, state: 'on', powered: true, discovering: true,
                                    adapter_present: true, hci_devices: ['hci0'],
                                    adapter_address: 'AA:BB:CC:DD:EE:FF' }) },
      NuxelHost: null,
    };
    sbSandbox.window = sbWindow;
    sbSandbox.self = sbSandbox;
    sbSandbox.globalThis = sbSandbox;
    vm.createContext(sbSandbox);
    vm.runInContext(sbSrc + '\nthis.StatusBar = StatusBar;', sbSandbox);
    const sb = new sbSandbox.StatusBar();
    await new Promise((r) => setTimeout(r, 0));
    check('status bar shows a powered Bluetooth adapter', ids['status-bluetooth'].hidden === false,
          String(ids['status-bluetooth'].hidden));
    check('status bar exposes discovery state', ids['status-bluetooth'].dataset.discovering === 'true',
          String(ids['status-bluetooth'].dataset.discovering));
  }

  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
