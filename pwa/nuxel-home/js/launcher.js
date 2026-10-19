// Nuxel Home — App Launcher v0.1.1
// Drag-and-drop reorder, persistent order, tap-to-launch

class Launcher {
    constructor() {
        this.appList = document.getElementById('app-list');
        this.dockItems = document.getElementById('dock-items');
        this.searchOverlay = document.getElementById('search-overlay');

        this.currentPage = 0;
        this.appsPerPage = 20;
        this.settings = { gridColumns: 4, gridRows: 5, dockColumns: 4, desktopCount: 2, homeLocked: false };
        this.hiddenAppIds = new Set();
        this.appSizes = {};
        this.layout = null;
        this.folderHover = null;
        this.drawerOpen = false;
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
        this.pageAssignments = {};
        try {
            const saved = JSON.parse(localStorage.getItem('nuxel.launcherLayout') || '{}');
            this.settings = Object.assign(this.settings, saved.settings || {});
            this.hiddenAppIds = new Set(Array.isArray(saved.hiddenAppIds) ? saved.hiddenAppIds : []);
            this.appSizes = saved.appSizes && typeof saved.appSizes === 'object' ? saved.appSizes : {};
            this.savedEntries = saved.entries || null;
            this.pageAssignments = saved.pageAssignments && typeof saved.pageAssignments === 'object' ? saved.pageAssignments : {};
        } catch (e) { /* first launch or an old, invalid layout */ }
    }

    _saveLayout() {
        try {
            localStorage.setItem('nuxel.launcherLayout', JSON.stringify({
                settings: this.settings,
                hiddenAppIds: Array.from(this.hiddenAppIds),
                appSizes: this.appSizes,
                entries: this.layout ? this.layout.snapshot().entries : this.savedEntries,
                pageAssignments: this.pageAssignments,
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
        this.settings.dockColumns = 4; // Four original fixed dock shortcuts.
        this.settings.desktopCount = clamp(this.settings.desktopCount, 1, 8, 2);
        this.settings.homeLocked = this.settings.homeLocked === true;
        this.appsPerPage = this.settings.gridColumns * this.settings.gridRows;
        document.documentElement.style.setProperty('--home-columns', this.settings.gridColumns);
        document.documentElement.style.setProperty('--dock-columns', this.settings.dockColumns);
    }

    updateHomeSettings(next) {
        const desired = Object.assign({}, this.settings, next || {});
        const cap = (Number(desired.gridColumns) || 4) * (Number(desired.gridRows) || 5);
        const wanted = Number(desired.desktopCount) || 2;
        const occupied = this._entries().length;
        if (wanted * cap < occupied) {
            // Never delete or hide shortcuts when the requested count is too small.
            alert('This layout needs at least ' + Math.ceil(occupied / cap) + ' desktops. Move shortcuts first.');
            return false;
        }
        if (wanted < this.settings.desktopCount) {
            const counts = Array.from({length:wanted}, (_, i) => this._pageEntries(i).length);
            for (const entry of this._entries()) {
                if (Number(this.pageAssignments[entry.id]) < wanted) continue;
                const free = counts.findIndex(count => count < cap);
                if (free < 0) return false;
                this.pageAssignments[entry.id] = free; counts[free]++;
            }
        }
        this.settings = desired;
        this._applyLayout();
        this.currentPage = Math.min(this.currentPage, this.settings.desktopCount - 1);
        this._saveLayout();
        this._renderAll();
        return true;
    }

    isHomeLocked() { return this.settings.homeLocked === true; }
    _lockedNotice() {
        let note = document.getElementById('nuxel-home-lock-toast');
        if (!note) { note = document.createElement('div'); note.id = 'nuxel-home-lock-toast'; note.className = 'toast'; document.body.appendChild(note); }
        note.textContent = 'Home screen locked — unlock in Home Settings.';
        clearTimeout(this._lockToastTimer);
        this._lockToastTimer = setTimeout(() => note.remove(), 2100);
    }
    mainDesktop() {
        this.currentPage = 0; this.closeDrawer(); this._renderAppGrid();
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

    _ensureLayout() {
        const ids = this._getOrderedApps().map(app => app.id);
        if (!this.layout || ids.some(id => !this.layout.appIds.includes(id))) {
            this.layout = new window.NuxelHomeLayout(ids, this.savedEntries ? { entries: this.savedEntries } : { order: this.appOrder });
            this.savedEntries = null;
        }
        this.layout.entries.forEach((entry, index) => {
            const id = typeof entry === 'string' ? entry : entry.id;
            if (this.pageAssignments[id] === undefined) this.pageAssignments[id] = Math.floor(index / this.appsPerPage);
        });
        return this.layout;
    }

    _entries() {
        const byId = new Map(this._getOrderedApps().map(app => [app.id, app]));
        return this._ensureLayout().entries.map(entry => {
            if (typeof entry === 'string') return byId.get(entry);
            return Object.assign({}, entry, { apps: entry.items.map(id => byId.get(id)).filter(Boolean) });
        }).filter(Boolean);
    }

    _pageEntries(page) {
        return this._entries().filter(entry => Number(this.pageAssignments[entry.id]) === page);
    }

    _pageCount() {
        const assigned = Object.values(this.pageAssignments).map(Number).filter(Number.isInteger);
        return Math.max(this.settings.desktopCount, 1 + Math.max(0, ...assigned));
    }

    resetOrder() {
        localStorage.removeItem('nuxel.appOrder');
        localStorage.removeItem('nuxel.launcherLayout');
        this.appOrder = null;
        this.hiddenAppIds.clear();
        this.appSizes = {};
        this.pageAssignments = {};
        this.layout = null;
        this.settings = { gridColumns: 4, gridRows: 5, dockColumns: 4, desktopCount: 2, homeLocked: false };
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
        this._ensureLayout();
        const totalPages = this._pageCount();
        if (this.currentPage >= totalPages) this.currentPage = totalPages - 1;
        const page = this._pageEntries(this.currentPage);
        if (this.drawerOpen) { this._renderDrawerApps(); this._updatePageDots(totalPages); return; }

        this.appList.innerHTML = page.map(app => app.type === 'folder'
            ? '<div class="app-item app-folder" data-folder-id="' + app.id + '" tabindex="0" role="button" aria-label="' + app.name + '"><div class="app-icon folder-icon">' + app.apps.slice(0, 4).map(a => this._appIcon(a)).join('') + '</div><span class="app-label">' + app.name + '</span></div>'
            :
            '<div class="app-item" data-size="' + (this.appSizes[app.id] || 'normal') + '" data-app-id="' + app.id + '" tabindex="0" role="button" aria-label="' + app.name + '" title="' + (app.description || '') + '"><div class="app-icon app-category-' + app.category + '" style="background: ' + app.color + '33; color: ' + app.color + '">' + this._appIcon(app) + '</div><span class="app-label">' + app.name + '</span></div>'
        ).join('');

        this._updatePageDots(totalPages);
    }

    _renderDrawerApps() {
        // Drawer is authoritative ALL apps, not a duplicate of the current Home
        // page. Hidden shortcuts are still discoverable and may be restored.
        this.appList.innerHTML = appRegistry.getAllApps().map((app) =>
            '<div class="app-item drawer-app" data-app-id="' + app.id + '" role="button" tabindex="0" aria-label="' + app.name + '">' +
            '<div class="app-icon" style="background:' + app.color + '33">' + this._appIcon(app) + '</div>' +
            '<span class="app-label">' + app.name + '</span></div>'
        ).join('');
    }

    addToHome(appId, dropIndex) {
        if (this.isHomeLocked()) { this._lockedNotice(); return false; }
        const app = appRegistry.getApp(appId);
        if (!app) return false;
        if (app.docked) { // Already visible in the four-icon dock.
            this.closeDrawer(); return true;
        }
        this.hiddenAppIds.delete(appId);
        this._ensureLayout();
        this.pageAssignments[appId] = this.currentPage;
        if (!this.layout.appIds.includes(appId)) { this.layout.appIds.push(appId); this.layout._normalise(); }
        const existing = this.layout._location(appId);
        if (existing && dropIndex == null) {
            this.currentPage = Math.floor(existing.top / this.appsPerPage);
        } else if (!existing || dropIndex != null) {
            const slot = Number.isInteger(dropIndex) ? dropIndex : Math.min(this._entries().length, (this.currentPage + 1) * this.appsPerPage);
            this.layout.insertApp(appId, slot);
        }
        this.closeDrawer(); this._saveLayout(); this._renderAppGrid();
        return true;
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

        if (item.dataset && item.dataset.folderId) { this._openFolder(item.dataset.folderId); return; }
        this.dragTarget = item;
        this.pressedPointer = e.pointerId;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        this.dragStartTime = Date.now();
        this.hasMoved = false;

        if (this.drawerOpen) {
            this.longPressTimer = setTimeout(() => {
                if (this.isHomeLocked()) { this._lockedNotice(); return; }
                this.drawerHold = true;
                this._showDrawerMenu(item.dataset.appId);
                if (window.NuxelHost && window.NuxelHost.available) window.NuxelHost.action('haptics-long');
            }, 450);
            return;
        }
        if (this.isHomeLocked() && !item.closest('#dock-items')) {
            this.longPressTimer = setTimeout(() => this._lockedNotice(), 450);
            return;
        }
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
            if (this.drawerOpen && this.drawerHold && this.dragTarget &&
                Math.hypot(e.clientX - this.dragStartX, e.clientY - this.dragStartY) > 12) {
                this._startDrag(this.dragTarget, e, true);
                this._updateDrag(e);
                return;
            }
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

        if (this.drawerHold) {
            this.drawerHold = false;
            this.dragTarget = null;
            this.pressedPointer = null;
            this.suppressClickUntil = Date.now() + 500;
            return; // Keep the Add to Home context button visible.
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
        this.drawerHold = false;
    }

    _showDrawerMenu(appId) {
        let menu = document.getElementById('nuxel-drawer-context');
        if (!menu) { menu = document.createElement('div'); menu.id = 'nuxel-drawer-context'; menu.className = 'launcher-edit-toolbar'; document.body.appendChild(menu); }
        menu.replaceChildren();
        const button = document.createElement('button'); button.type = 'button';
        button.textContent = 'Add to Home screen';
        button.onclick = () => { this.addToHome(appId); menu.remove(); };
        menu.appendChild(button);
    }

    // ── Drag mechanics ──────────────────────────────────────────────

    _startDrag(item, e, fromDrawer = false) {
        if (this.isHomeLocked()) { this._lockedNotice(); return; }
        this.drawerHold = false;
        this.isDragging = true;
        this.dragData = { id: item.dataset.appId, el: item, fromDrawer };
        this._positionedThisDrag = false;
        item.classList.add('dragging');
        document.body.classList.add('launcher-dragging');

        // Create ghost
        this.dragGhost = item.cloneNode(true);
        this.dragGhost.classList.add('drag-ghost');
        this.dragGhost.style.position = 'fixed';
        this.dragGhost.style.zIndex = '99999';
        this.dragGhost.style.pointerEvents = 'auto'; // Stable pointer owner during drawer unmount.
        this.dragGhost.style.opacity = '0.85';
        this.dragGhost.style.transform = 'scale(1.1)';
        this.dragGhost.style.left = (e.clientX - 32) + 'px';
        this.dragGhost.style.top = (e.clientY - 32) + 'px';
        document.body.appendChild(this.dragGhost);
        try { this.dragGhost.setPointerCapture(e.pointerId); } catch (err) {}
        if (fromDrawer) {
            const menu = document.getElementById('nuxel-drawer-context'); if (menu) menu.remove();
            this.closeDrawer();
        }

        // Hide original
        item.style.opacity = '0.3';
    }

    _updateDrag(e) {
        if (!this.dragGhost) return;
        const edge = e.clientX < 22 ? -1 : e.clientX > innerWidth - 22 ? 1 : 0;
        if (edge !== this._dragEdge) {
            clearTimeout(this._dragPageTimer);
            this._dragEdge = edge;
            if (edge) this._dragPageTimer = setTimeout(() => {
                const next = this.currentPage + edge;
                if (next >= 0 && next < this._pageCount()) {
                    this.currentPage = next; this._renderAppGrid();
                    this.folderHover = null; this._positionedThisDrag = false;
                }
            }, 550);
        }
        this.dragGhost.style.left = (e.clientX - 32) + 'px';
        this.dragGhost.style.top = (e.clientY - 32) + 'px';

        // Find target under pointer. A folder target needs deliberate centered
        // dwell; ordinary near-edge drops always use insertion/reflow.
        this.dragGhost.style.display = 'none';
        const under = document.elementFromPoint(e.clientX, e.clientY);
        this.dragGhost.style.display = '';

        const targetItem = under ? under.closest('.app-item') : null;
        if (targetItem && targetItem !== this.dragData.el && targetItem.closest('#app-list')) {
            const rect = targetItem.getBoundingClientRect();
            const centered = Math.abs(e.clientX - (rect.left + rect.width / 2)) < rect.width * .24 && Math.abs(e.clientY - (rect.top + rect.height / 2)) < rect.height * .24;
            const targetId = targetItem.dataset.appId;
            if (centered && targetId) {
                if (!this.folderHover || this.folderHover.id !== targetId) this.folderHover = { id: targetId, since: Date.now() };
                if (Date.now() - this.folderHover.since >= 350) targetItem.classList.add('folder-target');
            } else {
                this.folderHover = null;
                document.querySelectorAll('.folder-target').forEach(el => el.classList.remove('folder-target'));
                this._insertAtTarget(targetItem, e.clientX, e.clientY);
            }
        }
    }

    _insertAtTarget(target, x, y) {
        const id = this.dragData && this.dragData.id, targetId = target.dataset.appId;
        if (!id || !targetId) return;
        const entries = this._entries();
        const targetIndex = entries.findIndex(entry => entry && entry.id === targetId);
        if (targetIndex < 0) return;
        const rect = target.getBoundingClientRect();
        this.pageAssignments[id] = this.currentPage;
        this._ensureLayout().insertApp(id, targetIndex + (y > rect.top + rect.height / 2 ? 1 : 0));
        this._positionedThisDrag = true;
        this._renderAppGrid();
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
        clearTimeout(this._dragPageTimer); this._dragEdge = 0;

        if (this.dragData && this.dragData.el) {
            this.dragData.el.style.opacity = '';
            this.dragData.el.classList.remove('dragging');
        }
        if (this.dragGhost) {
            try { if (e && this.dragGhost.hasPointerCapture(e.pointerId)) this.dragGhost.releasePointerCapture(e.pointerId); } catch (err) {}
            this.dragGhost.remove();
            this.dragGhost = null;
        }

        document.body.classList.remove('launcher-dragging');
        document.querySelectorAll('.app-item').forEach(el => el.classList.remove('drag-over'));

        const folder = document.querySelector('.folder-target');
        if (this.dragData && this.dragData.fromDrawer) {
            this.addToHome(this.dragData.id);
        }
        if (this.dragData) {
            const id = this.dragData.id;
            this.pageAssignments[id] = this.currentPage;
            if (folder && folder.dataset.appId) {
                if (this._ensureLayout().createFolder(id, folder.dataset.appId)) {
                    const created = this._ensureLayout().entries.find(entry => entry && entry.type === 'folder' && entry.items.includes(id));
                    if (created) this.pageAssignments[created.id] = this.currentPage;
                }
            } else if (!this._positionedThisDrag) {
                const entries = this._entries();
                const onPage = entries.filter(entry => entry.id !== id && Number(this.pageAssignments[entry.id]) === this.currentPage);
                const last = onPage[onPage.length - 1];
                const pos = last ? entries.findIndex(entry => entry.id === last.id) + 1 : entries.length;
                this._ensureLayout().insertApp(id, pos);
            }
        }
        this._saveLayout();
        this._renderAppGrid();
        this.dragData = null;
        this.folderHover = null;
        this._positionedThisDrag = false;
    }

    _enterEditMode(appId) {
        if (this.isHomeLocked()) { this._lockedNotice(); return; }
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
        if (this.isHomeLocked()) { this._lockedNotice(); return; }
        if (!this.selectedAppId) return;
        this.appSizes[this.selectedAppId] = this.appSizes[this.selectedAppId] === 'large' ? 'normal' : 'large';
        this._saveLayout(); this._renderAll(); this._selectForEdit(this.selectedAppId);
    }

    removeSelected() {
        if (this.isHomeLocked()) { this._lockedNotice(); return; }
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

    _openFolder(id) {
        const folder = this._ensureLayout().entries.find(entry => entry && entry.type === 'folder' && entry.id === id);
        if (!folder) return;
        const apps = new Map(appRegistry.getAllApps().map(app => [app.id, app]));
        const sheet = document.createElement('section');
        sheet.className = 'folder-sheet'; sheet.dataset.folderId = id;
        const render = () => {
            sheet.innerHTML = '<div class="folder-card"><input aria-label="Folder name" value="' + folder.name.replace(/"/g, '&quot;') + '"><button type="button" data-folder-close>Done</button><div class="folder-items">' + folder.items.map(appId => { const app = apps.get(appId); return app ? '<button type="button" data-app-id="' + app.id + '">' + this._appIcon(app) + '<span>' + app.name + '</span></button>' : ''; }).join('') + '</div></div>';
            sheet.querySelector('input').onchange = ev => { this._ensureLayout().renameFolder(id, ev.target.value); this._saveLayout(); this._renderAppGrid(); };
            sheet.querySelector('[data-folder-close]').onclick = () => sheet.remove();
            sheet.querySelectorAll('[data-app-id]').forEach(button => button.onclick = () => { sheet.remove(); appRegistry.launchApp(button.dataset.appId); });
        };
        render(); document.body.appendChild(sheet);
    }

    openDrawer() { this.drawerOpen = true; document.body.classList.add('app-drawer-open'); this._renderAppGrid(); }
    closeDrawer() {
        this.drawerOpen = false; document.body.classList.remove('app-drawer-open');
        const menu = document.getElementById('nuxel-drawer-context'); if (menu) menu.remove();
        this._renderAppGrid();
    }
    advanceDrawer() { if (this.drawerOpen) { this.closeDrawer(); appRegistry.launchApp('nuxel-settings'); } else this.openDrawer(); }

    // ── Swipe navigation ────────────────────────────────────────────

    _onTouchStart(e) {
        if (this.isDragging || this.drawerOpen || !e.target.closest('.app-grid') ||
            e.target.closest('input,textarea,select,.home-settings')) { this.swipeStart = null; return; }
        const t = e.changedTouches[0];
        this.swipeStart = {id:t.identifier,x:t.clientX,y:t.clientY};
    }

    _onTouchEnd(e) {
        if (this.isDragging || this.drawerOpen || !this.swipeStart) return;
        const t = Array.from(e.changedTouches).find(t => t.identifier === this.swipeStart.id);
        if (!t) return;
        const dx = this.swipeStart.x - t.clientX;
        const dy = this.swipeStart.y - t.clientY;
        this.swipeStart = null;
        if (Math.abs(dx) < 52 || Math.abs(dx) < Math.abs(dy) * 1.35) return;
        const total = this._pageCount();
        if (dx > 0 && this.currentPage < total - 1) this.currentPage++;
        else if (dx < 0 && this.currentPage > 0) this.currentPage--;
        else return;
        this._renderAppGrid();
    }

    refresh() {
        this._renderAll();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.launcher = new Launcher();
});
