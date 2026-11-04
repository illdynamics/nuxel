/* Nuxel Doom — touch HUD, audio, persistence and app lifecycle. */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const ENGINE = window.NuxelDoomEngine;
  const SETTINGS_KEY = 'nuxel.doom.settings.v1';
  const SAVE_KEY = 'nuxel.doom.progress.v1';
  const DEFAULT_SETTINGS = {
    sound: true, haptics: true, lookSensitivity: 0.0034, inverted: false,
    leftHanded: false, opacity: 0.82,
  };
  let settings = Object.assign({}, DEFAULT_SETTINGS);
  try { Object.assign(settings, JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')); } catch (e) {}
  let progress = { bestSector: 1, kills: 0, runs: 0 };
  try { Object.assign(progress, JSON.parse(localStorage.getItem(SAVE_KEY) || '{}')); } catch (e) {}

  const canvas = $('view');
  const ctx = canvas.getContext('2d', { alpha: false });
  const engine = new ENGINE({ width: 320, height: 180 });
  let raf = 0, last = 0, paused = true, started = false;
  let fireHeld = false, useLatch = false;
  const input = { forward: 0, strafe: 0, turn: 0, lookYaw: 0, lookPitch: 0, run: false };

  // ---- Nuxel host integration --------------------------------------------
  // The launcher owns the real chrome. Immersive mode is requested explicitly:
  // Doom gets the whole glass, the top bar and triple buttons disappear, and
  // the launcher re-reveals them on a top/bottom edge gesture. The app never
  // raises the system keyboard: there are no text fields and focus is dropped.
  let immersive = false;
  let savedOrientation = null;
  let landscapeRequested = false;
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
      const parent = window.parent;
      if (parent && parent !== window && parent.nuxel && typeof parent.nuxel.dismissKeyboard === 'function') {
        parent.nuxel.dismissKeyboard();
        return;
      }
    } catch (e) { /* same-origin host only */ }
    try {
      if (window.NuxelHost && window.NuxelHost.available) window.NuxelHost.action('dismiss-keyboard');
    } catch (e) {}
  }
  function setImmersive(on) {
    on = !!on;
    if (immersive === on) return;
    immersive = on;
    document.documentElement.classList.toggle('doom-immersive', on);
    postToHost('nuxel:immersive', { active: on });
    try {
      const parent = window.parent;
      if (parent && parent !== window && parent.nuxel && typeof parent.nuxel.setImmersive === 'function') {
        parent.nuxel.setImmersive(on);
      }
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
    }).catch(() => { /* no orientation service in the VM/browser */ });
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
  function releaseAllInput() {
    input.forward = input.strafe = input.turn = 0;
    input.lookYaw = input.lookPitch = 0;
    input.run = false;
    fireHeld = false; useLatch = false; joyPointer = null; lookPointer = null; lookLast = null;
    try { stickKnob.style.transform = 'translate(0,0)'; } catch (e) {}
    document.querySelectorAll('.action.pressed').forEach(el => el.classList.remove('pressed'));
  }

  // ---- persisted settings -------------------------------------------------
  function saveSettings() {
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch (e) {}
    applySettings();
  }
  function saveProgress() {
    try { localStorage.setItem(SAVE_KEY, JSON.stringify(progress)); } catch (e) {}
  }
  function setToggle(id, value, onText, offText) {
    const el = $(id); if (!el) return;
    el.setAttribute('aria-pressed', String(!!value));
    const label = el.querySelector('strong');
    if (label) label.textContent = value ? (onText || 'ON') : (offText || 'OFF');
  }
  function applySettings() {
    document.body.classList.toggle('left-handed', !!settings.leftHanded);
    document.documentElement.style.setProperty('--hud-opacity', String(settings.opacity));
    setToggle('set-sound', settings.sound);
    setToggle('set-haptics', settings.haptics);
    setToggle('set-invert', settings.inverted);
    setToggle('set-hand', settings.leftHanded);
    const sens = $('sens-value'); if (sens) sens.textContent = Number(settings.lookSensitivity).toFixed(4);
  }

  // ---- audio --------------------------------------------------------------
  let audio = null;
  function ensureAudio() {
    if (!settings.sound) return null;
    if (audio) { if (audio.state === 'suspended') audio.resume().catch(() => {}); return audio; }
    try { audio = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { audio = null; }
    return audio;
  }
  function tone(freq, duration, type, gain, slide) {
    const ac = ensureAudio();
    if (!ac) return;
    const osc = ac.createOscillator();
    const g = ac.createGain();
    osc.type = type || 'square';
    osc.frequency.value = freq;
    if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(30, slide), ac.currentTime + duration);
    g.gain.value = gain || 0.04;
    g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + duration);
    osc.connect(g).connect(ac.destination);
    osc.start(); osc.stop(ac.currentTime + duration);
  }
  function noise(duration, gain) {
    const ac = ensureAudio();
    if (!ac) return;
    const frames = Math.floor(ac.sampleRate * duration);
    const buffer = ac.createBuffer(1, frames, ac.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < frames; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / frames);
    const src = ac.createBufferSource(); src.buffer = buffer;
    const g = ac.createGain(); g.gain.value = gain || 0.05;
    src.connect(g).connect(ac.destination); src.start();
  }
  function sfx(kind) {
    if (!settings.sound) return;
    if (kind === 'pistol') { noise(0.08, 0.06); tone(180, 0.06, 'square', 0.03, 90); }
    else if (kind === 'shotgun') { noise(0.18, 0.10); tone(95, 0.15, 'sawtooth', 0.05, 45); }
    else if (kind === 'plasma') { tone(640, 0.08, 'sawtooth', 0.035, 280); }
    else if (kind === 'hit') { tone(110, 0.08, 'square', 0.03, 60); }
    else if (kind === 'pickup') { tone(660, 0.07, 'sine', 0.04, 990); }
    else if (kind === 'door') { tone(70, 0.35, 'sawtooth', 0.035, 140); }
    else if (kind === 'pain') { noise(0.14, 0.07); tone(80, 0.14, 'sawtooth', 0.04, 40); }
    else if (kind === 'victory') { [523, 659, 784, 1046].forEach((f, i) => setTimeout(() => tone(f, 0.18, 'square', 0.035), i * 120)); }
    else if (kind === 'dead') { tone(140, 0.8, 'sawtooth', 0.06, 30); }
  }
  function vibrate(kind) {
    if (!settings.haptics) return;
    try {
      const host = window.parent && window.parent.NuxelHost;
      if (host && host.available && typeof host.action === 'function') {
        host.action('haptics-' + (kind === 'long' ? 'long' : 'navigation')).catch(() => {});
        return;
      }
    } catch (e) {}
    try { if (navigator.vibrate) navigator.vibrate(kind === 'long' ? 35 : 12); } catch (e) {}
  }

  // ---- lifecycle ----------------------------------------------------------
  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    // Keep the world framebuffer at 320x180 for speed; the CSS upscales it.
    canvas.width = 320;
    canvas.height = 180;
    ctx.imageSmoothingEnabled = false;
    return rect;
  }

  function updateHud() {
    const s = engine.snapshot();
    $('hud-health').textContent = String(s.health).padStart(3, '0');
    $('hud-armor').textContent = String(s.armor).padStart(3, '0');
    $('hud-ammo').textContent = String(s.ammo).padStart(2, '0');
    $('hud-weapon').textContent = s.weapon.toUpperCase();
    $('hud-kills').textContent = s.kills + '/' + s.enemies;
    $('hud-sector').textContent = s.level + '/' + s.levels;
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    if (!last) last = now;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!paused) {
      if (fireHeld) engine.fire();
      engine.update(dt, input);
      input.lookYaw = 0;
      input.lookPitch = 0;
      if (engine.state === 'dead' && !document.body.classList.contains('dead')) showEnd(false);
      if (engine.state === 'victory' && !document.body.classList.contains('victory')) showEnd(true);
      updateHud();
    }
    engine.render(ctx);
  }

  function startGame(sector) {
    ensureAudio();
    setImmersive(true);
    requestLandscape();
    hideKeyboard();
    engine.reset((sector || 0));
    stopped = false;
    paused = false;
    started = true;
    document.body.classList.remove('dead', 'victory', 'paused');
    $('start-screen').hidden = true;
    $('pause-screen').hidden = true;
    $('end-screen').hidden = true;
    $('hud').hidden = false;
    $('controls').hidden = false;
    progress.runs = (progress.runs || 0) + 1;
    saveProgress();
    vibrate('navigation');
    sfx('door');
    last = 0;
    dismissKeyboard();
    setTimeout(dismissKeyboard, 180);
  }
  let stopped = false;

  function pauseGame() {
    if (!started) return;
    paused = true;
    document.body.classList.add('paused');
    $('pause-screen').hidden = false;
    $('hud').hidden = true;
    $('controls').hidden = true;
    releaseAllInput();
    vibrate('navigation');
  }
  function resumeGame() {
    if (!started) return;
    paused = false;
    document.body.classList.remove('paused');
    $('pause-screen').hidden = true;
    $('hud').hidden = false;
    $('controls').hidden = false;
    last = 0;
  }
  function showEnd(victory) {
    paused = true;
    started = false;
    document.body.classList.add(victory ? 'victory' : 'dead');
    $('end-title').textContent = victory ? 'HELLGATE CLEARED' : 'YOU DIED';
    $('end-copy').textContent = victory
      ? 'All three sectors are clear. The penguin has a shotgun and the demons know it.'
      : 'The demons win this round. Restart the sector and make them regret it.';
    $('end-screen').hidden = false;
    $('hud').hidden = true;
    $('controls').hidden = true;
    releaseAllInput();
    progress.bestSector = Math.max(progress.bestSector || 1, engine.levelIndex + 1);
    progress.kills = (progress.kills || 0) + engine.kills;
    saveProgress();
    sfx(victory ? 'victory' : 'dead');
    vibrate(victory ? 'long' : 'navigation');
  }

  function exitApp() {
    setImmersive(false);
    restoreOrientation();
    dismissKeyboard();
    try { if (window.parent && window.parent.nuxel && window.parent.nuxel.home) window.parent.nuxel.home(); } catch (e) {}
    try { if (window.parent && window.parent.NuxelLauncherClose) window.parent.NuxelLauncherClose(); } catch (e) {}
  }
  function returnToCampaign() {
    setImmersive(false);
    restoreOrientation();
    paused = true;
    started = false;
    releaseAllInput();
    document.body.classList.remove('dead', 'victory', 'paused');
    $('pause-screen').hidden = true;
    $('end-screen').hidden = true;
    $('settings-screen').hidden = true;
    $('start-screen').hidden = false;
    $('hud').hidden = true;
    $('controls').hidden = true;
    dismissKeyboard();
  }

  function launchClassic() {
    const note = $('classic-note');
    if (note) { note.hidden = false; note.textContent = 'Requesting classic engine…'; }
    fetch('http://127.0.0.1:8080/api/v1/apps/exec', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: 'io.github.fabiangreffrath.Doom', app_id: 'org.nuxel.Doom', source: 'doom-launcher' }),
    }).then(r => r.json()).then(doc => {
      if (note) note.textContent = doc && doc.success ? 'Classic engine starting…' : 'Classic engine unavailable: ' + ((doc && (doc.detail || doc.error)) || 'not installed');
    }).catch(() => { if (note) note.textContent = 'Classic engine unavailable in this build.'; });
  }

  // ---- joystick -----------------------------------------------------------
  const stickZone = $('joy-zone');
  const stickBase = $('joy-base');
  const stickKnob = $('joy-knob');
  let joyPointer = null, joyCenter = null;
  function joyStart(e) {
    if (joyPointer !== null) return;
    joyPointer = e.pointerId;
    const r = stickBase.getBoundingClientRect();
    joyCenter = { x: r.left + r.width / 2, y: r.top + r.height / 2, radius: r.width * 0.42 };
    stickZone.setPointerCapture && stickZone.setPointerCapture(e.pointerId);
    joyMove(e);
  }
  function joyMove(e) {
    if (e.pointerId !== joyPointer) return;
    let dx = e.clientX - joyCenter.x, dy = e.clientY - joyCenter.y;
    const mag = Math.hypot(dx, dy) || 1;
    if (mag > joyCenter.radius) { dx = dx / mag * joyCenter.radius; dy = dy / mag * joyCenter.radius; }
    stickKnob.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
    const nx = dx / joyCenter.radius, ny = dy / joyCenter.radius;
    input.strafe = Math.abs(nx) > 0.16 ? nx : 0;
    input.forward = Math.abs(ny) > 0.16 ? -ny : 0;
    input.run = Math.hypot(nx, ny) > 0.86;
  }
  function joyEnd(e) {
    if (e.pointerId !== joyPointer) return;
    joyPointer = null;
    stickKnob.style.transform = 'translate(0,0)';
    input.forward = input.strafe = 0; input.run = false;
  }
  stickZone.addEventListener('pointerdown', joyStart);
  stickZone.addEventListener('pointermove', joyMove);
  stickZone.addEventListener('pointerup', joyEnd);
  stickZone.addEventListener('pointercancel', joyEnd);
  stickZone.addEventListener('lostpointercapture', joyEnd);

  // ---- look drag ----------------------------------------------------------
  let lookPointer = null, lookLast = null;
  const lookZone = $('look-zone');
  function isControl(target) { return target && target.closest && target.closest('button,.joy-zone,#hud,#overlay'); }
  lookZone.addEventListener('pointerdown', (e) => {
    if (lookPointer !== null || isControl(e.target)) return;
    lookPointer = e.pointerId; lookLast = { x: e.clientX, y: e.clientY };
    lookZone.setPointerCapture && lookZone.setPointerCapture(e.pointerId);
  });
  lookZone.addEventListener('pointermove', (e) => {
    if (e.pointerId !== lookPointer || !lookLast) return;
    const dx = e.clientX - lookLast.x, dy = e.clientY - lookLast.y;
    lookLast = { x: e.clientX, y: e.clientY };
    const sens = settings.lookSensitivity;
    input.lookYaw += dx * sens;
    input.lookPitch += (settings.inverted ? dy : -dy) * sens * 0.45;
  });
  function lookEnd(e) {
    if (e.pointerId !== lookPointer) return;
    lookPointer = null; lookLast = null;
  }
  lookZone.addEventListener('pointerup', lookEnd);
  lookZone.addEventListener('pointercancel', lookEnd);
  lookZone.addEventListener('lostpointercapture', lookEnd);

  // ---- action buttons -----------------------------------------------------
  function bindHold(id, down, up) {
    const el = $(id);
    if (!el) return;
    const press = (e) => { e.preventDefault(); e.stopPropagation(); el.classList.add('pressed'); el.setPointerCapture && el.setPointerCapture(e.pointerId); down && down(); };
    const release = (e) => { e.preventDefault(); e.stopPropagation(); el.classList.remove('pressed'); up && up(); };
    el.addEventListener('pointerdown', press);
    el.addEventListener('pointerup', release);
    el.addEventListener('pointercancel', release);
    el.addEventListener('lostpointercapture', release);
    el.addEventListener('click', (e) => { e.preventDefault(); if (!el.__heldAction) return; });
  }
  bindHold('btn-fire', () => {
    ensureAudio(); fireHeld = true; vibrate('navigation');
    const fired = engine.fire();
    if (fired) { sfx(window.NuxelDoomWeapons[engine.player.weapon].sound); setTimeout(() => { fireHeld = false; }, 260); }
    else fireHeld = false;
  }, () => { if (fireHeld) { fireHeld = false; } });
  bindHold('btn-use', () => {
    if (useLatch) return; useLatch = true;
    const what = engine.use();
    if (what === 'door') sfx('door');
    vibrate('navigation');
    setTimeout(() => { useLatch = false; }, 300);
  }, () => {});
  bindHold('btn-next', () => { engine.switchWeapon(1); vibrate('navigation'); }, () => {});
  bindHold('btn-prev', () => { engine.switchWeapon(-1); vibrate('navigation'); }, () => {});
  bindHold('btn-run', () => { input.run = !input.run; $('btn-run').classList.toggle('active', input.run); }, () => {});
  bindHold('btn-pause', () => { pauseGame(); }, () => {});
  $('btn-pause').addEventListener('click', (e) => { e.preventDefault(); pauseGame(); });

  // ---- menu wiring --------------------------------------------------------
  document.querySelectorAll('[data-sector]').forEach(btn => {
    btn.addEventListener('click', () => startGame(Number(btn.dataset.sector) || 0));
  });
  $('btn-resume').addEventListener('click', resumeGame);
  $('btn-restart').addEventListener('click', () => startGame(engine.levelIndex));
  $('btn-quit').addEventListener('click', exitApp);
  $('btn-again').addEventListener('click', () => startGame(0));
  $('btn-menu').addEventListener('click', returnToCampaign);
  const btnMenu2 = $('btn-menu-2'); if (btnMenu2) btnMenu2.addEventListener('click', returnToCampaign);
  const btnSettingsDone = $('btn-settings-done'); if (btnSettingsDone) btnSettingsDone.addEventListener('click', () => {
    $('settings-screen').hidden = true; $('start-screen').hidden = false;
  });
  $('btn-classic').addEventListener('click', launchClassic);
  $('btn-settings').addEventListener('click', () => {
    $('start-screen').hidden = true; $('settings-screen').hidden = false;
  });
  $('btn-settings-back').addEventListener('click', () => {
    $('settings-screen').hidden = true; $('start-screen').hidden = false;
  });
  $('set-sound').addEventListener('click', () => { settings.sound = !settings.sound; saveSettings(); });
  $('set-haptics').addEventListener('click', () => { settings.haptics = !settings.haptics; saveSettings(); });
  $('set-invert').addEventListener('click', () => { settings.inverted = !settings.inverted; saveSettings(); });
  $('set-hand').addEventListener('click', () => { settings.leftHanded = !settings.leftHanded; saveSettings(); });
  $('set-sens-down').addEventListener('click', () => { settings.lookSensitivity = Math.max(0.0015, settings.lookSensitivity - 0.0004); saveSettings(); });
  $('set-sens-up').addEventListener('click', () => { settings.lookSensitivity = Math.min(0.008, settings.lookSensitivity + 0.0004); saveSettings(); });

  // ---- keyboard (desktop convenience; phone play needs no keyboard) -------
  const keys = Object.create(null);
  function keyInput() {
    input.turn = (keys.ArrowRight ? 1 : 0) - (keys.ArrowLeft ? 1 : 0);
    if (keys.KeyW || keys.ArrowUp) input.forward = 1;
    else if (keys.KeyS || keys.ArrowDown) input.forward = -1;
    else if (joyPointer === null) input.forward = 0;
    if (keys.KeyD) input.strafe = 1;
    else if (keys.KeyA) input.strafe = -1;
    else if (joyPointer === null) input.strafe = 0;
    input.run = !!(keys.ShiftLeft || keys.ShiftRight) || input.run;
  }
  window.addEventListener('keydown', (e) => {
    if (!started || paused) return;
    keys[e.code] = true;
    if (e.code === 'Space') { e.preventDefault(); fireHeld = true; }
    else if (e.code === 'KeyE') engine.use();
    else if (e.code === 'Digit1') engine.selectWeapon(0);
    else if (e.code === 'Digit2') engine.selectWeapon(1);
    else if (e.code === 'Digit3') engine.selectWeapon(2);
    else if (e.code === 'Escape') pauseGame();
    if (/^(Arrow|Key[WASD]|Space)/.test(e.code)) e.preventDefault();
    keyInput();
  });
  window.addEventListener('keyup', (e) => {
    keys[e.code] = false;
    if (e.code === 'Space') fireHeld = false;
    keyInput();
  });

  // Open-app state can change focus; never leave the native keyboard raised.
  function hideKeyboard() {
    try { if (window.NuxelTouchKeyboard) window.NuxelTouchKeyboard.hide(); } catch (e) {}
    try { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); } catch (e) {}
  }
  window.addEventListener('focus', hideKeyboard);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && started && !paused) pauseGame();
    hideKeyboard();
  });
  window.addEventListener('blur', releaseAllInput);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) releaseAllInput();
  });
  window.addEventListener('pagehide', () => { setImmersive(false); restoreOrientation(); dismissKeyboard(); });
  window.addEventListener('focus', dismissKeyboard);

  applySettings();
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
  updateHud();
  raf = requestAnimationFrame(frame);
  hideKeyboard();
  setTimeout(hideKeyboard, 250);
  setTimeout(hideKeyboard, 1200);
  try {
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(() => {});
  } catch (e) {}

  // Public handle used by tests and the host diagnostics.
  window.NuxelDoom = {
    engine, startGame, pauseGame, resumeGame, setImmersive, returnToCampaign,
    settings, progress, get paused() { return paused; }, get immersive() { return immersive; },
  };
})();
