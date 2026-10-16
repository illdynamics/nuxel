// v2 (briq-06c): the mail app moved off the fake IMAP client onto the
// honest local store + transport pair, so the cached v1 bundle must be replaced.
const CACHE_NAME = 'nuxel-mail-v2';
const ASSETS = [
  './', './index.html', './manifest.json',
  './css/mail.css',
  './js/mail.js', './js/transport.js', './js/storage.js',
  './icons/icon-48.png', './icons/icon-72.png', './icons/icon-96.png',
  './icons/icon-128.png', './icons/icon-144.png', './icons/icon-152.png',
  './icons/icon-192.png', './icons/icon-384.png', './icons/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      // one missing asset must not abort the install of the whole app shell
      Promise.all(ASSETS.map(a => cache.add(a).catch(() => null))))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then(cached => {
      const fetchPromise = fetch(event.request).then(response => {
        if (response && response.status === 200) {
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, response.clone()));
        }
        return response;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});

self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const options = {
    body: data.body || 'New email',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-72.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/' }
  };
  event.waitUntil(
    self.registration.showNotification(data.title || 'Nuxel Mail', options)
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(clientList => {
      for (const client of clientList) {
        if (client.url.includes('/mail') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow('/');
    })
  );
});

// Background sync for email
self.addEventListener('sync', event => {
  if (event.tag === 'sync-mail') {
    event.waitUntil(
      self.clients.matchAll().then(clients => {
        clients.forEach(client => client.postMessage({ type: 'sync-mail' }));
      })
    );
  }
});

self.addEventListener('periodicsync', event => {
  if (event.tag === 'check-mail') {
    event.waitUntil(
      self.clients.matchAll().then(clients => {
        clients.forEach(client => client.postMessage({ type: 'check-mail' }));
      })
    );
  }
});
