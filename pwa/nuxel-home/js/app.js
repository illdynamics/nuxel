// Nuxel Home - Main Application Controller
// Coordinates all components and handles global events

class NuxelHome {
    constructor() {
        this.initialized = false;
        this.components = {};
        this._init();
    }

    async _init() {
        console.log('[Nuxel] Initializing Nuxel Home...');

        // Register service worker
        await this._registerServiceWorker();

        // Initialize all components
        this.components = {
            bridge: bridge,
            statusBar: window.statusBar,
            launcher: window.launcher,
            search: window.search || null,
            recents: null,
            qs: null,
        };

        // Request phone status capability
        await this._requestCoreCapabilities();

        // Bind global events
        this._bindGlobalEvents();

        this.initialized = true;
        console.log('[Nuxel] Nuxel Home initialized');

        // Boot animation splash: fade out once the app is ready (see below)
        this._finishBootSplash();
    }

    _finishBootSplash() {
        // The nuxel-boot-animation.mp4 plays as a fullscreen splash while the
        // app boots. Fade it out once the app is initialized AND the animation
        // has had a chance to play (full playthrough or ~3s minimum), so the
        // animation is actually seen without delaying the UI. Safety timeout
        // guarantees the splash can never outlive 12s.
        const hide = () => document.body.classList.add('ready');
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

        // Remove any previous app frame.
        document.querySelectorAll('.pwa-frame, .pwa-close-btn').forEach(el => el.remove());

        const frame = document.createElement('iframe');
        frame.src = url;
        frame.className = 'pwa-frame';
        frame.setAttribute('title', app.name);
        frame.style.cssText = `
            position: fixed !important;
            inset: 0 !important;
            width: 100vw !important;
            height: 100dvh !important;
            min-width: 100vw !important;
            min-height: 100dvh !important;
            border: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            z-index: 9999 !important;
            background: #071426 !important;
            display: block !important;
        `;
        document.body.appendChild(frame);

        const closeBtn = document.createElement('button');
        closeBtn.className = 'pwa-close-btn';
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `
            position: fixed !important;
            top: 12px !important;
            right: 12px !important;
            z-index: 10000 !important;
            background: rgba(0,0,0,0.65) !important;
            color: white !important;
            border: none !important;
            border-radius: 50% !important;
            width: 44px !important;
            height: 44px !important;
            font-size: 24px !important;
            cursor: pointer !important;
        `;
        closeBtn.onclick = () => {
            frame.remove();
            closeBtn.remove();
        };
        document.body.appendChild(closeBtn);
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
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.nuxel = new NuxelHome();
});
