const fs = require('fs');
const path = require('path');
const { parseHTML } = require('linkedom');
const ROOT = path.resolve(__dirname, '../..');
const ids = ['back-btn','home-btn','refresh-btn','select-btn','selection-bar','selection-label','sel-all','sel-none','sel-cancel','toolbar','new-folder-btn','rename-btn','delete-btn','copy-btn','cut-btn','paste-btn','archive-btn','extract-btn','send-btn','clipboard-info','file-grid','status','cwd-abs','prompt-dialog','prompt-title','prompt-input','prompt-error','prompt-cancel','prompt-ok','confirm-dialog','confirm-text','confirm-cancel','confirm-ok','breadcrumb','send-dialog','send-summary','send-device','send-progress','send-status','send-error','send-close','send-ok','share-bluetooth','share-wifi','share-nearby'];
const html = '<!doctype html><html><body>' + ids.map(i => `<div id="${i}"></div>`).join('') + '<script></script></body></html>';
const { window, document } = parseHTML(html);
global.window = window; global.document = document;
window.requestAnimationFrame = fn => setTimeout(fn, 0);
window.localStorage = { getItem(){return null;}, setItem(){}, removeItem(){} };
const src = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-apps/files/js/files.js'), 'utf8');
window.eval(src);
const app = window.nuxelFiles.app();
const N = 1000;
const entries = [];
for (let i=0;i<N;i++) entries.push({ name: 'file-'+i+'.txt', path: '/dir/file-'+i+'.txt', type: 'file', size: 1024+i, modified: 1700000000 });
app.entries = entries; app.cwd='/dir'; app.home='/home/nuxel';
const grid = document.getElementById('file-grid');

function legacyRender() {
  const self = app;
  grid.innerHTML = self.entries.map(function (f) {
    var isSel = self.selected.has(f.path);
    var icon = f.type === 'folder' ? 'X' : self.iconFor(f.name);
    var meta = self.formatSize(f.size) + (f.modified ? ' - ' + new Date(f.modified * 1000).toLocaleDateString() : '');
    return '<div class="file-item' + (isSel ? ' selected' : '') + '" data-path="' + self.esc(f.path) + '" data-type="' + self.esc(f.type) + '">' +
      '<div class="file-icon">' + icon + '</div><div class="file-name">' + self.esc(f.name) + '</div><div class="file-meta">' + self.esc(meta) + '</div></div>';
  }).join('');
  grid.querySelectorAll('.file-item').forEach(function (item) { item.addEventListener('click', function () {}); });
}
async function newRender() {
  app.render();
  while (grid.children.length < N) await new Promise(r => setTimeout(r, 1));
}
(async () => {
  const times = { legacy: [], progressive: [] };
  for (let i=0;i<20;i++) {
    grid.innerHTML='';
    let t=performance.now(); legacyRender(); times.legacy.push(performance.now()-t);
    grid.innerHTML='';
    t=performance.now(); await newRender(); times.progressive.push(performance.now()-t);
  }
  const stat = a => { const s=a.slice().sort((x,y)=>x-y); return { p50:+s[Math.floor(s.length*.5)].toFixed(2), p95:+s[Math.floor(s.length*.95)].toFixed(2), avg:+(a.reduce((x,y)=>x+y,0)/a.length).toFixed(2) }; };
  const L=stat(times.legacy), P=stat(times.progressive);
  console.log(JSON.stringify({ entries:N, iterations:times.legacy.length, legacy:L, progressive:P,
    p50_improvement_pct:+(((L.p50-P.p50)/L.p50)*100).toFixed(1),
    p95_improvement_pct:+(((L.p95-P.p95)/L.p95)*100).toFixed(1) }, null, 2));
})();
