// NuxTore service worker — offline-first: the catalog and the whole UI must work
// with no network at all (this app never makes a network request anyway).
const CACHE = 'nuxel-nuxtore-v1';
const ASSETS = [
  './', './index.html', './css/nuxtore.css',
  './js/nuxtore.js', './js/nuxtore-catalog.js', './js/nuxtore-crypto.js',
  './manifest.json', './catalog/nuxtore-catalog.json',
  './catalog/schema/nuxtore-catalog.schema.json', './catalog/schema/bundle.schema.json',
  './icons/icon-48.png', './icons/icon-72.png', './icons/icon-96.png',
  './icons/icon-128.png', './icons/icon-144.png', './icons/icon-152.png',
  './icons/icon-192.png', './icons/icon-384.png', './icons/icon-512.png', './icons/icon.svg'
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
    if (r && r.status === 200 && r.type === 'basic') {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
    }
    return r;
  }).catch(() => hit)));
});
