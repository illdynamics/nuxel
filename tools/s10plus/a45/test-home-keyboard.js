// A45 offline regression harness for the Home/penguin and touch-keyboard paths.
//
// It loads the SHIPPED launcher sources in a VM with a deliberately small DOM
// shell.  It is not a substitute for the physical S10+ test: it proves the state
// transitions and editing calls, never that the glass changed.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '../../..');
let failures = 0;
function check(name, condition, detail) {
  console.log((condition ? 'PASS ' : 'FAIL ') + name + (condition ? '' : '  ' + (detail === undefined ? '' : detail)));
  if (!condition) failures++;
}

function eventTarget(extra) {
  const handlers = {};
  return Object.assign({
    addEventListener(type, fn) { (handlers[type] = handlers[type] || []).push(fn); },
    removeEventListener() {},
    dispatch(type, event) { (handlers[type] || []).slice().forEach(fn => fn(event)); return true; },
    handlers,
  }, extra || {});
}

// ------------------------------------------------------------------------- //
// app.js: Home must background a PWA and close a native top-level app
// ------------------------------------------------------------------------- //
function loadHome() {
  const sandbox = {
    console,
    setTimeout, clearTimeout, setInterval, clearInterval,
    CustomEvent: class { constructor(type, options) { this.type = type; Object.assign(this, options || {}); } },
    document: eventTarget({ hidden: false, body: { dataset: {} }, activeElement: null, querySelectorAll: () => [] }),
    navigator: {}, localStorage: { getItem: () => null, setItem() {} },
  };
  sandbox.window = sandbox;
  sandbox.document.addEventListener = () => {};
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/app.js'), 'utf8'), sandbox);
  return sandbox;
}

const homeSandbox = loadHome();
check('app.js exports NuxelHome for the harness', typeof homeSandbox.NuxelHome === 'function');
class TestHome extends homeSandbox.NuxelHome { _init() {} }

function homeHarness(app, frame) {
  const harness = new TestHome();
  harness.components = {};
  harness.appSurfaces = new Map();
  harness.appSession = { state: 'ACTIVE', app, frame };
  harness._inputTrace = () => {};
  let sessionHome = 0, desktop = 0, closed = 0;
  harness.sessions = { home() { sessionHome++; }, activate() {} };
  harness._closeAppSurface = () => { closed++; harness.appSession = { state: 'CLOSED', app: null, frame: null }; };
  homeSandbox.launcher = { currentPage: 2, closeDrawer() {}, exitEditMode() {}, mainDesktop() { desktop++; this.currentPage = 0; } };
  homeSandbox.recents = undefined;
  harness.home();
  return { harness, sessionHome, desktop, closed };
}

let result = homeHarness({ id: 'org.nuxel.Terminal', name: 'Terminal' }, null);
check('Home closes a native top-level app instead of returning early', result.closed === 1 && result.harness.appSession.state === 'CLOSED', JSON.stringify(result.harness.appSession));
check('Home still paints Desktop 1 for a native app', result.desktop === 1, result.desktop);

const frame = { hidden: false, __nuxelBackgrounded: false, contentDocument: null };
const bar = { hidden: false }, status = { hidden: false };
result = homeHarness({ id: 'org.nuxel.Calendar', name: 'Calendar' }, frame);
result.harness.appSurfaces.set('org.nuxel.Calendar', { frame, bar, status });
result = homeHarness({ id: 'org.nuxel.Calendar', name: 'Calendar' }, frame);
result.harness.appSurfaces.set('org.nuxel.Calendar', { frame, bar, status });
result.harness.home();
check('Home hides the PWA frame, bar and status', frame.hidden && bar.hidden && status.hidden, JSON.stringify({ frame: frame.hidden, bar: bar.hidden, status: status.hidden }));
check('Home marks an in-flight iframe as backgrounded', frame.__nuxelBackgrounded === true);
check('Home records BACKGROUND, not a torn-down session', result.harness.appSession.state === 'BACKGROUND', result.harness.appSession.state);
check('Home paints Desktop 1 for a PWA app', result.harness.sessions ? homeSandbox.launcher.currentPage === 0 : false, homeSandbox.launcher.currentPage);

// ------------------------------------------------------------------------- //
// navigation.js: a penguin/Home pointer tap reaches nuxel.home()
// ------------------------------------------------------------------------- //
function loadNavigation() {
  const buttons = ['back', 'home', 'recents'].map(action => {
    const button = eventTarget({ dataset: { nav: action }, classList: { add() {}, remove() {} }, querySelector: () => null, setPointerCapture() {} });
    return button;
  });
  const nav = { querySelectorAll: () => buttons };
  const sandbox = {
    console, setTimeout, clearTimeout, navigator: { vibrate() {} },
    document: eventTarget({ getElementById: (id) => id === 'system-navigation' ? nav : null, querySelectorAll: () => [] }),
    CustomEvent: class { constructor(type, options) { this.type = type; Object.assign(this, options || {}); } },
  };
  sandbox.window = sandbox;
  sandbox.document.addEventListener = () => {};
  sandbox.document.dispatchEvent = () => true;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/navigation.js'), 'utf8'), sandbox);
  return { sandbox, buttons };
}

const navHarness = loadNavigation();
let homeTaps = 0;
navHarness.sandbox.nuxel = { home() { homeTaps++; }, back() {}, recentsToggle() {} };
navHarness.sandbox.nuxelNavigation = new navHarness.sandbox.NuxelSystemNavigation();
const homeButton = navHarness.buttons[1];
homeButton.dispatch('pointerdown', { button: 0, pointerId: 7 });
homeButton.dispatch('pointerup', { pointerId: 7 });
check('penguin/Home pointer tap calls nuxel.home()', homeTaps === 1, homeTaps);
homeButton.dispatch('click', {});
check('the compatibility click does not fire Home twice', homeTaps === 1, homeTaps);

// ------------------------------------------------------------------------- //
// touch-keyboard.js: real field edits, real caret position, hide/show lifecycle
// ------------------------------------------------------------------------- //
function loadKeyboard() {
  const body = eventTarget({ appendChild() {} });
  const head = { appendChild() {} };
  const doc = eventTarget({
    head, body, documentElement: head, activeElement: null,
    createElement(tag) { return eventTarget({ tagName: String(tag).toUpperCase(), style: {}, setAttribute() {} }); },
    querySelectorAll: () => [], execCommand: () => false,
  });
  class EventShim { constructor(type, options) { this.type = type; Object.assign(this, options || {}); } }
  class InputEventShim extends EventShim {}
  class KeyboardEventShim extends EventShim {}
  const sandbox = {
    console, setTimeout, clearTimeout, setInterval: () => 1, clearInterval() {},
    document: doc, navigator: { vibrate() {} }, Event: EventShim,
    InputEvent: InputEventShim, KeyboardEvent: KeyboardEventShim, fetch: null,
    parent: null,
  };
  sandbox.window = sandbox;
  sandbox.parent = sandbox;
  sandbox.NuxelHost = { available: true, action() {} };
  doc.defaultView = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/touch-keyboard.js'), 'utf8'), sandbox);
  sandbox.NuxelTouchKeyboard.enabledOverride = true;
  return sandbox;
}

function fakeInput(win, tag, type) {
  const events = [];
  const field = {
    tagName: tag, type: type || 'text', value: '', isConnected: true, disabled: false, readOnly: false,
    isContentEditable: false, selectionStart: 0, selectionEnd: 0, maxLength: -1,
    ownerDocument: win.document,
    focus() { win.document.activeElement = field; },
    setRangeText(text, start, end) {
      this.value = this.value.slice(0, start) + text + this.value.slice(end);
      this.selectionStart = this.selectionEnd = start + text.length;
    },
    setSelectionRange(start, end) { this.selectionStart = start; this.selectionEnd = end; },
    dispatchEvent(ev) { events.push(ev); return true; },
    addEventListener() {},
  };
  field.events = events;
  return field;
}

const keyboardSandbox = loadKeyboard();
const kb = keyboardSandbox.NuxelTouchKeyboard;
const field = fakeInput(keyboardSandbox, 'INPUT', 'text');
check('keyboard inserts a letter', kb.edit(field, 'N') === true && field.value === 'N', field.value);
check('keyboard leaves the real caret after the letter', field.selectionStart === 1 && field.selectionEnd === 1, field.selectionStart);
check('keyboard emits beforeinput and input', field.events.some(e => e.type === 'beforeinput') && field.events.some(e => e.type === 'input'), field.events.map(e => e.type).join(','));
field.value = 'Nuxel keyboard is alive 123';
field.selectionStart = field.selectionEnd = field.value.length;
const before = field.value.length;
kb.edit(field, 'Backspace');
check('Backspace removes one character and moves the caret', field.value.length === before - 1 && field.selectionStart === field.value.length, JSON.stringify({ value: field.value, caret: field.selectionStart }));
kb.edit(field, ' ');
check('Space inserts a real space', field.value.endsWith(' ') && field.selectionStart === field.value.length, field.value);
kb.edit(field, 'ArrowLeft');
check('ArrowLeft moves the native selection', field.selectionStart === field.value.length - 1, field.selectionStart);

// Contenteditable fields use WebKit's editing command, so the native caret and
// selection stay authoritative.  The harness records the command instead of
// implementing a text editor of its own.
const commands = [];
keyboardSandbox.document.execCommand = (command, ui, text) => { commands.push([command, text]); return true; };
const editable = fakeInput(keyboardSandbox, 'DIV', 'text');
editable.isContentEditable = true;
editable.value = '';
check('contenteditable uses insertText', kb.edit(editable, 'A') === true && commands[0][0] === 'insertText' && commands[0][1] === 'A', JSON.stringify(commands));
kb.edit(editable, 'Backspace');
check('contenteditable uses deleteContentBackward', commands.some(c => c[0] === 'delete'), JSON.stringify(commands));
keyboardSandbox.document.execCommand = () => false;

const form = { submitted: 0, requestSubmit() { this.submitted++; } };
const submitField = fakeInput(keyboardSandbox, 'INPUT', 'text');
submitField.form = form;
kb.edit(submitField, 'Enter');
check('Enter submits an input form through its owner', form.submitted === 1, form.submitted);

// The fallback must be off when a native input-method provider is live, so the
// compositor OSK and this HTML surface can never both appear.
kb.nativeProvider = true;
check('native provider disables the HTML fallback', kb.enabled === false);
kb.nativeProvider = false;
check('HTML fallback returns when the native provider is absent', kb.enabled === true);

// No decorative caret element may be created: the only injected style changes
// the engine caret colour, and hide() does not fabricate a blinking cursor.
check('no fake caret implementation is present', !/nuxel-caret|blink|animation.*caret/i.test(fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/touch-keyboard.js'), 'utf8')) || /This styles the engine's real caret/.test(fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/touch-keyboard.js'), 'utf8')));

console.log(failures ? `${failures} FAILURE(S)` : 'ALL PASS');
process.exit(failures ? 1 : 0);
