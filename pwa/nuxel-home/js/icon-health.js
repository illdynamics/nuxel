// Nuxel Home — manifest-driven icon/cache health probe (A44).
//
// Runs once per WebKit session in the launcher's own engine.  It deliberately
// uses the same URLs the UI uses, so an image that only exists in the repository
// or only returns 200 from a host-side curl cannot pass:
//   * every icon-registry asset is loaded as an Image and fetched no-store;
//   * bytes, MIME and SHA-256 are compared with the generated manifest;
//   * Quick Settings is opened/closed twice and checked for duplicate nodes;
//   * Settings and Browser are launched/closed to exercise app switching;
//   * one Home reload is performed and the post-reload DOM is compared;
//   * service-worker cache names and localStorage preservation are reported.
//
// The result is posted to the host's existing nuxelDiag channel, which writes it
// to /run/nuxel-home.state.  No layout, preference or credential is modified;
// the temporary storage probe is removed before the report is emitted.
(function () {
    'use strict';
    const VERSION = 'a44-3';
    const PHASE_KEY = 'nuxel.iconHealth.phase.' + VERSION;
    const RUN_KEY = 'nuxel.iconHealth.doneRun';
    const PROBE_KEY = 'nuxel.iconHealth.storageProbe.' + VERSION;

    function post(kind, payload) {
        const line = 'A44_ICON_HEALTH ' + kind + ' ' + JSON.stringify(payload);
        try {
            const diag = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.nuxelDiag;
            if (diag) diag.postMessage(line);
        } catch (e) { /* diagnostics never affect the UI */ }
        return line;
    }

    function wait(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

    async function sha256Hex(buffer) {
        if (!(window.crypto && crypto.subtle && crypto.subtle.digest)) return null;
        const d = await crypto.subtle.digest('SHA-256', buffer);
        return Array.from(new Uint8Array(d)).map(x => x.toString(16).padStart(2, '0')).join('');
    }

    function domSnapshot() {
        const images = Array.from(document.images).map(img => {
            const r = img.getBoundingClientRect();
            return {
                src: img.currentSrc || img.src, complete: !!img.complete,
                width: img.naturalWidth || 0, height: img.naturalHeight || 0,
                hidden: !!img.hidden, state: img.dataset.iconState || null,
                rendered: !!(r.width && r.height) && !img.hidden,
            };
        });
        const srcs = images.map(i => i.src);
        const unique = Array.from(new Set(srcs));
        return {
            imageCount: images.length,
            uniqueImageCount: unique.length,
            duplicateImageSrcs: unique.filter(s => srcs.filter(x => x === s).length > 1),
            allDecoded: images.every(i => !i.complete || i.width > 0),
            navImages: document.querySelectorAll('#system-navigation img').length,
            navLoaded: Array.from(document.querySelectorAll('#system-navigation img'))
                .filter(i => i.complete && i.naturalWidth > 0).length,
            appIconImages: document.querySelectorAll('.app-icon img').length,
            appIconLoaded: Array.from(document.querySelectorAll('.app-icon img'))
                .filter(i => i.complete && i.naturalWidth > 0).length,
            qsImages: document.querySelectorAll('#quick-settings .qs-item img.qs-icon').length,
            qsLoaded: Array.from(document.querySelectorAll('#quick-settings .qs-item img.qs-icon'))
                .filter(i => i.complete && i.naturalWidth > 0).length,
            navButtonsWithImage: document.querySelectorAll('#system-navigation button.has-image').length,
        };
    }

    async function loadAsset(asset) {
        const rec = {
            id: asset.id, kind: asset.kind, url: asset.url,
            expectedWidth: asset.width, expectedHeight: asset.height,
            expectedBytes: asset.bytes, expectedSha256: asset.sha256,
        };
        rec.image = await new Promise(resolve => {
            const img = new Image();
            const timer = setTimeout(() => resolve({ok: false, error: 'image timeout'}), 12000);
            img.onload = () => {
                clearTimeout(timer);
                resolve({ok: true, width: img.naturalWidth, height: img.naturalHeight});
            };
            img.onerror = () => { clearTimeout(timer); resolve({ok: false, error: 'WebKit image load error'}); };
            img.src = asset.url;
        });
        try {
            const response = await fetch(asset.url, {cache: 'no-store'});
            rec.status = response.status;
            rec.mime = (response.headers.get('content-type') || '').split(';')[0].trim();
            const bytes = new Uint8Array(await response.arrayBuffer());
            rec.bytes = bytes.length;
            rec.sha256 = await sha256Hex(bytes);
        } catch (e) {
            rec.fetchError = String(e);
        }
        rec.ok = !!(rec.image.ok &&
            rec.image.width === asset.width && rec.image.height === asset.height &&
            rec.status === 200 && rec.mime === 'image/png' &&
            rec.bytes === asset.bytes && rec.expectedSha256 === rec.sha256);
        return rec;
    }

    async function qsReopenCheck() {
        const cycles = [];
        if (!window.qs) return {cycles, error: 'Quick Settings unavailable'};
        for (let i = 0; i < 2; i++) {
            window.qs.open();
            await wait(350);
            const panel = document.getElementById('quick-settings');
            const imgs = Array.from((panel || document).querySelectorAll('.qs-item img.qs-icon'));
            const srcs = imgs.map(img => img.currentSrc || img.src);
            cycles.push({
                open: !!(panel && !panel.classList.contains('hidden')),
                imageCount: imgs.length,
                loaded: imgs.filter(img => img.complete && img.naturalWidth > 0).length,
                uniqueSrcs: new Set(srcs).size,
                failedStates: imgs.filter(img => img.dataset.iconState === 'failed').length,
                verboseTiles: panel ? panel.querySelectorAll('#qs-verbose-boot').length : 0,
            });
            window.qs.close();
            await wait(180);
        }
        return {cycles};
    }

    async function appSwitchCheck() {
        const steps = [];
        if (!window.appRegistry || !window.nuxel) return {steps, error: 'launcher controller unavailable'};
        function visible(el) {
            if (!el || el.hidden) return false;
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' &&
                   Number(style.opacity || 1) > 0 && rect.width > 0 && rect.height > 0;
        }
        function snap(label) {
            const frames = Array.from(document.querySelectorAll('.pwa-frame'));
            const bars = Array.from(document.querySelectorAll('.pwa-app-bar'));
            steps.push({
                label,
                frames: frames.length,
                visibleFrames: frames.filter(visible).length,
                visibleFrameSrcs: frames.filter(visible).map(f => f.getAttribute('src')),
                bars: bars.length,
                visibleBars: bars.filter(visible).length,
                closeButtons: document.querySelectorAll('.pwa-close-btn').length,
                current: window.nuxel.appSession && window.nuxel.appSession.app ? window.nuxel.appSession.app.id : null,
                state: window.nuxel.appSession ? window.nuxel.appSession.state : null,
            });
        }
        appRegistry.launchApp('nuxel-settings');
        await wait(1600);
        snap('settings-1');
        if (window.NuxelLauncherClose) window.NuxelLauncherClose();
        await wait(500);
        snap('home');
        appRegistry.launchApp('nuxel-settings');
        await wait(1300);
        snap('settings-2');
        appRegistry.launchApp('org.nuxel.Browser');
        await wait(1300);
        snap('browser');
        if (window.NuxelLauncherClose) window.NuxelLauncherClose();
        await wait(500);
        snap('home-final');
        return {steps};
    }

    async function trigger() {
        try {
            const r = await fetch('icon-health-trigger.json?probe=' + Date.now(), {cache: 'no-store'});
            if (!r.ok) return null;
            const doc = await r.json();
            return doc && doc.enabled === true && doc.run_id ? doc : null;
        } catch (e) { return null; }
    }

    async function run() {
        // Never launch apps or reload the owner's Home unless an explicit,
        // short-lived trigger file is served.  Normal production boots skip.
        const gate = await trigger();
        if (!gate) return;
        const runId = String(gate.run_id);
        try { if (localStorage.getItem(RUN_KEY) === runId) return; } catch (e) {}
        const phase = sessionStorage.getItem(PHASE_KEY);
        if (!phase || phase !== runId + ':reload') {
            // First pass: record the freshly booted DOM, then prove Home can be
            // reloaded without duplicating icons.  The second pass produces the
            // full report (sessionStorage survives the reload).
            const pre = domSnapshot();
            try {
                sessionStorage.setItem('nuxel.iconHealth.preReload.' + VERSION, JSON.stringify(pre));
                sessionStorage.setItem(PHASE_KEY, runId + ':reload');
            } catch (e) {}
            post('PRE_RELOAD', pre);
            await wait(250);
            location.reload();
            return;
        }

        const started = Date.now();
        const out = {
            schema: 'nuxel.icon-health/1', version: VERSION,
            generated: new Date().toISOString(),
            href: location.href, dpr: window.devicePixelRatio,
            runId: runId, cacheVersion: null, cacheNames: [], registration: null,
            assets: [], errors: [], qs: null, apps: null,
            dom: null, preReload: null, storageProbe: null,
            storageKeysBefore: [], storageKeysAfter: [],
        };
        try {
            localStorage.setItem(PROBE_KEY, 'keep');
            out.storageKeysBefore = Object.keys(localStorage).sort();
            out.preReload = (() => {
                try { return JSON.parse(sessionStorage.getItem('nuxel.iconHealth.preReload.' + VERSION) || 'null'); }
                catch (e) { return null; }
            })();
            try {
                const reg = await Promise.race([
                    navigator.serviceWorker.ready,
                    new Promise((_, reject) => setTimeout(() => reject(new Error('service worker ready timeout')), 9000)),
                ]);
                out.registration = {
                    scope: reg.scope,
                    active: reg.active ? reg.active.scriptURL : null,
                    state: reg.active ? reg.active.state : null,
                };
                await wait(700);
                out.cacheNames = await caches.keys();
            } catch (e) { out.errors.push('service-worker: ' + String(e)); }

            const registryResponse = await fetch('icon-registry.json', {cache: 'no-store'});
            if (!registryResponse.ok) throw new Error('icon-registry HTTP ' + registryResponse.status);
            const registry = await registryResponse.json();
            out.cacheVersion = registry.asset_revision;
            for (const asset of registry.assets) out.assets.push(await loadAsset(asset));

            out.dom = domSnapshot();
            out.qs = await qsReopenCheck();
            out.apps = await appSwitchCheck();
            // Quick Settings and app surfaces are closed before the final DOM.
            if (window.qs) window.qs.close();
            if (window.NuxelLauncherClose) window.NuxelLauncherClose();
            if (window.nuxel && window.nuxel.home) window.nuxel.home();
            await wait(350);
            out.domAfterSwitch = domSnapshot();
            out.storageProbe = localStorage.getItem(PROBE_KEY);
            out.storageKeysAfter = Object.keys(localStorage).sort();
            localStorage.removeItem(PROBE_KEY);

            const assetsOk = out.assets.length === 23 && out.assets.every(a => a.ok);
            const qsOk = out.qs && out.qs.cycles && out.qs.cycles.length === 2 &&
                out.qs.cycles.every(c => c.open && c.imageCount === 8 && c.loaded === 8 &&
                                         c.uniqueSrcs === 8 && c.failedStates === 0 && c.verboseTiles === 1);
            const appsOk = out.apps && out.apps.steps && out.apps.steps.length === 5 &&
                out.apps.steps.every(s => s.visibleFrames <= 1 && s.visibleBars <= 1) &&
                out.apps.steps.filter(s => s.label.indexOf('home') === 0).every(s => s.visibleFrames === 0) &&
                out.apps.steps.some(s => s.label === 'settings-2' && s.visibleFrames === 1);
            const reloadOk = out.dom && out.dom.duplicateImageSrcs.length === 0 &&
                out.dom.navLoaded === 3 && out.dom.uniqueImageCount === out.dom.imageCount;
            const cachesOk = out.cacheNames.some(n => n.indexOf('nuxel-icons-v28-a44-') === 0) &&
                out.cacheNames.every(n => !/^nuxel-(static|dynamic|icons|home)-v(?:[0-9]|1[0-9]|2[0-7])-/.test(n));
            const storageOk = out.storageProbe === 'keep' &&
                out.storageKeysBefore.every(k => out.storageKeysAfter.indexOf(k) >= 0);
            out.ok = !!(assetsOk && qsOk && appsOk && reloadOk && cachesOk && storageOk && out.errors.length === 0);
            out.checks = {assetsOk, qsOk, appsOk, reloadOk, cachesOk, storageOk};
            out.elapsedMs = Date.now() - started;
            try { localStorage.setItem(RUN_KEY, runId); } catch (e) {}
            try { sessionStorage.removeItem(PHASE_KEY); } catch (e) {}
            post('RESULT', out);
            if (!out.ok) console.error('A44 icon health FAILED', JSON.stringify(out.checks));
        } catch (e) {
            out.error = String(e && e.stack || e);
            out.ok = false;
            post('ERROR', out);
            console.error('A44 icon health error', out.error);
            try { localStorage.setItem(RUN_KEY, runId); } catch (err) {}
            try { sessionStorage.removeItem(PHASE_KEY); } catch (err) {}
        }
    }

    window.NuxelIconHealth = {version: VERSION, run: run};
    function start() {
        setTimeout(function () { run().catch(function () {}); }, 1400);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
    else start();
})();
