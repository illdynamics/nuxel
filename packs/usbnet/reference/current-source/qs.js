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

// PWNAGE-96000: bounded, event-only diagnostics.  It emits one line per
// open/close/provider-sync transition through the existing nuxelDiag channel;
// there is no timer and no user data (no SSID, address, credential or path).
function nuxelPerfDiag(tag, fields) {
    try {
        const line = tag + ' ' + JSON.stringify(fields || {});
        const diag = window.webkit && window.webkit.messageHandlers &&
            window.webkit.messageHandlers.nuxelDiag;
        if (diag) diag.postMessage(line);
        else if (console && console.log) console.log('[perf] ' + line);
    } catch (e) { /* diagnostics must never break the panel */ }
}

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
        // PWNAGE-94000: ONE top-bar state machine.
        //   0 TOPBAR_HIDDEN   (no panel; an immersive app may also hide the bar)
        //   1 TOPBAR_STANDARD (desktop bar visible, panel closed)
        //   2 TOPBAR_EXPANDED (Quick Settings tiles)
        //   3 TOPBAR_EXTENDED (details + notification list)
        // Opening is progressive, closing is atomic: any upward gesture goes
        // straight to 0 (no per-level reverse walk).
        this.level = 0;
        this.expanded = false;
        this.extended = false;
        this.isOpen = false;
        this.shadeState = 'hidden';
        // The DOM-free machine is the single owner of level transitions.
        this.machine = (typeof window !== 'undefined' && window.NuxelTopBarMachine)
            ? new window.NuxelTopBarMachine() : null;
        // null means UNKNOWN/CHECKING, never a fabricated OFF.
        this.state = {
            wifi: null,
            bluetooth: false,
            mobile: false,
            location: false,
            dnd: null,
            flashlight: false,
            rotate: false,
            nfc: null,
            fingerprint: null,
            camera: null,
            microphone: null,
        };
        this.privacy = { nfc: null, fingerprint: null, camera: null, microphone: null };
        this._privacyGeneration = 0;
        this._privacyInFlight = false;
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
        // PWNAGE-90000 direction-aware contract:
        //   closed + down                 -> compact shade
        //   compact + down                -> expanded Quick Settings
        //   compact/expanded + up         -> closed (upward dismiss always)
        //   expanded + down               -> closed
        // `revealed` means the compact status bar was already revealed by the
        // fullscreen top-edge gesture; the next down pull opens expanded QS.
        document.addEventListener('gesture:qs', (ev) => {
            const direction = ev && ev.detail && ev.detail.direction;
            const revealed = !!(ev && ev.detail && ev.detail.revealed);
            this.pull(direction, { revealed });
        });
        this._bindPullGesture();

        // Individual toggle clicks
        const toggles = ['wifi', 'bluetooth', 'mobile', 'location', 'dnd', 'flashlight', 'rotate',
                         'nfc', 'fingerprint', 'camera', 'microphone'];
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
        const rows = panel.querySelectorAll('.qs-row:not(.qs-privacy-row)');
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

    // ---- progressive top-bar state machine --------------------------------
    // Level 0 is hidden, level 1 is the standard desktop bar, level 2 is the
    // expanded Quick Settings panel and level 3 is the extended panel.  The
    // model is intentionally asymmetric: advance() moves one step at a time,
    // while closeAll() removes every level at once.
    static get LEVEL_HIDDEN() { return 0; }
    static get LEVEL_STANDARD() { return 1; }
    static get LEVEL_EXPANDED() { return 2; }
    static get LEVEL_EXTENDED() { return 3; }

    get levelName() {
        return this.level <= 0 ? 'hidden'
            : this.level === 1 ? 'standard'
            : this.level === 2 ? 'expanded' : 'extended';
    }

    _setLevel(level, reason) {
        const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
        const wasOpen = this.isOpen;
        let next = Math.max(0, Math.min(3, Number(level) || 0));
        if (this.machine) {
            this.machine.set(next, reason);
            next = this.machine.level;
        }
        const changed = next !== this.level;
        this.level = next;
        this.expanded = next >= 2;
        this.extended = next >= 3;
        this.isOpen = next >= 2;
        if (this.panel) {
            this.panel.classList.toggle('hidden', next < 2);
            this.panel.classList.toggle('expanded', next >= 2);
            this.panel.classList.toggle('extended', next >= 3);
        }
        this._setExpandedUI(next);
        this._emitState(reason);
        if (next >= 2) {
            this._ensureVisibleRefresh();
            // PWNAGE-96000: this call was missing.  The panel's cache-first
            // renderer (and its bounded post-paint provider refresh) existed but
            // was never invoked on open, so a panel opened long after startup
            // showed stale tiles.  It is still cache-first: the DOM is painted
            // immediately and providers are refreshed after two animation frames.
            this._render();
        } else {
            this._stopVisibleRefresh();
        }
        const elapsed = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0;
        if (next >= 2 && !wasOpen) {
            const raf = (window.requestAnimationFrame || (fn => setTimeout(fn, 0)));
            raf(() => raf(() => nuxelPerfDiag('QS_PERF', {
                event: 'open', ms: Math.round(((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0) * 10) / 10,
                sync_ms: this._lastSyncMs || null,
                level: next, reason: String(reason || ''),
                tiles: this.panel ? this.panel.querySelectorAll('.qs-item').length : 0,
                cache_first: true,
            })));
        } else if (next < 2 && wasOpen) {
            nuxelPerfDiag('QS_PERF', { event: 'close', ms: Math.round(elapsed * 10) / 10,
                                       level: next, reason: String(reason || '') });
        }
        return changed;
    }

    _ensureVisibleRefresh() {
        if (this._locationTimer) return;
        // Bounded refresh while the panel is visible.  Every timer is owned by
        // the panel and stopped in closeAll(); a hidden panel never polls.
        this._locationTimer = setInterval(() => {
            if (!this.isOpen) return;
            this._syncLocation();
            this._syncIndicators();
            this._syncPrivacy();
        }, 5000);
    }

    _stopVisibleRefresh() {
        if (this._locationTimer) { clearInterval(this._locationTimer); this._locationTimer = null; }
        // Stale indicator responses are ignored by the generation check.
        this._indicatorGeneration = (this._indicatorGeneration || 0) + 1;
        this._privacyGeneration = (this._privacyGeneration || 0) + 1;
    }

    advance(reason) {
        if (this.machine) {
            const target = this.machine.nextLevel();
            if (target === this.level) { this._emitState(reason || 'extended-hold'); return false; }
            return this._setLevel(target, reason || 'advance');
        }
        if (this.level >= 3) { this._emitState(reason || 'extended-hold'); return false; }
        if (this.level <= 0) return this._setLevel(1, reason || 'standard');
        return this._setLevel(this.level + 1, reason || 'advance');
    }

    showStandard(reason) { return this._setLevel(1, reason || 'standard'); }

    // Kept for callers that legitimately want the full panel at once (the
    // hardware Quick Settings button and the notification bell).
    open() { return this._setLevel(2, 'open'); }
    expand() { return this._setLevel(Math.max(2, this.level + (this.level >= 2 ? 1 : 0)), 'expand'); }
    extend() { return this._setLevel(3, 'extend'); }

    // Atomic upward dismissal: every open level disappears in ONE transition.
    close() { return this.closeAll('close'); }
    closeAll(reason) {
        if (this.level === 0 && !this.isOpen) {
            if (this.machine) this.machine.closeAll(reason || 'close-all');
            if (this.panel) this.panel.classList.add('hidden');
            return false;
        }
        return this._setLevel(0, reason || 'close-all');
    }

    // `direction` is 'up', 'down' or undefined (legacy cyclic pull).
    //   hidden/standard + down -> standard / expanded (one step only)
    //   expanded + down         -> extended
    //   any level + up          -> hidden (atomic)
    pull(direction, options) {
        const desktopBarVisible = !document.body.classList.contains('app-immersive') &&
            !document.body.classList.contains('app-status-hidden');
        if (direction === 'up') { this.closeAll('up'); return; }
        if (direction === 'down') {
            if (this.level >= 3) return;
            if (this.level === 0 && desktopBarVisible) {
                // The desktop already shows the standard bar, so the first
                // physical pull there opens the panel instead of doing nothing.
                this._setLevel(2, 'desktop-first-pull');
                return;
            }
            this.advance('down');
            return;
        }
        // Legacy cyclic pull: advance until extended, then dismiss.
        if (this.level >= 3) this.closeAll('cyclic-close');
        else this.advance('cyclic');
    }

    // One state-change event keeps CSS, aria-expanded and native/Home chrome
    // observers in lockstep.  `state` remains the legacy compact/expanded
    // vocabulary for existing listeners; `level` is the authoritative value.
    _emitState(reason) {
        const state = this.levelName;
        this.shadeState = state;
        try {
            this.panel.setAttribute('data-shade-state', state);
            this.panel.setAttribute('data-shade-level', String(this.level));
            this.panel.setAttribute('aria-expanded', this.level >= 2 ? 'true' : 'false');
        } catch (e) {}
        try {
            document.dispatchEvent(new CustomEvent('nuxel:qs-state', {
                detail: { state, level: this.level, reason: reason || '' },
            }));
            document.dispatchEvent(new CustomEvent('nuxel:top-state', {
                detail: { state, level: this.level, reason: reason || '' },
            }));
        } catch (e) {}
        try { document.dispatchEvent(new CustomEvent('nuxel:overlay-changed')); } catch (e) {}
    }

    // Swiping the Quick Settings panel itself follows the same contract as a
    // pull on the status bar.  Pointer and touch are both observed because
    // WebKit cancels the pointer stream once a pan starts; the first stream to
    // cross the threshold wins and the other is ignored for a short settle
    // window.  A swipe never activates the tile under the finger.
    _bindPullGesture() {
        const panel = this.panel;
        if (!panel || this._pullGestureBound) return;
        this._pullGestureBound = true;
        const MIN_PULL = 42;
        const MAX_SKEW = 70;
        let start = null;
        let lastHandledAt = 0;
        const begin = (x, y, id, source) => {
            start = this.isOpen ? { x, y, id, source } : null;
        };
        const finish = (x, y, id, source) => {
            const gesture = start;
            if (!gesture || gesture.source !== source) return;
            if (id !== undefined && gesture.id !== undefined && id !== gesture.id) return;
            start = null;
            if (!this.isOpen) return;
            const dx = x - gesture.x;
            const dy = y - gesture.y;
            if (Math.abs(dy) < MIN_PULL || Math.abs(dx) > MAX_SKEW ||
                Math.abs(dx) > Math.abs(dy) * 1.1 + 8) return;
            // A down-swipe while reading scrolled details belongs to the
            // details scroller, not to the panel expansion gesture.
            if (dy > 0 && (panel.scrollTop || 0) > 0) return;
            const now = performance.now();
            if (now - lastHandledAt < 400) return;   // pointer+touch duplicate
            lastHandledAt = now;
            this._suppressSwipeClickUntil = now + 450;
            this.pull(dy > 0 ? 'down' : 'up');
        };
        panel.addEventListener('pointerdown', (ev) => {
            if (ev.button !== undefined && ev.button !== 0) return;
            begin(ev.clientX, ev.clientY, ev.pointerId, 'pointer');
        }, { passive: true });
        panel.addEventListener('pointerup', (ev) => finish(ev.clientX, ev.clientY, ev.pointerId, 'pointer'), { passive: true });
        panel.addEventListener('pointercancel', () => { if (start && start.source === 'pointer') start = null; }, { passive: true });
        panel.addEventListener('touchstart', (ev) => {
            const t = ev.changedTouches && ev.changedTouches[0];
            if (t) begin(t.clientX, t.clientY, t.identifier, 'touch');
        }, { passive: true });
        panel.addEventListener('touchend', (ev) => {
            if (!start || start.source !== 'touch') return;
            const t = Array.from(ev.changedTouches || []).find(x => x.identifier === start.id);
            if (t) finish(t.clientX, t.clientY, t.identifier, 'touch');
            else start = null;
        }, { passive: true });
        panel.addEventListener('touchcancel', () => { if (start && start.source === 'touch') start = null; }, { passive: true });
        // Swallow the compatibility click a swipe would otherwise deliver to
        // the tile it started on.
        panel.addEventListener('click', (ev) => {
            if (performance.now() < (this._suppressSwipeClickUntil || 0)) {
                ev.preventDefault();
                ev.stopPropagation();
            }
        }, true);
    }

    _setExpandedUI(level) {
        if (typeof level !== 'number') level = this.level;
        const details = document.getElementById('qs-details');
        const privacy = document.getElementById('qs-privacy-row');
        const notifications = document.getElementById('qs-notifications');
        const btn = document.getElementById('qs-expand-toggle');
        const wantDetails = level >= 3;
        const wantPrivacy = level >= 2;
        if (details) details.hidden = !wantDetails;
        if (privacy) privacy.hidden = !wantPrivacy;
        // PWNAGE-93000: the real notification reminder list is a bounded
        // section BELOW every control/status row, never part of the tiles.
        if (notifications) notifications.hidden = !wantDetails;
        if (btn) {
            btn.setAttribute('aria-expanded', level >= 3 ? 'true' : 'false');
            btn.textContent = level >= 3 ? 'Collapse extended settings'
                : level >= 2 ? 'More connection status' : 'More connection status';
        }
        // PWNAGE-52000: privacy providers are read only while this row is
        // actually visible in the expanded panel.
        if (!wantPrivacy) {
            // Invalidates any in-flight result when the row is no longer shown.
            this._privacyGeneration = (this._privacyGeneration || 0) + 1;
        }
        // When the row is visible the reads are started by _render() after the
        // first paint, not synchronously in the open state transition.
        if (wantDetails && window.statusBar && window.statusBar._renderNotificationsPanel) {
            try { window.statusBar._renderNotificationsPanel(); } catch (e) {}
        }
    }

    collapseOrClose() {
        // The explicit button walks down one level; the upward gesture
        // (closeAll) remains the atomic full dismissal.
        if (this.level >= 3) this._setLevel(2, 'collapse');
        else if (this.level >= 2) this._setLevel(1, 'collapse');
        else this.closeAll('collapse');
    }

    toggle() {
        if (this.level >= 2) this.closeAll('toggle');
        else this.advance('toggle');
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
        if (id === 'dnd') {
            await this._toggleDnd();
            return;
        }
        if (id === 'flashlight') {
            await this._toggleFlashlight();
            return;
        }
        if (id === 'nfc' || id === 'fingerprint' || id === 'camera' || id === 'microphone') {
            await this._togglePrivacy(id);
            return;
        }
        // A tile must not become a decorative switch.  Keep unintegrated
        // controls honest until their hardware backend is landed.
        this._osdNotice(`${id} control is unavailable on this build`);
    }

    // ---- PWNAGE-52000 privacy row --------------------------------------
    // Every tile is a real provider action.  UNSUPPORTED is rendered as a
    // disabled tile with the provider's blocker, never as a fake ON.
    _privacyCall(ns, verb, params, timeoutMs) {
        const ms = timeoutMs || 3500;
        let timer;
        const timeout = new Promise((resolve) => {
            timer = setTimeout(() => resolve({ success: false, timeout: true, state: 'timeout',
                error: 'provider did not answer within ' + Math.round(ms / 1000) + ' s' }), ms);
        });
        return Promise.race([bridge.call(ns, verb, params || {}), timeout]).then((r) => {
            if (timer) clearTimeout(timer);
            return r;
        }, (e) => {
            if (timer) clearTimeout(timer);
            return { success: false, error: String(e && e.message || e) };
        });
    }

    async _syncPrivacy() {
        if (!this.isOpen || !this.expanded) return;
        if (this._privacyInFlight) return;
        this._privacyInFlight = true;
        const gen = this._privacyGeneration || 0;
        try {
            const [nfc, fp, cam, mic, sec] = await Promise.all([
                this._privacyCall('nfc', 'status', {}),
                this._privacyCall('fingerprint', 'status', {}),
                this._privacyCall('privacy', 'camera-status', {}),
                this._privacyCall('privacy', 'microphone-status', {}),
                this._privacyCall('security', 'status', {}),
            ]);
            if (!this.isOpen || !this.expanded || gen !== (this._privacyGeneration || 0)) return;
            this.privacy = { nfc, fingerprint: fp, camera: cam, microphone: mic, security: sec };
            this._renderPrivacy();
        } finally {
            this._privacyInFlight = false;
        }
    }

    _setPrivacyTile(id, supported, on, label, title) {
        const el = document.getElementById(id);
        if (!el) return;
        el.dataset.supported = supported ? 'true' : (supported === false ? 'false' : 'unknown');
        el.dataset.enabled = on === true ? 'true' : (on === false ? 'false' : 'unknown');
        el.setAttribute('aria-disabled', supported === false ? 'true' : 'false');
        const lab = el.querySelector('.qs-label');
        if (lab) lab.innerHTML = label;
        el.title = title || label.replace(/<br>/g, ' ');
    }

    _renderPrivacy() {
        const nfc = this.privacy.nfc || {};
        const nfcSupported = nfc.success !== false && nfc.supported === true;
        this._setPrivacyTile('qs-nfc', nfcSupported,
            nfcSupported && nfc.enabled === true,
            'NFC<br>' + (nfcSupported ? (nfc.enabled === true ? 'on' : 'off') : 'unsupported'),
            nfcSupported ? 'NFC provider state; tap to toggle' :
            ('NFC unsupported/blocked: ' + (nfc.blocker || nfc.state || 'provider unavailable')));

        const fp = this.privacy.fingerprint || {};
        const sec = this.privacy.security || {};
        const fpReady = fp.success !== false && fp.ready === true && fp.supported === true;
        const bio = sec.biometric_unlock || sec.fingerprint_unlock || {};
        const fpPolicy = (bio && typeof bio === 'object') ? bio.enabled === true : bio === true;
        this._setPrivacyTile('qs-fingerprint', fpReady,
            fpReady && fpPolicy,
            'Fingerprint<br>' + (fpReady ? (fpPolicy ? 'unlock on' : 'unlock off') : 'unsupported'),
            fpReady ? 'Biometric unlock policy; PIN fallback always retained' :
            ('Fingerprint unavailable: ' + (fp.blocker || fp.state || 'no secure provider')));

        const cam = this.privacy.camera || {};
        const camSupported = cam.success !== false && cam.supported !== false;
        const camBlocked = cam.blocked === true;
        this._setPrivacyTile('qs-camera', camSupported,
            camSupported && camBlocked,
            'Camera<br>' + (camSupported ? (camBlocked ? 'blocked' : 'allow') : 'unsupported'),
            camSupported ? ('Camera privacy gate: ' + (camBlocked ? 'blocked' : 'allowed') +
                '; frame capture=' + (cam.capture_supported === true ? 'available' : 'unavailable on this kernel') +
                '; active sessions=' + (cam.active_sessions == null ? 'unknown' : cam.active_sessions)) :
            ('Camera privacy unavailable: ' + (cam.error || cam.state || 'provider unavailable')));

        const mic = this.privacy.microphone || {};
        const micSupported = mic.success !== false && mic.supported !== false;
        const micMuted = mic.muted === true;
        this._setPrivacyTile('qs-microphone', micSupported,
            micSupported && micMuted,
            'Microphone<br>' + (micSupported ? (micMuted ? 'muted' : 'live') : 'unsupported'),
            micSupported ? ('System capture mute: ' + (micMuted ? 'muted' : 'not muted') +
                '; sources=' + (mic.source_count == null ? 'unknown' : mic.source_count)) :
            ('Microphone privacy unavailable: ' + (mic.error || mic.state || 'provider unavailable')));
    }

    async _togglePrivacy(id) {
        const tile = document.getElementById('qs-' + id);
        if (!tile || tile.dataset.supported === 'false') {
            const provider = this.privacy && this.privacy[id === 'fingerprint' ? 'fingerprint' : id];
            this._osdNotice((provider && (provider.blocker || provider.error || provider.state)) ||
                (id + ' is unsupported on this device'));
            return;
        }
        const now = tile.dataset.enabled === 'true';
        let res;
        if (id === 'nfc') {
            res = await this._privacyCall('nfc', 'set-enabled', { enabled: !now }, 6000);
        } else if (id === 'fingerprint') {
            res = await this._privacyCall('security', 'set-biometric-unlock', { enabled: !now });
        } else if (id === 'camera') {
            res = await this._privacyCall('privacy', 'camera-set', { blocked: !now }, 6000);
        } else {
            res = await this._privacyCall('privacy', 'microphone-set', { muted: !now }, 8000);
        }
        if (!res || res.success === false) {
            this._osdNotice(id + ' failed: ' + ((res && (res.error || res.detail || res.blocker)) || 'provider did not confirm'));
        } else {
            this._osdNotice(id + ' ' + (now ? 'turned off' : 'turned on') + ' (provider confirmed)');
        }
        await this._syncPrivacy();
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

    // ---- persistent Do Not Disturb ------------------------------------
    async _syncDnd() {
        const tile = document.getElementById('qs-dnd');
        if (!tile) return;
        try {
            const st = await bridge.call('dnd', 'status', {});
            if (!st || st.success === false) {
                this.state.dnd = null;
                tile.dataset.enabled = 'unknown';
                tile.dataset.state = 'unavailable';
                const l = tile.querySelector('.qs-label'); if (l) l.innerHTML = 'DND<br>unknown';
                tile.title = 'DND provider unavailable' + (st && st.error ? ': ' + st.error : '');
                return;
            }
            this.state.dnd = st.active === true;
            tile.dataset.enabled = st.active === true ? 'true' : 'false';
            tile.dataset.state = st.active ? ('on-' + (st.reason || 'manual')) : 'off';
            const l = tile.querySelector('.qs-label');
            if (l) l.innerHTML = st.active
                ? (st.reason === 'schedule' ? 'DND<br>scheduled' : 'DND<br>on')
                : 'DND<br>off';
            tile.title = 'Do Not Disturb: ' + (st.active ? ('ON (' + (st.reason || 'manual') + ')') : 'OFF')
                + '\nSuppresses popups/sound/haptics/LED; notification history is preserved';
        } catch (e) {
            this.state.dnd = null;
            tile.dataset.enabled = 'unknown';
            tile.dataset.state = 'error';
            const l = tile.querySelector('.qs-label'); if (l) l.innerHTML = 'DND<br>unknown';
            tile.title = 'DND provider error: ' + (e && e.message ? e.message : 'bridge error');
        }
    }

    async _toggleDnd() {
        const tile = document.getElementById('qs-dnd');
        if (tile) tile.dataset.pending = 'true';
        try {
            const res = await bridge.call('dnd', 'toggle', {});
            if (!res || res.success === false) throw new Error((res && (res.error || res.detail)) || 'DND provider unavailable');
            this._osdNotice(res.active ? 'Do Not Disturb on (history preserved)' : 'Do Not Disturb off');
            this._hapticSwitch();
            await this._syncDnd();
        } catch (e) {
            await this._syncDnd();
            this._osdNotice('DND unchanged: ' + (e && e.message ? e.message : 'provider unavailable'));
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

    // ---- orientation: long-press selects all seven exact owner labels ----
    async _orientationState() {
        try {
            const res = await bridge.call('orientation', 'get', {});
            return (res && typeof res === 'object') ? res : { mode: 'portrait' };
        } catch (e) {
            return { mode: 'portrait', error: String(e && e.message || e) };
        }
    }

    async _toggleRotate() {
        // Short tap is a predictable 90-degree clockwise LOCKED rotation.
        // Auto is never selected by a tap: a blocked sensor must not look like
        // a successful automatic rotation.  The seven-mode chooser is the
        // long-press / context-menu action.
        const cur = await this._orientationState();
        const order = [
            ['portrait', 0], ['landscape', 90],
            ['reverse-portrait', 180], ['reverse-landscape', 270],
        ];
        let effective = Number(cur.effective_orientation);
        if (!Number.isFinite(effective)) effective = 0;
        const index = order.findIndex(([, deg]) => deg === ((effective % 360) + 360) % 360);
        const next = order[(index + 1 + order.length) % order.length];
        await this._setOrientation(next[0]);
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
            const display = res.display || res.compositor || {};
            const applied = res.applied === true || display.applied === true;
            if (!applied) {
                this._osdNotice('Rotation NOT applied: '
                    + (res.last_error || display.error || 'compositor unavailable'));
            } else {
                const trial = res.trial || {};
                const secs = trial.pending_confirmation && trial.deadline_epoch
                    ? Math.max(0, Math.round(trial.deadline_epoch - Date.now() / 1000)) : 0;
                const degraded = res.auto && res.sensor && res.sensor.available === false;
                this._osdNotice('Rotation applied: ' + (res.mode_label || res.mode)
                    + ' · ' + (res.effective_orientation === undefined ? '?' : res.effective_orientation + '°')
                    + ' · ' + (display.transform || 'transform?')
                    + (degraded ? ' · AUTO DEGRADED: no live sensor' : '')
                    + (trial.pending_confirmation ? (' · confirm in Notes (' + secs + 's)') : ''));
            }
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
        // Auto is only "enabled" (green) when a REAL sensor source is live.
        // A blocked Auto policy stays selected but is rendered as degraded.
        tile.dataset.enabled = (auto && sensorOk) ? 'true' : 'false';
        tile.dataset.degraded = (auto && !sensorOk) ? 'true' : 'false';
        tile.dataset.mode = this.orientationMode;
        const label = tile.querySelector('.qs-label');
        // Show the REAL selected mode (one of seven), never a bare Locked/Auto.
        if (label) label.textContent = this._rotateModeLabel(this.orientationMode);
        const display = st.display || st.compositor || {};
        const applied = st.applied === true || display.applied === true;
        tile.title = 'Rotation: ' + (st.mode_label || this._rotateModeLabel(this.orientationMode))
            + ' | effective ' + (st.effective_orientation === undefined ? '?' : st.effective_orientation + '°')
            + ' | ' + (applied ? 'APPLIED' : 'NOT APPLIED')
            + (display.output ? (' on ' + display.output) : '')
            + (display.transform ? (' (' + display.transform + ')') : '')
            + (auto ? (' | sensor ' + (sensorOk ? 'available' : 'DEGRADED - no live sensor')) : '')
            + (st.transition_state ? (' | state ' + st.transition_state) : '')
            + (st.vnc_status ? (' | VNC ' + st.vnc_status) : '')
            + '\nTap = rotate 90 degrees (locked), long-press = all seven modes';
    }

    _rotateModes() {
        return [
            ['auto', 'Auto (FULL)'], ['auto-portrait', 'Auto (PT)'], ['auto-landscape', 'Auto (LS)'],
            ['portrait', 'Locked (PT)'], ['landscape', 'Locked (LS)'],
            ['reverse-portrait', 'Locked (RPT)'], ['reverse-landscape', 'Locked (RLS)'],
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
            // Privacy/connection-detail providers are secondary to first paint.
            // Start them only after the panel is already on screen; the panel is
            // interactive from cached state before these requests leave.
            if (this.expanded) {
                this._syncPrivacy();
                this._syncIndicators();
            }
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
        const syncT0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
        const preserveRadio = !!(options && options.preserveRadio);
        const retainRadio = preserveRadio && typeof this.state.wifi === 'boolean';
        // Start the independent provider reads immediately.  Previously they
        // waited for getPhoneStatus(), which is the slowest call (measured
        // 1.8-2.4 s), so hydrating Bluetooth/location/DND/flashlight added its
        // latency on top instead of overlapping it.  The panel is already
        // painted from cache; this only shortens the truthful state hydration.
        const timed = (name, promise) => {
            const p0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
            return Promise.resolve(promise).then((v) => {
                nuxelPerfDiag('QS_PERF', { event: 'provider', name: name,
                    ms: Math.round((((typeof performance !== 'undefined' ? performance.now() : Date.now()) - p0) * 10)) / 10 });
                return v;
            }, (e) => {
                nuxelPerfDiag('QS_PERF', { event: 'provider', name: name, error: true,
                    ms: Math.round((((typeof performance !== 'undefined' ? performance.now() : Date.now()) - p0) * 10)) / 10 });
                throw e;
            });
        };
        const secondary = [timed('bluetooth', this._syncBluetooth()),
                           timed('location', this._syncLocation()),
                           timed('dnd', this._syncDnd()),
                           timed('flashlight', this._syncFlashlight())];
        const phoneT0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
        try {
            const status = await bridge.getPhoneStatus();
            const phoneMs = Math.round((((typeof performance !== 'undefined' ? performance.now() : Date.now()) - phoneT0) * 10)) / 10;
            this._phoneStatusMs = phoneMs;
            nuxelPerfDiag('QS_PERF', { event: 'provider', name: 'phone_status', ms: phoneMs });
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
        // Independent providers run concurrently; one slow radio never blocks
        // the others.  Each keeps its own tri-state/generation guard.
        try { await Promise.allSettled(secondary); } catch (e) {}
        this._lastSyncMs = Math.round(((typeof performance !== 'undefined' ? performance.now() : Date.now()) - syncT0) * 10) / 10;
        nuxelPerfDiag('QS_PERF', { event: 'sync', ms: this._lastSyncMs,
                                   wifi: this.state.wifi, link: this.wifiConnected });
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
