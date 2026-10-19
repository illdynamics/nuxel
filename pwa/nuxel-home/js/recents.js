// Nuxel Home - Recent Apps View
// Manages the recent apps carousel/overview

class RecentsManager {
    constructor() {
        this.view = document.getElementById('recents-view');
        this.list = document.getElementById('recents-list');
        this.isOpen = false;
        this._init();
    }

    _init() {
        this._bindEvents();
    }

    _bindEvents() {
        // Listen for recents gesture (swipe up from bottom)
        document.addEventListener('gesture:recents', () => this.toggle());
    }

    open() {
        if (this.isOpen) return;
        this.isOpen = true;
        this._render();
        this.view.classList.remove('hidden');
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;
        this.view.classList.add('hidden');
    }

    toggle() {
        if (this.isOpen) this.close();
        else this.open();
    }

    _render() {
        const recentApps = appRegistry.getRecentApps();
        
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
            <div class="recents-card press-effect" data-app-id="${app.id}">
                <div class="recents-preview" style="background: ${app.color}22">
                    <span class="recent-app-icon">${window.NuxelAppIcon ? window.NuxelAppIcon(app) : app.icon}</span>
                </div>
                <div class="recents-label">
                    <span>${app.name}</span>
                    <span style="float: right; font-size: 12px; color: var(--text-secondary)">
                        ${app.type === 'native' ? 'System' : 'App'}
                    </span>
                </div>
            </div>
        `).join('');

        // Bind clicks
        this.list.querySelectorAll('.recents-card').forEach(card => {
            card.addEventListener('click', () => {
                const appId = card.dataset.appId;
                this.close();
                appRegistry.launchApp(appId);
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.recents = new RecentsManager();
});
