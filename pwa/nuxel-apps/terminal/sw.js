// Nuxel Terminal service worker - the shell itself is host-provided, so only the
// presentation assets are cached; a cached stale terminal UI is still safe.
const CACHE_NAME = 'nuxel-terminal-v3';
const ASSETS = ['./', './index.html', './terminal.css', './terminal.js', './manifest.json',
  '../../nuxel-common/bridge.js',
  '../../nuxel-home/js/host-bridge.js', '../../nuxel-home/js/osd.js', './icons/icon-192.png', './icons/icon-512.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache =>
    Promise.all(ASSETS.map(a => cache.add(a).catch(() => null)))));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then(cached => cached ||
      fetch(event.request).then(response => {
        if (response && response.status === 200 && response.type === 'basic') {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        }
        return response;
      }).catch(() => cached || Response.error()))
  );
});
