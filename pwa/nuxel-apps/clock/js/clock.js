// Nuxel Clock (mission area 30; ties into time/RTC - mission area 5)
//
// Honesty rules implemented here:
//   * The displayed time is always the kernel clock (Date.now()).  If the
//     time/RTC service reports a source through the bridge or the launcher host
//     we show it; if nothing answers we say "not reported" instead of guessing.
//   * Alarms ring while Clock is open.  A wake-from-suspend alarm needs an RTC
//     alarm that this platform has not provisioned, so the UI says exactly that
//     and never claims a background alarm it does not have.
(function () {
  'use strict';

  var K_ALARMS = 'nuxel-clock-alarms';
  var K_CITIES = 'nuxel-clock-cities';
  var K_STATE = 'nuxel-clock-state';

  var el = {};
  ['source-badge','frac-time','frac-date','epoch','offset','source-detail','refresh-source',
   'cities','city','utc-offset','add-city','alarm-time','alarm-label','add-alarm','alarm-repeat',
   'alarm-capability','alarms','ring-status','snooze','stop-ring','sw-time','sw-state','sw-start',
   'sw-lap','sw-reset','laps','tm-time','tm-state','tm-min','tm-sec','tm-set','tm-start','tm-pause',
   'tm-reset','toast'].forEach(function (id) {
    el[id.replace(/-([a-z])/g, function (m, c) { return c.toUpperCase(); })] = document.getElementById(id);
  });

  /* ---------- host + bridge ---------- */
  function host() {
    if (window.NuxelHost && window.NuxelHost.available) return window.NuxelHost;
    try { if (window.parent && window.parent !== window && window.parent.NuxelHost) return window.parent.NuxelHost; } catch (e) { /* cross-frame denied */ }
    return null;
  }
  function hostRead(name) {
    var h = host();
    if (!h || !h.available) return Promise.resolve({ ok: false, offline: true });
    return h.statusRead(name);
  }
  function bridgeCall(ns, verb, params) {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
      return window.NuxelBridge.call(ns, verb, params);
    }
    return Promise.resolve({ success: false, offline: true });
  }

  /* ---------- storage ---------- */
  function load(key, dflt) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : dflt; }
    catch (e) { return dflt; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
  }

  function toast(msg) {
    el.toast.textContent = msg;
    el.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.toast.classList.add('hidden'); }, 2400);
  }

  /* ---------- tone (WebAudio, generated in-page - no sound file) ---------- */
  var audioCtx = null;
  function beep(times) {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return false;
      if (!audioCtx) audioCtx = new Ctx();
      var now = audioCtx.currentTime;
      for (var i = 0; i < (times || 1); i++) {
        var osc = audioCtx.createOscillator();
        var gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(0.0001, now + i * 0.45);
        gain.gain.exponentialRampToValueAtTime(0.22, now + i * 0.45 + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.45 + 0.4);
        osc.connect(gain).connect(audioCtx.destination);
        osc.start(now + i * 0.45);
        osc.stop(now + i * 0.45 + 0.42);
      }
      return true;
    } catch (e) { return false; }
  }

  /* ---------- clock face ---------- */
  function pad(n, w) { return String(n).padStart(w || 2, '0'); }
  function fmtOffset(minutes) {
    var sign = minutes < 0 ? '-' : '+';
    var m = Math.abs(minutes);
    return 'UTC' + sign + pad(Math.floor(m / 60)) + ':' + pad(m % 60);
  }
  function tick() {
    var d = new Date();
    el.fracTime.textContent = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    el.fracDate.textContent = d.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    el.epoch.textContent = String(Math.floor(d.getTime() / 1000));
    el.offset.textContent = fmtOffset(-d.getTimezoneOffset());
    renderCities(d);
    checkAlarms(d);
  }

  /* ---------- world clocks ---------- */
  var cities = load(K_CITIES, [
    { label: 'UTC', offset: 0 },
    { label: 'Nuxel HQ (Amsterdam)', offset: 120 }
  ]);
  function parseOffsetMinutes(text) {
    var m = /^([+-]?)(\d{1,2}):?(\d{2})?$/.exec(String(text).trim());
    if (!m) return null;
    var sign = m[1] === '-' ? -1 : 1;
    return sign * (Number(m[2]) * 60 + Number(m[3] || 0));
  }
  function renderCities(now) {
    var d = now || new Date();
    el.cities.innerHTML = '';
    cities.forEach(function (c, i) {
      var utcMs = d.getTime() + d.getTimezoneOffset() * 60000 + c.offset * 60000;
      var ld = new Date(utcMs);
      var li = document.createElement('li');
      var left = document.createElement('div');
      var t = document.createElement('div');
      t.className = 'mono';
      t.textContent = pad(ld.getHours()) + ':' + pad(ld.getMinutes()) + ':' + pad(ld.getSeconds());
      var sub = document.createElement('div');
      sub.className = 'li-sub';
      sub.textContent = fmtOffset(c.offset) + (ld.getHours() >= 6 && ld.getHours() < 20 ? '  ☀ day' : '  ☾ night');
      left.appendChild(t); left.appendChild(sub);
      var nameEl = document.createElement('div');
      nameEl.textContent = c.label;
      var actions = document.createElement('div');
      actions.className = 'li-actions';
      var del = document.createElement('button');
      del.textContent = 'Remove';
      del.addEventListener('click', function () {
        cities.splice(i, 1); save(K_CITIES, cities); renderCities();
      });
      actions.appendChild(del);
      li.appendChild(nameEl); li.appendChild(left); li.appendChild(actions);
      el.cities.appendChild(li);
    });
    if (!cities.length) {
      var empty = document.createElement('li');
      empty.textContent = 'No world clocks. Add a city label and its UTC offset.';
      el.cities.appendChild(empty);
    }
  }
  el.addCity.addEventListener('click', function () {
    var label = (el.city.value || '').trim();
    var off = parseOffsetMinutes(el['utcOffset'].value);
    if (!label) { toast('Give the city a label'); return; }
    if (off === null) { toast('UTC offset must look like +02:00'); return; }
    cities.push({ label: label, offset: off });
    save(K_CITIES, cities);
    el.city.value = '';
    renderCities();
  });

  /* ---------- time source reporting ---------- */
  function refreshSource() {
    el.sourceDetail.textContent = 'checking…';
    Promise.all([
      hostRead('time'),
      hostRead('rtc'),
      bridgeCall('clock', 'status', {})
    ]).then(function (res) {
      var lines = [];
      var hostTime = res[0], hostRtc = res[1], br = res[2];
      if (hostTime && hostTime.ok && hostTime.text) {
        lines.push('launcher host (status.read time): ' + String(hostTime.text).trim());
        el.sourceBadge.textContent = 'clock source: kernel';
        el.sourceBadge.classList.remove('warn');
      } else {
        lines.push('launcher host status.read time: not reported');
      }
      if (hostRtc && hostRtc.ok && hostRtc.text) lines.push('launcher host RTC: ' + String(hostRtc.text).trim());
      else lines.push('launcher host RTC: not reported');
      if (br && (br.source || br.time_source || br.status)) {
        lines.push('nuxel-bridge clock.status: ' + JSON.stringify(br).slice(0, 300));
      } else {
        lines.push('nuxel-bridge clock.status: unavailable (no bridge in this session)');
        el.sourceBadge.textContent = 'clock source: local only';
        el.sourceBadge.classList.add('warn');
      }
      lines.push('');
      lines.push('Device clock (Date) : ' + new Date().toISOString());
      lines.push('Timezone            : ' + (Intl.DateTimeFormat().resolvedOptions().timeZone || 'unset') + ' (' + fmtOffset(-new Date().getTimezoneOffset()) + ')');
      lines.push('Battery-backed RTC wake alarm: not provisioned on this platform - alarms ring while Clock runs.');
      el.sourceDetail.textContent = lines.join('\n');
    });
  }
  el.refreshSource.addEventListener('click', refreshSource);

  /* ---------- alarms ---------- */
  var alarms = load(K_ALARMS, []);
  var ringing = null;
  var snoozeUntil = 0;
  var lastRingKey = '';

  function renderAlarms() {
    el.alarms.innerHTML = '';
    if (!alarms.length) {
      var li0 = document.createElement('li');
      li0.textContent = 'No alarms set.';
      el.alarms.appendChild(li0);
      return;
    }
    alarms.forEach(function (a, i) {
      var li = document.createElement('li');
      if (!a.enabled) li.classList.add('off');
      if (ringing && ringing.id === a.id) li.classList.add('ringing');
      var left = document.createElement('div');
      var t = document.createElement('div');
      t.className = 'mono';
      t.textContent = a.time;
      var sub = document.createElement('div');
      sub.className = 'li-sub';
      sub.textContent = (a.label || 'Alarm') + (a.repeat ? '  ·  daily' : '  ·  once');
      left.appendChild(t); left.appendChild(sub);
      var actions = document.createElement('div');
      actions.className = 'li-actions';
      var toggle = document.createElement('button');
      toggle.textContent = a.enabled ? 'On' : 'Off';
      toggle.addEventListener('click', function () {
        alarms[i].enabled = !alarms[i].enabled;
        save(K_ALARMS, alarms); renderAlarms();
      });
      var del = document.createElement('button');
      del.textContent = 'Delete';
      del.addEventListener('click', function () {
        alarms.splice(i, 1); save(K_ALARMS, alarms); renderAlarms();
      });
      actions.appendChild(toggle); actions.appendChild(del);
      li.appendChild(left); li.appendChild(actions);
      el.alarms.appendChild(li);
    });
  }

  el.addAlarm.addEventListener('click', function () {
    var t = el.alarmTime.value || '07:00';
    if (!/^\d{2}:\d{2}$/.test(t)) { toast('Pick a valid time'); return; }
    alarms.push({
      id: 'alarm-' + Date.now(),
      time: t,
      label: (el.alarmLabel.value || '').trim() || 'Alarm',
      repeat: !!el.alarmRepeat.checked,
      enabled: true
    });
    alarms.sort(function (a, b) { return a.time.localeCompare(b.time); });
    save(K_ALARMS, alarms);
    el.alarmLabel.value = '';
    el.alarmRepeat.checked = false;
    renderAlarms();
    toast('Alarm set for ' + t + ' (rings while Clock is open)');
  });

  function checkAlarms(now) {
    if (ringing) return;
    if (snoozeUntil && now.getTime() < snoozeUntil) return;
    for (var i = 0; i < alarms.length; i++) {
      var a = alarms[i];
      if (!a.enabled) continue;
      var key = a.id + '@' + now.toDateString() + ' ' + a.time;
      if (key === lastRingKey) continue;
      if (a.time === pad(now.getHours()) + ':' + pad(now.getMinutes()) && now.getSeconds() < 30) {
        lastRingKey = key;
        startRinging(a);
        return;
      }
    }
  }
  function startRinging(a) {
    ringing = a;
    el.ringStatus.textContent = 'Ringing: ' + a.time + ' — ' + (a.label || 'Alarm');
    el.snooze.disabled = false;
    el.stopRing.disabled = false;
    var ok = beep(a.repeat ? 3 : 1);
    if (!ok) toast('Alarm ringing, but no audio device is available for the tone');
    if (window.NuxelBridge && window.NuxelBridge.sendNotification) {
      window.NuxelBridge.sendNotification('Alarm ' + a.time, a.label || 'Nuxel Clock').catch(function () { /* notifications are best-effort */ });
    }
    if (!a.repeat) {
      a.enabled = false;
      save(K_ALARMS, alarms);
    }
    renderAlarms();
  }
  el.snooze.addEventListener('click', function () {
    snoozeUntil = Date.now() + 5 * 60000;
    ringing = null;
    el.ringStatus.textContent = 'Snoozed until ' + new Date(snoozeUntil).toLocaleTimeString();
    el.snooze.disabled = true; el.stopRing.disabled = true;
    toast('Snoozed for 5 minutes');
    renderAlarms();
  });
  el.stopRing.addEventListener('click', function () {
    ringing = null; snoozeUntil = 0;
    el.ringStatus.textContent = 'Stopped.';
    el.snooze.disabled = true; el.stopRing.disabled = true;
    renderAlarms();
  });

  /* ---------- stopwatch (survives a reload; monotonic via performance.now) ---------- */
  var sw = load(K_STATE, { swRunning: false, swStartedAt: 0, swAccum: 0, laps: [] });
  function swElapsed() {
    return sw.swAccum + (sw.swRunning ? (performance.now() - sw.swStartedAt) : 0);
  }
  function fmtSw(ms) {
    var h = Math.floor(ms / 3600000), m = Math.floor(ms % 3600000 / 60000),
        s = Math.floor(ms % 60000 / 1000), cs = Math.floor(ms % 1000 / 10);
    return pad(h) + ':' + pad(m) + ':' + pad(s) + '.' + pad(cs);
  }
  function paintSw() {
    el.swTime.textContent = fmtSw(swElapsed());
    el.swState.textContent = sw.swRunning ? 'Running' : (swElapsed() > 0 ? 'Paused' : 'Idle');
    el.swStart.textContent = sw.swRunning ? 'Pause' : 'Start';
  }
  function paintLaps() {
    el.laps.innerHTML = '';
    var prev = 0;
    sw.laps.forEach(function (lapMs, i) {
      var li = document.createElement('li');
      var n = document.createElement('span'); n.textContent = 'Lap ' + (i + 1);
      var d = document.createElement('span'); d.className = 'mono'; d.textContent = '+' + fmtSw(lapMs - prev);
      var t = document.createElement('span'); t.className = 'mono'; t.textContent = fmtSw(lapMs);
      li.appendChild(n); li.appendChild(d); li.appendChild(t);
      el.laps.appendChild(li);
      prev = lapMs;
    });
  }
  el.swStart.addEventListener('click', function () {
    if (sw.swRunning) { sw.swAccum = swElapsed(); sw.swRunning = false; }
    else { sw.swStartedAt = performance.now(); sw.swRunning = true; }
    save(K_STATE, sw); paintSw();
  });
  el.swLap.addEventListener('click', function () {
    if (swElapsed() === 0) return;
    sw.laps.push(swElapsed()); save(K_STATE, sw); paintLaps();
  });
  el.swReset.addEventListener('click', function () {
    sw = { swRunning: false, swStartedAt: 0, swAccum: 0, laps: [] };
    save(K_STATE, sw); paintSw(); paintLaps();
  });
  paintSw(); paintLaps();

  /* ---------- timer ---------- */
  var timer = { remaining: 300000, running: false, endsAt: 0, setMs: 300000 };
  function paintTimer() {
    el.tmTime.textContent = fmtSw(Math.max(0, timer.remaining));
    el.tmState.textContent = timer.running ? 'Running — ends ' + new Date(timer.endsAt).toLocaleTimeString()
      : (timer.remaining === 0 ? 'Finished' : 'Ready');
  }
  function setTimerFromInputs() {
    var m = Math.max(0, parseInt(el.tmMin.value, 10) || 0);
    var s = Math.min(59, Math.max(0, parseInt(el.tmSec.value, 10) || 0));
    timer.setMs = (m * 60 + s) * 1000;
    timer.remaining = timer.setMs;
    timer.running = false;
    paintTimer();
  }
  el.tmSet.addEventListener('click', setTimerFromInputs);
  document.querySelectorAll('.preset').forEach(function (b) {
    b.addEventListener('click', function () {
      var sec = Number(b.dataset.sec);
      timer.setMs = sec * 1000; timer.remaining = timer.setMs; timer.running = false;
      el.tmMin.value = String(Math.floor(sec / 60)); el.tmSec.value = String(sec % 60);
      paintTimer();
    });
  });
  el.tmStart.addEventListener('click', function () {
    if (timer.running) return;
    if (timer.remaining <= 0) setTimerFromInputs();
    timer.endsAt = Date.now() + timer.remaining;
    timer.running = true;
    paintTimer();
  });
  el.tmPause.addEventListener('click', function () {
    if (!timer.running) return;
    timer.remaining = Math.max(0, timer.endsAt - Date.now());
    timer.running = false;
    paintTimer();
  });
  el.tmReset.addEventListener('click', function () {
    timer.running = false; timer.remaining = timer.setMs; paintTimer();
  });
  paintTimer();

  /* ---------- main loop ---------- */
  tick();
  setInterval(tick, 250);
  setInterval(function () {
    paintSw();
    if (timer.running) {
      timer.remaining = Math.max(0, timer.endsAt - Date.now());
      if (timer.remaining === 0) {
        timer.running = false;
        var ok = beep(3);
        el.tmState.textContent = ok ? 'Finished' : 'Finished (no audio device)';
        if (window.NuxelBridge && window.NuxelBridge.sendNotification) {
          window.NuxelBridge.sendNotification('Timer finished', 'Nuxel Clock').catch(function () { /* best effort */ });
        }
      }
      paintTimer();
    }
  }, 100);

  refreshSource();
  renderAlarms();

  hostRead('alarm').then(function (r) {
    if (r && r.ok) el.alarmCapability.textContent = 'Wake alarm service: ' + String(r.text || '').trim();
    else el.alarmCapability.textContent =
      'No RTC wake-alarm service answered: alarms ring while Clock is open. ' +
      'Wake-from-suspend alarms are recorded as NEEDS_OWNER_TEST / blocked on the time-RTC service.';
  });

  // headless smoke-test hook
  window.nuxelClock = { tick: tick, alarms: alarms, beep: beep, fmtSw: fmtSw, fmtOffset: fmtOffset, parseOffsetMinutes: parseOffsetMinutes };
})();
