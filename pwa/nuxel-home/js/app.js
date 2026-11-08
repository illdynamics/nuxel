// Nuxel Home - Main Application Controller
// Coordinates all components and handles global events

// PWNAGE-63000: relay a keyring-token request from the exact PWA iframe the
// launcher created to the native top-frame relay.  The WeakMap is keyed by the
// real event.source window, never by a value the iframe can supply.  The
// native relay holds the per-device secret in a top-frame-only closure and
// exchanges the request for a Bridge token for this app id.
const NuxelKeyringRelay = (function () {
    const frames = new WeakMap();
    const pending = new Map();
    const NONCE_RE = /^[A-Za-z0-9._-]{8,96}$/;
    function attach(frame, appId) {
        try { if (frame && frame.contentWindow) frames.set(frame.contentWindow, String(appId)); } catch (e) {}
    }
    try {
        window.addEventListener('message', function (event) {
            if (event.origin !== window.location.origin || !event.data) return;
            const data = event.data;
            if (data.type === 'nuxel-keyring-token-request') {
                const appId = frames.get(event.source);
                const nonce = String(data.nonce || '');
                if (!appId || !NONCE_RE.test(nonce)) return;
                pending.set(nonce, event.source);
                try {
                    window.postMessage({ type: 'nuxel-keyring-mint', app_id: appId, nonce: nonce },
                        window.location.origin);
                } catch (e) { pending.delete(nonce); }
                return;
            }
            if (event.source === window && data.type === 'nuxel-keyring-token') {
                const nonce = String(data.nonce || '');
                const source = pending.get(nonce);
                if (!source) return;
                pending.delete(nonce);
                try {
                    source.postMessage({ type: 'nuxel-keyring-token', nonce: nonce,
                        token: String(data.token || '') }, window.location.origin);
                } catch (e) { /* the frame is gone; the app will time out closed */ }
            }
        });
    } catch (e) { /* no DOM (offline tests) */ }
    return { attach: attach };
}());

class NuxelHome {
    constructor() {
        this.initialized = false;
        this.components = {};
        this.appGeneration = 0;
        this.appSession = { state: 'CLOSED', app: null, frame: null };
        // A Home press backgrounds an app; it must not tear down its document.
        // Keep one surface per app id so Recents can resume the exact session.
        this.appSurfaces = new Map();
        this.sessions = window.NuxelAppSessions ? new window.NuxelAppSessions() : null;
        // Input de-duplication: the native nav dock can deliver a long-press
        // as back-long AND a release/click back for the same gesture, and the
        // nuxel:action event is registered on both window and document.  A
        // single physical action must resolve to a single logical action.
        this._lastAction = null;
        this._lastActionAt = 0;
        this._suppressBackUntil = 0;
        this._backBusy = false;
        this._pwaBackStrikes = 0;
        this._fgInvisibleCount = 0;
        this._keyboardLikelyOpen = false;
        this._nativeKeyboardVisible = false;
        // v0.7.7-beta: every cold boot starts in portrait while the lockscreen
        // is up.  The previous orientation mode is remembered and restored only
        // after a successful unlock, so rotation becomes available again once
        // the owner is past the lockscreen.
        this._bootOrientationActive = false;
        this._bootOrientationPrevious = null;
        this._init();
    }

    _setAppState(state, app = this.appSession.app, frame = this.appSession.frame) {
        const allowed = ['CLOSED', 'LAUNCHING', 'ACTIVE', 'BACKGROUND', 'CLOSING', 'FAILED'];
        if (!allowed.includes(state)) throw new Error(`Invalid app lifecycle state: ${state}`);
        this.appSession = { state, app: app || null, frame: frame || null };
        document.body.dataset.appState = state;
        document.dispatchEvent(new CustomEvent('app:lifecycle', {
            detail: { state, appId: app && app.id ? app.id : null },
        }));
        this._inputTrace(`app:lifecycle id=${app && app.id || 'home'} state=${state}`);
    }

    /* Foreground visibility truth, independent of the ACTIVE string.  A PWA
       that is ACTIVE but whose iframe is hidden/backgrounded/zero-sized must
       never block the Applications drawer or hold the glass invisibly. */
    _foregroundSurfaceVisible() {
        const { app, frame, state } = this.appSession;
        if (state !== 'ACTIVE' || !app) return false;
        if (frame) {
            try {
                if (frame.__nuxelBackgrounded) return false;
                if (frame.getAttribute && frame.getAttribute('data-nuxel-backgrounded') === 'true') return false;
                if (frame.hidden) return false;
                const rect = frame.getBoundingClientRect();
                const vw = window.innerWidth || 360;
                const vh = window.innerHeight || 760;
                if (!rect || rect.width < 1 || rect.height < 1) return false;
                if (rect.right <= 0 || rect.bottom <= 0 || rect.left >= vw || rect.top >= vh) return false;
                const cs = window.getComputedStyle(frame);
                if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return false;
                const doc = frame.contentDocument;
                if (doc && doc.hidden) return false;
                return true;
            } catch (e) {
                // Cross-origin frames cannot be inspected; treat as visible so a
                // healthy foreign app is never destroyed by mistake.
                return true;
            }
        }
        // Native/flatpak apps own a separate Wayland surface that cannot be
        // inspected synchronously; the native Back reconciliation path is the
        // authority for those.
        return true;
    }

    isForegroundVisible() {
        return this._foregroundSurfaceVisible();
    }

    /* Bounded watchdog: an invisible foreground PWA is backgrounded within 1-2 s
       so holding Back to force-kill is never the only recovery. */
    _watchForegroundVisibility() {
        if (this._fgWatchdog) return;
        this._fgWatchdog = setInterval(() => {
            if (this.appSession.state !== 'ACTIVE' || !this.appSession.app || !this.appSession.frame) {
                this._fgInvisibleCount = 0;
                return;
            }
            if (this._foregroundSurfaceVisible()) {
                this._fgInvisibleCount = 0;
                return;
            }
            this._fgInvisibleCount++;
            this._inputTrace('foreground-visibility invisible count=' + this._fgInvisibleCount);
            if (this._fgInvisibleCount >= 2) {
                this._fgInvisibleCount = 0;
                this._backgroundForegroundApp();
                this.home();
                this._inputTrace('foreground-visibility watchdog recovered invisible app');
            }
        }, 1000);
    }

    _inputTrace(message) {
        try {
            const handler = window.webkit && window.webkit.messageHandlers.nuxelDiag;
            if (handler) handler.postMessage(`EVT ${message} ts=${Date.now()}`);
        } catch (e) { /* observation must never change input delivery */ }
    }

    _observeAppFrame(frame, app) {
        // The native host observes only the top document. App events do not
        // bubble out of an iframe: observe the same-origin document separately.
        // Record hit targets and lifecycle, never field values or entered text.
        try {
            const doc = frame.contentDocument;
            if (!doc || doc.__nuxelObserved) return;
            if (window.NuxelTouchKeyboard) window.NuxelTouchKeyboard.attach(doc);
            if (window.NuxelImmersive) window.NuxelImmersive.attach(doc);
            doc.__nuxelObserved = true;
            const editable = el => {
                try {
                    const tag = String((el && el.tagName) || '').toUpperCase();
                    return !!(el && (el.isContentEditable || tag === 'TEXTAREA' ||
                        (tag === 'INPUT' && !/^(button|checkbox|radio|submit|reset|file|range|color)$/i.test(String(el.type || 'text')))));
                } catch (e) { return false; }
            };
            doc.addEventListener('focusin', event => { if (editable(event.target)) this._keyboardLikelyOpen = true; }, { capture: true, passive: true });
            doc.addEventListener('focusout', () => {
                setTimeout(() => {
                    try { this._keyboardLikelyOpen = editable(doc.activeElement); } catch (e) { this._keyboardLikelyOpen = false; }
                }, 80);
            }, { capture: true, passive: true });
            doc.addEventListener('contextmenu', event => event.preventDefault());
            let lastMove = 0;
            const label = el => el && ((el.id || el.tagName || '').replace(/[^a-zA-Z0-9_.:-]/g, '').slice(0, 80)) || '-';
            ['pointerdown', 'pointerup', 'pointercancel', 'touchstart', 'touchmove', 'touchend', 'click', 'focusin', 'input'].forEach(kind => {
                doc.addEventListener(kind, event => {
                    if (kind === 'touchmove' && Date.now() - lastMove < 250) return;
                    if (kind === 'touchmove') lastMove = Date.now();
                    const point = event.changedTouches && event.changedTouches[0] || event;
                    const x = Number.isFinite(point.clientX) ? Math.round(point.clientX) : -1;
                    const y = Number.isFinite(point.clientY) ? Math.round(point.clientY) : -1;
                    const hit = x >= 0 && y >= 0 ? doc.elementFromPoint(x, y) : null;
                    const path = event.composedPath ? event.composedPath().slice(0, 5).map(label).join(':') : label(event.target);
                    this._inputTrace(`${kind} app=${app.id} x=${x} y=${y} id=${label(event.target)} hit=${label(hit)} path=${path} trusted=${event.isTrusted ? 1 : 0} state=${this.appSession.state}`);
                }, { passive: true, capture: true });
            });
        } catch (e) { /* cross-origin applications are deliberately not inspected */ }
    }

    _removeAppSurface(appId = null) {
        const ids = appId ? [appId] : Array.from(this.appSurfaces.keys());
        for (const id of ids) {
            const surface = this.appSurfaces.get(id);
            if (!surface) continue;
            try { if (surface.frame && surface.frame.contentWindow) surface.frame.contentWindow.stop(); } catch (e) {}
            [surface.frame, surface.bar, surface.status].forEach(el => {
                if (!el) return;
                try { el.remove(); } catch (e) {}
            });
            this.appSurfaces.delete(id);
        }
        // A stale node that lost its Map entry is still a full-screen iframe and
        // can keep an invisible modal/input layer alive.  Remove only nodes that
        // are no longer owned by a live background session; removing every
        // surface here would silently destroy every tab in Recents.
        try {
            const live = new Set();
            this.appSurfaces.forEach(surface => {
                [surface.frame, surface.bar, surface.status].forEach(el => { if (el) live.add(el); });
            });
            document.querySelectorAll('.pwa-frame,.pwa-app-status,.pwa-app-bar').forEach(el => {
                if (!live.has(el)) el.remove();
            });
        } catch (e) {}
        try {
            if (document.exitPointerLock) document.exitPointerLock();
            if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
        } catch (e) {}
    }

    _closeAppSurface(reason) {
        const app = this.appSession.app;
        const appId = app && app.id;
        this.appGeneration++;
        if (app && app.id === 'org.nuxel.Terminal' &&
            !this.appSession.frame && window.NuxelHost && window.NuxelHost.available) {
            Promise.resolve(window.NuxelHost.action('close-terminal')).catch(error => {
                console.error('[Nuxel] Terminal close failed:', error);
            });
        }
        // Keyboard/IME focus, pointer grabs and transient overlays belong to the
        // closing app.  Release them before the compositor is asked to repaint.
        try { this._dismissKeyboard(); } catch (e) {}
        if (this.appSession.state !== 'CLOSED') this._setAppState('CLOSING', app, this.appSession.frame);
        this._removeAppSurface(appId || null);
        ['#nuxel-power-menu'].forEach(sel => {
            try { document.querySelectorAll(sel).forEach(el => el.remove()); } catch (e) {}
        });
        this._setAppState('CLOSED', null, null);
        this._nativeKeyboardVisible = false;
        this._keyboardLikelyOpen = false;
        if (this.sessions) {
            if (appId) this.sessions.close(appId);
            else this.sessions.home();
        }
        try {
            window.dispatchEvent(new CustomEvent('nuxel:app-closed', {
                detail: { appId: appId || null, reason: reason || 'close' },
            }));
        } catch (e) {}
        try {
            if (window.NuxelZoomPolicy && window.NuxelZoomPolicy.reset) window.NuxelZoomPolicy.reset(window);
        } catch (e) {}
        try {
            const host = window.NuxelHost;
            if (host && host.available && typeof host.action === 'function') {
                Promise.resolve(host.action('after-app-close')).catch(() => {});
            }
        } catch (e) {}
        this._inputTrace(`app:closed id=${appId || 'none'} reason=${reason || 'close'}`);
    }

    _notifyAppFrame(type, reason) {
        const frame = this.appSession.frame;
        if (!frame || !frame.contentWindow) return;
        try {
            frame.contentWindow.postMessage({ type, reason: reason || type }, window.location.origin);
        } catch (e) { /* a cross-origin or torn-down frame is ignored */ }
    }

    _backgroundForegroundApp(replacing = false) {
        const { app, frame } = this.appSession;
        if (!app || this.appSession.state === 'CLOSED') return false;
        // A new foreground intent invalidates callbacks from the app being
        // backgrounded (a slow launch acknowledgement must not steal ACTIVE).
        this.appGeneration++;
        // Tell a same-origin app to suspend its runtime before the surface is
        // removed from hit-testing.  Doom uses this to pause the WASM loop;
        // document.visibilitychange alone was not delivered while the parent
        // lockscreen covered a still-ACTIVE iframe (measured 136% CPU).
        this._notifyAppFrame('nuxel:suspend', 'background');
        // A native application owns a separate top-level Wayland surface, not a
        // DOM iframe.  Home/lock must only MINIMIZE it: calling
        // _closeAppSurface() retired the launcher session (and a Terminal PTY)
        // even though the owner merely pressed Power or Home.  Keep the process
        // and its session alive so it is still running after unlock and the
        // same window can be resumed instead of spawning a second copy.
        if (!frame) {
            // When another app is taking the glass, retire Terminal's native
            // GTK/WebKit window instead of merely minimizing it: a top-level
            // Wayland surface would otherwise stay above the launcher/PWA
            // frame.  Home, lock and recents pass replacing=false and must
            // preserve the running Terminal PTY.
            if (replacing && app.id === 'org.nuxel.Terminal' &&
                window.NuxelHost && window.NuxelHost.available) {
                Promise.resolve(window.NuxelHost.action('close-terminal')).catch(error => {
                    console.error('[Nuxel] Terminal close failed:', error);
                });
            }
            this._setAppState('BACKGROUND', app, null);
            if (this.sessions && app) this.sessions.home();
            this._httpBridge('POST', '/api/v1/apps/home', { app_id: 'org.nuxel.Home' }, 4000);
            this._inputTrace(`app:backgrounded id=${app.id} native=1 preserved=1`);
            return true;
        }
        const surface = this.appSurfaces.get(app.id);
        if (surface) {
            [surface.frame, surface.bar, surface.status].forEach(el => {
                if (el) el.hidden = true;
            });
        } else {
            frame.hidden = true;
        }
        // Returning to the launcher always restores the ordinary chrome.  A
        // fullscreen game must not leave the top bar or the nav strip hidden.
        if (window.NuxelImmersive) window.NuxelImmersive.reset();
        this._setNavDock(true);
        // Remember the user's intent for an app that is still loading.  Its
        // load handler must not flip an intentionally backgrounded surface back
        // to ACTIVE and paint over Home.  The data attribute is the CSS hook:
        // .pwa-frame carries an author-level `display: block !important`, so
        // the boolean `hidden` property alone cannot win against it.  Setting
        // both is what actually removes the app iframe from the glass and from
        // hit-testing before Home's dock is shown.
        frame.__nuxelBackgrounded = true;
        if (typeof frame.setAttribute === 'function') frame.setAttribute('data-nuxel-backgrounded', 'true');
        this._setAppState('BACKGROUND', app, frame);
        if (this.sessions && app) this.sessions.home();
        try {
            const host = window.NuxelHost;
            if (host && host.available && typeof host.action === 'function') {
                Promise.resolve(host.action('force-redraw')).catch(() => {});
            }
        } catch (e) {}
        return true;
    }

    _resumeApp(app) {
        const surface = app && this.appSurfaces.get(app.id);
        if (!surface) return false;
        if (this.appSession.app && this.appSession.app.id !== app.id) this._backgroundForegroundApp(true);
        [surface.frame, surface.bar, surface.status].forEach(el => {
            if (el) el.hidden = false;
        });
        // A PWA owns the glass: its triple buttons start hidden and the bottom
        // edge gesture reveals them.  Native apps still use their own dock.
        this._setNavDock(false);
        if (surface.frame) {
            try { this._installPwaHistoryProbe(surface.frame); } catch (e) {}
            surface.frame.__nuxelBackgrounded = false;
            if (typeof surface.frame.removeAttribute === 'function') surface.frame.removeAttribute('data-nuxel-backgrounded');
            this._observeAppFrame(surface.frame, app);
        }
        this._setAppState('ACTIVE', app, surface.frame);
        // The surface is visible again; let the app resume a paused runtime.
        this._notifyAppFrame('nuxel:resume', 'resume');
        // A game or any app may gain focus without owning an editable field.
        // Never let a stale IME surface ride along with the app launch.
        this._dismissKeyboard();
        if (this.sessions) this.sessions.activate(app.id);
        return true;
    }

    async _init() {
        console.log('[Nuxel] Initializing Nuxel Home...');

        // Initialize all components
        this.components = {
            bridge: bridge,
            statusBar: window.statusBar,
            launcher: window.launcher,
            search: window.search || null,
            recents: null,
            qs: window.qs || null,
        };
        // The native host publishes the actual OSK visibility, including for
        // native toplevels and frames this controller cannot inspect directly.
        // Back's first precedence rule therefore remains truthful everywhere.
        try {
            if (window.NuxelHost && typeof window.NuxelHost.onEvent === 'function') {
                window.NuxelHost.onEvent((name, detail) => {
                    if (name !== 'keyboard-visible' || !detail) return;
                    this._nativeKeyboardVisible = detail.visible === true ||
                        detail.visible === 1 || detail.visible === '1';
                    if (this._nativeKeyboardVisible) this._keyboardLikelyOpen = true;
                });
            }
        } catch (e) {}

        // Bind global events
        this._bindGlobalEvents();

        // A45 Penguin lockscreen + boot lock + display-off re-lock.
        this._initLockscreen();

        this.initialized = true;
        console.log('[Nuxel] Nuxel Home initialized');

        // PWNAGE-45000: the canonical registry file is authoritative.  Merge it
        // after first paint so NuxTore-installed local apps appear without a
        // reboot and static fallback entries cannot drift from the device.
        try {
            if (window.appRegistry && window.appRegistry.refreshFromBridge) {
                window.appRegistry.refreshFromBridge();
                if (window.appRegistry.startBridgeWatch) window.appRegistry.startBridgeWatch(30000);
            }
        } catch (e) { /* first paint must not depend on the bridge */ }

        // Boot animation splash: fade out once the app is ready (see below)
        this._finishBootSplash();

        // App navigation must work even while an optional backend or service
        // worker is unavailable. Neither request owns the splash or input.
        this._registerServiceWorker();
        this._requestCoreCapabilities().catch(error => {
            console.warn('[Nuxel] Core capabilities unavailable:', error);
        });
        this._warmLauncherChrome();
    }

    /* PWNAGE-37000B: move the first-open DOM/decode cost of the drawer and
       Home Settings off the owner's tap.  This runs once, in an idle slice
       after the launcher is interactive, and never delays first paint. */
    _warmLauncherChrome() {
        const warm = () => {
            try {
                if (window.launcher && window.launcher._renderDrawerApps) {
                    // Build the cached drawer markup without showing it.
                    window.launcher._renderDrawerApps();
                }
            } catch (e) { /* optional warm-up */ }
            try {
                if (window.NuxelHomeSettings && window.NuxelHomeSettings.prime) {
                    window.NuxelHomeSettings.prime();
                }
            } catch (e) { /* optional warm-up */ }
            // Decode the warmed hidden images now.  Building the DOM alone did
            // not pay the first-open decode cost (measured 168 ms); the second
            // open was 3 ms because the bitmaps were then resident.
            const decodeAll = (root) => {
                if (!root || !root.querySelectorAll) return;
                root.querySelectorAll('img').forEach((img) => {
                    if (!img || !img.decode) return;
                    try {
                        const p = img.decode();
                        if (p && p.catch) p.catch(() => {});
                    } catch (e) { /* decode is best-effort */ }
                });
            };
            decodeAll(document.getElementById('drawer-list'));
            decodeAll(document.getElementById('home-settings'));
            // Force the one-time grid/sheet layout while both are invisible.
            // No frame can paint inside this task, and the owner's first tap
            // then only toggles visibility (the layout cache is warm).
            const drawer = document.getElementById('drawer-list');
            if (drawer && drawer.hidden) {
                drawer.hidden = false;
                void drawer.offsetHeight;
                drawer.hidden = true;
            }
            const sheet = document.getElementById('home-settings');
            if (sheet && sheet.hidden) {
                sheet.hidden = false;
                void sheet.offsetHeight;
                sheet.hidden = true;
            }
        };
        const schedule = window.requestIdleCallback
            ? () => window.requestIdleCallback(warm, { timeout: 4000 })
            : () => setTimeout(warm, 2200);
        // Give the lockscreen/boot handoff a settled first frame before doing
        // optional work.
        setTimeout(schedule, 1800);
    }

    _finishBootSplash() {
        // The nuxel-boot-animation.mp4 plays as a fullscreen splash while the
        // app boots. Fade it out once the app is initialized AND the animation
        // has had a chance to play (full playthrough or ~3s minimum), so the
        // animation is actually seen without delaying the UI. Safety timeout
        // guarantees the splash can never outlive 12s.
        const hide = () => document.body.classList.add('ready');

        // BOOT-ANIMATION OWNERSHIP (?boot=os).
        // On the S10+ the OS has already played the authoritative boot animation
        // from the initramfs before this document exists, so a second fullscreen
        // animation here would (a) show the animation twice and (b) put an
        // opaque, pointer-events:auto element above the launcher for up to 12 s.
        // In that launch mode the splash is REMOVED from the DOM (not merely
        // faded), so it can neither flash over the launcher nor intercept a
        // touch. The VM/desktop launch has no such parameter and is unchanged.
        try {
            if (new URLSearchParams(window.location.search).get('boot') === 'os') {
                const splash = document.getElementById('boot-splash');
                if (splash && splash.parentNode) splash.parentNode.removeChild(splash);
                hide();
                this._holdPreloadCover();
                return;
            }
        } catch (e) { /* URLSearchParams unavailable: fall through to normal path */ }

        const video = document.getElementById('boot-splash-video');
        if (!video || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            hide();
            return;
        }
        const started = Date.now();
        let minPlayed = false;
        const maybeHide = () => {
            if (minPlayed && Date.now() - started >= 3000) {
                hide();
            }
        };
        video.addEventListener('ended', () => { minPlayed = true; maybeHide(); });
        video.addEventListener('timeupdate', () => {
            if (video.currentTime >= 3) { minPlayed = true; maybeHide(); }
        });
        video.addEventListener('error', hide);
        setTimeout(hide, 12000);
    }

    /* PWNAGE-36000: hold the opaque first-frame cover until the mpv preload
       overlay has actually presented a frame.  The native controller writes
       /run/nuxel/preload-cinema.overlay; the session exposes it as the
       same-origin preload-status.json.  States:
         starting -> keep waiting
         covered  -> reveal the real lockscreen underneath the video
         fallback/done -> reveal the lockscreen (fail-open)
       A 15 s poll deadline and a 15 s hard stop make a missing/stuck marker
       harmless; the early controller waits for launcher_ready before it maps
       mpv, so this cover is what hides WebKit until the video is on top. */
    _holdPreloadCover() {
        if (this._preloadCoverDone) return;
        const cover = document.getElementById('preload-cover');
        if (!cover) return;
        const started = Date.now();
        let revealing = false;
        const reveal = (why) => {
            if (this._preloadCoverDone || revealing) return;
            revealing = true;
            preloadLockscreen().then(() => new Promise((resolve) => {
                const raf = window.requestAnimationFrame || ((fn) => setTimeout(fn, 0));
                raf(() => raf(resolve));
            })).then(() => {
                if (this._preloadCoverDone) return;
                this._preloadCoverDone = true;
                document.body.classList.add('preload-ready');
                try { console.log('[Nuxel] preload cover released: ' + why); } catch (e) {}
            });
        };
        // The preloading clip is composited ABOVE this WebView.  When mpv exits
        // the panel shows whatever WebKit last painted, so the lockscreen
        // wallpaper/lockhead must already be decoded.  Waiting for a real image
        // decode here is what removes the black/white frame between the MP4 and
        // the lockscreen; it is bounded and never blocks first paint.
        const preloadLockscreen = () => new Promise((resolve) => {
            const urls = ['/assets/nuxel-lockscreen.jpg', '/assets/nuxel-lockhead.png',
                          '/assets/nuxel-connection-mode.png', '/assets/nuxel-file-transfer.png'];
            let left = urls.length;
            const done = () => { if (--left <= 0) resolve(); };
            urls.forEach((src) => {
                const img = new Image();
                img.onload = () => {
                    if (img.decode) img.decode().then(done, done);
                    else done();
                };
                img.onerror = done;
                img.src = src;
                if (img.complete && img.naturalWidth) {
                    if (img.decode) img.decode().then(done, done); else done();
                }
            });
            setTimeout(resolve, 2500);
        });
        const endpoint = new URL('preload-status.json', window.location.href);
        const timeoutMs = 40000;
        // The controller can publish "covered" before this document has even
        // committed (mpv maps first, the PWA loads a few hundred ms later).
        // Releasing on the first poll then exposed the lockscreen while the
        // video was still compositing.  Hold the poster frame for a short
        // bounded grace period so the first video frames are on the panel.
        const minHoldMs = 1400;
        let backoffMs = 100;
        const schedule = (fn, delayMs) => {
            if (this._preloadCoverDone) return;
            setTimeout(fn, delayMs);
        };
        const poll = () => {
            if (this._preloadCoverDone) return;
            const elapsed = Date.now() - started;
            endpoint.searchParams.set('_', String(Date.now()));
            fetch(endpoint.toString(), { cache: 'no-store' })
                .then((r) => (r && r.ok) ? r.json() : null)
                .then((doc) => {
                    backoffMs = 100;
                    const terminal = doc && (doc.state === 'fallback' || doc.state === 'done');
                    const covered = doc && doc.state === 'covered';
                    if (terminal) { reveal('marker:' + doc.state); return; }
                    if (covered) {
                        if (elapsed < minHoldMs) {
                            schedule(poll, Math.min(100, minHoldMs - elapsed));
                            return;
                        }
                        reveal('marker:covered');
                        return;
                    }
                    if (elapsed >= timeoutMs) { reveal('timeout'); return; }
                    schedule(poll, 100);
                })
                .catch(() => {
                    if (elapsed >= timeoutMs) { reveal('timeout-fetch-error'); return; }
                    // A missing status file (404) or fetch error is the common
                    // warm-boot case. Back off instead of hammering nuxel-web
                    // every 100 ms while the hard timeout still bounds the cover.
                    backoffMs = Math.min(1000, Math.max(100, backoffMs * 2));
                    schedule(poll, backoffMs);
                });
        };
        poll();
        setTimeout(() => reveal('hard-timeout'), 40000);
    }

    async _registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/pwa/nuxel-home/sw.js', {
                    // Scope must be within the SW script directory (/pwa/nuxel-home/).
                    // '/', the previous value, is rejected by browsers (SecurityError:
                    // scope not under max allowed scope) so the worker never installed.
                    scope: '/pwa/nuxel-home/',
                });
                console.log('[Nuxel] Service worker registered:', registration.scope);

                // Handle service worker updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            // New version available
                            this._showUpdateNotification();
                        }
                    });
                });

                // Listen for messages from service worker
                navigator.serviceWorker.addEventListener('message', (event) => {
                    this._handleServiceWorkerMessage(event.data);
                });

            } catch (e) {
                console.warn('[Nuxel] Service worker registration failed:', e);
            }
        } else {
            console.warn('[Nuxel] Service workers not supported');
        }
    }

    async _requestCoreCapabilities() {
        const coreCapabilities = ['phone:status', 'notifications:receive'];
        for (const cap of coreCapabilities) {
            await bridge.requestCapability(cap);
        }
    }

    _bindGlobalEvents() {
        const topEditable = el => {
            try {
                const tag = String((el && el.tagName) || '').toUpperCase();
                return !!(el && (el.isContentEditable || tag === 'TEXTAREA' ||
                    (tag === 'INPUT' && !/^(button|checkbox|radio|submit|reset|file|range|color)$/i.test(String(el.type || 'text')))));
            } catch (e) { return false; }
        };
        document.addEventListener('focusin', e => { if (topEditable(e.target)) this._keyboardLikelyOpen = true; }, { capture: true, passive: true });
        document.addEventListener('focusout', () => {
            setTimeout(() => { this._keyboardLikelyOpen = topEditable(document.activeElement); }, 80);
        }, { capture: true, passive: true });

        // Handle incoming calls
        document.addEventListener('call:incoming', (event) => {
            this._showIncomingCall(event.detail);
        });

        // Handle app launch events from search or recents
        document.addEventListener('app:launch', (event) => {
            console.log(`[Nuxel] Launching app: ${event.detail.app.name}`);
            // A69-13: dismiss launcher chrome (app drawer, search, recents,
            // folder sheet, edit mode) BEFORE the app surface is created, so the
            // chosen app can never be raised behind the Applications drawer.
            this._dismissLauncherChrome();
        });

        // Handle PWA open events
        document.addEventListener('pwa:open', (event) => {
            const { app, url } = event.detail;
            this._openPwa(app, url);
        });

        // Handle native launch events
        document.addEventListener('native:launch', (event) => {
            const { app, url } = event.detail;
            this._launchNative(app, url);
        });

        // A32 — logical actions from the Nuxel hardware buttons / host API.
        // The button manager and the Settings app never poke the DOM directly:
        // they emit the same logical action, which is resolved here.
        // A34 TOUCHDOWN: nuxel-pwa-host delivers host actions with
        // `window.dispatchEvent(new CustomEvent('nuxel:action', ...))`.  An
        // event dispatched on window does NOT bubble down to document, so the
        // document-only listener here never saw the host's `home` / `search` /
        // `settings` actions (measured: launch Mail, then host `action home`
        // left the Mail iframe on the glass).  Listen on both targets; the same
        // handler is idempotent.
        const onNuxelAction = (event) => {
            const action = event.detail && event.detail.action;
            console.log('[Nuxel] logical action:', action);
            if (!action) return;
            this._inputTrace('nav:action ' + action + ' locked=' + (this._isLocked() ? 1 : 0));
            const _now = Date.now();
            // Coalesce the same logical action that arrives twice from the two
            // registered targets or from the nav dock's pointerup + click.  The
            // window is far shorter than any deliberate double-press.
            if (action === this._lastAction && _now - this._lastActionAt < 250) {
                this._inputTrace('nav:dedupe action=' + action);
                return;
            }
            this._lastAction = action;
            this._lastActionAt = _now;
            // A long-press Back terminates the foreground app; the nav dock's
            // release then emits a short Back for the same gesture.  Swallow it
            // so one held Back never also performs a second navigation.
            if (action === 'back' && _now < this._suppressBackUntil) {
                this._inputTrace('nav:suppress-back-after-long');
                return;
            }
            if (action === 'lock') { this._lock('host'); return; }
            if (action === 'unlock') {
                if (this._isLocked()) {
                    // PWNAGE-52000: a host/dock unlock must pass the SAME
                    // authoritative credential check as the penguin gesture.
                    // Otherwise the visible overlay hid while
                    // /run/nuxel/security/lock-state.json stayed locked, and
                    // the native dock correctly refused to map.
                    const verify = (window.NuxelSecurityLock && window.NuxelSecurityLock.verifyUnlock)
                        ? Promise.resolve(window.NuxelSecurityLock.verifyUnlock())
                        : Promise.resolve({ ok: true, legacy: true });
                    verify.then((v) => {
                        if (v && v.ok === true) this._unlock('host-verified');
                        else this._inputTrace('unlock:host-rejected ' + ((v && (v.error || v.detail)) || 'unknown'));
                    }).catch((e) => this._inputTrace('unlock:host-error ' + (e && e.message ? e.message : e)));
                    return;
                }
                // A45 pwa-host bug: the native nav dock's long-press Back
                // ("back-long") is dispatched as "unlock" (its js_action map
                // never added a back-long entry).  A session that is already
                // unlocked can only receive that misrouted long-press, so honour
                // the owner's real intent: terminate ONLY the foreground app.
                this.terminateForeground();
                return;
            }
            if (this._isLocked()) {
                // The local lockscreen is only a cache.  If a host/dock action
                // arrives while it still says locked, reconcile with the
                // authoritative security provider and replay the action ONLY
                // after the provider confirms unlocked.  A real lock returns
                // true and nothing is replayed.
                this._inputTrace('nav:locked-reconcile action=' + action);
                if (this._reconcileLockThenRetry(() => {
                    this._lastAction = null;
                    try { window.dispatchEvent(new CustomEvent('nuxel:action', { detail: { action } })); } catch (e) {}
                })) return;
                return;
            }
            if (action === 'home') this.home();
            else if (action === 'back') this.back();
            else if (action === 'back-long' || action === 'terminate') this.terminateForeground();
            else if (action === 'forward') this.forward();
            else if (action === 'stop') this.stopLoading();
            else if (action === 'reload-launcher') this.reloadLauncher();
            else if (action === 'recents') this.recentsToggle();
            else if (action === 'all-apps') {
                this._dismissLauncherChrome();
                if (window.launcher) window.launcher.openDrawer();
            }
            else if (action === 'notifications-panel') {
                this._dismissLauncherChrome();
                if (this.components.qs) this.components.qs.open();
            }
            else if (action === 'search' && this.components.search) this.components.search.open();
            else if (action === 'settings') appRegistry.launchApp('nuxel-settings');
        };
        document.addEventListener('nuxel:action', onNuxelAction);
        window.addEventListener('nuxel:action', onNuxelAction);

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+F or / for search
            if ((e.ctrlKey && e.key === 'f') || e.key === '/') {
                e.preventDefault();
                if (this.components.search) {
                    this.components.search.open();
                }
            }
            // Escape to close overlays
            if (e.key === 'Escape') {
                this._closeOverlays();
            }
        });
        // Long press is reserved for launcher editing and never opens WebKit's
        // generic Back/Forward/Stop/Reload context menu.
        document.addEventListener('contextmenu', event => event.preventDefault());

        // Keep lifecycle truth aligned with WebKit visibility.  BACKGROUND is
        // descriptive only: it never creates another surface or input owner.
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.appSession.state === 'ACTIVE') {
                this._setAppState('BACKGROUND');
            } else if (!document.hidden && this.appSession.state === 'BACKGROUND') {
                this._setAppState('ACTIVE');
            }
        });
    }

    _showIncomingCall(detail) {
        const statusBar = document.getElementById('phone-status');
        if (statusBar) {
            statusBar.classList.remove('hidden');
            document.getElementById('call-status-text').textContent = 
                `Incoming call from ${detail.number || 'Unknown'}`;
            
            document.getElementById('call-status-end').onclick = () => {
                bridge.endCall();
                statusBar.classList.add('hidden');
            };
        }
    }

    _applyAppOrientation(appId) {
        // The bridge is the single owner of the compositor transform.  This
        // covers PWA and native launches/resumes from the launcher; the bridge
        // also applies it on /apps/exec and /windows/activate for other paths.
        try {
            if (typeof bridge !== 'undefined' && bridge && typeof bridge.call === 'function') {
                Promise.resolve(bridge.call('apps', 'apply-orientation', { app_id: appId }))
                    .catch(() => {});
            }
        } catch (e) { /* orientation must never block a launch */ }
    }

    _openPwa(app, url) {
        console.log(`Opening PWA: ${app.name} at ${url}`);
        // A deep link, manifest shortcut or late startup callback must never
        // build an app surface over the lockscreen.  The user can launch it
        // again after the boot unlock, which always lands on Home.
        if (this._isLocked()) {
            this._inputTrace(`launch:blocked-locked app=${app.id}`);
            if (this._reconcileLockThenRetry(() => this._openPwa(app, url))) return;
            return;
        }
        this._applyAppOrientation(app.id);
        this._dismissLauncherChrome();
        if (this._resumeApp(app)) return;
        this._backgroundForegroundApp(true);
        // A new foreground app invalidates every in-flight launch callback
        // (for example a slow Terminal acknowledgement) before it can claim
        // ACTIVE over the app the owner actually opened.
        const generation = ++this.appGeneration;
        this._setAppState('LAUNCHING', app, null);

        // A34 TOUCHDOWN: the terminal is a real PTY rendered in a SEPARATE
        // native GTK/WebKit window (one instance, driven by nuxel-pwa-host).
        // Opening an iframe as well produced two terminal surfaces: closing the
        // native window revealed a second, non-functional one, and home could
        // not dismiss the native surface.  Launch it through the host instead.
        if (app.id === 'org.nuxel.Terminal' &&
            window.NuxelHost && window.NuxelHost.available) {
            Promise.resolve(window.NuxelHost.action('open-terminal')).then((result) => {
                if (generation !== this.appGeneration) return;
                if (!result || !result.ok) throw new Error((result && (result.error || (result.timeout && 'timeout'))) || 'host refused terminal launch');
            this._setAppState('ACTIVE', app, null);
                if (this.sessions) this.sessions.register(app, null);
            }).catch((error) => {
                if (generation !== this.appGeneration) return;
                console.error('[Nuxel] Terminal launch failed:', error);
                this._setAppState('FAILED', app, null);
            });
            return;
        }

        const frame = document.createElement('iframe');
        frame.src = url;
        frame.className = 'pwa-frame';
        frame.setAttribute('title', app.name);
        frame.style.cssText = `
            position: fixed !important;
            top: var(--status-bar-height, 36px) !important;
            left: 0 !important;
            right: 0 !important;
            width: 100vw !important;
            bottom: var(--system-nav-height) !important;
            height: calc(100dvh - var(--status-bar-height, 36px) - var(--system-nav-height)) !important;
            min-height: 0 !important;
            border: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            z-index: 60 !important;
            background: #071426 !important;
            display: block !important;
        `;
        document.body.appendChild(frame);
        try { NuxelKeyringRelay.attach(frame, app.id); } catch (e) {}
        // PWA chrome is immersive by default: no native dock over the app.  The
        // bottom swipe reveals it (immersive.js -> nuxel.setNavVisible).
        // Calendar is a normal app with persistent Nuxel navigation.  Every
        // other PWA is immersive by default.  The native dock reserves its
        // exclusive zone, so the OSK sits above the three buttons.
        const persistentNav = app.id === 'org.nuxel.Calendar';
        this._setNavDock(persistentNav);
        this._setAppState('LAUNCHING', app, frame);

        const status = document.createElement('div');
        status.className = 'pwa-app-status';
        status.setAttribute('role', 'status');
        status.textContent = `Opening ${app.name}…`;
        status.style.cssText = `
            position: fixed !important; inset: auto 16px 24px 16px !important;
            z-index: 62 !important; padding: 12px 16px !important;
            border-radius: 12px !important; background: rgba(0,0,0,.82) !important;
            color: white !important; text-align: center !important;
        `;
        document.body.appendChild(status);

        frame.addEventListener('load', () => {
            if (this.appSession.frame !== frame) return;
            status.remove();
            try { this._installPwaHistoryProbe(frame); } catch (e) {}
            if (frame.__nuxelBackgrounded || this.appSession.state === 'BACKGROUND') {
                // Home was pressed while this document was loading.  Keep it
                // hidden; Recents can still resume the completed session.
                this._observeAppFrame(frame, app);
                return;
            }
            this._setAppState('ACTIVE', app, frame);
            this._observeAppFrame(frame, app);
            this._setNavDock(app.id === 'org.nuxel.Calendar');
            this._dismissKeyboard();
        }, { once: true });
        frame.addEventListener('error', () => {
            if (this.appSession.frame !== frame) return;
            status.textContent = `${app.name} could not load. Close it to return Home.`;
            this._setAppState('FAILED', app, frame);
        }, { once: true });

        // PWNAGE-43000: no second in-app title bar.  The status bar above and
        // the native Back/Home/Recents layer are the only chrome; an app-owned
        // "Home + app name" strip is redundant and cost 56 px of every app.
        // The surface record keeps `bar: null` so lifecycle hiding is uniform.
        this.appSurfaces.set(app.id, { frame, bar: null, status });
        if (this.sessions) this.sessions.register(app, this.appSurfaces.get(app.id));
    }

    _launchNative(app, url) {
        console.log(`Launching native app: ${app.name} (${url})`);
        // Same lock gate for registry/host deep links as _openPwa().
        if (this._isLocked()) {
            this._inputTrace(`launch:blocked-locked app=${app.id}`);
            if (this._reconcileLockThenRetry(() => this._launchNative(app, url))) return;
            return;
        }
        this._applyAppOrientation(app.id);
        this._dismissLauncherChrome();
        // Native applications are fullscreen top-level Wayland clients.  The
        // global contract is the same as for PWAs: no visible triple buttons
        // over the app.  nuxel-navdock keeps a 14 px bottom gesture strip
        // mapped instead; an upward swipe reveals Back/Home/Recents and then
        // auto-hides them.  Home and the lockscreen are the only exceptions.
        this._backgroundForegroundApp(true);
        this._setNavDock(false);
        const generation = ++this.appGeneration;
        const target = app.nativeAppId || app.id;
        this._setAppState('LAUNCHING', app, null);

        // Installed state check for apps that may not be present (e.g. Snapshot).
        if (app.installed === false || app.status === 'unsupported') {
            this._setAppState('FAILED', app, null);
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = app.status === 'unsupported'
                ? `${app.name}: not supported on this device (${app.description || 'unavailable'})`
                : `${app.name} is not installed on this device`;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 5000);
            return;
        }

        // Lock/Home/minimize never terminate a native process.  Before
        // spawning anything, ask the compositor for its real toplevel inventory
        // and activate that exact window if it is still alive.  This is what
        // makes "lock, unlock, tap the icon again" resume the running app
        // instead of creating a second instance (and a second window).
        this._findLiveNativeWindow(app).then((win) => {
            if (generation !== this.appGeneration) return;
            if (!win) return this._execNativeLaunch(app, target, generation);
            const surfaceTarget = win.app_id || target;
            return this._httpBridge('POST', '/api/v1/windows/activate', {
                app_id: surfaceTarget,
            }, 6000).then((res) => {
                if (generation !== this.appGeneration) return;
                if (!res || res.success === false) return this._execNativeLaunch(app, target, generation);
                if (this.appSession.app && this.appSession.app.id !== app.id) return;
                console.log('[Nuxel] native resumed:', surfaceTarget);
                this._setAppState('ACTIVE', app, null);
                if (this.sessions) this.sessions.register(app, null);
                this._inputTrace('native:resumed id=' + app.id + ' surface=' + surfaceTarget);
            });
        }).catch(() => {
            if (generation === this.appGeneration) this._execNativeLaunch(app, target, generation);
        });
    }

    _findLiveNativeWindow(app) {
        const target = app.nativeAppId || app.flatpak_id || app.id;
        const ids = [target, app.id, app.nativeAppId, app.flatpak_id].filter(Boolean);
        const wantedTitle = String(app.name || '').trim().toLowerCase();
        return this._httpBridge('GET', '/api/v1/windows/list', null, 4000).then((list) => {
            const windows = (list && Array.isArray(list.windows)) ? list.windows : [];
            return windows.find((win) => {
                if (!win || win.home) return false;
                if (ids.indexOf(win.app_id) >= 0) return true;
                const title = String(win.title || '').toLowerCase();
                return !!(wantedTitle && title.indexOf(wantedTitle) >= 0);
            }) || null;
        });
    }

    _execNativeLaunch(app, target, generation = null) {
        // The authoritative launch authority is the HTTP bridge's CLOSED-verb
        // /apps/exec endpoint: it resolves the target from its fixed allowlist /
        // canonical registry and never executes a client-supplied path.
        this._httpBridge('POST', '/api/v1/apps/exec', {
            target: target,
            app_id: 'org.nuxel.Home',
            source: 'launcher',
        }, 30000).then((res) => {
            if (generation !== null && generation !== this.appGeneration) return;
            if (!res || res.success !== true) {
                const err = new Error((res && (res.error || res.detail)) || 'launch refused');
                err.detail = (res && res.detail) || null;
                throw err;
            }
            if (this.appSession.app && this.appSession.app.id !== app.id) return;
            console.log('[Nuxel] native launched:', target, res.pid || '');
            // Native apps own a separate top-level Wayland surface, so the
            // launcher records the session without an iframe.
            this._setAppState('ACTIVE', app, null);
            if (this.sessions) this.sessions.register(app, null);
        }).catch((error) => {
            if (generation !== null && generation !== this.appGeneration) return;
            console.error('[Nuxel] native launch failed:', error);
            if (this.appSession.app && this.appSession.app.id !== app.id) return;
            this._setAppState('FAILED', app, null);
            const detail = error && (error.detail || error.message);
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = detail ? `${app.name}: ${detail}` : `Could not open ${app.name}`;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        });
    }

    _httpBridge(method, path, body, timeoutMs) {
        // Minimal, bounded client for the local HTTP bridge (dev mode on
        // 127.0.0.1). The launcher origin (http://127.0.0.1:8000) is on the
        // bridge's explicit CORS allowlist. Never a general-purpose proxy.
        // Native launches legitimately take several seconds: the bridge starts
        // a transient unit and waits for a real Wayland surface.  The old 8 s
        // ceiling reported a false "timeout" for VLC/Firefox while the app was
        // still mapping.
        return new Promise((resolve) => {
            const timeout = setTimeout(() => resolve({ success: false, error: 'timeout' }), timeoutMs || 8000);
            const options = { method: method, headers: { 'Content-Type': 'application/json' } };
            if (body) options.body = JSON.stringify(body);
            fetch('http://127.0.0.1:8080' + path, options)
                .then((r) => r.json().catch(() => ({})))
                .then((data) => { clearTimeout(timeout); resolve(data); })
                .catch((e) => { clearTimeout(timeout); resolve({ success: false, error: String(e) }); });
        });
    }

    _showUpdateNotification() {
        console.log('[Nuxel] New version available');
        // Show a toast or banner that a new version is available
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = 'Update available. <a href="#" onclick="location.reload()">Refresh</a>';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 10000);
    }

    _handleServiceWorkerMessage(data) {
        if (!data) return;
        
        switch (data.type) {
            case 'notification':
                this._handleNotification(data);
                break;
            case 'sync':
                console.log('[Nuxel] Background sync triggered');
                break;
            case 'push':
                console.log('[Nuxel] Push notification received:', data);
                break;
        }
    }

    _handleNotification(data) {
        console.log('[Nuxel] Notification:', data.title, data.body);
        // Could show in-app notification or update badge
    }

    _closeOverlays() {
        if (this.components.search) {
            this.components.search.close();
        }
        if (this.components.qs) {
            this.components.qs.close();
        }
        if (window.recents) window.recents.close('home');
        if (window.launcher) { window.launcher.closeDrawer(); window.launcher.exitEditMode(); }
        if (window.NuxelTouchKeyboard) window.NuxelTouchKeyboard.hide();
        document.querySelectorAll('.folder-sheet').forEach(el => el.remove());
        this._backgroundForegroundApp();
    }

    // A69-13: dismiss launcher chrome without touching the foreground app. This
    // is the launch-time counterpart of _closeOverlays(): close the Applications
    // drawer, search, recents, folder sheet and edit mode so the app surface the
    // launcher is about to create owns the foreground (and body[data-app-state]
    // hides the dock/drawer chrome once ACTIVE/LAUNCHING is set).
    _dismissLauncherChrome() {
        if (this.components.search) this.components.search.close();
        if (window.recents) window.recents.close('launch');
        if (window.launcher) { window.launcher.closeDrawer(); window.launcher.exitEditMode(); }
        document.querySelectorAll('.folder-sheet').forEach(el => el.remove());
    }

    // Public system-navigation contract.  Keep these methods on the Home
    // controller rather than making the button bar reach into individual app
    // iframes: Back/Home/Recents must work identically for every PWA.

    /* An app-declared Back state is the most precise source of truth.  Apps
       opt in with window.NuxelBack={canGoBack,back}; Calendar and Doom use it
       so a hidden editor/pause control can never be clicked by mistake. */
    _pwaExplicitBack(win) {
        try {
            const api = win && win.NuxelBack;
            if (!api || typeof api.canGoBack !== 'function') return null;
            const can = api.canGoBack() === true;
            if (!can) return 'root';
            if (typeof api.back !== 'function') return 'root';
            const handled = api.back();
            return handled === false ? 'root' : 'handled';
        } catch (e) { return null; }
    }

    /* Only a genuinely visible, enabled Back control counts.  The old
       querySelector() selected Calendar's hidden editor Back and Doom's hidden
       in-game MENU button, making a single Back appear to do nothing. */
    _visibleBackControl(doc) {
        try {
            const win = doc && doc.defaultView;
            const nodes = doc.querySelectorAll('[data-action="back"], [data-nav="back"], .settings-back');
            for (const el of nodes) {
                if (!el || el.disabled) continue;
                if (el.closest('[hidden], [aria-hidden="true"]')) continue;
                if (el.getAttribute('aria-hidden') === 'true') continue;
                const cs = win && win.getComputedStyle ? win.getComputedStyle(el) : null;
                if (cs && (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0)) continue;
                const rect = typeof el.getBoundingClientRect === 'function' ? el.getBoundingClientRect() : null;
                if (!rect || rect.width <= 0 || rect.height <= 0) continue;
                return el;
            }
        } catch (e) {}
        return null;
    }

    /* Same-document history entries are the real Back stack for a WebKit PWA.
       A bare history.length is monotonic (and therefore sticky after one Back),
       so track depth through pushState/replaceState and popstate instead. */
    _installPwaHistoryProbe(frame) {
        try {
            const win = frame && frame.contentWindow;
            const hist = win && win.history;
            if (!win || !hist || typeof hist.pushState !== 'function' || win.__nuxelHistoryProbe) return;
            win.__nuxelHistoryProbe = true;
            frame.__nuxelNavDepth = 0;
            const marker = state => (state && typeof state === 'object' && Number.isFinite(Number(state.__nuxelDepth)))
                ? Math.max(0, Number(state.__nuxelDepth)) : null;
            const withDepth = (state, depth) => (state && typeof state === 'object' && !Array.isArray(state))
                ? Object.assign({}, state, { __nuxelDepth: depth })
                : { __nuxelValue: state, __nuxelDepth: depth };
            try {
                hist.replaceState(withDepth(hist.state, 0), '', win.location.href);
            } catch (e) {}
            const push = hist.pushState;
            const replace = hist.replaceState;
            hist.pushState = function (state, title, url) {
                const depth = (frame.__nuxelNavDepth || 0) + 1;
                const result = push.call(hist, withDepth(state, depth), title, url);
                frame.__nuxelNavDepth = depth;
                return result;
            };
            hist.replaceState = function (state, title, url) {
                const depth = frame.__nuxelNavDepth || 0;
                return replace.call(hist, withDepth(state, depth), title, url);
            };
            win.addEventListener('popstate', event => {
                const depth = marker(event && event.state);
                if (depth !== null) frame.__nuxelNavDepth = depth;
                else if (frame.__nuxelBackPending) frame.__nuxelNavDepth = Math.max(0, (frame.__nuxelNavDepth || 0) - 1);
                frame.__nuxelBackPending = false;
            }, true);
        } catch (e) { /* cross-origin frames are deliberately not inspected */ }
    }

    _pwaBack(frame) {
        try {
            const win = frame && frame.contentWindow;
            const doc = frame && frame.contentDocument;
            if (!win || !doc) return 'root';
            this._installPwaHistoryProbe(frame);
            const explicit = this._pwaExplicitBack(win);
            if (explicit) return explicit;
            /* The Navigation API exposes a real canGoBack flag where WebKit
               provides it; it updates after Back, unlike history.length. */
            try {
                if (win.navigation && typeof win.navigation.canGoBack === 'boolean') {
                    if (win.navigation.canGoBack) { win.navigation.back(); return 'handled'; }
                }
            } catch (e) {}
            if ((frame.__nuxelNavDepth || 0) > 0) {
                frame.__nuxelBackPending = true;
                win.history.back();
                return 'handled';
            }
            const control = this._visibleBackControl(doc);
            if (control) { control.click(); return 'handled'; }
        } catch (e) { /* cross-origin iframe: no authority to read history */ }
        return 'root';
    }

    back() {
        if (this._isLocked()) return;
        // PWNAGE-80000 precedence: keyboard -> in-app Back -> graceful close.
        // A normal single Back never force-kills anything.
        if (this._keyboardVisible()) {
            this._inputTrace('back:keyboard-dismiss');
            this._dismissKeyboard();
            return;
        }
        if (this.components.search && this.components.search.isOpen) { this.components.search.close(); return; }
        if (this.components.qs && this.components.qs.isOpen) { this.components.qs.collapseOrClose(); return; }
        if (window.recents && window.recents.isOpen) { window.recents.close('back'); return; }
        const folder = document.querySelector('.folder-sheet'); if (folder) { folder.remove(); return; }
        if (window.launcher && window.launcher.drawerOpen) { window.launcher.closeDrawer(); return; }

        const frame = this.appSession.frame;
        if (frame && this.appSession.state === 'ACTIVE') {
            const target = this._pwaBack(frame);
            if (target === 'handled') {
                this._inputTrace('back:pwa-app-control');
                if (this._foregroundSurfaceVisible()) {
                    this._pwaBackStrikes = 0;
                } else {
                    this._pwaBackStrikes++;
                    if (this._pwaBackStrikes >= 2) {
                        this._pwaBackStrikes = 0;
                        this._backgroundForegroundApp();
                        this.home();
                        this._inputTrace('back:pwa-invisible-bounded-recovery');
                    }
                }
                return;
            }
            this._pwaBackStrikes = 0;
            this._inputTrace('back:pwa-at-root-graceful-close');
            this.gracefulCloseForeground('back-root');
            return;
        }
        if (!frame && this.appSession.app && this.appSession.state === 'ACTIVE' &&
            (this.appSession.app.type === 'native' || this.appSession.app.type === 'flatpak')) {
            if (this._backBusy) return;
            this._backBusy = true;
            this._inputTrace('back:native-request');
            this._httpBridge('POST', '/api/v1/apps/back', {
                app_id: 'org.nuxel.Home', source: 'short-back',
            }, 4000).then((res) => {
                this._backBusy = false;
                if (res && res.handled) { this._inputTrace('back:native-handled'); return; }
                if (res && res.at_root && res.foreground) {
                    this._inputTrace('back:native-at-root-graceful-close');
                    this.gracefulCloseForeground('back-native-root');
                    return;
                }
                this._inputTrace('back:native-no-foreground');
                this.home();
            }).catch(() => { this._backBusy = false; this.home(); });
            return;
        }
        this.home();
    }

    home() {
        if (this._isLocked()) return;
        // PWNAGE-43000: Home is a real navigation action, so the active IME
        // must be dismissed FIRST.  Merely hiding the Home overlay left an
        // invisible Stevia/DOM keyboard intercepting the next touch.  Blur the
        // focused control (which asks the compositor's text-input to close),
        // hide the DOM fallback, then continue the normal Home transition.
        this._dismissKeyboard();
        this._setNavDock(true);
        if (window.NuxelImmersive) window.NuxelImmersive.reset();
        try {
            this._closeOverlays();
        } catch (error) {
            this._inputTrace(`home:overlay-error ${error && error.message ? error.message : error}`);
        }
        try {
            // System Home always navigates to Desktop 1, never to the current
            // page.  It must work with no app, a loading app, a PWA iframe and
            // a native top-level app (Terminal) alike.
            if (window.launcher) window.launcher.mainDesktop();
            // Authoritative compositor-level Home: minimize any external native
            // toplevel (browser/camera/Firefox/…) WITHOUT killing it, then raise
            // the Home window. The pwa-host already closed the Terminal surface
            // on this path; this covers every other native window.
            this._httpBridge('POST', '/api/v1/apps/home', { app_id: 'org.nuxel.Home' });
            this._inputTrace(`home:complete state=${this.appSession.state} page=${window.launcher ? window.launcher.currentPage : '?'}`);
        } catch (error) {
            this._inputTrace(`home:error ${error && error.message ? error.message : error}`);
            console.error('[Nuxel] Home failed:', error);
        }
    }

    recentsToggle() {
        if (this._isLocked()) return;
        if (this.components.search && this.components.search.isOpen) this.components.search.close();
        if (this.components.qs && this.components.qs.isOpen) this.components.qs.close();
        if (window.launcher) { window.launcher.closeDrawer(); window.launcher.exitEditMode(); }
        if (window.recents) window.recents.toggle('system-nav');
    }

    _isLocked() { return !!(this.lockscreen && this.lockscreen.isLocked()); }

    /* The local LockScreen instance is a cache.  A WebKit reload/resume can
       leave it at locked while the root Bridge (the authority) has already
       accepted the unlock, which produced the false "unlock the phone first"
       refusal for native apps while Archive Manager still opened.  Reconcile
       once and retry the exact launch; a genuinely locked session stays
       blocked.  Never clears the gate without a success from the provider. */
    _reconcileLockThenRetry(retry) {
        if (this._lockReconcileInFlight) return true;
        const sec = window.NuxelSecurityLock;
        if (!sec || typeof sec.status !== 'function') return false;
        this._lockReconcileInFlight = true;
        Promise.resolve(sec.status()).then((st) => {
            this._lockReconcileInFlight = false;
            if (st && st.success !== false && st.locked === false) {
                this._inputTrace('launch:lock-authority-unlocked-stale-local');
                this._unlock('lock-authority-refresh');
                try { retry(); } catch (e) {}
            } else {
                this._inputTrace('launch:blocked-locked-confirmed');
            }
        }).catch(() => { this._lockReconcileInFlight = false; });
        return true;
    }

    _lock(reason) {
        this._inputTrace(`lock reason=${reason}`);
        // PWNAGE-52000 order is deliberate: hide every chrome layer (top bar,
        // DOM nav, Home content) AND unmap the native layer-shell dock BEFORE
        // the lockscreen surface is revealed.  CSS alone cannot hide the
        // native dock; z-index alone cannot prevent a one-frame flash.
        try {
            document.body.classList.add('lockscreen-active');
            document.documentElement.classList.add('nuxel-boot-locked');
        } catch (e) {}
        this._blurActiveField();
        if (window.NuxelTouchKeyboard) window.NuxelTouchKeyboard.hide();
        // Locking must suspend a foreground game/app.  The lockscreen is only
        // a visual overlay; leaving the app ACTIVE kept Doom's main loop and
        // WebKit's compositor running behind it.  Backgrounding preserves the
        // iframe/session so unlocking can resume the exact game state.
        try { this._backgroundForegroundApp(); } catch (e) {}
        this._setNavDock(false);
        if (this.lockscreen) this.lockscreen.show(reason);
        // Persist the authoritative locked state in the root bridge; the JS
        // overlay is only the presentation of that decision.
        try {
            if (window.NuxelSecurityLock && window.NuxelSecurityLock.lock) {
                window.NuxelSecurityLock.lock(reason || 'screen-lock');
            }
        } catch (e) { /* fail closed: the overlay remains */ }
        /* A lock always blanks the panel: idempotent for a display-off lock.
         * Ask for a full compositor/framebuffer frame as well, so a stale app
         * surface cannot leave a coloured band above the lockscreen. */
        const host = window.NuxelHost;
        if (host && host.available && typeof host.action === 'function') {
            Promise.resolve(host.action('force-redraw')).catch(() => {});
            Promise.resolve(host.action('screen-off')).catch(() => {});
        }
    }

    _unlock(reason) {
        const ls = this.lockscreen;
        this._inputTrace(`unlock reason=${reason || 'host'}`);
        if (!ls) return { ok: false, error: 'no-lockscreen' };
        if (!ls.isLocked()) return { ok: true, already: true, state: ls.state };
        ls.hide();
        try { document.documentElement.classList.remove('nuxel-boot-locked'); } catch (e) {}
        // Boot/unlock navigation contract: a successful unlock is an explicit
        // transition to the canonical Home desktop.  Hiding the overlay alone
        // revealed whatever route was underneath it (notably the Applications
        // drawer kept open before locking).  Do this synchronously with hide()
        // so there is no frame in which stale chrome can paint.
        this._enterHomeAfterUnlock(reason || 'unlock');
        // The native dock is restored only after authentication succeeded and
        // the Home surface has been requested.  One animation frame lets the
        // lockscreen removal commit before the layer-shell surface maps.
        const raf = window.requestAnimationFrame || ((fn) => setTimeout(fn, 0));
        raf(() => {
            this._setNavDock(true);
            try {
                const host = window.NuxelHost;
                if (host && host.available && typeof host.action === 'function') {
                    Promise.resolve(host.action('force-redraw')).catch(() => {});
                }
            } catch (e) {}
        });
        /* The system monitor pauses while the panel is locked or display-off.
           The boot-lock path never passed through a display ON transition, so
           its poll loop stayed stopped after unlock (a real startup race).
           Re-arm it here: the call is idempotent and a no-op when Home is not
           actually visible. */
        try {
            if (window.NuxelSystemMonitor && window.NuxelSystemMonitor.configure) window.NuxelSystemMonitor.configure();
        } catch (e) { /* a monitor misstep must never block unlock */ }
        /* A fresh unlocked session must not consume the stale OFF sample that
           caused the lock in the first place.  `null` means "unknown/armed":
           one OFF sample records the state but does not re-lock.  After the
           panel has been observed ON, the next real OFF transition locks. */
        this._lastDisplayOff = null;
        this._unlockGeneration = (this._unlockGeneration || 0) + 1;
        this._inputTrace(`unlock:complete gen=${this._unlockGeneration} locked=${ls.isLocked() ? 1 : 0} ` +
                         `visible=${ls.el && !ls.el.hidden ? 1 : 0}`);
        return { ok: true, state: 'UNLOCKED', generation: this._unlockGeneration };
    }

    /* Canonical post-unlock destination.  Kept separate from home() so the
       contract is testable and so a failed unlock can never call it. */
    _enterHomeAfterUnlock(reason) {
        this._inputTrace(`unlock:home reason=${reason}`);
        // The boot pose ends here, not before: portrait is held through the
        // lockscreen and the previously selected mode may rotate only now.
        this._releaseBootOrientation();
        // A stale #app=<id> is a route from before the lock; clear it so a
        // later hashchange/reload cannot reopen the Applications window.
        try {
            if (typeof history !== 'undefined' && history.replaceState && /(?:^#|&)app=/.test(location.hash || '')) {
                history.replaceState(null, '', location.pathname + location.search);
            }
        } catch (e) { /* history is best-effort; the explicit Home call is authoritative */ }
        try {
            this.home();
        } catch (error) {
            this._inputTrace(`unlock:home-error ${error && error.message ? error.message : error}`);
            console.error('[Nuxel] post-unlock Home failed:', error);
        }
    }

    /* The ONLY path from the penguin gesture into the authoritative lock state.
       The active lockscreen instance consumes a one-shot gesture id, then this
       controller asks the native host for its acknowledgement before hiding the
       overlay.  A rejected/missing backend leaves the session locked. */
    unlockFromLockscreen(instance, request) {
        const ls = this.lockscreen;
        if (!ls || ls !== instance) {
            return Promise.resolve({ ok: false, error: 'inactive-lockscreen' });
        }
        if (!ls.acceptGestureUnlock || !ls.acceptGestureUnlock(request)) {
            return Promise.resolve({ ok: false, error: 'invalid-or-replayed-gesture' });
        }
        const commit = () => {
            if (this.lockscreen !== ls) return { ok: false, error: 'lockscreen-changed' };
            if (!ls.isLocked()) {
                // The native host may already have released its own lock view.
                // The launcher still owns the visible Home transition.
                this._enterHomeAfterUnlock('penguin-host-event');
                return { ok: true, state: 'UNLOCKED', via: 'host-event' };
            }
            return this._unlock('penguin-gesture');
        };
        // Credential verification happens in the root Bridge before any
        // surface/nav transition.  A failure leaves the session locked.
        const verify = () => {
            if (window.NuxelSecurityLock && window.NuxelSecurityLock.verifyUnlock) {
                return Promise.resolve(window.NuxelSecurityLock.verifyUnlock());
            }
            return Promise.resolve({ ok: true, legacy: true });
        };
        const host = window.NuxelHost;
        if (host && host.available && typeof host.action === 'function') {
            return verify().then((v) => {
                if (!v || v.ok !== true) {
                    this._inputTrace(`unlock:credential-rejected ${(v && (v.error || v.detail)) || 'unknown'}`);
                    return v || { ok: false, error: 'credential-rejected' };
                }
                return Promise.resolve(host.action('unlock')).then((res) => {
                    if (!res || res.ok === false) {
                        this._inputTrace(`unlock:backend-rejected ${(res && (res.error || res.timeout)) || 'unknown'}`);
                        return { ok: false, error: 'backend-unlock-failed', backend: res || null };
                    }
                    return commit();
                });
            }).catch((err) => {
                this._inputTrace(`unlock:backend-error ${err && err.message ? err.message : err}`);
                return { ok: false, error: 'backend-unlock-error' };
            });
        }
        /* VM/desktop launcher: there is no native lock surface to release, so
           the launcher controller itself is authoritative after verification. */
        return verify().then((v) => (v && v.ok === true) ? commit() : v);
    }

    _initLockscreen() {
        if (window.NuxelLockscreen) this.lockscreen = new window.NuxelLockscreen();
        /* Boot lock: the inline HTML gate left #lockscreen visible in phone
           launch mode (?boot=os), so mark the session locked. */
        if (this.lockscreen && this.lockscreen.el && !this.lockscreen.el.hidden) {
            this.lockscreen.show('boot');
        }
        // The boot HTML gate is not authority.  If the root security provider
        // already reports unlocked (e.g. the session was resumed), hide the
        // stale local overlay so Back/Home/Tabs are not inert behind it.
        const sec = window.NuxelSecurityLock;
        if (sec && typeof sec.status === 'function') {
            Promise.resolve(sec.status()).then((st) => {
                if (st && st.success !== false && st.locked === false && this.lockscreen) {
                    this.lockscreen.hide();
                    try { document.documentElement.classList.remove('nuxel-boot-locked'); } catch (e) {}
                    this._setNavDock(true);
                    this._releaseBootOrientation();
                    this._inputTrace('lockscreen:boot-authority-unlocked');
                }
            }).catch(() => {});
        }
        this._inputTrace(`lockscreen-controller version=a45.1 device=${window.NuxelHost && window.NuxelHost.available ? 'phone' : 'local'}`);
        if (this._isLocked()) this._setNavDock(false);
        // Portrait is the boot pose.  This runs only while the lockscreen is
        // actually up; a warm launcher reload does not rotate a live session.
        const bootLocked = !!(document.documentElement &&
            document.documentElement.classList &&
            document.documentElement.classList.contains('nuxel-boot-locked'));
        if (this._isLocked() || bootLocked) {
            this._applyBootOrientation();
        }
        this._watchDisplayForLock();
        this._watchForegroundVisibility();
    }

    /* Boot orientation contract (v0.7.7-beta).
       The owner asked for Nuxel to ALWAYS come up in portrait, up to and
       including the lockscreen; only after a successful unlock may the saved
       orientation mode take over again.  The bridge is the one owner of the
       compositor transform, so this only asks it to apply portrait and later
       restores the exact mode that was selected before boot. */
    _applyBootOrientation() {
        if (this._bootOrientationActive) return Promise.resolve(false);
        this._bootOrientationActive = true;
        this._bootOrientationPrevious = null;
        const b = (typeof bridge !== 'undefined' && bridge && typeof bridge.call === 'function')
            ? bridge : null;
        if (!b) return Promise.resolve(false);
        let current = null;
        return Promise.resolve(b.call('orientation', 'get', {})).then((st) => {
            if (st && st.success !== false) {
                current = st.mode || (st.state && st.state.mode) || null;
                // The daemon may already have applied the cold-boot portrait
                // hold and recorded the owner's pre-boot mode.  Prefer that
                // record over the now-portrait current mode.
                const recorded = st.boot_previous_mode || null;
                if (recorded && recorded !== 'portrait') this._bootOrientationPrevious = recorded;
                else if (current && current !== 'portrait') this._bootOrientationPrevious = current;
            }
            return b.call('orientation', 'set', { mode: 'portrait' });
        }).then((res) => {
            const display = (res && (res.display || res.compositor)) || {};
            const applied = !!(res && (res.applied === true || display.applied === true));
            this._inputTrace('boot-orientation portrait applied=' + (applied ? 1 : 0));
            return applied;
        }).catch((e) => {
            this._inputTrace('boot-orientation error ' + (e && e.message ? e.message : e));
            return false;
        });
    }

    _releaseBootOrientation() {
        if (!this._bootOrientationActive) return Promise.resolve(false);
        this._bootOrientationActive = false;
        const previous = this._bootOrientationPrevious;
        this._bootOrientationPrevious = null;
        if (!previous || previous === 'portrait') return Promise.resolve(false);
        const b = (typeof bridge !== 'undefined' && bridge && typeof bridge.call === 'function')
            ? bridge : null;
        if (!b) return Promise.resolve(false);
        return Promise.resolve(b.call('orientation', 'set', { mode: previous }))
            .then((res) => {
                this._inputTrace('boot-orientation released mode=' + previous +
                    ' success=' + (res && res.success === true ? 1 : 0));
                return !!(res && res.success === true);
            })
            .catch((e) => {
                this._inputTrace('boot-orientation release-error ' +
                    (e && e.message ? e.message : e));
                return false;
            });
    }

    /* Re-lock when the display actually powers down (idle timeout or Power),
       so waking always shows the lockscreen.  The ON->OFF transition locks;
       an unknown/stale OFF sample never does. */
    _watchDisplayForLock() {
        this._lastDisplayOff = null;
        let watchTimer = null;
        const read = () => {
            const host = window.NuxelHost;
            if (!host || !host.available || typeof host.statusRead !== 'function') return;
            /* PWNAGE-85000: the wl-fb state document is authoritative again
               after the launcher resize re-entry fix.  Do not block this 5 s
               watcher on a bridge RPC that may not have a token yet; a stalled
               RPC would leave body.display-off unset and keep the 1 Hz
               lockscreen indicator poll running while the panel is blanked. */
            Promise.resolve(host.statusRead('wlfb-state')).then((r) => {
                const t = (r && (r.text || r.value)) || '';
                const off = /(^|[\s;])display=off([\s;]|$)/i.test(t) || /^DISPLAY_OFF\b/m.test(t);
                document.body.classList.toggle('display-off', off);
                document.body.dataset.displayOff = off ? '1' : '0';
                if (off) {
                    this._blurActiveField();
                    if (window.NuxelTouchKeyboard) window.NuxelTouchKeyboard.hide();
                    if (window.NuxelSystemMonitor && window.NuxelSystemMonitor.stop) window.NuxelSystemMonitor.stop();
                } else if (this._lastDisplayOff === true && window.NuxelSystemMonitor && window.NuxelSystemMonitor.configure) {
                    window.NuxelSystemMonitor.configure();
                }
                const woke = (this._lastDisplayOff === true && !off);
                if (woke) {
                    try {
                        document.dispatchEvent(new CustomEvent('nuxel:display-on'));
                        if (this.lockscreen && typeof this.lockscreen.refreshIndicators === 'function') {
                            this.lockscreen.refreshIndicators();
                        }
                        // PWNAGE-88000 zero-flash: re-assert the locked
                        // presentation and force a compositor repaint so the
                        // post-wake screencopy is the lockscreen, not the
                        // desktop.  Never show the lockscreen over an unlocked
                        // session; the security provider is authority.
                        if (this._isLocked() && this.lockscreen && typeof this.lockscreen.show === 'function') {
                            this.lockscreen.show('display-on');
                        }
                        const host = window.NuxelHost;
                        if (host && host.available && typeof host.action === 'function') {
                            Promise.resolve(host.action('force-redraw')).catch(() => {});
                        }
                    } catch (e) {}
                }
                if (this._lastDisplayOff === false && off && !this._isLocked()) this._lock('display-off');
                this._lastDisplayOff = off;
                /* Fast wake detection: while the panel is off, sample the
                   authoritative wl-fb state at 500 ms so the lockscreen is
                   asserted before nuxel-wl-fb unblanks; once on, relax back
                   to a 5 s background cadence. */
                if (watchTimer) clearInterval(watchTimer);
                watchTimer = setInterval(read, off ? 500 : 5000);
            }).catch(() => {});
        };
        read();
    }

    forward() {
        const frame = this.appSession.frame;
        try { if (frame && frame.contentWindow) frame.contentWindow.history.forward(); } catch (e) {}
    }

    stopLoading() {
        const frame = this.appSession.frame;
        try { if (frame && frame.contentWindow) frame.contentWindow.stop(); } catch (e) {}
    }

    reloadLauncher() {
        // One full compositor/framebuffer frame before the document reloads, so
        // a stale top band cannot survive the reload transition.
        try {
            const host = window.NuxelHost;
            if (host && host.available && typeof host.action === 'function') {
                Promise.resolve(host.action('force-redraw')).catch(() => {});
            }
        } catch (e) {}
        window.location.reload();
    }

    /* Graceful close: ask the app/compositor to close, bound the wait, and
     * leave a CLOSING state visible in Recents when it refuses.  This never
     * force-kills. */
    gracefulCloseForeground(reason) {
        const app = this.appSession.app;
        if (!app) { this.home(); return Promise.resolve(false); }
        return this.gracefulCloseApp(app.id, reason || 'back-root');
    }

    gracefulCloseApp(appId, reason) {
        const app = (this.appSession.app && this.appSession.app.id === appId)
            ? this.appSession.app : (appRegistry.getApp(appId) || { id: appId, name: appId });
        const isForeground = !!(this.appSession.app && this.appSession.app.id === appId &&
            ['ACTIVE', 'LAUNCHING', 'CLOSING'].indexOf(this.appSession.state) >= 0);
        const surface = this.appSurfaces.get(appId);
        const frame = isForeground ? this.appSession.frame : (surface && surface.frame) || null;
        const session = this.sessions && this.sessions.get(appId);
        if (session) session.state = 'closing';
        if (isForeground) this._setAppState('CLOSING', app, frame);
        this._dismissKeyboard();
        /* A background PWA is not a native app merely because appSession does
           not currently point at its iframe.  Classify by the app contract and
           keep the stored surface so Recents can tear the PWA down correctly. */
        const native = app.type === 'native' || app.type === 'flatpak' || (isForeground && !frame);
        this._inputTrace(`app:graceful-start id=${appId} native=${native ? 1 : 0} reason=${reason || 'close'}`);
        if (native) {
            const target = app.nativeAppId || app.id;
            const endpoint = isForeground ? '/api/v1/apps/close-foreground' : '/api/v1/apps/close';
            const payload = isForeground
                ? { app_id: 'org.nuxel.Home', source: reason || 'graceful-close' }
                : { app_id: target, source: reason || 'graceful-close' };
            return this._httpBridge('POST', endpoint, payload, 4000)
              .then(() => new Promise(resolve => setTimeout(resolve, 1200)))
              .then(() => this._httpBridge('GET', '/api/v1/windows/list', null, 3000))
              .then((list) => {
                const still = !!(list && Array.isArray(list.windows) && list.windows.some(w =>
                    w && !w.home && (w.app_id === target || w.app_id === app.id)));
                if (still) {
                    if (session) session.state = 'closing';
                    this._inputTrace(`app:graceful-timeout id=${appId} (swipe right to force-kill)`);
                    this._notifySessions();
                    return false;
                }
                this._finishGracefulClose(appId, reason);
                return true;
            }).catch(() => {
                if (session) session.state = 'closing';
                this._notifySessions();
                return false;
            });
        }
        // PWA: give the document one bounded turn to flush/cancel, then remove
        // the iframe.  There is no native process to leave hung in this case.
        try {
            if (frame && frame.contentWindow) {
                frame.contentWindow.postMessage({ type: 'nuxel:close-request' }, window.location.origin);
            }
        } catch (e) {}
        return new Promise(resolve => setTimeout(() => {
            this._finishGracefulClose(appId, reason);
            resolve(true);
        }, 250));
    }

    _finishGracefulClose(appId, reason) {
        if (this.appSession.app && this.appSession.app.id === appId) {
            this._closeAppSurface('graceful:' + (reason || 'close'));
            this.home();
        } else {
            if (this.sessions) this.sessions.close(appId);
            this._removeAppSurface(appId);
            this._notifySessions();
        }
    }

    _notifySessions() {
        try { document.dispatchEvent(new CustomEvent('nuxel:sessions-changed', { detail: this.sessions ? this.sessions.list() : [] })); } catch (e) {}
        try { if (window.recents && window.recents.isOpen && window.recents._render) window.recents._render(); } catch (e) {}
    }

    /* Force-kill is exactly the long-Back behaviour: release every keyboard,
     * focus, modal and compositor resource, then stop the app (never Home or a
     * daemon).  It is the explicit second-stage action in Recents. */
    forceKillForeground(reason) {
        const app = this.appSession.app;
        if (!app) return false;
        this._suppressBackUntil = Date.now() + 500;
        this._dismissKeyboard();
        const appId = app.id;
        const native = !this.appSession.frame || app.type === 'native' || app.type === 'flatpak';
        this._closeAppSurface('force:' + (reason || 'long-back'));
        if (native) {
            const target = app.nativeAppId || app.id;
            this._httpBridge('POST', '/api/v1/apps/force-close', {
                app_id: target, source: reason || 'long-back',
            }, 5000).catch(() => {});
        }
        this.home();
        this._inputTrace(`app:force-killed id=${appId} reason=${reason || 'long-back'}`);
        return true;
    }

    forceKillApp(appId, reason) {
        if (this.appSession.app && this.appSession.app.id === appId) return this.forceKillForeground(reason);
        const app = appRegistry.getApp(appId) || { id: appId };
        if (this.sessions) this.sessions.close(appId);
        this._removeAppSurface(appId);
        const target = app.nativeAppId || appId;
        this._httpBridge('POST', '/api/v1/apps/force-close', {
            app_id: target, source: reason || 'recents-force',
        }, 5000).catch(() => {});
        this._notifySessions();
        this._inputTrace(`app:force-killed-background id=${appId}`);
        return true;
    }

    terminateForeground() {
        return this.forceKillForeground('long-back');
    }

    /* Public chrome controls used by immersive.js.  A PWA can hide the native
       dock as well as the DOM fallback; desktop/VM runs simply have no host. */
    setNavVisible(visible) {
        if (!this.appSession.app) { this._setNavDock(true); return; }
        this._setNavDock(!!visible);
    }

    /* Requested by a same-origin foreground app (Nuxel Doom).  The app remains
       the owner of its own content; this only changes launcher chrome. */
    setImmersive(on) {
        if (window.NuxelImmersive) window.NuxelImmersive.setImmersive(!!on);
    }

    /* Public, non-destructive keyboard dismissal for apps that never use text
       input.  Doom calls this on start/focus so the system OSK cannot linger. */
    dismissKeyboard() {
        this._dismissKeyboard();
    }

    isLocked() {
        return this._isLocked();
    }

    _setNavDock(visible) {
        // Fail closed: never map the native dock while the lockscreen is
        // active, even if a caller passes true during a race.
        if (visible && this._isLocked()) return;
        const host = window.NuxelHost;
        if (!host || !host.available || typeof host.action !== 'function') return;
        try { Promise.resolve(host.action(visible ? 'nav-show' : 'nav-hide')).catch(() => {}); }
        catch (e) { /* the native dock FIFO may not exist yet; next lock retries */ }
    }

    _keyboardVisible() {
        if (this._nativeKeyboardVisible) return true;
        try { if (window.NuxelTouchKeyboard && window.NuxelTouchKeyboard.visible()) return true; } catch (e) {}
        if (document.body && document.body.classList && document.body.classList.contains('touch-keyboard-open')) return true;
        const field = this._activeEditable();
        return !!(field && this._keyboardLikelyOpen);
    }

    _activeEditable() {
        let doc = document;
        for (let depth = 0; depth < 3; depth++) {
            const active = doc.activeElement;
            if (!active) return null;
            const tag = String(active.tagName || '').toUpperCase();
            if (tag === 'IFRAME') {
                try { doc = active.contentDocument; continue; } catch (e) { return null; }
            }
            if (active.isContentEditable) return active;
            if (tag === 'TEXTAREA') return active;
            if (tag === 'INPUT' && !/^(button|checkbox|radio|submit|reset|file|range|color)$/i.test(String(active.type || 'text'))) return active;
            return null;
        }
        return null;
    }

    _blurActiveField() {
        try {
            const field = this._activeEditable();
            if (field && typeof field.blur === 'function') field.blur();
            const sel = window.getSelection && window.getSelection();
            if (sel && sel.removeAllRanges) sel.removeAllRanges();
        } catch (e) { /* losing focus is best-effort and must never break lock */ }
    }

    _dismissKeyboard() {
        // Preserve the typed value: blur only, never clear the field.  This is
        // intentionally synchronous so Home cannot raise the desktop in the
        // same frame as an still-focused input surface.
        try { this._blurActiveField(); } catch (e) {}
        try {
            const active = document.activeElement;
            if (active && active !== document.body && typeof active.blur === 'function') active.blur();
        } catch (e) {}
        try {
            if (window.NuxelTouchKeyboard && typeof window.NuxelTouchKeyboard.hide === 'function') {
                window.NuxelTouchKeyboard.hide();
            }
        } catch (e) {}
        this._keyboardLikelyOpen = false;
        this._nativeKeyboardVisible = false;
        // A PWA/Home keyboard is closed by the blur above.  Only a native
        // top-level app needs the compositor focus bounce, and that helper now
        // restores the same app instead of raising Home over it.
        try {
            const app = this.appSession.app;
            const nativeForeground = !!(app && !this.appSession.frame &&
                (app.type === 'native' || app.type === 'flatpak'));
            const host = window.NuxelHost;
            if (nativeForeground && host && host.available && typeof host.action === 'function') {
                Promise.resolve(host.action('hide-keyboard')).catch(() => {});
            }
        } catch (e) {}
        try { window.dispatchEvent(new CustomEvent('nuxel:dismiss-keyboard')); } catch (e) {}
    }

    openHomeSettings() {
        this._closeOverlays();
        if (window.NuxelHomeSettings) window.NuxelHomeSettings.open();
    }
}

// The offline regression harness instantiates this class without a browser.
try { window.NuxelHome = NuxelHome; } catch (e) { /* non-window test context */ }

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.nuxel = new NuxelHome();
    // Same-origin app iframes (Settings, Cleanup, DevMgmt, Nuxtore, Root
    // Control) call this to return Home.  It did not exist anywhere, so their
    // own Close buttons fell through and did nothing (A34 owner test).
    window.NuxelLauncherClose = () => {
        if (window.nuxel) window.nuxel._closeOverlays();
    };
});
