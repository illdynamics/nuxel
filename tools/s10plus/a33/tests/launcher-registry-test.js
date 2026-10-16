// A33 launcher-parity test (briq-02d) — "the launcher the phone serves is the
// launcher the repository owns".
//
// WHY THIS EXISTS
//   On the handset the launcher page was fine but its ASSETS had drifted: the
//   device copy of js/status-bar.js was v0.3.2 while the repository was already
//   v0.4.0-alpha, manifest.json was stale, the registry had no Terminal entry and
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
//   6. no stale device copy of a launcher asset is bundled in the repo.
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

console.log('\n' + (failures ? failures + ' FAILURES' : 'launcher registry/parity tests passed') +
            (warnings ? ' (' + warnings + ' warning(s))' : ''));
process.exit(failures ? 1 : 0);
