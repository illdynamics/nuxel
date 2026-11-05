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
    sound: true, haptics: true, strafe: true, leftHanded: false, turnSensitivity: 1.0,
  };
  let settings = Object.assign({}, DEFAULT_SETTINGS);
  try { Object.assign(settings, JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')); } catch (e) {}

  const canvas = $('canvas');
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
  function bridge() {
    try { if (window.parent && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    try { if (window.NuxelBridge) return window.NuxelBridge; } catch (e) {}
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
    setToggle('set-strafe', settings.strafe);
    setToggle('set-hand', settings.leftHanded);
    const sens = $('sens-value');
    if (sens) sens.textContent = Number(settings.turnSensitivity).toFixed(1);
  }

  // ---- keyboard bridge into Chocolate Doom --------------------------------
  const held = new Map();
  function dispatchKey(type, code, keyCode, key) {
    const ev = new KeyboardEvent(type, {
      key: key || code, code: code, keyCode: keyCode, which: keyCode,
      bubbles: true, cancelable: true,
    });
    try { window.dispatchEvent(ev); } catch (e) {}
    try { document.dispatchEvent(ev); } catch (e) {}
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
    try { $('joy-knob').style.transform = 'translate(0,0)'; } catch (e) {}
    joyPointer = null; lookPointer = null; lookLast = null;
    document.querySelectorAll('.action.pressed').forEach(function (el) { el.classList.remove('pressed'); });
    const run = $('btn-run'); if (run) run.classList.remove('active');
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
        '-window', '-nogui', '-nomusic', '-config', 'default.cfg',
        '-width', '640', '-height', '400', '-skill', '3',
      ]);
      if (!settings.sound) args.push('-nosound');
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

  // ---- touch controls -----------------------------------------------------
  const stickZone = $('joy-zone');
  const stickBase = $('joy-base');
  const stickKnob = $('joy-knob');
  let joyPointer = null, joyCenter = null;
  let lookPointer = null, lookLast = null;
  let turnTimer = 0;
  let runLatch = false;

  function joyStart(e) {
    if (joyPointer !== null) return;
    joyPointer = e.pointerId;
    const r = stickBase.getBoundingClientRect();
    joyCenter = { x: r.left + r.width / 2, y: r.top + r.height / 2, radius: r.width * 0.42 };
    try { stickZone.setPointerCapture(e.pointerId); } catch (err) {}
    joyMove(e);
  }
  function joyMove(e) {
    if (e.pointerId !== joyPointer || !joyCenter) return;
    let dx = e.clientX - joyCenter.x, dy = e.clientY - joyCenter.y;
    const mag = Math.hypot(dx, dy) || 1;
    if (mag > joyCenter.radius) { dx = dx / mag * joyCenter.radius; dy = dy / mag * joyCenter.radius; }
    stickKnob.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
    const nx = dx / joyCenter.radius, ny = dy / joyCenter.radius;
    const dead = 0.20;
    if (ny < -dead) keyDown('ArrowUp', 38, 'ArrowUp'); else keyUp('ArrowUp');
    if (ny > dead) keyDown('ArrowDown', 40, 'ArrowDown'); else keyUp('ArrowDown');
    if (settings.strafe) {
      if (nx < -dead) keyDown('Comma', 188, ','); else keyUp('Comma');
      if (nx > dead) keyDown('Period', 190, '.'); else keyUp('Period');
    } else {
      if (nx < -dead) keyDown('ArrowLeft', 37, 'ArrowLeft'); else keyUp('ArrowLeft');
      if (nx > dead) keyDown('ArrowRight', 39, 'ArrowRight'); else keyUp('ArrowRight');
    }
    const running = Math.hypot(nx, ny) > 0.88;
    if (running || runLatch) keyDown('ShiftLeft', 16, 'Shift'); else keyUp('ShiftLeft');
  }
  function joyEnd(e) {
    if (e.pointerId !== joyPointer) return;
    joyPointer = null;
    stickKnob.style.transform = 'translate(0,0)';
    ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Comma', 'Period'].forEach(keyUp);
    if (!runLatch) keyUp('ShiftLeft');
  }
  if (stickZone) {
    stickZone.addEventListener('pointerdown', joyStart);
    stickZone.addEventListener('pointermove', joyMove);
    stickZone.addEventListener('pointerup', joyEnd);
    stickZone.addEventListener('pointercancel', joyEnd);
    stickZone.addEventListener('lostpointercapture', joyEnd);
  }

  const lookZone = $('look-zone');
  function lookStopTurn() {
    if (turnTimer) { clearTimeout(turnTimer); turnTimer = 0; }
    keyUp('ArrowLeft'); keyUp('ArrowRight');
  }
  function lookStart(e) {
    if (lookPointer !== null) return;
    if (e.target && e.target.closest && e.target.closest('button,.joy-zone,.look-pad')) return;
    lookPointer = e.pointerId; lookLast = { x: e.clientX, y: e.clientY };
    try { lookZone.setPointerCapture(e.pointerId); } catch (err) {}
  }
  function lookMove(e) {
    if (e.pointerId !== lookPointer || !lookLast) return;
    const dx = e.clientX - lookLast.x;
    lookLast = { x: e.clientX, y: e.clientY };
    const threshold = Math.max(1.5, 5 / Math.max(0.3, settings.turnSensitivity));
    if (Math.abs(dx) < threshold) return;
    if (dx < 0) { keyUp('ArrowRight'); keyDown('ArrowLeft', 37, 'ArrowLeft'); }
    else { keyUp('ArrowLeft'); keyDown('ArrowRight', 39, 'ArrowRight'); }
    if (turnTimer) clearTimeout(turnTimer);
    turnTimer = setTimeout(lookStopTurn, 90);
  }
  function lookEnd(e) {
    if (e.pointerId !== lookPointer) return;
    lookPointer = null; lookLast = null; lookStopTurn();
  }
  if (lookZone) {
    lookZone.addEventListener('pointerdown', lookStart);
    lookZone.addEventListener('pointermove', lookMove);
    lookZone.addEventListener('pointerup', lookEnd);
    lookZone.addEventListener('pointercancel', lookEnd);
    lookZone.addEventListener('lostpointercapture', lookEnd);
  }

  // Right-side look pad.  Left/right are true engine turn keys (hold to keep
  // turning); MAP and MENU are one-shot engine shortcuts.  Chocolate Doom is a
  // faithful vanilla engine and has no free-look pitch, so no fake vertical
  // axis is exposed here.
  bindHold('look-left', function () { keyDown('ArrowLeft', 37, 'ArrowLeft'); vibrate('navigation'); }, function () { keyUp('ArrowLeft'); });
  bindHold('look-right', function () { keyDown('ArrowRight', 39, 'ArrowRight'); vibrate('navigation'); }, function () { keyUp('ArrowRight'); });
  bindHold('look-map', function () { tapKey('Tab', 9, 'Tab', 90); vibrate('navigation'); }, function () {});
  bindHold('look-menu', function () { tapKey('Escape', 27, 'Escape', 90); vibrate('navigation'); }, function () {});

  function bindHold(id, down, up) {
    const el = $(id); if (!el) return;
    const press = function (e) {
      e.preventDefault(); e.stopPropagation();
      el.classList.add('pressed');
      try { el.setPointerCapture(e.pointerId); } catch (err) {}
      if (down) down();
    };
    const release = function (e) {
      e.preventDefault(); e.stopPropagation();
      el.classList.remove('pressed');
      if (up) up();
    };
    el.addEventListener('pointerdown', press);
    el.addEventListener('pointerup', release);
    el.addEventListener('pointercancel', release);
    el.addEventListener('lostpointercapture', release);
  }
  bindHold('btn-fire', function () { keyDown('ControlLeft', 17, 'Control'); vibrate('navigation'); }, function () { keyUp('ControlLeft'); });
  bindHold('btn-use', function () { tapKey('Space', 32, ' ', 140); vibrate('navigation'); }, function () {});
  bindHold('btn-next', function () {
    lastWeaponIndex = (lastWeaponIndex + 1) % WEAPON_KEYS.length;
    tapKey('Digit' + (lastWeaponIndex + 1), WEAPON_KEYS[lastWeaponIndex], String(lastWeaponIndex + 1));
    vibrate('navigation');
  }, function () {});
  bindHold('btn-prev', function () {
    lastWeaponIndex = (lastWeaponIndex + WEAPON_KEYS.length - 1) % WEAPON_KEYS.length;
    tapKey('Digit' + (lastWeaponIndex + 1), WEAPON_KEYS[lastWeaponIndex], String(lastWeaponIndex + 1));
    vibrate('navigation');
  }, function () {});
  bindHold('btn-run', function () {
    runLatch = !runLatch;
    $('btn-run').classList.toggle('active', runLatch);
    if (runLatch) keyDown('ShiftLeft', 16, 'Shift'); else keyUp('ShiftLeft');
  }, function () {});
  bindHold('btn-pause', pauseEngine, function () {});

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
  $('set-sound').addEventListener('click', function () { settings.sound = !settings.sound; saveSettings(); });
  $('set-haptics').addEventListener('click', function () { settings.haptics = !settings.haptics; saveSettings(); });
  $('set-strafe').addEventListener('click', function () { settings.strafe = !settings.strafe; saveSettings(); });
  $('set-hand').addEventListener('click', function () { settings.leftHanded = !settings.leftHanded; saveSettings(); });
  $('set-sens-down').addEventListener('click', function () { settings.turnSensitivity = Math.max(0.4, settings.turnSensitivity - 0.1); saveSettings(); });
  $('set-sens-up').addEventListener('click', function () { settings.turnSensitivity = Math.min(2.5, settings.turnSensitivity + 0.1); saveSettings(); });

  // Desktop convenience only.  Phone play needs no keyboard.
  window.addEventListener('keydown', function (e) {
    if (!engineStarted || paused) return;
    if (e.code === 'Escape') { e.preventDefault(); pauseEngine(); }
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
  window.addEventListener('pagehide', function () { releaseAllInput(); setImmersive(false); restoreOrientation(); dismissKeyboard(); });

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
    if (!event.data || event.data.type !== 'nuxel:close-request') return;
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
  };
})();
