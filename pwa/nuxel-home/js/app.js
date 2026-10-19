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
                    if (kind === 'touchmove' && Date.now() - lastMove < 100) return;
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
        if (!app || !frame) return;
        const surface = this.appSurfaces.get(app.id);
        if (surface) {
            [surface.frame, surface.bar, surface.status].forEach(el => {
                if (el) el.hidden = true;
            });
        }
        this._setAppState('BACKGROUND', app, frame);
        if (this.sessions && app) this.sessions.home();
    }

    _resumeApp(app) {
        const surface = app && this.appSurfaces.get(app.id);
        if (!surface) return false;
        if (this.appSession.app && this.appSession.app.id !== app.id) this._backgroundForegroundApp();
        [surface.frame, surface.bar, surface.status].forEach(el => {
            if (el) el.hidden = false;
        });
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
            // Close search if open
            if (this.components.search) {
                this.components.search.close();
            }
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
            if (action === 'home') this._closeOverlays();
            else if (action === 'back') this.back();
            else if (action === 'forward') this.forward();
            else if (action === 'stop') this.stopLoading();
            else if (action === 'reload-launcher') this.reloadLauncher();
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
            top: calc(var(--status-bar-height, 36px) + 56px) !important;
            left: 0 !important;
            right: 0 !important;
            width: 100vw !important;
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
            this._setAppState('ACTIVE', app, frame);
            this._observeAppFrame(frame, app);
        }, { once: true });
        frame.addEventListener('error', () => {
            if (this.appSession.frame !== frame) return;
            status.textContent = `${app.name} could not load. Close it to return Home.`;
            this._setAppState('FAILED', app, frame);
        }, { once: true });

        // Keep navigation below the camera/status area and outside app content.
        // A floating upper-right glyph covered Calendar's Save button and the
        // S10+ cutout. The status bar remains reachable for Quick Settings.
        const appBar = document.createElement('div');
        appBar.className = 'pwa-app-bar';
        const closeBtn = document.createElement('button');
        closeBtn.className = 'pwa-close-btn';
        closeBtn.textContent = 'Home';
        closeBtn.setAttribute('aria-label', `Close ${app.name} and return Home`);
        closeBtn.onclick = () => this._backgroundForegroundApp();
        appBar.appendChild(closeBtn);
        const appTitle = document.createElement('span');
        appTitle.textContent = app.name;
        appBar.appendChild(appTitle);
        document.body.appendChild(appBar);
        this.appSurfaces.set(app.id, { frame, bar: appBar, status });
        if (this.sessions) this.sessions.register(app, this.appSurfaces.get(app.id));
    }

    _launchNative(app, url) {
        console.warn(`Native app not implemented yet: ${app.name} (${url})`);

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = `${app.name} native app is not implemented yet`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
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
        if (window.recents) window.recents.close();
        if (window.launcher) { window.launcher.closeDrawer(); window.launcher.exitEditMode(); }
        document.querySelectorAll('.folder-sheet').forEach(el => el.remove());
        this._backgroundForegroundApp();
    }

    // Public system-navigation contract.  Keep these methods on the Home
    // controller rather than making the button bar reach into individual app
    // iframes: Back/Home/Recents must work identically for every PWA.
    back() {
        if (this.components.search && this.components.search.isOpen) { this.components.search.close(); return; }
        if (this.components.qs && this.components.qs.isOpen) { this.components.qs.collapseOrClose(); return; }
        if (window.recents && window.recents.isOpen) { window.recents.close(); return; }
        const folder = document.querySelector('.folder-sheet'); if (folder) { folder.remove(); return; }
        if (window.launcher && window.launcher.drawerOpen) { window.launcher.closeDrawer(); return; }
        if (window.NuxelTouchKeyboard && window.NuxelTouchKeyboard.visible()) { window.NuxelTouchKeyboard.hide(); return; }
        this._backgroundForegroundApp();
    }

    home() { this._closeOverlays(); }

    recentsToggle() {
        if (this.components.search && this.components.search.isOpen) this.components.search.close();
        if (this.components.qs && this.components.qs.isOpen) this.components.qs.close();
        if (window.launcher) { window.launcher.closeDrawer(); window.launcher.exitEditMode(); }
        if (window.recents) window.recents.toggle();
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
        if (this.appSession.app) this._closeAppSurface();
    }

    openHomeSettings() {
        this._closeOverlays();
        if (window.NuxelHomeSettings) window.NuxelHomeSettings.open();
    }
}

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
