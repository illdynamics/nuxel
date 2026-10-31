// Nuxel Status Bar — v0.7.4-beta
//
// SINGLE SOURCE OF TRUTH (briq-02d).  The handset used to serve a stale
// v0.3.2 copy of this file while the repo (and the UTM VM) was on v0.4.x, so the
// phone silently ran older status-bar behaviour than the build everyone tested.
// The version below is now a machine-readable constant that the launcher reports
// on its own evidence channel and that
// tools/s10plus/a33/tests/launcher-registry-test.js asserts against the repo - a
// stale device copy is therefore DETECTED instead of tolerated, and the service
// worker cache key (sw.js CACHE_VERSION) is bumped for the same revision so a
// stale cached bundle is invalidated deterministically.
// Real-wired to the HTTP bridge (/api/v1/phone/status) and to the same
// notification JSON source the daemon persists (/var/lib/nuxel/notifications.json,
// surfaced via the bridge as `notifications/list`). Polls every 5 seconds in
// dev, resilient to bridge failures.

class StatusBar {
    // Keep in sync with manifest.json ("nuxel.pwa_version") and sw.js
    // (CACHE_VERSION) - the registry test fails if the three ever diverge.
    static get VERSION() { return '0.7.4-beta'; }

    constructor() {
        this.state = {
            // Never draw a carrier signal merely because Home has not received
            // a hardware report yet.  In particular, a generic ethernet/Wi-Fi
            // connection is not evidence of a registered modem or inserted SIM.
            signalLevel: 0,
            signalMax: 4,
            mobileNetwork: false,
            cellularState: 'unknown',
            operator: '',
            wifiConnected: false,
            wifiState: 'unavailable',
            // Bluetooth is a real radio fact, independent of Wi-Fi.  null is
            // UNKNOWN: the indicator stays hidden until a hardware-backed
            // reading says the adapter is powered.
            bluetoothOn: null,
            bluetoothState: 'unknown',
            bluetoothDiscovering: false,
            bluetoothAddress: '',
            batteryLevel: null,
            batteryCharging: false,
            batteryCapacityUah: null,
            batteryDesignCapacityUah: null,
            // Location is a provider fact, independent of the privacy toggle.
            // state 'unknown' keeps the glyph hidden until the bridge answers.
            locationState: 'unknown',
            locationKind: null,
            locationSource: null,
            locationEnabled: false,
            locationAge: null,
            locationAccuracy: null,
            soundMode: 'unknown',
            // Canonical single-owner system indicator snapshot (same data the
            // lockscreen consumes).  null means UNKNOWN, never a guessed OFF.
            indicators: null,
            usbLabel: '',
        };
        /* The same 100% -> 0% guard the lockscreen uses.  A one-sample gauge
           reset must not replace a known-good reading. */
        this._batteryZeroCount = 0;
        this._batteryBigCandidate = null;
        this._batteryBigCount = 0;
        this._batteryRenderKey = '';

        this.state.notifications = [];
        this.elements = {
            time: document.getElementById('status-time'),
            signal: document.getElementById('status-signal'),
            wifi: document.getElementById('status-wifi'),
            bluetooth: document.getElementById('status-bluetooth'),
            location: document.getElementById('status-location'),
            sound: document.getElementById('status-sound'),
            usb: document.getElementById('status-usb'),
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
        this.batteryStyle = 'inside';
        this._init();
        this._pubVersion();
    }

    // Evidence marker: STATE channel + diag hook, so the live console and the VM
    // can both be asked "which status-bar revision is actually running?".
    _pubVersion() {
        const line = 'STATUSBAR_READY version=' + StatusBar.VERSION + ' safezones=' +
                     (typeof NuxelSafeZones !== 'undefined' ? 'present' : 'absent');
        try {
            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.nuxelDiag) {
                window.webkit.messageHandlers.nuxelDiag.postMessage(line);
            }
            if (window.NuxelHost && window.NuxelHost.available && window.NuxelHost.statusRead) {
                // read-only poll: publishing happens host-side for the services
            }
            console.log('[status-bar] ' + line);
        } catch (e) { /* evidence must never break the bar */ }
        try { window.NUXEL_STATUS_BAR_VERSION = StatusBar.VERSION; } catch (e) {}
    }

    _init() {
        this._updateTime();
        this._renderBattery();
        // The native page host can read the fuel gauge before the HTTP bridge
        // has finished waiting for network-online.target.  Hydrate from that
        // kernel-backed path immediately so boot never invents a charge state
        // or leaves a real reading hidden for tens of seconds.
        this._hydrateBatteryFromHost();
        this._renderSignal();
        this._renderWifi();
        this._renderBluetooth();
        this._buildNotificationsUI();
        // A34 TOUCHDOWN: the Quick Settings panel has always listened for
        // `gesture:qs`, but nothing in the launcher ever dispatched it (measured
        // on the handset: the handler existed and the pull-down did nothing).
        // Wire the gesture to the REAL status bar; no layout or visual change.
        this._bindQuickSettingsGesture();

        // Update local time every second (no bridge needed)
        // HH:MM only needs a minute cadence.  The old 1 s timer woke the
        // WebProcess 60x/min to rewrite identical text.
        this._scheduleClock();

        // Poll phone status slowly; these are provider/daemon states, not
        // frame-rate signals.  Every read is skipped while covered by the
        // lockscreen and refreshed on unlock.
        this._pollPhoneStatus();
        this._pollBluetooth();
        this._pollTimer = setInterval(() => { if (!this._statusInactive()) this._pollPhoneStatus(); }, 15000);
        this._pollLocation();
        this._locationPollTimer = setInterval(() => {
            if (!this._statusInactive()) this._pollLocation();
        }, 10000);
        // Sound mode + wired USB/file-transfer/console state.  One canonical
        // in-process read; no second high-frequency poller is created.
        this._pollSystemIndicators();
        this._indicatorPollTimer = setInterval(() => {
            if (!this._statusInactive()) this._pollSystemIndicators();
        }, 10000);

        // Poll notifications from the same JSON source (canonical
        // /var/lib/nuxel/notifications.json surfaced via the bridge).
        this._pollNotifications();
        this._notifPollTimer = setInterval(() => { if (!this._statusInactive()) this._pollNotifications(); }, 20000);
        // A wake is an event: refresh immediately instead of waiting a poll.
        document.addEventListener('nuxel:display-on', () => {
            this._updateTime();
            this._hydrateBatteryFromHost();
            this._pollPhoneStatus();
            this._pollBluetooth();
            this._pollLocation();
            this._pollSystemIndicators();
            this._pollNotifications();
        });
        // Unlock reveals the bar without a display OFF->ON transition; refresh
        // the authoritative state once instead of polling behind the lock.
        document.addEventListener('nuxel:lockscreen-hidden', () => {
            this._updateTime();
            this._pollPhoneStatus();
            this._pollBluetooth();
            this._pollLocation();
            this._pollSystemIndicators();
            this._pollNotifications();
        });

        // Listen for bridge push events if available
        if (typeof bridge !== 'undefined' && bridge.on) {
            bridge.on('status:update', (data) => this._onStatusUpdate(data));
        }

        // A32 — camera/cutout safe zones: the item row is re-solved whenever the
        // set changes or the viewport does, so no indicator can stay inside a
        // blocked zone just because it was laid out earlier.
        this._applySafeZones();
        window.addEventListener('resize', () => this._applySafeZones());
        window.addEventListener('orientationchange', () => setTimeout(() => this._applySafeZones(), 120));
        document.addEventListener('nuxel:safezones-changed', () => this._applySafeZones());
    }

    _scheduleClock() {
        const tick = () => {
            if (!this._statusInactive()) this._updateTime();
            const now = new Date();
            const delay = Math.max(1000, 60000 - (now.getSeconds() * 1000 + now.getMilliseconds()));
            this._clockTimer = setTimeout(tick, delay);
        };
        const now = new Date();
        this._clockTimer = setTimeout(tick,
            Math.max(1000, 60000 - (now.getSeconds() * 1000 + now.getMilliseconds())));
    }

    _bindQuickSettingsGesture() {
        const bar = document.getElementById('status-bar');
        if (!bar) return;
        const PULL_PX = 24;      // CSS px, measured against the real 360x760 viewport
        const MAX_SKEW = 80;     // reject diagonal drags that are not a pull-down
        let startX = 0, startY = 0, tracking = false, fired = false;

        const start = (x, y) => {
            startX = x; startY = y; tracking = true; fired = false;
        };
        const move = (x, y) => {
            if (!tracking || fired) return;
            const dy = y - startY;
            const dx = Math.abs(x - startX);
            if (dy >= PULL_PX && dx <= MAX_SKEW) {
                fired = true;
                tracking = false;
                try {
                    document.dispatchEvent(new CustomEvent('gesture:qs'));
                } catch (e) {}
            }
        };
        const end = () => { tracking = false; };

        // Pointer events are what WebKitGTK delivers for a real finger on this
        // port (verified: one physical tap produced pointerdown + touchstart).
        // The touch fallback is passive and shares the same state, so a browser
        // that emits both cannot open the panel twice.
        bar.addEventListener('pointerdown', (e) => {
            if (e.button !== undefined && e.button !== 0) return;
            start(e.clientX, e.clientY);
            // Keep receiving moves after the finger leaves the 36 px bar.
            try { bar.setPointerCapture(e.pointerId); } catch (err) {}
        });
        bar.addEventListener('pointermove', (e) => move(e.clientX, e.clientY));
        bar.addEventListener('pointerup', (e) => {
            try { bar.releasePointerCapture(e.pointerId); } catch (err) {}
            end();
        });
        bar.addEventListener('pointercancel', end);
        bar.addEventListener('touchstart', (e) => {
            const t = e.touches && e.touches[0];
            if (t) start(t.clientX, t.clientY);
        }, { passive: true });
        bar.addEventListener('touchmove', (e) => {
            const t = e.touches && e.touches[0];
            if (t) move(t.clientX, t.clientY);
        }, { passive: true });
        bar.addEventListener('touchend', end, { passive: true });
        bar.addEventListener('touchcancel', end, { passive: true });
    }

    _applySafeZones() {
        if (!window.NuxelSafeZones || typeof window.NuxelSafeZones.applyLayout !== 'function') return;
        // Many render paths call this within one state update.  Coalesce them
        // into ONE measurement/paint instead of two nested rAF layout passes
        // per caller (the old code could run 10+ forced layouts per poll).
        if (this._safeZonesScheduled) return;
        this._safeZonesScheduled = true;
        requestAnimationFrame(() => {
            this._safeZonesScheduled = false;
            try { window.NuxelSafeZones.applyLayout(); }
            catch (e) { console.warn('safe zones:', e.message || e); }
        });
    }

    // A54: deterministic collision assertion.  Measure every VISIBLE status
    // cell and report any intersecting pair.  This is the same geometry the
    // physical panel renders; a PASS means no two indicators share pixels.
    _assertNoOverlap() {
        const ids = ['status-signal', 'status-wifi', 'status-location', 'status-bluetooth',
                     'status-sound', 'status-usb', 'status-battery', 'status-battery-pct'];
        const boxes = [];
        ids.forEach((id) => {
            const el = document.getElementById(id);
            if (!el || el.hidden || el.style.display === 'none') return;
            const r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) return;
            boxes.push({ id, left: r.left, right: r.right, top: r.top, bottom: r.bottom });
        });
        const overlaps = [];
        for (let i = 0; i < boxes.length; i++) {
            for (let j = i + 1; j < boxes.length; j++) {
                const a = boxes[i], b = boxes[j];
                if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) {
                    overlaps.push(a.id + '<->' + b.id);
                }
            }
        }
        const line = 'STATUSBAR_OVERLAP_CHECK cells=' + boxes.length +
                     ' overlaps=' + (overlaps.length ? overlaps.join(',') : 'none');
        try { console.log('[status-bar] ' + line); } catch (e) {}
        try {
            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.nuxelDiag) {
                window.webkit.messageHandlers.nuxelDiag.postMessage(line);
            }
        } catch (e) {}
        this._overlapReport = { cells: boxes.map(b => b.id), overlaps };
        return overlaps;
    }

    _displayOff() {
        try { return document.body.classList.contains('display-off'); } catch (e) { return false; }
    }

    /* The status bar is physically covered by the lockscreen.  Its 5/10 s
       provider polls were still running behind it; pause them until unlock.
       A wake or an explicit lockscreen-hidden event refreshes immediately. */
    _coveredByLock() {
        try {
            if (document.body.classList.contains('lockscreen-active')) return true;
            const ls = document.getElementById('lockscreen');
            return !!(ls && !ls.hidden);
        } catch (e) { return false; }
    }
    _statusInactive() { return this._displayOff() || this._coveredByLock(); }

    _updateTime() {
        if (this._displayOff()) return;
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const text = hours + ':' + minutes;
        if (this.elements.time && this.elements.time.textContent !== text) {
            this.elements.time.textContent = text;
        }
    }

    _renderSignal() {
        if (!this.elements.signal) return;
        const state = this.state.cellularState;
        const visible = state === 'registered';
        this.elements.signal.hidden = !visible;
        this.elements.signal.dataset.cellularState = state;
        if (!visible) {
            const labels = {
                'no-sim': 'No SIM',
                unavailable: 'Cellular adapter unavailable',
                searching: 'Cellular network searching',
                unknown: 'Cellular status unavailable',
            };
            this.elements.signal.setAttribute('aria-label', labels[state] || labels.unknown);
            this.elements.signal.replaceChildren();
            this._applySafeZones();
            return;
        }
        const barsCount = 4;
        const activeBars = Math.max(0, Math.min(barsCount, Math.round(
            (this.state.signalLevel / this.state.signalMax) * barsCount
        )));

        let html = '<span class="signal-bars">';
        for (let i = 0; i < barsCount; i++) {
            const active = i < activeBars ? 'active' : '';
            html += '<span class="signal-bar ' + active + '"></span>';
        }
        html += '</span>';
        this.elements.signal.innerHTML = html;
        this.elements.signal.setAttribute('aria-label', 'Cellular signal ' + activeBars + ' of ' + barsCount);
        this._applySafeZones();
    }

    _renderWifi() {
        if (!this.elements.wifi) return;
        // The CSS glyph is the single Wi-Fi drawing.  Rendering an SVG inside
        // it created the doubled icon seen on the handset.
        this.elements.wifi.replaceChildren();
        const state = this.state.wifiState;
        const connected = state === 'connected' || state === 'internet';
        const connecting = state === 'connecting';
        const labels = {
            disabled: 'Wi-Fi disabled',
            unavailable: 'Wi-Fi adapter unavailable',
            unmanaged: 'Wi-Fi adapter unmanaged',
            enabled_disconnected: 'Wi-Fi enabled, not connected',
            connecting: 'Wi-Fi connecting',
            connected: 'Wi-Fi connected without verified internet',
            internet: 'Wi-Fi internet verified',
        };
        this.elements.wifi.dataset.wifiState = state;
        this.elements.wifi.setAttribute('aria-label', labels[state] || labels.unavailable);
        this.elements.wifi.style.opacity = connected ? '1' : (connecting ? '0.7' : '0.4');
        this.elements.wifi.style.setProperty('--wifi-colour', connected ? '#4CAF50' : (connecting ? '#d9a441' : '#666'));
    }

    // Bluetooth is drawn only when a real powered adapter is present.  OFF and
    // UNKNOWN both hide the glyph; the Quick Settings tile carries the detailed
    // blocker/state.  An unreadable provider never becomes a false OFF.
    _renderBluetooth() {
        if (!this.elements.bluetooth) return;
        const on = this.state.bluetoothOn === true;
        this.elements.bluetooth.hidden = !on;
        this.elements.bluetooth.dataset.bluetoothState = this.state.bluetoothState;
        this.elements.bluetooth.dataset.discovering =
            this.state.bluetoothDiscovering ? 'true' : 'false';
        if (!on) {
            this.elements.bluetooth.replaceChildren();
            this.elements.bluetooth.setAttribute('aria-label', 'Bluetooth off or unavailable');
            this._applySafeZones();
            return;
        }
        const label = this.state.bluetoothDiscovering
            ? 'Bluetooth on, discovering'
            : 'Bluetooth on';
        this.elements.bluetooth.setAttribute('aria-label',
            label + (this.state.bluetoothAddress ? (', ' + this.state.bluetoothAddress) : ''));
        this.elements.bluetooth.title = label +
            (this.state.bluetoothAddress ? (' · ' + this.state.bluetoothAddress) : '');
        this._applySafeZones();
    }

    async _pollBluetooth() {
        if (this._statusInactive()) return;
        try {
            if (typeof bridge === 'undefined' || !bridge.call) return;
            const st = await bridge.call('bluetooth', 'status', {});
            if (!st || st.success === false) {
                // Provider unavailable is UNKNOWN.  Do not keep a stale ON glyph
                // after a failure, and do not assert OFF either.
                this.state.bluetoothOn = null;
                this.state.bluetoothState = 'unavailable';
                this.state.bluetoothDiscovering = false;
                this._renderBluetooth();
                return;
            }
            const known = typeof st.powered === 'boolean';
            this.state.bluetoothOn = known ? st.powered : null;
            this.state.bluetoothState = st.state || (known ? (st.powered ? 'on' : 'off') : 'unknown');
            this.state.bluetoothDiscovering = st.discovering === true;
            this.state.bluetoothAddress = st.adapter_address || '';
            this._renderBluetooth();
        } catch (e) {
            this.state.bluetoothOn = null;
            this.state.bluetoothState = 'error';
            this.state.bluetoothDiscovering = false;
            this._renderBluetooth();
        }
    }

    // Location indicator: the glyph reflects real provider state, not the
    // Location tile's optimistic label.  Network/Wi-Fi/IP positions are shown
    // as approximate (blue); only a provider-confirmed GNSS source is green.
    _renderLocation() {
        const el = this.elements.location;
        if (!el) return;
        const state = this.state.locationState || 'unknown';
        const visible = this.state.locationEnabled && state !== 'unknown' && state !== 'disabled';
        el.hidden = !visible;
        el.dataset.state = state;
        el.dataset.kind = this.state.locationKind || 'unknown';
        let label;
        if (!this.state.locationEnabled) label = 'Location off (privacy policy)';
        else if (state === 'fixed' && this.state.locationKind === 'satellite') label = 'GNSS satellite fix';
        else if (state === 'fixed' && this.state.locationKind === 'network') label = 'Approximate network location';
        else if (state === 'fixed') label = 'Location provider fix';
        else if (state === 'stale') label = 'Location fix is stale';
        else if (state === 'searching') label = 'Location searching for a fix';
        else if (state === 'unavailable') label = 'Location provider unavailable';
        else if (state === 'error') label = 'Location provider error';
        else label = 'No location fix';
        const parts = [label];
        if (this.state.locationSource) parts.push('source=' + this.state.locationSource);
        if (typeof this.state.locationAccuracy === 'number') parts.push('±' + Math.round(this.state.locationAccuracy) + ' m');
        if (typeof this.state.locationAge === 'number') parts.push(Math.round(this.state.locationAge) + ' s old');
        el.title = parts.join(' · ');
        el.setAttribute('aria-label', label);
        this._applySafeZones();
    }

    async _pollLocation() {
        if (this._statusInactive()) return;
        if (typeof bridge === 'undefined' || !bridge.call) return;
        try {
            const st = await bridge.call('location', 'get-status', {});
            if (!st || st.success === false) {
                this.state.locationState = 'unavailable';
                this.state.locationEnabled = !!st.enabled;
                this.state.locationKind = null;
                this.state.locationSource = null;
                this._renderLocation();
                return;
            }
            this.state.locationEnabled = st.enabled === true;
            this.state.locationState = st.state || (st.enabled ? 'no_fix' : 'disabled');
            this.state.locationKind = st.fix_kind || null;
            this.state.locationSource = st.fix_source || null;
            this.state.locationAge = (typeof st.last_fix_age_s === 'number') ? st.last_fix_age_s : null;
            this.state.locationAccuracy = (typeof st.accuracy === 'number') ? st.accuracy : null;
            this._renderLocation();
        } catch (e) {
            this.state.locationState = 'unavailable';
            this.state.locationKind = null;
            this.state.locationSource = null;
            this._renderLocation();
        }
    }

    _renderSound() {
        const el = this.elements.sound;
        if (!el) return;
        const mode = this.state.soundMode;
        const known = mode === 'normal' || mode === 'vibrate' || mode === 'silent';
        el.hidden = !known;
        el.dataset.mode = known ? mode : 'unknown';
        if (!known) {
            el.setAttribute('aria-label', 'Sound mode unknown');
            el.title = 'Sound mode unknown (provider has not reported)';
            this._applySafeZones();
            return;
        }
        const labels = {
            normal: 'Sound mode: normal',
            vibrate: 'Sound mode: vibrate (selected; haptics not claimed)',
            silent: 'Sound mode: silent',
        };
        el.setAttribute('aria-label', labels[mode]);
        el.title = labels[mode] + ' · Power + Volume Up cycles normal → vibrate → silent';
        this._applySafeZones();
    }

    _renderUsb() {
        const el = this.elements.usb;
        if (!el) return;
        const ind = this.state.indicators;
        let label = '';
        let visible = false;
        if (ind) {
            const usb = ind.usb_data || {};
            const transfer = ind.file_transfer || {};
            const transports = ind.console_transports || {};
            const charging = ind.charging || {};
            // Deterministic precedence: active file transfer > active USB
            // console > active charge > enumerated data link.
            if (transfer.active === true) { label = 'file'; visible = true; }
            else if (transports.usb && transports.usb.active === true) { label = 'term'; visible = true; }
            else if (charging.charging === true && (usb.pc_connected === true || charging.external_power === true)) { label = 'chrg'; visible = true; }
            else if (usb.pc_connected === true) { label = ''; visible = true; }
        }
        this.state.usbLabel = label;
        el.hidden = !visible;
        el.dataset.state = visible ? (label || 'connected') : 'unknown';
        const tag = el.querySelector('.usb-label');
        if (tag) tag.textContent = label;
        if (!visible) {
            el.setAttribute('aria-label', 'USB not connected');
            el.title = 'USB: no wired data link reported';
        } else {
            const detail = label === 'file' ? 'File transfer endpoint active'
                : label === 'term' ? 'USB console active'
                : label === 'chrg' ? 'Charging over USB'
                : 'USB data link to host';
            el.setAttribute('aria-label', 'USB: ' + detail);
            el.title = 'USB: ' + detail;
        }
        this._applySafeZones();
    }

    async _pollSystemIndicators() {
        if (this._statusInactive()) return;
        try {
            if (typeof bridge === 'undefined' || !bridge.call) return;
            const ind = await bridge.call('system', 'indicators', {});
            if (!ind || ind.success === false) {
                // Keep the last-known snapshot only briefly; on provider failure
                // mark the USB glyph UNKNOWN rather than inventing a disconnect.
                this.state.indicators = null;
                this._renderUsb();
                return;
            }
            this.state.indicators = ind;
            const sound = ind.sound_mode && ind.sound_mode.mode;
            this.state.soundMode = (sound === 'normal' || sound === 'vibrate' || sound === 'silent') ? sound : 'unknown';
            this._renderSound();
            this._renderUsb();
        } catch (e) {
            this.state.indicators = null;
            this._renderUsb();
        }
    }

    setBatteryStyle(style) {
        this.batteryStyle = ['inside', 'percentage', 'bar'].includes(style) ? style : 'inside';
        this._renderBattery();
        this._applySafeZones();
    }

    _renderBattery() {
        if (!this.elements.battery) return;
        this.elements.battery.className = 'status-icon battery-slot';
        const known = Number.isFinite(this.state.batteryLevel);
        const level = known ? Math.max(0, Math.min(100, this.state.batteryLevel)) : null;
        const charging = this.state.batteryCharging;

        let levelClass = '';
        if (level !== null && level <= 10) levelClass = 'critical';
        else if (level !== null && level <= 20) levelClass = 'warning';

        const style = this.batteryStyle || 'inside';
        const width = level === null ? 0 : level;
        const renderKey = [level, charging ? 1 : 0, style, this.state.batteryCapacityUah].join('|');
        if (this._batteryRenderKey === renderKey) return;
        this._batteryRenderKey = renderKey;
        if (style === 'percentage') {
            this.elements.battery.innerHTML = '';
            this.elements.battery.style.display = 'none';
            if (this.elements.batteryPct) { this.elements.batteryPct.hidden = false; this.elements.batteryPct.textContent = level === null ? '—' : level + '%'; }
            return;
        }
        this.elements.battery.style.display = '';
        const inside = style === 'inside';
        const capacity = this.state.batteryCapacityUah;
        const capacityLabel = Number.isFinite(capacity) && capacity > 0
            ? Math.round(capacity / 1000) + ' mAh'
            : 'capacity unavailable';
        try { this.elements.battery.title = 'Battery ' + (level === null ? '—' : level + '%') + ' · ' + capacityLabel; } catch (e) {}
        this.elements.battery.innerHTML = '<span class="battery-icon' + (charging ? ' charging' : '') + '">' +
            '<span class="battery-level ' + levelClass + '" style="width:' + width + '%"></span>' +
            (inside ? '<span class="battery-inside-pct">' + (level === null ? '—' : level + '%') + '</span>' : '') + '</span>';
        if (this.elements.batteryPct) { this.elements.batteryPct.textContent = ''; this.elements.batteryPct.hidden = true; }
        this._applySafeZones();
    }

    _acceptBatteryLevel(level, charging, status) {
        const n = Number(level);
        if (!Number.isFinite(n) || n < 0 || n > 100) return false;
        const next = Math.round(n);
        const st = String(status == null ? '' : status).trim().toLowerCase();
        const prev = Number.isFinite(this.state.batteryLevel) ? this.state.batteryLevel : null;

        if (next === 0) {
            if (st === 'full') { this._batteryZeroCount = 0; return false; }
            if (prev !== null && prev >= 5) {
                this._batteryZeroCount++;
                if (this._batteryZeroCount < 3) return false;
            }
        } else {
            this._batteryZeroCount = 0;
        }

        const zeroConfirmed = next === 0 && (prev === null || prev < 5 || this._batteryZeroCount >= 3);
        if (!zeroConfirmed && prev !== null && next !== prev && Math.abs(next - prev) > 30) {
            if (this._batteryBigCandidate === next) this._batteryBigCount++;
            else { this._batteryBigCandidate = next; this._batteryBigCount = 1; }
            if (this._batteryBigCount < 2) return false;
        } else {
            this._batteryBigCandidate = null;
            this._batteryBigCount = 0;
        }

        this.state.batteryLevel = next;
        // 'Full' means externally powered and topped up, NOT actively charging.
        // Only a canonical charging===true or the kernel status 'charging' may
        // light the bolt.
        this.state.batteryCharging = charging === true || st === 'charging';
        return true;
    }

    async _hydrateBatteryFromHost() {
        try {
            if (!window.NuxelHost || !window.NuxelHost.available ||
                typeof window.NuxelHost.statusRead !== 'function') return;
            const readings = await Promise.all([
                window.NuxelHost.statusRead('battery-capacity'),
                window.NuxelHost.statusRead('battery-status'),
            ]);
            const capacity = readings[0] || {};
            const status = readings[1] || {};
            const rawText = String(capacity.text == null ? '' : capacity.text).trim();
            // A66-02: an absent/empty sysfs read during boot is UNKNOWN, not 0%.
            // Number('') === 0, so it must be rejected BEFORE numeric coercion.
            if (!capacity.ok || !rawText) return;
            const level = Number(rawText);
            if (!Number.isFinite(level) || level < 0 || level > 100) return;

            // "Full" is externally powered but not actively charging.  Only
            // the kernel's exact Charging state earns the charging glyph.
            const statusText = String(status.text == null ? '' : status.text).trim();
            this._acceptBatteryLevel(level, statusText.toLowerCase() === 'charging', statusText);
            this._renderBattery();
            const marker = 'BATTERY_HOST_READY level=' + level +
                ' charging=' + (this.state.batteryCharging ? '1' : '0');
            try { console.log('[status-bar] ' + marker); } catch (e) {}
            try {
                if (window.webkit && window.webkit.messageHandlers &&
                    window.webkit.messageHandlers.nuxelDiag) {
                    window.webkit.messageHandlers.nuxelDiag.postMessage(marker);
                }
            } catch (e) {}
        } catch (e) {
            console.warn('StatusBar: direct battery hydration failed:', e.message || e);
        }
    }

    async _pollPhoneStatus() {
        if (this._statusInactive()) return;
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
            const level = status.battery.level == null ? NaN : Number(status.battery.level);
            const charging = Boolean(status.battery.charging);
            // A missing/out-of-range sysfs reading is UNKNOWN, not 0% and not a
            // stale old value.  The icon renders an em dash instead.  A valid
            // reading still goes through the same 100% -> 0% guard.
            if (Number.isFinite(level) && level >= 0 && level <= 100) {
                this._acceptBatteryLevel(
                    level, charging,
                    status.battery.status == null ? '' : status.battery.status
                );
            }
            // Actual capacity representation (A48): microampere-hours from the
            // fuel gauge. charge_full is the current usable full capacity.
            const capUah = Number(status.battery.capacity_uah);
            const designUah = Number(status.battery.design_capacity_uah);
            this.state.batteryCapacityUah = Number.isFinite(capUah) && capUah > 0 ? capUah : null;
            this.state.batteryDesignCapacityUah = Number.isFinite(designUah) && designUah > 0 ? designUah : null;
        }

        // Modem / cellular.  Only an explicit registered/connected modem is
        // allowed to produce carrier bars.  The old network fallback made a
        // Wi-Fi or ethernet connection look like a SIM signal on this S10+.
        const modem = status.modem;
        const simAbsent = modem && (modem.sim_present === false ||
            modem.sim === 'absent' || modem.sim_state === 'absent' ||
            modem.state === 'no-sim');
        if (modem && modem.connected && !simAbsent) {
            const signalQuality = Number(status.modem.signal_quality || 0);
            this.state.signalLevel = Math.round((signalQuality / 100) * this.state.signalMax);
            this.state.mobileNetwork = true;
            this.state.cellularState = 'registered';
            this.state.operator = status.modem.operator || '';
        } else if (simAbsent) {
            this.state.signalLevel = 0;
            this.state.mobileNetwork = false;
            this.state.cellularState = 'no-sim';
            this.state.operator = '';
        } else if (modem && (modem.available === false || modem.state === 'unavailable')) {
            this.state.signalLevel = 0;
            this.state.mobileNetwork = false;
            this.state.cellularState = 'unavailable';
            this.state.operator = '';
        } else if (modem && (modem.state === 'searching' || modem.searching === true)) {
            this.state.signalLevel = 0;
            this.state.mobileNetwork = false;
            this.state.cellularState = 'searching';
            this.state.operator = '';
        } else {
            this.state.signalLevel = 0;
            this.state.mobileNetwork = false;
            this.state.cellularState = 'unknown';
            this.state.operator = '';
        }

        // Network / Wi-Fi. The bridge reports Wi-Fi device state separately
        // from its own D-Bus reachability and generic ethernet routes.
        const network = status.network || {};
        if (typeof network.wifi_state === 'string') {
            this.state.wifiState = network.wifi_state;
            this.state.wifiConnected = Boolean(network.wifi_connected);
        } else if (network.type === 'wifi' && network.connected) {
            this.state.wifiState = network.connectivity === 4 ? 'internet' : 'connected';
            this.state.wifiConnected = true;
        } else if (network.wifi_enabled) {
            this.state.wifiState = 'enabled_disconnected';
            this.state.wifiConnected = false;
        } else {
            this.state.wifiState = 'unavailable';
            this.state.wifiConnected = false;
        }

        this._renderSignal();
        this._renderWifi();
        this._renderBattery();
        this._applySafeZones();
        this._assertNoOverlap();
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
        if (this._statusInactive()) return;
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
                'background:rgba(26,26,46,0.98);border:1px solid ' +
                'rgba(255,255,255,0.08);border-radius:14px;box-shadow:0 2px 4px rgba(0,0,0,0.5);' +
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
        const n = Number(level);
        this.state.batteryLevel = Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : null;
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
