// Launcher-only settings and wallpaper picker.  Everything is browser-local so
// changing a layout or chosen photo never grants a PWA access to device files.
(function (global) {
    'use strict';
    const KEY = 'nuxel.homeAppearance';
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
        panel.innerHTML = '<div class="home-settings-card">' +
            '<header><h2>Home settings</h2><button type="button" data-home-close>Done</button></header>' +
            '<h3>Wallpaper</h3><div class="wallpaper-choices">' +
            presets.map((p, i) => '<button type="button" class="wallpaper-choice" data-wallpaper="' + i + '" style="background-image:' + p[1] + '"><span>' + p[0] + '</span></button>').join('') +
            '</div><label class="wallpaper-upload">Choose photo<input type="file" accept="image/*" data-wallpaper-file></label>' +
            '<h3>Home grid</h3><div class="home-setting-row"><label>Columns <select data-grid-columns>' + options(3, 6, settings.gridColumns) + '</select></label>' +
            '<label>Rows <select data-grid-rows>' + options(4, 7, settings.gridRows) + '</select></label></div>' +
            '<p class="home-setting-hint">Default: 4 columns × 5 rows.</p>' +
            '<h3>Bottom dock</h3><div class="home-setting-row"><label>Icons wide <select data-dock-columns>' + options(3, 6, settings.dockColumns) + '</select></label></div>' +
            '<p class="home-setting-hint">Default: 5-wide dock.</p>' +
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
        const update = () => launcher && launcher.updateHomeSettings({
            gridColumns: Number(panel.querySelector('[data-grid-columns]').value),
            gridRows: Number(panel.querySelector('[data-grid-rows]').value),
            dockColumns: Number(panel.querySelector('[data-dock-columns]').value),
        });
        panel.querySelectorAll('select').forEach(select => select.onchange = update);
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
    global.NuxelHomeSettings = { open, close, apply };
    document.addEventListener('DOMContentLoaded', () => { apply(); bindLongPress(); });
})(window);
