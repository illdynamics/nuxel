// Nuxel Home - Quick Settings Panel (A32 base, A33 verbose-boot tile)
// Manages the quick settings toggles.
//
// A33 adds the VERBOSE BOOT tile (briq-02b).  It is built here rather than in
// index.html on purpose: the tile must not exist at all on a build without the
// setting store, and building it in JS keeps the A32 markup/screenshot surface
// byte-identical when the feature is off.  The tile reads and writes the SAME
// durable document the console writes (`nuxelctl verbose-boot on|off`) and the
// consumer reads at boot (/etc/nuxel/boot/verbose-boot.json), so the UI, the
// console and the early boot stage cannot disagree.

class QuickSettings {
    constructor() {
        this.panel = document.getElementById('quick-settings');
        this.isOpen = false;
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

    // ---- A33: verbose boot -------------------------------------------------
    _buildVerboseBootTile() {
        const panel = this.panel;
        if (!panel || document.getElementById('qs-verbose-boot')) return;
        const rows = panel.querySelectorAll('.qs-row');
        const row = rows[rows.length - 1] || panel;
        const tile = document.createElement('div');
        tile.className = 'qs-item';
        tile.id = 'qs-verbose-boot';
        tile.dataset.enabled = 'false';
        tile.title = 'Verbose boot: show the Nuxel boot log on the glass and shorten the boot animation';
        tile.innerHTML = '<span class="qs-icon verbose-icon"></span><span class="qs-label">Verbose<br>boot</span>';
        tile.addEventListener('click', () => this._toggleVerboseBoot());
        const settingsTile = document.getElementById('qs-settings');
        if (settingsTile && settingsTile.parentNode === row) row.insertBefore(tile, settingsTile);
        else row.appendChild(tile);
        this._syncVerboseBoot();
    }

    _syncVerboseBoot() {
        const tile = document.getElementById('qs-verbose-boot');
        if (!tile) return;
        const store = window.NuxelSettings;
        const on = !!(store && store.verboseBoot && store.verboseBoot());
        tile.dataset.enabled = on ? 'true' : 'false';
        if (store && store.subscribe && !this._vbSubscribed) {
            this._vbSubscribed = true;
            store.subscribe((ev) => { if (ev && ev.name === 'verbose-boot') this._syncVerboseBoot(); });
        }
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
            this._osdNotice(next
                ? 'Verbose boot ON (applies from the next boot, ' + how + ')'
                : 'Verbose boot OFF (' + how + ')');
            if (next && window.NuxelBootLog) window.NuxelBootLog.show();
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
        if (this.isOpen) return;
        this.isOpen = true;
        this._render();
        this._syncVerboseBoot();
        this.panel.classList.remove('hidden');
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;
        this.panel.classList.add('hidden');
    }

    toggle() {
        if (this.isOpen) this.close();
        else this.open();
    }

    _toggle(id) {
        this.state[id] = !this.state[id];
        const el = document.getElementById(`qs-${id}`);
        if (el) {
            el.dataset.enabled = this.state[id] ? 'true' : 'false';
        }
        
        // Dispatch event
        const event = new CustomEvent('qs:toggle', {
            detail: { id, enabled: this.state[id] },
            bubbles: true,
        });
        document.dispatchEvent(event);
        
        // Provide haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(10);
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
