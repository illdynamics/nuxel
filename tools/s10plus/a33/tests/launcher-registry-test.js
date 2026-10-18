// A33 launcher-parity test (briq-02d) — "the launcher the phone serves is the
// launcher the repository owns".
//
// WHY THIS EXISTS
//   On the handset the launcher page was fine but its ASSETS had drifted: the
//   device copy of js/status-bar.js was v0.3.2 while the repository was already
//   v0.5.1-alpha, manifest.json was stale, the registry had no Terminal entry and
//   nuxel-settings had no runnable frontend.  The A32 fix was the service-worker
//   cache bump (INV-1) + the authoritative PWA tree.  This test is the repository
//   half of that fix: it fails if the three version stamps ever diverge, if the
//   cache namespace goes backwards, if a registry app points at an asset that is
//   not in the tree, or if a stale bundled copy of the launcher reappears.
//
// WHAT IT ASSERTS (all offline, no browser, no host):
//   1. the registry contains org.nuxel.Terminal and nuxel-settings (the two A33
//      additions), and every entry is launchable;
//   2. every PWA entry resolves to a real file under /pwa/nuxel-apps/ and that
//      app directory carries a valid manifest.json (name + start_url);
//   3. pwa/nuxel-home/manifest.json, js/status-bar.js and sw.js agree on ONE
//      version triple (pwa_version / StatusBar.VERSION / cache_version suffix);
//   4. the service-worker CACHE_VERSION has ADVANCED past the A32 baseline
//      'v3-a32' and every launcher asset (including the A33 additions) is in the
//      precache list;
//   5. the manifest shortcuts resolve to registry ids, and the manifest's
//      settings_documents are the ones the boot settings actually use;
//   6. no stale device copy of a launcher asset is bundled in the repo;
//   7. the launcher BEHAVES: activation opens a real frame with exactly one owner,
//      closing it returns home, the registry is the search matcher, the manifest
//      #app=<id> deeplinks navigate, and the grid is the scrollable surface the
//      finger drags (bg-02 verification pass).
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HOME = path.join(__dirname, '../../../../pwa/nuxel-home');
const PWA = path.join(__dirname, '../../../../pwa/nuxel-apps');
const ROOT = path.join(__dirname, '../../../..');

let failures = 0;
let warnings = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}
function warn(name, extra) {
  console.log('WARN ' + name + (extra === undefined ? '' : '  ' + extra));
  warnings++;
}
function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return null; }
}

// --------------------------------------------------------------------------- //
// 1. the registry itself
// --------------------------------------------------------------------------- //
const appsSrc = fs.readFileSync(path.join(HOME, 'js/apps.js'), 'utf8');
const sandbox = {
  console: console,
  document: { addEventListener() {}, dispatchEvent() {}, readyState: 'complete' },
  window: {},
  localStorage: { getItem: () => null, setItem() {} },
  CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
  setTimeout: setTimeout,
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(appsSrc + '\nthis.__apps = NUXEL_APPS; this.__ver = NUXEL_REGISTRY_VERSION;', sandbox);
const apps = sandbox.__apps || {};
const registryVersion = sandbox.__ver;

check('registry loaded', !!apps && Object.keys(apps).length >= 10, JSON.stringify(Object.keys(apps)));
check('registry carries a machine-readable revision', Number.isInteger(registryVersion) && registryVersion >= 3, registryVersion);

// The two additions this briq is responsible for.
check('registry has org.nuxel.Terminal', !!apps['org.nuxel.Terminal'], JSON.stringify(Object.keys(apps)));
check('registry has nuxel-settings', !!apps['nuxel-settings']);

// The A32 baseline entries must not have been removed by the A33 refresh.
for (const id of ['nuxel-dialer', 'nuxel-messages', 'nuxel-contacts', 'org.nuxel.Mail',
                  'org.nuxel.Calendar', 'org.nuxel.Notes', 'org.nuxel.Files', 'nuxel-camera']) {
  check('A32 registry entry kept: ' + id, !!apps[id]);
}

for (const [id, app] of Object.entries(apps)) {
  check('entry ' + id + ' is launchable (id/name/url/type/category)',
        app && app.id === id && typeof app.name === 'string' && app.name.length > 1 &&
        typeof app.url === 'string' && app.url.length > 1 &&
        (app.type === 'native' || app.type === 'pwa') && typeof app.category === 'string',
        JSON.stringify(app));
}
check('settings is a served PWA, not the native placeholder',
      apps['nuxel-settings'] && apps['nuxel-settings'].type === 'pwa' &&
      /^\/pwa\/nuxel-apps\/settings\//.test(apps['nuxel-settings'].url),
      apps['nuxel-settings'] && (apps['nuxel-settings'].type + ' ' + apps['nuxel-settings'].url));
check('terminal is a served PWA under the authoritative tree',
      apps['org.nuxel.Terminal'] && apps['org.nuxel.Terminal'].type === 'pwa' &&
      /^\/pwa\/nuxel-apps\/terminal\//.test(apps['org.nuxel.Terminal'].url),
      apps['org.nuxel.Terminal'] && apps['org.nuxel.Terminal'].url);

// --------------------------------------------------------------------------- //
// 2. every PWA entry resolves to a served file, with a valid app manifest
// --------------------------------------------------------------------------- //
const pwaEntries = Object.values(apps).filter((a) => a.type === 'pwa');
check('every PWA url lives under /pwa/nuxel-apps/',
      pwaEntries.length > 0 && pwaEntries.every((a) => a.url.startsWith('/pwa/nuxel-apps/')),
      JSON.stringify(pwaEntries.map((a) => a.url)));

// Entries whose tree THIS briq owns (the A32 baseline + the Terminal/Settings
// additions) are pinned strictly: a missing asset is a FAIL.  Entries added by
// the parallel application groups are reported as a WARN while their tree lands,
// so this test never turns another group's work-in-progress into red.
const STRICT = new Set(['nuxel-settings', 'org.nuxel.Terminal', 'org.nuxel.Mail',
                        'org.nuxel.Calendar', 'org.nuxel.Notes', 'org.nuxel.Files']);
for (const app of pwaEntries) {
  const abs = path.join(ROOT, app.url.replace(/^\//, ''));
  const exists = fs.existsSync(abs);
  const mfManifest = path.join(path.dirname(abs), 'manifest.json');
  const m = readJson(mfManifest);
  const manifestOk = !!(m && typeof m.name === 'string' && typeof m.start_url === 'string');
  if (STRICT.has(app.id)) {
    check('served asset exists for ' + app.id + ' (' + app.url + ')', exists, abs);
    check('app manifest valid for ' + app.id, manifestOk,
          fs.existsSync(mfManifest) ? 'unparseable or missing keys' : 'manifest.json absent');
  } else if (!exists || !manifestOk) {
    warn('registry entry ' + app.id + ' is not fully served yet (' + app.url + ')' +
         ' - owned by another build group, not a bg-02 regression');
  } else {
    check('registry entry ' + app.id + ' is served with a valid manifest', true);
  }
}
const settingDocs = ['settings'];
for (const d of settingDocs) {
  check('nuxel-apps/' + d + ' frontend is runnable (index.html + js)',
        fs.existsSync(path.join(PWA, d, 'index.html')) &&
        fs.readdirSync(path.join(PWA, d)).some((f) => f.endsWith('.js')),
        path.join(PWA, d));
}
// Manifests of apps owned by other groups are checked too, but only as a warning:
// those trees are being written in parallel and are not this briq's regression.
for (const d of fs.readdirSync(PWA)) {
  const mf = path.join(PWA, d, 'manifest.json');
  if (!fs.existsSync(mf)) continue;
  const m = readJson(mf);
  if (!m || typeof m.name !== 'string' || typeof m.start_url !== 'string') {
    warn('app manifest for /' + d + ' is not (yet) valid JSON with name+start_url');
  }
}

// --------------------------------------------------------------------------- //
// 3. one version triple: manifest.json == status-bar.js == sw.js
// --------------------------------------------------------------------------- //
const manifest = readJson(path.join(HOME, 'manifest.json'));
check('launcher manifest.json parses', !!manifest);
const pwaVersion = manifest && manifest.nuxel && manifest.nuxel.pwa_version;
const cacheVersion = manifest && manifest.nuxel && manifest.nuxel.cache_version;
check('manifest carries nuxel.pwa_version', typeof pwaVersion === 'string' && /^\d+\.\d+\.\d+/.test(pwaVersion), pwaVersion);
check('manifest carries nuxel.cache_version', typeof cacheVersion === 'string', cacheVersion);
check('manifest declares this tree the single source of truth',
      !!(manifest && manifest.nuxel && /pwa\/nuxel-home/.test(String(manifest.nuxel.single_source_of_truth))),
      manifest && manifest.nuxel && manifest.nuxel.single_source_of_truth);

const statusBarSrc = fs.readFileSync(path.join(HOME, 'js/status-bar.js'), 'utf8');
const sbMatch = /static\s+get\s+VERSION\s*\(\)\s*\{\s*return\s+'([^']+)'/.exec(statusBarSrc) ||
                /VERSION\s*[:=]\s*'([^']+)'/.exec(statusBarSrc);
const statusBarVersion = sbMatch && sbMatch[1];
check('status-bar.js exposes a machine-readable VERSION', !!statusBarVersion, statusBarVersion);
check('status-bar.js VERSION == manifest pwa_version (' + pwaVersion + ')',
      statusBarVersion === pwaVersion, statusBarVersion + ' vs ' + pwaVersion);
check('status-bar.js reports a newer revision than the stale v0.3.2 device copy',
      !!statusBarVersion && statusBarVersion !== '0.3.2', statusBarVersion);

const swSrc = fs.readFileSync(path.join(HOME, 'sw.js'), 'utf8');
const swMatch = /const\s+CACHE_VERSION\s*=\s*'([^']+)'/.exec(swSrc);
const swVersion = swMatch && swMatch[1];
check('sw.js declares an explicit CACHE_VERSION', !!swVersion, swVersion);
check('sw.js CACHE_VERSION == manifest cache_version (' + cacheVersion + ')',
      swVersion === cacheVersion, swVersion + ' vs ' + cacheVersion);

// --------------------------------------------------------------------------- //
// 4. cache invalidation: the namespace must ADVANCE past the A32 baseline
// --------------------------------------------------------------------------- //
const A32_CACHE_VERSION = 'v3-a32';
const numOf = (v) => { const m = /^v(\d+)/.exec(String(v || '')); return m ? parseInt(m[1], 10) : -1; };
check('sw.js cache namespace advanced past the A32 baseline ' + A32_CACHE_VERSION,
      numOf(swVersion) > numOf(A32_CACHE_VERSION), swVersion + ' <= ' + A32_CACHE_VERSION);
check('sw.js activate deletes the previous namespaces', /caches\.delete\(/.test(swSrc));
check('sw.js keeps the A32 network-first rule for code assets',
      /networkFirst|fetch\(request\)[\s\S]*caches\.open/.test(swSrc));

const precacheMatch = /const\s+PRECACHE_ASSETS\s*=\s*\[([\s\S]*?)\]/.exec(swSrc);
const precache = precacheMatch ? precacheMatch[1] : '';
for (const asset of ['./js/status-bar.js', './js/qs.js', './js/safe-zones.js',
                     './js/settings-store.js', './js/bootlog.js', './manifest.json',
                     './assets/nuxel-background.png']) {
  check('precache list contains ' + asset, precache.includes(asset));
}
// Every precached path must exist on disk (a promise the worker keeps at install).
let missing = [];
for (const m of precache.matchAll(/'\.\/([^']*)'/g)) {
  const rel = m[1];
  if (!rel) continue; // './' == the scope root
  if (!fs.existsSync(path.join(HOME, rel))) missing.push(rel);
}
check('every precached asset exists in the tree', missing.length === 0, JSON.stringify(missing));

// The launcher page must actually load the A33 modules.
const indexHtml = fs.readFileSync(path.join(HOME, 'index.html'), 'utf8');
for (const s of ['js/apps.js', 'js/status-bar.js', 'js/qs.js', 'js/safe-zones.js',
                 'js/settings-store.js', 'js/app.js']) {
  check('index.html loads ' + s, indexHtml.includes(s));
}

// --------------------------------------------------------------------------- //
// 5. manifest shortcuts resolve to real registry ids
// --------------------------------------------------------------------------- //
const shortcuts = (manifest && manifest.shortcuts) || [];
check('manifest exposes shortcuts (Terminal/Settings/Console)', shortcuts.length >= 3, shortcuts.length);
for (const sc of shortcuts) {
  const m = /#app=([^&]+)$/.exec(sc.url || '');
  check('shortcut "' + sc.name + '" points at a registry id',
        !!(m && apps[decodeURIComponent(m[1])]),
        sc.url);
}
const docs = (manifest && manifest.nuxel && manifest.nuxel.settings_documents) || [];
for (const want of ['/etc/nuxel/boot/verbose-boot.json', '/etc/nuxel/boot/animation-handoff.json',
                    '/etc/nuxel/display/statusbar-safezones.json', '/etc/nuxel/input/buttons.json']) {
  check('manifest settings_documents lists ' + want, docs.includes(want), JSON.stringify(docs));
}
check('manifest apps_in_registry matches the registry ids',
      !!manifest && JSON.stringify((manifest.nuxel.apps_in_registry || []).slice().sort()) ===
                    JSON.stringify(Object.keys(apps).sort()),
      JSON.stringify(manifest && manifest.nuxel.apps_in_registry));
check('manifest registry_version matches the registry revision',
      !!manifest && manifest.nuxel.registry_version === registryVersion,
      manifest && manifest.nuxel.registry_version);

// --------------------------------------------------------------------------- //
// 6. no stale bundled copy of a launcher asset
// --------------------------------------------------------------------------- //
for (const bad of ['pwa/nuxel-home/js/status-bar.js.orig', 'pwa/nuxel-home/status-bar.js',
                   'pwa/nuxel-home/js/bundle.js']) {
  check('no stale duplicate launcher asset ' + bad, !fs.existsSync(path.join(ROOT, bad)));
}
// A v0.3.2 stamp must not survive as a VERSION CONSTANT anywhere.  The string is
// allowed in prose (status-bar.js documents the drift it fixes), so only an
// assignment/return of the old value counts as the stale copy coming back.
const staleVersionRe = /(?:VERSION|version)\s*[:=]\s*['"]0\.3\.2/;
const staleFiles = fs.readdirSync(path.join(HOME, 'js'))
  .filter((f) => staleVersionRe.test(fs.readFileSync(path.join(HOME, 'js', f), 'utf8')));
check('no v0.3.2 launcher version constant survives under pwa/nuxel-home/js',
      staleFiles.length === 0, JSON.stringify(staleFiles));

// --------------------------------------------------------------------------- //
// 7. LAUNCHER BEHAVIOUR (briq-02d): activation, search, deeplink navigation,
//    scrolling and close-and-return-home.  These are exercised against the REAL
//    code (js/apps.js registry + js/app.js controller) inside a minimal DOM
//    shell, so what is asserted is the launcher's own behaviour and not a copy of
//    it.  No browser, no host, no phone.
// --------------------------------------------------------------------------- //
function makeDom(startHash) {
  const listeners = {};
  function el(tag) {
    const node = {
      tagName: tag, children: [], className: '', textContent: '', innerHTML: '',
      style: { cssText: '' }, dataset: {}, attrs: {}, parentNode: null,
      setAttribute(k, v) { this.attrs[k] = v; },
      getAttribute(k) { return this.attrs[k]; },
      appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
      removeChild(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; },
      insertBefore(c) { return this.appendChild(c); },
      remove() { if (this.parentNode) this.parentNode.removeChild(this); },
      addEventListener() {}, removeEventListener() {},
      querySelectorAll() { return []; }, querySelector() { return null; },
      onclick: null,
    };
    node.classList = { add() {}, remove() {}, contains() { return false; } };
    return node;
  }
  const body = el('body');
  const document = {
    readyState: 'complete',
    body: body,
    createElement: el,
    getElementById() { return null; },
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    dispatchEvent(ev) { (listeners[ev.type] || []).slice().forEach((f) => f(ev)); return true; },
    querySelectorAll(sel) {
      const want = String(sel).split(',').map((x) => x.trim().replace(/^\./, ''));
      const out = [];
      (function walk(n) {
        for (const c of n.children) {
          if (String(c.className).split(/\s+/).some((k) => want.includes(k))) out.push(c);
          walk(c);
        }
      })(body);
      return out;
    },
  };
  const win = {
    location: { hash: startHash || '', search: '', href: 'http://127.0.0.1:8000/pwa/nuxel-home/index.html' + (startHash || '') },
    addEventListener(t, f) { (listeners['win:' + t] = listeners['win:' + t] || []).push(f); },
    dispatchEvent(ev) { (listeners['win:' + ev.type] || []).slice().forEach((f) => f(ev)); return true; },
  };
  const timers = [];
  const sandbox = {
    console: { log() {}, warn() {}, error() {} }, document: document, window: win,
    localStorage: { getItem: () => null, setItem() {} },
    CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
    URLSearchParams: URLSearchParams,
    setTimeout: (fn) => { timers.push(fn); return timers.length; },
    clearTimeout() {},
    navigator: {
      serviceWorker: {
        register: () => Promise.resolve({ scope: '/pwa/nuxel-home/', addEventListener() {}, installing: { addEventListener() {}, state: 'installed' } }),
        controller: null, addEventListener() {},
      },
    },
    bridge: { requestCapability: () => Promise.resolve(true), endCall() {}, getPhoneStatus: () => Promise.resolve({}) },
    fetch: () => Promise.resolve({ ok: false, text: () => Promise.resolve('') }),
    Promise: Promise,
  };
  sandbox.self = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  return { sandbox, flush: () => { while (timers.length) timers.shift()(); }, document, win };
}

async function tick() { await new Promise((resolve) => setImmediate(resolve)); }

function loadLauncher(startHash) {
  const dom = makeDom(startHash);
  vm.runInContext(fs.readFileSync(path.join(HOME, 'js/apps.js'), 'utf8'), dom.sandbox);
  // app.js defines class NuxelHome and instantiates it on DOMContentLoaded; drive
  // that signal explicitly so the controller is the real one.
  vm.runInContext(fs.readFileSync(path.join(HOME, 'js/app.js'), 'utf8'), dom.sandbox);
  return dom;
}

(async function behaviourSection() {
// --- 7a. activation: registry -> app:launch -> the controller opens a frame ---
{
  const dom = loadLauncher();
  const launched = [];
  dom.document.addEventListener('app:launch', (ev) => launched.push(ev.detail.app.id));
  vm.runInContext("document.dispatchEvent(new CustomEvent('DOMContentLoaded'))", dom.sandbox);
  await tick();                       // NuxelHome._init() is async: let it bind
  dom.flush();
  const reg = vm.runInContext('appRegistry', dom.sandbox);
  check('the registry is exposed to the launcher host (window.appRegistry)', !!reg);
  check('the real controller booted and bound its events',
        !!vm.runInContext('window.nuxel && window.nuxel.initialized', dom.sandbox));
  reg.launchApp('nuxel-settings');
  check('activation dispatches app:launch for the requested id',
        launched[launched.length - 1] === 'nuxel-settings', JSON.stringify(launched));
  check('activation records the app in the recents list',
        reg.getRecentApps().some((a) => a.id === 'nuxel-settings'));
  const frames = dom.document.querySelectorAll('.pwa-frame');
  check('activation actually opens the app frame (real controller, not a mock)',
        frames.length === 1, frames.length);
  check('the opened frame points at the app url from the registry',
        frames.length === 1 && frames[0].src === (reg.getApp('nuxel-settings').url || reg.getApp('nuxel-settings').url),
        frames.length === 1 ? frames[0].src : '');
  check('the frame is fullscreen and above the launcher (fixed inset:0 / z-index)',
        frames.length === 1 && /position:\s*fixed/.test(frames[0].style.cssText)
        && /inset:\s*0/.test(frames[0].style.cssText) && /z-index:\s*9999/.test(frames[0].style.cssText));
  // --- 7b. close-and-return-home ---
  const closeBtn = dom.document.querySelectorAll('.pwa-close-btn')[0];
  check('a close control is created with the frame', !!closeBtn && closeBtn.textContent === '✕');
  closeBtn.onclick();
  check('closing the app removes the frame (returns to the launcher)',
        dom.document.querySelectorAll('.pwa-frame').length === 0);
  check('closing the app removes the close control',
        dom.document.querySelectorAll('.pwa-close-btn').length === 0);
  // opening a second app must not stack a second frame
  reg.launchApp('org.nuxel.Terminal'); reg.launchApp('nuxel-settings');
  check('activation of a second app does not stack frames (one owner)',
        dom.document.querySelectorAll('.pwa-frame').length === 1,
        dom.document.querySelectorAll('.pwa-frame').length);
  // the controller closes overlays on the logical "home" action
  const nuxel = vm.runInContext('window.nuxel', dom.sandbox);
  let searchClosed = 0, qsClosed = 0;
  nuxel.components.search = { close() { searchClosed++; } };
  nuxel.components.qs = { close() { qsClosed++; } };
  dom.document.dispatchEvent(new dom.sandbox.CustomEvent('nuxel:action', { detail: { action: 'home' } }));
  check('the logical "home" action closes overlays (return-home)',
        searchClosed === 1 && qsClosed === 1, [searchClosed, qsClosed].join('/'));
  // A34 TOUCHDOWN: app iframes call window.parent.NuxelLauncherClose() from their
  // own Close buttons.  It existed nowhere, so those buttons did nothing.
  check('the launcher exposes the same-origin app close hook',
        typeof vm.runInContext('window.NuxelLauncherClose', dom.sandbox) === 'function');
  const statusBarSrc = fs.readFileSync(path.join(HOME, 'js/status-bar.js'), 'utf8');
  check('the status bar wires a real vertical pull to gesture:qs',
        /gesture:qs/.test(statusBarSrc) && /pointermove/.test(statusBarSrc) &&
        /PULL_PX\s*=\s*24/.test(statusBarSrc));
}

// --- 7c. search: the registry is the matcher the UI uses ---
{
  const dom = loadLauncher();
  vm.runInContext("document.dispatchEvent(new CustomEvent('DOMContentLoaded'))", dom.sandbox);
  await tick();
  const reg = vm.runInContext('appRegistry', dom.sandbox);
  check('an empty query returns no results', reg.searchApps('').length === 0);
  const byName = reg.searchApps('term');
  check('search finds the Terminal by name', byName.some((a) => a.id === 'org.nuxel.Terminal'),
        JSON.stringify(byName.map((a) => a.id)));
  check('a name match is ranked as a name match', byName[0] && byName[0].matchType === 'name', byName[0] && byName[0].matchType);
  check('search is case-insensitive', reg.searchApps('TERMINAL').length === byName.length);
  const byCategory = reg.searchApps('system');
  check('search matches the category too', byCategory.length >= 2, byCategory.length);
  check('a nonsense query returns nothing (no fake results)', reg.searchApps('zzzzqqq').length === 0);
  const search = fs.readFileSync(path.join(HOME, 'js/search.js'), 'utf8');
  check('the search UI delegates to the registry matcher (no second implementation)',
        /searchApps\(/.test(search) && /launchApp\(/.test(search));
}

// --- 7d. navigation: the manifest deeplink (#app=<id>) launches the real app ---
{
  const dom = loadLauncher('#app=org.nuxel.Terminal');
  const launched = [];
  vm.runInContext("document.dispatchEvent(new CustomEvent('DOMContentLoaded'))", dom.sandbox);
  await tick();
  dom.document.addEventListener('app:launch', (ev) => launched.push(ev.detail.app.id));
  dom.flush();
  check('the #app=<id> deeplink launches that registry app',
        launched.includes('org.nuxel.Terminal'), JSON.stringify(launched));
  const dom2 = loadLauncher('#app=does.not.Exist');
  vm.runInContext("document.dispatchEvent(new CustomEvent('DOMContentLoaded'))", dom2.sandbox);
  await tick();
  dom2.flush();
  const reg2 = vm.runInContext('appRegistry', dom2.sandbox);
  check('an unknown deeplink is refused, not launched into a blank frame',
        reg2.getRecentApps().length === 0 && dom2.document.querySelectorAll('.pwa-frame').length === 0);
  check('every manifest shortcut id is launchable from the deeplink path',
        shortcuts.every((sc) => { const m = /#app=([^&]+)$/.exec(sc.url || ''); return m && !!reg2.getApp(decodeURIComponent(m[1])); }),
        JSON.stringify(shortcuts.map((s) => s.url)));
}

// --- 7e. scrolling / viewport contract (the surface the finger actually drags) --
{
  const css = fs.readFileSync(path.join(HOME, 'css/launcher.css'), 'utf8');
  check('the launcher grid is a scrollable container',
        /\.app-grid\s*\{[^}]*overflow-y:\s*auto/s.test(css));
  check('the grid keeps touch momentum scrolling on the phone',
        /\.app-grid\s*\{[^}]*(-webkit-overflow-scrolling:\s*touch|scroll-behavior:\s*smooth)/s.test(css));
  check('the app grid is a real CSS grid (4 columns as shipped)',
        /grid-template-columns:\s*repeat\(\s*4/.test(css));
  check('the launcher page declares the fullscreen viewport-fit the cutout needs',
        /viewport-fit=cover/.test(indexHtml) && /maximum-scale=1\.0/.test(indexHtml));
  check('the app grid container exists in the page', /id="app-grid"/.test(indexHtml));
  const searchCss = fs.readFileSync(path.join(HOME, 'css/search.css'), 'utf8');
  check('the search results list is scrollable too',
        /\.search-results\s*\{[^}]*overflow-y:\s*auto/s.test(searchCss) || /overflow-y:\s*auto/.test(searchCss));
}

// The summary is printed here (not at the top level) because section 7 has to
// await the real launcher controller's async boot before it can assert anything.
console.log('\n' + (failures ? failures + ' FAILURES' : 'launcher registry/parity tests passed') +
            (warnings ? ' (' + warnings + ' warning(s))' : ''));
process.exit(failures ? 1 : 0);
})();
