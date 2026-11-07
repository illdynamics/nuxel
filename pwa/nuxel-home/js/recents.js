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
        document.addEventListener('nuxel:sessions-changed', () => { if (this.isOpen) this._render(); });
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
                    <p>Apps you open appear here. Swipe left to close gracefully; swipe right to force-kill a hung app.</p>
                </div>
            `;
            return;
        }

        this.list.innerHTML = recentApps.map(app => {
            const closing = !!(app.session && app.session.state === 'closing');
            return `
            <div id="recents-card-${app.id}" class="recents-card press-effect${closing ? ' closing' : ''}" data-app-id="${app.id}" data-native="${app.nativeWindow ? '1' : '0'}" data-session-id="${app.session ? app.session.sessionId : ''}">
                <div class="recents-preview" style="background: ${app.color}22">
                    <span class="recent-app-icon">${window.NuxelAppIcon ? window.NuxelAppIcon(app) : app.icon}</span>
                </div>
                <div class="recents-label">
                    <span>${app.name}${closing ? ' · closing…' : ''}</span>
                    <button type="button" class="recents-close" aria-label="Close ${app.name}" title="Close ${app.name} gracefully">Close</button>
                </div>
            </div>`;
        }).join('');

        // Bind gestures.  Scope is deliberately the card only: the drawer and
        // every other horizontal app gesture keep their existing meaning.
        this.list.querySelectorAll('.recents-card').forEach(card => {
            let startX = 0, startY = 0, active = false;
            const resetSwipe = () => {
                card.classList.remove('swiping');
                card.style.transform = '';
                card.style.opacity = '';
            };
            card.addEventListener('pointerdown', e => {
                if (e.button !== undefined && e.button !== 0) return;
                if (e.target.closest('.recents-close')) return;
                active = true;
                startX = e.clientX; startY = e.clientY;
                try { card.setPointerCapture && card.setPointerCapture(e.pointerId); } catch (err) {}
            });
            card.addEventListener('pointermove', e => {
                if (!active) return;
                const dx = e.clientX - startX, dy = e.clientY - startY;
                if (Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(dy)) {
                    card.classList.add('swiping');
                    card.style.transform = 'translateX(' + Math.max(-90, Math.min(90, dx * 0.45)) + 'px)';
                    card.style.opacity = String(Math.max(0.55, 1 - Math.abs(dx) / 320));
                }
            });
            const finish = (e) => {
                if (!active) return;
                active = false;
                const dx = e.clientX - startX, dy = e.clientY - startY;
                resetSwipe();
                const appId = card.dataset.appId;
                const isNative = card.dataset.native === '1';
                const horizontal = Math.abs(dx) > 72 && Math.abs(dx) > Math.abs(dy) * 1.2;
                if (horizontal && dx < 0) {
                    // Swipe LEFT = graceful close / stop, bounded grace.
                    this._graceful(appId, 'recents-swipe-left');
                    return;
                }
                if (horizontal && dx > 0) {
                    // Swipe RIGHT = explicit force-kill (same as long Back).
                    this._force(appId, 'recents-swipe-right');
                    return;
                }
                if (e.target.closest('.recents-close')) {
                    this._graceful(appId, 'recents-close-button');
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
            };
            card.addEventListener('pointerup', finish);
            card.addEventListener('pointercancel', () => { active = false; resetSwipe(); });
            card.addEventListener('lostpointercapture', () => { if (active) { active = false; resetSwipe(); } });
            const closeBtn = card.querySelector('.recents-close');
            if (closeBtn) closeBtn.addEventListener('click', (ev) => {
                ev.preventDefault(); ev.stopPropagation();
                this._graceful(card.dataset.appId, 'recents-close-button');
            });
        });
    }

    _graceful(appId, reason) {
        const n = window.nuxel;
        if (!n) return;
        const isNative = (this._native || []).some(w => this._nativeId(w) === appId);
        if (isNative && n.appSession && n.appSession.app && n.appSession.app.id !== appId) {
            // A background native card: ask the exact toplevel to close, then
            // remove the card only after the backend accepted the request.
            const win = this._native.find(w => this._nativeId(w) === appId);
            const target = (win && win.app_id) || appId;
            fetch('http://127.0.0.1:8080/api/v1/windows/close', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app_id: target })
            }).then(r => r.json().catch(() => ({}))).then(res => {
                /* The card is retired only after the compositor backend
                   accepted the close request.  A refused close stays visible
                   in the CLOSING state so the owner can force-kill it. */
                if (!res || res.success === false) {
                    const session = window.nuxel && window.nuxel.sessions && window.nuxel.sessions.get(appId);
                    if (session) session.state = 'closing';
                    try { n._inputTrace('recents:graceful-native-refused id=' + appId); } catch (e) {}
                    if (this.isOpen) this._render();
                    return;
                }
                const session = window.nuxel && window.nuxel.sessions && window.nuxel.sessions.get(appId);
                if (session) session.state = 'closing';
                this._native = this._native.filter(w => this._nativeId(w) !== appId);
                setTimeout(() => { if (this.isOpen) this._render(); }, 900);
            }).catch(() => {
                const session = window.nuxel && window.nuxel.sessions && window.nuxel.sessions.get(appId);
                if (session) session.state = 'closing';
                if (this.isOpen) this._render();
            });
            return;
        }
        Promise.resolve(n.gracefulCloseApp(appId, reason)).then(() => { if (this.isOpen) this._render(); });
    }

    _force(appId, reason) {
        const n = window.nuxel;
        if (!n) return;
        this._native = (this._native || []).filter(w => this._nativeId(w) !== appId);
        n.forceKillApp(appId, reason || 'recents-force');
        if (this.isOpen) this._render();
    }

    _closeNative(appId) { this._graceful(appId, 'dismiss-native-card'); }
    _closeCard(appId) { this._graceful(appId, 'dismiss-card'); }
}

document.addEventListener('DOMContentLoaded', () => {
    window.recents = new RecentsManager();
});
