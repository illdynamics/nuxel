// Nuxel Home — App Launcher v0.1.1
// Drag-and-drop reorder, persistent order, tap-to-launch

class Launcher {
    constructor() {
        this.appList = document.getElementById('app-list');
        this.dockItems = document.getElementById('dock-items');
        this.searchOverlay = document.getElementById('search-overlay');

        this.currentPage = 0;
        this.appsPerPage = 16;
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

    _saveOrder() {
        const docked = appRegistry.getDockedApps().map(a => a.id);
        const ordered = appRegistry.getAllApps()
            .filter(a => !docked.includes(a.id))
            .map(a => a.id);
        localStorage.setItem('nuxel.appOrder', JSON.stringify(ordered));
    }

    _getOrderedApps() {
        const all = appRegistry.getAllApps();
        const docked = new Set(appRegistry.getDockedApps().map(a => a.id));
        const gridApps = all.filter(a => !docked.has(a.id));

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
        this.appOrder = null;
        this._renderAll();
    }

    // ── Render ──────────────────────────────────────────────────────

    _renderAll() {
        this._renderDock();
        this._renderAppGrid();
    }

    _renderDock() {
        if (!this.dockItems) return;
        const docked = appRegistry.getDockedApps();
        this.dockItems.innerHTML = docked.map((app, i) =>
            '<div class="app-item press-effect" data-app-id="' + app.id + '" data-index="' + i + '" tabindex="0" role="button" aria-label="' + app.name + '"><div class="app-icon app-category-' + app.category + '" style="background: ' + app.color + '33; color: ' + app.color + '"><span>' + app.icon + '</span></div></div>'
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
            '<div class="app-item" data-app-id="' + app.id + '" tabindex="0" role="button" aria-label="' + app.name + '" title="' + (app.description || '') + '"><div class="app-icon app-category-' + app.category + '" style="background: ' + app.color + '33; color: ' + app.color + '"><span>' + app.icon + '</span></div><span class="app-label">' + app.name + '</span></div>'
        ).join('');

        this._updatePageDots(totalPages);
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
        // Swipe for page change
        document.addEventListener('touchstart', (e) => this._onTouchStart(e), { passive: true });
        document.addEventListener('touchend', (e) => this._onTouchEnd(e), { passive: true });
    }

    _onPointerDown(e) {
        const item = e.target.closest('.app-item');
        if (!item) return;
        if (item.closest('#dock-items')) return; // No drag on dock

        this.dragTarget = item;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        this.dragStartTime = Date.now();
        this.hasMoved = false;

        // Long-press to start drag
        clearTimeout(this.longPressTimer);
        this.longPressTimer = setTimeout(() => {
            this._startDrag(item, e);
        }, 500);
    }

    _onPointerMove(e) {
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
        clearTimeout(this.longPressTimer);

        if (this.isDragging) {
            this._endDrag(e);
            return;
        }

        // Normal tap/click → launch app
        if (!this.hasMoved && this.dragTarget) {
            const appId = this.dragTarget.dataset.appId;
            if (appId) appRegistry.launchApp(appId);
        }

        this.dragTarget = null;
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
