// Nuxel Status Bar — v0.3.3-alpha
// Real-wired to the HTTP bridge (/api/v1/phone/status) and to the same
// notification JSON source the daemon persists (/var/lib/nuxel/notifications.json,
// surfaced via the bridge as `notifications/list`). Polls every 5 seconds in
// dev, resilient to bridge failures.

class StatusBar {
    constructor() {
        this.state = {
            signalLevel: 4,
            signalMax: 4,
            mobileNetwork: false,
            operator: '',
            wifiConnected: false,
            batteryLevel: 100,
            batteryCharging: true,
        };

        this.state.notifications = [];
        this.elements = {
            time: document.getElementById('status-time'),
            signal: document.getElementById('status-signal'),
            wifi: document.getElementById('status-wifi'),
            battery: document.getElementById('status-battery'),
            batteryPct: document.getElementById('status-battery-pct'),
        };
        this._notificationElements = {
            button: null,
            badge: null,
            panel: null,
        };
        this._notifPollTimer = null;
        this._pollTimer = null;
        this._init();
    }

    _init() {
        this._updateTime();
        this._renderBattery();
        this._renderSignal();
        this._renderWifi();
        this._buildNotificationsUI();

        // Update local time every second (no bridge needed)
        setInterval(() => this._updateTime(), 1000);

        // Poll phone status every 5 seconds (dev mode)
        this._pollPhoneStatus();
        this._pollTimer = setInterval(() => this._pollPhoneStatus(), 5000);

        // Poll notifications from the same JSON source (canonical
        // /var/lib/nuxel/notifications.json surfaced via the bridge).
        this._pollNotifications();
        this._notifPollTimer = setInterval(() => this._pollNotifications(), 5000);

        // Listen for bridge push events if available
        if (typeof bridge !== 'undefined' && bridge.on) {
            bridge.on('status:update', (data) => this._onStatusUpdate(data));
        }
    }

    _updateTime() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        if (this.elements.time) {
            this.elements.time.textContent = hours + ':' + minutes;
        }
    }

    _renderSignal() {
        if (!this.elements.signal) return;
        const barsCount = 4;
        const activeBars = Math.max(1, Math.round(
            (this.state.signalLevel / this.state.signalMax) * barsCount
        ));

        let html = '<span class="signal-bars">';
        for (let i = 0; i < barsCount; i++) {
            const active = i < activeBars ? 'active' : '';
            html += '<span class="signal-bar ' + active + '"></span>';
        }
        html += '</span>';
        this.elements.signal.innerHTML = html;
    }

    _renderWifi() {
        if (!this.elements.wifi) return;
        if (this.state.wifiConnected) {
            this.elements.wifi.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4CAF50" stroke-width="2"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1" fill="#4CAF50" stroke="none"/></svg>';
            this.elements.wifi.style.opacity = '1';
        } else {
            this.elements.wifi.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="2"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1" fill="#666" stroke="none"/></svg>';
            this.elements.wifi.style.opacity = '0.4';
        }
    }

    _renderBattery() {
        if (!this.elements.battery) return;
        const level = Math.max(0, Math.min(100, this.state.batteryLevel));
        const charging = this.state.batteryCharging;

        let levelClass = '';
        if (level <= 10) levelClass = 'critical';
        else if (level <= 20) levelClass = 'warning';

        const width = Math.max(2, (level / 100) * 18);
        this.elements.battery.innerHTML = '<span class="battery-icon' + (charging ? ' charging' : '') + '"><span class="battery-level ' + levelClass + '" style="width: ' + width + 'px"></span>' + (charging ? '<span class="charging-indicator">⚡</span>' : '') + '</span>';
        if (this.elements.batteryPct) {
            this.elements.batteryPct.textContent = level + '%';
        }
    }

    async _pollPhoneStatus() {
        try {
            if (typeof bridge === 'undefined' || !bridge.getPhoneStatus) {
                console.warn('StatusBar: bridge not available for phone status');
                return;
            }
            const status = await bridge.getPhoneStatus();
            this._onStatusUpdate(status);
        } catch (e) {
            console.warn('StatusBar: phone status poll failed:', e.message || e);
        }
    }

    _onStatusUpdate(status) {
        if (!status) return;

        // Update time from backend if provided (takes priority over local JS clock)
        if (status.time && this.elements.time) {
            this.elements.time.textContent = status.time;
        }

        // Battery
        if (status.battery) {
            const level = Number(status.battery.level ?? this.state.batteryLevel);
            const charging = Boolean(status.battery.charging);
            this.state.batteryLevel = Math.max(0, Math.min(100, level));
            this.state.batteryCharging = charging;
        }

        // Modem / cellular
        if (status.modem && status.modem.connected) {
            const signalQuality = Number(status.modem.signal_quality || 0);
            this.state.signalLevel = Math.round((signalQuality / 100) * this.state.signalMax);
            this.state.mobileNetwork = true;
            this.state.operator = status.modem.operator || '';
        } else if (status.network && status.network.connected) {
            // Fallback to network signal for VM/ethernet
            const networkSignal = Number(status.network.signal ?? 4);
            this.state.signalLevel = Math.max(0, Math.min(this.state.signalMax, networkSignal));
            this.state.mobileNetwork = false;
            this.state.operator = status.network.operator || '';
        } else {
            this.state.signalLevel = 0;
            this.state.mobileNetwork = false;
        }

        // Network / WiFi / Ethernet
        if (status.network && status.network.connected) {
            this.state.wifiConnected = Boolean(
                status.network.wifi_enabled ||
                status.network.type === 'wifi' ||
                status.network.type === 'ethernet' ||
                status.vm_mode
            );
        } else {
            this.state.wifiConnected = false;
        }

        this._renderSignal();
        this._renderWifi();
        this._renderBattery();
    }

    // ---- Notifications (same JSON source as the daemon) ----
    // Build a bell indicator + dropdown in the status bar right cluster,
    // populated from bridge.getNotifications() which mirrors the canonical
    // /var/lib/nuxel/notifications.json persisted by the daemon.

    _buildNotificationsUI() {
        const right = document.querySelector('.status-right');
        if (!right) return;
        if (this._notificationElements.button) return;

        const wrap = document.createElement('div');
        wrap.className = 'status-icon status-notification';
        wrap.style.cssText = 'position:relative;width:16px;height:16px;display:inline-flex;cursor:pointer;';
        wrap.title = 'Notifications';
        wrap.innerHTML =
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
            '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>';
        const badge = document.createElement('span');
        badge.className = 'status-notif-badge';
        badge.style.cssText =
            'position:absolute;top:-5px;right:-7px;min-width:15px;height:15px;border-radius:8px;' +
            'background:#ef4444;color:#fff;font-size:9px;font-weight:700;display:none;' +
            'align-items:center;justify-content:center;padding:0 3px;';
        badge.textContent = '0';
        wrap.appendChild(badge);
        wrap.setAttribute('role', 'button');
        wrap.setAttribute('aria-haspopup', 'true');
        wrap.addEventListener('click', (e) => { e.stopPropagation(); this._toggleNotificationsPanel(); });
        right.appendChild(wrap);

        this._notificationElements.button = wrap;
        this._notificationElements.badge = badge;
    }

    async _pollNotifications() {
        try {
            if (typeof bridge === 'undefined' || !bridge.getNotifications) {
                return;
            }
            const res = await bridge.getNotifications();
            const list = (res && res.notifications && Array.isArray(res.notifications))
                ? res.notifications
                : [];
            this._setNotifications(list);
        } catch (e) {
            console.warn('StatusBar: notification poll failed:', e.message || e);
        }
    }

    _setNotifications(notifications) {
        if (!Array.isArray(notifications)) notifications = [];
        this.state.notifications = notifications;
        this._renderNotificationsBadge();
        this._renderNotificationsPanel();
    }

    _renderNotificationsBadge() {
        const badge = this._notificationElements.badge;
        if (!badge) return;
        const count = this.state.notifications.length;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : String(count);
            badge.style.display = 'inline-flex';
        } else {
            badge.style.display = 'none';
        }
    }

    _toggleNotificationsPanel() {
        const panel = this._notificationElements.panel;
        if (!panel) {
            this._renderNotificationsPanel();
        }
        const p = this._notificationElements.panel;
        if (p) {
            const hidden = p.classList.toggle('open');
            if (hidden) {
                const closeListener = (ev) => {
                    if (!p.contains(ev.target)) { p.classList.remove('open'); document.removeEventListener('click', closeListener); }
                };
                document.addEventListener('click', closeListener);
            }
        }
    }

    _renderNotificationsPanel() {
        const button = this._notificationElements.button;
        if (!button) return;
        let panel = this._notificationElements.panel;
        if (!panel) {
            panel = document.createElement('div');
            panel.className = 'status-notif-panel';
            panel.style.cssText =
                'position:fixed;top:calc(var(--status-bar-height,40px) + 6px);right:14px;' +
                'min-width:280px;max-width:92vw;max-height:70vh;overflow-y:auto;' +
                'background:rgba(26,26,46,0.98);backdrop-filter:blur(16px);border:1px solid ' +
                'rgba(255,255,255,0.08);border-radius:14px;box-shadow:0 16px 48px rgba(0,0,0,0.5);' +
                'color:var(--text-primary, #e8e8f0);z-index:120;padding:10px 0;display:none;';
            document.body.appendChild(panel);
            this._notificationElements.panel = panel;
        }
        const notifs = this.state.notifications || [];
        if (notifs.length === 0) {
            panel.innerHTML = '<div style="padding:18px 20px;font-size:13px;color:var(--text-secondary,#9a9ab0);text-align:center;">No notifications</div>';
        } else {
            let html = '<div style="padding:4px 16px 10px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-secondary,#9a9ab0);">Notifications</div>';
            notifs.forEach((n) => {
                const app = String(n.app_id || n.app_name || 'System');
                const title = String(n.summary || n.title || '');
                const body = String(n.body || '');
                const time = n.timestamp ? new Date(n.timestamp) : null;
                const tstr = time && !isNaN(time.getTime())
                    ? String(time.getHours()).padStart(2, '0') + ':' + String(time.getMinutes()).padStart(2, '0')
                    : '';
                html +=
                    '<div class="status-notif-item" style="display:flex;gap:10px;padding:9px 16px;border-bottom:1px solid rgba(255,255,255,0.05);cursor:default;">' +
                    '<div style="flex:1;min-width:0;"><div style="font-size:12px;font-weight:600;' +
                    'color:var(--text-accent,#7aa2ff);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
                    escapeHtml(app) + '</div>' +
                    (title ? '<div style="font-size:13px;font-weight:600;margin-top:1px;">' + escapeHtml(title) + '</div>' : '') +
                    (body ? '<div style="font-size:12px;color:var(--text-secondary,#9a9ab0);margin-top:2px;' +
                    'overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">' +
                    escapeHtml(body) + '</div>' : '') +
                    '</div>' +
                    (tstr ? '<div style="font-size:10px;color:var(--text-secondary,#9a9ab0);white-space:nowrap;">' + tstr + '</div>' : '') +
                    '</div>';
            });
            panel.innerHTML = html;
        }
    }

    setBatteryLevel(level, charging) {
        this.state.batteryLevel = Math.max(0, Math.min(100, level ?? 100));
        this.state.batteryCharging = !!charging;
        this._renderBattery();
    }

    setSignalLevel(level) {
        this.state.signalLevel = Math.max(0, Math.min(this.state.signalMax, level ?? 0));
        this._renderSignal();
    }

    setWifiConnected(connected) {
        this.state.wifiConnected = !!connected;
        this._renderWifi();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.statusBar = new StatusBar();
});


function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
}
