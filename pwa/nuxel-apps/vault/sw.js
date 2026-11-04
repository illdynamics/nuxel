// Nuxel Vault service worker: static shell only.
//
// It never caches /api/, /auth/, /rpc, Secret Service results, decrypted items,
// passwords, notes or form state.  Only same-origin GET shell assets are kept.
const CACHE_NAME = 'nuxel-vault-v2-p63000';
const ASSETS = [
  '/pwa/nuxel-apps/vault/',
  '/pwa/nuxel-apps/vault/index.html',
  '/pwa/nuxel-apps/vault/css/vault.css',
  '/pwa/nuxel-apps/vault/js/app.js',
  '/pwa/nuxel-apps/vault/js/boot-guard.js',
  '/pwa/nuxel-apps/vault/js/archive.js',
  '/pwa/nuxel-apps/vault/js/pwgen.js',
  '/pwa/nuxel-apps/vault/manifest.json',
  '/pwa/nuxel-apps/vault/app.json',
  '/pwa/nuxel-common/bridge.js',
  '/pwa/nuxel-common/responsive.css',
  '/pwa/nuxel-apps/vault/icons/icon-48.png',
  '/pwa/nuxel-apps/vault/icons/icon-192.png',
  '/pwa/nuxel-apps/vault/icons/icon-512.png',
  '/pwa/nuxel-apps/vault/icons/icon.svg'
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
