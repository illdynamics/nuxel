const CACHE = 'nuxel-devmgmt-v2-p82000';
const ASSETS = ['./', './index.html', './css/devmgmt.css?v=p82000', './js/devmgmt.js?v=p82000',
  './js/devmgmt-parsers.js?v=p82000', './manifest.json', '../_shared/sysinfo.js',
  '../_shared/samples/sys-snapshot.json', './icons/icon-192.png', './icons/icon-512.png', './icons/icon.svg'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(() => {})); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== CACHE).map(x => caches.delete(x))))); self.clients.claim(); });
self.addEventListener('fetch', e => { e.respondWith(caches.match(e.request).then(h => h || fetch(e.request).catch(() => h))); });
