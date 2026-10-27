// PWNAGE-30000 widget-framework unit test (node, DOM-light sandbox).
// Exercises the widget registry, per-desktop placement persistence, render
// isolation between desktop 1/2, enable/disable and Notes synchronization.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '../../..');
const SRC = path.join(ROOT, 'pwa/nuxel-home/js/widgets.js');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}

const src = fs.readFileSync(SRC, 'utf8');
function makeSandbox() {
  const store = {};
  const els = {};
  function el(tag) {
    const node = { tagName: (tag || 'div').toUpperCase(), children: [], __html: '',
      className: '', style: {}, hidden: false, dataset: {},
      setAttribute() {}, appendChild(c) { this.children.push(c); return c; },
      insertBefore(c) { this.children.unshift(c); return c; },
      addEventListener() {}, title: '' };
    Object.defineProperty(node, 'innerHTML', {
      get() { return this.__html; },
      set(v) { this.__html = String(v == null ? '' : v); this.children.length = 0; }
    });
    Object.defineProperty(node, 'id', {
      get() { return this.__id || ''; },
      set(v) { this.__id = v; if (v) els[v] = this; }
    });
    Object.defineProperty(node, 'textContent', {
      get() { return this.__text || ''; },
      set(v) {
        this.__text = String(v == null ? '' : v);
        this.innerHTML = this.__text.replace(/[&<>]/g, function (c) {
          return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
        });
      }
    });
    return node;
  }
  const appList = el('div');
  const sandbox = {
    console: { log() {}, warn() {} },
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    },
    addEventListener() {},
    document: {
      getElementById: (id) => (id === 'app-list' ? appList : (els[id] || null)),
      createElement: (tag) => el(tag),
    },
    Date: Date,
  };
  sandbox.window = sandbox;
  sandbox.launcher = { currentPage: 1, settings: { gridColumns: 4 } };
  sandbox.appRegistry = { launchApp: () => {} };
  sandbox.__store = store;
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox);
  return sandbox;
}

const s = makeSandbox();
const W = s.NuxelWidgets;
check('widget module exposes NuxelWidgets', !!W);
check('widgets default to enabled with no items', W.state().enabled === true && W.state().items.length === 0);

s.__store[W.NOTES_KEY] = JSON.stringify([
  { id: 'note-1', title: 'PWNAGE-30000 Notes Widget Test', body: 'Hello from desktop two', updatedAt: new Date().toISOString() },
]);
const item = W.add('notes', { desktop: 2, noteId: 'note-1', w: 2, h: 2 });
check('add() returns a widget and persists it', !!item && W.state().items.length === 1);
check('widget is assigned to desktop 2', item && Number(item.desktop) === 2);

// Render page 2: the layer must be visible and contain the note title.
s.launcher.currentPage = 2;
W.renderPage(2);
const layer2 = s.document.getElementById('widgets-layer');
check('desktop 2 renders a widget layer', !!layer2 && layer2.hidden === false);
check('desktop 2 widget shows the selected note title', !!layer2 && layer2.children.length === 1 && layer2.children[0].innerHTML.indexOf('PWNAGE-30000 Notes Widget Test') >= 0);

// Render page 1: no widget assigned there.
s.launcher.currentPage = 1;
W.renderPage(1);
check('desktop 1 hides the widget layer', s.document.getElementById('widgets-layer').hidden === true);

// Notes edits re-render (the storage event path is exercised by renderPage).
s.__store[W.NOTES_KEY] = JSON.stringify([
  { id: 'note-1', title: 'PWNAGE-30000 Notes Widget Test', body: 'EDITED BODY', updatedAt: new Date().toISOString() },
]);
s.launcher.currentPage = 2;
W.renderPage(2);
check('widget reflects the edited note body', s.document.getElementById('widgets-layer').children[0].innerHTML.indexOf('EDITED BODY') >= 0);

W.setEnabled(false);
s.launcher.currentPage = 2;
W.renderPage(2);
check('disabled widgets hide the layer', s.document.getElementById('widgets-layer').hidden === true);

W.setEnabled(true);
W.remove(item.id);
check('remove() deletes the widget from persisted state', W.state().items.length === 0);

process.exit(failures ? 1 : 0);
