// Nuxel SnekByte — rendering, input and the menu state machine.
//
// The port's fidelity claim rests on js/snek-engine.js, which
// tools/s10plus/a33/snekbyte/parity-run.js proves identical to the original
// Python game tick for tick.  This file adds only what the original delegated to
// pygame: drawing, the keyboard/触 input, and the menu screens described in
// src/game_loop.py / src/ui.py.
(function () {
  'use strict';
  var E = window.SnekEngine;
  var el = function (id) { return document.getElementById(id); };
  var cfg = E.cloneConfig({});
  var STATE = { MENU: 'menu', SETTINGS: 'settings', PLAYING: 'playing', GAME_OVER: 'game_over' };
  var KEY_SETTINGS = 'nuxel-snekbyte-settings-v1';

  var view = {
    state: STATE.MENU, menuIndex: 0, settingsIndex: 0, overIndex: 0,
    game: null, settings: null, raf: null, acc: 0, last: 0, paused: false,
    highScore: 0, events: [], showGrid: true
  };

  function toast(m) {
    var t = el('toast'); t.textContent = m; t.classList.add('show');
    clearTimeout(toast._t); toast._t = setTimeout(function () { t.classList.remove('show'); }, 2200);
  }

  function loadPrefs() {
    try {
      var raw = localStorage.getItem(KEY_SETTINGS);
      if (!raw) return;
      var p = JSON.parse(raw);
      if (typeof p.speedIndex === 'number') cfg.defaultSpeedIndex = Math.max(0, Math.min(cfg.speedLevels.length - 1, p.speedIndex));
      if (typeof p.wonqMode === 'boolean') cfg.defaultWonqMode = p.wonqMode;
      if (typeof p.highScore === 'number') view.highScore = p.highScore;
      if (typeof p.showGrid === 'boolean') view.showGrid = p.showGrid;
    } catch (e) { /* corrupt prefs are ignored, not fatal */ }
  }
  function savePrefs() {
    try {
      localStorage.setItem(KEY_SETTINGS, JSON.stringify({
        speedIndex: view.settings ? view.settings.speedIndex : cfg.defaultSpeedIndex,
        wonqMode: view.settings ? view.settings.wonqMode : cfg.defaultWonqMode,
        highScore: view.highScore, showGrid: view.showGrid
      }));
    } catch (e) { /* storage full: the game still runs */ }
  }

  /* ---------------- canvas ---------------- */
  var canvas = el('screen'), ctx = canvas.getContext('2d');

  function resize() {
    var stage = el('stage');
    var availW = stage.clientWidth - 8, availH = stage.clientHeight - 8;
    // Keep the original aspect ratio (800x600 = 4:3).
    var scale = Math.min(availW / cfg.screenWidth, availH / cfg.screenHeight);
    scale = Math.max(1, Math.floor(scale * 4) / 4);
    canvas.width = cfg.screenWidth; canvas.height = cfg.screenHeight;
    canvas.style.width = Math.floor(cfg.screenWidth * scale) + 'px';
    canvas.style.height = Math.floor(cfg.screenHeight * scale) + 'px';
  }

  function rgb(a) { return 'rgb(' + a[0] + ',' + a[1] + ',' + a[2] + ')'; }

  function drawGrid() {
    if (!view.showGrid) return;
    ctx.strokeStyle = rgb(cfg.colors.grid);
    ctx.globalAlpha = 0.35;
    for (var x = 0; x <= cfg.gridWidth; x++) {
      ctx.beginPath(); ctx.moveTo(x * cfg.gridSize, 0); ctx.lineTo(x * cfg.gridSize, cfg.gridHeight * cfg.gridSize); ctx.stroke();
    }
    for (var y = 0; y <= cfg.gridHeight; y++) {
      ctx.beginPath(); ctx.moveTo(0, y * cfg.gridSize); ctx.lineTo(cfg.gridWidth * cfg.gridSize, y * cfg.gridSize); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  function cell(p, color) {
    ctx.fillStyle = color;
    ctx.fillRect(p[0] * cfg.gridSize, p[1] * cfg.gridSize, cfg.gridSize, cfg.gridSize);
    ctx.strokeStyle = rgb(cfg.colors.gray);
    ctx.lineWidth = 1;
    ctx.strokeRect(p[0] * cfg.gridSize + 0.5, p[1] * cfg.gridSize + 0.5, cfg.gridSize - 1, cfg.gridSize - 1);
  }

  function text(str, size, color, x, y, align) {
    ctx.fillStyle = color;
    ctx.font = 'bold ' + size + 'px "DejaVu Sans Mono", Menlo, monospace';
    ctx.textAlign = align || 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(str, x, y);
  }

  // A canvas wordmark (the upstream menu module referenced a SNEKBYTE_ASCII_ART
  // constant that does not exist in its own archive — see UPSTREAM-PROVENANCE.md
  // §2 — so this is a Nuxel-drawn title, not a ported asset).
  function drawTitle() {
    text('SNEK', 64, rgb(cfg.colors.green), cfg.screenWidth / 2 - 70, 60);
    text('BYTE', 64, rgb(cfg.colors.gold), cfg.screenWidth / 2 + 70, 60);
    text('ported from the original pygame game', 14, rgb(cfg.colors.white), cfg.screenWidth / 2, 100);
  }

  function drawMenu() {
    ctx.fillStyle = rgb(cfg.colors.uiBackground); ctx.fillRect(0, 0, cfg.screenWidth, cfg.screenHeight);
    drawTitle();
    var items = ['Play', 'Settings', (view.settings.wonqMode ? 'Deactivate' : 'Activate') + ' WoNQ mode',
                 'How the port is verified', 'Quit'];
    items.forEach(function (item, i) {
      text(item, 34, i === view.menuIndex ? rgb(cfg.colors.gold) : rgb(cfg.colors.white),
           cfg.screenWidth / 2, 200 + i * 60);
    });
    text('high score ' + view.highScore + '   ·   speed ' + E.speedName(cfg, view.settings) +
         '   ·   WoNQ ' + (view.settings.wonqMode ? 'ON' : 'OFF'),
         15, rgb(cfg.colors.white), cfg.screenWidth / 2, cfg.screenHeight - 40);
  }

  function drawSettings() {
    ctx.fillStyle = rgb(cfg.colors.uiBackground); ctx.fillRect(0, 0, cfg.screenWidth, cfg.screenHeight);
    text('Settings', 56, rgb(cfg.colors.white), cfg.screenWidth / 2, 80);
    var rows = [
      'Speed: < ' + E.speedName(cfg, view.settings) + ' (' + E.speedOf(cfg, view.settings) + ' fps) >',
      'WoNQ Mode: < ' + (view.settings.wonqMode ? 'ON' : 'OFF') + ' >',
      'Grid: < ' + (view.showGrid ? 'shown' : 'hidden') + ' >',
      'Back'
    ];
    rows.forEach(function (r, i) {
      text(r, 30, i === view.settingsIndex ? rgb(cfg.colors.gold) : rgb(cfg.colors.white),
           cfg.screenWidth / 2, 200 + i * 56);
    });
    text('← → change · ↑ ↓ move · Enter/Backspace select · Esc back', 14, rgb(cfg.colors.gray),
         cfg.screenWidth / 2, cfg.screenHeight - 40);
  }

  function drawGameOver() {
    ctx.fillStyle = rgb(cfg.colors.uiBackground); ctx.fillRect(0, 0, cfg.screenWidth, cfg.screenHeight);
    text('Game Over', 56, rgb(cfg.colors.white), cfg.screenWidth / 2, 90);
    text('Final Score: ' + view.game.score, 36, rgb(cfg.colors.gold), cfg.screenWidth / 2, 170);
    var cause = { wall: 'hit the wall', self: 'bit its own tail', poop: 'stepped on a WoNQ poop' }[view.game.cause] || 'ended';
    text('the snake ' + cause + (view.game.config.wonqModePoopThreshold ? '' : ''), 16, rgb(cfg.colors.gray), cfg.screenWidth / 2, 215);
    ['Retry', 'Main Menu'].forEach(function (item, i) {
      text(item, 32, i === view.overIndex ? rgb(cfg.colors.gold) : rgb(cfg.colors.white), cfg.screenWidth / 2, 300 + i * 56);
    });
    text('high score ' + view.highScore, 16, rgb(cfg.colors.white), cfg.screenWidth / 2, cfg.screenHeight - 40);
  }

  function drawPlaying() {
    var g = view.game;
    ctx.fillStyle = rgb(cfg.colors.black); ctx.fillRect(0, 0, cfg.screenWidth, cfg.screenHeight);
    drawGrid();
    g.poops.forEach(function (p) { cell(p.position, rgb(cfg.colors.brown)); });
    if (g.food.position) cell(g.food.position, rgb(cfg.colors.food));
    g.snake.positions.forEach(function (p, i) { cell(p, i === 0 ? rgb(cfg.colors.gold) : rgb(cfg.colors.green)); });
    text('Score: ' + g.score, 28, rgb(cfg.colors.gold), 70, 22);
    if (view.settings.wonqMode) {
      text('Poop-o-meter: ' + g.shitCounter + '/' + cfg.wonqModePoopThreshold, 26, rgb(cfg.colors.white),
           cfg.screenWidth - 190, 22);
    }
    if (view.paused) {
      ctx.fillStyle = 'rgba(0,0,0,.6)'; ctx.fillRect(0, 0, cfg.screenWidth, cfg.screenHeight);
      text('paused — Space to resume', 30, rgb(cfg.colors.white), cfg.screenWidth / 2, cfg.screenHeight / 2);
    }
  }

  function draw(ts) {
    requestAnimationFrame(draw);
    // Tick at the speed-table rate (the original drove pygame's clock with
    // GameSettings.get_speed()); rendering happens every animation frame.
    var dt = view.last ? ts - view.last : 0;
    view.last = ts;
    if (view.state === STATE.PLAYING && !view.paused) {
      view.acc += dt;
      var period = 1000 / E.speedOf(cfg, view.settings);
      var guard = 0;
      while (view.acc >= period && guard++ < 8) {
        view.acc -= period;
        E.step(view.game, view.settings);
        if (view.game.gameOver) {
          finishGame();
          break;
        }
      }
    }
    if (view.state === STATE.MENU) drawMenu();
    else if (view.state === STATE.SETTINGS) drawSettings();
    else if (view.state === STATE.PLAYING) drawPlaying();
    else if (view.state === STATE.GAME_OVER) drawGameOver();
  }

  /* ---------------- game control ---------------- */

  function newGame() {
    view.game = E.reset(cfg, null, E.createRng(Date.now() & 0xffffffff));
    view.settings = E.settings(cfg);
    view.settings.foodPlan = null; view.settings.rng = E.createRng((Date.now() ^ 0x5bf03635) >>> 0);
    view.acc = 0; view.paused = false;
    view.state = STATE.PLAYING;
  }

  function finishGame() {
    if (view.game.score > view.highScore) {
      view.highScore = view.game.score;
      savePrefs();
      toast('New high score: ' + view.highScore);
    }
    view.state = STATE.GAME_OVER; view.overIndex = 0;
  }

  function menu() { view.state = STATE.MENU; view.menuIndex = 0; }

  function menuSelect() {
    switch (view.menuIndex) {
      case 0: newGame(); break;
      case 1: view.state = STATE.SETTINGS; view.settingsIndex = 0; break;
      case 2:
        view.settings.wonqMode = !view.settings.wonqMode;
        cfg.defaultWonqMode = view.settings.wonqMode;
        savePrefs(); toast('WoNQ mode ' + (view.settings.wonqMode ? 'ON' : 'OFF')); break;
      case 3: openVerify(); break;
      case 4: try { window.close(); } catch (e) {} break;
    }
  }

  function settingsChange(delta) {
    if (view.settingsIndex === 0) { E.changeSpeed(cfg, view.settings, delta); savePrefs(); }
    else if (view.settingsIndex === 1) { view.settings.wonqMode = !view.settings.wonqMode; cfg.defaultWonqMode = view.settings.wonqMode; savePrefs(); }
    else if (view.settingsIndex === 2) { view.showGrid = !view.showGrid; savePrefs(); }
  }

  /* ---------------- input ---------------- */

  function move(dx, dy) {
    if (view.state !== STATE.PLAYING || view.paused || !view.game) return;
    E.turn(view.game, [dx, dy]);   // a refused reversal is silently ignored, as upstream
    el('dp-up').blur();
  }

  function onKey(e) {
    var k = e.key;
    if (verifyPanelOpen()) {                     // the panel is modal
      if (k === 'Escape' || k === 'Backspace' || k === 'Enter') { closeVerify(); e.preventDefault(); }
      return;
    }
    if (view.state === STATE.MENU) {
      if (k === 'ArrowUp' || k === 'w') view.menuIndex = (view.menuIndex + 4) % 5;
      else if (k === 'ArrowDown' || k === 's') view.menuIndex = (view.menuIndex + 1) % 5;
      else if (k === 'Enter' || k === ' ') menuSelect();
      else if (k === 'Escape' || k === 'q') { try { window.close(); } catch (err) {} }
      else return;
    } else if (view.state === STATE.SETTINGS) {
      if (k === 'ArrowUp' || k === 'w') view.settingsIndex = (view.settingsIndex + 3) % 4;
      else if (k === 'ArrowDown' || k === 's') view.settingsIndex = (view.settingsIndex + 1) % 4;
      else if (k === 'ArrowLeft' || k === 'a') settingsChange(-1);
      else if (k === 'ArrowRight' || k === 'd') settingsChange(1);
      else if (k === 'Enter' || k === ' ') {
        if (view.settingsIndex === 3) menu(); else settingsChange(1);
      } else if (k === 'Escape' || k === 'Backspace') menu();
      else return;
    } else if (view.state === STATE.GAME_OVER) {
      if (k === 'ArrowUp' || k === 'w' || k === 'ArrowDown' || k === 's') view.overIndex = view.overIndex ? 0 : 1;
      else if (k === 'Enter' || k === ' ') { view.overIndex === 0 ? newGame() : menu(); }
      else if (k === 'Escape') menu();
      else return;
    } else if (view.state === STATE.PLAYING) {
      if (k === 'ArrowUp' || k === 'w') move(0, -1);
      else if (k === 'ArrowDown' || k === 's') move(0, 1);
      else if (k === 'ArrowLeft' || k === 'a') move(-1, 0);
      else if (k === 'ArrowRight' || k === 'd') move(1, 0);
      else if (k === ' ') { view.paused = !view.paused; }
      else if (k === 'Escape' || k === 'q') { menu(); }
      else return;
    }
    e.preventDefault();
  }

  // Swipe over the stage (touch devices), plus the on-screen D-pad.
  function installSwipe() {
    var sx = 0, sy = 0, active = false;
    var stage = el('stage');
    stage.addEventListener('touchstart', function (e) {
      if (!e.touches.length) return;
      active = true; sx = e.touches[0].clientX; sy = e.touches[0].clientY;
    }, { passive: true });
    stage.addEventListener('touchend', function (e) {
      if (!active || !e.changedTouches.length) return;
      active = false;
      var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) < 24 && Math.abs(dy) < 24) return;
      if (Math.abs(dx) > Math.abs(dy)) move(dx > 0 ? 1 : -1, 0);
      else move(0, dy > 0 ? 1 : -1);
    }, { passive: true });
  }


  /* ---------------- verification panel (DOM, single source for this claim) ---- */
  // The port's fidelity claim lives in ONE place in the UI: this panel.  It is a
  // DOM sheet rather than a canvas screen so the commands are selectable and the
  // text reflows on a phone-sized viewport.
  function verifyPanel() { return el('panel-provenance'); }
  function verifyPanelOpen() { var p = verifyPanel(); return !!p && p.classList.contains('open'); }
  function openVerify() {
    var p = verifyPanel();
    if (p) { p.classList.add('open'); var c = el('prov-close'); if (c) c.focus(); }
    else { view.state = STATE.MENU; }          // no panel in the DOM: fail visibly, don't lie
  }
  function closeVerify() {
    var p = verifyPanel();
    if (p) p.classList.remove('open');
    if (view.state !== STATE.PLAYING && view.state !== STATE.GAME_OVER) menu();
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadPrefs();
    view.settings = E.settings(cfg);
    view.settings.foodPlan = null;
    if (window.matchMedia && window.matchMedia('(hover: none)').matches) document.body.classList.add('showpad');
    el('pad-toggle').addEventListener('click', function () { document.body.classList.toggle('showpad'); });
    el('pad-toggle').addEventListener('touchstart', function () { document.body.classList.add('showpad'); });
    el('help').addEventListener('click', openVerify);
    el('prov-close').addEventListener('click', closeVerify);
    el('close').addEventListener('click', function () { try { window.close(); } catch (e) {} });
    [['dp-up', 0, -1], ['dp-down', 0, 1], ['dp-left', -1, 0], ['dp-right', 1, 0]].forEach(function (b) {
      var node = el(b[0]);
      node.addEventListener('click', function () { move(b[1], b[2]); });
    });
    el('restart').addEventListener('click', newGame);
    el('menu').addEventListener('click', menu);
    el('pause').addEventListener('click', function () { if (view.state === STATE.PLAYING) view.paused = !view.paused; });
    el('fast').addEventListener('click', function () {
      var lvl = prompt('Speed index 0-' + (cfg.speedLevels.length - 1) +
        '\nspeeds: ' + cfg.speedLevels.join(', ') + ' fps\n\n(settings screen exposes this without typing)');
      if (lvl === null) return;
      var n = parseInt(lvl, 10);
      if (isNaN(n) || n < 0 || n >= cfg.speedLevels.length) { toast('Speed index must be 0-' + (cfg.speedLevels.length - 1)); return; }
      view.settings.speedIndex = n; savePrefs(); toast('speed ' + E.speedName(cfg, view.settings));
    });
    document.addEventListener('keydown', onKey);
    window.addEventListener('resize', resize);
    window.addEventListener('orientationchange', function () { setTimeout(resize, 200); });
    installSwipe();
    resize();
    requestAnimationFrame(draw);
  });
}());
