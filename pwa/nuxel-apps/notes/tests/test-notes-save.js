// PWNAGE-44000: durable/serialized Notes saves (Bridge success, failure,
// offline fallback and a write race where an older completion must not mark
// newer text as saved).
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}

const src = fs.readFileSync(path.join(__dirname, '../js/notes.js'), 'utf8');

function makeSandbox(bridgeCall) {
  const store = {};
  const elements = {};
  function classList() {
    const set = new Set();
    return { add: c => set.add(c), remove: c => set.delete(c), contains: c => set.has(c), toggle: (c, on) => on ? set.add(c) : set.delete(c) };
  }
  function node(id) {
    return {
      id, value: '', textContent: '', innerHTML: '', hidden: false, classList: classList(),
      dataset: {}, style: {}, selectionStart: 0, selectionEnd: 0,
      addEventListener() {}, appendChild() {}, replaceChildren() {},
      querySelectorAll() { return []; }, focus() {}, setRangeText() {},
    };
  }
  ['note-title', 'note-body', 'note-meta', 'notes-list', 'note-editor', 'new-note-btn',
   'editor-back', 'editor-save', 'menu-btn'].forEach(id => { elements[id] = node(id); });
  const sandbox = {
    console: { log() {}, warn() {} },
    localStorage: {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: k => { delete store[k]; },
    },
    setTimeout, clearTimeout, Date, isNaN, JSON, Math,
    document: {
      getElementById: id => elements[id] || (elements[id] = node(id)),
      querySelectorAll: () => [],
      addEventListener() {},
      createElement: () => node('temp'),
      body: { appendChild() {} },
      dispatchEvent() {},
    },
    CustomEvent: function (name, opts) { this.type = name; this.detail = opts && opts.detail; },
    __store: store,
    __elements: elements,
  };
  sandbox.window = sandbox;
  sandbox.NuxelBridge = { call: bridgeCall };
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox);
  return sandbox;
}

(async () => {
  const writes = [];
  let failNext = false;
  const s = makeSandbox(async (ns, verb, params) => {
    if (verb === 'write') {
      writes.push(JSON.parse(JSON.stringify(params.data)));
      if (failNext) return { success: false, error: 'disk full' };
      return { success: true, saved: true };
    }
    if (verb === 'read') return { success: true, data: [] };
    return { success: true };
  });
  const app = s.nuxelNotes.app();
  app.notes = [{ id: 'n1', title: 'Old', body: 'old body', updatedAt: new Date().toISOString() }];
  app.currentNote = app.notes[0];
  s.__elements['note-title'].value = 'New title';
  s.__elements['note-body'].value = 'new body';

  const r1 = await app.save();
  check('bridge save succeeds', r1.ok === true);
  check('bridge received the new content', writes.length === 1 && writes[0][0].body === 'new body');
  check('dirty flag clears after confirmed save', app.dirty === false);
  check('local cache has the saved document', JSON.parse(s.__store['nuxel-notes'])[0].body === 'new body');

  // Failure: content must remain dirty and retained.
  failNext = true;
  app.currentNote.body = 'unsaved body';
  s.__elements['note-body'].value = 'unsaved body';
  const r2 = await app.save();
  failNext = false;
  check('bridge failure is reported honestly', r2.ok === false && r2.error === 'disk full');
  check('failed save keeps dirty state', app.dirty === true);
  check('failed save keeps content in the local cache', JSON.parse(s.__store['nuxel-notes'])[0].body === 'unsaved body');

  // Race: two saves; the first completion must not clear the newer revision.
  let releaseFirst;
  const firstGate = new Promise(res => { releaseFirst = res; });
  let call = 0;
  const s2 = makeSandbox(async (ns, verb, params) => {
    if (verb !== 'write') return { success: true, data: [] };
    call++;
    if (call === 1) { await firstGate; return { success: true }; }
    return { success: true };
  });
  const app2 = s2.nuxelNotes.app();
  app2.notes = [{ id: 'n1', title: 'T', body: 'first', updatedAt: new Date().toISOString() }];
  app2.currentNote = app2.notes[0];
  s2.__elements['note-title'].value = 'T';
  s2.__elements['note-body'].value = 'first';
  const p1 = app2.save();
  await Promise.resolve();
  s2.__elements['note-body'].value = 'second';
  app2.currentNote.body = 'second';
  const p2 = app2.save();
  releaseFirst();
  await Promise.all([p1, p2]);
  check('race keeps the newest body dirty until its own write completes', app2.dirty === false);
  check('race persisted both snapshots in order', call === 2);
  check('newest local cache is the second body', JSON.parse(s2.__store['nuxel-notes'])[0].body === 'second');

  process.exit(failures ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
