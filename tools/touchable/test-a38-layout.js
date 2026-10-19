const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const box = { window: {}, Date: { now: () => 42 } }; box.window = box;
vm.createContext(box);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../pwa/nuxel-home/js/layout-model.js'), 'utf8'), box);
const Layout = box.NuxelHomeLayout;
function top(layout) { return JSON.parse(JSON.stringify(layout.entries.map(e => typeof e === 'string' ? e : '[' + e.items.join(',') + ']'))); }
let l = new Layout(['A','B','C','D']);
l.insertApp('D', 1); assert.deepEqual(top(l), ['A','D','B','C']);
l.insertApp('A', 3); assert.deepEqual(top(l), ['D','B','C','A']);
assert.equal(l.createFolder('D', 'B'), true); assert.deepEqual(top(l), ['[B,D]','C','A']);
const folder = l.entries[0]; assert.equal(l.renameFolder(folder.id, 'Work'), true); assert.equal(folder.name, 'Work');
assert.equal(l.addToFolder('A', folder.id), true); assert.deepEqual(Array.from(folder.items), ['B','D','A']);
assert.equal(l.removeFromFolder('D', folder.id, 1), true); assert.deepEqual(top(l), ['[B,A]','D','C']);
const saved = JSON.parse(JSON.stringify(l.snapshot())), restored = new Layout(['A','B','C','D'], saved); assert.deepEqual(JSON.parse(JSON.stringify(restored.snapshot())), saved);
console.log('PASS A38 deterministic insertion, folders, removal and persistence');
