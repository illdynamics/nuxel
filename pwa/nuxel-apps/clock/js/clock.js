/* Nuxel Clock — scheduler client (PWNAGE-84000).
 *
 * The page renders state; it does not own alarm/timer execution.  Every
 * mutation goes to nuxel-clockd through the bridge and only the daemon's
 * returned authoritative snapshot changes the UI.  A bridge outage is shown as
 * such and never converted into a fake saved/ringing state.
 */
(function () {
  'use strict';
  var K_CITIES = 'nuxel-clock-cities';
  var K_STATE = 'nuxel-clock-state';
  var K_ALARMS_CACHE = 'nuxel-clock-alarms';
  var K_SETTINGS_CACHE = 'nuxel-clock-settings';
  var el = {};
  var ids = ['source-badge','frac-time','frac-date','epoch','offset','source-detail','refresh-source',
    'cities','city','utc-offset','add-city','alarm-time','alarm-label','add-alarm','alarm-repeat',
    'alarm-capability','alarms','ring-status','ring-list','snooze','stop-ring','sw-time','sw-state',
    'sw-start','sw-lap','sw-reset','laps','tm-time','tm-state','tm-min','tm-sec','tm-set','tm-start',
    'tm-pause','tm-reset','tm-stop','toast','alarm-vibrate','snooze-minutes','snooze-enabled',
    'save-snooze'];
  ids.forEach(function (id) {
    el[id.replace(/-([a-z])/g, function (_, c) { return c.toUpperCase(); })] = document.getElementById(id);
  });

  function pad(n) { return String(n).padStart(2, '0'); }
  function load(key, dflt) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : dflt; }
    catch (e) { return dflt; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
  }
  function toast(msg) {
    if (!el.toast) return;
    el.toast.textContent = msg;
    el.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.toast.classList.add('hidden'); }, 2600);
  }
  function bridgeCall(ns, verb, params) {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
      return Promise.resolve(window.NuxelBridge.call(ns, verb, params || {}))
        .catch(function (e) { return { success: false, error: String(e && e.message || e) }; });
    }
    return Promise.resolve({ success: false, offline: true, error: 'Nuxel bridge unavailable' });
  }
  function hostRead(name) {
    var h = window.NuxelHost || (window.parent && window.parent.NuxelHost);
    if (!h || !h.available) return Promise.resolve({ ok: false, offline: true });
    return h.statusRead(name);
  }
  function normaliseClockTime(value) {
    var v = String(value == null ? '' : value).trim();
    var digits = v.replace(/[^0-9]/g, '');
    if (digits.length === 3) digits = '0' + digits;
    if (digits.length !== 4) return null;
    var h = Number(digits.slice(0, 2)), m = Number(digits.slice(2));
    if (h > 23 || m > 59) return null;
    return pad(h) + ':' + pad(m);
  }
  function fmtOffset(minutes) {
    var sign = minutes < 0 ? '-' : '+', m = Math.abs(minutes);
    return 'UTC' + sign + pad(Math.floor(m / 60)) + ':' + pad(m % 60);
  }
  function fmtSw(ms) {
    ms = Math.max(0, Number(ms) || 0);
    var h = Math.floor(ms / 3600000), m = Math.floor(ms % 3600000 / 60000),
      s = Math.floor(ms % 60000 / 1000), cs = Math.floor(ms % 1000 / 10);
    return pad(h) + ':' + pad(m) + ':' + pad(s) + '.' + pad(cs);
  }
  /* Timer countdown format: MM:SS below one hour, H:MM:SS at one hour or more.
     Sub-minute timers must never render as 0:00. */
  function fmtTimer(ms) {
    var total = Math.max(0, Math.floor(Number(ms) || 0) / 1000);
    var h = Math.floor(total / 3600), m = Math.floor(total % 3600 / 60), s = total % 60;
    if (h > 0) return pad(h) + ':' + pad(m) + ':' + pad(s);
    return pad(m) + ':' + pad(s);
  }

  /* ---------- tabs ---------- */
  document.querySelectorAll('.tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.tab').forEach(function (t) { t.classList.toggle('active', t === tab); });
      document.querySelectorAll('.panel').forEach(function (p) { p.classList.toggle('active', p.id === 'tab-' + tab.dataset.tab); });
    });
  });

  /* ---------- world clocks ---------- */
  var cities = load(K_CITIES, [
    { label: 'UTC', offset: 0 },
    { label: 'Nuxel HQ (Amsterdam)', offset: 120 }
  ]);
  function parseOffsetMinutes(text) {
    var m = /^([+-]?)(\d{1,2}):?(\d{2})?$/.exec(String(text).trim());
    if (!m) return null;
    return (m[1] === '-' ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3] || 0));
  }
  function renderCities(now) {
    if (!el.cities) return;
    var d = now || new Date();
    el.cities.textContent = '';
    cities.forEach(function (c) {
      var utcMs = d.getTime() + d.getTimezoneOffset() * 60000 + c.offset * 60000;
      var ld = new Date(utcMs);
      var li = document.createElement('li');
      var name = document.createElement('div'); name.textContent = c.label;
      var time = document.createElement('div'); time.className = 'mono';
      time.textContent = pad(ld.getHours()) + ':' + pad(ld.getMinutes()) + ':' + pad(ld.getSeconds());
      var sub = document.createElement('div'); sub.className = 'li-sub';
      sub.textContent = fmtOffset(c.offset) + (ld.getHours() >= 6 && ld.getHours() < 20 ? ' · day' : ' · night');
      var actions = document.createElement('div'); actions.className = 'li-actions';
      var del = document.createElement('button'); del.textContent = 'Remove';
      del.addEventListener('click', function () {
        cities.splice(cities.indexOf(c), 1); save(K_CITIES, cities); renderCities();
      });
      actions.appendChild(del);
      li.appendChild(name); li.appendChild(time); li.appendChild(sub); li.appendChild(actions);
      el.cities.appendChild(li);
    });
  }
  if (el.addCity) el.addCity.addEventListener('click', function () {
    var label = (el.city.value || '').trim(), off = parseOffsetMinutes(el.utcOffset.value);
    if (!label) { toast('Give the city a label'); return; }
    if (off === null) { toast('UTC offset must look like +02:00'); return; }
    cities.push({ label: label, offset: off });
    save(K_CITIES, cities); el.city.value = ''; renderCities();
  });

  /* ---------- clock source / face ---------- */
  function tick() {
    var d = new Date();
    if (el.fracTime) el.fracTime.textContent = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    if (el.fracDate) el.fracDate.textContent = d.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    if (el.epoch) el.epoch.textContent = String(Math.floor(d.getTime() / 1000));
    if (el.offset) el.offset.textContent = fmtOffset(-d.getTimezoneOffset());
    renderCities(d);
    paintStopwatch();
    paintTimer();
  }
  function refreshSource() {
    if (!el.sourceDetail) return;
    el.sourceDetail.textContent = 'checking…';
    Promise.all([hostRead('time'), hostRead('rtc'), bridgeCall('clock', 'status', {})]).then(function (res) {
      var lines = [], hostTime = res[0], hostRtc = res[1], br = res[2];
      if (hostTime && hostTime.ok && hostTime.text) {
        lines.push('launcher host (status.read time): ' + String(hostTime.text).trim());
        el.sourceBadge.textContent = 'clock source: kernel';
        el.sourceBadge.classList.remove('warn');
      } else lines.push('launcher host status.read time: not reported');
      if (hostRtc && hostRtc.ok && hostRtc.text) lines.push('launcher host RTC: ' + String(hostRtc.text).trim());
      else lines.push('launcher host RTC: not reported');
      if (br && br.success !== false) {
        var caps = br.capabilities || {};
        lines.push('scheduler      : nuxel-clockd ready, revision ' + (br.revision == null ? '?' : br.revision));
        lines.push('active events  : ' + ((br.active_occurrences || []).length));
        lines.push('next event     : ' + (br.next ? (br.next.kind + ' ' + new Date(br.next.at).toLocaleString()) : 'none'));
        var rtc = caps.rtc_wakealarm || {};
        lines.push('RTC wake node  : ' + (rtc.present ? (rtc.path + (rtc.writable ? ' (writable)' : ' (read-only)')) : 'not present'));
        lines.push('suspend wake   : ' + (caps.rtc_wake_from_suspend_verified ? 'verified' : 'not verified on this kernel'));
      } else {
        lines.push('scheduler      : unavailable (' + ((br && (br.detail || br.error)) || 'no bridge') + ')');
        el.sourceBadge.textContent = 'clock source: local only';
        el.sourceBadge.classList.add('warn');
      }
      lines.push('');
      lines.push('Device clock (Date) : ' + new Date().toISOString());
      lines.push('Timezone            : ' + (Intl.DateTimeFormat().resolvedOptions().timeZone || 'unset') + ' (' + fmtOffset(-new Date().getTimezoneOffset()) + ')');
      el.sourceDetail.textContent = lines.join('\n');
    });
  }
  if (el.refreshSource) el.refreshSource.addEventListener('click', refreshSource);

  /* ---------- scheduler state ---------- */
  var scheduler = { alarms: [], timer: null, occurrences: [], settings: { snooze_minutes: 9, snooze_enabled: true } };
  var pollBusy = false;
  function applyState(doc) {
    if (!doc || doc.success === false) return false;
    scheduler = {
      alarms: Array.isArray(doc.alarms) ? doc.alarms : [],
      timer: doc.timer || null,
      occurrences: Array.isArray(doc.occurrences) ? doc.occurrences : [],
      settings: doc.settings || scheduler.settings || {},
      capabilities: doc.capabilities || scheduler.capabilities || {},
      revision: doc.revision
    };
    save(K_ALARMS_CACHE, scheduler.alarms);
    save(K_SETTINGS_CACHE, scheduler.settings);
    renderAlarms();
    renderRinging();
    paintTimer();
    paintAlarmSettings();
    paintCapability();
    return true;
  }
  function refreshScheduler() {
    if (pollBusy) return Promise.resolve(null);
    pollBusy = true;
    return bridgeCall('clock', 'status', {}).then(function (doc) {
      pollBusy = false;
      if (!applyState(doc)) {
        scheduler.alarms = load(K_ALARMS_CACHE, []);
        scheduler.settings = load(K_SETTINGS_CACHE, scheduler.settings);
        renderAlarms();
        renderRinging();
        if (el.alarmCapability) el.alarmCapability.textContent = 'Clock scheduler unavailable: ' + ((doc && (doc.detail || doc.error)) || 'no bridge');
      }
      return doc;
    }, function (e) { pollBusy = false; return { success: false, error: String(e) }; });
  }
  function paintAlarmSettings() {
    var s = scheduler.settings || {};
    if (el.snoozeMinutes) el.snoozeMinutes.value = String(s.snooze_minutes || 9);
    if (el.snoozeEnabled) el.snoozeEnabled.checked = s.snooze_enabled !== false;
    if (el.snooze) el.snooze.textContent = 'Snooze ' + (s.snooze_minutes || 9) + ' minutes';
    if (el.alarmVibrate) el.alarmVibrate.checked = s.vibrate !== false;
  }
  function paintCapability() {
    if (!el.alarmCapability) return;
    var caps = scheduler.capabilities || {};
    var rtc = caps.rtc_wakealarm || {};
    el.alarmCapability.textContent = 'nuxel-clockd owns alarms and timers independently of this page. ' +
      'Display-off while the OS is awake is supported. RTC wake node: ' +
      (rtc.present ? rtc.path + (rtc.writable ? ' (writable)' : ' (read-only)') : 'not present') +
      '; wake-from-suspend is not claimed until a physical resume test proves it.';
  }
  function occurrenceById(id) {
    return (scheduler.occurrences || []).find(function (o) { return o && o.id === id; });
  }
  function renderRinging() {
    var ringing = (scheduler.occurrences || []).filter(function (o) { return o && o.state === 'ringing'; });
    if (el.ringList) {
      el.ringList.textContent = '';
      ringing.forEach(function (occ) {
        var li = document.createElement('li');
        li.className = 'ringing';
        var text = document.createElement('div');
        var title = document.createElement('div');
        title.className = 'mono';
        title.textContent = occ.kind === 'timer' ? 'TIMER' : 'ALARM';
        var sub = document.createElement('div');
        sub.className = 'li-sub';
        sub.textContent = (occ.label || '') + (occ.state === 'ringing' ? ' · ringing' : '');
        text.appendChild(title); text.appendChild(sub);
        var actions = document.createElement('div'); actions.className = 'li-actions';
        var stop = document.createElement('button'); stop.textContent = 'Stop';
        stop.addEventListener('click', function () { stopOccurrence(occ); });
        actions.appendChild(stop);
        if (occ.kind !== 'timer' && scheduler.settings.snooze_enabled !== false) {
          var snooze = document.createElement('button');
          snooze.textContent = 'Snooze ' + (scheduler.settings.snooze_minutes || 9);
          snooze.addEventListener('click', function () { snoozeOccurrence(occ); });
          actions.appendChild(snooze);
        }
        li.appendChild(text); li.appendChild(actions);
        el.ringList.appendChild(li);
      });
    }
    if (el.ringStatus) {
      el.ringStatus.textContent = ringing.length
        ? ringing.length + ' event(s) ringing. Stop affects only the selected occurrence.'
        : 'Nothing ringing.';
    }
    var firstAlarm = ringing.find(function (o) { return o && o.kind !== 'timer'; });
    if (el.stopRing) el.stopRing.disabled = !firstAlarm;
    if (el.snooze) {
      el.snooze.disabled = !firstAlarm || scheduler.settings.snooze_enabled === false;
      el.snooze.style.display = scheduler.settings.snooze_enabled === false ? 'none' : '';
    }
  }
  function stopOccurrence(occ) {
    bridgeCall('clock', 'dismiss-occurrence', { id: occ.id }).then(function (r) {
      if (r && r.success !== false) { toast('Stopped'); applyState(r.state || {}); }
      else toast('Stop failed: ' + ((r && (r.detail || r.error)) || 'unknown error'));
      refreshScheduler();
    });
  }
  function snoozeOccurrence(occ) {
    if (scheduler.settings.snooze_enabled === false) { toast('Snooze is disabled'); return; }
    bridgeCall('clock', 'snooze-occurrence', { id: occ.id }).then(function (r) {
      if (r && r.success !== false) { toast('Snoozed'); applyState(r.state || {}); }
      else toast('Snooze failed: ' + ((r && (r.detail || r.error)) || 'unknown error'));
      refreshScheduler();
    });
  }
  if (el.stopRing) el.stopRing.addEventListener('click', function () {
    var occ = (scheduler.occurrences || []).find(function (o) { return o && o.kind !== 'timer' && o.state === 'ringing'; });
    if (occ) stopOccurrence(occ);
  });
  if (el.snooze) el.snooze.addEventListener('click', function () {
    var occ = (scheduler.occurrences || []).find(function (o) { return o && o.kind !== 'timer' && o.state === 'ringing'; });
    if (occ) snoozeOccurrence(occ);
  });
  if (el.saveSnooze) el.saveSnooze.addEventListener('click', function () {
    var mins = Math.max(1, Math.min(60, parseInt(el.snoozeMinutes.value, 10) || 9));
    bridgeCall('clock', 'set-settings', { snooze_minutes: mins, snooze_enabled: el.snoozeEnabled.checked }).then(function (r) {
      if (r && r.success !== false) { toast('Snooze preference saved'); applyState(r.state || {}); }
      else toast('Save failed: ' + ((r && (r.detail || r.error)) || 'unknown error'));
    });
  });
  if (el.alarmVibrate) el.alarmVibrate.addEventListener('change', function () {
    bridgeCall('clock', 'set-settings', { vibrate: el.alarmVibrate.checked }).then(refreshScheduler);
  });

  /* ---------- alarms ---------- */
  function renderAlarms() {
    if (!el.alarms) return;
    el.alarms.textContent = '';
    if (!scheduler.alarms.length) {
      var empty = document.createElement('li');
      empty.textContent = 'No alarms set.';
      el.alarms.appendChild(empty);
      return;
    }
    scheduler.alarms.forEach(function (a) {
      var li = document.createElement('li');
      if (!a.enabled) li.classList.add('off');
      var text = document.createElement('div');
      var time = document.createElement('div'); time.className = 'mono'; time.textContent = a.time;
      var sub = document.createElement('div'); sub.className = 'li-sub';
      sub.textContent = (a.label || 'Alarm') + (a.repeat ? ' · daily' : ' · once') +
        (a.snooze_minutes ? ' · snooze ' + a.snooze_minutes + 'm' : '');
      text.appendChild(time); text.appendChild(sub);
      var actions = document.createElement('div'); actions.className = 'li-actions';
      var toggle = document.createElement('button'); toggle.textContent = a.enabled ? 'On' : 'Off';
      toggle.addEventListener('click', function () {
        bridgeCall('clock', 'enable-alarm', { id: a.id, enabled: !a.enabled }).then(function (r) {
          if (r && r.success !== false) applyState(r.state || {}); else toast('Update failed');
        });
      });
      var del = document.createElement('button'); del.textContent = 'Delete';
      del.addEventListener('click', function () {
        bridgeCall('clock', 'delete-alarm', { id: a.id }).then(function (r) {
          if (r && r.success !== false) applyState(r.state || {}); else toast('Delete failed');
        });
      });
      actions.appendChild(toggle); actions.appendChild(del);
      li.appendChild(text); li.appendChild(actions);
      el.alarms.appendChild(li);
    });
  }
  if (el.addAlarm) el.addAlarm.addEventListener('click', function () {
    var t = normaliseClockTime(el.alarmTime.value || '07:00');
    if (!t) { toast('Enter a time as HH:MM (24-hour)'); return; }
    el.alarmTime.value = t;
    var alarm = {
      id: 'alarm-' + Date.now(), time: t,
      label: (el.alarmLabel.value || '').trim() || 'Alarm',
      repeat: !!el.alarmRepeat.checked, enabled: true,
      vibrate: el.alarmVibrate ? el.alarmVibrate.checked : true
    };
    bridgeCall('clock', 'create-alarm', alarm).then(function (r) {
      if (r && r.success !== false) {
        applyState(r.state || {});
        el.alarmLabel.value = ''; el.alarmRepeat.checked = false;
        toast('Alarm set for ' + t);
      } else {
        toast('Alarm was not scheduled: ' + ((r && (r.detail || r.error)) || 'scheduler unavailable'));
      }
    });
  });

  /* ---------- stopwatch (page-local by design) ---------- */
  var sw = load(K_STATE, { swRunning: false, swStartedAt: 0, swAccum: 0, laps: [] });
  function swElapsed() { return sw.swAccum + (sw.swRunning ? (performance.now() - sw.swStartedAt) : 0); }
  function paintStopwatch() {
    if (!el.swTime) return;
    el.swTime.textContent = fmtSw(swElapsed());
    el.swState.textContent = sw.swRunning ? 'Running' : (swElapsed() > 0 ? 'Paused' : 'Idle');
    el.swStart.textContent = sw.swRunning ? 'Pause' : 'Start';
  }
  function paintLaps() {
    if (!el.laps) return;
    el.laps.textContent = '';
    var prev = 0;
    sw.laps.forEach(function (lapMs, i) {
      var li = document.createElement('li');
      var n = document.createElement('span'); n.textContent = 'Lap ' + (i + 1);
      var d = document.createElement('span'); d.className = 'mono'; d.textContent = '+' + fmtSw(lapMs - prev);
      var t = document.createElement('span'); t.className = 'mono'; t.textContent = fmtSw(lapMs);
      li.appendChild(n); li.appendChild(d); li.appendChild(t); el.laps.appendChild(li); prev = lapMs;
    });
  }
  if (el.swStart) el.swStart.addEventListener('click', function () {
    if (sw.swRunning) { sw.swAccum = swElapsed(); sw.swRunning = false; }
    else { sw.swStartedAt = performance.now(); sw.swRunning = true; }
    save(K_STATE, sw); paintStopwatch();
  });
  if (el.swLap) el.swLap.addEventListener('click', function () {
    if (swElapsed() === 0) return;
    sw.laps.push(swElapsed()); save(K_STATE, sw); paintLaps();
  });
  if (el.swReset) el.swReset.addEventListener('click', function () {
    sw = { swRunning: false, swStartedAt: 0, swAccum: 0, laps: [] };
    save(K_STATE, sw); paintStopwatch(); paintLaps();
  });

  /* ---------- timer ---------- */
  function timerRemaining() {
    var t = scheduler.timer || {};
    if (t.state === 'running' && t.deadline_ms) return Math.max(0, Number(t.deadline_ms) - Date.now());
    return Math.max(0, Number(t.remaining_ms || t.duration_ms || 0));
  }
  function paintTimer() {
    if (!el.tmTime) return;
    var t = scheduler.timer || {};
    var rem = timerRemaining();
    el.tmTime.textContent = fmtTimer(rem);
    var state = t.state || 'idle';
    if (state === 'running') el.tmState.textContent = 'Running — ends ' + new Date(t.deadline_ms).toLocaleTimeString();
    else if (state === 'paused') el.tmState.textContent = 'Paused';
    else if (state === 'completed') el.tmState.textContent = 'Finished — tap Stop timer';
    else if (state === 'acknowledged') el.tmState.textContent = 'Stopped';
    else el.tmState.textContent = 'Ready';
    if (el.tmStop) el.tmStop.disabled = !(state === 'completed' || state === 'running' || state === 'paused');
    if (el.tmStart) el.tmStart.textContent = state === 'paused' ? 'Resume' : 'Start';
  }
  function setTimerInputs() {
    var m = Math.max(0, parseInt(el.tmMin.value, 10) || 0);
    var s = Math.min(59, Math.max(0, parseInt(el.tmSec.value, 10) || 0));
    return (m * 60 + s) * 1000;
  }
  if (el.tmSet) el.tmSet.addEventListener('click', function () {
    var ms = setTimerInputs();
    if (ms < 1000) { toast('Set a timer of at least one second'); return; }
    bridgeCall('clock', 'set-timer', { duration_ms: ms, label: 'Timer' }).then(function (r) {
      if (r && r.success !== false) { applyState(r.state || {}); toast('Timer set to ' + fmtTimer(ms)); }
      else toast('Set failed: ' + ((r && (r.detail || r.error)) || 'scheduler unavailable'));
    });
  });
  document.querySelectorAll('.preset').forEach(function (b) {
    b.addEventListener('click', function () {
      var sec = Number(b.dataset.sec);
      el.tmMin.value = String(Math.floor(sec / 60)); el.tmSec.value = String(sec % 60);
      bridgeCall('clock', 'set-timer', { duration_ms: sec * 1000, label: 'Timer' }).then(function (r) {
        if (r && r.success !== false) { applyState(r.state || {}); }
        else { scheduler.timer = { state: 'idle', duration_ms: sec * 1000, remaining_ms: sec * 1000 }; paintTimer(); }
      });
    });
  });
  if (el.tmStart) el.tmStart.addEventListener('click', function () {
    var t = scheduler.timer || {};
    if (t.state === 'paused') {
      bridgeCall('clock', 'resume-timer', {}).then(function (r) {
        if (r && r.success !== false) applyState(r.state || {}); else toast('Resume failed');
      });
      return;
    }
    var ms = t.state === 'idle' || t.state === 'acknowledged' ? setTimerInputs() : Math.max(1000, timerRemaining());
    if (ms < 1000) { toast('Set a timer of at least one second'); return; }
    bridgeCall('clock', 'start-timer', { duration_ms: ms, label: 'Timer' }).then(function (r) {
      if (r && r.success !== false) { applyState(r.state || {}); toast('Timer started'); }
      else toast('Timer did not start: ' + ((r && (r.detail || r.error)) || 'scheduler unavailable'));
    });
  });
  if (el.tmPause) el.tmPause.addEventListener('click', function () {
    bridgeCall('clock', 'pause-timer', {}).then(function (r) {
      if (r && r.success !== false) applyState(r.state || {}); else toast('Pause failed');
    });
  });
  if (el.tmReset) el.tmReset.addEventListener('click', function () {
    bridgeCall('clock', 'reset-timer', {}).then(function (r) {
      if (r && r.success !== false) applyState(r.state || {}); else toast('Reset failed');
    });
  });
  if (el.tmStop) el.tmStop.addEventListener('click', function () {
    bridgeCall('clock', 'stop-timer', {}).then(function (r) {
      if (r && r.success !== false) { applyState(r.state || {}); toast('Timer stopped'); }
      else toast('Timer stop failed');
    });
  });

  /* ---------- compatibility hooks ---------- */
  function playAlarmSound(kind) {
    return bridgeCall('clock', 'preview-sound', { kind: kind === 'timer' ? 'timer' : 'alarm' })
      .then(function (r) { return !!(r && r.success !== false); });
  }
  function stopAlarmSound() {
    return bridgeCall('clock', 'stop-timer', {});
  }
  function syncClockSchedule() { return refreshScheduler(); }
  function checkAlarms() { /* scheduler-owned; retained as a no-op test hook */ }

  window.nuxelClock = {
    tick: tick, alarms: scheduler.alarms, playAlarmSound: playAlarmSound,
    stopAlarmSound: stopAlarmSound, syncClockSchedule: syncClockSchedule,
    normaliseClockTime: normaliseClockTime, fmtSw: fmtSw, fmtTimer: fmtTimer, fmtOffset: fmtOffset,
    parseOffsetMinutes: parseOffsetMinutes, refresh: refreshScheduler,
    checkAlarms: checkAlarms,
    get state() { return scheduler; }
  };

  function consumeAlarmDraft() {
    try {
      var raw = localStorage.getItem('nuxel.clock.alarmDraft');
      if (!raw) return;
      localStorage.removeItem('nuxel.clock.alarmDraft');
      var draft = JSON.parse(raw);
      if (!draft || typeof draft !== 'object') return;
      var alarmTab = document.querySelector('.tab[data-tab="alarm"]');
      if (alarmTab) alarmTab.click();
      if (draft.time && el.alarmTime) el.alarmTime.value = normaliseClockTime(draft.time) || el.alarmTime.value;
      if (draft.label && el.alarmLabel) el.alarmLabel.value = String(draft.label).slice(0, 120);
      if (el.alarmRepeat) el.alarmRepeat.checked = false;
      toast('Alarm prefilled from ' + (draft.sourceEventId ? 'Calendar' : 'Notes') + '. Review and tap Add.');
    } catch (e) {}
  }

  tick();
  paintLaps();
  consumeAlarmDraft();
  refreshScheduler();
  refreshSource();
  setInterval(tick, 500);
  setInterval(paintTimer, 250);
  setInterval(refreshScheduler, 1000);
})();
