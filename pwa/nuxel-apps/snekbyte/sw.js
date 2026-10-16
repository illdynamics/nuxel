// Nuxel SnekByte service worker — the game is fully offline: the engine, the
// renderer and every asset are in this directory.  There is no network path at
// all, so the cache is cache-first and a fetch that somehow reaches the network
// is only used to refresh the cache, never to make the game work.
//
// CACHE_NAME is versioned; `activate` deletes every other namespace so a stale
// engine can never be served after a redeploy (the INV-1 lesson from A32).
const CACHE_NAME = 'nuxel-snekbyte-v1';
const ASSETS = [
  './', './index.html', './manifest.json', './app.json',
  './css/snekbyte.css', './js/snek-engine.js', './js/snekbyte.js',
  './icons/icon-48.png', './icons/icon-72.png', './icons/icon-96.png',
  './icons/icon-128.png', './icons/icon-144.png', './icons/icon-152.png',
  './icons/icon-192.png', './icons/icon-384.png', './icons/icon-512.png',
  './icons/icon.svg'
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;                       // never cache a mutation
  e.respondWith(caches.match(req).then(cached => {
    if (cached) return cached;
    return fetch(req).then(res => {
      if (res && res.status === 200 && res.type === 'basic') {
        const copy = res.clone();
        caches.open(CACHE_NAME).then(c => c.put(req, copy));
      }
      return res;
    }).catch(() => cached);
  }));
});
