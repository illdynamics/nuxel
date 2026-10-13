<!-- Nuxel v0.2.2-alpha -->
# Nuxel PWA Application Model — Hardened Runtime

> **Each PWA runs in its own isolated WebKitGTK instance. No shared state. No ambient access.**
> **Target mustang: Tensor G5, Exynos 5500 modem, PowerVR DXT GPU**

---

## 1. Architecture: Per-App WebKitGTK Isolation

Every PWA runs as a **separate Flatpak application** with its own **dedicated WebKitGTK WebContext**.

### 1.1 Isolation Model

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   PWA: Mail         │  │   PWA: Calendar     │  │   PWA: Notes        │
│                     │  │                     │  │                     │
│ WebKitGTK Instance  │  │ WebKitGTK Instance  │  │ WebKitGTK Instance  │
│ ├─ WebContext #1    │  │ ├─ WebContext #2    │  │ ├─ WebContext #3    │
│ ├─ IndexedDB #1     │  │ ├─ IndexedDB #2     │  │ ├─ IndexedDB #3     │
│ ├─ CacheAPI #1      │  │ ├─ CacheAPI #2      │  │ ├─ CacheAPI #3      │
│ ├─ SW Registration 1│  │ ├─ SW Registration 2│  │ ├─ SW Registration 3│
│ └─ Cookies #1       │  │ └─ Cookies #2       │  │ └─ Cookies #3       │
└─────────┬───────────┘  └─────────┬───────────┘  └─────────┬───────────┘
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                    nuxel-bridge (capability gated)
                                   │
                    ┌──────────────┴──────────────┐
                    │       D-Bus System Bus       │
                    └─────────────────────────────┘
```

**Key isolation guarantees:**
- **No shared cookies** between PWAs — each has its own HTTP cookie jar
- **No shared localStorage** — each has its own origin storage quota
- **No shared ServiceWorker registrations** — each PWA has its own `self.registration`
- **No shared IndexedDB** — database namespaces are per-WebContext
- **No shared CacheAPI** — cache storage is per-WebContext
- **No shared browsing data** — autofill, passwords, history are per-instance

### 1.2 Storage Locations

```
/var/app/<pwa-id>/data/
├── webkit/              — WebKitGTK persistent storage
│   ├── LocalStorage/    — localStorage data
│   ├── IndexedDB/       — IndexedDB databases
│   ├── CacheStorage/    — CacheAPI entries
│   ├── ServiceWorkers/  — SW script caches + registrations
│   ├── CookieJar/       — HTTP cookies (per-origin)
│   └── Databases/       — WebSQL (disabled by default)
├── config/              — PWA configuration
│   ├── bridge-permissions.json
│   └── preferences.json
├── cache/               — Ephemeral cache (cleared on low disk)
└── tmp/                 — Runtime temp files (per-session)
```

---

## 2. WebKitGTK Hardening

### 2.1 Sandboxed WebContext Configuration

Each PWA WebContext is created with maximum isolation:

```c
// WebKitGTK hardened configuration for PWA
WebKitWebsiteDataManager *manager = webkit_website_data_manager_new(
    "base-data-directory", "/var/app/org.example.pwa/data/",
    "base-cache-directory", "/var/app/org.example.pwa/cache/",
    "local-storage-enabled", TRUE,
    "offline-application-cache-enabled", FALSE,
    "indexeddb-enabled", TRUE,
    "websql-enabled", FALSE,            // Disabled — deprecated API
    "hsts-cache-enabled", TRUE,
    "itp-enabled", TRUE,                // Intelligent Tracking Prevention
    "itp-json-model-enabled", TRUE,
    NULL);

WebKitWebContext *context = webkit_web_context_new_with_website_data_manager(manager);

// Security settings
WebKitSecurityManager *security = webkit_web_context_get_security_manager(context);
webkit_security_manager_register_uri_scheme_as_cors_enabled(security, "nuxel");
webkit_security_manager_register_uri_scheme_as_display_isolated(security, "nuxel");
webkit_security_manager_register_uri_scheme_as_local(security, "nuxel");

// Disable dangerous features
WebKitSettings *settings = webkit_web_view_get_settings(view);
webkit_settings_set_enable_java(FALSE);
webkit_settings_set_enable_plugins(FALSE);
webkit_settings_set_enable_hyperlink_auditing(FALSE);
webkit_settings_set_enable_webaudio(TRUE);  // Needed for media
webkit_settings_set_enable_mediasource(TRUE); // MSE for video/audio
webkit_settings_set_enable_encrypted_media(FALSE); // EME — DRM, disabled
webkit_settings_set_enable_fullscreen(FALSE);  // No fullscreen without portal
webkit_settings_set_enable_page_cache(TRUE);   // Offline support
webkit_settings_set_javascript_can_open_windows_automatically(FALSE);
```

### 2.2 Permissions in WebKit

```c
// WebKit permission requests are forwarded to nuxel-portal
static gboolean permission_request(WebKitWebView *web_view,
                                    WebKitPermissionRequest *request,
                                    gpointer user_data) {
    const char *type_name = G_OBJECT_TYPE_NAME(request);
    
    if (WEBKIT_IS_GEOLOCATION_PERMISSION_REQUEST(request)) {
        // Forward to nuxel-portal for location dialog
        nuxel_portal_request_location(app_id, request);
        return TRUE;
    }
    
    if (WEBKIT_IS_NOTIFICATION_PERMISSION_REQUEST(request)) {
        // Check if app has notifications capability
        if (nuxel_bridge_check_capability(app_id, "notifications:send")) {
            webkit_permission_request_allow(request);
        } else {
            webkit_permission_request_deny(request);
        }
        return TRUE;
    }
    
    if (WEBKIT_IS_USER_MEDIA_PERMISSION_REQUEST(request)) {
        // Forward camera/mic to portal
        nuxel_portal_request_media(app_id, request);
        return TRUE;
    }
    
    // Deny all other permission requests by default
    webkit_permission_request_deny(request);
    return TRUE;
}
```

### 2.3 Disabled Web APIs

The following APIs are explicitly disabled in the PWA runtime:

| API | Reason | Configuration |
|-----|--------|--------------|
| **WebUSB** | Security risk, no portal yet | Blocked in WebKitGTK build config |
| **WebBluetooth** | No portal infrastructure | Blocked in WebKitGTK build config |
| **WebNFC** | No portal infrastructure | Blocked in WebKitGTK build config |
| **WebSerial** | No use case for PWAs | Blocked in WebKitGTK build config |
| **WebHID** | No use case for PWAs | Blocked in WebKitGTK build config |
| **WebMIDI** | No use case for PWAs | Blocked in WebKitGTK build config |
| **WebGPU** | Allowed (PowerVR DXT) | Enabled when GPU driver available |
| **WebRTC** | Requires `network:outbound` | Enabled only with capability |
| **WebAuthn** | Allowed (Titan M3) | Enabled with portal integration |
| **File API** | Sandboxed to app data | Only `/var/app/<id>/data` visible |

---

## 3. App Lifecycle

### 3.1 Launch

```
1. User taps app icon in nuxel-home launcher
2. nuxel-home calls: flatpak run org.example.pwa
3. Flatpak bubblewrap sandbox activates
   - Mount namespace, PID namespace, netns created
   - seccomp filters applied
   - Landlock rules applied
4. WebKitGTK runtime starts
   - Creates isolated WebContext with per-app data dir
   - Loads start_url from manifest
   - Establishes connection to nuxel-bridge socket
5. PWA boots: ServiceWorker activates, app shell renders
6. PWA can request capabilities via bridge
   - Portal dialog shown for each new capability
   - Previously granted capabilities auto-authorized
```

### 3.2 Background / Suspend

```
1. User switches away (app switcher / home gesture)
2. Phosh compositor sends focus-loss event
3. After grace period (30 seconds configurable):
   a. If app has NO `background:execution` capability:
      - cgroup freezer: SIGSTOP to all app processes
      - All bridge method calls return "app suspended"
   b. If app HAS `background:execution` capability:
      - App continues running
      - ServiceWorker can process push/background-sync
      - Bridge socket remains active
4. Under memory pressure:
   - OOM killer targets suspended apps first (oom_score_adj = 1000)
   - If app is killed, next launch is cold start
```

### 3.3 Termination

```
1. User swipes app away in overview
2. OR system-initiated (low memory / battery saver)
3. All app processes killed via SIGKILL
4. WebKit WebContext saved to disk:
   - IndexedDB, CacheAPI, cookies persisted
   - ServiceWorker state checkpointed
5. Bridge connection terminated
   - Pending capability grants released
   - Event subscriptions cleaned up
```

### 3.4 Uninstall

```
1. User removes app via Settings → Apps → [App] → Uninstall
2. Flatpak uninstall: flatpak uninstall org.example.pwa
3. All app data removed:
   - /var/app/org.example.pwa/ deleted entirely (rm -rf)
   - Capability grants in /var/lib/nuxel/permissions/ removed
   - .desktop file in /usr/share/applications/ removed
   - App icon caches invalidated
4. No trace of the app remains
```

---

## 4. PWA Manifest Extensions

Nuxel extends the W3C Web App Manifest with fields for capability management:

```json
{
    "name": "Nuxel Mail",
    "short_name": "Mail",
    "description": "Email client for Nuxel",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#1a1a2e",
    "theme_color": "#16213e",
    
    "icons": [
        { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
        { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
    ],
    
    "categories": ["email", "productivity"],
    
    "nuxel_capabilities": [
        "network:outbound",
        "notifications:send",
        "notifications:receive",
        "storage:persistent"
    ],
    
    "nuxel_background_sync": true,
    "nuxel_min_protocol_version": 2,
    "nuxel_network_required": true
}
```

### Manifest Extensions

| Field | Type | Description |
|-------|------|-------------|
| `nuxel_capabilities` | `string[]` | Required capabilities (shown at install time) |
| `nuxel_background_sync` | `boolean` | Whether ServiceWorker can run in background |
| `nuxel_min_protocol_version` | `integer` | Minimum bridge protocol version required |
| `nuxel_network_required` | `boolean` | If true, app requires `network:outbound` |
| `nuxel_allowed_origins` | `string[]` | Additional origins allowed (e.g., API servers) |

---

## 5. Bridge Protocol: PWA ↔ nuxel-bridge

### 5.1 Transport

- **Unix domain socket** at `/run/nuxel/bridge/<app-id>.sock`
- **JSON message framing:** newline-delimited JSON (one JSON object per line)
- **Connection established** by the PWA launcher before loading start_url
- **Authentication:** App identity verified by the socket path ownership

### 5.2 Capability Request Flow (Portal Gated)

```
PWA                              nuxel-bridge                  nuxel-portal           User
 │                                    │                            │                   │
 │── bridge.handshake ──────────────> │                            │                   │
 │<── protocol_version, capabilities  │                            │                   │
 │                                    │                            │                   │
 │── requestCapability("location")  > │                            │                   │
 │                                    │── CheckPermission───────> │                   │
 │                                    │                            │── GTK4 Dialog ──> │
 │                                    │                            │                   │─ Allow/Deny
 │                                    │                            │<── User Response   │
 │                                    │<── PermissionResponse     │                   │
 │                                    │                            │                   │
 │                                    │── Store grant in          │                   │
 │                                    │   /var/lib/nuxel/         │                   │
 │                                    │   permissions/app-id.json │                   │
 │                                    │                            │                   │
 │<── capability_granted              │                            │                   │
 │                                    │                            │                   │
 │── location.get_current ──────────> │                            │                   │
 │<── { lat, lng, accuracy }         │                            │                   │
```

### 5.3 JavaScript Bridge API

```typescript
// window.nuxel API exposed by the PWA runtime

interface NuxelAPI {
    // Make a bridge method call
    call(method: string, params?: object): Promise<BridgeResult>;
    
    // Subscribe to bridge events
    on(event: string, callback: (data: any) => void): void;
    
    // Unsubscribe from events
    off(event: string, callback: (data: any) => void): void;
    
    // Check if a capability is currently granted
    hasCapability(capability: string): Promise<boolean>;
    
    // Request a new capability (shows portal dialog)
    requestCapability(capability: string): Promise<boolean>;
    
    // Get all currently granted capabilities
    getCapabilities(): Promise<string[]>;
    
    // Open the file picker portal
    pickFile(mimeTypes?: string[]): Promise<FileHandle>;
    
    // Check connection status
    isConnected(): boolean;
}

interface BridgeResult {
    success: boolean;
    data?: any;
    error?: {
        code: string;
        message: string;
    };
}
```

### 5.4 Portal-Driven Permission Requests from JS

```javascript
// PWA requests camera access through portal
async function takePhoto() {
    if (!await nuxel.hasCapability('camera:capture')) {
        // This triggers a GTK4 portal dialog for user consent
        const granted = await nuxel.requestCapability('camera:capture');
        if (!granted) {
            showToast('Camera access denied');
            return null;
        }
    }
    
    // Capability is now granted (for this session or permanently)
    try {
        const result = await nuxel.call('camera.capture');
        return result.image_data;
    } catch (e) {
        showToast('Failed to capture: ' + e.message);
        return null;
    }
}

// Permission status display
async function showPermissionInfo() {
    const caps = await nuxel.getCapabilities();
    const permissionList = document.getElementById('permissions');
    caps.forEach(cap => {
        const row = document.createElement('div');
        row.className = 'permission-row';
        row.innerHTML = `
            <span class="permission-name">${cap}</span>
            <span class="permission-status">Granted</span>
        `;
        permissionList.appendChild(row);
    });
}
```

---

## 6. Network Per-PWA Control

### 6.1 Default: No Network

By default, every PWA runs with **no network access**:
- `--share=ipc` only (unix sockets to nuxel-bridge)
- `--share=net` NOT set
- seccomp blocks `socket(AF_INET)` and `socket(AF_INET6)`

### 6.2 Network-Enabled PWAs

When a PWA has `network:outbound` capability:
- `--share=net` is added to bwrap arguments
- The PWA's cgroup is added to the nftables allow set
- DNS (port 53) is always allowed for resolution
- Only TCP and UDP outbound — no raw sockets, no packet sockets

### 6.3 VPN Awareness

If the system VPN is active:
- All app traffic routes through VPN interface
- Kill switch enforced by nftables (no traffic leaks outside VPN interface)
- Per-app split tunneling configurable in Settings

---

## 7. Service Worker in Phone Context

### 7.1 Offline-First Pattern

```javascript
// service-worker.js — Nuxel PWA Service Worker
const CACHE_NAME = 'nuxel-mail-v1';
const CRITICAL_URLS = ['/', '/index.html', '/css/mail.css', '/js/app.js'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(CRITICAL_URLS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys => 
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
});

self.addEventListener('fetch', (event) => {
    // Network-first with cache fallback for dynamic content
    // Cache-first for static assets
    const url = new URL(event.request.url);
    if (CRITICAL_URLS.includes(url.pathname)) {
        event.respondWith(cacheFirst(event.request));
    } else {
        event.respondWith(networkFirst(event.request));
    }
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    if (event.tag === 'send-queued-mail') {
        event.waitUntil(processMailQueue());
    }
    if (event.tag === 'sync-calendar') {
        event.waitUntil(syncCalendarEvents());
    }
});

// Push notifications handled through nuxel-notifications bridge
self.addEventListener('push', (event) => {
    const data = event.data.json();
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/icons/icon-192.png',
            badge: '/icons/icon-72.png',
            data: { url: data.url || '/' }
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.notification.data.url));
});
```

### 7.2 Push Notification Flow (PWA → System)

```
PWA ServiceWorker
    │
    ├── navigator.serviceWorker.register() → SW registration
    ├── Notification.requestPermission() → portal dialog
    │
    ▼
nuxel-bridge
    │
    ├── Receives notification.send() from PWA
    ├── Checks notifications:send capability
    ├── Forwards to org.freedesktop.Notifications
    │
    ▼
nuxel-notifications (org.freedesktop.Notifications)
    │
    ├── Displays notification in Phosh panel
    ├── Emits NotificationClosed signal when dismissed
    │
    ▼
PWA receives notificationclick event → app opens to relevant view
```

---

## 8. Comparison: Nuxel PWA vs Standard PWA

| Aspect | Standard Desktop PWA | Nuxel Hardened PWA |
|--------|---------------------|-------------------|
| **Runtime** | Shared browser instance | Isolated WebKitGTK instance |
| **Cookies** | Shared with browser | Per-app cookie jar |
| **Storage** | Shared with browser origins | Per-app data directory |
| **Service Workers** | Shared registration scope | Per-app, isolated |
| **Network** | Browser's full network | Gated by `network:outbound` capability |
| **Camera/Mic** | Browser permission prompt | Portal dialog with nuxel-portal |
| **Location** | Geolocation API prompt | Portal dialog → GeoClue2 |
| **File access** | Browser file picker | Portal file picker (fd only) |
| **Notifications** | Browser push | nuxel-notifications bridge |
| **Bluetooth/USB/NFC** | Web API (if browser supports) | **Disabled** |
| **Background** | Limited by browser | Controlled by `background:execution` cap |
| **Uninstall** | Browser manages | Full data removal |
| **Network isolation** | Browser-level | nftables cgroupv2 per-app |
| **IPC** | Full network stack | Only AF_UNIX to nuxel-bridge |
| **Sandbox stacking** | Browser sandbox only | 5-layer sandbox |

---

## 9. PWA Flatpak Packaging

Each PWA is packaged as a Flatpak extending `org.nuxel.PWARuntime`:

```json
{
    "app-id": "org.nuxel.Mail",
    "runtime": "org.nuxel.PWARuntime",
    "runtime-version": "stable",
    "sdk": "org.nuxel.PWARuntime",
    "command": "nuxel-pwa-launcher",
    
    "finish-args": [
        "--socket=wayland",
        "--socket=pipewire",
        "--filesystem=/var/app/org.nuxel.Mail/data",
        "--socket=/run/nuxel/bridge/org.nuxel.Mail.sock",
        "--env=NUXEL_APP_ID=org.nuxel.Mail",
        "--env=WEBKIT_DISABLE_COMPOSITING_MODE=1",
        "--env=WEBKIT_FORCE_SANDBOX=1"
    ],
    
    "modules": [
        {
            "name": "pwa-data",
            "buildsystem": "simple",
            "build-commands": [
                "install -Dm644 manifest.json /app/share/nuxel-pwa/manifest.json",
                "install -Dm755 launcher.sh /app/bin/nuxel-pwa-launcher",
                "install -Dm644 icon-192.png /app/share/icons/hicolor/192x192/apps/org.nuxel.Mail.png",
                "install -Dm644 icon-512.png /app/share/icons/hicolor/512x512/apps/org.nuxel.Mail.png",
                "install -Dm644 org.nuxel.Mail.desktop /app/share/applications/org.nuxel.Mail.desktop"
            ],
            "sources": [
                {"type": "dir", "path": "pwa/nuxel-apps/mail"}
            ]
        }
    ]
}
```

---

## 10. Known Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| Multi-process WebKit not available in sandbox | Slightly reduced isolation between PWA tabs | PWAs are single-tab; multi-process less critical |
| Memory overhead from per-app WebKit instances | Each PWA uses ~80-150 MB RSS | Capping at 8-10 concurrent PWAs; aggressive swap |
| ServiceWorker background sync unreliable | Events may be delayed until next launch | Use nuxel-notifications push as primary channel |
| WebRTC requires network capability | Video calls complex to implement | Use native libcalls/pipewire for telephony |
| WebAuthn integration with Titan M3 | Passkey UX not yet optimal | Basic credential management in Settings |
