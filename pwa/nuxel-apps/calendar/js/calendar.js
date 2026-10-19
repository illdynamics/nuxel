// Helper: wrap the shared bridge call with a graceful offline fallback.
async function nuxelBridgeCall(namespace, verb, params, fallback) {
    try {
        const b = window.NuxelBridge;
        if (!b) { window.__nuxelBridgeOffline = true; return fallback; }
        const res = await b.call(namespace, verb, params);
        if (!res || res.success === false) { window.__nuxelBridgeOffline = true; return fallback; }
        window.__nuxelBridgeOffline = false;
        return res;
    } catch (e) { window.__nuxelBridgeOffline = true; return fallback; }
}

function nuxelBridgeOfflineBanner() {
    if (!window.__nuxelBridgeOffline) return;
    if (document.getElementById('bridge-offline-banner')) return;
    const el = document.createElement('div');
    el.id = 'bridge-offline-banner';
    el.textContent = '🔌 Bridge offline — showing local data';
    el.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:#ef6c00;color:#fff;font-size:13px;padding:6px 12px;z-index:9999;text-align:center;';
    document.body.appendChild(el);
}

// Nuxel Calendar - Full Calendar PWA

class CalendarApp {
    constructor() {
        this.currentDate = new Date();
        this.selectedDate = new Date();
        this.events = [];
        this.viewDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
        this.calendarPermission = 'prompt';  // 'prompt', 'granted', 'denied'
        this.portalAvailable = false;

        this._init();
    }

    async _init() {
        // Bind controls before any optional portal call.  A missing local portal
        // must never leave Calendar looking alive while every button is inert.
        this._bindEvents();
        await this._checkCalendarPermission();
        await this._loadEvents();
        this._render();
    }

    /**
     * Check calendar permission status via D-Bus portal.
     * On first launch, requests permission via the nuxel-portal daemon.
     * Falls back to local-only mode if portal is unavailable or permission is denied.
     */
    async _checkCalendarPermission() {
        try {
            // Try the native D-Bus bridge via the portal API
            const stored = localStorage.getItem('nuxel-calendar-permission');
            if (stored === 'granted') {
                this.calendarPermission = 'granted';
                this.portalAvailable = true;
                console.log('[Calendar] Permission already granted (cached)');
                this._updatePermissionUI();
                return;
            }

            // Attempt portal request via the nuxel-bridge Web API
            if (window.nuxelBridge && typeof window.nuxelBridge.requestPermission === 'function') {
                const result = await window.nuxelBridge.requestPermission('calendar');
                if (result && result.granted) {
                    this.calendarPermission = 'granted';
                    this.portalAvailable = true;
                    localStorage.setItem('nuxel-calendar-permission', 'granted');
                    console.log('[Calendar] Calendar permission granted via bridge');
                } else {
                    this.calendarPermission = 'denied';
                    this.portalAvailable = false;
                    localStorage.setItem('nuxel-calendar-permission', 'denied');
                    console.log('[Calendar] Calendar permission denied');
                }
            } else {
                // No bridge available — try D-Bus via fetch to local portal HTTP endpoint
                const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
                const timeout = setTimeout(() => { if (controller) controller.abort(); }, 1800);
                const response = await fetch('http://127.0.0.1:4678/portal/calendar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    signal: controller && controller.signal,
                    body: JSON.stringify({
                        app_id: 'org.nuxel.Calendar',
                        action: 'request'
                    })
                });
                clearTimeout(timeout);
                if (response.ok) {
                    const result = await response.json();
                    if (result.granted) {
                        this.calendarPermission = 'granted';
                        this.portalAvailable = true;
                        localStorage.setItem('nuxel-calendar-permission', 'granted');
                    } else {
                        this.calendarPermission = 'denied';
                        localStorage.setItem('nuxel-calendar-permission', 'denied');
                    }
                } else {
                    // Portal HTTP endpoint not available — fall back to local-only
                    console.log('[Calendar] Portal HTTP endpoint not available. Running in local-only mode.');
                    this.calendarPermission = 'denied';
                    this.portalAvailable = false;
                }
            }
        } catch (e) {
            // Portal not available — this is expected when running as a plain PWA
            // without the Nuxel bridge. Calendar runs in local-only mode.
            console.log('[Calendar] Portal not available:', e.message);
            console.log('[Calendar] Running in local-only mode (permission: denied)');
            this.calendarPermission = 'denied';
            this.portalAvailable = false;
        }

        this._updatePermissionUI();
    }

    /**
     * Update the UI to reflect current calendar permission status.
     * Shows a permission banner when denied, hides it when granted.
     */
    _updatePermissionUI() {
        const banner = document.getElementById('permission-banner');
        const statusIndicator = document.getElementById('permission-status');

        if (!banner) return;  // UI not rendered yet

        if (this.calendarPermission === 'granted') {
            banner.classList.add('hidden');
            if (statusIndicator) {
                statusIndicator.textContent = 'Calendar access granted';
                statusIndicator.className = 'permission-granted';
            }
        } else if (this.calendarPermission === 'denied') {
            if (!this.portalAvailable) {
                // Portal unavailable — show info banner, not error
                banner.classList.remove('hidden');
                banner.className = 'permission-banner info';
                document.getElementById('permission-text').textContent =
                    'Local-only mode: Calendar data is stored on this device only. ' +
                    'Install the Nuxel portal service for cross-app calendar sync.';
                if (statusIndicator) {
                    statusIndicator.textContent = 'Local storage only';
                    statusIndicator.className = 'permission-denied';
                }
            } else {
                // User explicitly denied
                banner.classList.remove('hidden');
                banner.className = 'permission-banner warning';
                document.getElementById('permission-text').textContent =
                    'Calendar access denied. Events are stored locally on this device.';
                if (statusIndicator) {
                    statusIndicator.textContent = 'Permission denied — local only';
                    statusIndicator.className = 'permission-denied';
                }
            }
        }
    }

    /**
     * Request calendar access again (e.g., user clicks "Enable" in the banner).
     */
    async _requestCalendarAccess() {
        localStorage.removeItem('nuxel-calendar-permission');
        await this._checkCalendarPermission();
    }

    _render() {
        this._renderPermissionBanner();
        this._renderMonth();
        this._renderEvents();
        this._updateTitle();
    }

    _renderPermissionBanner() {
        const container = document.getElementById('app-container');
        if (!container) return;

        // Remove existing banner if any
        const existing = document.getElementById('permission-banner');
        if (existing) existing.remove();

        const banner = document.createElement('div');
        banner.id = 'permission-banner';
        banner.className = 'permission-banner hidden';

        const icon = document.createElement('span');
        icon.className = 'permission-icon';
        icon.textContent = '🔒';
        banner.appendChild(icon);

        const text = document.createElement('span');
        text.id = 'permission-text';
        text.className = 'permission-text';
        text.textContent = '';
        banner.appendChild(text);

        const enableBtn = document.createElement('button');
        enableBtn.id = 'permission-enable-btn';
        enableBtn.className = 'permission-enable-btn';
        enableBtn.textContent = 'Enable';
        enableBtn.addEventListener('click', () => this._requestCalendarAccess());
        banner.appendChild(enableBtn);

        container.insertBefore(banner, container.firstChild);

        this._updatePermissionUI();
    }

    _renderMonth() {
        const grid = document.getElementById('day-grid');
        const year = this.viewDate.getFullYear();
        const month = this.viewDate.getMonth();
        
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const daysInPrev = new Date(year, month, 0).getDate();
        
        // Adjust for Monday start (0=Sunday -> shift)
        const startOffset = firstDay === 0 ? 6 : firstDay - 1;
        
        const today = new Date();
        const todayStr = `${today.getFullYear()}-${today.getMonth()}-${today.getDate()}`;
        const selectedStr = `${this.selectedDate.getFullYear()}-${this.selectedDate.getMonth()}-${this.selectedDate.getDate()}`;
        
        let cells = [];
        
        // Previous month days
        for (let i = startOffset - 1; i >= 0; i--) {
            const day = daysInPrev - i;
            const date = new Date(year, month - 1, day);
            cells.push(this._createDayCell(day, true, date, todayStr, selectedStr));
        }
        
        // Current month days
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(year, month, day);
            cells.push(this._createDayCell(day, false, date, todayStr, selectedStr));
        }
        
        // Next month days
        const remaining = 42 - cells.length;
        for (let day = 1; day <= remaining; day++) {
            const date = new Date(year, month + 1, day);
            cells.push(this._createDayCell(day, true, date, todayStr, selectedStr));
        }

        grid.innerHTML = cells.join('');
        
        // Bind click events
        grid.querySelectorAll('.day-cell').forEach(cell => {
            cell.addEventListener('click', () => {
                const d = new Date(parseInt(cell.dataset.year), parseInt(cell.dataset.month), parseInt(cell.dataset.day));
                this.selectedDate = d;
                this._renderMonth();
                this._renderEvents();
            });
        });
    }

    _createDayCell(day, otherMonth, date, todayStr, selectedStr) {
        const dateStr = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
        const isToday = dateStr === todayStr;
        const isSelected = dateStr === selectedStr;
        const hasEvents = this._hasEvents(date);
        
        let cls = 'day-cell';
        if (otherMonth) cls += ' other-month';
        if (isToday) cls += ' today';
        if (isSelected) cls += ' selected';
        if (hasEvents) cls += ' has-events';
        
        return `<div class="${cls}" data-day="${day}" data-month="${date.getMonth()}" data-year="${date.getFullYear()}">${day}</div>`;
    }

    _renderEvents() {
        const list = document.getElementById('events-list');
        const dateStr = this._formatDateStr(this.selectedDate);
        document.getElementById('selected-date').textContent = 
            this.selectedDate.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
        
        const dayEvents = this.events.filter(e => e.date === dateStr);
        
        if (dayEvents.length === 0) {
            list.innerHTML = '<div class="empty-state">No events</div>';
            return;
        }
        
        dayEvents.sort((a, b) => (a.startTime || '00:00').localeCompare(b.startTime || '00:00'));
        
        list.innerHTML = dayEvents.map((ev, i) => `
            <div class="event-item" data-index="${i}" style="border-left-color: ${ev.color || '#E91E63'}">
                <div class="event-time">${ev.startTime || 'All day'}${ev.endTime ? ` - ${ev.endTime}` : ''}</div>
                <div class="event-title">${this._escapeHtml(ev.title)}</div>
            </div>
        `).join('');
        
        list.querySelectorAll('.event-item').forEach(item => {
            item.addEventListener('click', () => {
                const idx = parseInt(item.dataset.index);
                const ev = dayEvents[idx];
                this._editEvent(ev);
            });
        });
    }

    _updateTitle() {
        const label = this.viewDate.toLocaleDateString([], { month: 'long', year: 'numeric' });
        document.getElementById('cal-title').textContent = label;
        document.getElementById('month-label').textContent = label;
    }

    _bindEvents() {
        document.getElementById('prev-month').addEventListener('click', () => {
            this.viewDate.setMonth(this.viewDate.getMonth() - 1);
            this._render();
        });
        document.getElementById('next-month').addEventListener('click', () => {
            this.viewDate.setMonth(this.viewDate.getMonth() + 1);
            this._render();
        });
        document.getElementById('today-btn').addEventListener('click', () => {
            this.viewDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
            this.selectedDate = new Date();
            this._render();
        });
        document.getElementById('add-event-btn').addEventListener('click', () => this._openEditor());
        
        // Editor buttons
        document.getElementById('editor-back').addEventListener('click', () => this._closeEditor());
        document.getElementById('editor-save').addEventListener('click', () => this._saveEvent());

        // Color picker
        document.querySelectorAll('.color-opt').forEach(el => {
            el.addEventListener('click', () => {
                document.querySelectorAll('.color-opt').forEach(c => c.classList.remove('selected'));
                el.classList.add('selected');
            });
        });
    }

    _openEditor(event = null) {
        const editor = document.getElementById('event-editor');
        editor.classList.remove('hidden');
        
        if (event) {
            document.getElementById('editor-title').textContent = 'Edit Event';
            document.getElementById('event-title').value = event.title;
            document.getElementById('event-date').value = event.date;
            document.getElementById('event-start').value = event.startTime || '';
            document.getElementById('event-end').value = event.endTime || '';
            document.getElementById('event-desc').value = event.description || '';
            document.getElementById('editor-save').dataset.editId = event.id;
            
            // Select color
            document.querySelectorAll('.color-opt').forEach(c => {
                c.classList.toggle('selected', c.dataset.color === (event.color || '#E91E63'));
            });
        } else {
            document.getElementById('editor-title').textContent = 'New Event';
            document.getElementById('event-title').value = '';
            document.getElementById('event-date').value = this._formatDateStr(this.selectedDate);
            document.getElementById('event-start').value = '';
            document.getElementById('event-end').value = '';
            document.getElementById('event-desc').value = '';
            document.getElementById('editor-save').dataset.editId = '';
            document.querySelector('.color-opt:first-child').classList.add('selected');
        }
    }

    _saveEvent() {
        const title = document.getElementById('event-title').value.trim();
        if (!title) { alert('Please enter a title'); return; }
        
        const selectedColor = document.querySelector('.color-opt.selected');
        const color = selectedColor ? selectedColor.dataset.color : '#E91E63';
        const editId = document.getElementById('editor-save').dataset.editId;
        
        const event = {
            id: editId || `evt-${Date.now()}`,
            title: title,
            date: document.getElementById('event-date').value,
            startTime: document.getElementById('event-start').value,
            endTime: document.getElementById('event-end').value,
            description: document.getElementById('event-desc').value,
            color: color,
            createdAt: new Date().toISOString(),
        };

        if (editId) {
            const idx = this.events.findIndex(e => e.id === editId);
            if (idx >= 0) this.events[idx] = event;
        } else {
            this.events.push(event);
        }

        this._saveEvents();
        this._closeEditor();
        this._renderEvents();
        this._renderMonth();
    }

    _editEvent(event) {
        this._openEditor(event);
    }

    _closeEditor() {
        document.getElementById('event-editor').classList.add('hidden');
        // Calendar is hosted in the same-origin launcher frame.  Hiding the
        // editor must also dismiss its launcher-owned touch keyboard.
        try {
            if (window.parent && window.parent.NuxelTouchKeyboard) window.parent.NuxelTouchKeyboard.hide();
        } catch (e) { /* standalone Calendar has no parent keyboard */ }
    }

    _hasEvents(date) {
        const dateStr = this._formatDateStr(date);
        return this.events.some(e => e.date === dateStr);
    }

    _formatDateStr(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    }

    async _loadEvents() {
        const fallback = () => {
            try {
                const raw = localStorage.getItem('nuxel-calendar-events');
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                return [];
            }
        };
        try {
            const res = await nuxelBridgeCall('caldav', 'list', { app_id: 'org.nuxel.Calendar' }, null);
            if (res && Array.isArray(res.events)) {
                this.events = res.events;
            } else {
                this.events = fallback();
            }
            nuxelBridgeOfflineBanner();
        } catch (e) {
            this.events = fallback();
        }
    }

    _saveEvents() {
        try {
            localStorage.setItem('nuxel-calendar-events', JSON.stringify(this.events));
        } catch (e) {
            console.warn('Failed to save events locally:', e);
        }
        nuxelBridgeCall('caldav', 'put', { app_id: 'org.nuxel.Calendar', events: this.events }, null);
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

/**
 * Permission banner styles — injected via JS for self-contained PWA.
 */
(function injectPermissionStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .permission-banner {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 8px;
            margin: 4px 8px;
            font-size: 13px;
            transition: all 0.3s ease;
        }
        .permission-banner.warning {
            background: rgba(255, 87, 34, 0.1);
            border: 1px solid rgba(255, 87, 34, 0.3);
            color: #FF5722;
        }
        .permission-banner.info {
            background: rgba(33, 150, 243, 0.1);
            border: 1px solid rgba(33, 150, 243, 0.3);
            color: #2196F3;
        }
        .permission-banner.hidden {
            display: none;
        }
        .permission-icon {
            flex-shrink: 0;
            font-size: 16px;
        }
        .permission-text {
            flex: 1;
            line-height: 1.3;
        }
        .permission-enable-btn {
            flex-shrink: 0;
            padding: 4px 12px;
            border: none;
            border-radius: 4px;
            background: #2196F3;
            color: white;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
        }
        .permission-enable-btn:hover {
            background: #1976D2;
        }
        .permission-granted {
            color: #4CAF50;
            font-size: 11px;
            font-weight: 500;
        }
        .permission-denied {
            color: #FF9800;
            font-size: 11px;
            font-weight: 500;
        }
        #permission-status {
            text-align: center;
            padding: 4px;
            margin: 0 8px;
        }
    `;
    document.head.appendChild(style);
})();

document.addEventListener('DOMContentLoaded', () => {
    window.calApp = new CalendarApp();
});
