// Nuxel Home - Main Application Controller
// Coordinates all components and handles global events

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
            doc.__nuxelObserved = true;
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

    _removeAppSurface() {
        const { app, frame } = this.appSession;
        if (frame && frame.releasePointerCapture) {
            try {
                const captures = frame.__nuxelPointerCaptures || [];
                captures.forEach(id => frame.releasePointerCapture(id));
            } catch (e) { /* the frame may already have been detached */ }
        }
        const surface = app && this.appSurfaces.get(app.id);
        if (surface) {
            [surface.frame, surface.bar, surface.status].forEach(el => { if (el) el.remove(); });
            this.appSurfaces.delete(app.id);
        }
        try {
            if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
        } catch (e) { /* a torn-down WebKit frame may no longer expose activeElement */ }
    }

    _closeAppSurface() {
        this.appGeneration++;
        if (this.appSession.app && this.appSession.app.id === 'org.nuxel.Terminal' &&
            !this.appSession.frame && window.NuxelHost && window.NuxelHost.available) {
            Promise.resolve(window.NuxelHost.action('close-terminal')).catch(error => {
                console.error('[Nuxel] Terminal close failed:', error);
            });
        }
        if (this.appSession.state !== 'CLOSED') this._setAppState('CLOSING');
        this._removeAppSurface();
        this._setAppState('CLOSED', null, null);
    }

    _backgroundForegroundApp() {
        const { app, frame } = this.appSession;
        if (!app || this.appSession.state === 'CLOSED') return false;
        // A native application owns a separate top-level Wayland surface, not a
        // DOM iframe.  Returning early here (the pre-A45 behaviour) left the
        // Terminal window in front of Home: the penguin/Home tap ran, the
        // launcher repainted underneath it, and the glass did not change.
        // Close that surface through the host's narrow, typed action instead.
        if (!frame) {
            this._closeAppSurface();
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
        return true;
    }

    _resumeApp(app) {
        const surface = app && this.appSurfaces.get(app.id);
        if (!surface) return false;
        if (this.appSession.app && this.appSession.app.id !== app.id) this._backgroundForegroundApp();
        [surface.frame, surface.bar, surface.status].forEach(el => {
            if (el) el.hidden = false;
        });
        if (surface.frame) {
            surface.frame.__nuxelBackgrounded = false;
            if (typeof surface.frame.removeAttribute === 'function') surface.frame.removeAttribute('data-nuxel-backgrounded');
            this._observeAppFrame(surface.frame, app);
        }
        this._setAppState('ACTIVE', app, surface.frame);
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

        // Bind global events
        this._bindGlobalEvents();

        // A45 Penguin lockscreen + boot lock + display-off re-lock.
        this._initLockscreen();

        this.initialized = true;
        console.log('[Nuxel] Nuxel Home initialized');

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
                if (this._isLocked()) { this._unlock(); return; }
                // A45 pwa-host bug: the native nav dock's long-press Back
                // ("back-long") is dispatched as "unlock" (its js_action map
                // never added a back-long entry).  A session that is already
                // unlocked can only receive that misrouted long-press, so honour
                // the owner's real intent: terminate ONLY the foreground app.
                this.terminateForeground();
                return;
            }
            if (this._isLocked()) return;   // locked: navigation/app actions are inert
            if (action === 'home') this.home();
            else if (action === 'back') this.back();
            else if (action === 'back-long' || action === 'terminate') this.terminateForeground();
            else if (action === 'forward') this.forward();
            else if (action === 'stop') this.stopLoading();
            else if (action === 'reload-launcher') this.reloadLauncher();
            else if (action === 'recents') this.recentsToggle();
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

    _openPwa(app, url) {
        console.log(`Opening PWA: ${app.name} at ${url}`);
        // A deep link, manifest shortcut or late startup callback must never
        // build an app surface over the lockscreen.  The user can launch it
        // again after the boot unlock, which always lands on Home.
        if (this._isLocked()) {
            this._inputTrace(`launch:blocked-locked app=${app.id}`);
            return;
        }
        this._dismissLauncherChrome();
        if (this._resumeApp(app)) return;
        this._backgroundForegroundApp();
        const generation = this.appGeneration;
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
            if (frame.__nuxelBackgrounded || this.appSession.state === 'BACKGROUND') {
                // Home was pressed while this document was loading.  Keep it
                // hidden; Recents can still resume the completed session.
                this._observeAppFrame(frame, app);
                return;
            }
            this._setAppState('ACTIVE', app, frame);
            this._observeAppFrame(frame, app);
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
            return;
        }
        this._dismissLauncherChrome();
        // Native applications are fullscreen top-level Wayland clients; the
        // layer-shell nav dock is what keeps Back/Home/Recents (and the top
        // status bar in the Home surface) available over them.
        this._setNavDock(true);
        const target = app.nativeAppId || app.id;
        this._setAppState('LAUNCHING', app, null);

        // Installed state check for apps that may not be present (e.g. Snapshot).
        if (app.installed === false) {
            this._setAppState('FAILED', app, null);
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = `${app.name} is not installed on this device`;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
            return;
        }

        // The authoritative launch authority is the HTTP bridge's CLOSED-verb
        // /apps/exec endpoint: it resolves the target from its fixed allowlist /
        // canonical registry and never executes a client-supplied path.
        this._httpBridge('POST', '/api/v1/apps/exec', {
            target: target,
            app_id: 'org.nuxel.Home',
            source: 'launcher',
        }).then((res) => {
            if (!res || res.success !== true) {
                const err = new Error((res && (res.error || res.detail)) || 'launch refused');
                err.detail = (res && res.detail) || null;
                throw err;
            }
            console.log('[Nuxel] native launched:', target, res.pid || '');
            // Native apps own a separate top-level Wayland surface, so the
            // launcher records the session without an iframe.
            this._setAppState('ACTIVE', app, null);
            if (this.sessions) this.sessions.register(app, null);
        }).catch((error) => {
            console.error('[Nuxel] native launch failed:', error);
            this._setAppState('FAILED', app, null);
            const detail = error && (error.detail || error.message);
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = detail ? `${app.name}: ${detail}` : `Could not open ${app.name}`;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        });
    }

    _httpBridge(method, path, body) {
        // Minimal, bounded client for the local HTTP bridge (dev mode on
        // 127.0.0.1). The launcher origin (http://127.0.0.1:8000) is on the
        // bridge's explicit CORS allowlist. Never a general-purpose proxy.
        return new Promise((resolve) => {
            const timeout = setTimeout(() => resolve({ success: false, error: 'timeout' }), 8000);
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
    back() {
        if (this._isLocked()) return;
        if (this.components.search && this.components.search.isOpen) { this.components.search.close(); return; }
        if (this.components.qs && this.components.qs.isOpen) { this.components.qs.collapseOrClose(); return; }
        if (window.recents && window.recents.isOpen) { window.recents.close('back'); return; }
        const folder = document.querySelector('.folder-sheet'); if (folder) { folder.remove(); return; }
        if (window.launcher && window.launcher.drawerOpen) { window.launcher.closeDrawer(); return; }
        if (window.NuxelTouchKeyboard && window.NuxelTouchKeyboard.visible()) { window.NuxelTouchKeyboard.hide(); return; }
        // The working keyboard is the compositor's Stevia OSK, not the DOM
        // fallback.  Back must first remove text-input focus, which asks the
        // compositor to hide its keyboard while preserving the typed value.
        if (window.NuxelTouchKeyboard && window.NuxelTouchKeyboard.nativeProvider) {
            const field = this._activeEditable();
            if (field) { this._blurActiveField(); return; }
        }
        const frame = this.appSession.frame;
        if (frame && this.appSession.state === 'ACTIVE') {
            // Same-origin PWAs use their own browser history.  Track the
            // baseline history length when the app surface first loads, so a
            // just-opened app (or one that has returned to its root) minimises
            // to Home instead of navigating back to about:blank or a stale
            // in-app entry and appearing to stay foreground while the dock
            // paints over it.
            try {
                const win = frame.contentWindow;
                const hist = win && win.history;
                if (hist) {
                    if (typeof frame.__nuxelNavBase !== 'number') {
                        frame.__nuxelNavBase = hist.length;
                    }
                    if (hist.length > frame.__nuxelNavBase) {
                        frame.__nuxelNavBase = hist.length - 1;
                        hist.back();
                        return;
                    }
                }
                const doc = frame.contentDocument;
                const back = doc && doc.querySelector('[data-action="back"], [data-nav="back"], .settings-back');
                if (back) { back.click(); return; }
            } catch (err) { /* cross-origin iframe: no authority to read history */ }
        }
        // Native apps own a separate top-level Wayland surface (browser,
        // camera, ...): Back must first navigate that app's own history before
        // it may background to Home.  The bridge drives the foreground native
        // app's back contract and reports whether it was handled or at root.
        if (!frame && this.appSession.app && this.appSession.state === 'ACTIVE' &&
            this.appSession.app.type === 'native') {
            if (this._backBusy) return;
            this._backBusy = true;
            this._inputTrace('back:native-request');
            this._httpBridge('POST', '/api/v1/apps/back', {
                app_id: 'org.nuxel.Home', source: 'short-back',
            }).then((res) => {
                this._backBusy = false;
                if (res && res.handled) {
                    this._inputTrace('back:native-handled');
                    return;   // app stays foreground, unobscured
                }
                this._inputTrace('back:native-at-root');
                this.home();
            });
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

    _lock(reason) {
        this._inputTrace(`lock reason=${reason}`);
        if (this.lockscreen) this.lockscreen.show(reason);
        this._blurActiveField();
        if (window.NuxelTouchKeyboard) window.NuxelTouchKeyboard.hide();
        this._setNavDock(false);
        /* A lock always blanks the panel: idempotent for a display-off lock. */
        const host = window.NuxelHost;
        if (host && host.available && typeof host.action === 'function') {
            Promise.resolve(host.action('screen-off')).catch(() => {});
        }
    }

    _unlock(reason) {
        const ls = this.lockscreen;
        this._inputTrace(`unlock reason=${reason || 'host'}`);
        if (!ls) return { ok: false, error: 'no-lockscreen' };
        if (!ls.isLocked()) return { ok: true, already: true, state: ls.state };
        ls.hide();
        this._setNavDock(true);
        // Boot/unlock navigation contract: a successful unlock is an explicit
        // transition to the canonical Home desktop.  Hiding the overlay alone
        // revealed whatever route was underneath it (notably the Applications
        // drawer kept open before locking).  Do this synchronously with hide()
        // so there is no frame in which stale chrome can paint.
        this._enterHomeAfterUnlock(reason || 'unlock');
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
        const host = window.NuxelHost;
        if (host && host.available && typeof host.action === 'function') {
            return Promise.resolve(host.action('unlock')).then((res) => {
                if (!res || res.ok === false) {
                    this._inputTrace(`unlock:backend-rejected ${(res && (res.error || res.timeout)) || 'unknown'}`);
                    return { ok: false, error: 'backend-unlock-failed', backend: res || null };
                }
                return commit();
            }).catch((err) => {
                this._inputTrace(`unlock:backend-error ${err && err.message ? err.message : err}`);
                return { ok: false, error: 'backend-unlock-error' };
            });
        }
        /* VM/desktop launcher: there is no native lock surface to release, so
           the launcher controller itself is authoritative. */
        return Promise.resolve(commit());
    }

    _initLockscreen() {
        if (window.NuxelLockscreen) this.lockscreen = new window.NuxelLockscreen();
        /* Boot lock: the inline HTML gate left #lockscreen visible in phone
           launch mode (?boot=os), so mark the session locked. */
        if (this.lockscreen && this.lockscreen.el && !this.lockscreen.el.hidden) {
            this.lockscreen.show('boot');
        }
        this._inputTrace(`lockscreen-controller version=a45.1 device=${window.NuxelHost && window.NuxelHost.available ? 'phone' : 'local'}`);
        if (this._isLocked()) this._setNavDock(false);
        this._watchDisplayForLock();
    }

    /* Re-lock when the display actually powers down (idle timeout or Power),
       so waking always shows the lockscreen.  The ON->OFF transition locks;
       an unknown/stale OFF sample never does. */
    _watchDisplayForLock() {
        this._lastDisplayOff = null;
        const read = () => {
            const host = window.NuxelHost;
            if (!host || !host.available || typeof host.statusRead !== 'function') return;
            Promise.resolve(host.statusRead('wlfb-state')).then((r) => {
                const t = (r && (r.text || r.value)) || '';
                /* The running bridge publishes `display=off` in its frame
                   status line; older display-state documents used DISPLAY_OFF.
                   Accept both so an idle/power screen-off always re-locks. */
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
                /* A wake is an event, not a reason to wait for the next poll.
                   Dispatch it ONLY on an actual OFF -> ON transition: the old
                   unconditional dispatch every 2 s re-ran battery, touch and
                   status reads forever while the display was already on. */
                const woke = (this._lastDisplayOff === true && !off);
                if (woke) {
                    try {
                        document.dispatchEvent(new CustomEvent('nuxel:display-on'));
                        if (this.lockscreen && typeof this.lockscreen.refreshIndicators === 'function') {
                            this.lockscreen.refreshIndicators();
                        }
                    } catch (e) {}
                }
                if (this._lastDisplayOff === false && off && !this._isLocked()) this._lock('display-off');
                this._lastDisplayOff = off;
            }).catch(() => {});
        };
        read();
        setInterval(read, 2000);
    }

    forward() {
        const frame = this.appSession.frame;
        try { if (frame && frame.contentWindow) frame.contentWindow.history.forward(); } catch (e) {}
    }

    stopLoading() {
        const frame = this.appSession.frame;
        try { if (frame && frame.contentWindow) frame.contentWindow.stop(); } catch (e) {}
    }

    reloadLauncher() { window.location.reload(); }

    terminateForeground() {
        // The launcher is never a session, so a held Back can only terminate a
        // foreground app.  On Home this intentionally does nothing.
        const app = this.appSession.app;
        this._suppressBackUntil = Date.now() + 500;
        if (!app) return;
        if (window.NuxelTouchKeyboard) window.NuxelTouchKeyboard.hide();
        if (this.sessions) this.sessions.close(app.id);
        // A native app owns a separate top-level Wayland surface (browser,
        // camera, ...): clearing the DOM session does not close that surface.
        // Route the close through the compositor's fixed verb, which closes
        // ONLY the activated non-Home toplevel and never kills Home/daemons.
        if (!this.appSession.frame) {
            this._httpBridge('POST', '/api/v1/apps/close-foreground', {
                app_id: 'org.nuxel.Home', source: 'long-back',
            });
        }
        this._closeAppSurface();
        this.home();
    }

    _setNavDock(visible) {
        const host = window.NuxelHost;
        if (!host || !host.available || typeof host.action !== 'function') return;
        try { Promise.resolve(host.action(visible ? 'nav-show' : 'nav-hide')).catch(() => {}); }
        catch (e) { /* the native dock FIFO may not exist yet; next lock retries */ }
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
        // The compositor keyboard belongs to whichever client owns text-input
        // focus.  Ask the trusted host to raise Home/minimize the native app,
        // which makes phoc send text-input leave to the app and closes Stevia.
        try {
            const host = window.NuxelHost;
            if (host && host.available && typeof host.action === 'function') {
                Promise.resolve(host.action('dismiss-keyboard')).catch(() => {});
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
