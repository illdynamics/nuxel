// Launcher-only settings and wallpaper picker.  Everything is browser-local so
// changing a layout or chosen photo never grants a PWA access to device files.
(function (global) {
    'use strict';
    const KEY = 'nuxel.homeAppearance';
    // `none` is intentional: it keeps all dock hitboxes and navigation
    // behaviour while removing only the decorative, pointer-inert artwork.
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
        // The shortcut dock and the fixed Back/Home/Recents dock are distinct
        // surfaces, but one explicit preference must update both. Previously
        // the picker changed only #dock while the visible navigation strip was
        // hard-coded to BG2, making a successful switch appear to do nothing.
        const docks = Array.from(document.querySelectorAll('#dock, #system-navigation'));
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
        image.src = artwork;
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
        const selectedDock = dockChoice(appearance.dockBackground);
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
            '<h3>Bottom dock</h3>' +
            '<p class="home-setting-hint">Applies to the shortcut and Back/Home/Recents docks. BG2 is the default; tap to preview immediately.</p>' +
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
            '<footer><button type="button" data-home-restore>Restore hidden apps</button><button type="button" class="reset-home" data-home-reset>Reset launcher layout</button></footer></div>';
        panel.hidden = false;
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
        panel.querySelector('[data-home-restore]').onclick = () => { if (launcher) launcher.restoreHiddenApps(); };
        panel.querySelector('[data-home-reset]').onclick = () => { if (launcher) launcher.resetOrder(); close(); };
    }
    function options(min, max, selected) {
        let out = ''; for (let i = min; i <= max; i++) out += '<option value="' + i + '"' + (i === selected ? ' selected' : '') + '>' + i + '</option>';
        return out;
    }
    function close() { const panel = document.getElementById('home-settings'); if (panel) panel.hidden = true; }
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
    global.NuxelHomeSettings = { open, close, apply, dockChoice, dockPaths: DOCKS };
    document.addEventListener('DOMContentLoaded', () => { apply(); bindLongPress(); });
})(window);
