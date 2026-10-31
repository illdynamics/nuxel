// Nuxel Home - Quick Settings Panel (A32 base, A33 boot-diagnostics tile)
// Manages the quick settings toggles.
//
// A33 adds the BOOT DIAGNOSTICS tile (briq-02b; extended in the bg-02
// verification pass).  It is built here rather than in index.html on purpose:
// the tile must not exist at all on a build without the setting store, and
// building it in JS keeps the A32 markup/screenshot surface byte-identical when
// the feature is off.  The tile reads and writes the SAME durable document the
// console writes (`nuxelctl verbose-boot on|off|animation|verbosity`) and the
// consumer reads at boot (/etc/nuxel/boot/verbose-boot.json), so the UI, the
// console and the early boot stage cannot disagree.
//
//   tap        = verbose boot on/off (show the boot log on the glass)
//   long press = cycle the animation policy standard -> short -> off
// The tile always shows the EFFECTIVE animation policy and its reason, which is
// how the documented precedence (off > short > verbose_boot > standard) stays
// visible instead of surprising the operator after a reboot.

class QuickSettings {
    // A missing Wi-Fi field is NOT evidence that the radio is off.  Only an
    // explicit NetworkManager WirelessEnabled false (or wifi_state=disabled)
    // may render OFF; everything else stays CHECKING/UNKNOWN.
    static wifiRadioState(network) {
        if (!network || typeof network !== 'object') return null;
        if (typeof network.wifi_enabled === 'boolean') return network.wifi_enabled;
        if (network.wifi_state === 'disabled') return false;
        if (network.wifi_connected === true) return true;
        if (['internet', 'connected', 'enabled_disconnected', 'connecting', 'associating']
            .includes(network.wifi_state)) return true;
        return null;
    }

    // Link state is deliberately separate from radio state.  A radio can be ON
    // while no network is connected, and that must not turn the tile OFF.
    static wifiLinkState(network) {
        if (!network || typeof network !== 'object') return null;
        if (['disabled', 'unavailable', 'unmanaged'].includes(network.wifi_state)) return false;
        if (['internet', 'connected'].includes(network.wifi_state)) return true;
        if (typeof network.wifi_connected === 'boolean') return network.wifi_connected;
        if (network.type === 'wifi' && network.connected === true) return true;
        return null;
    }

    constructor() {
        this.panel = document.getElementById('quick-settings');
        this.isOpen = false;
        this.expanded = false;
        // null means UNKNOWN/CHECKING, never a fabricated OFF.
        this.state = {
            wifi: null,
            bluetooth: false,
            mobile: false,
            location: false,
            dnd: false,
            flashlight: false,
            rotate: false,
        };
        this.wifiConnected = null;
        this._init();
    }

    _init() {
        this._bindEvents();
        this._bindIconAssets();
        // Radios can come up a beat after the launcher.  Sync once at startup
        // so the Wi-Fi tile reflects live NetworkManager state without ever
        // inventing a false OFF from the pre-flight placeholder.
        this._syncState();
    }

    // One decode/error owner for custom tile artwork.  The label remains usable
    // if a PNG is missing, and the browser's broken-image glyph is suppressed.
    // Re-opening Quick Settings reuses these nodes, so no second renderer is
    // created (the A44 duplicate-icon regression).
    _bindIconAssets() {
        if (this._iconAssetsBound) return;
        this._iconAssetsBound = true;
        document.querySelectorAll('#quick-settings .qs-item img.qs-icon').forEach(img => {
            const mark = () => {
                img.dataset.iconState = 'failed';
                img.hidden = true;
            };
            img.addEventListener('load', () => { img.dataset.iconState = 'loaded'; img.hidden = false; });
            img.addEventListener('error', mark);
            if (img.complete) {
                if (img.naturalWidth > 0) img.dataset.iconState = 'loaded';
                else mark();
            }
        });
    }

    _bindEvents() {
        // Toggle on status bar swipe down
        // First pull opens the compact panel; a deeper/second pull expands it
        // instead of closing it.  Closing stays an explicit action/back.
        document.addEventListener('gesture:qs', () => this.pull());

        // Individual toggle clicks
        const toggles = ['wifi', 'bluetooth', 'mobile', 'location', 'dnd', 'flashlight', 'rotate'];
        toggles.forEach(id => {
            const el = document.getElementById(`qs-${id}`);
            if (el) {
                el.addEventListener('click', () => {
                    this._toggle(id);
                });
            }
        });

        // A49: long-press the rotate tile for the seven-mode menu.
        const rotateTile = document.getElementById('qs-rotate');
        if (rotateTile) {
            rotateTile.addEventListener('contextmenu', (ev) => { ev.preventDefault(); this._openRotateMenu(); });
            let rt = null, rf = false;
            rotateTile.addEventListener('pointerdown', () => { rf = false; rt = setTimeout(() => { rf = true; this._openRotateMenu(); }, 600); });
            rotateTile.addEventListener('pointerup', () => { if (rt) clearTimeout(rt); if (rf) { /* swallow the click after a long-press */ rotateTile.dataset.longpress = 'true'; setTimeout(() => delete rotateTile.dataset.longpress, 400); } });
            rotateTile.addEventListener('pointerleave', () => { if (rt) clearTimeout(rt); });
        }

        // A33: the verbose-boot tile (created dynamically, see header comment)
        this._buildVerboseBootTile();

        const expandBtn = document.getElementById('qs-expand-toggle');
        if (expandBtn) expandBtn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            if (this.expanded) this.collapseOrClose(); else this.expand();
        });

        // Settings button
        const settingsBtn = document.getElementById('qs-settings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.close();
                appRegistry.launchApp('nuxel-settings');
            });
        }
    }

    // ---- A33: boot diagnostics --------------------------------------------
    // ONE tile drives the SAME durable document the Settings app and
    // `nuxelctl verbose-boot …` write:
    //   tap        -> verbose boot on/off   (show the boot log on the glass)
    //   long press -> cycle the animation policy  standard -> short -> off
    // The tile label always names the EFFECTIVE animation policy and its reason,
    // so the precedence rule (off > short > verbose_boot > standard) is visible
    // in the panel instead of being a surprise after a reboot.
    _buildVerboseBootTile() {
        const panel = this.panel;
        if (!panel || document.getElementById('qs-verbose-boot')) return;
        const rows = panel.querySelectorAll('.qs-row');
        const row = rows[rows.length - 1] || panel;
        const tile = document.createElement('div');
        tile.className = 'qs-item';
        tile.id = 'qs-verbose-boot';
        tile.dataset.enabled = 'false';
        tile.dataset.animation = 'standard';
        tile.title = 'Verbose boot: tap to show the Nuxel boot log on the glass; long-press to cycle the animation policy (standard / short / off)';
        tile.innerHTML = '<span class="qs-icon verbose-icon"></span><span class="qs-label">Verbose<br>boot</span>';
        tile.addEventListener('click', () => {
            // A long press already acted: swallow the click it produces.
            if (this._vbLongPressFired) { this._vbLongPressFired = false; return; }
            this._toggleVerboseBoot();
        });
        this._bindLongPress(tile, () => this._cycleAnimationMode());
        const settingsTile = document.getElementById('qs-settings');
        if (settingsTile && settingsTile.parentNode === row) row.insertBefore(tile, settingsTile);
        else row.appendChild(tile);
        this._syncVerboseBoot();
    }

    // A long press that cannot double-fire, cannot fire on a scroll and cannot
    // leave the timer running after a pointer release.  Same shape the hardware
    // button manager uses (debounce -> duration -> one action).
    _bindLongPress(tile, action) {
        let timer = null;
        let fired = false;
        const HOLD_MS = 600;
        const cancel = () => { if (timer) { clearTimeout(timer); timer = null; } };
        const start = (ev) => {
            fired = false;
            cancel();
            timer = setTimeout(() => {
                timer = null;
                fired = true;
                this._vbLongPressFired = true;
                action();
            }, HOLD_MS);
        };
        const end = () => {
            cancel();
            if (fired) this._vbLongPressFired = true;
        };
        tile.addEventListener('pointerdown', start);
        tile.addEventListener('pointerup', end);
        tile.addEventListener('pointercancel', () => { cancel(); fired = false; });
        tile.addEventListener('pointerleave', () => { cancel(); fired = false; });
        tile.addEventListener('contextmenu', (ev) => { ev.preventDefault(); action(); });
    }

    _syncVerboseBoot() {
        const tile = document.getElementById('qs-verbose-boot');
        const store = window.NuxelSettings;
        if (store && store.subscribe && !this._vbSubscribed) {
            this._vbSubscribed = true;
            store.subscribe((ev) => { if (ev && ev.name === 'verbose-boot') this._syncVerboseBoot(); });
        }
        if (!tile) return;
        const on = !!(store && store.verboseBoot && store.verboseBoot());
        const policy = (store && store.effectiveAnimation)
            ? store.effectiveAnimation()
            : { mode: 'standard', reason: 'store-unavailable' };
        const verbosity = (store && store.verbosityLevel) ? store.verbosityLevel() : 1;
        tile.dataset.enabled = on ? 'true' : 'false';
        tile.dataset.animation = policy.mode;
        tile.dataset.verbosity = String(verbosity);
        tile.title = 'Verbose boot: ' + (on ? 'ON' : 'off')
            + ' | animation: ' + policy.mode + ' (' + policy.reason + ')'
            + ' | verbosity: ' + verbosity
            + '\nTap = verbose boot on/off, long-press = cycle the animation policy';
    }

    _toggleVerboseBoot() {
        const store = window.NuxelSettings;
        if (!store) {
            this._osdNotice('Settings store unavailable');
            return;
        }
        const next = !store.verboseBoot();
        const res = store.setVerboseBoot(next);
        const settle = (r) => {
            this._syncVerboseBoot();
            const how = (r && r.transport) ? r.transport : 'localStorage';
            const policy = store.effectiveAnimation ? store.effectiveAnimation() : { mode: 'standard', reason: '?' };
            this._osdNotice((next ? 'Verbose boot ON' : 'Verbose boot OFF')
                + ' (' + how + ') — next boot: animation ' + policy.mode
                + ' (' + policy.reason + ')');
            if (next && window.NuxelBootLog) window.NuxelBootLog.show();
        };
        if (res && res.then) res.then(settle); else settle(res);
    }

    _cycleAnimationMode() {
        const store = window.NuxelSettings;
        if (!store || !store.setAnimationMode) {
            this._osdNotice('Animation policy needs the settings store');
            return;
        }
        const order = (store.ANIMATION_MODES && store.ANIMATION_MODES.length)
            ? store.ANIMATION_MODES : ['standard', 'short', 'off'];
        const cur = store.animationMode ? store.animationMode() : 'standard';
        const idx = Math.max(0, order.indexOf(cur));
        const next = order[(idx + 1) % order.length];
        const res = store.setAnimationMode(next);
        const settle = (r) => {
            this._syncVerboseBoot();
            const policy = store.effectiveAnimation ? store.effectiveAnimation() : { mode: next, reason: '?' };
            const how = (r && r.transport) ? r.transport : 'localStorage';
            this._osdNotice('Boot animation: ' + next + ' → effective ' + policy.mode
                + ' from the next boot (' + how + ')');
        };
        if (res && res.then) res.then(settle); else settle(res);
    }

    _osdNotice(text) {
        if (window.nuxel && window.nuxel.components && window.nuxel.components.osd) return;
        if (window.osd && window.osd.show) { window.osd.show(text); return; }
        if (window.NuxelOSD && window.NuxelOSD.show) { window.NuxelOSD.show(text); return; }
        const t = document.createElement('div');
        t.className = 'toast';
        t.textContent = text;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 2600);
    }

    open() {
        if (this.isOpen) { this.expand(); return; }
        this.isOpen = true;
        this.expanded = false;
        this._render();
        this.panel.classList.remove('hidden');
        this._setExpandedUI(false);
        try { document.dispatchEvent(new CustomEvent('nuxel:overlay-changed')); } catch (e) {}
        // Bounded refresh while the panel is visible.  Every timer is owned by
        // the panel and stopped in close(); a hidden panel never polls.
        if (!this._locationTimer) {
            this._locationTimer = setInterval(() => {
                if (!this.isOpen) return;
                this._syncLocation();
                if (this.expanded) this._syncIndicators();
            }, 5000);
        }
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;
        this.expanded = false;
        this.panel.classList.remove('expanded');
        this.panel.classList.add('hidden');
        this._setExpandedUI(false);
        if (this._locationTimer) { clearInterval(this._locationTimer); this._locationTimer = null; }
        // Stale indicator responses are ignored by the generation check.
        this._indicatorGeneration = (this._indicatorGeneration || 0) + 1;
        try { document.dispatchEvent(new CustomEvent('nuxel:overlay-changed')); } catch (e) {}
    }

    pull() {
        if (!this.isOpen) this.open();
        else if (!this.expanded) this.expand();
        else this.close();
    }

    _setExpandedUI(on) {
        const details = document.getElementById('qs-details');
        const btn = document.getElementById('qs-expand-toggle');
        if (details) details.hidden = !on;
        if (btn) {
            btn.setAttribute('aria-expanded', on ? 'true' : 'false');
            btn.textContent = on ? 'Hide connection status' : 'More connection status';
        }
    }

    expand() {
        if (!this.isOpen) return this.open();
        this.expanded = true;
        this.panel.classList.add('expanded');
        this._setExpandedUI(true);
        this._syncIndicators();
    }
    collapseOrClose() { if (this.expanded) { this.expanded = false; this.panel.classList.remove('expanded'); this._setExpandedUI(false); } else this.close(); }

    toggle() {
        if (this.isOpen) this.close();
        else this.open();
    }

    async _toggle(id) {
        if (id === 'wifi') {
            // Unknown is not OFF.  Resolve once before deciding; if the bridge
            // still cannot report the radio, request ON and let NetworkManager
            // confirm the resulting state.
            if (this.state.wifi === null) await this._syncState();
            await this._setWifiEnabled(this.state.wifi !== true);
            return;
        }
        if (id === 'rotate') {
            await this._toggleRotate();
            return;
        }
        if (id === 'bluetooth') {
            await this._setBluetoothEnabled(!this.state.bluetooth);
            return;
        }
        if (id === 'location') {
            await this._setLocationEnabled(!this.state.location);
            return;
        }
        if (id === 'flashlight') {
            await this._toggleFlashlight();
            return;
        }
        // A tile must not become a decorative switch.  Keep unintegrated
        // controls honest until their hardware backend is landed.
        this._osdNotice(`${id} control is unavailable on this build`);
    }

    // ---- expanded canonical connection indicators ---------------------
    async _syncIndicators() {
        if (!this.isOpen || !this.expanded) return;
        if (this._indicatorInFlight) return;
        this._indicatorInFlight = true;
        const gen = this._indicatorGeneration || 0;
        try {
            const ind = await bridge.call('system', 'indicators', {});
            if (!this.isOpen || !this.expanded || gen !== (this._indicatorGeneration || 0)) return;
            if (!ind || ind.success === false) {
                this._setDetail('qs-detail-charging', 'unknown', 'Power: unknown');
                this._setDetail('qs-detail-usb', 'unknown', 'USB: unknown');
                this._setDetail('qs-detail-file', 'unknown', 'File transfer: unknown');
                this._setDetail('qs-detail-console', 'unknown', 'Live console: unknown');
                this._setDetail('qs-detail-transports', 'unknown', 'Console transports: unknown');
                return;
            }
            const charging = ind.charging || {};
            const usb = ind.usb_data || {};
            const file = ind.file_transfer || {};
            const live = ind.live_console || {};
            const tr = ind.console_transports || {};
            if (charging.charging === true) this._setDetail('qs-detail-charging', 'active', 'Charging · ' + (charging.battery_level == null ? 'level unknown' : charging.battery_level + '%'));
            else if (charging.external_power === true) this._setDetail('qs-detail-charging', 'external', 'External power · not charging');
            else this._setDetail('qs-detail-charging', 'inactive', 'Battery');
            if (usb.pc_connected === true) this._setDetail('qs-detail-usb', 'active', 'USB data link to host');
            else this._setDetail('qs-detail-usb', 'inactive', 'No USB host link');
            if (file.active === true) this._setDetail('qs-detail-file', 'active', 'File transfer active');
            else if (file.selected === 'file_transfer') this._setDetail('qs-detail-file', 'selected', 'File transfer selected · inactive');
            else this._setDetail('qs-detail-file', 'inactive', 'File transfer inactive');
            if (live.active === true) this._setDetail('qs-detail-console', 'active', 'Live console connected');
            else if (live.service_armed === true) this._setDetail('qs-detail-console', 'armed', 'Live console armed · not connected');
            else this._setDetail('qs-detail-console', 'inactive', 'Live console inactive');
            const parts = [];
            if ((tr.usb || {}).active) parts.push('USB');
            if ((tr.serial || {}).active) parts.push('Serial');
            if ((tr.wlan || {}).active) parts.push('WLAN');
            this._setDetail('qs-detail-transports',
                parts.length ? 'active' : 'inactive',
                'Console transports: ' + (parts.length ? parts.join(' + ') : 'none active'));
        } catch (e) {
            if (this.isOpen && this.expanded) {
                this._setDetail('qs-detail-charging', 'unknown', 'Power: provider error');
                this._setDetail('qs-detail-usb', 'unknown', 'USB: provider error');
            }
        } finally {
            this._indicatorInFlight = false;
        }
    }

    _setDetail(id, state, text) {
        const el = document.getElementById(id);
        if (!el) return;
        el.dataset.state = state;
        const label = el.querySelector('.qs-detail-label');
        if (label) label.textContent = text;
        el.setAttribute('aria-label', text);
    }

    // ---- flashlight: one safe privileged owner ------------------------
    async _syncFlashlight() {
        const tile = document.getElementById('qs-flashlight');
        if (!tile) return;
        try {
            const st = await bridge.call('flashlight', 'status', {});
            if (!st || st.success === false) {
                this.state.flashlight = null;
                tile.dataset.enabled = 'unknown';
                tile.dataset.state = 'unavailable';
                const l = tile.querySelector('.qs-label'); if (l) l.innerHTML = 'Flash<br>unknown';
                tile.title = 'Flashlight status unavailable' + (st && st.error ? (': ' + st.error) : '');
                return;
            }
            const supported = st.supported === true || ['ON', 'OFF', 'BLOCKED_CAMERA', 'THERMAL_LIMIT'].includes(st.state);
            this.state.flashlight = st.state === 'ON';
            tile.dataset.state = st.state || 'UNKNOWN';
            tile.dataset.enabled = !supported ? 'unsupported' : (st.state === 'ON' ? 'true' : 'false');
            const l = tile.querySelector('.qs-label');
            if (l) l.innerHTML = !supported ? 'Flash<br>unsupported'
                : st.state === 'ON' ? 'Flash<br>on'
                : st.state === 'BLOCKED_CAMERA' ? 'Flash<br>camera busy'
                : st.state === 'THERMAL_LIMIT' ? 'Flash<br>thermal'
                : st.state === 'OFF' ? 'Flash<br>off' : 'Flash<br>unknown';
            tile.title = (st.reason || ('Flashlight: ' + (st.state || 'unknown')))
                + (st.max_on_seconds ? ('\nPolicy max on: ' + st.max_on_seconds + ' s') : '')
                + '\nTap = toggle through the privileged owner';
        } catch (e) {
            this.state.flashlight = null;
            tile.dataset.enabled = 'unknown';
            tile.dataset.state = 'error';
            const l = tile.querySelector('.qs-label'); if (l) l.innerHTML = 'Flash<br>unknown';
            tile.title = 'Flashlight provider error: ' + (e && e.message ? e.message : 'bridge error');
        }
    }

    async _toggleFlashlight() {
        const tile = document.getElementById('qs-flashlight');
        if (tile) tile.dataset.pending = 'true';
        try {
            // Always ask the owner; never paint ON optimistically.
            const res = await bridge.call('flashlight', 'toggle', {});
            if (!res || res.success === false) {
                throw new Error((res && (res.reason || res.error)) || 'flashlight owner unavailable');
            }
            if (res.state === 'UNSUPPORTED' || res.state === 'NOT_SUPPORTED_ON_DEVICE') {
                this._osdNotice('Flashlight not supported on this device');
            } else if (res.state === 'BLOCKED_CAMERA') {
                this._osdNotice('Flashlight blocked: camera owns the LED');
            } else if (res.state === 'THERMAL_LIMIT') {
                this._osdNotice('Flashlight blocked by the thermal policy');
            } else if (res.state === 'ON') {
                this._osdNotice('Flashlight on (bounded by the LED policy)');
                this._hapticSwitch();
            } else if (res.state === 'OFF') {
                this._osdNotice('Flashlight off');
                this._hapticSwitch();
            } else {
                this._osdNotice('Flashlight: ' + (res.state || 'unknown state'));
            }
            await this._syncFlashlight();
        } catch (error) {
            await this._syncFlashlight();
            this._osdNotice('Flashlight unchanged: ' + (error && error.message ? error.message : 'owner unavailable'));
        } finally {
            if (tile) delete tile.dataset.pending;
        }
    }

    async _setWifiEnabled(enabled) {
        const el = document.getElementById('qs-wifi');
        if (el) el.dataset.pending = 'true';
        try {
            const grant = await bridge.requestCapability('network:manage', 'Change Wi-Fi power');
            if (grant === false) throw new Error('Network control permission denied');
            const result = await bridge.call('network', 'wifi-enabled', { enabled: !!enabled });
            if (!result || result.success !== true || Boolean(result.wifi_enabled) !== Boolean(enabled)) {
                throw new Error((result && result.error) || 'NetworkManager did not confirm Wi-Fi state');
            }
            this.state.wifi = Boolean(result.wifi_enabled);
            this._updateUI();
            // Refresh the link separately; the radio result already confirmed
            // ON/OFF and must not be overwritten by a missing network field.
            this._syncState({ preserveRadio: true });
            document.dispatchEvent(new CustomEvent('qs:toggle', {
                detail: { id: 'wifi', enabled: this.state.wifi }, bubbles: true,
            }));
            if (window.NuxelHost && window.NuxelHost.available) window.NuxelHost.action('haptics-switch');
            else if (navigator.vibrate) navigator.vibrate(10);
        } catch (error) {
            await this._syncState();
            this._osdNotice('Wi-Fi unchanged: ' + (error && error.message ? error.message : 'backend unavailable'));
        } finally {
            if (el) delete el.dataset.pending;
        }
    }

    // ---- orientation (A53): tap = forced portrait<->auto, long-press = five primary + advanced modes ----
    async _orientationState() {
        try {
            const res = await bridge.call('orientation', 'get', {});
            return (res && typeof res === 'object') ? res : { mode: 'portrait' };
        } catch (e) {
            return { mode: 'portrait', error: String(e && e.message || e) };
        }
    }

    async _toggleRotate() {
        const cur = await this._orientationState();
        const next = (cur.mode === 'auto') ? 'portrait' : 'auto';
        await this._setOrientation(next);
    }

    async _setOrientation(mode) {
        const tile = document.getElementById('qs-rotate');
        if (tile) tile.dataset.pending = 'true';
        try {
            const res = await bridge.call('orientation', 'set', { mode: mode });
            if (!res || res.success !== true) {
                throw new Error((res && res.error) || 'orientation backend unavailable');
            }
            this.orientationMode = res.mode || mode;
            await this._syncRotate();
            this._osdNotice('Rotation: ' + (res.mode_label || res.mode));
            this._hapticSwitch();
        } catch (error) {
            await this._syncRotate();
            this._osdNotice('Rotation unchanged: ' + (error && error.message ? error.message : 'backend unavailable'));
        } finally {
            if (tile) delete tile.dataset.pending;
        }
    }

    _hapticSwitch() {
        if (window.NuxelHost && window.NuxelHost.available) window.NuxelHost.action('haptics-switch');
        else if (navigator.vibrate) navigator.vibrate(10);
    }

    async _syncRotate() {
        const tile = document.getElementById('qs-rotate');
        if (!tile) return;
        const st = await this._orientationState();
        this.orientationMode = st.mode || 'portrait';
        const auto = !!(st.auto);
        const sensor = st.sensor;
        const sensorOk = !!(sensor && sensor.available);
        tile.dataset.enabled = auto ? 'true' : 'false';
        tile.dataset.mode = this.orientationMode;
        const label = tile.querySelector('.qs-label');
        // Show the REAL selected mode (one of seven), never a bare Locked/Auto.
        if (label) label.textContent = this._rotateModeLabel(this.orientationMode);
        tile.title = 'Rotation: ' + (st.mode_label || this._rotateModeLabel(this.orientationMode))
            + ' | effective ' + (st.effective_orientation === undefined ? '?' : st.effective_orientation + '°')
            + (auto ? (' | sensor ' + (sensorOk ? 'available' : 'unavailable')) : '')
            + '\nTap = forced portrait/auto, long-press = all seven modes';
    }

    _rotateModes() {
        return [
            ['auto', 'Auto'], ['auto-portrait', 'Auto Portrait'], ['auto-landscape', 'Auto Landscape'],
            ['portrait', 'Forced Portrait'], ['landscape', 'Forced Landscape'],
            ['reverse-portrait', 'Reverse Portrait (advanced)'], ['reverse-landscape', 'Reverse Landscape (advanced)'],
        ];
    }

    _rotateModeLabel(mode) {
        const hit = this._rotateModes().find(([m]) => m === mode);
        return hit ? hit[1] : (mode || 'Portrait');
    }

    _openRotateMenu() {
        if (document.getElementById('qs-rotate-menu')) return;
        const modes = this._rotateModes();
        const menu = document.createElement('div');
        menu.id = 'qs-rotate-menu';
        menu.className = 'qs-rotate-menu';
        modes.forEach(([id, label]) => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'qs-rotate-item';
            item.textContent = label;
            if (id === this.orientationMode) item.classList.add('selected');
            item.addEventListener('click', (ev) => {
                ev.stopPropagation();
                menu.remove();
                this._setOrientation(id);
            });
            menu.appendChild(item);
        });
        const dismiss = (ev) => { if (menu && !menu.contains(ev.target)) menu.remove(); };
        menu.addEventListener('pointerdown', (ev) => ev.stopPropagation());
        document.body.appendChild(menu);
        setTimeout(() => document.addEventListener('pointerdown', dismiss, { once: true }), 0);
    }

    // ---- Bluetooth (A73): real BlueZ/rfkill/HCI status + powered toggle ----
    //
    // The provider reports a tri-state:
    //   powered=true   radio ON
    //   powered=false  BlueZ says the adapter is Powered=false
    //   powered=null   controller/service not ready yet -> UNKNOWN, never OFF
    // A registered hci0 plus a powered BlueZ adapter is the verified S10+
    // state; a missing adapter shows the real kernel/firmware blocker.
    static bluetoothRadioState(st) {
        if (!st || typeof st !== 'object') return null;
        if (typeof st.powered === 'boolean') return st.powered;
        if (st.state === 'off') return false;
        if (st.state === 'on' || st.state === 'discovering') return true;
        return null;
    }

    _bluetoothLabel(st) {
        if (!st) return 'Bluetooth<br>unknown';
        const s = st.state;
        if (s === 'on') return st.discovering ? 'Bluetooth<br>discovering' : 'Bluetooth<br>on';
        if (s === 'off') return 'Bluetooth<br>off';
        if (s === 'hardware_blocked') return 'Bluetooth<br>blocked';
        if (s === 'service_unavailable') return 'Bluetooth<br>no radio';
        if (s === 'unknown') return 'Bluetooth<br>checking';
        return 'Bluetooth<br>unknown';
    }

    _bluetoothDetail(st) {
        if (!st) return 'Bluetooth: status unavailable';
        const lines = ['Bluetooth: ' + (st.state || 'unknown')];
        if (st.adapter_present === false) lines.push('controller: no hci0 registered');
        else if (st.hci_devices && st.hci_devices.length) lines.push('controller: ' + st.hci_devices.join(', '));
        if (st.adapter_address) lines.push('address: ' + st.adapter_address);
        if (st.rfkill_present) {
            lines.push('rfkill: ' + (st.rfkill_soft_blocked ? 'soft-blocked' : 'unblocked') +
                (st.rfkill_hard_blocked ? ', HARD-blocked' : ''));
        }
        if (st.discovering === true) lines.push('discovery: active');
        else if (st.discovering === false) lines.push('discovery: idle');
        if (st.blocker) lines.push('blocker: ' + st.blocker);
        if (st.detail) lines.push(st.detail);
        lines.push('Tap = power on/off (real BlueZ/rfkill state)');
        return lines.join('\n');
    }

    async _syncBluetooth() {
        const tile = document.getElementById('qs-bluetooth');
        if (!tile) return;
        try {
            const st = await bridge.call('bluetooth', 'status', {});
            if (!st || st.success === false) {
                // A bridge/provider failure is UNKNOWN, never a fabricated OFF.
                this.state.bluetooth = null;
                tile.dataset.enabled = 'unknown';
                tile.dataset.state = 'unavailable';
                const label = tile.querySelector('.qs-label');
                if (label) label.innerHTML = 'Bluetooth<br>unknown';
                tile.title = 'Bluetooth status unavailable' +
                    (st && st.error ? (': ' + st.error) : '');
                return;
            }
            const radio = QuickSettings.bluetoothRadioState(st);
            this.state.bluetooth = radio;
            const known = typeof radio === 'boolean';
            tile.dataset.enabled = known ? (radio ? 'true' : 'false') : 'unknown';
            tile.dataset.state = (st.state) ? st.state : 'unknown';
            tile.dataset.adapterPresent = st.adapter_present === true ? 'true' : 'false';
            if (st.adapter_present === false) tile.dataset.state = 'no_adapter';
            if (st.discovering === true) tile.dataset.discovering = 'true';
            else delete tile.dataset.discovering;
            const label = tile.querySelector('.qs-label');
            if (label) label.innerHTML = this._bluetoothLabel(st);
            tile.title = this._bluetoothDetail(st);
        } catch (e) {
            // Never turn a failed status read into OFF.
            this.state.bluetooth = null;
            tile.dataset.enabled = 'unknown';
            tile.dataset.state = 'error';
            const label = tile.querySelector('.qs-label');
            if (label) label.innerHTML = 'Bluetooth<br>unknown';
            tile.title = 'Bluetooth status read failed: ' +
                (e && e.message ? e.message : 'bridge error');
        }
    }

    async _setBluetoothEnabled(enabled) {
        const el = document.getElementById('qs-bluetooth');
        if (el) el.dataset.pending = 'true';
        try {
            const grant = await bridge.requestCapability('bluetooth:manage', 'Toggle Bluetooth radio');
            if (grant === false) throw new Error('Bluetooth control permission denied');
            const result = await bridge.call('bluetooth', 'power', { enabled: !!enabled });
            if (!result || result.success !== true) {
                throw new Error((result && (result.error || result.detail)) || 'Bluetooth radio did not confirm');
            }
            this.state.bluetooth = Boolean(result.powered);
            this._updateUI();
            this._hapticSwitch();
            await this._syncBluetooth();
        } catch (error) {
            await this._syncBluetooth();
            this._osdNotice('Bluetooth unchanged: ' + (error && error.message ? error.message : 'backend unavailable'));
        } finally {
            if (el) delete el.dataset.pending;
        }
    }

    // ---- Location (A73/27000): canonical provider state, never a fix claim ----
    _locationLabel(st) {
        const state = (st && st.state) || (!st ? 'unavailable' : (st.enabled ? 'no_fix' : 'disabled'));
        const kind = st && (st.fix_kind || '');
        const source = st && String(st.fix_source || '');
        const isNetwork = kind === 'network' || /^(network|wifi|ip)/.test(source);
        switch (state) {
            case 'fixed':
                if (kind === 'satellite' || st.gnss_fix === true) return 'Location<br>GNSS fix';
                if (isNetwork) return 'Location<br>network fix';
                return 'Location<br>provider fix';
            case 'stale':
                if (isNetwork) return 'Location<br>network stale';
                return 'Location<br>stale fix';
            case 'searching': return 'Location<br>searching';
            case 'no_fix': return 'Location<br>no fix';
            case 'disabled': return 'Location<br>off';
            case 'error': return 'Location<br>error';
            case 'unavailable':
            default: return 'Location<br>unavailable';
        }
    }

    async _syncLocation() {
        const tile = document.getElementById('qs-location');
        if (!tile) return;
        try {
            const st = await bridge.call('location', 'get-status', {});
            if (!st || st.success === false) throw new Error((st && (st.error || st.detail)) || 'provider unavailable');
            const state = st.state || (st.enabled ? (st.location_fix_available ? 'fixed' : 'no_fix') : 'disabled');
            this.state.location = !!st.enabled;
            tile.dataset.enabled = this.state.location ? 'true' : 'false';
            tile.dataset.state = state;
            const label = tile.querySelector('.qs-label');
            if (label) label.innerHTML = this._locationLabel(st);
            const age = (typeof st.last_fix_age_s === 'number') ? (' | last provider fix ' + Math.round(st.last_fix_age_s) + ' s ago') : '';
            const acc = (typeof st.accuracy === 'number') ? (' | accuracy ±' + Math.round(st.accuracy) + ' m') : '';
            const provider = (st.provider || 'unknown') + ' (' + (st.provider_ready ? 'ready' : (st.provider_available ? 'installed, not answering' : 'unavailable')) + ')';
            const source = st.fix_source ? (' | source=' + st.fix_source + (st.fix_kind ? ' (' + st.fix_kind + ')' : '')) : '';
            tile.title = 'Location: ' + state
                + ' | provider=' + provider
                + source + age + acc
                + (st.detail ? ('\n' + st.detail) : '')
                + (st.gnss && st.gnss.blocker ? ('\nGNSS: ' + st.gnss.blocker) : '')
                + '\nTap = global location permission/provider ON/OFF (independent of a position fix)';
        } catch (e) {
            this.state.location = false;
            tile.dataset.enabled = 'false';
            tile.dataset.state = 'unavailable';
            const label = tile.querySelector('.qs-label');
            if (label) label.innerHTML = this._locationLabel(null);
            tile.title = 'Location provider unavailable: ' + (e && e.message ? e.message : 'bridge error');
        }
    }

    async _setLocationEnabled(enabled) {
        const el = document.getElementById('qs-location');
        if (el) el.dataset.pending = 'true';
        try {
            let result = await bridge.call('location', 'set-enabled', { enabled: !!enabled });
            if (result && result.error_code === 'CAPABILITY_DENIED') {
                const grant = await bridge.requestCapability('location:manage', 'Toggle location policy');
                if (grant === false || (grant && grant.granted === false)) {
                    throw new Error((grant && grant.error) || 'Location control permission denied');
                }
                result = await bridge.call('location', 'set-enabled', { enabled: !!enabled });
            }
            if (!result || result.success !== true) {
                throw new Error((result && (result.error || result.detail)) || 'Location policy did not confirm');
            }
            this.state.location = Boolean(result.enabled);
            this._updateUI();
            this._hapticSwitch();
            this._syncLocation();
            document.dispatchEvent(new CustomEvent('nuxel:location-policy', {
                detail: { enabled: this.state.location }, bubbles: true,
            }));
        } catch (error) {
            await this._syncLocation();
            this._osdNotice('Location unchanged: ' + (error && error.message ? error.message : 'backend unavailable'));
        } finally {
            if (el) delete el.dataset.pending;
        }
    }

    _render() {
        // PWNAGE-43000: paint the panel from cached state first, then refresh
        // providers on the next frame.  The panel must become interactive
        // immediately even if NetworkManager/BlueZ/GeoClue are slow.
        this._syncVerboseBoot();
        const now = Date.now();
        const refresh = () => {
            if (!this.isOpen) return;
            if (!this._lastSyncAt || now - this._lastSyncAt > 15000) {
                this._lastSyncAt = Date.now();
                this._syncState();
                this._syncRotate();
            }
        };
        const raf = (window.requestAnimationFrame || (fn => setTimeout(fn, 0)));
        raf(() => raf(refresh));
    }

    async _syncState(options) {
        // One provider refresh at a time.  Opening the panel while the
        // startup refresh was still in flight used to start a second
        // NetworkManager/BlueZ/GeoClue round-trip and repaint every tile twice.
        if (this._stateSyncPromise) return this._stateSyncPromise;
        this._stateSyncPromise = this._syncStateOnce(options);
        try { return await this._stateSyncPromise; }
        finally { this._stateSyncPromise = null; }
    }

    async _syncStateOnce(options) {
        const preserveRadio = !!(options && options.preserveRadio);
        const retainRadio = preserveRadio && typeof this.state.wifi === 'boolean';
        try {
            const status = await bridge.getPhoneStatus();
            const hasNetwork = status && status.network &&
                typeof status.network === 'object';
            if (hasNetwork) {
                const net = status.network;
                // Preserve the tri-state: missing fields remain UNKNOWN.
                const radio = QuickSettings.wifiRadioState(net);
                if (radio !== null || !retainRadio) this.state.wifi = radio;
                const link = QuickSettings.wifiLinkState(net);
                if (link !== null || !preserveRadio) this.wifiConnected = link;
            } else {
                if (!retainRadio) this.state.wifi = null;
                if (!preserveRadio) this.wifiConnected = null;
            }
            if (status && status.modem) {
                this.state.mobile = status.modem.connected || false;
            }
        } catch (e) {
            // An unavailable bridge is UNKNOWN, not a fabricated OFF.
            if (!retainRadio) this.state.wifi = null;
            if (!preserveRadio) this.wifiConnected = null;
        }
        this._updateUI();
        this._syncBluetooth();
        this._syncLocation();
        this._syncFlashlight();
    }

    _wifiLinkLabel() {
        if (this.wifiConnected === null) return 'network unknown';
        return this.wifiConnected ? 'network connected' : 'radio on, not connected';
    }

    // State-only diagnostic for the live launcher log.  It emits when the
    // effective radio/link state changes, never on every poll, and never
    // includes an SSID, address or credential.
    _traceWifiState() {
        const radio = typeof this.state.wifi === 'boolean'
            ? (this.state.wifi ? 'ON' : 'OFF') : 'UNKNOWN';
        const link = typeof this.wifiConnected === 'boolean'
            ? (this.wifiConnected ? 'CONNECTED' : 'DISCONNECTED') : 'UNKNOWN';
        const key = radio + '/' + link;
        if (key === this._wifiTraceKey) return;
        this._wifiTraceKey = key;
        const line = 'QS_WIFI radio=' + radio + ' link=' + link;
        try {
            const diag = window.webkit && window.webkit.messageHandlers &&
                window.webkit.messageHandlers.nuxelDiag;
            if (diag) diag.postMessage(line);
            else if (window.NuxelHost && window.NuxelHost.available && window.NuxelHost.statusRead) {
                // No native diag channel on the desktop/VM host.
            } else if (console && console.log) console.log('[qs] ' + line);
        } catch (e) { /* evidence must never break the tile */ }
    }

    _updateUI() {
        for (const [id, enabled] of Object.entries(this.state)) {
            if (id === 'wifi') continue;
            const el = document.getElementById(`qs-${id}`);
            if (!el) continue;
            const next = enabled ? 'true' : 'false';
            if (el.dataset.enabled !== next) el.dataset.enabled = next;
        }

        const wifi = document.getElementById('qs-wifi');
        if (!wifi) return;
        const radioKnown = typeof this.state.wifi === 'boolean';
        const linkKnown = typeof this.wifiConnected === 'boolean';
        wifi.dataset.enabled = radioKnown ? (this.state.wifi ? 'true' : 'false') : 'unknown';
        wifi.dataset.radioEnabled = radioKnown ? (this.state.wifi ? 'true' : 'false') : 'unknown';
        wifi.dataset.connected = linkKnown ? (this.wifiConnected ? 'true' : 'false') : 'unknown';
        const label = wifi.querySelector('.qs-label');
        if (label) {
            if (!radioKnown) label.innerHTML = 'WiFi<br>checking';
            else if (!this.state.wifi) label.innerHTML = 'WiFi<br>off';
            else if (this.wifiConnected === true) label.innerHTML = 'WiFi<br>linked';
            else label.innerHTML = 'WiFi<br>on';
        }
        const radio = radioKnown ? (this.state.wifi ? 'ON' : 'OFF') : 'CHECKING/UNKNOWN';
        wifi.title = 'Wi-Fi radio: ' + radio + ' | ' + this._wifiLinkLabel()
            + '\nTap = turn the Wi-Fi radio on/off';
        this._traceWifiState();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Load the durable settings document first so the tile reflects the stored
    // value immediately (and migrates any pre-A33 local flag once).
    if (window.NuxelSettings) {
        try { window.NuxelSettings.load('verbose-boot'); } catch (e) { /* offline is fine */ }
    }
    window.qs = new QuickSettings();
});
