// Nuxel Home — App Launcher v0.1.1
// Drag-and-drop reorder, persistent order, tap-to-launch

class Launcher {
    constructor() {
        this.appList = document.getElementById('app-list');
        this.dockItems = document.getElementById('dock-items');
        this.searchOverlay = document.getElementById('search-overlay');

        this.currentPage = 0;
        this.appsPerPage = 20;
        this.settings = { gridColumns: 4, gridRows: 5, drawerColumns: 3, dockColumns: 4, desktopCount: 2, homeLocked: false, defaultDesktop: 1, desktopNames: {} };
        /* Home and the All Apps drawer are independent grids.  The Home grid
           always honours the saved column count; the drawer has its own saved
           count so changing one never silently changes the other. */
        this.effectiveGridColumns = 4;
        this.hiddenAppIds = new Set();
        this.appSizes = {};
        this.layout = null;
        this.folderHover = null;
        this.drawerOpen = false;
        this.editMode = false;
        this.selectedAppId = null;
        this.isDragging = false;
        this.dragState = 'IDLE';
        this.dragData = null;
        this.dragGhost = null;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.dragStartTime = 0;
        this.longPressTimer = null;
        this.moveArmed = false;
        this.hasMoved = false;
        this.lastPointerX = 0;
        this.lastPointerY = 0;
        this.pointerCaptureEl = null;
        this._dragSnapshot = null;
        this._dropIndex = -1;
        // PWNAGE-37000B: the drawer is built once and toggled, not rebuilt on
        // every open.  The old open/close path reparsed 30 tiles and 29 image
        // elements (measured 39-57 ms of synchronous main-thread work).
        this.drawerList = null;
        this._drawerSignature = '';
        this._homeScrollTop = 0;
        /* A real scroll can deliver pointermove events sparsely.  Once the
           drawer/scroll container moves, a release is never a tap. */
        this._scrollDirty = false;
        this._pointerDownAt = 0;

        this._init();
    }

    _init() {
        this._loadOrder();
        this._loadLayout();
        this._applyLayout();
        this._ensureDesktopLayout();
        this._renderAll();
        this._bindPointerEvents();
        this._bindOrientation();
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
            if (this.desktopLayout) this.desktopLayout.save();
        } catch (e) { console.warn('Could not save launcher layout:', e); }
    }

    /* Retained for callers that need the current orientation; Home column
       count is now an explicit user setting and is never overridden by it. */
    _isPortrait() {
        try {
            if (window.matchMedia) {
                const mq = window.matchMedia('(orientation: portrait)');
                if (mq && typeof mq.matches === 'boolean') return mq.matches;
            }
            if (typeof window.innerWidth === 'number' && typeof window.innerHeight === 'number') {
                return window.innerHeight >= window.innerWidth;
            }
        } catch (e) { /* no media query support: use the configured width */ }
        return false;
    }

    _applyLayout() {
        const clamp = (value, low, high, fallback) => {
            value = Number(value);
            return Number.isInteger(value) && value >= low && value <= high ? value : fallback;
        };
        this.settings.gridColumns = clamp(this.settings.gridColumns, 3, 6, 4);
        this.settings.gridRows = clamp(this.settings.gridRows, 4, 7, 5);
        this.settings.drawerColumns = clamp(this.settings.drawerColumns, 3, 6, 3);
        this.settings.dockColumns = 4; // Four original fixed dock shortcuts.
        this.settings.desktopCount = clamp(this.settings.desktopCount, 1, 8, 2);
        this.settings.homeLocked = this.settings.homeLocked === true;
        this.settings.defaultDesktop = clamp(this.settings.defaultDesktop, 1, this.settings.desktopCount, 1);
        if (!this.settings.desktopNames || typeof this.settings.desktopNames !== 'object') this.settings.desktopNames = {};
        // Home settings are authoritative in every orientation.  The old
        // portrait-only three-column override made a 4-column setting render
        // as three and is intentionally gone.
        this.effectiveGridColumns = this.settings.gridColumns;
        this.appsPerPage = this.effectiveGridColumns * this.settings.gridRows;
        document.documentElement.style.setProperty('--home-columns', this.effectiveGridColumns);
        document.documentElement.style.setProperty('--drawer-columns', this.settings.drawerColumns);
        document.documentElement.style.setProperty('--dock-columns', this.settings.dockColumns);
    }

    _bindOrientation() {
        if (this._orientationWired) return;
        this._orientationWired = true;
        let pending = null;
        let suppressResize = false;
        const reflow = () => {
            /* The synthetic resize below is a notification to other widgets,
               not a request to run this reflow again.  Without this guard the
               resize listener re-entered forever, calling reset-zoom/repaint at
               ~5 Hz even while the panel was blanked. */
            if (suppressResize) return;
            if (pending !== null) clearTimeout(pending);
            pending = setTimeout(() => {
                pending = null;
                const before = this.effectiveGridColumns;
                const drawerBefore = this.settings.drawerColumns;
                this._applyLayout();
                // A rotation can leave WebKit page scale, cached layout or the
                // drawer's intrinsic size from the previous viewport.  Reset the
                // central zoom policy, rebuild the cached drawer, and force the
                // grid to a fresh layout even when the column count is unchanged.
                try {
                    if (window.NuxelZoomPolicy && window.NuxelZoomPolicy.reset) window.NuxelZoomPolicy.reset(window);
                    const host = window.NuxelHost;
                    if (host && host.available && typeof host.action === 'function') {
                        Promise.resolve(host.action('reset-zoom')).catch(() => {});
                    }
                } catch (e) {}
                if (this.drawerOpen || this.drawerList) this._renderDrawerApps(true);
                if (this.drawerList) {
                    this.drawerList.style.gridTemplateColumns = 'repeat(' + this.settings.drawerColumns + ', minmax(0, 1fr))';
                    this.drawerList.scrollTop = 0;
                    try { void this.drawerList.offsetHeight; } catch (e) {}
                }
                try { document.documentElement.style.setProperty('--viewport-width', window.innerWidth + 'px'); } catch (e) {}
                if (this.effectiveGridColumns !== before || drawerBefore !== this.settings.drawerColumns) this._renderAll();
                try {
                    suppressResize = true;
                    try { window.dispatchEvent(new Event('resize')); }
                    finally { suppressResize = false; }
                } catch (e) {}
                try { document.dispatchEvent(new CustomEvent('nuxel:orientation-reflow', { detail: { columns: this.settings.drawerColumns, width: window.innerWidth, height: window.innerHeight } })); } catch (e) {}
            }, 160);
        };
        try {
            if (window.matchMedia) {
                const mq = window.matchMedia('(orientation: portrait)');
                if (mq && mq.addEventListener) mq.addEventListener('change', reflow);
                else if (mq && mq.addListener) mq.addListener(reflow);
            }
        } catch (e) { /* optional */ }
        try { window.addEventListener('orientationchange', reflow, { passive: true }); } catch (e) {}
        try { window.addEventListener('resize', reflow, { passive: true }); } catch (e) {}
        try { if (window.visualViewport) window.visualViewport.addEventListener('resize', reflow, { passive: true }); } catch (e) {}
    }

    updateHomeSettings(next) {
        const desired = Object.assign({}, this.settings, next || {});
        const desiredColumns = Math.max(3, Math.min(6, Number(desired.gridColumns) || 4));
        desired.gridColumns = desiredColumns;
        desired.drawerColumns = Math.max(3, Math.min(6, Number(desired.drawerColumns) || 3));
        const effectiveColumns = desiredColumns;
        const cap = effectiveColumns * (Number(desired.gridRows) || 5);
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
        desired.defaultDesktop = Math.max(1, Math.min(wanted, Number(desired.defaultDesktop) || 1));
        this.settings = desired;
        this._applyLayout();
        if (this.desktopLayout) this.desktopLayout.setGeometry(this.settings.gridColumns, this.settings.gridRows, this.settings.desktopCount);
        this.currentPage = Math.min(this.currentPage, this.settings.desktopCount - 1);
        this._saveLayout();
        this._renderAll();
        return true;
    }

    moveDesktop(direction) {
        const from = Number(this.currentPage) || 0;
        const to = from + (Number(direction) < 0 ? -1 : 1);
        if (to < 0 || to >= this.settings.desktopCount) return false;
        const swap = (from, to) => {
            const fromIds = this._entries().filter(e => Number(this.pageAssignments[e.id]) === from).map(e => e.id);
            const toIds = this._entries().filter(e => Number(this.pageAssignments[e.id]) === to).map(e => e.id);
            fromIds.forEach(id => { this.pageAssignments[id] = to; });
            toIds.forEach(id => { this.pageAssignments[id] = from; });
        };
        swap(from, to);
        const names = this.settings.desktopNames || {};
        const a = names[from + 1], b = names[to + 1];
        if (b) names[from + 1] = b; else delete names[from + 1];
        if (a) names[to + 1] = a; else delete names[to + 1];
        this.settings.desktopNames = names;
        if (Number(this.settings.defaultDesktop) === from + 1) this.settings.defaultDesktop = to + 1;
        else if (Number(this.settings.defaultDesktop) === to + 1) this.settings.defaultDesktop = from + 1;
        this.currentPage = to;
        this._saveLayout();
        this._renderAll();
        return true;
    }

    renameDesktop(name) {
        const page = (Number(this.currentPage) || 0) + 1;
        this.settings.desktopNames = this.settings.desktopNames || {};
        const clean = String(name || '').trim().slice(0, 40);
        if (clean) this.settings.desktopNames[page] = clean;
        else delete this.settings.desktopNames[page];
        this._saveLayout();
        return true;
    }

    isHomeLocked() { return Boolean(this.settings && this.settings.homeLocked === true); }
    _lockedNotice() {
        let note = document.getElementById('nuxel-home-lock-toast');
        if (!note) { note = document.createElement('div'); note.id = 'nuxel-home-lock-toast'; note.className = 'toast'; document.body.appendChild(note); }
        note.textContent = 'Home screen locked — unlock in Home Settings.';
        clearTimeout(this._lockToastTimer);
        this._lockToastTimer = setTimeout(() => note.remove(), 2100);
    }
    mainDesktop() {
        // System Home is a hard reset of the visible launcher surface: primary
        // desktop, no drawer, no edit mode, no transient folder sheet, and the
        // page scrolled back to the top.  It never depends on the page the user
        // happened to be on when they pressed the penguin/Home button.
        this.currentPage = Math.max(0, Math.min(this.settings.desktopCount - 1,
            (Number(this.settings.defaultDesktop) || 1) - 1));
        this.exitEditMode();
        this.closeDrawer();
        document.querySelectorAll('.folder-sheet').forEach(el => el.remove());
        const grid = document.getElementById('app-grid');
        if (grid) grid.scrollTop = 0;
        this._renderAppGrid();
        if (window.NuxelWidgets) window.NuxelWidgets.renderPage(this.currentPage);
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
        if (!this.layout) {
            this.layout = new window.NuxelHomeLayout(ids, this.savedEntries ? { entries: this.savedEntries } : { order: this.appOrder });
            this.savedEntries = null;
        } else {
            const added = ids.some(id => !this.layout.appIds.includes(id));
            const removed = this.layout.appIds.some(id => !ids.includes(id));
            if (added || removed) {
                // A locked Home keeps the owner's exact layout.  New installs
                // remain in the All Apps drawer and join Home after unlock.
                if (!this.isHomeLocked()) {
                    this.layout = new window.NuxelHomeLayout(ids, { entries: this.layout.snapshot().entries });
                }
            }
        }
        this.layout.entries.forEach((entry, index) => {
            const id = typeof entry === 'string' ? entry : entry.id;
            if (this.pageAssignments[id] === undefined) this.pageAssignments[id] = Math.floor(index / this.appsPerPage);
        });
        return this.layout;
    }

    _ensureDesktopLayout() {
        if (!window.NuxelDesktopLayout) return null;
        const apps = this._getOrderedApps().map(app => app.id);
        if (!this.desktopLayout) {
            let legacyWidgets = null;
            try { legacyWidgets = JSON.parse(localStorage.getItem('nuxel.widgets') || 'null'); } catch (e) {}
            this.desktopLayout = window.NuxelDesktopLayout.load({
                columns: this.settings.gridColumns,
                rows: this.settings.gridRows,
                desktopCount: this.settings.desktopCount,
                apps: apps,
                appOrder: apps,
                pageAssignments: this.pageAssignments,
                legacyWidgets: legacyWidgets
            });
        }
        this.desktopLayout.setGeometry(this.settings.gridColumns, this.settings.gridRows, this.settings.desktopCount);
        this.desktopLayout.ensureApps(apps, this.pageAssignments, Array.from(this.hiddenAppIds));
        this._ensureLayout();
        const folderEntries = this.layout ? this.layout.entries.filter(e => e && e.type === 'folder') : [];
        const folderIds = new Set(folderEntries.map(e => e.id));
        this.desktopLayout.entities.slice().forEach(e => {
            if (e.type === 'folder' && !folderIds.has(e.id)) this.desktopLayout.remove(e.id);
        });
        folderEntries.forEach(e => {
            if (!this.desktopLayout.entity(e.id)) {
                const desktop = Number(this.pageAssignments[e.id]);
                const d = Number.isInteger(desktop) ? Math.max(0, Math.min(this.settings.desktopCount - 1, desktop)) : 0;
                const spot = this.desktopLayout.findFree(d, 1, 1, null);
                if (spot) this.desktopLayout.entities.push({ id: e.id, type: 'folder', ref: e.id, desktop: d, x: spot.x, y: spot.y, w: 1, h: 1 });
            }
        });
        this.desktopLayout.entities.forEach(e => {
            if (e.type === 'app' || e.type === 'folder') this.pageAssignments[e.type === 'app' ? e.ref : e.ref] = e.desktop;
        });
        return this.desktopLayout;
    }

    _renderGridPosition(node, id) {
        if (!this.desktopLayout) return;
        const e = this.desktopLayout.entity(id);
        if (!e) return;
        node.style.gridColumn = (e.x + 1) + ' / span ' + e.w;
        node.style.gridRow = (e.y + 1) + ' / span ' + e.h;
    }

    _dropGridCoordinates(clientX, clientY) {
        if (!this.appList) return { x: 0, y: 0 };
        const rect = this.appList.getBoundingClientRect();
        const colW = rect.width / Math.max(1, this.settings.gridColumns);
        const rowH = rect.height / Math.max(1, this.settings.gridRows);
        return {
            x: Math.max(0, Math.min(this.settings.gridColumns - 1, Math.floor((clientX - rect.left) / colW))),
            y: Math.max(0, Math.min(this.settings.gridRows - 1, Math.floor((clientY - rect.top) / rowH)))
        };
    }

    _entries() {
        const byId = new Map(this._getOrderedApps().map(app => [app.id, app]));
        return this._ensureLayout().entries.map(entry => {
            if (typeof entry === 'string') return byId.get(entry);
            return Object.assign({}, entry, { apps: entry.items.map(id => byId.get(id)).filter(Boolean) });
        }).filter(Boolean);
    }

    _pageEntries(page) {
        this._ensureDesktopLayout();
        return this._entries().filter(entry => {
            const e = this.desktopLayout && this.desktopLayout.entity(entry.id);
            return e ? e.desktop === page : Number(this.pageAssignments[entry.id]) === page;
        });
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
        this.desktopLayout = null;
        try { localStorage.removeItem(window.NuxelDesktopLayout ? window.NuxelDesktopLayout.KEY : 'nuxel.desktopLayout.v1'); } catch (e) {}
        this.settings = { gridColumns: 4, gridRows: 5, drawerColumns: 3, dockColumns: 4, desktopCount: 2, homeLocked: false, defaultDesktop: 1, desktopNames: {} };
        this._applyLayout();
        this._renderAll();
    }

    // ── Render ──────────────────────────────────────────────────────

    _renderAll() {
        this._renderDock();
        this._renderAppGrid();
        if (window.NuxelWidgets) window.NuxelWidgets.renderPage(this.currentPage);
    }

    _renderDock() {
        // Stable identities: registry refreshes happen every few seconds and
        // used to replace all four dock nodes, causing the intermittent bottom
        // row flicker.  Reuse each app's node and only move/update what really
        // changed.
        if (!this.dockItems) return;
        const docked = appRegistry.getDockedApps().filter(app => !this.hiddenAppIds.has(app.id));
        const sig = docked.map(app => [app.id, app.name, app.icon, app.color, app.category].join(':')).join('|');
        const children = Array.from(this.dockItems.children);
        const order = children.map(el => el.dataset.appId).filter(Boolean);
        const wanted = docked.map(app => app.id);
        if (sig === this._dockSignature && order.join('|') === wanted.join('|') && children.length === wanted.length) return;
        const existing = new Map(children.map(el => [el.dataset.appId, el]));
        this._dockSignature = sig;
        docked.forEach((app, i) => {
            let node = existing.get(app.id);
            if (!node) {
                node = document.createElement('div');
                node.className = 'app-item press-effect';
                node.dataset.appId = app.id;
                node.tabIndex = 0;
                node.setAttribute('role', 'button');
                const icon = document.createElement('div');
                icon.className = 'app-icon app-category-' + app.category;
                node.appendChild(icon);
                node.__nuxelIcon = icon;
            }
            node.dataset.index = i;
            node.setAttribute('aria-label', app.name);
            const icon = node.__nuxelIcon || node.querySelector('.app-icon');
            if (icon) {
                const itemSig = [app.name, app.icon, app.color, app.category].join(':');
                if (icon.dataset.signature !== itemSig) {
                    icon.className = 'app-icon app-category-' + app.category;
                    icon.style.background = app.color + '33';
                    icon.style.color = app.color;
                    icon.innerHTML = this._appIcon(app, { priority: 'visible' });
                    icon.dataset.signature = itemSig;
                }
            }
            if (this.dockItems.children[i] !== node) {
                this.dockItems.insertBefore(node, this.dockItems.children[i] || null);
            }
        });
        for (const el of Array.from(this.dockItems.children)) {
            if (!wanted.includes(el.dataset.appId)) el.remove();
        }
    }

    _renderAppGrid() {
        if (!this.appList) return;
        this._ensureLayout();
        const totalPages = this._pageCount();
        if (this.currentPage >= totalPages) this.currentPage = totalPages - 1;
        const page = this._pageEntries(this.currentPage);
        if (this.drawerOpen) {
            this._renderDrawerApps();
            if (this.drawerList) this.drawerList.hidden = false;
            this.appList.hidden = true;
            this._updatePageDots(totalPages);
            return;
        }
        if (this.drawerList) this.drawerList.hidden = true;
        this.appList.hidden = false;

        // PWNAGE-90000: reconcile keyed nodes instead of replacing the whole
        // page.  A registry/status refresh must not discard decoded <img> nodes
        // or trigger a second network/decode pass on first unlock.
        const wanted = page.map((app) => app.type === 'folder' ? 'f:' + app.id : 'a:' + app.id);
        const existing = new Map();
        Array.from(this.appList.children).forEach((node) => {
            const key = node.dataset.folderId ? 'f:' + node.dataset.folderId
                : node.dataset.appId ? 'a:' + node.dataset.appId : '';
            if (key && !existing.has(key)) existing.set(key, node);
            else node.remove();
        });
        page.forEach((app, index) => {
            const key = app.type === 'folder' ? 'f:' + app.id : 'a:' + app.id;
            let node = existing.get(key);
            if (!node) {
                node = this._createGridNode(app);
            } else {
                this._updateGridNode(node, app);
            }
            const current = this.appList.children[index];
            if (current !== node) this.appList.insertBefore(node, current || null);
            const id = node.dataset.appId || node.dataset.folderId;
            if (id) this._renderGridPosition(node, id);
        });
        for (const node of Array.from(this.appList.children)) {
            const key = node.dataset.folderId ? 'f:' + node.dataset.folderId
                : node.dataset.appId ? 'a:' + node.dataset.appId : '';
            if (!wanted.includes(key)) node.remove();
        }
        this.appList.style.gridTemplateColumns = 'repeat(' + this.settings.gridColumns + ', minmax(0, 1fr))';
        this.appList.style.gridTemplateRows = 'repeat(' + this.settings.gridRows + ', var(--home-row-height, 86px))';
        if (window.NuxelWidgets) { try { window.NuxelWidgets.renderPage(this.currentPage); } catch (e) {} }
        this._updatePageDots(totalPages);
    }

    _gridSignature(app) {
        if (app.type === 'folder') {
            return ['folder', app.id, app.name, (app.apps || []).map((a) => a.id).join(',')].join(':');
        }
        const iconSrc = (window.NuxelIconManifest && window.NuxelIconManifest[app.id])
            || app.iconAsset || '';
        return ['app', app.id, app.name, app.description || '', app.category || '',
                app.color || '', this.appSizes[app.id] || 'normal',
                iconSrc, app.icon || ''].join(':');
    }

    _createGridNode(app) {
        const node = document.createElement('div');
        if (app.type === 'folder') {
            node.className = 'app-item app-folder';
            node.dataset.folderId = app.id;
            node.tabIndex = 0;
            node.setAttribute('role', 'button');
            const icon = document.createElement('div');
            icon.className = 'app-icon folder-icon';
            node.appendChild(icon);
            const label = document.createElement('span');
            label.className = 'app-label';
            node.appendChild(label);
        } else {
            node.className = 'app-item';
            node.dataset.appId = app.id;
            node.tabIndex = 0;
            node.setAttribute('role', 'button');
            const icon = document.createElement('div');
            icon.className = 'app-icon app-category-' + (app.category || 'default');
            node.appendChild(icon);
            const label = document.createElement('span');
            label.className = 'app-label';
            node.appendChild(label);
        }
        this._updateGridNode(node, app, true);
        return node;
    }

    _updateGridNode(node, app, force) {
        if (!node) return;
        const sig = this._gridSignature(app);
        if (!force && node.dataset.gridSignature === sig) return;
        node.dataset.gridSignature = sig;
        node.setAttribute('aria-label', app.name);
        if (app.type === 'folder') {
            const icon = node.querySelector('.app-icon');
            if (icon) {
                const inner = app.apps.slice(0, 4).map((a) => this._appIcon(a)).join('');
                if (icon.innerHTML !== inner) icon.innerHTML = inner;
            }
        } else {
            node.dataset.size = this.appSizes[app.id] || 'normal';
            node.title = app.description || '';
            const icon = node.querySelector('.app-icon');
            if (icon) {
                icon.className = 'app-icon app-category-' + (app.category || 'default');
                icon.style.background = (app.color || '') + '33';
                icon.style.color = app.color || '';
                // Only rebuild the icon subtree when the actual source/glyph
                // changed.  Ordinary re-renders keep the decoded <img> node.
                const iconSig = [app.name, app.icon, app.color, app.category,
                                 app.iconAsset || ''].join(':');
                if (icon.dataset.iconSignature !== iconSig) {
                    icon.innerHTML = this._appIcon(app, { priority: 'visible' });
                    icon.dataset.iconSignature = iconSig;
                }
            }
        }
        const label = node.querySelector('.app-label');
        if (label && label.textContent !== app.name) label.textContent = app.name;
    }

    _drawerContainer() {
        if (this.drawerList && this.drawerList.isConnected) return this.drawerList;
        const grid = document.getElementById('app-grid');
        if (!grid) return null;
        let el = document.getElementById('drawer-list');
        if (!el) {
            el = document.createElement('div');
            el.id = 'drawer-list';
            el.className = 'app-list drawer-list';
            el.hidden = true;
            const anchor = this.appList || document.getElementById('app-list');
            if (anchor && anchor.parentNode === grid) grid.insertBefore(el, anchor.nextSibling);
            else grid.appendChild(el);
        }
        this.drawerList = el;
        return el;
    }

    _dockAppIds() {
        // The four pinned desktop shortcuts are Home chrome, never drawer
        // entries.  The static IDs are a fail-safe for a stale canonical
        // registry that has not published docked=true yet; the registry set is
        // authoritative for any future dock change.
        const ids = new Set(appRegistry.getDockedApps().map((app) => app.id));
        ['nuxel-dialer', 'nuxel-messages', 'nuxel-settings', 'org.nuxel.Terminal']
            .forEach((id) => ids.add(id));
        return ids;
    }

    _renderDrawerApps(force) {
        // Drawer is the authoritative ALL-apps list, EXCEPT the four pinned
        // dock shortcuts.  The previous implementation rendered every app and
        // therefore duplicated the dock inside the drawer.  Hidden shortcuts
        // remain discoverable and may be restored.
        const list = this._drawerContainer();
        if (!list) return;
        const dockedIds = this._dockAppIds();
        const apps = appRegistry.getAllApps().filter((app) => !dockedIds.has(app.id));
        // Rebuild only when the registry output actually changes (install,
        // rename, icon/colour edit).  Normal opens are a class/hidden toggle.
        const signature = apps.map((app) =>
            [app.id, app.name, app.icon, app.color, app.category, app.type, app.docked ? '1' : '0'].join(':')
        ).join('|');
        if (!force && signature === this._drawerSignature && list.childElementCount) return;
        this._drawerSignature = signature;
        list.innerHTML = apps.map((app) =>
            '<div class="app-item drawer-app" data-app-id="' + app.id + '" data-drawer-entry="1" role="button" tabindex="0" aria-label="' + app.name + '">' +
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

    _appIcon(app, opts) {
        if (window.NuxelAppIcon) return window.NuxelAppIcon(app, opts);
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
        // One authoritative pointer stream.  The old code also listened to
        // touchstart/touchend for page swipes; those are passive observers and
        // never drive the icon drag.  Pointer capture is taken on a STABLE
        // element (the grid) once the long press fires, not on an app tile
        // that may be replaced by a rerender mid-gesture.
        document.addEventListener('pointerdown', (e) => this._onPointerDown(e));
        document.addEventListener('pointermove', (e) => this._onPointerMove(e), { passive: false });
        document.addEventListener('pointerup', (e) => this._onPointerUp(e));
        const markScroll = (e) => {
            const t = e && e.target;
            if (!t || !t.closest || !t.closest('#app-grid,.drawer-list,.app-list')) return;
            this._scrollDirty = true;
            // WebKit can synthesize the compatibility click after the finger
            // has already started a kinetic scroll.  Keep taps suppressed for
            // a short settle window after ANY real scroll event.
            this.suppressClickUntil = Date.now() + 650;
        };
        const gridEl = document.getElementById('app-grid');
        if (gridEl) gridEl.addEventListener('scroll', markScroll, { passive: true, capture: true });
        document.addEventListener('scroll', markScroll, { passive: true, capture: true });
        // Some WebKitGTK builds report touch scrolling before the scroll event
        // itself.  Track finger travel directly as a second, independent guard.
        document.addEventListener('touchstart', (e) => {
            const t = e.target && e.target.closest && e.target.closest('#app-grid,.drawer-list,.app-list');
            const p = e.touches && e.touches[0];
            this._touchGuard = t && p ? { x: p.clientX, y: p.clientY } : null;
        }, { passive: true, capture: true });
        // Drawer-opening settle guard: the swipe that opened the drawer must not
        // move its scroll position.  Only a fresh touch sequence may scroll.
        document.addEventListener('touchmove', (e) => {
            const p = e.touches && e.touches[0];
            if (!p) return;
            if (Date.now() < (this._drawerOpenGuardUntil || 0)) {
                if (e.cancelable) e.preventDefault();
                if (this.drawerList) this.drawerList.scrollTop = 0;
                const grid = document.getElementById('app-grid');
                if (grid) grid.scrollTop = 0;
                return;
            }
            if (!this._touchGuard) return;
            if (Math.abs(p.clientX - this._touchGuard.x) > 12 ||
                Math.abs(p.clientY - this._touchGuard.y) > 12) {
                this._scrollDirty = true;
                this.suppressClickUntil = Date.now() + 650;
            }
        }, { passive: false, capture: true });
        document.addEventListener('pointercancel', (e) => this._cancelPointer(e && e.pointerId));
        document.addEventListener('lostpointercapture', (e) => {
            // Capture can be lost without a pointercancel (window switch,
            // target teardown).  Roll back a real drag, but ignore the normal
            // release path where _endDrag already cleared isDragging.
            if (this.isDragging && e && e.pointerId === this.pressedPointer) {
                this._cancelPointer(e.pointerId);
            }
        });
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
        // Page swipes. Passive and deliberately separate from the pointer drag
        // state; a drag clears swipeStart so the release cannot also paginate.
        document.addEventListener('touchstart', (e) => this._onTouchStart(e), { passive: true });
        document.addEventListener('touchend', (e) => this._onTouchEnd(e), { passive: true });

        // Visible host acknowledgement (screenshot, refused action, ...).
        const showToast = (ev) => {
            const text = ev && ev.detail && ev.detail.text;
            if (!text) return;
            if (window.NuxelOSD && typeof window.NuxelOSD.show === 'function') {
                window.NuxelOSD.show(String(text));
                return;
            }
            let t = document.getElementById('nuxel-host-toast');
            if (!t) {
                t = document.createElement('div');
                t.id = 'nuxel-host-toast';
                t.className = 'toast';
                t.style.pointerEvents = 'none';
                t.style.zIndex = '12000';
                document.body.appendChild(t);
            }
            t.textContent = String(text);
            clearTimeout(this._hostToastTimer);
            this._hostToastTimer = setTimeout(() => t.remove(), 3200);
        };
        document.addEventListener('nuxel:toast', showToast);
        if (typeof window.addEventListener === 'function') window.addEventListener('nuxel:toast', showToast);
    }

    _capturePointer(pointerId) {
        const grid = document.getElementById('app-grid') || document.documentElement;
        try {
            grid.setPointerCapture(pointerId);
            this.pointerCaptureEl = grid;
        } catch (e) {
            // Capture is an enhancement; document-level listeners still see
            // the stream on engines without element capture.
            this.pointerCaptureEl = null;
        }
        this._capturedPointer = pointerId;
    }

    _releasePointer() {
        if (this.pointerCaptureEl && this._capturedPointer !== null && this._capturedPointer !== undefined) {
            try { this.pointerCaptureEl.releasePointerCapture(this._capturedPointer); } catch (e) {}
        }
        this.pointerCaptureEl = null;
        this._capturedPointer = null;
    }

    _onPointerDown(e) {
        // A second finger must not cancel or hijack the primary interaction.
        if (this.pressedPointer !== null && this.pressedPointer !== undefined &&
            e.pointerId !== this.pressedPointer) return;
        if (e.isPrimary === false || (e.button !== undefined && e.button !== 0)) return;
        this._cancelPointer();
        const item = e.target.closest && e.target.closest('.app-item');
        if (!item) return;

        if (item.dataset && item.dataset.folderId) { this._openFolder(item.dataset.folderId); return; }
        this.dragTarget = item;
        this.dragState = 'PRESS_PENDING';
        this.pressedPointer = e.pointerId;
        this.dragStartX = this.lastPointerX = e.clientX;
        this.dragStartY = this.lastPointerY = e.clientY;
        this.dragStartTime = Date.now();
        this._pointerDownAt = this.dragStartTime;
        this._scrollDirty = false;
        this.hasMoved = false;

        // Move arms an explicit drag: the next press on the selected icon
        // begins a real grid drag without the long-press hold.
        if (this.moveArmed && this.selectedAppId && item.dataset.appId === this.selectedAppId &&
            !item.closest('#dock-items')) {
            this.moveArmed = false;
            document.body.classList.remove('move-armed');
            this._startDrag(item, e);
            return;
        }

        const afterHold = (fn) => {
            this.longPressTimer = setTimeout(() => {
                this.longPressTimer = null;
                fn();
            }, 450);
        };
        if (this.drawerOpen) {
            afterHold(() => {
                if (this.isHomeLocked()) { this._lockedNotice(); return; }
                this.drawerHold = true;
                this._showDrawerMenu(item.dataset.appId);
                if (window.NuxelHost && window.NuxelHost.available) window.NuxelHost.action('haptics-long');
            });
            return;
        }
        if (this.isHomeLocked() && !item.closest('#dock-items')) {
            afterHold(() => this._lockedNotice());
            return;
        }
        // Dock items still activate on release; long press selects them for
        // removal but does not turn the fixed dock into a reordering UI.
        if (item.closest('#dock-items')) {
            afterHold(() => this._enterEditMode(item.dataset.appId));
            return;
        }
        afterHold(() => {
            // PWNAGE-88000: long-press shows a stable action row (Resize /
            // Remove / Move / Desktop N / Done).  Drag no longer auto-starts
            // here; the Move button arms an explicit drag.
            this._enterEditMode(item.dataset.appId);
        });
    }

    _onPointerMove(e) {
        if (this.pressedPointer === null || this.pressedPointer === undefined) return;
        if (e.pointerId !== this.pressedPointer) return;
        this.lastPointerX = e.clientX;
        this.lastPointerY = e.clientY;
        if (!this.isDragging) {
            if (this.drawerOpen && this.drawerHold && this.dragTarget &&
                Math.hypot(e.clientX - this.dragStartX, e.clientY - this.dragStartY) > 12) {
                this._startDrag(this.dragTarget, e, true);
                this._updateDrag(e);
                return;
            }
            // A finger that moves before the 450 ms hold expires is scrolling
            // or swiping, not dragging. Cancel the pending hold exactly once.
            if (this.dragTarget && !this.hasMoved) {
                const dx = Math.abs(e.clientX - this.dragStartX);
                const dy = Math.abs(e.clientY - this.dragStartY);
                // 12 CSS px is the measured tap/scroll boundary on the S10+
                // panel.  Anything larger is a scroll/page swipe, never a tap.
                if (dx > 12 || dy > 12) {
                    this.hasMoved = true;
                    this._scrollDirty = true;
                    if (this.longPressTimer) { clearTimeout(this.longPressTimer); this.longPressTimer = null; }
                }
            }
            return;
        }
        if (e.cancelable) e.preventDefault();
        this._updateDrag(e);
    }

    _onPointerUp(e) {
        if (this.pressedPointer === null || this.pressedPointer === undefined) return;
        if (e.pointerId !== this.pressedPointer) return;
        if (this.longPressTimer) { clearTimeout(this.longPressTimer); this.longPressTimer = null; }

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
        // Normal tap either chooses an icon to edit or launches it. The release
        // target is re-hit-tested so WebKit retargeting cannot launch a
        // different icon under the finger.
        const released = e.target && e.target.closest ? e.target.closest('.app-item') : null;
        const stableTap = !this.hasMoved && !this._scrollDirty &&
            Date.now() >= (this.suppressClickUntil || 0) &&
            (Date.now() - this._pointerDownAt) < 650;
        if (stableTap && released && released === this.dragTarget) {
            const appId = released.dataset.appId;
            if (appId && this.editMode) this._selectForEdit(appId);
            else if (appId) appRegistry.launchApp(appId);
        }

        this.dragTarget = null;
        this.pressedPointer = null;
        this.hasMoved = false;
        this._scrollDirty = false;
        this._touchGuard = null;
        this.dragState = 'IDLE';
    }

    _cancelPointer(pointerId) {
        if (pointerId !== undefined && pointerId !== null &&
            this.pressedPointer !== null && this.pressedPointer !== undefined &&
            pointerId !== this.pressedPointer) return;
        if (this.longPressTimer) { clearTimeout(this.longPressTimer); this.longPressTimer = null; }
        if (this.isDragging) this._endDrag(null, true);
        this._releasePointer();
        this.dragTarget = null;
        this.pressedPointer = null;
        this.hasMoved = false;
        this.drawerHold = false;
        this.swipeStart = null;
        this._scrollDirty = false;
        this.dragState = 'IDLE';
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
        this.swipeStart = null;
        this.isDragging = true;
        this.dragState = 'DRAGGING';
        // Snapshot the complete model before any render: pointercancel must be
        // a true rollback for both a Home reorder and a drawer->Home drag.
        this._dragSnapshot = {
            layout: this.layout ? this.layout.snapshot() : null,
            assignments: Object.assign({}, this.pageAssignments),
            hidden: Array.from(this.hiddenAppIds),
            page: this.currentPage,
        };
        this.dragData = {
            id: item.dataset.appId,
            el: item,
            fromDrawer,
        };
        this._positionedThisDrag = false;
        this._dropIndex = -1;
        item.classList.add('dragging');
        document.body.classList.add('launcher-dragging');
        this._capturePointer(e.pointerId);

        // One stable ghost, mounted to <body>; pointer-events:none is set in
        // CSS so it can never steal hit-testing from Home icons.
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
        if (fromDrawer) {
            const menu = document.getElementById('nuxel-drawer-context'); if (menu) menu.remove();
            // Reveal a temporary Home slot before unmounting the drawer. This
            // is in-memory only until pointerup; cancel restores the snapshot.
            const id = this.dragData.id;
            this.hiddenAppIds.delete(id);
            this._ensureLayout();
            if (!this.layout.appIds.includes(id)) { this.layout.appIds.push(id); this.layout._normalise(); }
            this.pageAssignments[id] = this.currentPage;
            this.closeDrawer();
        }

        // Hide original
        item.style.opacity = '0.3';
    }

    _updateDrag(e) {
        if (!this.dragGhost) return;
        this.dragState = 'DROP_TARGET';
        // Edge dwell: 26 px entry, 34 px exit (hysteresis).  The page changes
        // after 1000 ms while the finger stays in the edge strip; the drag ghost
        // remains attached and the new desktop is immediately a valid drop
        // target.  A visible edge indicator makes the intent clear.
        let edge = 0;
        if (this._dragEdge === -1 && e.clientX <= 34) edge = -1;
        else if (this._dragEdge === 1 && e.clientX >= innerWidth - 34) edge = 1;
        else if (e.clientX < 26) edge = -1;
        else if (e.clientX > innerWidth - 26) edge = 1;
        if (edge !== this._dragEdge) {
            clearTimeout(this._dragPageTimer);
            this._dragEdge = edge;
            document.body.classList.toggle('edge-dwell-left', edge === -1);
            document.body.classList.toggle('edge-dwell-right', edge === 1);
            if (edge) this._dragPageTimer = setTimeout(() => {
                if (!this.isDragging) return;
                const next = this.currentPage + edge;
                if (next >= 0 && next < this._pageCount()) {
                    this.currentPage = next; this._renderAppGrid();
                    if (window.NuxelWidgets) window.NuxelWidgets.renderPage(this.currentPage);
                    this.folderHover = null; this._positionedThisDrag = false;
                    this._dropIndex = -1;
                }
            }, 1000);
        }
        this.dragGhost.style.left = (e.clientX - 32) + 'px';
        this.dragGhost.style.top = (e.clientY - 32) + 'px';

        // Hit-test by live coordinates. `event.target` is the captured element
        // during a drag and cannot identify the tile under the finger.
        const under = document.elementFromPoint(e.clientX, e.clientY);
        const targetItem = under ? under.closest('.app-item') : null;
        if (targetItem && targetItem.closest('#app-list')) {
            const targetId = targetItem.dataset.appId;
            const rect = targetItem.getBoundingClientRect();
            const centered = Math.abs(e.clientX - (rect.left + rect.width / 2)) < rect.width * .24 &&
                             Math.abs(e.clientY - (rect.top + rect.height / 2)) < rect.height * .24;
            if (centered && targetId && targetId !== this.dragData.id) {
                if (!this.folderHover || this.folderHover.id !== targetId) this.folderHover = { id: targetId, since: Date.now() };
                if (Date.now() - this.folderHover.since >= 350) targetItem.classList.add('folder-target');
            } else {
                this.folderHover = null;
                document.querySelectorAll('.folder-target').forEach(el => el.classList.remove('folder-target'));
                this._insertAtTarget(targetItem, e.clientX, e.clientY);
            }
        } else if (under && under.closest('#app-grid')) {
            // Empty area of the current desktop: append at the end. This gives
            // "drop after the last icon" a deterministic meaning.
            this._insertAtEnd();
        }
    }

    _insertAtTarget(target, x, y) {
        const id = this.dragData && this.dragData.id, targetId = target.dataset.appId;
        if (!id || !targetId || id === targetId) return;
        const entries = this._entries();
        const targetIndex = entries.findIndex(entry => entry && entry.id === targetId);
        if (targetIndex < 0) return;
        const rect = target.getBoundingClientRect();
        const insertIndex = targetIndex + (y > rect.top + rect.height / 2 ? 1 : 0);
        if (this._positionedThisDrag && this._dropIndex === insertIndex) return;
        this.pageAssignments[id] = this.currentPage;
        this._ensureLayout().insertApp(id, insertIndex);
        this._dropIndex = insertIndex;
        this._positionedThisDrag = true;
        this._renderAppGrid();
    }

    _insertAtEnd() {
        const id = this.dragData && this.dragData.id;
        if (!id) return;
        const entries = this._entries();
        const pos = entries.length;
        if (this._positionedThisDrag && this._dropIndex === pos) return;
        this.pageAssignments[id] = this.currentPage;
        this._ensureLayout().insertApp(id, pos);
        this._dropIndex = pos;
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

    _endDrag(e, cancelled = false) {
        const snapshot = this._dragSnapshot;
        this.isDragging = false;
        clearTimeout(this._dragPageTimer); this._dragEdge = 0;
        document.body.classList.remove('edge-dwell-left', 'edge-dwell-right');
        this._releasePointer();

        if (this.dragData && this.dragData.el && this.dragData.el.isConnected) {
            this.dragData.el.style.opacity = '';
            this.dragData.el.classList.remove('dragging');
        }
        if (this.dragGhost) {
            this.dragGhost.remove();
            this.dragGhost = null;
        }

        document.body.classList.remove('launcher-dragging');
        const folder = document.querySelector('.folder-target');
        document.querySelectorAll('.app-item').forEach(el => el.classList.remove('drag-over', 'folder-target'));
        // Releasing outside the app grid is not a valid Home drop. Treat it as
        // a cancel so an accidental edge release cannot silently append.
        if (!cancelled && e && this.dragData) {
            const under = document.elementFromPoint(e.clientX, e.clientY);
            if (!under || !under.closest('#app-grid')) cancelled = true;
        }
        if (cancelled && snapshot) {
            this.hiddenAppIds = new Set(snapshot.hidden || []);
            this.layout = new window.NuxelHomeLayout(
                this._getOrderedApps().map(app => app.id), snapshot.layout || {});
            this.pageAssignments = Object.assign({}, snapshot.assignments || {});
            this.currentPage = snapshot.page;
        } else if (this.dragData) {
            const id = this.dragData.id;
            this.pageAssignments[id] = this.currentPage;
            if (e && this.desktopLayout) {
                const point = this._dropGridCoordinates(e.clientX, e.clientY);
                this.desktopLayout.move(id, this.currentPage, point.x, point.y);
            }
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
        if (!cancelled) this._saveLayout();
        this._renderAppGrid();
        this.dragData = null;
        this.folderHover = null;
        this._positionedThisDrag = false;
        this._dropIndex = -1;
        this._dragSnapshot = null;
        this.dragState = 'IDLE';
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
        const desktopLabel = (this.settings.desktopNames && this.settings.desktopNames[this.currentPage]) ||
            ('Desktop ' + (this.currentPage + 1));
        bar.innerHTML = '<button type="button" data-edit="size">Resize</button>' +
            '<button type="button" class="danger" data-edit="remove">Remove</button>' +
            '<button type="button" data-edit="move">Move</button>' +
            '<button type="button" data-edit="desktop">' + this._esc(desktopLabel) + '</button>' +
            '<button type="button" data-edit="done">Done</button>';
        bar.querySelector('[data-edit="size"]').onclick = () => this.toggleSelectedSize();
        bar.querySelector('[data-edit="remove"]').onclick = () => this.removeSelected();
        bar.querySelector('[data-edit="move"]').onclick = () => this.armMove();
        bar.querySelector('[data-edit="desktop"]').onclick = () => this.openDesktopPicker();
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
        this.moveArmed = false;
        document.body.classList.remove('launcher-editing', 'move-armed');
        const bar = document.getElementById('launcher-edit-toolbar');
        if (bar) bar.remove();
    }

    _esc(v) {
        return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
        });
    }

    armMove() {
        if (!this.selectedAppId) return;
        this.moveArmed = true;
        document.body.classList.add('move-armed');
        const item = document.querySelector('.app-item[data-app-id="' + CSS.escape(this.selectedAppId) + '"]');
        if (item) item.classList.add('selected-for-edit');
        try {
            if (window.NuxelOSD && typeof window.NuxelOSD.show === 'function') {
                window.NuxelOSD.show('Drag the highlighted icon to a new cell');
            }
        } catch (e) {}
        const bar = document.getElementById('launcher-edit-toolbar');
        if (bar) bar.querySelector('[data-edit="move"]').textContent = 'Drag now…';
    }

    openDesktopPicker() {
        if (!this.selectedAppId) return;
        let menu = document.getElementById('nuxel-desktop-picker');
        if (!menu) {
            menu = document.createElement('div');
            menu.id = 'nuxel-desktop-picker';
            menu.className = 'launcher-edit-toolbar desktop-picker';
            document.body.appendChild(menu);
        }
        menu.replaceChildren();
        const count = Number(this.settings.desktopCount) || 2;
        for (let i = 0; i < count; i++) {
            const b = document.createElement('button');
            b.type = 'button';
            const name = (this.settings.desktopNames && this.settings.desktopNames[i]) || ('Desktop ' + (i + 1));
            b.textContent = name;
            b.onclick = () => {
                this._moveSelectedToDesktop(i);
                menu.remove();
            };
            menu.appendChild(b);
        }
    }

    _moveSelectedToDesktop(desktopIndex) {
        const id = this.selectedAppId;
        if (!id || !this.desktopLayout) return;
        const moved = this.desktopLayout.move(id, desktopIndex, 0, 0);
        if (moved) {
            this.pageAssignments[id] = desktopIndex;
            this._saveLayout();
            this._renderAll();
            this._selectForEdit(id);
        }
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

    openDrawer() {
        if (this.drawerOpen) return;
        this.drawerOpen = true;
        document.body.classList.add('app-drawer-open');
        this._renderDrawerApps();
        const grid = document.getElementById('app-grid');
        if (grid) { this._homeScrollTop = grid.scrollTop; grid.scrollTop = 0; }
        if (this.drawerList) {
            this.drawerList.hidden = false;
            // The opening gesture must never be replayed into the newly visible
            // scroller.  A 250 ms settle window absorbs WebKit's residual
            // touch/kinetic deltas; a fresh pointer sequence scrolls normally.
            this.drawerList.scrollTop = 0;
            this._drawerOpenGuardUntil = Date.now() + 250;
        }
        if (this.appList) this.appList.hidden = true;
        this._updatePageDots(this._pageCount());
        if (window.NuxelWidgets) { try { window.NuxelWidgets.renderPage(this.currentPage); } catch (e) {} }
        try { document.dispatchEvent(new CustomEvent('nuxel:overlay-changed')); } catch (e) {}
    }
    closeDrawer() {
        const wasOpen = this.drawerOpen;
        this.drawerOpen = false;
        document.body.classList.remove('app-drawer-open');
        const menu = document.getElementById('nuxel-drawer-context'); if (menu) menu.remove();
        if (this.drawerList) this.drawerList.hidden = true;
        if (this.appList) this.appList.hidden = false;
        if (wasOpen) {
            const grid = document.getElementById('app-grid');
            if (grid) grid.scrollTop = this._homeScrollTop || 0;
        }
        try { document.dispatchEvent(new CustomEvent('nuxel:overlay-changed')); } catch (e) {}
    }
    advanceDrawer() { if (!this.drawerOpen) this.openDrawer(); }

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
        const grid = document.getElementById('app-grid');
        if (grid) {
            grid.style.setProperty('--page-slide-from', dx > 0 ? '22px' : '-22px');
            grid.classList.remove('page-changing');
            void grid.offsetWidth; // restart transition only for completed desktop swipes
            grid.classList.add('page-changing');
            clearTimeout(this._pageAnimationTimer);
            this._pageAnimationTimer = setTimeout(() => grid.classList.remove('page-changing'), 250);
        }
        this._renderAppGrid();
    }

    refresh() {
        this._renderAll();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.launcher = new Launcher();
});
