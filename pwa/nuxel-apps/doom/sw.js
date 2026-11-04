// Nuxel Doom — offline-first cache. One cache for this app only; a failed
// install never replaces a working offline copy.
const NAME = 'nuxel-doom-100-v2';
const PREFIX = 'nuxel-doom-';
const ASSETS = [
  './', './index.html', './app.json', './manifest.json',
  './css/doom.css', './js/doom-engine.js', './js/doom.js',
  './icons/icon-48.png', './icons/icon-72.png', './icons/icon-96.png',
  './icons/icon-128.png', './icons/icon-144.png', './icons/icon-152.png',
  './icons/icon-192.png', './icons/icon-384.png', './icons/icon-512.png',
  './icons/icon.svg'
];
self.addEventListener('install', event => event.waitUntil(
  caches.open(NAME).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting())
));
self.addEventListener('activate', event => event.waitUntil(
  caches.keys().then(keys => Promise.all(keys
    .filter(k => k.startsWith(PREFIX) && k !== NAME).map(k => caches.delete(k))))
    .then(() => self.clients.claim())
));
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (!url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;
  event.respondWith(caches.open(NAME).then(cache =>
    cache.match(req, { ignoreSearch: true }).then(found => found || fetch(req))));
});
