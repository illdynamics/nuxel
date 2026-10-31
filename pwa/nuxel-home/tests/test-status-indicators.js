// PWNAGE-44000 status-bar truth tests: charging bolt, sound modes, USB label
// precedence and the Full-is-not-charging regression.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}
const src = fs.readFileSync(path.join(__dirname, '../js/status-bar.js'), 'utf8');
function el() {
  const tag = { textContent: '', title: '', hidden: false, dataset: {}, className: '', innerHTML: '',
    style: {}, setAttribute() {}, replaceChildren() {}, querySelector() { return null; } };
  return tag;
}
const elements = {};
function instance() {
  const sandbox = {
    console: { log() {}, warn() {} },
    document: {
      getElementById(id) { return elements[id] || (elements[id] = el()); },
      addEventListener() {}, querySelectorAll() { return []; },
      body: { classList: { contains() { return false; }, add() {}, remove() {} } },
    },
    window: { addEventListener() {}, NuxelSafeZones: null, NuxelHost: null },
    setInterval, clearInterval, setTimeout, clearTimeout, Date, Math, Number, String, Object, JSON,
  };
  sandbox.window = Object.assign(sandbox.window, sandbox);
  vm.createContext(sandbox);
  vm.runInContext(src + '\nthis.__StatusBar = StatusBar;', sandbox);
  const sb = Object.create(sandbox.__StatusBar.prototype);
  sb.state = { batteryLevel: null, batteryCharging: false, indicators: null, usbLabel: '', soundMode: 'unknown' };
  sb.elements = {
    battery: elements['status-battery'] || (elements['status-battery'] = el()),
    batteryPct: elements['status-battery-pct'] || (elements['status-battery-pct'] = el()),
    sound: elements['status-sound'] || (elements['status-sound'] = el()),
    usb: elements['status-usb'] || (elements['status-usb'] = el()),
  };
  sb.elements.usb.querySelector = () => sb.elements['usb-label'] || (sb.elements['usb-label'] = { textContent: '' });
  sb._applySafeZones = () => {};
  sb.batteryStyle = 'inside';
  sb._batteryRenderKey = '';
  return sb;
}

(async () => {
  const sb = instance();
  sb.state.batteryLevel = 55;
  check('accepts Charging as active charging', sb._acceptBatteryLevel(55, true, 'Charging') && sb.state.batteryCharging === true);
  sb.state.batteryLevel = 99;
  check('full is NOT active charging', sb._acceptBatteryLevel(100, false, 'Full') && sb.state.batteryCharging === false);
  sb.state.batteryLevel = 90;
  check('not-charging status is not active charging', sb._acceptBatteryLevel(90, false, 'Not charging') && sb.state.batteryCharging === false);
  sb.state.batteryLevel = 80;
  check('displaying is not active charging', sb._acceptBatteryLevel(80, false, 'Discharging') && sb.state.batteryCharging === false);
  sb._renderBattery();
  check('battery icon has no charging class when Full', !/charging/.test(sb.elements.battery.innerHTML), sb.elements.battery.innerHTML);
  sb._acceptBatteryLevel(55, true, 'Charging');
  sb._renderBattery();
  check('battery icon gets charging class only while charging', /battery-icon charging/.test(sb.elements.battery.innerHTML));

  const setInd = (ind) => { sb.state.indicators = ind; sb._renderUsb(); };
  const base = { charging: {}, usb_data: {}, console_transports: {}, file_transfer: {}, live_console: {} };
  setInd(Object.assign({}, base, { file_transfer: { active: true }, console_transports: { usb: { active: true } }, usb_data: { pc_connected: true }, charging: { charging: true, external_power: true } }));
  check('active file transfer wins the USB label', sb.elements.usb.dataset.state === 'file' && sb.elements['usb-label'].textContent === 'file');
  setInd(Object.assign({}, base, { file_transfer: { selected: 'file_transfer', active: false }, console_transports: { usb: { active: true } }, usb_data: { pc_connected: true } }));
  check('selected-but-inactive file transfer does not label file', sb.elements.usb.dataset.state === 'term');
  setInd(Object.assign({}, base, { usb_data: { pc_connected: true }, charging: { charging: true, external_power: true } }));
  check('active charging gets chrg', sb.elements.usb.dataset.state === 'chrg');
  setInd(Object.assign({}, base, { usb_data: { pc_connected: true }, charging: { charging: false, external_power: true } }));
  check('external power + Full shows a cable without a false chrg tag', sb.elements.usb.hidden === false && sb.elements['usb-label'].textContent === '' && sb.elements.usb.dataset.state === 'connected');
  setInd(Object.assign({}, base, { usb_data: { pc_connected: false } }));
  check('detached USB hides the glyph', sb.elements.usb.hidden === true);

  sb.state.soundMode = 'normal'; sb._renderSound();
  check('normal sound mode is visible and labelled', sb.elements.sound.hidden === false && sb.elements.sound.dataset.mode === 'normal');
  sb.state.soundMode = 'vibrate'; sb._renderSound();
  check('vibrate mode is selected, not a haptics claim', sb.elements.sound.dataset.mode === 'vibrate' && /not claimed/.test(sb.elements.sound.title));
  sb.state.soundMode = 'silent'; sb._renderSound();
  check('silent mode renders silent', sb.elements.sound.dataset.mode === 'silent');
  sb.state.soundMode = 'unknown'; sb._renderSound();
  check('unknown sound mode is hidden rather than guessed normal', sb.elements.sound.hidden === true);

  const index = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
  const css = fs.readFileSync(path.join(__dirname, '../css/status-bar.css'), 'utf8');
  check('top bar declares Location, sound and USB cells', ['status-location','status-sound','status-usb'].every(id => index.includes('id="' + id + '"')));
  check('overlap assertion includes the new cells', /status-sound/.test(src) && /status-usb/.test(src) && /_assertNoOverlap\(\)/.test(src));
  check('charging bolt exists in CSS', /\.battery-icon\.charging::after/.test(css));
  check('USB label CSS has file/term/chrg precedence states', ['file','term','chrg'].every(x => css.includes('data-state="' + x + '"')));

  process.exit(failures ? 1 : 0);
})();
