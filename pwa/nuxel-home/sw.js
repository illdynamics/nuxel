// Nuxel Home - Service Worker
// Provides offline support, background sync, and push notification handling

// Cache version is bumped by hand when a launcher asset changes.  It is the
// controlled migration path for the cache-first static strategy below: a new
// worker installs its own cache namespace and 'activate' deletes the old ones,
// so a redeployed launcher is never served from a stale cache (briq A31).
//
// A33 bumped it to v4-a33 because that revision adds js/settings-store.js and
// js/bootlog.js and changes js/status-bar.js (v0.5.1-alpha -> v0.4.1-a33) and
// js/qs.js.  The bg-02 verification pass bumps it again to v5-a33 because
// js/qs.js (the boot-diagnostics tile: tap = verbose boot, long-press = cycle the
// animation policy) and js/settings-store.js (animation_mode + verbosity_level)
// changed again: without the bump a launcher restored from the v4 cache would
// keep serving the old tile with no way to tell.  The registry test asserts this
// string advanced past 'v3-a32', and manifest.json carries the same key as
// nuxel.cache_version, so a launcher that was served from a stale bundle is a
// detectable state rather than a mystery.
// v0.5.2-beta changes launcher lifecycle and Terminal interaction assets.
const CACHE_VERSION = 'v22-a42-dock-asset-url';
const CACHE_NAME = 'nuxel-home-' + CACHE_VERSION;
const STATIC_CACHE = 'nuxel-static-' + CACHE_VERSION;
const DYNAMIC_CACHE = 'nuxel-dynamic-' + CACHE_VERSION;

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
    './css/home-settings.css',
    './css/search.css',
    './js/apps.js',
    './js/layout-model.js',
    './js/launcher.js',
    './js/status-bar.js',
    './js/search.js',
    './js/bridge.js',
    './js/recents.js',
    './js/qs.js',
    './js/host-bridge.js',
    './js/safe-zones.js',
    './js/settings-store.js',
    './js/osd.js',
    './js/bootlog.js',
    './js/app.js',
    './js/touch-keyboard.js',
    './js/navigation.js',
    './js/gestures.js',
    './js/home-settings.js',
    './js/system-monitor.js',
    './js/scroll-indicators.js',
    './icons/icon-192.png',
    './icons/icon-512.png',
    './assets/nuxel-boot-animation.mp4',
    // The real home-screen wallpaper (assets/nuxel-background.png). It is
    // referenced by css/style.css as ../assets/nuxel-background.png, so a
    // missing copy at this path means the launcher renders with no wallpaper.
    './assets/nuxel-background.png',
    './assets/nuxel-bottom-bar.jpg',
    './assets/nuxel-bottom-bar2.png',
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

    // A32: CODE assets (js/css/html) are NETWORK FIRST on this device.  The
    // launcher is served by a local static server that is always up, so a stale
    // cache can only ever hurt: an earlier revision served the launcher from a
    // cache-first path and a redeployed index.html/js was invisible on the glass
    // until the cache namespace changed under it.  Images/video stay cache-first
    // (large, immutable, and re-validated through HTTP when they do change).
    const isCode = /\.(js|css|json|html|webmanifest)(\?|$)/i.test(request.url) ||
                   request.url.includes('/pwa/nuxel-home/js/') ||
                   request.url.includes('/pwa/nuxel-apps/');
    if (isCode) {
        event.respondWith(
            fetch(request).then((response) => {
                if (response.status === 200) {
                    const clone = response.clone();
                    caches.open(DYNAMIC_CACHE).then((cache) => { cache.put(request, clone); });
                }
                return response;
            }).catch(() => caches.match(request).then((cached) => cached || new Response('Offline', { status: 503 })))
        );
        return;
    }

    // A37: owner artwork is mutable during live deployment. The previous
    // cache-first branch could keep old/missing artwork visible indefinitely.
    // Use network-first even for previously cached 404/fallback PNG responses.
    const ownerArt = /\/(?:assets\/(?:button-(?:left|middle|right)\.png|nuxel-(?:applications|quicksettings)-icon-pack\/)|pwa\/nuxel-home\/assets\/branding\/)/.test(new URL(request.url).pathname);
    if (ownerArt) {
        event.respondWith(fetch(request, {cache: 'no-store'}).then(response => {
            if (!response.ok || !response.headers.get('content-type')?.includes('image/png'))
                throw new Error('Nuxel owner art unavailable: ' + response.status);
            const clone = response.clone();
            caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, clone));
            return response;
        }).catch(() => caches.match(request).then(cached => cached || new Response('Nuxel art unavailable', {status: 503}))));
        return;
    }

    // Cache first for immutable static assets (images, video, fonts)
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
