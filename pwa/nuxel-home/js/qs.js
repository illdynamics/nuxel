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
    constructor() {
        this.panel = document.getElementById('quick-settings');
        this.isOpen = false;
        this.expanded = false;
        this.state = {
            wifi: false,
            bluetooth: false,
            mobile: false,
            location: false,
            dnd: false,
            flashlight: false,
            rotate: false,
        };
        this._init();
    }

    _init() {
        this._bindEvents();
    }

    _bindEvents() {
        // Toggle on status bar swipe down
        document.addEventListener('gesture:qs', () => this.toggle());

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

        // A33: the verbose-boot tile (created dynamically, see header comment)
        this._buildVerboseBootTile();

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
        this._syncVerboseBoot();
        this.panel.classList.remove('hidden');
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;
        this.expanded = false;
        this.panel.classList.remove('expanded');
        this.panel.classList.add('hidden');
    }

    expand() { if (!this.isOpen) return this.open(); this.expanded = true; this.panel.classList.add('expanded'); }
    collapseOrClose() { if (this.expanded) { this.expanded = false; this.panel.classList.remove('expanded'); } else this.close(); }

    toggle() {
        if (this.isOpen) this.close();
        else this.open();
    }

    async _toggle(id) {
        if (id === 'wifi') {
            await this._setWifiEnabled(!this.state.wifi);
            return;
        }
        // A tile must not become a decorative switch.  Keep unintegrated
        // controls honest until their hardware backend is landed.
        this._osdNotice(`${id} control is unavailable on this build`);
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

    _render() {
        // Update all toggle states from bridge
        this._syncState();
        this._syncVerboseBoot();
    }

    async _syncState() {
        try {
            const status = await bridge.getPhoneStatus();
            if (status.network) {
                this.state.wifi = status.network.wifi_enabled || false;
            }
            if (status.modem) {
                this.state.mobile = status.modem.connected || false;
            }
            this._updateUI();
        } catch (e) {
            // Use defaults
        }
    }

    _updateUI() {
        for (const [id, enabled] of Object.entries(this.state)) {
            const el = document.getElementById(`qs-${id}`);
            if (el) {
                el.dataset.enabled = enabled ? 'true' : 'false';
            }
        }
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
