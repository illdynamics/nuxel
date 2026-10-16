const CACHE_NAME = 'nuxel-downloader-v1';
const ASSETS = [
  '/', '/index.html', '/css/downloader.css', '/js/downloader.js', '/js/download-queue.js',
  '../nuxel-common/bridge.js', '/manifest.json',
  '/icons/icon-48.png', '/icons/icon-72.png', '/icons/icon-96.png', '/icons/icon-128.png',
  '/icons/icon-144.png', '/icons/icon-152.png', '/icons/icon-192.png', '/icons/icon-384.png',
  '/icons/icon-512.png', '/icons/icon.svg'
];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS))); self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  // Never cache a transfer: this service worker is for the app shell only.
  e.respondWith(caches.match(e.request).then(cached => {
    const net = fetch(e.request).then(res => {
      if (res && res.status === 200) caches.open(CACHE_NAME).then(c => c.put(e.request, res.clone()));
      return res;
    }).catch(() => cached);
    return cached || net;
  }));
});
