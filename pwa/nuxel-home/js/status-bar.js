// Nuxel Status Bar — v0.8.2-beta
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
    static get VERSION() { return '0.8.2-beta'; }

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
            // Radio power is distinct from link state.  null = unknown.
            wifiRadioOn: null,
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
            remote: document.getElementById('status-remote'),
            battery: document.getElementById('status-battery'),
            batteryPct: document.getElementById('status-battery-pct'),
            nfc: document.getElementById('status-nfc'),
        };
        this._notificationElements = {
            button: null,
            badge: null,
            panel: null,
        };
        this._notifPollTimer = null;
        this._pollTimer = null;
        this.iconPrefs = null;            // null = loading/default-visible
        this._providerVisible = {};       // element id -> provider says it is relevant
        this._loadIconPreferences();
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

    /* PWNAGE-94000: the native fullscreen adapter (nuxel-statusbar) renders
       the SAME canonical model instead of inventing a second status bar.  The
       launcher writes a tiny JSON document through the host's whitelisted
       config channel; /run is the only destination and no app data is sent. */
    _publishCanonicalModel(force) {
        const now = Date.now();
        if (!force && now - (this._modelAt || 0) < 5000) return;
        const st = this.state || {};
        const counts = st.notificationCounts || this._countNotifications(st.notifications);
        const model = {
            schema_version: 1,
            time: this.elements.time ? String(this.elements.time.textContent || '') : '',
            wifi: st.wifiConnected === true ? 'connected' : String(st.wifiState || 'unknown'),
            wifi_on: st.wifiRadioOn === true,
            battery: Number.isFinite(st.batteryLevel) ? st.batteryLevel : null,
            charging: st.batteryCharging === true,
            bluetooth: st.bluetoothOn === true,
            bluetooth_state: String(st.bluetoothState || 'unknown'),
            mobile: String(st.cellularState || 'unknown'),
            signal: Number.isFinite(st.signalLevel) ? st.signalLevel : 0,
            location: st.locationEnabled === true,
            location_state: String(st.locationState || 'unknown'),
            sound: String(st.soundMode || 'unknown'),
            notifications: counts.unread || 0,
            active_notifications: counts.active || 0,
            usb: String(st.usbLabel || ''),
        };
        const text = JSON.stringify(model);
        if (!force && text === this._modelKey) return;
        this._modelKey = text;
        this._modelAt = now;
        try {
            if (window.NuxelHost && window.NuxelHost.available && window.NuxelHost.configSet) {
                Promise.resolve(window.NuxelHost.configSet('statusbar-model', text)).catch(() => {});
            }
        } catch (e) { /* the DOM bar remains authoritative if the host is absent */ }
    }

    // PWNAGE-52000: status-bar icon visibility is a user preference layered on
    // top of real provider state.  It never turns a radio/service off.  A
    // provider OFF/unsupported/unknown state wins over the user's "show".
    _loadIconPreferences(attempt) {
        const tries = attempt || 0;
        const api = window.NuxelStatusBarIcons;
        if (!api || typeof api.load !== 'function') { this._applyIconPreferences(); return; }
        api.load().then((doc) => {
            this.iconPrefs = doc;
            this._applyIconPreferences();
            this._applySafeZones();
            // status-bar.js is loaded before host-bridge.js in index.html.  If
            // the durable host channel was not ready yet, keep the default for
            // one frame and re-read the real /etc document shortly after.
            const hostReady = !!(window.NuxelHost && window.NuxelHost.available);
            if (!hostReady && tries < 12) setTimeout(() => this._loadIconPreferences(tries + 1), 250);
        }).catch(() => { this.iconPrefs = null; this._applyIconPreferences(); });
    }

    reloadIconPreferences() { return this._loadIconPreferences(0); }

    _prefVisible(id) {
        if (!this.iconPrefs || !this.iconPrefs.icons) return true;
        return this.iconPrefs.icons[id] !== false;
    }

    _setProviderVisible(element, visible) {
        if (!element) return;
        if (!this._providerVisible) this._providerVisible = {};
        if (element.id) this._providerVisible[element.id] = !!visible;
        const def = window.NuxelStatusBarIcons && window.NuxelStatusBarIcons.byElement(element.id);
        const pref = def ? this._prefVisible(def.id) : true;
        element.hidden = !(visible && pref);
        element.dataset.userVisible = pref ? 'true' : 'false';
        element.dataset.providerVisible = visible ? 'true' : 'false';
    }

    _applyIconPreferences() {
        const api = window.NuxelStatusBarIcons;
        if (api && Array.isArray(api.DEFS)) {
            api.DEFS.forEach((def) => {
                const el = document.getElementById(def.element);
                if (!el) return;
                const provider = this._providerVisible[def.element];
                // Before any provider sample, only the local clock and the
                // battery cell may paint.  Every hardware/radio icon requires
                // an explicit provider proof (unknown is hidden, not guessed).
                const providerVisible = provider === true ||
                    (provider === undefined && (def.id === 'time' || def.id === 'battery'));
                this._setProviderVisible(el, providerVisible);
            });
        }
        this.elements.time && this._setProviderVisible(this.elements.time, this._providerVisible['status-time'] !== false);
        try {
            const ids = (api && api.DEFS ? api.DEFS : []).map((d) => d.id + '=' +
                (document.getElementById(d.element) && !document.getElementById(d.element).hidden ? '1' : '0')).join(',');
            const line = 'STATUSBAR_ICONS ' + ids + ' locked=' +
                (document.body.classList.contains('lockscreen-active') ? '1' : '0');
            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.nuxelDiag) {
                window.webkit.messageHandlers.nuxelDiag.postMessage(line);
            } else if (window.console && window.console.log) {
                window.console.log('[status-bar] ' + line);
            }
        } catch (e) { /* evidence must never break the bar */ }
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
        this._bindNfcTile();

        // Update local time every second (no bridge needed)
        // HH:MM only needs a minute cadence.  The old 1 s timer woke the
        // WebProcess 60x/min to rewrite identical text.
        this._scheduleClock();

        // Poll phone status slowly; these are provider/daemon states, not
        // frame-rate signals.  Every read is skipped while covered by the
        // lockscreen and refreshed on unlock.
        this._pollPhoneStatus();
        this._pollBluetooth();
        this._pollTimer = setInterval(() => { if (!this._statusInactive()) this._pollPhoneStatus(); }, 30000);
        this._pollLocation();
        this._locationPollTimer = setInterval(() => {
            if (!this._statusInactive()) this._pollLocation();
        }, 30000);
        // Sound mode + wired USB/file-transfer/console state.  One canonical
        // in-process read; no second high-frequency poller is created.
        this._pollSystemIndicators();
        this._indicatorPollTimer = setInterval(() => {
            if (!this._statusInactive()) this._pollSystemIndicators();
        }, 15000);

        // Poll notifications from the same JSON source (canonical
        // /var/lib/nuxel/notifications.json surfaced via the bridge).
        this._pollNotifications();
        this._notifPollTimer = setInterval(() => { if (!this._statusInactive()) this._pollNotifications(); }, 30000);
        // NFC: one provider read per visible interval; no separate duplicated
        // poller in Settings (Settings reads on tab selection).
        this._pollNfc();
        this._nfcPollTimer = setInterval(() => { if (!this._statusInactive()) this._pollNfc(); }, 60000);
        // A wake is an event: refresh immediately instead of waiting a poll.
        document.addEventListener('nuxel:display-on', () => {
            this._updateTime();
            this._hydrateBatteryFromHost();
            this._pollPhoneStatus();
            this._pollBluetooth();
            this._pollLocation();
            this._pollSystemIndicators();
            this._pollNotifications();
            this._pollNfc();
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

        // The button manager writes the sound-mode FIFO; nuxel-pwa-host relays
        // it here immediately.  Do not wait for the 15 s provider poll: the
        // owner expects the square glyph to change on the same key chord.
        document.addEventListener('nuxel:sound-mode', (ev) => {
            const mode = ev && ev.detail && ev.detail.mode;
            if (mode === 'normal' || mode === 'vibrate' || mode === 'silent') {
                this.state.soundMode = mode;
                this._renderSound();
            }
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
        this._publishCanonicalModel(true);
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
        const MAX_SKEW = 80;     // reject diagonal drags that are not a vertical pull
        let startX = 0, startY = 0, tracking = false, fired = false;

        const start = (x, y) => {
            // The bar is visible on the lockscreen, but protected Quick
            // Settings actions remain unavailable until a real unlock.
            if (this._displayOff() || this._coveredByLock()) return;
            startX = x; startY = y; tracking = true; fired = false;
            window.__nuxelQsGestureConsumed = false;
        };
        const move = (x, y) => {
            if (!tracking || fired) return;
            const dy = y - startY;
            const dx = Math.abs(x - startX);
            if (Math.abs(dy) >= PULL_PX && dx <= MAX_SKEW) {
                fired = true;
                tracking = false;
                window.__nuxelQsGestureConsumed = true;
                try {
                    document.dispatchEvent(new CustomEvent('gesture:qs', {
                        detail: {
                            direction: dy > 0 ? 'down' : 'up',
                            // A revealed fullscreen compact bar means the next
                            // downward pull is the SECOND stage (expanded QS).
                            revealed: document.body.classList.contains('app-status-revealed'),
                            source: 'status-bar',
                        },
                    }));
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

    // ---- NFC status/toggle ------------------------------------------------
    async _pollNfc() {
        const el = this.elements.nfc;
        if (!el) return;
        try {
            const b = (typeof bridge !== 'undefined' && bridge && bridge.call) ? bridge : null;
            if (!b) { el.hidden = true; return; }
            const st = await b.call('nfc', 'status', {});
            if (!st || st.success === false) {
                el.dataset.state = 'unknown'; el.title = 'NFC status unavailable';
                this._setProviderVisible(el, false); return;
            }
            if (!st.supported) {
                el.dataset.state = (st.state || 'blocked') === 'BLOCKED_KERNEL' ? 'blocked' : 'unsupported';
                el.title = 'NFC unavailable: ' + (st.blocker || st.state || 'not supported');
                this._setProviderVisible(el, false);
                return;
            }
            const nfcOn = st.enabled === true;
            el.dataset.state = nfcOn ? 'on' : (st.enabled === false ? 'off' : 'unknown');
            el.title = 'NFC ' + (nfcOn ? 'on' : st.enabled === false ? 'off' : 'unknown') +
                ' — tap to toggle; long-press opens Settings';
            this._setProviderVisible(el, nfcOn);
        } catch (e) { el.dataset.state = 'unknown'; el.title = 'NFC provider error'; this._setProviderVisible(el, false); }
    }

    _bindNfcTile() {
        const el = this.elements.nfc;
        if (!el || el.dataset.bound === '1') return;
        el.dataset.bound = '1';
        let press = null, long = false;
        el.addEventListener('pointerdown', () => {
            long = false;
            press = setTimeout(() => {
                long = true;
                try { if (window.appRegistry) window.appRegistry.launchApp('nuxel-settings'); } catch (e) {}
            }, 700);
        });
        el.addEventListener('pointerup', async () => {
            if (press) clearTimeout(press);
            if (long) return;
            try {
                const st = await bridge.call('nfc', 'status', {});
                if (!st || !st.supported) {
                    if (window.appRegistry) window.appRegistry.launchApp('nuxel-settings');
                    return;
                }
                const r = await bridge.call('nfc', 'toggle', {});
                if (r && r.success === false) el.title = 'NFC unchanged: ' + (r.error || r.blocker || 'refused');
                await this._pollNfc();
            } catch (e) { /* diagnostics only */ }
        });
        el.addEventListener('pointerleave', () => { if (press) clearTimeout(press); });
    }

    // A54: deterministic collision assertion.  Measure every VISIBLE status
    // cell and report any intersecting pair.  This is the same geometry the
    // physical panel renders; a PASS means no two indicators share pixels.
    _assertNoOverlap() {
        const ids = ['status-signal', 'status-wifi', 'status-location', 'status-bluetooth',
                     'status-nfc', 'status-sound', 'status-usb', 'status-battery', 'status-battery-pct'];
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
    /* PWNAGE-49000: the proper DOM status bar is visible above the lockscreen
       now, so lock coverage must NOT pause its provider refreshes.  Only a
       real display-off state pauses the non-essential pollers. */
    _statusInactive() { return this._displayOff(); }

    _updateTime() {
        if (this._displayOff()) return;
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const text = hours + ':' + minutes;
        if (this.elements.time && this.elements.time.textContent !== text) {
            this.elements.time.textContent = text;
        }
        if (this.elements.time) this._setProviderVisible(this.elements.time, true);
        this._publishCanonicalModel();
    }

    _renderSignal() {
        if (!this.elements.signal) return;
        const state = this.state.cellularState;
        // PWNAGE-52000: unsupported/OFF is HIDDEN.  A muted zero-bar glyph
        // was indistinguishable from a real radio with no signal; on this
        // handset the CP transport is UNSUPPORTED, so it reserves no width.
        const registered = state === 'registered';
        const visible = registered;
        this._setProviderVisible(this.elements.signal, visible);
        this.elements.signal.dataset.cellularState = state;
        this.elements.signal.classList.toggle('unavailable', !registered);
        if (!registered) {
            const labels = {
                'no-sim': 'No SIM',
                unavailable: 'Cellular adapter unavailable',
                searching: 'Cellular network searching',
                unknown: 'Cellular status unavailable',
            };
            this.elements.signal.setAttribute('aria-label', labels[state] || labels.unknown);
            this.elements.signal.title = labels[state] || labels.unknown;
            let muted = '<span class="signal-bars">';
            for (let i = 0; i < 4; i++) muted += '<span class="signal-bar"></span>';
            muted += '</span>';
            this.elements.signal.innerHTML = muted;
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
        // PWNAGE-52000: radio OFF / unsupported hides the icon completely.
        // ON-but-disconnected remains visible with a neutral glyph.  Unknown
        // never becomes a confident connection.
        const radioOn = this.state.wifiRadioOn;
        const knownOff = radioOn === false || ['disabled', 'unavailable', 'unmanaged'].includes(state);
        const visible = radioOn === true && !knownOff;
        this._setProviderVisible(this.elements.wifi, visible);
        this.elements.wifi.dataset.wifiState = state;
        this.elements.wifi.setAttribute('aria-label', labels[state] || labels.unavailable);
        if (!visible) {
            this.elements.wifi.title = knownOff ? 'Wi-Fi radio off / unavailable' : 'Wi-Fi state unknown';
            this._applySafeZones();
            return;
        }
        // PWNAGE-42000: disconnected/unknown Wi-Fi must remain legible.  The
        // old #666 at 0.4 opacity disappeared into the navy status strip.
        this.elements.wifi.style.opacity = connected ? '1' : (connecting ? '0.95' : '0.9');
        this.elements.wifi.style.setProperty(
            '--wifi-colour',
            connected ? '#7ee29a' : (connecting ? '#ffd166' : '#c8d7ea'));
    }

    // PWNAGE-49000: show the recognisable Bluetooth rune whenever the adapter
    // state is known.  OFF is a muted rune (not a false ON), UNKNOWN/error is
    // hidden rather than invented.  This remains a state indicator, never a
    // toggle; the Quick Settings tile owns the detailed blocker text.
    _renderBluetooth() {
        if (!this.elements.bluetooth) return;
        const state = this.state.bluetoothState || 'unknown';
        // PWNAGE-52000: Bluetooth is shown only while the provider confirms
        // the radio is powered.  OFF/unknown/error reserves no layout width.
        const visible = this.state.bluetoothOn === true && state !== 'unknown' && state !== 'error';
        this._setProviderVisible(this.elements.bluetooth, visible);
        this.elements.bluetooth.classList.toggle('unavailable', state === 'unknown' || state === 'error');
        this.elements.bluetooth.dataset.bluetoothState = state;
        this.elements.bluetooth.dataset.discovering =
            this.state.bluetoothDiscovering ? 'true' : 'false';
        this.elements.bluetooth.replaceChildren();
        if (!visible) {
            this.elements.bluetooth.setAttribute('aria-label', 'Bluetooth state unavailable');
            this.elements.bluetooth.title = 'Bluetooth state unavailable';
            this._applySafeZones();
            return;
        }
        const label = state === 'off'
            ? 'Bluetooth off'
            : (this.state.bluetoothDiscovering ? 'Bluetooth on, discovering' : 'Bluetooth on');
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
        // PWNAGE-52000: Location off/unsupported/unknown is hidden.  Only an
        // actually enabled provider reserves status-bar width.
        const visible = this.state.locationEnabled === true &&
            state !== 'unknown' && state !== 'unavailable' && state !== 'error' && state !== 'disabled';
        this._setProviderVisible(el, visible);
        el.classList.toggle('unavailable', state === 'unknown' || state === 'unavailable' || state === 'error');
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
        this._setProviderVisible(el, known);
        el.dataset.mode = known ? mode : 'unknown';
        if (!known) {
            el.setAttribute('aria-label', 'Sound mode unknown');
            el.title = 'Sound mode unknown (provider has not reported)';
            this._applySafeZones();
            return;
        }
        const labels = {
            normal: 'Sound normal',
            vibrate: 'Vibrate mode',
            silent: 'Silent mode',
        };
        const details = {
            normal: 'Speaker on · notifications may play sound',
            vibrate: 'Speaker muted · vibration alerts enabled',
            silent: 'Speaker muted · no vibration alert',
        };
        el.setAttribute('aria-label', labels[mode]);
        el.title = labels[mode] + ' · ' + details[mode] + ' · Power + Volume Up cycles normal → vibrate → silent';
        this._applySafeZones();
    }

    _renderUsb() {
        const el = this.elements.usb;
        if (!el) return;
        const ind = this.state.indicators;
        let label = '';
        let state = '';
        let visible = false;
        if (ind) {
            const usb = ind.usb_data || {};
            const transfer = ind.file_transfer || {};
            const transports = ind.console_transports || {};
            // PWNAGE-96000: the battery lightning is the ONLY charge indicator.
            // A wall charger elevates charging.external_power but is not a USB
            // data/host connection, so it must never light this glyph.  The
            // provider's usb_data.pc_connected is already vetoed by UDC state,
            // Type-C data role, speed and VBUS; do not derive it here.
            // Deterministic precedence: active file transfer > active USB
            // console > enumerated USB data link to a host.
            if (transfer.active === true) { label = 'file'; state = 'file'; visible = true; }
            else if (transports.usb && transports.usb.active === true) { label = 'term'; state = 'term'; visible = true; }
            else if (usb.pc_connected === true) { state = 'connected'; visible = true; }
        }
        this.state.usbLabel = label;
        const providerVisible = this._providerVisible['status-usb'] !== false;
        const renderKey = (visible ? '1' : '0') + '|' + (state || 'unknown') + '|' +
            label + '|' + (providerVisible ? '1' : '0');
        this._setProviderVisible(el, visible);
        if (this._usbRenderKey === renderKey) {
            this._applySafeZones();
            return;
        }
        this._usbRenderKey = renderKey;
        el.dataset.state = visible ? (state || 'connected') : 'unknown';
        const tag = el.querySelector('.usb-label');
        if (tag) tag.textContent = label;
        if (!visible) {
            el.setAttribute('aria-label', 'USB not connected');
            el.title = 'USB: no wired data link reported';
        } else {
            const detail = state === 'file' ? 'File transfer endpoint active'
                : state === 'term' ? 'USB console active'
                : 'USB data link to host';
            el.setAttribute('aria-label', 'USB: ' + detail);
            el.title = 'USB: ' + detail;
        }
        this._applySafeZones();
    }

    _renderRemote(remote) {
        const el = this.elements.remote;
        if (!el) return;
        const active = !!(remote && remote.active === true);
        this._setProviderVisible(el, active);
        el.dataset.state = active ? 'active' : 'off';
        const tag = el.querySelector('.remote-label');
        if (tag) tag.textContent = active ? 'R' : '';
        if (active) {
            const names = remote.services ? Object.keys(remote.services).filter((k) => remote.services[k] && remote.services[k].active).join(', ') : '';
            el.setAttribute('aria-label', 'Remote desktop active' + (names ? ': ' + names : ''));
            el.title = 'REMOTE DESKTOP ACTIVE' + (names ? ' · ' + names : '') + ' — open a remote app for the kill switch';
        } else {
            el.setAttribute('aria-label', 'Remote desktop off');
            el.title = 'Remote desktop off';
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
            this._renderRemote(ind.remote_desktop);
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
            this._providerVisible['status-battery'] = false;
            if (this.elements.batteryPct) {
                this._providerVisible['status-battery-pct'] = true;
                this.elements.batteryPct.textContent = level === null ? '—' : level + '%';
                this._setProviderVisible(this.elements.batteryPct, true);
            }
            this._applyIconPreferences();
            return;
        }
        this.elements.battery.style.display = '';
        this._setProviderVisible(this.elements.battery, true);
        const inside = style === 'inside';
        const capacity = this.state.batteryCapacityUah;
        const capacityLabel = Number.isFinite(capacity) && capacity > 0
            ? Math.round(capacity / 1000) + ' mAh'
            : 'capacity unavailable';
        try { this.elements.battery.title = 'Battery ' + (level === null ? '—' : level + '%') + ' · ' + capacityLabel; } catch (e) {}
        const zaps = charging ? '<span class="battery-zaps" aria-hidden="true"><i></i><i></i></span>' : '';
        this.elements.battery.innerHTML = '<span class="battery-icon' + (charging ? ' charging' : '') + '">' +
            '<span class="battery-level ' + levelClass + '" style="width:' + width + '%"></span>' +
            (inside ? '<span class="battery-inside-pct">' + (level === null ? '—' : level + '%') + '</span>' : '') +
            zaps + '</span>';
        if (this.elements.batteryPct) {
            this.elements.batteryPct.textContent = '';
            this._providerVisible['status-battery-pct'] = false;
            this._setProviderVisible(this.elements.batteryPct, false);
        }
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
        if (typeof network.wifi_enabled === 'boolean') {
            this.state.wifiRadioOn = network.wifi_enabled;
        } else if (['disabled', 'unavailable', 'unmanaged'].includes(network.wifi_state)) {
            this.state.wifiRadioOn = false;
        } else if (['connected', 'internet', 'enabled_disconnected', 'connecting'].includes(network.wifi_state)) {
            this.state.wifiRadioOn = true;
        } else {
            this.state.wifiRadioOn = null;
        }
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

    // ---- Notifications: authoritative daemon store -----------------------
    // The native notification hub is the single owner of persistence and
    // read/archive state.  The status bar only renders its snapshot and asks
    // the hub to commit actions; it never invents a count or a successful
    // swipe.  The visible reminder list lives inside expanded Quick Settings
    // below every control/status row and shares this same renderer.

    _buildNotificationsUI() {
        const right = document.querySelector('.status-right');
        if (!right) return;
        if (this._notificationElements.button) return;

        const wrap = document.createElement('div');
        wrap.className = 'status-icon status-notification';
        wrap.style.cssText = 'position:relative;width:16px;height:16px;display:inline-flex;cursor:pointer;';
        wrap.title = 'Notifications';
        wrap.setAttribute('role', 'button');
        wrap.setAttribute('tabindex', '0');
        wrap.setAttribute('aria-haspopup', 'dialog');
        wrap.setAttribute('aria-label', 'Notifications');
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
        const open = (e) => { if (e) e.stopPropagation(); this._openNotificationsInQuickSettings(); };
        wrap.addEventListener('click', open);
        wrap.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(e); }
        });
        right.appendChild(wrap);

        this._notificationElements.button = wrap;
        this._notificationElements.badge = badge;
        this._bindNotificationGestures();
        // Refresh the visible list when Quick Settings expands; this keeps the
        // notification card rendering tied to the real panel state.
        document.addEventListener('nuxel:qs-state', (ev) => {
            const state = ev && ev.detail && ev.detail.state;
            if (state === 'expanded') {
                // Refresh from the authoritative hub when the reminder list
                // becomes visible; the 30 s safety poll alone left a newly
                // received notification absent from an already-open panel.
                this._pollNotifications();
            }
        });
    }

    async _pollNotifications() {
        if (this._statusInactive()) return;
        try {
            if (typeof bridge === 'undefined' || !bridge.getNotifications) {
                this._setNotifications([], null, 'notification bridge unavailable');
                return;
            }
            const res = await bridge.getNotifications();
            if (!res || res.success === false) {
                // Keep the last good snapshot visible but never pretend the
                // provider's failure is a fresh zero-count snapshot.
                this._renderNotificationsPanel(res && res.error ? String(res.error) : 'notification provider unavailable');
                return;
            }
            const list = Array.isArray(res.notifications) ? res.notifications : [];
            this._setNotifications(list, res.counts || null, '');
        } catch (e) {
            const msg = String((e && e.message) || e);
            console.warn('StatusBar: notification poll failed:', msg);
            this._renderNotificationsPanel(msg);
        }
    }

    _setNotifications(notifications, counts, error) {
        this.state.notifications = Array.isArray(notifications) ? notifications : [];
        this.state.notificationCounts = counts || this._countNotifications(this.state.notifications);
        this.state.notificationError = error || '';
        this._renderNotificationsBadge();
        this._renderNotificationsPanel(this.state.notificationError);
        this._publishCanonicalModel(true);
        try {
            document.dispatchEvent(new CustomEvent('nuxel:notifications-changed', {
                detail: { notifications: this.state.notifications,
                          counts: this.state.notificationCounts,
                          error: this.state.notificationError },
            }));
        } catch (e) {}
    }

    _countNotifications(notifications) {
        const list = Array.isArray(notifications) ? notifications : [];
        const active = list.filter((n) => !n || !n.archived_at);
        const unread = active.filter((n) => n && !n.read_at).length;
        return { active: active.length, unread: unread, read: active.length - unread,
                 archived: list.length - active.length, total: list.length };
    }

    _renderNotificationsBadge() {
        const badge = this._notificationElements.badge;
        if (!badge) return;
        const counts = this.state.notificationCounts || this._countNotifications(this.state.notifications);
        const count = Number(counts.unread) || 0;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : String(count);
            badge.style.display = 'inline-flex';
            badge.setAttribute('aria-label', count + ' unread notifications');
        } else {
            badge.style.display = 'none';
            badge.setAttribute('aria-label', 'No unread notifications');
        }
    }

    _openNotificationsInQuickSettings() {
        if (this._displayOff() || this._coveredByLock()) return;
        if (window.qs && typeof window.qs.open === 'function') {
            window.qs.open();
            window.qs.expand();
        }
        this._renderNotificationsPanel();
    }

    _renderNotificationsPanel(error) {
        const list = document.getElementById('qs-notifications-list');
        if (!list) return;
        const section = document.getElementById('qs-notifications');
        const empty = document.getElementById('qs-notifications-empty');
        const errorEl = document.getElementById('qs-notifications-error');
        const countEl = document.getElementById('qs-notifications-count');
        const counts = this.state.notificationCounts || this._countNotifications(this.state.notifications);
        if (countEl) {
            const unread = Number(counts.unread) || 0;
            const active = Number(counts.active) || 0;
            countEl.textContent = active ? (unread ? unread + ' unread · ' + active + ' active'
                                                 : active + ' reminder' + (active === 1 ? '' : 's'))
                                         : '';
        }
        if (section) section.hidden = !(window.qs && window.qs.expanded);
        if (errorEl) {
            errorEl.hidden = !error;
            errorEl.textContent = error ? ('Notifications unavailable: ' + error) : '';
        }
        const notifs = (this.state.notifications || []).filter((n) => n && !n.archived_at);
        if (!notifs.length) {
            list.innerHTML = '';
            list.hidden = true;
            if (empty) empty.hidden = !!error;
            return;
        }
        if (empty) empty.hidden = true;
        list.hidden = false;
        list.innerHTML = notifs.map((n) => this._notificationCardHtml(n)).join('') +
            '<div class="qs-notification-swipe-hint">Swipe left to archive · swipe right to mark read</div>';
    }

    _notificationCardHtml(n) {
        const id = String(n.id == null ? '' : n.id);
        const app = String(n.app_name || n.app_id || 'System');
        const title = String(n.summary || n.title || '');
        const body = String(n.body || '');
        const t = n.timestamp ? new Date(n.timestamp) : null;
        const valid = t && !isNaN(t.getTime());
        let tstr = '';
        if (valid) {
            const ageS = Math.max(0, (Date.now() - t.getTime()) / 1000);
            if (ageS < 60) tstr = 'now';
            else if (ageS < 3600) tstr = Math.floor(ageS / 60) + 'm';
            else if (ageS < 86400) tstr = Math.floor(ageS / 3600) + 'h';
            else tstr = String(t.getDate()) + '/' + String(t.getMonth() + 1);
        }
        const appIcon = n.icon ? String(n.icon) : '';
        const iconHtml = appIcon
            ? '<span class="qs-notification-icon"><img src="' + escapeHtml(appIcon) + '" alt="" draggable="false" onerror="this.style.display=\'none\'"></span>'
            : '<span class="qs-notification-icon" aria-hidden="true">🔔</span>';
        const read = !!n.read_at;
        return '<article class="qs-notification-card" id="qs-notification-' + escapeHtml(id) + '" role="listitem" tabindex="0" data-notification-id="' + escapeHtml(id) +
            '" data-read="' + (read ? 'true' : 'false') + '" aria-label="' +
            escapeHtml(app + ': ' + title + (read ? ' (read)' : ' (unread)')) + '">' +
            iconHtml +
            '<div class="qs-notification-body">' +
            '<div class="qs-notification-app">' + escapeHtml(app) + '</div>' +
            (title ? '<div class="qs-notification-title">' + escapeHtml(title) + '</div>' : '') +
            (body ? '<div class="qs-notification-text">' + escapeHtml(body) + '</div>' : '') +
            '<div class="qs-notification-actions">' +
            '<button type="button" class="qs-notification-action read" data-notification-action="read" aria-label="Mark notification read">Mark read</button>' +
            '<button type="button" class="qs-notification-action archive" data-notification-action="archive" aria-label="Archive notification">Archive</button>' +
            '</div></div>' +
            (tstr ? '<div class="qs-notification-meta">' + escapeHtml(tstr) + '</div>' : '') +
            '</article>';
    }

    _bindNotificationGestures() {
        const list = document.getElementById('qs-notifications-list');
        if (!list || list.__nuxelNotifGestures) return;
        list.__nuxelNotifGestures = true;
        const THRESHOLD = 64;
        const MAX_VERTICAL = 42;
        let gesture = null;
        let lastHandledAt = 0;

        const cardFrom = (target) => target && target.closest ? target.closest('.qs-notification-card') : null;
        const begin = (x, y, id, source, card) => {
            if (!card) return;
            gesture = { x, y, id, source, card, dx: 0, dy: 0, horizontal: false, committed: false };
        };
        const move = (x, y, id, source) => {
            if (!gesture || gesture.source !== source) return;
            if (id !== undefined && gesture.id !== undefined && id !== gesture.id) return;
            gesture.dx = x - gesture.x;
            gesture.dy = y - gesture.y;
            if (!gesture.horizontal) {
                if (Math.abs(gesture.dx) > 12 && Math.abs(gesture.dx) > Math.abs(gesture.dy) * 1.25) {
                    gesture.horizontal = true;
                    gesture.card.dataset.swiping = 'true';
                } else if (Math.abs(gesture.dy) > MAX_VERTICAL) {
                    gesture = null;   // vertical scroll owns this touch
                    return;
                }
            }
            if (!gesture.horizontal) return;
            // A diagonal drag that becomes a scroll must not archive/read.
            if (Math.abs(gesture.dy) > 70) { cancel(source); return; }
            const dx = Math.max(-120, Math.min(120, gesture.dx));
            gesture.card.style.transform = 'translateX(' + dx + 'px)';
            gesture.card.style.opacity = String(Math.max(0.45, 1 - Math.abs(dx) / 220));
        };
        const finish = (x, y, id, source) => {
            if (!gesture || gesture.source !== source) return;
            if (id !== undefined && gesture.id !== undefined && id !== gesture.id) return;
            const g = gesture;
            gesture = null;
            g.card.dataset.swiping = 'false';
            g.card.style.transform = '';
            g.card.style.opacity = '';
            if (!g.horizontal) return;
            const now = performance.now();
            if (now - lastHandledAt < 350) return;
            const dx = x - g.x;
            if (Math.abs(dx) < THRESHOLD) return;
            lastHandledAt = now;
            const idValue = g.card.getAttribute('data-notification-id');
            if (dx < 0) this._archiveNotification(idValue, g.card);
            else this._markNotificationRead(idValue, g.card);
        };
        const cancel = (source) => {
            if (gesture && gesture.source === source) {
                gesture.card.dataset.swiping = 'false';
                gesture.card.style.transform = '';
                gesture.card.style.opacity = '';
            }
            gesture = null;
        };

        list.addEventListener('pointerdown', (e) => {
            if (e.button !== undefined && e.button !== 0) return;
            // Swipe actions are touch/pen gestures.  A mouse (including a
            // diagnostic virtual pointer) must use the visible action buttons;
            // otherwise a harmless pointer diagnostic could archive cards.
            if (e.pointerType === 'mouse') return;
            begin(e.clientX, e.clientY, e.pointerId, 'pointer', cardFrom(e.target));
        }, { passive: true });
        list.addEventListener('pointermove', (e) => move(e.clientX, e.clientY, e.pointerId, 'pointer'), { passive: true });
        list.addEventListener('pointerup', (e) => finish(e.clientX, e.clientY, e.pointerId, 'pointer'), { passive: true });
        list.addEventListener('pointercancel', () => cancel('pointer'), { passive: true });
        list.addEventListener('touchstart', (e) => {
            const t = e.changedTouches && e.changedTouches[0];
            if (t) begin(t.clientX, t.clientY, t.identifier, 'touch', cardFrom(e.target));
        }, { passive: true });
        list.addEventListener('touchmove', (e) => {
            const t = Array.from(e.changedTouches || []).find(x => gesture && x.identifier === gesture.id);
            if (t) move(t.clientX, t.clientY, t.identifier, 'touch');
        }, { passive: true });
        list.addEventListener('touchend', (e) => {
            if (!gesture || gesture.source !== 'touch') return;
            const t = Array.from(e.changedTouches || []).find(x => x.identifier === gesture.id);
            if (t) finish(t.clientX, t.clientY, t.identifier, 'touch');
            else cancel('touch');
        }, { passive: true });
        list.addEventListener('touchcancel', () => cancel('touch'), { passive: true });

        list.addEventListener('click', (e) => {
            const button = e.target && e.target.closest ? e.target.closest('[data-notification-action]') : null;
            if (!button) return;
            e.preventDefault();
            e.stopPropagation();
            const card = cardFrom(button);
            if (!card) return;
            const id = card.getAttribute('data-notification-id');
            if (button.getAttribute('data-notification-action') === 'read') this._markNotificationRead(id, card);
            else this._archiveNotification(id, card);
        }, true);
        list.addEventListener('keydown', (e) => {
            const card = cardFrom(e.target);
            if (!card) return;
            const id = card.getAttribute('data-notification-id');
            if (e.key === 'Enter') { e.preventDefault(); this._markNotificationRead(id, card); }
            else if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); this._archiveNotification(id, card); }
        });
    }

    _setNotificationError(message) {
        const errorEl = document.getElementById('qs-notifications-error');
        if (!errorEl) return;
        errorEl.hidden = !message;
        errorEl.textContent = message || '';
    }

    async _markNotificationRead(id, card) {
        const nid = parseInt(id, 10);
        if (!nid || !card) return;
        if (card.getAttribute('data-read') === 'true') return;
        if (card.getAttribute('data-pending') === 'true') return;
        card.setAttribute('data-pending', 'true');
        try {
            const res = await bridge.markNotificationRead(nid);
            if (!res || res.success === false) {
                this._setNotificationError('Mark read failed: ' + ((res && (res.error || res.detail)) || 'provider did not confirm'));
                return;
            }
            this._setNotificationError('');
            await this._pollNotifications();
        } catch (e) {
            this._setNotificationError('Mark read failed: ' + String((e && e.message) || e));
        } finally {
            card.removeAttribute('data-pending');
        }
    }

    async _archiveNotification(id, card) {
        const nid = parseInt(id, 10);
        if (!nid || !card) return;
        if (card.getAttribute('data-pending') === 'true') return;
        card.setAttribute('data-pending', 'true');
        try {
            const res = await bridge.archiveNotification(nid);
            if (!res || res.success === false) {
                this._setNotificationError('Archive failed: ' + ((res && (res.error || res.detail)) || 'provider did not confirm'));
                return;
            }
            this._setNotificationError('');
            card.setAttribute('data-archiving', 'true');
            // Remove only after the hub confirmed the durable archive.
            setTimeout(() => { try { card.remove(); } catch (e) {} }, 160);
            await this._pollNotifications();
        } catch (e) {
            this._setNotificationError('Archive failed: ' + String((e && e.message) || e));
        } finally {
            card.removeAttribute('data-pending');
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
    window.NuxelStatusBar = window.statusBar;
});


function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
}
