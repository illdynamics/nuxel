// Nuxel Home - Service Worker
// Provides offline support, background sync, and push notification handling

const CACHE_NAME = 'nuxel-home-v1';
const STATIC_CACHE = 'nuxel-static-v1';
const DYNAMIC_CACHE = 'nuxel-dynamic-v1';

// Assets to cache on install (critical path)
// Assets to cache on install (critical path). Paths are SCOPE-RELATIVE so the
// worker installs cleanly whether the PWA is served at a sub-path (e.g.
// /pwa/nuxel-home on the nuxel-web :8000 static server) or at the web root.
const PRECACHE_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './css/style.css',
    './css/launcher.css',
    './css/status-bar.css',
    './css/search.css',
    './js/apps.js',
    './js/launcher.js',
    './js/status-bar.js',
    './js/search.js',
    './js/bridge.js',
    './js/recents.js',
    './js/qs.js',
    './js/app.js',
    './icons/icon-192.png',
    './icons/icon-512.png',
    './assets/nuxel-boot-animation.mp4',
];

// Install event: cache critical assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(PRECACHE_ASSETS);
        }).then(() => {
            // Skip waiting to activate immediately
            return self.skipWaiting();
        })
    );
});

// Activate event: clean old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating...');
    
    const validCaches = [STATIC_CACHE, DYNAMIC_CACHE, CACHE_NAME];
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (!validCaches.includes(cacheName)) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            // Claim all clients immediately
            return self.clients.claim();
        })
    );
});

// Fetch event: network first, cache fallback
self.addEventListener('fetch', (event) => {
    const request = event.request;
    
    // Skip non-GET requests
    if (request.method !== 'GET') return;
    
    // Skip bridge API calls (always go to network)
    if (request.url.includes('/api/v1/')) {
        event.respondWith(fetch(request));
        return;
    }
    
    // Skip D-Bus (shouldn't happen in SW context)
    if (request.url.startsWith('nuxel-')) {
        event.respondWith(fetch(request));
        return;
    }

    // Strategy: Network first, cache fallback for HTML
    if (request.headers.get('Accept')?.includes('text/html')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Cache successful responses
                    const clone = response.clone();
                    caches.open(DYNAMIC_CACHE).then((cache) => {
                        cache.put(request, clone);
                    });
                    return response;
                })
                .catch(() => {
                    // Fallback to cache
                    return caches.match(request).then((cached) => {
                        return cached || caches.match('./index.html') || caches.match('/index.html');
                    });
                })
        );
        return;
    }

    // Cache first for static assets
    event.respondWith(
        caches.match(request).then((cached) => {
            if (cached) return cached;
            
            return fetch(request).then((response) => {
                if (response.status === 200) {
                    const clone = response.clone();
                    caches.open(DYNAMIC_CACHE).then((cache) => {
                        cache.put(request, clone);
                    });
                }
                return response;
            }).catch(() => {
                // Return a fallback for known asset types
                if (request.url.match(/\.(png|jpg|jpeg|gif|svg|ico)$/)) {
                    return caches.match('/icons/icon-192.png');
                }
                return new Response('Offline', { status: 503 });
            });
        })
    );
});

// Push notification event
self.addEventListener('push', (event) => {
    console.log('[SW] Push received:', event);
    
    let data;
    try {
        data = event.data?.json() || {};
    } catch {
        data = { title: 'Nuxel', body: event.data?.text() || 'New notification' };
    }

    const options = {
        title: data.title || 'Nuxel',
        body: data.body || '',
        icon: data.icon || '/icons/icon-192.png',
        badge: data.badge || '/icons/icon-192.png',
        tag: data.tag || 'default',
        data: data.data || {},
        vibrate: data.vibrate || [100, 50, 100],
        requireInteraction: data.requireInteraction || false,
        actions: data.actions || [],
        timestamp: Date.now(),
        renotify: true,
        silent: data.silent || false,
    };

    event.waitUntil(
        self.registration.showNotification(options.title, options)
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event.notification.tag);
    
    event.notification.close();

    // Determine action
    const action = event.action;
    const notificationData = event.notification.data || {};

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            // Focus existing window or open new one
            for (const client of clientList) {
                if (client.url === '/' && 'focus' in client) {
                    // Send message to client about notification action
                    client.postMessage({
                        type: 'notification_action',
                        notification: event.notification,
                        action: action,
                    });
                    return client.focus();
                }
            }
            // Open new window
            if (clients.openWindow) {
                return clients.openWindow(notificationData.url || '/');
            }
        })
    );
});

// Notification close event
self.addEventListener('notificationclose', (event) => {
    console.log('[SW] Notification closed:', event.notification.tag);
});

// Background sync event
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync:', event.tag);
    
    if (event.tag === 'sync-messages') {
        event.waitUntil(syncMessages());
    } else if (event.tag === 'sync-mail') {
        event.waitUntil(syncMail());
    } else if (event.tag === 'sync-calendar') {
        event.waitUntil(syncCalendar());
    }
});

// Background sync handlers
async function syncMessages() {
    console.log('[SW] Syncing messages...');
    // In production, connect to bridge for pending outbox messages
    try {
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'sync',
                tag: 'sync-messages',
                status: 'completed',
            });
        });
    } catch (e) {
        console.error('[SW] Sync failed:', e);
    }
}

async function syncMail() {
    console.log('[SW] Syncing mail...');
    // In production, check IMAP for new mail
}

async function syncCalendar() {
    console.log('[SW] Syncing calendar...');
    // In production, sync CalDAV events
}

// Message handler for app->SW communication
self.addEventListener('message', (event) => {
    const data = event.data;
    if (!data) return;

    switch (data.type) {
        case 'skip-waiting':
            self.skipWaiting();
            break;
        case 'register-sync':
            if (data.tag) {
                self.registration.sync.register(data.tag);
            }
            break;
        case 'cache-url':
            if (data.url) {
                caches.open(DYNAMIC_CACHE).then((cache) => {
                    cache.add(data.url);
                });
            }
            break;
        case 'clear-cache':
            caches.delete(DYNAMIC_CACHE);
            caches.delete(STATIC_CACHE);
            break;
    }
});
