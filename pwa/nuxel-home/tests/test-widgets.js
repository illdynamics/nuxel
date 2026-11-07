// PWNAGE-44000 widget-framework test.
// The old test set launcher.currentPage=2 and rendered page 2, which masked
// the real defect: currentPage is ZERO-BASED while persisted widget.desktop is
// ONE-BASED.  This suite drives the actual launcher lifecycle (page 0 = desktop 1,
// page 1 = desktop 2) and the real one-based storage contract.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '../../..');
const SRC = path.join(ROOT, 'pwa/nuxel-home/js/widgets.js');
const LAYOUT_SRC = path.join(ROOT, 'pwa/nuxel-home/js/desktop-layout.js');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}

const src = fs.readFileSync(SRC, 'utf8');
const LEGACY_KEY = 'nuxel.widgets';
function makeSandbox() {
  const store = {};
  const els = {};
  function el(tag) {
    const node = {
      tagName: (tag || 'div').toUpperCase(), children: [], __html: '', __text: '',
      className: '', style: {}, hidden: false, dataset: {}, title: '', tabIndex: 0,
      setAttribute() {}, getAttribute() { return null; },
      appendChild(c) { this.children.push(c); return c; },
      insertBefore(c) { this.children.unshift(c); return c; },
      replaceChildren() { this.children.length = 0; },
      addEventListener() {},
      querySelector() { return null; },
      getBoundingClientRect() { return { left: 0, top: 0, width: 100, height: 60 }; },
    };
    Object.defineProperty(node, 'innerHTML', {
      get() { return this.__html; },
      set(v) { this.__html = String(v == null ? '' : v); this.children.length = 0; },
    });
    Object.defineProperty(node, 'textContent', {
      get() { return this.__text; },
      set(v) {
        this.__text = String(v == null ? '' : v);
        this.__html = this.__text.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
        this.children.length = 0;
      },
    });
    Object.defineProperty(node, 'id', {
      get() { return this.__id || ''; },
      set(v) { this.__id = v; if (v) els[v] = this; },
    });
    return node;
  }
  const appList = el('div');
  const sandbox = {
    console: { log() {}, warn() {} },
    localStorage: {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: k => { delete store[k]; },
    },
    addEventListener() {},
    document: {
      getElementById: id => (id === 'app-list' ? appList : (els[id] || null)),
      createElement: tag => el(tag),
      elementFromPoint: () => null,
      addEventListener() {},
    },
    Date, Math, CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } },
    setInterval: () => 1, clearInterval() {}, setTimeout: () => 1, clearTimeout() {},
    removeEventListener() {},
  };
  sandbox.window = sandbox;
  sandbox.launcher = { currentPage: 0, settings: { gridColumns: 4, desktopCount: 2 } };
  sandbox.appRegistry = { launchApp() {} };
  sandbox.__store = store;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(LAYOUT_SRC, 'utf8'), sandbox);
  vm.runInContext(src, sandbox);
  return sandbox;
}

const s = makeSandbox();
const W = s.NuxelWidgets;
check('widget module exposes NuxelWidgets', !!W);
check('widgets default enabled, empty, unified schema', W.state().enabled === true && W.state().items.length === 0 && W.state().schema_version === 1 && W.state().layout_key === 'nuxel.desktopLayout.v1');

s.__store[W.NOTES_KEY] = JSON.stringify([
  { id: 'note-1', title: 'PWNAGE-44000 Notes Widget Test', body: 'Hello from desktop two', updatedAt: new Date().toISOString() },
]);

const item = W.add('notes', { desktop: 2, noteId: 'note-1', w: 2, h: 2 });
check('add() returns a widget and persists it', !!item && W.state().items.length === 1);
check('persisted desktop is one-based 2', item && Number(item.desktop) === 2);

// Real launcher lifecycle: page index 0 is desktop 1.
s.launcher.currentPage = 0;
W.renderPage(0);
let layer = s.document.getElementById('widgets-layer');
check('desktop 1 (page index 0) hides the desktop-2 widget', !!layer && layer.hidden === true);

// Page index 1 is the human desktop 2.
s.launcher.currentPage = 1;
W.renderPage(1);
layer = s.document.getElementById('widgets-layer');
check('desktop 2 (page index 1) renders the widget', !!layer && layer.hidden === false);
check('widget shows the selected note title', !!layer && layer.children.length === 1 && layer.children[0].children[0].textContent.indexOf('PWNAGE-44000 Notes Widget Test') >= 0);
check('widget body is text, not interpolated HTML', layer.children[0].children[1].textContent.indexOf('Hello from desktop two') >= 0);

// Default desktop uses currentPage + 1.
s.launcher.currentPage = 0;
const auto = W.add('notes', { noteId: 'note-1' });
check('add() defaults to currentPage + 1', auto && auto.desktop === 1);

// Resize/reposition persistence.
W.update(item.id, { w: 3, h: 3 });
let saved = W.state().items.find(w => w.id === item.id);
check('resize persists width/height', saved.w === 3 && saved.h === 3);
W.update(item.id, { desktop: 1 });
saved = W.state().items.find(w => w.id === item.id);
check('move persists desktop', saved.desktop === 1);

// Note edit and deletion are reflected, without stale text.
s.__store[W.NOTES_KEY] = JSON.stringify([{ id: 'note-1', title: 'Edited', body: 'EDITED BODY', updatedAt: new Date().toISOString() }]);
W.update(item.id, { desktop: 2 });
s.launcher.currentPage = 1;
W.renderPage(1);
layer = s.document.getElementById('widgets-layer');
check('widget reflects edited note body', layer.children[0].children[1].textContent.indexOf('EDITED BODY') >= 0);
s.__store[W.NOTES_KEY] = JSON.stringify([]);
W.renderPage(1);
layer = s.document.getElementById('widgets-layer');
check('deleted note leaves a reselect state, not stale text', layer.children[0].children[1].textContent.indexOf('EDITED BODY') < 0 && layer.children[0].children[1].textContent.indexOf('No note selected') >= 0);

// No note -> add refuses instead of creating an empty broken widget.
const before = W.state().items.length;
check('add() with no notes returns null', W.add('notes', { desktop: 2 }) === null && W.state().items.length === before);

// Legacy widget document migration is lossless.
const legacySandbox = makeSandbox();
legacySandbox.__store[LEGACY_KEY] = JSON.stringify({ enabled: true, items: [{ id: 'old', type: 'notes', desktop: 2, noteId: 'note-1', w: 2, h: 2 }] });
const LW = legacySandbox.NuxelWidgets;
check('legacy one-based widget desktop migrates to unified desktop 2', LW.state().items[0].desktop === 2 && LW.state().items[0].id === 'old');

W.setEnabled(false);
s.launcher.currentPage = 1;
W.renderPage(1);
check('disabled widgets hide the layer', s.document.getElementById('widgets-layer').hidden === true);
W.setEnabled(true);
W.remove(item.id);
check('remove() deletes the widget from persisted state', W.state().items.find(w => w.id === item.id) === undefined);

process.exit(failures ? 1 : 0);
