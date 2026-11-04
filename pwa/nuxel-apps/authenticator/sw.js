// Nuxel Authenticator service worker: static shell only.
//
// It MUST NOT cache /api/, /rpc, /auth/, Secret Service results, decrypted
// vault content, TOTP codes, QR enrollment payloads or form state.
const CACHE_NAME = 'nuxel-authenticator-v4-p63000';
const ASSETS = [
  '/', '/index.html', '/css/authenticator.css', '/js/authenticator.js', '/js/totp.js',
  '/js/vault.js', '/vendor/jsQR.js', '/vendor/jsQR.LICENSE.txt',
  '/samples/otpauth-examples.json', '../nuxel-common/bridge.js', '/manifest.json',
  '/icons/icon-48.png', '/icons/icon-72.png', '/icons/icon-96.png', '/icons/icon-128.png',
  '/icons/icon-144.png', '/icons/icon-152.png', '/icons/icon-192.png', '/icons/icon-384.png',
  '/icons/icon-512.png', '/icons/icon.svg'
];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;
  if (url.pathname.indexOf('/api/') === 0 || url.pathname.indexOf('/rpc') === 0 ||
      url.pathname.indexOf('/auth/') === 0) return;
  e.respondWith(
    caches.match(req).then((cached) => cached || fetch(req).then((res) => {
      if (res && res.status === 200 && res.type === 'basic') {
        const copy = res.clone();
        caches.open(CACHE_NAME).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => cached))
  );
});
