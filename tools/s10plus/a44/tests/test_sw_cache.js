#!/usr/bin/env node
/*
 * Behavioural service-worker cache test for A44.
 *
 * Evaluates the real sw.js with CacheStorage/fetch stubs and drives its actual
 * install/activate/fetch/message handlers.  This is deliberately not a string
 * assertion: it proves 200 image responses are cached, 404s are evicted and not
 * stored, exact offline fallback works, and only old `nuxel-*` caches are
 * removed (another app's cache is untouched).
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const SW = path.join(ROOT, 'pwa/nuxel-home/sw.js');
const MANIFEST = JSON.parse(fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/manifest.json'), 'utf8'));
const version = MANIFEST.nuxel.cache_version;
const ICON_CACHE = 'nuxel-icons-' + version;
const DYNAMIC_CACHE = 'nuxel-dynamic-' + version;
const STATIC_CACHE = 'nuxel-static-' + version;

let failures = 0;
function check(cond, label, detail) {
  console.log((cond ? 'PASS ' : 'FAIL ') + label + (cond ? '' : '  ' + (detail || '')));
  if (!cond) failures++;
}

const stores = new Map();
const deleted = [];
function cacheFor(name) {
  if (!stores.has(name)) stores.set(name, new Map());
  const m = stores.get(name);
  return {
    async addAll(urls) { for (const u of urls) m.set(u, new Response('precache:' + u, {status: 200, headers: {'content-type': 'application/octet-stream'}})); },
    async put(req, res) { m.set(typeof req === 'string' ? req : req.url, res); },
    async delete(req) { return m.delete(typeof req === 'string' ? req : req.url); },
    async match(req) { return m.get(typeof req === 'string' ? req : req.url) || undefined; },
  };
}
const caches = {
  async open(name) { return cacheFor(name); },
  async keys() { return [...stores.keys()]; },
  async delete(name) { deleted.push(name); return stores.delete(name); },
  async match(req) {
    const key = typeof req === 'string' ? req : req.url;
    for (const m of stores.values()) if (m.has(key)) return m.get(key);
    return undefined;
  },
};

const handlers = {};
const self = {
  addEventListener(type, fn) { handlers[type] = fn; },
  async skipWaiting() {}, async clientsClaim() {},
  clients: { async claim() {} },
  registration: { async showNotification() {}, sync: { async register() {} } },
};
const clients = { async matchAll() { return []; }, async openWindow() { return null; } };

let fetchImpl;
const fetchCalls = [];
async function fetchStub(req, opts) {
  fetchCalls.push({url: req.url || req, opts: opts || {}});
  return fetchImpl(req, opts);
}

const context = vm.createContext({
  self, caches, clients, fetch: fetchStub, Response, Headers, URL,
  console: { log() {}, warn() {}, error() {} }, Promise, setTimeout, clearTimeout,
});
vm.runInContext(fs.readFileSync(SW, 'utf8'), context, {filename: SW});

async function waitAll(event) {
  const waits = [];
  event.waitUntil = p => waits.push(Promise.resolve(p));
  return waits;
}
function request(url, {accept = '', destination = ''} = {}) {
  return { method: 'GET', url, destination, headers: { get(h) { return h.toLowerCase() === 'accept' ? accept : null; } } };
}
async function dispatch(req) {
  let response;
  handlers.fetch({request: req, respondWith(p) { response = Promise.resolve(p); }});
  return response ? await response : null;
}
function response(status, body, type) {
  return new Response(body, {status, headers: type ? {'content-type': type} : {}});
}

(async () => {
  // install: critical assets, including the generated icon manifest
  let waits = await waitAll({});
  handlers.install({waitUntil: p => waits.push(Promise.resolve(p))});
  await Promise.all(waits);
  check(stores.has(STATIC_CACHE), 'install creates the versioned static cache');
  check(stores.get(STATIC_CACHE).has('./icon-registry.json'), 'install precaches icon-registry.json');

  // activate: version migration only removes old Nuxel caches
  stores.set('other-app-data', new Map());
  stores.set('nuxel-static-v1-old', new Map());
  stores.set('nuxel-dynamic-v1-old', new Map());
  stores.set('nuxel-icons-v1-old', new Map());
  deleted.length = 0;
  waits = [];
  handlers.activate({waitUntil: p => waits.push(Promise.resolve(p))});
  await Promise.all(waits);
  check(deleted.includes('nuxel-static-v1-old') && deleted.includes('nuxel-dynamic-v1-old') &&
        deleted.includes('nuxel-icons-v1-old'), 'activate deletes old Nuxel cache generations', deleted.join(','));
  check(!deleted.includes('other-app-data'), 'activate preserves another app cache');
  check(stores.has('other-app-data'), 'another app cache remains in storage');

  // 200 PNG is cached under its exact URL with no-store network semantics
  const iconReq = request('http://127.0.0.1:8000/assets/nuxel-applications-icon-pack/01-08_phone.png?v=a44',
                          {destination: 'image'});
  fetchImpl = async () => response(200, 'png-bytes', 'image/png');
  let r = await dispatch(iconReq);
  check(r.status === 200, 'icon network response returned');
  check(stores.get(ICON_CACHE) && stores.get(ICON_CACHE).has(iconReq.url), 'successful PNG is cached by exact URL');
  check(fetchCalls[fetchCalls.length - 1].opts.cache === 'no-store', 'icon fetch bypasses the HTTP cache');

  // 404 evicts a previously cached key and is not stored
  stores.get(ICON_CACHE).set(iconReq.url, response(200, 'old-icon', 'image/png'));
  fetchImpl = async () => response(404, 'not found', 'text/html');
  r = await dispatch(iconReq);
  check(r.status === 404, 'real 404 is returned to the image element');
  check(!stores.get(ICON_CACHE).has(iconReq.url), '404 evicts the stale icon key');
  check(stores.get(ICON_CACHE).get(iconReq.url) === undefined, '404 is not permanently cached');

  // network failure uses exact cached bytes, never a substitute icon
  const cached = response(200, 'exact-cached-icon', 'image/png');
  stores.get(ICON_CACHE).set(iconReq.url, cached);
  fetchImpl = async () => { throw new Error('offline'); };
  r = await dispatch(iconReq);
  check(r === cached, 'offline serves the exact cached icon');

  // no cached copy: explicit 503 instead of /icons/icon-192.png substitution
  const otherReq = request('http://127.0.0.1:8000/assets/nuxel-quicksettings-icon-pack/01-wifi.png?v=a44',
                           {destination: 'image'});
  fetchImpl = async () => { throw new Error('offline'); };
  r = await dispatch(otherReq);
  check(r.status === 503 && (await r.text()).includes('unavailable'), 'uncached icon miss is an explicit 503');

  // HTML and code 404s are not cached
  for (const [req, label] of [
    [request('http://127.0.0.1:8000/pwa/nuxel-home/index.html', {accept: 'text/html'}), 'HTML'],
    [request('http://127.0.0.1:8000/pwa/nuxel-home/js/apps.js?v=a44'), 'code'],
  ]) {
    fetchImpl = async () => response(404, 'missing', 'text/html');
    r = await dispatch(req);
    check(r.status === 404, label + ' 404 returned');
    check(!stores.get(DYNAMIC_CACHE).has(req.url), label + ' 404 not cached');
  }

  // image MIME guard: a 200 HTML error page at an image URL is not cached
  const htmlAtImage = request('http://127.0.0.1:8000/assets/nuxel-applications-icon-pack/02-01_messages.png?v=a44',
                              {destination: 'image'});
  fetchImpl = async () => response(200, '<html>error</html>', 'text/html');
  r = await dispatch(htmlAtImage);
  check(r.status === 200 && !stores.get(ICON_CACHE).has(htmlAtImage.url),
        '200 HTML at an image URL is not cached as artwork');

  // clear-cache is limited to this PWA's cache namespaces
  stores.set('nuxel-other-tool', new Map());
  deleted.length = 0;
  waits = [];
  handlers.message({data: {type: 'clear-cache'}, waitUntil: p => waits.push(Promise.resolve(p))});
  await Promise.all(waits);
  check(deleted.includes(ICON_CACHE) && deleted.includes(DYNAMIC_CACHE) && deleted.includes(STATIC_CACHE),
        'clear-cache clears this PWA caches', deleted.join(','));
  check(!deleted.includes('other-app-data') && !deleted.includes('nuxel-other-tool'),
        'clear-cache does not erase unrelated caches', deleted.join(','));

  console.log('\n' + (failures ? failures + ' FAILURES' : 'service-worker cache behaviour passed'));
  process.exit(failures ? 1 : 0);
})().catch(e => { console.error(e.stack || e); process.exit(1); });
