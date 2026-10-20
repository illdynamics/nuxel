// Nuxel Home - Recent Apps View
// Manages the recent apps carousel/overview

class RecentsManager {
    constructor() {
        this.view = document.getElementById('recents-view');
        this.list = document.getElementById('recents-list');
        this.isOpen = false;
        this.lastTransition = null;
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

    _render() {
        const sessions = window.nuxel && window.nuxel.sessions;
        const recentApps = sessions ? sessions.list().map(s => Object.assign({}, appRegistry.getApp(s.appId), { session: s })) : appRegistry.getRecentApps();
        
        if (recentApps.length === 0) {
            this.list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🕐</div>
                    <h3>No Recent Apps</h3>
                    <p>Apps you open will appear here for quick switching</p>
                </div>
            `;
            return;
        }

        this.list.innerHTML = recentApps.map(app => `
            <div class="recents-card press-effect" data-app-id="${app.id}" data-session-id="${app.session ? app.session.sessionId : ''}">
                <div class="recents-preview" style="background: ${app.color}22">
                    <span class="recent-app-icon">${window.NuxelAppIcon ? window.NuxelAppIcon(app) : app.icon}</span>
                </div>
                <div class="recents-label">
                    <span>${app.name}</span>
                    <button type="button" class="recents-close" aria-label="Close ${app.name}">Close</button>
                </div>
            </div>
        `).join('');

        // Bind clicks
        this.list.querySelectorAll('.recents-card').forEach(card => {
            let startX = 0;
            card.addEventListener('pointerdown', e => { startX = e.clientX; });
            card.addEventListener('pointerup', e => {
                if (Math.abs(e.clientX - startX) > 72) { this._closeCard(card.dataset.appId); return; }
                if (e.target.closest('.recents-close')) { this._closeCard(card.dataset.appId); return; }
                const appId = card.dataset.appId;
                this.close('select-app');
                if (!(window.nuxel && window.nuxel._resumeApp(appRegistry.getApp(appId)))) appRegistry.launchApp(appId);
            });
        });
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
