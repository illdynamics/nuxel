/* SnekByte mobile shell. Core game logic is the original Python parity port in snek-engine.js.
 * Offline-first, no framework, no remote calls, no privileged device permissions.
 */
(function () {
  'use strict';
  var E = window.SnekEngine;
  var C = window.SnekControls;
  if (!E) throw new Error('SnekByte engine is unavailable');
  var $ = function (id) { return document.getElementById(id); };
  var canvas = $('screen'), ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('2D canvas unavailable');
  var cfg = E.cloneConfig({});
  // Nuxel defaults to WoNQ enabled to demonstrate the poo meter; the canonical
  // engine defaults remain unchanged and still pass upstream Python parity tests.
  cfg.defaultWonqMode = true;
  var PREFS_KEY = 'nuxel-snekbyte-settings-v2';
  var OLD_PREFS_KEY = 'nuxel-snekbyte-settings-v1';
  var view = { mode: 'menu', paused: false, game: null, settings: E.settings(cfg), activeSettings: null, grid: true,
    highScore: 0, raf: null, dirty: true, suspended: false, dialog: null, prefsLoaded: false };
  var playingSettings = function () { return view.mode === 'playing' && view.activeSettings ? view.activeSettings : view.settings; };
  var tickMs = function () { return 1000 / E.speedOf(cfg, playingSettings()); };
  var queue = C.createQueue(), clock = C.createClock(E.speedOf(cfg, view.settings));
  var swipe = C.createSwipe(function (dir, e) { return sendDirection(dir[0], dir[1], e, 'swipe'); });
  var debug = window.__SNEK_DEBUG__ === true || /(?:\?|&)snekdebug=1(?:&|$)/.test(location.search);
  var traces = [], frames = [], drawn = [], longTasks = [], traceId = 0, droppedMs = 0;
  var hostInactive = false;
  var background = document.createElement('canvas'), gridCached = null;
  background.width = cfg.screenWidth; background.height = cfg.screenHeight;
  var bg = background.getContext('2d'), hudKey = '';
  function bounded(list, value, max) { list.push(value); if (list.length > max) list.shift(); }
  function clearInput() { queue.clear(); swipe.clear(); }
  function rememberBest() {
    if (view.game && view.game.score > view.highScore) { view.highScore = view.game.score; savePrefs(); }
  }

  function toast(s) {
    $('toast').textContent = s;
    $('toast').classList.add('show');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { $('toast').classList.remove('show'); }, 2100);
  }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function savePrefs() {
    if (!view.prefsLoaded) return;
    var value = JSON.stringify({
      speedIndex: view.settings.speedIndex, wonqMode: view.settings.wonqMode,
      wrapWalls: view.settings.wrapWalls, showGrid: view.grid, highScore: view.highScore
    });
    try { localStorage.setItem(PREFS_KEY,value); } catch (e) { /* storage may be disabled */ }
    if (window.SnekBytePersistence) window.SnekBytePersistence.save(value);
  }
  function loadPrefs() {
    try {
      // Fall back to the intact older key if the newer JSON is corrupt. Keep
      // both keys and the maximum valid score; migration never deletes data.
      var records = [PREFS_KEY, OLD_PREFS_KEY].map(function (key) {
        try { var p = JSON.parse(localStorage.getItem(key)); return p && typeof p === 'object' ? p : {}; }
        catch (e) { return {}; }
      });
      if (window.SnekBytePersistence && window.SnekBytePersistence.value) {
        try { var nativePrefs=JSON.parse(window.SnekBytePersistence.value);
          if(nativePrefs && typeof nativePrefs==='object') records.unshift(nativePrefs);
        } catch(e) { /* malformed native record falls back to existing web data */ }
      }
      records.slice().reverse().forEach(function (p) {
        if (Number.isInteger(p.speedIndex)) view.settings.speedIndex = clamp(p.speedIndex, 0, cfg.speedLevels.length - 1);
        if (typeof p.wonqMode === 'boolean') view.settings.wonqMode = p.wonqMode;
        if (typeof p.wrapWalls === 'boolean') view.settings.wrapWalls = p.wrapWalls;
        if (typeof p.showGrid === 'boolean') view.grid = p.showGrid;
      });
      records.forEach(function (record) {
        if (Number.isFinite(record.highScore) && record.highScore >= 0)
          view.highScore = Math.max(view.highScore, Math.floor(record.highScore));
      });
    } catch (e) { /* invalid old state must not crash launch */ }
  }
  function renderStats() {
    if (view.mode !== 'menu' || view.dialog) $('back-button').setAttribute('data-action','back');
    else $('back-button').removeAttribute('data-action');
    var score = view.game ? view.game.score : 0;
    var counter = view.game ? view.game.shitCounter : 0, settings = playingSettings();
    var key = [score, view.highScore, settings.speedIndex, settings.wonqMode, settings.wrapWalls, counter, view.mode, view.paused].join('|');
    if (key === hudKey) return;
    hudKey = key;
    $('score').textContent = String(score);
    $('best').textContent = String(Math.max(view.highScore, score));
    $('speed').textContent = String(E.speedOf(cfg, playingSettings()));
    $('speed-down').disabled = settings.speedIndex === 0;
    $('speed-up').disabled = settings.speedIndex === cfg.speedLevels.length - 1;
    $('wall-mode').textContent = settings.wrapWalls ? 'WRAP ON' : 'CLASSIC WALLS';
    $('status').textContent = view.mode === 'playing' ? (view.paused ? 'PAUSED' : 'GO!') :
      view.mode === 'over' ? 'GAME OVER' : 'READY';
    $('pause-button').innerHTML = view.mode === 'playing' && !view.paused ? '⏸ <span>PAUSE</span>' : '▶ <span>RESUME</span>';
    var activeWonq = playingSettings().wonqMode;
    $('meter-count').textContent = (activeWonq ? counter : 'OFF') + ' / ' + cfg.wonqModePoopThreshold;
    $('meter-progress').setAttribute('aria-valuenow', String(activeWonq ? counter : 0));
    $('meter-progress').setAttribute('aria-valuetext', activeWonq ? counter + ' of 5 snacks' : 'WoNQ mode disabled');
    $('meter').classList.toggle('disabled', !activeWonq);
    Array.prototype.forEach.call($('meter-progress').children, function (n, i) {
      n.classList.toggle('filled', activeWonq && i < counter);
    });
    $('meter-note').textContent = activeWonq ?
      'Every 5 snacks drops a permanent poop obstacle. Watch your tail!' :
      'WoNQ Mode is off — enable it in Settings for poop obstacles.';
  }
  function showOverlay(title, desc, actions) {
    $('overlay').hidden = false;
    $('overlay-title').textContent = title;
    $('overlay-subtitle').textContent = desc;
    var container = $('overlay-buttons');
    container.textContent = '';
    actions.forEach(function (item, i) {
      var button = document.createElement('button');
      button.type = 'button'; button.textContent = item.label;
      if (i === 0) button.className = 'primary';
      button.addEventListener('click', item.action);
      container.appendChild(button);
    });
  }
  function hideOverlay() { $('overlay').hidden = true; }
  function showMenu() {
    rememberBest(); clearInput(); stopLoop(); clock.reset();
    view.mode = 'menu'; view.paused = true;
    showOverlay('SNEKBYTE', 'Eat snacks. Grow longer. Drop chaos. WoNQ mode is ' + (view.settings.wonqMode ? 'ON' : 'OFF') + '.', [
      { label: '▶ PLAY', action: startGame },
      { label: '⚙ SETTINGS', action: openSettings }
    ]);
    renderStats(); invalidate();
  }
  function startGame() {
    rememberBest(); clearInput();
    var seed = Date.now() >>> 0;
    view.game = E.reset(cfg, [], E.createRng(seed));
    view.activeSettings = E.settings(cfg, { speedIndex: view.settings.speedIndex, wonqMode: view.settings.wonqMode,
      wrapWalls: view.settings.wrapWalls, foodPlan: null, rng: E.createRng((seed ^ 0x45fb79ad) >>> 0) });
    view.mode = 'playing'; view.paused = view.suspended || document.visibilityState === 'hidden';
    clock.setRate(E.speedOf(cfg, view.activeSettings), performance.now());
    hideOverlay(); renderStats(); view.dirty = true;
    if (document.visibilityState !== 'hidden') startLoop();
    try { canvas.focus({ preventScroll: true }); } catch (e) { canvas.focus(); }
  }
  function finishGame() {
    clearInput();
    view.mode = 'over'; view.paused = true;
    if (view.game.score > view.highScore) { view.highScore = view.game.score; savePrefs(); toast('NEW HIGH SCORE!'); }
    var why = { wall: 'The wall won.', self: 'Your tail fought back.', poop: 'You stepped in it. 💩' }[view.game.cause] || 'Game over.';
    showOverlay('GAME OVER', why + ' Score: ' + view.game.score + '.', [
      { label: '↻ RETRY', action: startGame },
      { label: '☰ MENU', action: showMenu }
    ]);
    renderStats(); view.dirty = true;
  }
  function setPause(paused) {
    if (view.mode !== 'playing') return;
    if (!paused && (view.suspended || document.visibilityState === 'hidden' || view.dialog)) return;
    view.paused = !!paused;
    clearInput(); clock.reset(performance.now());
    if (view.paused) { rememberBest(); stopLoop(); }
    if (view.paused) showOverlay('PAUSED', 'Taking a breather? The snake is waiting.', [
      { label: '▶ RESUME', action: function () { setPause(false); } },
      { label: '☰ MENU', action: showMenu }
    ]);
    else { hideOverlay(); startLoop(); }
    renderStats(); invalidate();
  }
  function openDialog(which) {
    // Playing is paused while a dialog is open, including if it was open already.
    if (view.mode === 'playing' && !view.paused) setPause(true);
    view.dialog = which;
    renderStats();
    $(which + '-panel').hidden = false;
    if (which === 'settings') {
      $('speed-setting').value = String(view.settings.speedIndex);
      $('wonq-setting').checked = !!view.settings.wonqMode;
      $('wrap-setting').checked = !!view.settings.wrapWalls;
      $('grid-setting').checked = !!view.grid;
      updateSpeedLabel();
    }
    view.dirty = true;
  }
  function closeDialog() {
    if (!view.dialog) return;
    $(view.dialog + '-panel').hidden = true;
    view.dialog = null;
    renderStats();
    view.dirty = true;
  }
  function openSettings() { openDialog('settings'); }
  function updateSpeedLabel() {
    $('speed-label').textContent = E.speedName(cfg, view.settings) + ' · ' + E.speedOf(cfg, view.settings) + ' ticks/s';
  }
  function setSpeed(index) {
    index = Number.isInteger(index) ? clamp(index, 0, cfg.speedLevels.length - 1) : cfg.defaultSpeedIndex;
    if (index !== view.settings.speedIndex) {
      view.settings.speedIndex = index;
      if (view.activeSettings) view.activeSettings.speedIndex = index;
      // Give the player one full period at the new rate, never a catch-up jump.
      clock.setRate(E.speedOf(cfg, playingSettings()), performance.now());
    }
    $('speed-setting').value = String(index);
    updateSpeedLabel(); renderStats(); savePrefs();
  }
  function sendDirection(dx, dy, event, source) {
    if (view.mode !== 'playing' || view.paused || !view.game || view.dialog || view.suspended) return false;
    var now = performance.now(), trace = null;
    if (debug) {
      var stamp = event && event.timeStamp;
      if (stamp > 1e12) stamp -= performance.timeOrigin;
      // Some WebKit native events use a different monotonic clock origin.
      // Mark those unavailable instead of reporting negative/fabricated latency.
      var compatible = Number.isFinite(stamp) && stamp >= 0 && Math.abs(now-stamp) < 60000;
      trace = { id: ++traceId, source: source || 'keyboard', eventAt: compatible ? stamp : null,
        rawEventTimeStamp: event ? event.timeStamp : null, receivedAt: now, recognizedAt: now, dir: [dx, dy] };
    }
    var result = queue.offer([dx, dy], view.game.snake.direction, now, trace);
    if (trace) { trace.result = result; bounded(traces, trace, 128); }
    if (result !== 'accepted') return false;
    $('input-ack').textContent = dx < 0 ? '◀' : dx > 0 ? '▶' : dy < 0 ? '▲' : '▼';
    return true;
  }
  var DIRS = { up: [0,-1], down: [0,1], left: [-1,0], right: [1,0] };
  function handleBack() {
    if (view.dialog) closeDialog();
    else if (view.mode === 'playing' && !view.paused) setPause(true);
    else if (view.mode === 'playing') showMenu();
    else if (view.mode === 'over') showMenu();
    else return false;
    return true;
  }
  function onKey(e) {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === 'Escape' || e.key === 'Backspace') {
      if (handleBack()) e.preventDefault();
      return;
    }
    if (e.target.matches('input,select,textarea')) return;
    if (view.dialog) return;
    if (e.target.closest('button') && (e.key === 'Enter' || e.key === ' ')) return;
    if (e.repeat) return;
    var k = e.key.toLowerCase();
    var dirs = { arrowup:'up',w:'up',arrowdown:'down',s:'down',arrowleft:'left',a:'left',arrowright:'right',d:'right' };
    if (dirs[k]) { var d = DIRS[dirs[k]]; sendDirection(d[0], d[1], e, 'keyboard'); e.preventDefault(); }
    else if (k === ' ' || k === 'p') {
      if (view.mode === 'playing') { setPause(!view.paused); e.preventDefault(); }
      else if (view.mode === 'menu' || view.mode === 'over') { startGame(); e.preventDefault(); }
    } else if (k === 'enter' && view.mode !== 'playing') { startGame(); e.preventDefault(); }
  }
  function initSwipe() {
    // Pointer events on the canvas only; buttons and nav dock keep normal touch semantics.
    canvas.addEventListener('pointerdown', function (e) {
      if (view.mode !== 'playing' || view.paused || view.dialog || e.isPrimary === false || e.button !== 0) return;
      if (!swipe.start(e.pointerId, e.clientX, e.clientY)) return;
      try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
    });
    canvas.addEventListener('pointermove', function (e) {
      swipe.move(e.pointerId, e.clientX, e.clientY, e);
    }, { passive: true });
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function (type) {
      canvas.addEventListener(type, function (e) { swipe.end(e.pointerId); });
    });
  }
  function fillRect(x,y,w,h,c) { ctx.fillStyle=c; ctx.fillRect(x,y,w,h); }
  function drawCell(p, color, border) {
    var s=cfg.gridSize, x=p[0]*s, y=p[1]*s;
    fillRect(x+1,y+1,s-2,s-2,color);
    if (border) { ctx.strokeStyle=border;ctx.lineWidth=1;ctx.strokeRect(x+1.5,y+1.5,s-3,s-3); }
  }
  function drawPoop(p) {
    var s=cfg.gridSize, x=p[0]*s,y=p[1]*s;
    fillRect(x+3,y+12,s-6,5,'#784b2d');
    fillRect(x+5,y+8,s-10,5,'#b97b3e');
    fillRect(x+7,y+4,s-14,5,'#dfae6b');
    fillRect(x+7,y+8,2,2,'#0b171b'); fillRect(x+11,y+8,2,2,'#0b171b');
  }
  function drawBoard() {
    var w=cfg.screenWidth,h=cfg.screenHeight,s=cfg.gridSize;
    if (gridCached !== view.grid) {
      bg.fillStyle='#07151b';bg.fillRect(0,0,w,h);
      if (view.grid) {
        bg.strokeStyle='rgba(40,121,142,.23)';bg.lineWidth=1;bg.beginPath();
        for (var x=0;x<=cfg.gridWidth;x++) {bg.moveTo(x*s+.5,0);bg.lineTo(x*s+.5,h);}
        for (var y=0;y<=cfg.gridHeight;y++) {bg.moveTo(0,y*s+.5);bg.lineTo(w,y*s+.5);}
        bg.stroke();
      }
      gridCached = view.grid;
    }
    ctx.drawImage(background,0,0);
    if (!view.game) {
      ctx.fillStyle='#56d7dc';ctx.font='bold 28px monospace';ctx.textAlign='center';
      ctx.fillText('PRESS PLAY',w/2,h/2);
      return;
    }
    var game=view.game;
    game.poops.forEach(function (p) { drawPoop(p.position); });
    if (game.food.position) {
      var p=game.food.position;
      drawCell(p,'#fa6171','#ffd0cc');
      fillRect(p[0]*s+6,p[1]*s+5,6,6,'#ffd1b6');
    }
    game.snake.positions.forEach(function (p,i) {
      drawCell(p,i===0?'#f9e06f':'#84ef79',i===0?'#f8a93c':'#327c4f');
      if (i===0 && p[0]>=0 && p[0]<cfg.gridWidth && p[1]>=0 && p[1]<cfg.gridHeight) {
        fillRect(p[0]*s+5,p[1]*s+6,3,3,'#08151a');
        fillRect(p[0]*s+12,p[1]*s+6,3,3,'#08151a');
      }
    });
  }
  function loop(ts) {
    view.raf=null;
    if (document.visibilityState === 'hidden' || view.suspended) return;
    var started = debug ? performance.now() : 0;
    if (view.mode==='playing' && !view.paused && !view.dialog) {
      var result = clock.advance(ts, function () {
        var command = queue.take(performance.now());
        if (command) {
          if (E.turn(view.game, command.dir)) {
            if (command.trace) { command.trace.appliedAt=performance.now(); command.trace.tick=view.game.ticks+1; drawn.push(command.trace); }
          } else queue.clear();
        }
        var beforePoopCount=view.game.poops.length;
        E.step(view.game,view.activeSettings);
        if (view.game.poops.length>beforePoopCount) {
          toast('💩 POO DROP! Watch your tail!');
          $('meter').classList.add('drop-flash');
          clearTimeout(view.pooFlashTimer);
          view.pooFlashTimer=setTimeout(function(){$('meter').classList.remove('drop-flash');},480);
        }
        // Don't accumulate unbounded telemetry or memory in long-running sessions.
        if (view.game.events.length>80) view.game.events.splice(0,view.game.events.length-60);
        view.dirty=true;
        if (view.game.gameOver) { finishGame();return false; }
      });
      if (debug) droppedMs += result.droppedMs;
      if (result.steps) renderStats();
    }
    if (view.dirty) {
      drawBoard();view.dirty=false;
      if (debug) { drawn.forEach(function (trace) { trace.drawnAt=performance.now(); }); drawn.length=0; }
    }
    if (debug) bounded(frames, performance.now()-started, 300);
    // Menu/paused screens need no continuous 60 FPS polling; stop the rAF
    // after painting once. Game loop restarts on Start/Resume.
    if (view.mode==='playing' && !view.paused && !view.dialog) startLoop();
  }
  function startLoop() {
    if (view.raf!==null || document.visibilityState==='hidden' || view.suspended) return;
    view.raf=requestAnimationFrame(loop);
  }
  function stopLoop() { if(view.raf!==null)cancelAnimationFrame(view.raf);view.raf=null;clock.reset(); }
  function invalidate() { view.dirty=true;startLoop(); }
  function suspend() {
    if(view.mode==='playing'&&!view.paused)setPause(true);
    clearInput(); view.suspended=true; stopLoop();rememberBest();savePrefs();
  }
  function wake() {
    if (hostInactive || document.visibilityState==='hidden') return;
    view.suspended=false;clock.reset();invalidate();
  }
  function observeHost() {
    // Nuxel keeps Home/Recents app iframes alive with hidden=true. That does
    // not change document.visibilityState. Observe only our own surface and
    // the existing lock overlay; do not change the shell or its navigation.
    try {
      var frame=window.frameElement;
      if (!frame || !window.MutationObserver) return;
      var parentDoc=frame.ownerDocument, lock=parentDoc.getElementById('lockscreen');
      function sync() {
        hostInactive=frame.hidden || frame.style.display==='none' || !!(lock && !lock.hidden);
        if (hostInactive) suspend(); else if (view.suspended) wake();
      }
      var observer=new MutationObserver(sync);
      observer.observe(frame,{attributes:true,attributeFilter:['hidden','style']});
      if(lock)observer.observe(lock,{attributes:true,attributeFilter:['hidden']});
      sync();
      window.addEventListener('unload',function(){observer.disconnect();});
    } catch(e) { /* Cross-origin embedding gets normal visibility/lifecycle. */ }
  }
  function onVisibility() {
    if (document.visibilityState==='hidden') suspend();
    else wake();
  }
  function install() {
    loadPrefs();
    view.prefsLoaded=true;
    clock.setRate(E.speedOf(cfg,view.settings));savePrefs();updateSpeedLabel();
    $('best').textContent=String(view.highScore);
    $('settings-button').addEventListener('click',openSettings);
    $('help-button').addEventListener('click',function(){openDialog('help');});
    $('settings-close').addEventListener('click',closeDialog);
    $('settings-done').addEventListener('click',closeDialog);
    $('help-close').addEventListener('click',closeDialog);
    $('help-done').addEventListener('click',closeDialog);
    $('speed-setting').addEventListener('input',function(){setSpeed(Number(this.value));});
    $('speed-down').addEventListener('click',function(){setSpeed(view.settings.speedIndex-1);});
    $('speed-up').addEventListener('click',function(){setSpeed(view.settings.speedIndex+1);});
    $('wonq-setting').addEventListener('change',function(){
      // Switching rules mid-round would make pre-existing poop obstacles inert.
      // Apply only to next round; pause current round and explain clearly.
      view.settings.wonqMode=!!this.checked;
      savePrefs();renderStats();toast('WoNQ mode '+(this.checked?'ON':'OFF')+' — applies to next game');
    });
    $('wrap-setting').addEventListener('change',function(){
      view.settings.wrapWalls=!!this.checked;savePrefs();renderStats();
      toast((this.checked?'Wrap ON':'Classic Walls')+' — applies to next game');
    });
    $('grid-setting').addEventListener('change',function(){view.grid=!!this.checked;savePrefs();invalidate();});
    $('back-button').addEventListener('click',function(){if(!handleBack())showMenu();});
    $('pause-button').addEventListener('click',function(){if(view.mode==='playing')setPause(!view.paused);});
    Array.prototype.forEach.call(document.querySelectorAll('[data-dir]'),function(button){
      function steer(e) {var d=DIRS[button.getAttribute('data-dir')];sendDirection(d[0],d[1],e,'dpad');}
      button.addEventListener('pointerdown',function(e){
        if(e.isPrimary===false||e.button!==0)return;
        e.preventDefault();steer(e);
      });
      // Keyboard/assistive activation has detail=0; compatibility mouse/touch
      // clicks have detail>0 and must not steer a second time after pointerdown.
      button.addEventListener('click',function(e){if(e.detail===0)steer(e);});
    });
    document.addEventListener('keydown',onKey);
    initSwipe();
    document.addEventListener('visibilitychange',onVisibility);
    window.addEventListener('pagehide',suspend);
    window.addEventListener('pageshow',wake);
    window.addEventListener('blur',function(){if(view.mode==='playing'&&!view.paused)setPause(true);clearInput();});
    window.addEventListener('resize',function(){clearInput();invalidate();});
    window.addEventListener('orientationchange',function(){clearInput();invalidate();});
    showMenu();invalidate();
    observeHost();
    // Service worker optional: WebKitGTK deployments without SW still run offline
    // as a locally served, network-independent application.
    if ('serviceWorker' in navigator && window.Capacitor) {
      // APK assets are already offline. Never let an old worker mask an update.
      navigator.serviceWorker.getRegistrations().then(function(regs){regs.forEach(function(r){r.unregister();});}).catch(function(){});
    } else if ('serviceWorker' in navigator && window.isSecureContext) {
      navigator.serviceWorker.register('./sw.js',{scope:'./'}).catch(function(){ /* optional */ });
    }
  }
  // Shared lifecycle contract; Android wires native callbacks without patching
  // game logic. Also useful to a Nuxel host which needs explicit suspension.
  window.SnekByteUI = Object.freeze({ requestPause:suspend, invalidate:wake,
    isAtRoot:function(){return !view.dialog&&view.mode==='menu';}, handleBack:handleBack });
  if(debug) {
    if(window.PerformanceObserver) {
      try { new PerformanceObserver(function(list){list.getEntries().forEach(function(e){bounded(longTasks,{at:e.startTime,ms:e.duration},60);});}).observe({entryTypes:['longtask']}); } catch(e) {}
    }
    window.SnekByteDebug=Object.freeze({snapshot:function(){return {
      game:view.game?E.snapshot(view.game):null,mode:view.mode,paused:view.paused,
      queue:queue.size(),period:tickMs(),rafPending:view.raf!==null,settings:Object.assign({},playingSettings()),
      traces:traces.map(function(t){return Object.assign({},t);}),frameWorkMs:frames.slice(),
      droppedMs:droppedMs,longTasks:longTasks.slice()
    };}});
  }
  function ready() {
    if(window.SnekBytePersistence) window.SnekBytePersistence.ready.then(install);
    else install();
  }
  if (document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready);
  else ready();
}());
