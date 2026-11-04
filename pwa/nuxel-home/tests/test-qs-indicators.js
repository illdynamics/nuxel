// PWNAGE-44000 expanded Quick Settings canonical-indicator tests.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}
const src = fs.readFileSync(path.join(__dirname, '../js/qs.js'), 'utf8');
const classSrc = src.slice(src.indexOf('class QuickSettings'), src.lastIndexOf("document.addEventListener"));

function load(indicators) {
  const els = {};
  function el(id) {
    return { id, hidden: false, dataset: {}, textContent: '', title: '',
      setAttribute() {}, querySelector(sel) { return sel === '.qs-detail-label' ? (this.label || (this.label = { textContent: '' })) : null; } };
  }
  const sandbox = {
    console: { log() {}, warn() {} },
    document: {
      getElementById(id) { return els[id] || (els[id] = el(id)); },
      querySelectorAll() { return []; }, addEventListener() {}, dispatchEvent() {},
      body: { appendChild() {} }, createElement() { return el('x'); },
    },
    CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
    setTimeout, clearTimeout, setInterval, clearInterval, navigator: {},
    bridge: { call: async (ns, verb) => ns === 'system' && verb === 'indicators' ? indicators : { success: false } },
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(classSrc + '\nthis.__QS = QuickSettings;', sandbox);
  const qs = Object.create(sandbox.__QS.prototype);
  qs.isOpen = true; qs.expanded = true; qs.state = {}; qs._indicatorGeneration = 0;
  return { qs, els, QS: sandbox.__QS };
}
const base = {
  charging: { charging: false, external_power: false, battery_level: 42 },
  usb_data: { pc_connected: false }, file_transfer: { selected: 'charging', active: false },
  live_console: { active: false, service_armed: false },
  console_transports: { usb: { active: false }, serial: { active: false }, wlan: { active: false } },
};
(async () => {
  let { qs, els } = load(Object.assign({}, base, { charging: { charging: true, external_power: true, battery_level: 42 } }));
  await qs._syncIndicators();
  check('active charging shown as Charging', els['qs-detail-charging'].dataset.state === 'active' && /Charging/.test(els['qs-detail-charging'].label.textContent));
  check('no USB host link is not file transfer', els['qs-detail-usb'].dataset.state === 'inactive');

  ({ qs, els } = load(Object.assign({}, base, { charging: { charging: false, external_power: true }, usb_data: { pc_connected: true }, file_transfer: { selected: 'file_transfer', active: false } })));
  await qs._syncIndicators();
  check('external power + Full is not active charging', els['qs-detail-charging'].dataset.state === 'external');
  check('selected-but-inactive transfer is labelled selected/inactive', els['qs-detail-file'].dataset.state === 'selected');

  ({ qs, els } = load(Object.assign({}, base, { file_transfer: { selected: 'file_transfer', active: true }, live_console: { active: false, service_armed: true }, console_transports: { usb: { active: true }, serial: { active: false }, wlan: { active: true } } })));
  await qs._syncIndicators();
  check('active file transfer shown distinctly', els['qs-detail-file'].dataset.state === 'active');
  check('armed console is not named connected', els['qs-detail-console'].dataset.state === 'armed');
  check('transports list only active links', /USB \+ WLAN/.test(els['qs-detail-transports'].label.textContent));

  ({ qs, els } = load(Object.assign({}, base, { live_console: { active: true } })));
  await qs._syncIndicators();
  check('live console connected is active', els['qs-detail-console'].dataset.state === 'active');

  ({ qs, els } = load({ success: false, error: 'provider down' }));
  await qs._syncIndicators();
  check('provider failure renders UNKNOWN, not OFF', els['qs-detail-usb'].dataset.state === 'unknown');

  check('QS close stops the panel timers', /close\(\)[\s\S]*clearInterval\(this\._locationTimer\)/.test(src));
  check('stale indicator responses are discarded after close', /_indicatorGeneration/.test(src));
  // Directional pull contract: closed -> compact -> expanded, while an
  // upward pull closes only the compact panel.
  const { QS } = load(base);
  const pullOutcome = (isOpen, expanded, direction) => {
    const q = Object.create(QS.prototype);
    q.isOpen = isOpen; q.expanded = expanded;
    const calls = [];
    q.open = () => { calls.push('open'); q.isOpen = true; q.expanded = false; };
    q.expand = () => { calls.push('expand'); q.expanded = true; };
    q.close = () => { calls.push('close'); q.isOpen = false; q.expanded = false; };
    q.pull(direction);
    return calls[0] || 'noop';
  };
  check('closed + pull-down opens compact', pullOutcome(false, false, 'down') === 'open');
  check('closed + pull-up is inert', pullOutcome(false, false, 'up') === 'noop');
  check('compact + pull-down expands', pullOutcome(true, false, 'down') === 'expand');
  check('compact + pull-up closes', pullOutcome(true, false, 'up') === 'close');
  check('expanded + pull-down closes', pullOutcome(true, true, 'down') === 'close');
  check('expanded + pull-up is inert', pullOutcome(true, true, 'up') === 'noop');
  check('Quick Settings panel owns its own pointer/touch pull',
        /_bindPullGesture\(\)/.test(src) && /\.addEventListener\('touchstart'/.test(src) &&
        /\.addEventListener\('pointerup'/.test(src));
  check('flashlight uses the privileged provider', /bridge\.call\('flashlight', 'toggle'/.test(src));
  process.exit(failures ? 1 : 0);
})();
