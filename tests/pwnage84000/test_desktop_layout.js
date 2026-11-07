const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '../..');
const src = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/js/desktop-layout.js'), 'utf8');
let failures = 0;
function check(name, ok, extra) { console.log((ok ? 'PASS ' : 'FAIL ') + name + (ok ? '' : '  ' + (extra || ''))); if (!ok) failures++; }
function sandbox() {
  const store = {};
  const s = {
    console,
    localStorage: { getItem: k => store[k] || null, setItem: (k, v) => { store[k] = String(v); } },
    __store: store,
  };
  s.window = s;
  vm.createContext(s);
  vm.runInContext(src, s);
  return s;
}
const s = sandbox();
const L = s.NuxelDesktopLayout;
const layout = L.load({ columns: 4, rows: 5, desktopCount: 2, apps: ['a', 'b', 'c', 'd', 'e'], appOrder: ['a','b','c','d','e'] });
check('migration creates one app entity per shortcut', layout.entities.filter(e => e.type === 'app').length === 5);
check('apps receive unique zero-based cells', new Set(layout.entities.map(e => e.desktop + ':' + e.x + ':' + e.y)).size === 5);
check('schema is versioned', layout.snapshot().schema_version === 1 && layout.snapshot().desktop_count === 2);

const w = layout.addWidget('notes', { desktop: 1, noteId: 'n1' }, { w: 2, h: 2 });
check('widget is placed on selected zero-based desktop', !!w && w.desktop === 0 && w.w === 2 && w.h === 2);
const area = layout.entitiesOn(0).reduce((n, e) => n + e.w * e.h, 0);
check('widget and icons do not share a cell', layout.occupancy(0).size === area);
check('slot under a widget is collision-free', layout.canPlace(0, w.x, w.y, 1, 1) === false);
check('free cell exists outside the widget', layout.canPlace(0, w.x + w.w, w.y, 1, 1) === true);

const appB = layout.entity('b');
const moved = layout.move('b', 1, 3, 4);
check('app moves to a free cell on another desktop', moved && moved.desktop === 1 && moved.x === 3 && moved.y === 4);
check('app is now owned by only desktop 2', layout.apps(1).some(e => e.ref === 'b') && !layout.apps(0).some(e => e.ref === 'b'));
const blocked = layout.move('c', 1, 3, 4);
check('collision resolves to nearest free valid cell', blocked && !(blocked.x === 3 && blocked.y === 4));
const resized = layout.resize(w.id, 3, 2);
check('resize succeeds when no collision', resized && resized.w === 3 && resized.h === 2);
const refused = layout.resize(w.id, 4, 5);
check('impossible resize is refused instead of overlapping icons', refused === null);

const fullSandbox = sandbox();
const full = fullSandbox.NuxelDesktopLayout.load({ columns: 3, rows: 4, desktopCount: 1, apps: Array.from({length: 12}, (_, i) => 'f' + i) });
check('a full desktop has no free cell for another widget', full.findFree(0, 1, 1, null) === null);
const extra = full.addWidget('calendar', { desktop: 1 }, { w: 2, h: 2 });
check('overflow creates a new desktop rather than dropping the widget', extra && extra.desktop === 1 && full.desktopCount >= 2);

layout.save();
const reloaded = L.load({ columns: 4, rows: 5, desktopCount: 2, apps: ['a','b','c','d','e'] });
check('saved layout reloads with widget ownership intact', reloaded.widgets(0).length === 1 && reloaded.apps(1).some(e => e.ref === 'b'));

const legacy = sandbox();
legacy.__store['legacy'] = JSON.stringify({ enabled: true, items: [{ id: 'w-old', type: 'notes', desktop: 2, noteId: 'x', w: 2, h: 2 }] });
const migrated = legacy.NuxelDesktopLayout.load({
  key: 'legacy', columns: 4, rows: 5, desktopCount: 2,
  apps: ['a'], appOrder: ['a'],
  legacyWidgets: { items: [{ id: 'w-old', type: 'notes', desktop: 2, noteId: 'x', w: 2, h: 2 }] }
});
check('legacy one-based widget desktop migrates to zero-based 1', migrated.widgets(1).length === 1 && migrated.widgets(0).length === 0);

// P84000 regression: a legacy app list larger than one grid used to make
// _migrate dereference a null placement and abort the whole launcher.
const overflowSandbox = sandbox();
let overflow = null;
let overflowError = null;
try {
  overflow = overflowSandbox.NuxelDesktopLayout.load({
    columns: 3, rows: 4, desktopCount: 1,
    apps: Array.from({length: 30}, (_, i) => 'o' + i),
    appOrder: Array.from({length: 30}, (_, i) => 'o' + i),
  });
} catch (e) { overflowError = e; }
check('legacy app overflow migrates without throwing', !overflowError, overflowError && overflowError.message);
check('legacy app overflow keeps every shortcut', !!overflow && overflow.entities.filter(e => e.type === 'app').length === 30);
check('legacy app overflow expands desktops', !!overflow && overflow.desktopCount >= 3);
check('legacy app overflow has unique cells', !!overflow && new Set(overflow.entities.map(e => e.desktop + ':' + e.x + ':' + e.y)).size === 30);

process.exit(failures ? 1 : 0);
