// Launcher-only settings and wallpaper picker.  Everything is browser-local so
// changing a layout or chosen photo never grants a PWA access to device files.
(function (global) {
    'use strict';
    const KEY = 'nuxel.homeAppearance';
    // `none` is intentional: it keeps all navigation hitboxes/behaviour
    // while removing only the decorative, pointer-inert artwork.
    // These URLs deliberately start at the active Nuxel Home web root.  A
    // relative URL stored in --dock-art is resolved at the stylesheet which
    // consumes it (css/launcher.css), not at this script.  That formerly made
    // both picker options request css/assets/... and silently lose their art.
    const DOCKS = Object.freeze({
        bg2: '/pwa/nuxel-home/assets/nuxel-bottom-bar2.png',
        bg1: '/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg',
        none: null,
    });
    const DEFAULT_DOCK = 'bg2';
    function dockChoice(value) { return Object.prototype.hasOwnProperty.call(DOCKS, value) ? value : DEFAULT_DOCK; }
    function applyDock(data) {
        const value = dockChoice(data.dockBackground);
        const artwork = DOCKS[value];
        // Artwork belongs ONLY to the fixed Back/Home/Recents strip.  The
        // shortcut dock is deliberately transparent: painting the same art
        // there created a second half-height bar above the navigation strip
        // and hid the four dock shortcuts behind its black matte.
        const docks = Array.from(document.querySelectorAll('#system-navigation'));
        if (!docks.length) return;
        docks.forEach(dock => {
            dock.dataset.background = value;
            if (artwork) dock.style.setProperty('--dock-art', 'url("' + artwork + '")');
            else dock.style.removeProperty('--dock-art');
            dock.setAttribute('data-dock-asset', artwork || 'none');
        });
        if (!artwork) {
            document.dispatchEvent(new CustomEvent('nuxel:dock-background', {detail:{id:value,path:null}}));
            return;
        }
        // Use a deliberately noninteractive background layer. /pwa/nuxel-home/
        // relative paths work for both the static dev server and live nuxel-web.
        // Validate the selected image with a real decode, but never reset the
        // user's saved preference because the network may be temporarily down.
        const image = new Image();
        image.onerror = () => {
            if (!docks.some(dock => dock.dataset.background === value)) return;
            const alternate = value === 'bg2' ? 'bg1' : 'bg2';
            docks.forEach(dock => {
                dock.dataset.backgroundFallback = alternate;
                dock.style.setProperty('--dock-art', 'url("' + DOCKS[alternate] + '")');
            });
            console.warn('[Nuxel] Missing/corrupt dock artwork:', artwork);
        };
        image.onload = () => docks.forEach(dock => { if (dock.dataset.background === value) delete dock.dataset.backgroundFallback; });
        image.src = artwork + '?v=0.7.4-beta';
        document.dispatchEvent(new CustomEvent('nuxel:dock-background', {detail:{id:value,path:artwork}}));
    }
    const DEFAULT_WALLPAPER = "url('assets/nuxel-background.png')";
    const presets = [
        ['Default', DEFAULT_WALLPAPER],
        ['Midnight', 'linear-gradient(145deg, #020617, #172554 52%, #0f766e)'],
        ['Sunset', 'linear-gradient(145deg, #3b0764, #9d174d 52%, #f97316)'],
        ['Forest', 'linear-gradient(145deg, #052e16, #14532d 52%, #0f766e)'],
    ];
    const read = () => { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } };
    const save = data => { try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) {} };
    const widgetDesktopDefault = () => {
        // Widget documents store ONE-BASED desktop numbers. Prefer desktop 2
        // when it exists (the owner's requested sticky-note desktop); otherwise
        // use the desktop currently in front of the user.
        const launcher = global.launcher;
        const count = launcher && launcher.settings ? Number(launcher.settings.desktopCount) || 1 : 1;
        if (count >= 2) return 2;
        return Math.max(1, (launcher ? Number(launcher.currentPage) || 0 : 0) + 1);
    };
    const refreshWidgetControls = (panel) => {
        if (!global.NuxelWidgets) return;
        const notes = global.NuxelWidgets.notes();
        const sel = panel.querySelector('[data-widget-note]');
        const add = panel.querySelector('[data-add-notes-widget]');
        if (sel) {
            const keep = sel.value;
            sel.replaceChildren();
            const auto = document.createElement('option');
            auto.value = ''; auto.textContent = 'Most recent note';
            sel.appendChild(auto);
            notes.forEach(n => {
                const o = document.createElement('option');
                o.value = n.id; o.textContent = n.title || 'Untitled';
                sel.appendChild(o);
            });
            if (notes.some(n => n.id === keep)) sel.value = keep;
        }
        if (add) {
            add.disabled = notes.length === 0;
            add.textContent = notes.length ? 'Add Notes widget' : 'Add Notes widget (no notes yet)';
        }
    };
    function apply() {
        const data = read();
        document.body.style.backgroundImage = data.wallpaper || DEFAULT_WALLPAPER;
        applyDock(data);
        // Battery style is a launcher preference, never a fake battery reading.
        if (global.statusBar && global.statusBar.setBatteryStyle) global.statusBar.setBatteryStyle(data.batteryStyle || 'inside');
    }
    function open() {
        let panel = document.getElementById('home-settings');
        if (!panel) {
            panel = document.createElement('section');
            panel.id = 'home-settings'; panel.className = 'home-settings';
            panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-modal', 'true');
            document.body.appendChild(panel);
        }
        const launcher = global.launcher;
        const settings = launcher ? launcher.settings : { gridColumns: 4, gridRows: 5, dockColumns: 5 };
        const appearance = read();
        // PWNAGE-43000: this panel is static once built.  Rebuilding it on
        // every open re-decoded the dock artwork and reparsed every control,
        // which made Home Settings feel sluggish.  Hydrate the existing
        // controls instead; the expensive preview images stay decoded.
        if (panel.dataset.nuxelBuilt === '1' && panel.firstElementChild) {
            const setVal = (sel, val) => { const e = panel.querySelector(sel); if (e) e.value = String(val); };
            const setChk = (sel, val) => { const e = panel.querySelector(sel); if (e) e.checked = !!val; };
            setVal('[data-grid-columns]', settings.gridColumns);
            setVal('[data-grid-rows]', settings.gridRows);
            setVal('[data-desktop-count]', settings.desktopCount || 2);
            setChk('[data-home-locked]', settings.homeLocked === true);
            setVal('[data-battery-style]', appearance.batteryStyle || 'inside');
            setChk('[data-system-monitor-enabled]', appearance.systemMonitorEnabled !== false);
            setVal('[data-system-monitor-interval]', Number(appearance.systemMonitorInterval || 3));
            setChk('[data-system-monitor-detailed]', appearance.systemMonitorDetailed !== false);
            const wd = panel.querySelector('[data-widget-desktop]');
            if (wd) { wd.min = '1'; wd.max = String(settings.desktopCount || 2); }
            refreshWidgetControls(panel);
            const lockSel = panel.querySelector('[data-lock-after-off]');
            const host = global.NuxelHost;
            if (lockSel && host && host.available && typeof host.configGet === 'function') {
                host.configGet('display-timeout').then((r) => {
                    try {
                        const doc = JSON.parse((r && r.text) || '{}');
                        const v = String(doc.lock_after_off_ms == null ? 0 : doc.lock_after_off_ms);
                        if ([...lockSel.options].some(o => o.value === v)) lockSel.value = v;
                    } catch (e) {}
                }).catch(() => {});
            }
            panel.hidden = false;
            try { document.dispatchEvent(new CustomEvent('nuxel:overlay-changed')); } catch (e) {}
            return;
        }
        const selectedDock = dockChoice(appearance.dockBackground);
        const widgetState = global.NuxelWidgets ? global.NuxelWidgets.state() : { enabled: true, items: [] };
        const widgetsEnabled = widgetState.enabled !== false;
        const widgetNotes = global.NuxelWidgets ? global.NuxelWidgets.notes() : [];
        const noteOptions = '<option value="">Most recent note</option>' +
            widgetNotes.map(n => '<option value="' + n.id.replace(/[^A-Za-z0-9._-]/g, '') + '">' +
                (n.title || 'Untitled').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</option>').join('');
        panel.innerHTML = '<div class="home-settings-card">' +
            '<header><h2>Home settings</h2><button type="button" data-home-close>Done</button></header>' +
            '<h3>Wallpaper</h3><div class="wallpaper-choices">' +
            presets.map((p, i) => '<button type="button" class="wallpaper-choice" data-wallpaper="' + i + '" style="background-image:' + p[1] + '"><span>' + p[0] + '</span></button>').join('') +
            '</div><label class="wallpaper-upload">Choose photo<input type="file" accept="image/*" data-wallpaper-file></label>' +
            '<h3>Home grid</h3><div class="home-setting-row"><label>Columns <select data-grid-columns>' + options(3, 6, settings.gridColumns) + '</select></label>' +
            '<label>Rows <select data-grid-rows>' + options(4, 7, settings.gridRows) + '</select></label></div>' +
            '<p class="home-setting-hint">Default: 4 columns × 5 rows.</p>' +
            '<h3>Home layout</h3>' +
            '<div class="home-setting-row"><label>Lock icon layout <input type="checkbox" data-home-locked' + (settings.homeLocked ? ' checked' : '') + '></label>' +
            '<label>Desktops <select data-desktop-count>' + options(1, 8, settings.desktopCount || 2) + '</select></label></div>' +
            '<h3>Navigation bar artwork</h3>' +
            '<p class="home-setting-hint">Shown behind Back, Home and Recents only. The app dock stays transparent. BG2 is the default; tap to preview immediately.</p>' +
            '<div class="dock-background-choices" role="group" aria-label="Dock background">' +
            Object.keys(DOCKS).map(id => '<button type="button" class="dock-background-choice" data-dock-choice="' + id + '" aria-pressed="' + (id === selectedDock) + '">' +
                (DOCKS[id] ? '<img src="' + DOCKS[id] + '" alt="' + (id === 'bg1' ? 'BG1 Classic' : 'BG2 Alternative') + '">' : '<span class="dock-background-none-preview" aria-hidden="true">No artwork</span>') +
                '<span>' + (id === 'bg1' ? 'BG1 · Classic' : id === 'bg2' ? 'BG2 · Alternative' : 'None') + '</span></button>').join('') + '</div>' +
            '<h3>Status bar</h3><label>Battery indicator <select data-battery-style>' +
            [['inside', 'Icon with percentage inside'], ['percentage', 'Percentage only'], ['bar', 'Battery bar only']].map(v => '<option value="' + v[0] + '"' + ((appearance.batteryStyle || 'inside') === v[0] ? ' selected' : '') + '>' + v[1] + '</option>').join('') +
            '</select></label>' +
            '<h3>System Monitor</h3><div class="system-monitor-controls">' +
            '<label>Show hardware meters <input type="checkbox" data-system-monitor-enabled' + (appearance.systemMonitorEnabled !== false ? ' checked' : '') + '></label>' +
            '<label>Refresh interval <select data-system-monitor-interval>' + [1, 2, 3, 5, 10].map(v => '<option value="' + v + '"' + (Number(appearance.systemMonitorInterval || 3) === v ? ' selected' : '') + '>' + v + ' seconds</option>').join('') + '</select></label>' +
            '<label>Detailed values <input type="checkbox" data-system-monitor-detailed' + (appearance.systemMonitorDetailed !== false ? ' checked' : '') + '></label>' +
            '<p class="home-setting-hint">3 seconds is recommended. One-second updates can use more battery.</p></div>' +
            '<h3>Widgets</h3>' +
            '<div class="home-setting-row"><label>Enable widgets <input type="checkbox" data-widgets-enabled' + (widgetsEnabled ? ' checked' : '') + '></label>' +
            '<label>Desktop (1-based) <input type="number" min="1" max="' + (settings.desktopCount || 2) + '" value="' + widgetDesktopDefault() + '" data-widget-desktop></label></div>' +
            '<div class="home-setting-row"><label>Note <select data-widget-note>' + noteOptions + '</select></label></div>' +
            '<div class="row"><button type="button" data-add-notes-widget' + (widgetNotes.length ? '' : ' disabled') + '>' + (widgetNotes.length ? 'Add Notes widget' : 'Add Notes widget (no notes yet)') + '</button></div>' +
            '<p class="home-setting-hint">The Notes widget shows a chosen note on the selected desktop and opens the full editor when tapped.</p>' +
            '<h3>Lock &amp; display</h3><div class="home-setting-row"><label>Lock after screen turns off <select data-lock-after-off>' +
            [['0','Immediately'],['5000','After 5 seconds'],['15000','After 15 seconds'],['30000','After 30 seconds'],['60000','After 1 minute'],['300000','After 5 minutes']].map(v => '<option value="' + v[0] + '">' + v[1] + '</option>').join('') +
            '</select></label></div>' +
            '<p class="home-setting-hint">Immediately is the secure default. A delay keeps the session briefly while the panel is off.</p>' +
            '<footer><button type="button" data-home-restore>Restore hidden apps</button><button type="button" class="reset-home" data-home-reset>Reset launcher layout</button></footer></div>';
        panel.dataset.nuxelBuilt = '1';
        panel.hidden = false;
        try { document.dispatchEvent(new CustomEvent('nuxel:overlay-changed')); } catch (e) {}
        panel.querySelector('[data-home-close]').onclick = close;
        panel.querySelectorAll('[data-wallpaper]').forEach(button => button.onclick = () => {
            const data = read(); data.wallpaper = presets[Number(button.dataset.wallpaper)][1]; save(data); apply();
        });
        panel.querySelector('[data-wallpaper-file]').onchange = event => {
            const file = event.target.files && event.target.files[0];
            if (!file || !/^image\//.test(file.type) || file.size > 5 * 1024 * 1024) return;
            const reader = new FileReader();
            reader.onload = () => { const data = read(); data.wallpaper = 'url("' + reader.result + '")'; save(data); apply(); };
            reader.readAsDataURL(file);
        };
        panel.querySelectorAll('[data-dock-choice]').forEach(button => button.onclick = () => {
            const data = read(); data.dockBackground = dockChoice(button.dataset.dockChoice);
            save(data); applyDock(data);
            panel.querySelectorAll('[data-dock-choice]').forEach(el => el.setAttribute('aria-pressed', String(el === button)));
        });
        panel.querySelector('[data-battery-style]').onchange = event => {
            const data = read(); data.batteryStyle = event.target.value; save(data); apply();
        };
        panel.querySelector('[data-system-monitor-enabled]').onchange = event => {
            const data = read(); data.systemMonitorEnabled = event.target.checked; save(data);
            global.NuxelSystemMonitor && global.NuxelSystemMonitor.configure(data);
        };
        panel.querySelector('[data-system-monitor-interval]').onchange = event => {
            const data = read(); data.systemMonitorInterval = Number(event.target.value); save(data);
            global.NuxelSystemMonitor && global.NuxelSystemMonitor.configure(data);
        };
        panel.querySelector('[data-system-monitor-detailed]').onchange = event => {
            const data = read(); data.systemMonitorDetailed = event.target.checked; save(data);
            global.NuxelSystemMonitor && global.NuxelSystemMonitor.configure(data);
        };
        const update = () => launcher && launcher.updateHomeSettings({
            gridColumns: Number(panel.querySelector('[data-grid-columns]').value),
            gridRows: Number(panel.querySelector('[data-grid-rows]').value),
            desktopCount: Number(panel.querySelector('[data-desktop-count]').value),
            homeLocked: panel.querySelector('[data-home-locked]').checked,
        });
        panel.querySelector('[data-grid-columns]').onchange = update;
        panel.querySelector('[data-grid-rows]').onchange = update;
        panel.querySelector('[data-desktop-count]').onchange = update;
        panel.querySelector('[data-home-locked]').onchange = update;
        const lockSel = panel.querySelector('[data-lock-after-off]');
        if (lockSel) {
            const applyLockDelay = (ms) => {
                const host = global.NuxelHost;
                if (!host || !host.available || typeof host.configGet !== 'function') return;
                const doc = { timeout_ms: 300000, never: false, lock_after_off_ms: ms };
                host.configSet('display-timeout', JSON.stringify(doc)).catch(() => {});
            };
            const hydrateLockDelay = () => {
                const host = global.NuxelHost;
                if (!host || !host.available || typeof host.configGet !== 'function') return;
                host.configGet('display-timeout').then((r) => {
                    try {
                        const doc = JSON.parse((r && r.text) || '{}');
                        const v = String(doc.lock_after_off_ms == null ? 0 : doc.lock_after_off_ms);
                        if ([...lockSel.options].some(o => o.value === v)) lockSel.value = v;
                    } catch (e) {}
                }).catch(() => {});
            };
            lockSel.onchange = () => applyLockDelay(Number(lockSel.value));
            hydrateLockDelay();
        }
        panel.querySelector('[data-home-restore]').onclick = () => { if (launcher) launcher.restoreHiddenApps(); };
        panel.querySelector('[data-home-reset]').onclick = () => { if (launcher) launcher.resetOrder(); close(); };

        // Bind the widget controls and the notes listener exactly once.  The
        // previous code re-added `nuxel:notes-updated` on every open, so
        // repeated Home Settings visits accumulated handlers.
        if (global.NuxelWidgets && panel.dataset.widgetsBound !== '1') {
            panel.dataset.widgetsBound = '1';
            refreshWidgetControls(panel);
            panel.querySelector('[data-widgets-enabled]').onchange = event => {
                global.NuxelWidgets.setEnabled(event.target.checked);
            };
            panel.querySelector('[data-add-notes-widget]').onclick = () => {
                var noteSel = panel.querySelector('[data-widget-note]');
                var noteId = noteSel ? noteSel.value : '';
                var notes = global.NuxelWidgets.notes();
                if (!noteId && notes.length) noteId = notes[0].id;
                if (!noteId) {
                    alert('No note exists yet. Create one in the Notes app first.');
                    return;
                }
                var desktopEl = panel.querySelector('[data-widget-desktop]');
                var desktop = Number(desktopEl && desktopEl.value ? desktopEl.value : widgetDesktopDefault());
                var maxDesktop = settings.desktopCount || 2;
                if (!Number.isInteger(desktop) || desktop < 1 || desktop > maxDesktop) {
                    alert('Choose a desktop from 1 to ' + maxDesktop + '.');
                    return;
                }
                var item = global.NuxelWidgets.add('notes', { desktop: desktop, noteId: noteId });
                if (!item) {
                    alert('That note no longer exists. Choose another note.');
                    return;
                }
                // The widget is persisted for its own desktop; if the user is
                // not there, move Home to it so the result is visible at once.
                if (global.launcher && global.launcher.currentPage !== desktop - 1) {
                    global.launcher.currentPage = desktop - 1;
                    global.launcher._renderAppGrid();
                    global.NuxelWidgets.renderPage(global.launcher.currentPage);
                }
                refreshWidgetControls(panel);
            };
            document.addEventListener('nuxel:notes-updated', () => refreshWidgetControls(panel));
        }
    }
    function options(min, max, selected) {
        let out = ''; for (let i = min; i <= max; i++) out += '<option value="' + i + '"' + (i === selected ? ' selected' : '') + '>' + i + '</option>';
        return out;
    }
    function close() { const panel = document.getElementById('home-settings'); if (panel) panel.hidden = true; try { document.dispatchEvent(new CustomEvent('nuxel:overlay-changed')); } catch (e) {} }
    function bindLongPress() {
        let timer = null, start = null;
        document.addEventListener('pointerdown', event => {
            if (event.button !== undefined && event.button !== 0) return;
            if (event.target.closest && event.target.closest('.app-item, #system-navigation, #status-bar, #dock, #quick-settings, .home-settings')) return;
            start = { x: event.clientX, y: event.clientY, id: event.pointerId };
            timer = setTimeout(() => { timer = null; open(); if (global.NuxelHost && global.NuxelHost.available) global.NuxelHost.action('haptics-long'); }, 550);
        });
        document.addEventListener('pointermove', event => { if (start && event.pointerId === start.id && (Math.abs(event.clientX - start.x) > 8 || Math.abs(event.clientY - start.y) > 8)) { clearTimeout(timer); timer = null; } });
        ['pointerup', 'pointercancel'].forEach(type => document.addEventListener(type, () => { clearTimeout(timer); timer = null; start = null; }));
    }
    // PWNAGE-37000B: build the panel once during an idle slice so the first
    // owner tap is not charged the 120-170 ms DOM+image-decode cost.  open()
    // and close() are called in the SAME task, so no frame can paint the
    // priming panel; the cached hydration path is left untouched.
    function prime() {
        try {
            const panel = document.getElementById('home-settings');
            if (panel && panel.dataset.nuxelBuilt === '1') return false;
            open();
            // Pay the one-time panel layout now; it is still hidden immediately
            // afterwards, so this cannot flash over the launcher.
            void panel.offsetHeight;
            close();
            return true;
        } catch (e) {
            try { close(); } catch (e2) {}
            return false;
        }
    }
    global.NuxelHomeSettings = { open, close, apply, prime, dockChoice, dockPaths: DOCKS };
    document.addEventListener('DOMContentLoaded', () => { apply(); bindLongPress(); });
})(window);
