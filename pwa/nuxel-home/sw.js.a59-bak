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
const CACHE_VERSION = 'v32-a54-reliability';
const CACHE_NAME = 'nuxel-home-' + CACHE_VERSION;   // version marker sent to clients
const STATIC_CACHE = 'nuxel-static-' + CACHE_VERSION;
const DYNAMIC_CACHE = 'nuxel-dynamic-' + CACHE_VERSION;
const ICON_CACHE = 'nuxel-icons-' + CACHE_VERSION;

// Assets to cache on install (critical path). Paths are SCOPE-RELATIVE so the
// worker installs cleanly whether the PWA is served at a sub-path (e.g.
// /pwa/nuxel-home on the nuxel-web :8000 static server) or at the web root.
const PRECACHE_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './icon-registry.json',
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
    './js/icon-health.js',
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

// Install event: cache critical code/UI assets. Custom app/navigation/toggle
// artwork is network-first at runtime (see the fetch handler), so a stale icon
// can never win just because it happened to be in the install-time cache.
self.addEventListener('install', (event) => {
    console.log('[SW] Installing...', CACHE_VERSION);
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate event: remove only OLD NUXEL caches. CacheStorage is code/offline
// bytes only: localStorage (layout, preferences), IndexedDB and credentials are
// separate stores and are deliberately never touched by this migration.
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating...', CACHE_VERSION);
    const validCaches = [STATIC_CACHE, DYNAMIC_CACHE, ICON_CACHE, CACHE_NAME];
    event.waitUntil(
        caches.keys().then((cacheNames) => Promise.all(
            cacheNames.map((cacheName) => {
                if (cacheName.startsWith('nuxel-') && !validCaches.includes(cacheName)) {
                    console.log('[SW] Deleting old Nuxel cache:', cacheName);
                    return caches.delete(cacheName);
                }
                return undefined;   // another app's cache is not ours to delete
            })
        )).then(() => self.clients.claim())
    );
});

const IMAGE_RE = /\.(?:png|jpe?g|gif|webp|svg|ico)(?:\?|$)/i;
const CODE_RE = /\.(?:js|css|json|html|webmanifest)(?:\?|$)/i;
const OWNER_ART_RE = /^\/(?:assets\/(?:button-(?:left|middle|right)\.png$|nuxel-(?:applications|quicksettings)-icon-pack\/)|pwa\/nuxel-home\/assets\/branding\/)/;

function cacheable(response, kind) {
    if (!response || !response.ok || response.status !== 200) return false;
    if (response.type === 'opaque' || response.type === 'opaqueredirect') return false;
    const type = String(response.headers.get('content-type') || '').toLowerCase();
    if (kind === 'image' && !type.startsWith('image/')) return false;
    if (kind === 'html' && type && !type.includes('text/html')) return false;
    return true;
}

async function cacheSuccessful(cacheName, request, response, kind) {
    const cache = await caches.open(cacheName);
    if (cacheable(response, kind)) {
        await cache.put(request, response.clone());
    } else if (response && response.status === 404) {
        // A redeploy can turn a previously good URL into a 404.  Remove that
        // exact stale entry instead of keeping a broken asset forever.
        await cache.delete(request);
    }
}

// Always ask the live static server first, then fall back to an exact cached
// response.  Only a verified 200 of the expected type is stored; 404/5xx/HTML
// error pages are never installed into a cache.
async function networkFirst(event, request, cacheName, kind, options) {
    event.respondWith((async () => {
        try {
            const response = await fetch(request, options || { cache: 'no-cache' });
            await cacheSuccessful(cacheName, request, response, kind);
            return response;
        } catch (error) {
            const cached = await caches.match(request);
            if (cached) return cached;
            return new Response('Nuxel asset unavailable while offline', {
                status: 503,
                headers: { 'Content-Type': 'text/plain', 'Cache-Control': 'no-store' },
            });
        }
    })());
}

// Fetch event: code and owner artwork are network-first; immutable media may be
// cache-first, but only after a successful 200.  There is no catch-all image
// fallback: substituting one icon for another is precisely the stale/duplicate
// artwork failure this policy exists to prevent.
self.addEventListener('fetch', (event) => {
    const request = event.request;

    if (request.method !== 'GET') return;

    // Bridge API calls are live state and must never be cached.
    if (request.url.includes('/api/v1/')) {
        event.respondWith(fetch(request));
        return;
    }
    if (request.url.startsWith('nuxel-')) {
        event.respondWith(fetch(request));
        return;
    }

    const url = new URL(request.url);
    const pathname = url.pathname;

    // HTML: live first, exact cached page second.  Never cache a 404 page.
    if (request.headers.get('Accept')?.includes('text/html') || pathname.endsWith('/')) {
        networkFirst(event, request, DYNAMIC_CACHE, 'html', { cache: 'no-cache' });
        return;
    }

    // Code assets are always revalidated so a build/cache-version bump cannot
    // leave an old launcher running from a previous service-worker generation.
    if (CODE_RE.test(pathname)) {
        networkFirst(event, request, DYNAMIC_CACHE, 'code', { cache: 'no-cache' });
        return;
    }

    // App/navigation/toggle artwork is mutable during a live userspace deploy.
    // `no-store` also bypasses WebKit's HTTP cache, not just CacheStorage.
    if (request.destination === 'image' || IMAGE_RE.test(pathname) || OWNER_ART_RE.test(pathname)) {
        networkFirst(event, request, ICON_CACHE, 'image', { cache: 'no-store' });
        return;
    }

    // Immutable media/fonts. The cache namespace changes with CACHE_VERSION, so
    // a new build cannot silently reuse these either.
    event.respondWith((async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        try {
            const response = await fetch(request);
            await cacheSuccessful(DYNAMIC_CACHE, request, response, 'other');
            return response;
        } catch (error) {
            return new Response('Nuxel asset unavailable while offline', {
                status: 503,
                headers: { 'Content-Type': 'text/plain', 'Cache-Control': 'no-store' },
            });
        }
    })());
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
            // Offline/code bytes only; layout, preferences and credentials live
            // in browser storage and are intentionally preserved.
            event.waitUntil(Promise.all([
                caches.delete(DYNAMIC_CACHE),
                caches.delete(STATIC_CACHE),
                caches.delete(ICON_CACHE),
            ]));
            break;
    }
});
