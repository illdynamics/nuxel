// Nuxel Home — App Launcher v0.1.1
// Drag-and-drop reorder, persistent order, tap-to-launch

class Launcher {
    constructor() {
        this.appList = document.getElementById('app-list');
        this.dockItems = document.getElementById('dock-items');
        this.searchOverlay = document.getElementById('search-overlay');

        this.currentPage = 0;
        this.appsPerPage = 20;
        this.settings = { gridColumns: 4, gridRows: 5, dockColumns: 5 };
        this.hiddenAppIds = new Set();
        this.appSizes = {};
        this.editMode = false;
        this.selectedAppId = null;
        this.isDragging = false;
        this.dragData = null;
        this.dragGhost = null;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.dragStartTime = 0;
        this.longPressTimer = null;
        this.hasMoved = false;

        this._init();
    }

    _init() {
        this._loadOrder();
        this._loadLayout();
        this._applyLayout();
        this._renderAll();
        this._bindPointerEvents();
    }

    // ── Persistence ────────────────────────────────────────────────

    _loadOrder() {
        try {
            const saved = localStorage.getItem('nuxel.appOrder');
            if (saved) {
                this.appOrder = JSON.parse(saved);
                if (!Array.isArray(this.appOrder)) this.appOrder = null;
            }
        } catch (e) {
            this.appOrder = null;
        }
    }

    _loadLayout() {
        try {
            const saved = JSON.parse(localStorage.getItem('nuxel.launcherLayout') || '{}');
            this.settings = Object.assign(this.settings, saved.settings || {});
            this.hiddenAppIds = new Set(Array.isArray(saved.hiddenAppIds) ? saved.hiddenAppIds : []);
            this.appSizes = saved.appSizes && typeof saved.appSizes === 'object' ? saved.appSizes : {};
        } catch (e) { /* first launch or an old, invalid layout */ }
    }

    _saveLayout() {
        try {
            localStorage.setItem('nuxel.launcherLayout', JSON.stringify({
                settings: this.settings,
                hiddenAppIds: Array.from(this.hiddenAppIds),
                appSizes: this.appSizes,
            }));
        } catch (e) { console.warn('Could not save launcher layout:', e); }
    }

    _applyLayout() {
        const clamp = (value, low, high, fallback) => {
            value = Number(value);
            return Number.isInteger(value) && value >= low && value <= high ? value : fallback;
        };
        this.settings.gridColumns = clamp(this.settings.gridColumns, 3, 6, 4);
        this.settings.gridRows = clamp(this.settings.gridRows, 4, 7, 5);
        this.settings.dockColumns = clamp(this.settings.dockColumns, 3, 6, 5);
        this.appsPerPage = this.settings.gridColumns * this.settings.gridRows;
        document.documentElement.style.setProperty('--home-columns', this.settings.gridColumns);
        document.documentElement.style.setProperty('--dock-columns', this.settings.dockColumns);
    }

    updateHomeSettings(next) {
        this.settings = Object.assign(this.settings, next || {});
        this._applyLayout();
        this._saveLayout();
        this._renderAll();
    }

    _saveOrder() {
        const visible = Array.from(this.appList ? this.appList.children : []).map(el => el.dataset.appId).filter(Boolean);
        const current = (this.appOrder || this._getOrderedApps().map(a => a.id)).filter(id => !visible.includes(id));
        this.appOrder = visible.concat(current);
        try { localStorage.setItem('nuxel.appOrder', JSON.stringify(this.appOrder)); } catch (e) {}
    }

    _getOrderedApps() {
        const all = appRegistry.getAllApps();
        const docked = new Set(appRegistry.getDockedApps().map(a => a.id));
        const gridApps = all.filter(a => !docked.has(a.id) && !this.hiddenAppIds.has(a.id));

        if (this.appOrder && this.appOrder.length) {
            const orderMap = new Map();
            this.appOrder.forEach((id, i) => orderMap.set(id, i));
            const ordered = gridApps.filter(a => orderMap.has(a.id))
                .sort((a, b) => orderMap.get(a.id) - orderMap.get(b.id));
            const newApps = gridApps.filter(a => !orderMap.has(a.id));
            return ordered.concat(newApps);
        }
        return gridApps;
    }

    resetOrder() {
        localStorage.removeItem('nuxel.appOrder');
        localStorage.removeItem('nuxel.launcherLayout');
        this.appOrder = null;
        this.hiddenAppIds.clear();
        this.appSizes = {};
        this.settings = { gridColumns: 4, gridRows: 5, dockColumns: 5 };
        this._applyLayout();
        this._renderAll();
    }

    // ── Render ──────────────────────────────────────────────────────

    _renderAll() {
        this._renderDock();
        this._renderAppGrid();
    }

    _renderDock() {
        if (!this.dockItems) return;
        const docked = appRegistry.getDockedApps().filter(app => !this.hiddenAppIds.has(app.id));
        this.dockItems.innerHTML = docked.map((app, i) =>
            '<div class="app-item press-effect" data-app-id="' + app.id + '" data-index="' + i + '" tabindex="0" role="button" aria-label="' + app.name + '"><div class="app-icon app-category-' + app.category + '" style="background: ' + app.color + '33; color: ' + app.color + '">' + this._appIcon(app) + '</div></div>'
        ).join('');
    }

    _renderAppGrid() {
        if (!this.appList) return;
        const gridApps = this._getOrderedApps();
        const totalPages = Math.max(1, Math.ceil(gridApps.length / this.appsPerPage));
        if (this.currentPage >= totalPages) this.currentPage = totalPages - 1;
        const start = this.currentPage * this.appsPerPage;
        const page = gridApps.slice(start, start + this.appsPerPage);

        this.appList.innerHTML = page.map(app =>
            '<div class="app-item" data-size="' + (this.appSizes[app.id] || 'normal') + '" data-app-id="' + app.id + '" tabindex="0" role="button" aria-label="' + app.name + '" title="' + (app.description || '') + '"><div class="app-icon app-category-' + app.category + '" style="background: ' + app.color + '33; color: ' + app.color + '">' + this._appIcon(app) + '</div><span class="app-label">' + app.name + '</span></div>'
        ).join('');

        this._updatePageDots(totalPages);
    }

    _appIcon(app) {
        if (window.NuxelAppIcon) return window.NuxelAppIcon(app);
        return '<span>' + app.icon + '</span>';
    }

    _updatePageDots(total) {
        const el = document.querySelector('.app-grid-indicator');
        if (!el) return;
        let html = '';
        for (let i = 0; i < total; i++) {
            html += '<span class="dot' + (i === this.currentPage ? ' active' : '') + '"></span>';
        }
        el.innerHTML = html;
    }

    // ── Pointer Events (mouse + touch, unified) ────────────────────

    _bindPointerEvents() {
        document.addEventListener('pointerdown', (e) => this._onPointerDown(e));
        document.addEventListener('pointermove', (e) => this._onPointerMove(e));
        document.addEventListener('pointerup', (e) => this._onPointerUp(e));
        document.addEventListener('pointercancel', () => this._cancelPointer());
        document.addEventListener('keydown', (e) => {
            const item = e.target.closest && e.target.closest('.app-item');
            if (item && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault();
                appRegistry.launchApp(item.dataset.appId);
            }
        });
        // Older engines/accessibility tools may deliver only click. Pointer
        // taps already activate on release, so their compatibility click is
        // never a second launch.
        document.addEventListener('click', (e) => {
            if (window.PointerEvent || Date.now() < (this.suppressClickUntil || 0)) return;
            const item = e.target.closest && e.target.closest('.app-item');
            if (item) appRegistry.launchApp(item.dataset.appId);
        });
        // Swipe for page change
        document.addEventListener('touchstart', (e) => this._onTouchStart(e), { passive: true });
        document.addEventListener('touchend', (e) => this._onTouchEnd(e), { passive: true });
    }

    _onPointerDown(e) {
        if (e.isPrimary === false || (e.button !== undefined && e.button !== 0)) {
            this._cancelPointer();
            return;
        }
        this._cancelPointer();
        const item = e.target.closest && e.target.closest('.app-item');
        if (!item) return;

        this.dragTarget = item;
        this.pressedPointer = e.pointerId;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        this.dragStartTime = Date.now();
        this.hasMoved = false;

        // Dock items still activate on release; long press selects them for
        // removal but does not turn the fixed dock into a surprise reordering UI.
        if (item.closest('#dock-items')) {
            this.longPressTimer = setTimeout(() => this._enterEditMode(item.dataset.appId), 450);
            return;
        }
        // Long-press to start drag
        clearTimeout(this.longPressTimer);
        this.longPressTimer = setTimeout(() => {
            this._enterEditMode(item.dataset.appId);
            this._startDrag(item, e);
        }, 450);
    }

    _onPointerMove(e) {
        if (this.pressedPointer !== e.pointerId) return;
        if (!this.isDragging) {
            // Check if moved beyond threshold before long-press fires
            if (this.dragTarget && !this.hasMoved) {
                const dx = Math.abs(e.clientX - this.dragStartX);
                const dy = Math.abs(e.clientY - this.dragStartY);
                if (dx > 8 || dy > 8) {
                    this.hasMoved = true;
                    clearTimeout(this.longPressTimer);
                }
            }
            return;
        }

        e.preventDefault();
        this._updateDrag(e);
    }

    _onPointerUp(e) {
        if (this.pressedPointer !== e.pointerId || e.isPrimary === false) return;
        clearTimeout(this.longPressTimer);

        if (this.isDragging) {
            this._endDrag(e);
            this.dragTarget = null;
            this.pressedPointer = null;
            this.suppressClickUntil = Date.now() + 500;
            return;
        }

        // Normal tap either chooses an icon to edit or launches it.
        const released = e.target.closest && e.target.closest('.app-item');
        if (!this.hasMoved && this.dragTarget && released === this.dragTarget) {
            const appId = this.dragTarget.dataset.appId;
            if (appId && this.editMode) this._selectForEdit(appId);
            else if (appId) appRegistry.launchApp(appId);
        }

        this.dragTarget = null;
        this.pressedPointer = null;
        this.hasMoved = false;
    }

    _cancelPointer() {
        clearTimeout(this.longPressTimer);
        if (this.isDragging) this._endDrag();
        this.dragTarget = null;
        this.pressedPointer = null;
        this.hasMoved = false;
    }

    // ── Drag mechanics ──────────────────────────────────────────────

    _startDrag(item, e) {
        this.isDragging = true;
        this.dragData = { id: item.dataset.appId, el: item };
        item.classList.add('dragging');
        document.body.classList.add('launcher-dragging');

        // Create ghost
        this.dragGhost = item.cloneNode(true);
        this.dragGhost.classList.add('drag-ghost');
        this.dragGhost.style.position = 'fixed';
        this.dragGhost.style.zIndex = '99999';
        this.dragGhost.style.pointerEvents = 'none';
        this.dragGhost.style.opacity = '0.85';
        this.dragGhost.style.transform = 'scale(1.1)';
        this.dragGhost.style.left = (e.clientX - 32) + 'px';
        this.dragGhost.style.top = (e.clientY - 32) + 'px';
        document.body.appendChild(this.dragGhost);

        // Hide original
        item.style.opacity = '0.3';
    }

    _updateDrag(e) {
        if (!this.dragGhost) return;
        this.dragGhost.style.left = (e.clientX - 32) + 'px';
        this.dragGhost.style.top = (e.clientY - 32) + 'px';

        // Find target under pointer
        this.dragGhost.style.display = 'none';
        const under = document.elementFromPoint(e.clientX, e.clientY);
        this.dragGhost.style.display = '';

        const targetItem = under ? under.closest('.app-item') : null;
        if (targetItem && targetItem !== this.dragData.el && targetItem.closest('#app-list')) {
            this._swapWithTarget(targetItem);
        }
    }

    _swapWithTarget(target) {
        const parent = this.dragData.el.parentNode;
        const children = Array.from(parent.children);
        const fromIdx = children.indexOf(this.dragData.el);
        const toIdx = children.indexOf(target);
        if (fromIdx < 0 || toIdx < 0 || fromIdx === toIdx) return;

        // Animate swap
        target.style.transition = 'transform 0.15s ease';
        target.style.transform = fromIdx < toIdx ? 'translateX(-72px)' : 'translateX(72px)';
        setTimeout(() => {
            target.style.transform = '';
            target.style.transition = '';
        }, 150);

        if (fromIdx < toIdx) {
            parent.insertBefore(this.dragData.el, target.nextSibling);
        } else {
            parent.insertBefore(this.dragData.el, target);
        }

        // Rebuild data-index attributes
        Array.from(parent.children).forEach((c, i) => c.dataset.index = i);
    }

    _endDrag(e) {
        this.isDragging = false;

        if (this.dragData && this.dragData.el) {
            this.dragData.el.style.opacity = '';
            this.dragData.el.classList.remove('dragging');
        }
        if (this.dragGhost) {
            this.dragGhost.remove();
            this.dragGhost = null;
        }

        document.body.classList.remove('launcher-dragging');
        document.querySelectorAll('.app-item').forEach(el => el.classList.remove('drag-over'));

        this._saveOrder();
        this.dragData = null;
    }

    _enterEditMode(appId) {
        this.editMode = true;
        document.body.classList.add('launcher-editing');
        this._selectForEdit(appId);
        if (window.NuxelHost && window.NuxelHost.available) window.NuxelHost.action('haptics-long');
    }

    _selectForEdit(appId) {
        this.selectedAppId = appId;
        document.querySelectorAll('.app-item').forEach(item => item.classList.toggle('selected-for-edit', item.dataset.appId === appId));
        this._renderEditToolbar();
    }

    _renderEditToolbar() {
        let bar = document.getElementById('launcher-edit-toolbar');
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'launcher-edit-toolbar';
            bar.className = 'launcher-edit-toolbar';
            document.body.appendChild(bar);
        }
        bar.innerHTML = '<button type="button" data-edit="size">Resize</button><button type="button" class="danger" data-edit="remove">Remove</button><button type="button" data-edit="settings">Home settings</button><button type="button" data-edit="done">Done</button>';
        bar.querySelector('[data-edit="size"]').onclick = () => this.toggleSelectedSize();
        bar.querySelector('[data-edit="remove"]').onclick = () => this.removeSelected();
        bar.querySelector('[data-edit="settings"]').onclick = () => window.NuxelHomeSettings && window.NuxelHomeSettings.open();
        bar.querySelector('[data-edit="done"]').onclick = () => this.exitEditMode();
    }

    toggleSelectedSize() {
        if (!this.selectedAppId) return;
        this.appSizes[this.selectedAppId] = this.appSizes[this.selectedAppId] === 'large' ? 'normal' : 'large';
        this._saveLayout(); this._renderAll(); this._selectForEdit(this.selectedAppId);
    }

    removeSelected() {
        if (!this.selectedAppId) return;
        this.hiddenAppIds.add(this.selectedAppId);
        this.appSizes[this.selectedAppId] = 'normal';
        this.selectedAppId = null;
        this._saveLayout(); this._renderAll();
        const next = this.appList && this.appList.querySelector('.app-item');
        if (next) this._selectForEdit(next.dataset.appId); else this.exitEditMode();
    }

    restoreHiddenApps() {
        this.hiddenAppIds.clear();
        this._saveLayout();
        this._renderAll();
    }

    exitEditMode() {
        this.editMode = false; this.selectedAppId = null;
        document.body.classList.remove('launcher-editing');
        const bar = document.getElementById('launcher-edit-toolbar');
        if (bar) bar.remove();
    }

    // ── Swipe navigation ────────────────────────────────────────────

    _onTouchStart(e) {
        if (this.isDragging) return;
        this.swipeStartX = e.changedTouches[0].screenX;
    }

    _onTouchEnd(e) {
        if (this.isDragging) return;
        const diff = this.swipeStartX - e.changedTouches[0].screenX;
        if (Math.abs(diff) < 50) return;
        const total = Math.ceil(this._getOrderedApps().length / this.appsPerPage);
        if (diff > 0 && this.currentPage < total - 1) {
            this.currentPage++;
            this._renderAppGrid();
        } else if (diff < 0 && this.currentPage > 0) {
            this.currentPage--;
            this._renderAppGrid();
        }
    }

    refresh() {
        this._renderAll();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.launcher = new Launcher();
});
