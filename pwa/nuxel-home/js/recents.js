// Nuxel Home - Recent Apps View
// Manages the recent apps carousel/overview

class RecentsManager {
    constructor() {
        this.view = document.getElementById('recents-view');
        this.list = document.getElementById('recents-list');
        this.isOpen = false;
        this.lastTransition = null;
        this._native = [];
        this._nativeLoading = false;
        this._init();
    }

    _init() {
        this._bindEvents();
    }

    _bindEvents() {
        // Listen for recents gesture (swipe up from bottom)
        document.addEventListener('gesture:recents', () => this.toggle());
    }

    _transition(state, reason) {
        this.lastTransition = { state, reason: reason || 'unspecified', at: Date.now() };
        document.dispatchEvent(new CustomEvent('recents:state', { detail: this.lastTransition }));
        try {
            const diag = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.nuxelDiag;
            if (diag) diag.postMessage(`RECENTS state=${state} reason=${this.lastTransition.reason} ts=${this.lastTransition.at}`);
        } catch (e) { /* diagnostics never control visibility */ }
    }

    open(reason) {
        if (this.isOpen) return;
        this.isOpen = true;
        this._loadNative();
        this._render();
        this.view.classList.remove('hidden');
        this._transition('OPEN', reason || 'explicit-open');
        requestAnimationFrame(() => this.view.classList.add('visible'));
    }

    close(reason) {
        if (!this.isOpen) return;
        this.isOpen = false;
        this.view.classList.remove('visible');
        this.view.classList.add('hidden');
        this._transition('CLOSED', reason || 'explicit-close');
    }

    toggle(reason) {
        if (this.isOpen) this.close(reason || 'toggle-close');
        else this.open(reason || 'toggle-open');
    }

    _nativeId(win) {
        const id = String((win && win.app_id) || '');
        if (id === 'vlc') return 'org.videolan.VLC';
        if (id === 'org.mozilla.firefox') return 'org.mozilla.firefox';
        if (id === 'org.gnome.Nautilus' || id === 'file-roller') return 'org.gnome.FileRoller';
        return id || ('native:' + String((win && win.title) || 'window'));
    }

    _loadNative() {
        if (this._nativeLoading) return;
        this._nativeLoading = true;
        fetch('http://127.0.0.1:8080/api/v1/windows/list', { cache: 'no-store' })
            .then(r => r.json())
            .then(doc => {
                this._native = (doc && Array.isArray(doc.windows) ? doc.windows : [])
                    .filter(w => w && !w.home && w.app_id && w.app_id !== 'nuxel-pwa-host');
            })
            .catch(() => { this._native = []; })
            .then(() => { this._nativeLoading = false; if (this.isOpen) this._render(); });
    }

    _render() {
        const sessions = window.nuxel && window.nuxel.sessions;
        const recentApps = sessions ? sessions.list().map(s => Object.assign({}, appRegistry.getApp(s.appId), { session: s })) : appRegistry.getRecentApps();
        const nativeSeen = new Set(recentApps.map(a => a && a.id));
        const nativeApps = this._native.map((w, i) => {
            const id = this._nativeId(w);
            if (nativeSeen.has(id)) return null;
            nativeSeen.add(id);
            const reg = appRegistry.getApp(id) || {};
            return Object.assign({}, reg, {
                id: id,
                name: reg.name || w.title || w.app_id || ('Window ' + (i + 1)),
                icon: reg.icon || '🪟',
                color: reg.color || '#3b82f6',
                nativeWindow: w,
            });
        }).filter(Boolean);
        recentApps.push(...nativeApps);
        
        if (recentApps.length === 0) {
            this.list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🕐</div>
                    <h3>No Open Tabs</h3>
                    <p>Apps you open appear here. Swipe a card left or press Close to force-close it.</p>
                </div>
            `;
            return;
        }

        this.list.innerHTML = recentApps.map(app => `
            <div class="recents-card press-effect" data-app-id="${app.id}" data-native="${app.nativeWindow ? '1' : '0'}" data-session-id="${app.session ? app.session.sessionId : ''}">
                <div class="recents-preview" style="background: ${app.color}22">
                    <span class="recent-app-icon">${window.NuxelAppIcon ? window.NuxelAppIcon(app) : app.icon}</span>
                </div>
                <div class="recents-label">
                    <span>${app.name}</span>
                    <button type="button" class="recents-close" aria-label="Close ${app.name}" title="Close ${app.name}">Close</button>
                </div>
            </div>
        `).join('');

        // Bind clicks
        this.list.querySelectorAll('.recents-card').forEach(card => {
            let startX = 0;
            card.addEventListener('pointerdown', e => { startX = e.clientX; });
            card.addEventListener('pointerup', e => {
                const appId = card.dataset.appId;
                const isNative = card.dataset.native === '1';
                const closedByButton = !!e.target.closest('.recents-close');
                // Owner gesture: swipe LEFT to force-close the tab.  A right
                // swipe is not a close and must not destroy an app by accident.
                const swipedLeft = e.clientX < startX - 72;
                if (closedByButton || swipedLeft) {
                    if (isNative) this._closeNative(appId);
                    else this._closeCard(appId);
                    return;
                }
                if (isNative) {
                    const win = this._native.find(w => this._nativeId(w) === appId);
                    this.close('select-native');
                    if (win) fetch('http://127.0.0.1:8080/api/v1/windows/activate', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ app_id: win.app_id })
                    }).then(() => setTimeout(() => window.NuxelHost && window.NuxelHost.action && window.NuxelHost.action('nav-show'), 80)).catch(() => {});
                    return;
                }
                this.close('select-app');
                if (!(window.nuxel && window.nuxel._resumeApp(appRegistry.getApp(appId)))) appRegistry.launchApp(appId);
            });
        });
    }

    _closeNative(appId) {
        const win = this._native.find(w => this._nativeId(w) === appId);
        const target = (win && win.app_id) || appId;
        fetch('http://127.0.0.1:8080/api/v1/windows/close', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ app_id: target })
        }).catch(() => {});
        this._native = this._native.filter(w => this._nativeId(w) !== appId);
        this._render();
        this._transition('OPEN', 'dismiss-native-card');
    }

    _closeCard(appId) {
        if (window.nuxel && window.nuxel.sessions) window.nuxel.sessions.close(appId);
        if (window.nuxel && window.nuxel.appSession.app && window.nuxel.appSession.app.id === appId) window.nuxel._closeAppSurface();
        this._render();
        this._transition('OPEN', 'dismiss-card');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.recents = new RecentsManager();
});
