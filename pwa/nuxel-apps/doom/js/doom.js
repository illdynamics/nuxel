/* Nuxel Doom — real Chocolate Doom WAD engine shell.
 *
 * The engine is the Cloudflare WebSockets Doom build of Chocolate Doom 3.0,
 * compiled to WebAssembly.  Nuxel supplies the WAD catalogue (read-only bridge
 * endpoint), the launch flow, the multitouch HUD and lifecycle integration.
 * Touch gestures are translated into the engine's own keyboard events; there
 * is no global input injection and no text field that can raise the OSK.
 */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const BRIDGE = 'http://127.0.0.1:8080';
  const SETTINGS_KEY = 'nuxel.doom.wad.settings.v1';
  const SELECTED_KEY = 'nuxel.doom.wad.selected.v1';
  const ENGINE_JS = 'engine/websockets-doom.js?v=p77002';
  const ENGINE_WASM = 'engine/websockets-doom.wasm?v=p77002';
  const DEFAULT_SETTINGS = {
    sound: true, haptics: true, leftHanded: false, sensitivity: 3,
  };
  let settings = Object.assign({}, DEFAULT_SETTINGS);
  try { Object.assign(settings, JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')); } catch (e) {}

  const canvas = $('canvas');
  try {
    document.documentElement.dataset.doomBuild = 'p82000';
    const marker = document.createElement('meta');
    marker.id = 'doom-p82000-js';
    marker.name = 'nuxel-doom-build';
    marker.content = 'p82000';
    document.head.appendChild(marker);
  } catch (e) {}
  let catalogue = [];
  let selectedWad = null;
  let selectedEngine = 'nuxel';
  let startMode = 'episode';
  let engineModule = null;
  let engineStarted = false;
  let paused = false;
  let immersive = false;
  let savedOrientation = null;
  let landscapeRequested = false;
  let scriptPromise = null;
  let lastWeaponIndex = 0;

  const WEAPON_KEYS = [49, 50, 51, 52, 53, 54, 55]; // 1..7

  // ---- host integration ---------------------------------------------------
  function postToHost(type, detail) {
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage(Object.assign({ type: type }, detail || {}), window.location.origin);
      }
    } catch (e) { /* standalone/offline: the app still plays */ }
  }
  function dismissKeyboard() {
    try { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); } catch (e) {}
    try { if (window.NuxelTouchKeyboard) window.NuxelTouchKeyboard.hide(); } catch (e) {}
    try {
      const p = window.parent;
      if (p && p !== window && p.nuxel && typeof p.nuxel.dismissKeyboard === 'function') {
        p.nuxel.dismissKeyboard(); return;
      }
    } catch (e) { /* same-origin host only */ }
    try { if (window.NuxelHost && window.NuxelHost.available) window.NuxelHost.action('dismiss-keyboard'); } catch (e) {}
  }
  function setImmersive(on) {
    on = !!on;
    if (immersive === on) return;
    immersive = on;
    document.documentElement.classList.toggle('doom-immersive', on);
    postToHost('nuxel:immersive', { active: on });
    try {
      const p = window.parent;
      if (p && p !== window && p.nuxel && typeof p.nuxel.setImmersive === 'function') p.nuxel.setImmersive(on);
    } catch (e) {}
  }
  let doomBridge = null;
  function bridge() {
    // Never use Home's shared client for Doom-only verbs: it carries
    // app_id=org.nuxel.Home and the bridge correctly denies the automap key.
    try {
      if (window.NuxelBridgeClient && !doomBridge) {
        doomBridge = new window.NuxelBridgeClient({ appId: 'org.nuxel.Doom' });
      }
      if (doomBridge && typeof doomBridge.call === 'function') return doomBridge;
    } catch (e) {}
    try { if (window.NuxelBridge) return window.NuxelBridge; } catch (e) {}
    try { if (window.parent && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    return null;
  }
  function requestLandscape() {
    const b = bridge();
    if (!b || typeof b.call !== 'function' || landscapeRequested) return;
    landscapeRequested = true;
    Promise.resolve(b.call('orientation', 'get', {})).then((cur) => {
      const mode = cur && (cur.mode || cur.requested_mode);
      if (mode && mode !== 'landscape' && mode !== 'auto-landscape') savedOrientation = mode;
      return b.call('orientation', 'set', { mode: 'landscape' });
    }).catch(() => { /* desktop/VM has no orientation service */ });
  }
  function restoreOrientation() {
    if (!landscapeRequested) return;
    landscapeRequested = false;
    const b = bridge();
    const mode = savedOrientation;
    savedOrientation = null;
    if (!b || typeof b.call !== 'function' || !mode) return;
    Promise.resolve(b.call('orientation', 'set', { mode: mode })).catch(() => {});
  }

  // ---- audio unlock -------------------------------------------------------
  let primeAudioCtx = null;
  function audioUnlocked() {
    try { return !!primeAudioCtx && primeAudioCtx.state === 'running'; } catch (e) { return false; }
  }
  function primeAudio() {
    if (!settings.sound) return false;
    try {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      if (!primeAudioCtx) primeAudioCtx = new AC();
      if (primeAudioCtx.state === 'suspended') { primeAudioCtx.resume(); }
      return primeAudioCtx.state === 'running';
    } catch (e) { return false; }
  }
  function surfaceAudioState() {
    const n = $('audio-note');
    if (!n) return;
    if (!settings.sound) { n.textContent = 'Sound is OFF. Enable it in Touch & Audio, then tap PLAY to unlock the speaker.'; return; }
    if (audioUnlocked()) { n.textContent = 'Audio unlocked and running. Effects and music route to the phone speaker.'; }
    else { n.textContent = 'Tap PLAY to enable audio. If WebKit blocks autoplay, the first tap unlocks it; the engine never fakes sound.'; }
  }

  // ---- settings -----------------------------------------------------------
  function saveSettings() {
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch (e) {}
    applySettings();
  }
  function setToggle(id, value, onText, offText) {
    const el = $(id); if (!el) return;
    el.setAttribute('aria-pressed', String(!!value));
    const label = el.querySelector('strong');
    if (label) label.textContent = value ? (onText || 'ON') : (offText || 'OFF');
  }
  function applySettings() {
    document.body.classList.toggle('left-handed', !!settings.leftHanded);
    setToggle('set-sound', settings.sound);
    setToggle('set-haptics', settings.haptics);
    setToggle('set-hand', settings.leftHanded);
    renderSensitivity();
    surfaceAudioState();
  }
  function renderSensitivity() {
    const out = $('sens-value');
    if (out) out.textContent = String(settings.sensitivity) + '\u00d7';
  }
  function changeSensitivity(delta) {
    const cur = Number(settings.sensitivity) || 3;
    settings.sensitivity = Math.max(1, Math.min(6, cur + delta));
    saveSettings();
    vibrate('navigation');
  }

  // ---- keyboard bridge into Chocolate Doom --------------------------------
  const held = new Map();
  function dispatchKey(type, code, keyCode, key) {
    // Emscripten/SDL reads legacy keyCode/which fields.  Modern KeyboardEvent
    // constructors may ignore them, and dispatching on both window and
    // document delivered every press twice (the automap opened and instantly
    // closed).  Build one event, define the legacy fields explicitly, and
    // dispatch it on the game canvas so it bubbles exactly once to whichever
    // of canvas/document/window owns the engine listener.
    const ev = new Event(type, { bubbles: true, cancelable: true });
    Object.defineProperties(ev, {
      key: { value: key || code },
      code: { value: code },
      keyCode: { value: keyCode },
      which: { value: keyCode },
      charCode: { value: 0 },
      location: { value: 0 },
      ctrlKey: { value: false },
      shiftKey: { value: false },
      altKey: { value: false },
      metaKey: { value: false },
      repeat: { value: false },
    });
    const target = canvas || document.body || window;
    try { target.dispatchEvent(ev); } catch (e) {}
  }
  function keyDown(code, keyCode, key) {
    if (held.has(code)) return;
    held.set(code, { keyCode: keyCode, key: key || code });
    dispatchKey('keydown', code, keyCode, key);
  }
  function keyUp(code) {
    const info = held.get(code);
    if (!info) return;
    held.delete(code);
    dispatchKey('keyup', code, info.keyCode, info.key);
  }
  function tapKey(code, keyCode, key, ms) {
    keyDown(code, keyCode, key);
    setTimeout(function () { keyUp(code); }, ms || 70);
  }
  function releaseAllInput() {
    Array.from(held.keys()).forEach(keyUp);
    fireHoldCount = 0;
    if (typeof resetSticks === 'function') resetSticks();
    document.querySelectorAll('.thumbstick.active,.fire-button.pressed,.map-button.pressed,.action-button.pressed')
      .forEach(function (el) { el.classList.remove('active', 'pressed'); });
    // Do not clear mapOpen here: an automap already open in the engine must
    // stay represented truthfully.  Only a real toggle changes this state.
  }
  function diagHud(tag) {
    try {
      const ids = ['walk-pad','aim-pad','fire-left','fire-right','look-map'];
      const out = { tag: tag, viewport: { w: innerWidth, h: innerHeight, dpr: devicePixelRatio }, body: document.body.className };
      ids.forEach(function (id) {
        const el = $(id);
        if (!el) { out[id] = null; return; }
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        out[id] = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
                    display: cs.display, visibility: cs.visibility, opacity: cs.opacity, z: cs.zIndex };
      });
      try { window.webkit.messageHandlers.nuxelDiag.postMessage('DOOM_HUD ' + JSON.stringify(out)); } catch (e) {}
      try { const b = bridge(); if (b && typeof b.call === 'function') b.call('storage','write',{ key:'nuxel.doom.hud.diag', data: out }).catch(function(){}); } catch (e) {}
    } catch (e) {}
  }

  function vibrate(kind) {
    if (!settings.haptics) return;
    try {
      const host = window.parent && window.parent.NuxelHost;
      if (host && host.available && typeof host.action === 'function') {
        host.action('haptics-' + (kind === 'long' ? 'long' : 'navigation')).catch(function () {});
        return;
      }
    } catch (e) {}
    try { if (navigator.vibrate) navigator.vibrate(kind === 'long' ? 35 : 12); } catch (e) {}
  }

  // ---- WAD catalogue ------------------------------------------------------
  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[c];
    });
  }
  function prettyBytes(n) {
    n = Number(n) || 0;
    if (n >= 1048576) return (n / 1048576).toFixed(1) + ' MB';
    return Math.round(n / 1024) + ' KB';
  }
  function renderWads() {
    const host = $('wad-list');
    if (!host) return;
    if (!catalogue.length) {
      host.innerHTML = '<button class="wad-tile" type="button" disabled><span class="campaign-art">!</span>' +
        '<span><strong>NO WAD FOUND</strong><small>Install Freedoom from the OS, or import a WAD you own below, then SCAN AGAIN.</small></span></button>';
      const subtitle = $('start-subtitle'); if (subtitle) subtitle.textContent = 'NO PLAYABLE WAD';
      return;
    }
    const saved = localStorage.getItem(SELECTED_KEY) || '';
    if (!selectedWad) {
      selectedWad = catalogue.find(function (w) { return w.id === saved; }) ||
        catalogue.find(function (w) { return w.tags && w.tags.indexOf('IWAD') !== -1; }) || catalogue[0];
    }
    host.innerHTML = catalogue.map(function (w) {
      const tags = (w.tags || []).join(' · ');
      return '<button class="wad-tile' + (w.id === selectedWad.id ? ' primary' : '') + '" type="button" data-wad="' +
        escapeHtml(w.id) + '" aria-pressed="' + (w.id === selectedWad.id) + '">' +
        '<span class="campaign-art">' + (w.tags && w.tags.indexOf('IWAD') !== -1 ? 'IWAD' : 'PWAD') + '</span>' +
        '<span><strong>' + escapeHtml(w.name) + '</strong><small>' + escapeHtml(w.file) + ' · ' +
        prettyBytes(w.size) + '</small></span><span class="wad-tag">' + escapeHtml(tags) + '</span></button>';
    }).join('');
    host.querySelectorAll('[data-wad]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const id = btn.getAttribute('data-wad');
        selectedWad = catalogue.find(function (w) { return w.id === id; }) || selectedWad;
        try { localStorage.setItem(SELECTED_KEY, selectedWad.id); } catch (e) {}
        renderWads(); updateStartSubtitle();
        vibrate('navigation');
      });
    });
    updateStartSubtitle();
  }
  function updateStartSubtitle() {
    const el = $('start-subtitle');
    if (!el) return;
    if (!selectedWad) { el.textContent = 'NO WAD SELECTED'; return; }
    const doom1 = (selectedWad.tags || []).some(function (t) { return t === 'Doom 1' || t === 'Freedoom'; });
    el.textContent = (startMode === 'episode' ? (doom1 ? 'WARP TO EPISODE 1, MAP 1' : 'WARP TO MAP 01') : 'TITLE SCREEN · IN-GAME MENU') + ' · ' + selectedWad.name;
  }
  function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }
  async function importWad(file) {
    const note = $('wad-import-note');
    const ack = $('wad-license-ack');
    if (!file) return;
    if (!/\.wad$/i.test(file.name)) {
      if (note) note.textContent = 'Import failed: choose a .wad file.';
      return;
    }
    if (!ack || !ack.checked) {
      if (note) note.textContent = 'Import blocked: confirm that you own the rights to this WAD.';
      return;
    }
    if (file.size > 256 * 1024 * 1024) {
      if (note) note.textContent = 'Import failed: WAD is larger than the 256 MB limit.';
      return;
    }
    if (note) note.textContent = 'Reading ' + file.name + '…';
    let data;
    try { data = await file.arrayBuffer(); }
    catch (e) { if (note) note.textContent = 'Import failed: could not read the file.'; return; }
    const b = bridge();
    if (!b || typeof b.call !== 'function') {
      if (note) note.textContent = 'Import failed: the Nuxel bridge is unavailable.';
      return;
    }
    if (note) note.textContent = 'Validating and storing ' + file.name + '…';
    let res;
    try {
      res = await b.call('doom', 'import', {
        name: file.name, license_ack: true, data_base64: arrayBufferToBase64(data),
      });
    } catch (e) {
      if (note) note.textContent = 'Import failed: ' + ((e && e.message) || e);
      return;
    }
    if (!res || res.success === false) {
      if (note) note.textContent = 'Import refused: ' + ((res && (res.error || res.detail)) || 'unknown error');
      return;
    }
    if (note) note.textContent = 'Imported ' + (res.name || file.name) + ' (' + (res.tags || []).join(' · ') + '). Rescanning…';
    await loadCatalogue();
    if (res.id) {
      selectedWad = catalogue.find(function (w) { return w.id === res.id; }) || selectedWad;
      try { localStorage.setItem(SELECTED_KEY, res.id); } catch (e) {}
      renderWads();
    }
  }

  async function loadCatalogue() {
    const host = $('wad-list');
    if (host) host.innerHTML = '<button class="wad-tile primary" type="button" disabled><span class="campaign-art">…</span><span><strong>SCANNING WADS</strong><small>Reading the read-only Nuxel WAD catalogue</small></span></button>';
    try {
      const res = await fetch(BRIDGE + '/api/v1/doom/wads', { cache: 'no-store' });
      const doc = await res.json();
      catalogue = Array.isArray(doc.wads) ? doc.wads : [];
      selectedWad = null;
      renderWads();
    } catch (e) {
      catalogue = [];
      renderWads();
    }
  }

  // ---- WASM engine start --------------------------------------------------
  function showScreen(id) {
    ['start-screen', 'settings-screen', 'about-screen', 'pause-screen', 'error-screen'].forEach(function (s) {
      const el = $(s); if (el) el.hidden = s !== id;
    });
  }
  function showError(message) {
    const copy = $('error-copy'); if (copy) copy.textContent = message;
    showScreen('error-screen');
    document.body.classList.remove('engine-running', 'loading');
  }
  function progressUi() {
    let bar = $('engine-progress');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'engine-progress';
      bar.className = 'loading-bar';
      bar.innerHTML = '<i></i>';
      const list = $('wad-list');
      if (list && list.parentNode) list.parentNode.insertBefore(bar, list.nextSibling);
    }
    return bar;
  }
  function setProgress(fraction) {
    const bar = progressUi();
    const fill = bar && bar.querySelector('i');
    if (fill) fill.style.width = Math.max(0, Math.min(100, Math.round(fraction * 100))) + '%';
  }
  function defaultConfig() {
    return [
      'use_mouse 0', 'grabmouse 0', 'fullscreen 0', 'aspect_ratio_correct 1',
      'window_width 640', 'window_height 400', 'show_endoom 0',
      'snd_samplerate 44100', 'use_libsamplerate 0',
      // Chocolate Doom's config file stores DOS set-1 scan codes, not DOM
      // keyCodes.  The old `key_fire 17` was DOM Ctrl but DOS `W`, so the Fire
      // button (ControlLeft) never matched.  These explicit bindings are the
      // real DOS scan codes and match the HUD exactly: fire = left Ctrl,
      // use = Space, run = Shift, arrows = move/turn, comma/period = strafe.
      'key_right 77', 'key_left 75', 'key_up 72', 'key_down 80',
      'key_strafeleft 51', 'key_straferight 52',
      'key_fire 29', 'key_use 57', 'key_speed 42', 'key_speed_alt 42',
      'key_strafe 56', 'key_strafe_alt 56',
      'key_lookup 73', 'key_lookdown 81', 'key_lookcenter 71',
      // Automap is bound to the Chocolate Doom KEY_* value for 'M' (77),
      // not a browser Tab.  The bridge emits a real compositor 'm' key and
      // the JS fallback sends the same KeyM event.
      'key_map_toggle 77',
      'key_prevweapon 26', 'key_nextweapon 27',
    ].join('\n');
  }
  async function fetchWadBytes(wad, onProgress) {
    const res = await fetch(BRIDGE + '/api/v1/doom/wad?id=' + encodeURIComponent(wad.id), { cache: 'force-cache' });
    if (!res.ok) throw new Error('WAD fetch failed (' + res.status + ')');
    const total = Number(res.headers.get('content-length')) || wad.size || 0;
    if (!res.body || !res.body.getReader) {
      const buf = await res.arrayBuffer();
      if (onProgress) onProgress(1);
      return new Uint8Array(buf);
    }
    const reader = res.body.getReader();
    const chunks = [];
    let got = 0;
    while (true) {
      const step = await reader.read();
      if (step.done) break;
      chunks.push(step.value);
      got += step.value.length;
      if (onProgress) onProgress(total ? Math.min(0.98, got / total) : 0.5);
    }
    const out = new Uint8Array(got);
    let at = 0;
    chunks.forEach(function (c) { out.set(c, at); at += c.length; });
    if (onProgress) onProgress(1);
    return out;
  }
  function loadEngineScript() {
    if (scriptPromise) return scriptPromise;
    scriptPromise = new Promise(function (resolve, reject) {
      const s = document.createElement('script');
      s.src = ENGINE_JS;
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error('engine script failed to load')); };
      document.body.appendChild(s);
    });
    return scriptPromise;
  }
  function safeFile(wad, index) {
    const base = String(wad.file || 'game.wad').replace(/[^A-Za-z0-9._-]/g, '_');
    return index + '-' + base;
  }
  function findBaseIwad() {
    return catalogue.find(function (w) { return w.tags && w.tags.indexOf('IWAD') !== -1; }) || null;
  }
  async function startWadEngine() {
    if (engineStarted) return;
    if (!selectedWad) { showError('No WAD is available. Add a legally obtained IWAD or install Freedoom, then scan again.'); return; }
    engineStarted = true;
    document.body.classList.add('loading');
    showScreen('start-screen');
    const note = $('engine-note');
    if (note) { note.hidden = false; note.textContent = 'Loading Chocolate Doom WebAssembly…'; }
    if (typeof WebAssembly !== 'object' || typeof WebAssembly.instantiate !== 'function') {
      engineStarted = false;
      showError('This WebKit build has WebAssembly disabled; Nuxel Doom cannot start the Chocolate Doom engine.');
      return;
    }
    setProgress(0.02);
    dismissKeyboard(); releaseAllInput();
    canvas.focus();
    requestLandscape(); setImmersive(true);

    let runtimeResolve = null;
    let runtimeReject = null;
    const runtimeReady = new Promise(function (resolve, reject) { runtimeResolve = resolve; runtimeReject = reject; });
    const module = {
      noInitialRun: true,
      canvas: canvas,
      locateFile: function (path) { return path === 'websockets-doom.wasm' ? ENGINE_WASM : path; },
      onRuntimeInitialized: function () {
        if (note) note.textContent = 'WebAssembly runtime ready; preparing the WAD…';
        if (runtimeResolve) runtimeResolve();
      },
      onAbort: function (what) { if (runtimeReject) runtimeReject(new Error('engine aborted: ' + what)); },
      print: function (text) { console.log('[doom] ' + text); },
      printErr: function (text) {
        console.warn('[doom] ' + text);
        if (/Error|failed|fatal/i.test(String(text))) {
          const n = $('engine-note'); if (n) { n.hidden = false; n.textContent = String(text); }
        }
      },
    };
    window.Module = module;

    try {
      await loadEngineScript();
      await Promise.race([
        runtimeReady,
        new Promise(function (_, reject) {
          setTimeout(function () {
            reject(new Error('engine runtime timed out while compiling the 2.2 MB WebAssembly module'));
          }, 120000);
        }),
      ]);
    } catch (err) {
      engineStarted = false;
      showError('The WebAssembly engine could not initialise: ' + (err && err.message ? err.message : err));
      console.error(err);
      return;
    }

    try {
      if (note) note.textContent = 'Streaming ' + selectedWad.name + '…';
      const base = (selectedWad.tags && selectedWad.tags.indexOf('IWAD') !== -1) ? selectedWad : findBaseIwad();
      if (!base) throw new Error('A PWAD needs an IWAD. Install Freedoom or add an IWAD first.');
      const baseBytes = await fetchWadBytes(base, function (f) { setProgress(0.05 + f * 0.45); });
      const baseName = safeFile(base, 0);
      module.FS.writeFile(baseName, baseBytes);
      let fileArgs = [];
      if (base.id !== selectedWad.id) {
        const bytes = await fetchWadBytes(selectedWad, function (f) { setProgress(0.5 + f * 0.4); });
        const pwadName = safeFile(selectedWad, 1);
        module.FS.writeFile(pwadName, bytes);
        fileArgs = ['-file', pwadName];
      }
      // Explicit bindings make the touch HUD deterministic across WADs.
      try { module.FS.writeFile('default.cfg', defaultConfig()); } catch (e) {}
      try { module.FS.mkdir('/libsdl'); } catch (e) {}
      try { module.FS.mkdir('/libsdl/doom-ws-wasm'); } catch (e) {}
      try { module.FS.writeFile('/libsdl/doom-ws-wasm/default.cfg', defaultConfig()); } catch (e) {}

      const doom1 = (selectedWad.tags || []).some(function (t) { return t === 'Doom 1' || t === 'Freedoom'; });
      const args = ['-iwad', baseName].concat(fileArgs).concat([
        '-window', '-nogui', '-config', 'default.cfg',
        '-width', '640', '-height', '400', '-skill', '3',
      ]);
      // Sound is on by default: never pass -nomusic unless the owner
      // explicitly disabled sound.  -nosound covers the explicit off case.
      if (!settings.sound) { args.push('-nosound', '-nomusic'); }
      if (startMode === 'episode') {
        args.push('-warp');
        if (doom1) args.push('1', '1'); else args.push('1');
      }
      if (note) note.textContent = 'Starting Chocolate Doom…';
      setProgress(0.97);
      document.body.classList.add('engine-running');
      document.body.classList.remove('loading');
      $('controls').hidden = false;
      $('hud').hidden = false;
      diagHud('start');
      setTimeout(function () { diagHud('start+600'); }, 600);
      $('hud-wad').textContent = String(selectedWad.name || 'WAD').toUpperCase().slice(0, 24);
      callMain(args);
      setProgress(1);
      setTimeout(function () { const b = $('engine-progress'); if (b) b.style.display = 'none'; }, 1200);
      setTimeout(dismissKeyboard, 250);
      setTimeout(dismissKeyboard, 1200);
      vibrate('navigation');
    } catch (err) {
      engineStarted = false;
      document.body.classList.remove('engine-running', 'loading');
      showError('Could not load the WAD: ' + (err && err.message ? err.message : err));
      console.error(err);
    }
  }

  // ---- native comparison engines -----------------------------------------
  const NATIVE_TARGETS = {
    chocolate: 'org.nuxel.Doom.Chocolate',
  };
  async function launchNative(kind) {
    const note = $('engine-note');
    const target = NATIVE_TARGETS[kind];
    if (!target) return;
    if (note) { note.hidden = false; note.textContent = 'Requesting ' + kind.toUpperCase() + ' through the Nuxel bridge…'; }
    try {
      const res = await fetch(BRIDGE + '/api/v1/apps/exec', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: target, app_id: 'org.nuxel.Doom', source: 'doom-engine-compare' }),
      });
      const doc = await res.json().catch(function () { return {}; });
      if (doc && doc.success) {
        if (note) note.textContent = kind.toUpperCase() + ' is starting. It is a native fullscreen app; use its own keyboard or gamepad bindings.';
        setImmersive(false);
      } else {
        const why = (doc && (doc.detail || doc.error)) || ('HTTP ' + res.status);
        if (note) note.textContent = kind.toUpperCase() + ' unavailable: ' + why + '. Use NUXEL DOOM above for the touch WAD engine.';
      }
    } catch (e) {
      if (note) note.textContent = kind.toUpperCase() + ' unavailable in this build (bridge unreachable).';
    }
  }

  // ---- twin analog thumbsticks ------------------------------------------
  let fireHoldCount = 0;
  let mapOpen = false;
  const DEAD_ZONE = 0.15;
  const sticks = {
    move: { el: null, knob: null, pointer: null, x: 0, y: 0 },
    aim: { el: null, knob: null, pointer: null, x: 0, y: 0 }
  };
  const moveHeld = new Set();
  let aimDir = 0;
  let aimMagnitude = 0;
  let aimTimer = null;
  let aimKey = null;
  let aimKeyDown = false;

  function stickEls(kind) {
    const stick = $(kind === 'move' ? 'move-stick' : 'aim-stick');
    const knob = $(kind === 'move' ? 'move-knob' : 'aim-knob');
    return { stick: stick, knob: knob };
  }
  function axisValue(value) {
    const a = Math.abs(value);
    if (a <= DEAD_ZONE) return 0;
    const scaled = Math.min(1, (a - DEAD_ZONE) / (1 - DEAD_ZONE));
    // Smooth, predictable response without stealing fine control.
    return Math.sign(value) * Math.pow(scaled, 1.18);
  }
  function setKnob(kind, dx, dy, radius) {
    const s = sticks[kind];
    if (!s.knob) return;
    const max = Math.max(8, radius * 0.58);
    const len = Math.hypot(dx, dy);
    const scale = len > max ? max / len : 1;
    s.knob.style.transform = 'translate(calc(-50% + ' + (dx * scale).toFixed(2) + 'px), calc(-50% + ' + (dy * scale).toFixed(2) + 'px))';
  }
  function centreKnob(kind) {
    const s = sticks[kind];
    if (s.knob) s.knob.style.transform = 'translate(-50%, -50%)';
    if (s.el) s.el.classList.remove('active');
  }
  function setMoveKey(code, keyCode, key, on) {
    const id = code;
    if (on && !moveHeld.has(id)) { moveHeld.add(id); keyDown(code, keyCode, key); }
    else if (!on && moveHeld.has(id)) { moveHeld.delete(id); keyUp(code); }
  }
  function applyMove(x, y) {
    const ax = axisValue(x), ay = axisValue(y);
    setMoveKey('ArrowUp', 38, 'ArrowUp', ay < 0);
    setMoveKey('ArrowDown', 40, 'ArrowDown', ay > 0);
    setMoveKey('Comma', 188, ',', ax < 0);
    setMoveKey('Period', 190, '.', ax > 0);
    sticks.move.x = x; sticks.move.y = y;
  }
  function stopAimPulse() {
    if (aimTimer !== null) { clearTimeout(aimTimer); aimTimer = null; }
    if (aimKeyDown && aimKey) { keyUp(aimKey.code); aimKeyDown = false; }
    aimKey = null;
    aimDir = 0;
    aimMagnitude = 0;
  }
  // Sensitivity scales the effective stick deflection before the duty-cycle
  // computation, so the same stick travel turns faster.  sensitivity 1 keeps
  // the historical curve exactly; the shipped default is 3 (3x response).
  function aimDuty(magnitude) {
    const sens = Math.max(1, Math.min(6, Number(settings.sensitivity) || 1));
    const m = Math.max(0, Math.min(1, Math.abs(magnitude) * sens));
    const onMs = Math.round(14 + 34 * m);
    const offMs = Math.round(78 - 54 * m);
    return { magnitude: m, onMs: onMs, offMs: offMs, sensitivity: sens };
  }
  function aimPulse() {
    if (!aimDir) return;
    const spec = aimDir < 0 ? { code: 'ArrowLeft', keyCode: 37, key: 'ArrowLeft' }
                            : { code: 'ArrowRight', keyCode: 39, key: 'ArrowRight' };
    if (!aimKey || aimKey.code !== spec.code) {
      if (aimKeyDown && aimKey) keyUp(aimKey.code);
      aimKey = spec;
      aimKeyDown = false;
    }
    if (!aimKeyDown) {
      keyDown(aimKey.code, aimKey.keyCode, aimKey.key);
      aimKeyDown = true;
    }
    // Duty cycle maps stick deflection to average turn rate.  The engine only
    // exposes digital turn keys, so this is the honest analog adapter.
    const duty = aimDuty(aimMagnitude);
    const onMs = duty.onMs;
    const offMs = duty.offMs;
    aimTimer = setTimeout(function () {
      aimTimer = null;
      if (!aimDir) return;
      if (aimKeyDown && aimKey) { keyUp(aimKey.code); aimKeyDown = false; }
      aimTimer = setTimeout(aimPulse, offMs);
    }, onMs);
  }
  function applyAim(x, y) {
    const ax = axisValue(x);
    sticks.aim.x = x; sticks.aim.y = y;
    if (ax === 0) { stopAimPulse(); return; }
    const dir = ax < 0 ? -1 : 1;
    aimMagnitude = Math.abs(ax);
    if (dir !== aimDir || aimTimer === null) {
      stopAimPulse();
      aimDir = dir;
      aimMagnitude = Math.abs(ax);
      aimPulse();
    }
  }
  function bindStick(kind) {
    const pair = stickEls(kind);
    const s = sticks[kind];
    s.el = pair.stick; s.knob = pair.knob;
    if (!s.el) return;
    const down = function (ev) {
      if (s.pointer !== null || (ev.button !== undefined && ev.button !== 0)) return;
      ev.preventDefault(); ev.stopPropagation();
      s.pointer = ev.pointerId;
      s.el.classList.add('active');
      try { s.el.setPointerCapture(ev.pointerId); } catch (e) {}
      const rect = s.el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
      const dx = ev.clientX - cx, dy = ev.clientY - cy;
      const radius = Math.max(1, Math.min(rect.width, rect.height) / 2);
      setKnob(kind, dx, dy, radius);
      const nx = Math.max(-1, Math.min(1, dx / radius));
      const ny = Math.max(-1, Math.min(1, dy / radius));
      if (kind === 'move') applyMove(nx, ny); else applyAim(nx, ny);
      vibrate('navigation');
    };
    const move = function (ev) {
      if (s.pointer === null || ev.pointerId !== s.pointer) return;
      ev.preventDefault();
      const rect = s.el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
      const radius = Math.max(1, Math.min(rect.width, rect.height) / 2);
      let dx = ev.clientX - cx, dy = ev.clientY - cy;
      const len = Math.hypot(dx, dy);
      if (len > radius) { dx = dx / len * radius; dy = dy / len * radius; }
      setKnob(kind, dx, dy, radius);
      const nx = Math.max(-1, Math.min(1, dx / radius));
      const ny = Math.max(-1, Math.min(1, dy / radius));
      if (kind === 'move') applyMove(nx, ny); else applyAim(nx, ny);
    };
    const release = function (ev) {
      if (ev && ev.pointerId !== undefined && s.pointer !== null && ev.pointerId !== s.pointer) return;
      if (s.pointer === null) return;
      if (ev) { try { ev.preventDefault(); ev.stopPropagation(); } catch (e) {} }
      try { s.el.releasePointerCapture(s.pointer); } catch (e) {}
      s.pointer = null;
      centreKnob(kind);
      if (kind === 'move') {
        applyMove(0, 0);
        Array.from(moveHeld).forEach(function (code) { keyUp(code); });
        moveHeld.clear();
      } else {
        stopAimPulse();
      }
    };
    s.el.addEventListener('pointerdown', down);
    s.el.addEventListener('pointermove', move);
    s.el.addEventListener('pointerup', release);
    s.el.addEventListener('pointercancel', release);
    s.el.addEventListener('lostpointercapture', release);
  }

  function bindHold(id, down, up) {
    const el = $(id); if (!el) return;
    let activePointer = null;
    const press = function (e) {
      if (activePointer !== null) return;
      e.preventDefault(); e.stopPropagation();
      activePointer = e.pointerId;
      el.classList.add('pressed');
      try { el.setPointerCapture(e.pointerId); } catch (err) {}
      if (down) down();
    };
    const release = function (e) {
      if (e && e.pointerId !== undefined && activePointer !== null && e.pointerId !== activePointer) return;
      if (activePointer === null) return;
      activePointer = null;
      e.preventDefault(); e.stopPropagation();
      el.classList.remove('pressed');
      if (up) up();
    };
    el.addEventListener('pointerdown', press);
    el.addEventListener('pointerup', release);
    el.addEventListener('pointercancel', release);
    el.addEventListener('lostpointercapture', release);
  }
  function bindTap(id, action) {
    const el = $(id); if (!el) return;
    let pointer = null;
    el.addEventListener('pointerdown', function (ev) {
      if (pointer !== null) return;
      pointer = ev.pointerId; ev.preventDefault(); ev.stopPropagation();
      el.classList.add('pressed'); try { el.setPointerCapture(ev.pointerId); } catch (e) {}
      action();
    });
    const finish = function (ev) {
      if (ev && ev.pointerId !== undefined && pointer !== null && ev.pointerId !== pointer) return;
      pointer = null; el.classList.remove('pressed');
      if (ev) { try { ev.preventDefault(); ev.stopPropagation(); } catch (e) {} }
    };
    el.addEventListener('pointerup', finish);
    el.addEventListener('pointercancel', finish);
    el.addEventListener('lostpointercapture', finish);
  }

  function fireDown() {
    if (fireHoldCount++ === 0) keyDown('ControlLeft', 17, 'Control');
    vibrate('navigation');
  }
  function fireUp() {
    if (fireHoldCount > 0 && --fireHoldCount === 0) keyUp('ControlLeft');
  }
  function resetSticks() {
    ['move', 'aim'].forEach(function (kind) {
      const s = sticks[kind];
      if (s && s.pointer !== null && s.el) { try { s.el.releasePointerCapture(s.pointer); } catch (e) {} }
      if (s) s.pointer = null;
      centreKnob(kind);
    });
    Array.from(moveHeld).forEach(function (code) { keyUp(code); });
    moveHeld.clear();
    stopAimPulse();
  }

  bindStick('move');
  bindStick('aim');
  bindHold('fire-left', fireDown, fireUp);
  bindHold('fire-right', fireDown, fireUp);
  bindTap('use-button', function () { tapKey('Space', 32, ' ', 90); vibrate('navigation'); });
  bindTap('weapon-prev', function () { tapKey('BracketLeft', 219, '[', 90); vibrate('navigation'); });
  bindTap('weapon-next', function () { tapKey('BracketRight', 221, ']', 90); vibrate('navigation'); });
  bindTap('hud-menu', function () { tapKey('Escape', 27, 'Escape', 90); vibrate('navigation'); });

  // MAP is the only legacy auxiliary control retained.  All held movement,
  // aim and fire inputs are released first so the automap cannot inherit one.
  let lastMapPointerAt = 0;
  function writeMapDiag(ok, method, source, open, detail) {
    try {
      const b = bridge();
      if (b && typeof b.call === 'function') {
        b.call('storage', 'write', { key: 'nuxel.doom.map.last',
          data: { ok: !!ok, method: method, source: source || 'pointer',
                  open: !!open, detail: detail || null, ts: Date.now() } }).catch(function () {});
      }
    } catch (e) {}
  }
  function toggleMap(source) {
    releaseAllInput();
    mapOpen = !mapOpen;
    const map = $('look-map');
    if (map) map.classList.toggle('active', mapOpen);
    vibrate('navigation');
    const b = bridge();
    if (b && typeof b.call === 'function') {
      Promise.resolve(b.call('doom', 'map-toggle', {})).then(function (r) {
        const ok = !!(r && r.success);
        writeMapDiag(ok, 'wtype-m', source, mapOpen, ok ? null : (r && (r.detail || r.error)));
        if (!ok) tapKey('KeyM', 77, 'm', 90);
      }).catch(function (e) {
        writeMapDiag(false, 'wtype-m', source, mapOpen, String(e));
        tapKey('KeyM', 77, 'm', 90);
      });
    } else {
      tapKey('KeyM', 77, 'm', 90);
      writeMapDiag(true, 'engine-key-M', source, mapOpen, 'bridge unavailable; in-page fallback');
    }
  }
  bindHold('look-map', function () {
    lastMapPointerAt = Date.now();
    toggleMap('pointer');
  }, function () {});
  const mapButton = $('look-map');
  if (mapButton) mapButton.addEventListener('click', function (e) {
    try { e.preventDefault(); } catch (x) {}
    if (Date.now() - lastMapPointerAt < 600) return;
    toggleMap('click');
  });

  // ---- lifecycle ----------------------------------------------------------
  function pauseEngine() {
    if (!engineStarted || paused) return;
    paused = true;
    releaseAllInput();
    try { if (engineModule && engineModule.pauseMainLoop) engineModule.pauseMainLoop(); } catch (e) {}
    try { if (window.Module && window.Module.pauseMainLoop) window.Module.pauseMainLoop(); } catch (e) {}
    document.body.classList.add('paused');
    showScreen('pause-screen');
    $('hud').hidden = true;
    $('controls').hidden = true;
    vibrate('navigation');
  }
  function resumeEngine() {
    if (!paused) return;
    paused = false;
    document.body.classList.remove('paused');
    showScreen('start-screen');
    try { if (window.Module && window.Module.resumeMainLoop) window.Module.resumeMainLoop(); } catch (e) {}
    $('hud').hidden = false;
    $('controls').hidden = false;
    releaseAllInput();
    setTimeout(dismissKeyboard, 120);
  }
  function showLauncher() {
    releaseAllInput();
    document.body.classList.remove('engine-running', 'paused', 'loading');
    $('hud').hidden = true;
    $('controls').hidden = true;
    showScreen('start-screen');
    setImmersive(false);
    restoreOrientation();
    dismissKeyboard();
    // A WebAssembly Module cannot be re-initialised safely in place.  Reload
    // the app shell so the launcher (and a later WAD/engine choice) starts
    // from a clean runtime instead of leaving a paused engine behind.
    if (engineStarted) setTimeout(function () { location.reload(); }, 120);
  }
  function exitGame() {
    releaseAllInput();
    try { if (window.Module && window.Module.pauseMainLoop) window.Module.pauseMainLoop(); } catch (e) {}
    setImmersive(false);
    restoreOrientation();
    dismissKeyboard();
    try {
      if (window.parent && window.parent.nuxel && typeof window.parent.nuxel.home === 'function') {
        window.parent.nuxel.home(); return;
      }
    } catch (e) {}
    location.reload();
  }

  // ---- wiring -------------------------------------------------------------
  document.querySelectorAll('[data-start]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      startMode = btn.getAttribute('data-start') === 'title' ? 'title' : 'episode';
      updateStartSubtitle();
      primeAudio();
      surfaceAudioState();
      startWadEngine();
    });
  });
  document.querySelectorAll('[data-engine]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const kind = btn.getAttribute('data-engine');
      selectedEngine = kind;
      document.querySelectorAll('[data-engine]').forEach(function (b) { b.classList.toggle('active', b === btn); });
      if (kind === 'nuxel') {
        const n = $('engine-note'); if (n) n.textContent = 'Nuxel Doom uses the in-app Chocolate Doom WebAssembly engine with the touch HUD.';
      } else {
        launchNative(kind);
      }
      vibrate('navigation');
    });
  });
  $('btn-rescan').addEventListener('click', loadCatalogue);
  const wadFile = $('wad-import');
  if (wadFile) wadFile.addEventListener('change', function () {
    importWad(wadFile.files && wadFile.files[0]).finally(function () { wadFile.value = ''; });
  });
  $('btn-settings').addEventListener('click', function () { showScreen('settings-screen'); });
  $('btn-settings-back').addEventListener('click', function () { showScreen('start-screen'); });
  $('btn-settings-done').addEventListener('click', function () { showScreen('start-screen'); });
  $('btn-about').addEventListener('click', function () { showScreen('about-screen'); });
  $('btn-about-back').addEventListener('click', function () { showScreen('start-screen'); });
  $('btn-about-done').addEventListener('click', function () { showScreen('start-screen'); });
  $('btn-resume').addEventListener('click', resumeEngine);
  $('btn-menu').addEventListener('click', showLauncher);
  $('btn-quit').addEventListener('click', exitGame);
  $('btn-error-back').addEventListener('click', showLauncher);
  $('set-sound').addEventListener('click', function () { settings.sound = !settings.sound; if (settings.sound) primeAudio(); saveSettings(); });
  $('set-haptics').addEventListener('click', function () { settings.haptics = !settings.haptics; saveSettings(); });
  $('set-hand').addEventListener('click', function () { settings.leftHanded = !settings.leftHanded; saveSettings(); });
  $('sens-down').addEventListener('click', function () { changeSensitivity(-1); });
  $('sens-up').addEventListener('click', function () { changeSensitivity(1); });

  // Desktop convenience only.  Phone play needs no keyboard.
  window.addEventListener('keydown', function (e) {
    if (!engineStarted || paused) return;
    // Only react to a real desktop keyboard; the synthetic in-engine menu
    // Escape (hud-menu) is dispatched on the canvas and must reach the engine.
    if (e.code === 'Escape' && e.isTrusted) { e.preventDefault(); pauseEngine(); }
  });

  // Never leave an OSK or held key behind when focus changes.
  window.addEventListener('blur', releaseAllInput);
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      releaseAllInput();
      if (engineStarted && !paused) pauseEngine();
      dismissKeyboard();
    }
  });
  window.addEventListener('focus', dismissKeyboard);
  window.addEventListener('pagehide', function () { releaseAllInput(); try { if (engineStarted && !paused) pauseEngine(); } catch (e) {} setImmersive(false); restoreOrientation(); dismissKeyboard(); });

  applySettings();
  showScreen('start-screen');
  loadCatalogue();
  dismissKeyboard();
  setTimeout(dismissKeyboard, 250);
  setTimeout(dismissKeyboard, 1200);

  try {
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(function () {});
  } catch (e) {}

  /* Explicit Back contract for the central Home dispatcher.  In-game Back
     pauses; Back from settings/about/error returns to the launch screen; Back
     at the launch screen reaches the app root so Home can close it. */
  function canAppGoBack() {
    if (paused || engineStarted) return true;
    const s = $('settings-screen'), a = $('about-screen'), e = $('error-screen');
    return !!((s && !s.hidden) || (a && !a.hidden) || (e && !e.hidden));
  }
  function appGoBack() {
    if (paused) { resumeEngine(); return true; }
    if (engineStarted) { pauseEngine(); return true; }
    const s = $('settings-screen'), a = $('about-screen'), e = $('error-screen');
    if ((s && !s.hidden) || (a && !a.hidden) || (e && !e.hidden)) {
      showScreen('start-screen');
      return true;
    }
    return false;
  }
  window.NuxelBack = { canGoBack: canAppGoBack, back: appGoBack };
  window.addEventListener('message', function (event) {
    if (event.origin !== window.location.origin) return;
    if (!event.data) return;
    // Home sends lifecycle messages to a same-origin iframe.  The WebKit
    // visibility event was not reliable when the lockscreen covered an ACTIVE
    // frame, so suspend explicitly.  Pausing retains the current game state.
    if (event.data.type === 'nuxel:suspend') {
      releaseAllInput();
      pauseEngine();
      setImmersive(false);
      restoreOrientation();
      dismissKeyboard();
      return;
    }
    if (event.data.type === 'nuxel:resume') {
      resumeEngine();
      return;
    }
    if (event.data.type !== 'nuxel:close-request') return;
    releaseAllInput();
    dismissKeyboard();
    setImmersive(false);
    restoreOrientation();
  });

  // Public handle used by offline contract tests and diagnostics.
  window.NuxelDoom = {
    startWadEngine: startWadEngine,
    pauseEngine: pauseEngine,
    resumeEngine: resumeEngine,
    releaseAllInput: releaseAllInput,
    setImmersive: setImmersive,
    settings: settings,
    get catalogue() { return catalogue; },
    get selectedWad() { return selectedWad; },
    get selectedEngine() { return selectedEngine; },
    get engineStarted() { return engineStarted; },
    get paused() { return paused; },
    keyDown: keyDown,
    keyUp: keyUp,
    fireDown: fireDown,
    fireUp: fireUp,
    get fireHoldCount() { return fireHoldCount; },
    diagHud: diagHud,
    toggleMap: toggleMap,
    get sticks() { return sticks; },
    setStickForTest: function (kind, x, y) {
      if (kind === 'move') applyMove(x, y); else applyAim(x, y);
      return kind === 'move' ? { x: sticks.move.x, y: sticks.move.y } : { x: sticks.aim.x, y: sticks.aim.y };
    },
    resetSticks: resetSticks,
    deadZone: DEAD_ZONE,
    aimDuty: aimDuty,
    primeAudio: primeAudio,
    audioUnlocked: audioUnlocked,
    get sensitivity() { return settings.sensitivity; },
  };
})();
