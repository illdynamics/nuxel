/* Nuxel lockscreen alarm/timer penguins (PWNAGE-84000).
 *
 * Authoritative state comes from nuxel-clockd via the bridge's system
 * indicators endpoint.  The alarm lane owns swipe-left (snooze) and swipe-right
 * (dismiss); the timer lane owns one tap (stop/acknowledge).  Neither gesture
 * ever touches the unlock handle or a full-screen invisible overlay.
 */
(function (global) {
  'use strict';
  var POLL_MS = 1000;
  var SWIPE_MIN = 68;
  var VELOCITY_MIN = 0.22;

  function $(id) { return global.document ? global.document.getElementById(id) : null; }
  function bridge() {
    if (global.NuxelBridge && typeof global.NuxelBridge.call === 'function') return global.NuxelBridge;
    return null;
  }
  function indicators() {
    try {
      if (global.bridge && typeof global.bridge.getSystemIndicators === 'function') {
        return Promise.resolve(global.bridge.getSystemIndicators());
      }
    } catch (e) {}
    return Promise.resolve(null);
  }
  function activeClockOccurrence(state, kind) {
    var list = (state && state.active_occurrences) || [];
    for (var i = 0; i < list.length; i++) {
      if (list[i] && list[i].kind === kind && list[i].state === 'ringing') return list[i];
    }
    return null;
  }
  function call(verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable' });
    try { return Promise.resolve(b.call('clock', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e) }); }
  }
  function setShown(el, shown) {
    if (!el) return;
    el.setAttribute('aria-hidden', shown ? 'false' : 'true');
    el.classList.toggle('visible', !!shown);
  }
  function toast(msg) {
    try {
      if (global.NuxelOSD && typeof global.NuxelOSD.show === 'function') { global.NuxelOSD.show(msg); return; }
    } catch (e) {}
    try { global.dispatchEvent(new CustomEvent('nuxel:toast', { detail: { text: msg } })); } catch (e) {}
  }

  function ClockPenguins() {
    this.alarm = $('lockscreen-alarm-indicator');
    this.timer = $('lockscreen-timer-indicator');
    this.alarmLane = $('lockscreen-alarm-lane');
    this.timerLane = $('lockscreen-timer-lane');
    this.alarmHint = $('lockscreen-alarm-hint');
    this.timerHint = $('lockscreen-timer-hint');
    this.state = null;
    this.timerId = null;
    this.inFlight = false;
    this.locked = false;
    this._wire();
  }

  ClockPenguins.prototype._wire = function () {
    var self = this;
    if (this.alarm) {
      this.alarm.addEventListener('pointerdown', function (ev) { self._alarmDown(ev); });
      this.alarm.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); }
      });
    }
    if (this.timer) {
      this.timer.addEventListener('pointerdown', function (ev) { self._timerTap(ev); });
      this.timer.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); self._stopTimer(); }
      });
    }
    try {
      global.document.addEventListener('nuxel:lockscreen-shown', function () { self.locked = true; self.refresh(); }, { passive: true });
      global.document.addEventListener('nuxel:lockscreen-hidden', function () { self.locked = false; self.stop(); }, { passive: true });
      global.document.addEventListener('nuxel:display-on', function () { self.refresh(); }, { passive: true });
      global.document.addEventListener('visibilitychange', function () { if (!global.document.hidden && self.locked) self.refresh(); }, { passive: true });
    } catch (e) {}
  };

  ClockPenguins.prototype.start = function () {
    this.locked = true;
    this.refresh();
    if (this.timerId === null) {
      var self = this;
      this.timerId = global.setInterval(function () { if (self.locked) self.refresh(); }, POLL_MS);
    }
  };
  ClockPenguins.prototype.stop = function () {
    this.locked = false;
    if (this.timerId !== null) { global.clearInterval(this.timerId); this.timerId = null; }
  };
  ClockPenguins.prototype.refresh = function () {
    var self = this;
    if (this.inFlight) return;
    this.inFlight = true;
    indicators().then(function (doc) {
      self.inFlight = false;
      if (!doc || doc.success === false) return;
      var clock = doc.clock_scheduler || {};
      self.state = clock;
      self.render(clock);
    }, function () { self.inFlight = false; });
  };
  ClockPenguins.prototype.render = function (clock) {
    clock = clock || {};
    var alarmShown = !!clock.available && (clock.alarm_visible || clock.alarm_ringing);
    var timerShown = !!clock.available && (clock.timer_visible || clock.timer_ringing);
    setShown(this.alarm, alarmShown);
    setShown(this.timer, timerShown);
    if (this.alarm) {
      this.alarm.classList.toggle('ringing', !!clock.alarm_ringing);
      this.alarm.classList.toggle('snoozed', !clock.alarm_ringing && !!clock.alarm_snoozed);
      this.alarm.setAttribute('aria-label', clock.alarm_ringing ? 'Alarm ringing — swipe left to snooze or right to stop' : 'Alarm set');
    }
    if (this.timer) {
      this.timer.classList.toggle('ringing', !!clock.timer_ringing);
      this.timer.setAttribute('aria-label', clock.timer_ringing ? 'Timer finished — tap to stop' : 'Timer running — tap to stop');
    }
    if (this.alarmHint) {
      this.alarmHint.textContent = clock.alarm_ringing
        ? (clock.snooze_enabled ? 'swipe left to snooze · right to stop' : 'swipe right to stop')
        : (clock.alarm_snoozed ? 'alarm snoozed' : 'next alarm is armed');
    }
    if (this.timerHint) this.timerHint.textContent = clock.timer_ringing ? 'tap to stop' : 'tap to stop timer';
  };

  ClockPenguins.prototype._alarmDown = function (ev) {
    if (!this.state || !this.state.alarm_ringing) return;
    if (ev.button !== undefined && ev.button !== 0) return;
    ev.preventDefault();
    ev.stopPropagation();
    var el = this.alarm;
    var startX = ev.clientX, startY = ev.clientY, startT = performance.now();
    var pointer = ev.pointerId;
    /* PWNAGE-87000: the alarm penguin must visibly follow the finger like the
       unlock handle.  Clamp to a safe horizontal band so the artwork never
       crosses into the timer lane or the unlock handle, and pause the shake
       animation so the drag transform is authoritative. */
    var maxX = Math.max(120, Math.min(170, Math.round((global.innerWidth || 400) * 0.34)));
    try { el.setPointerCapture(pointer); } catch (e) {}
    el.classList.add('dragging');
    var move = function (e) {
      if (e.pointerId !== pointer) return;
      var dx = e.clientX - startX, dy = e.clientY - startY;
      if (Math.abs(dx) > Math.abs(dy) * 1.2) {
        var clamped = Math.max(-maxX, Math.min(maxX, dx));
        el.style.transform = 'translate3d(' + clamped + 'px,0,0) scale(1)';
        el.classList.toggle('swipe-left', dx < -12);
        el.classList.toggle('swipe-right', dx > 12);
      }
      if (e.cancelable) e.preventDefault();
    };
    var cleanup = function () {
      try { el.releasePointerCapture(pointer); } catch (x) {}
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', finish);
      el.removeEventListener('pointercancel', cancel);
      el.removeEventListener('lostpointercapture', cancel);
      el.classList.remove('swipe-left', 'swipe-right', 'dragging');
      el.style.transform = '';
    };
    var finish = function (e) {
      if (e && e.pointerId !== pointer) return;
      cleanup();
      var dx = (e ? e.clientX : startX) - startX;
      var dy = (e ? e.clientY : startY) - startY;
      var dt = Math.max(1, performance.now() - startT);
      var velocity = Math.abs(dx) / dt;
      if (Math.abs(dx) < SWIPE_MIN || Math.abs(dx) < Math.abs(dy) * 1.25 || velocity < VELOCITY_MIN) {
        if (dx !== 0 && (Math.abs(dx) >= 20 || Math.abs(dy) >= 20)) {
          el.classList.add('rejected');
          global.setTimeout(function () { el.classList.remove('rejected'); }, 240);
        }
        return;
      }
      var occ = activeClockOccurrence(this.state, 'alarm');
      if (!occ) return;
      if (dx < 0) this._snoozeAlarm(occ);
      else this._dismissAlarm(occ);
    }.bind(this);
    var cancel = function (e) {
      if (e && e.pointerId !== pointer) return;
      cleanup();
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', finish);
    el.addEventListener('pointercancel', cancel);
    el.addEventListener('lostpointercapture', cancel);
  };

  ClockPenguins.prototype._snoozeAlarm = function (occ) {
    var self = this;
    if (!this.state || this.state.snooze_enabled === false) {
      toast('Snooze is disabled in Clock settings');
      this.alarm.classList.add('rejected');
      global.setTimeout(function () { self.alarm.classList.remove('rejected'); }, 240);
      return;
    }
    call('snooze-occurrence', { id: occ.id }).then(function (r) {
      if (r && r.success !== false) {
        toast('Alarm snoozed for ' + ((r.occurrence && r.occurrence.due_ms) ? 'the configured interval' : 'the configured interval'));
        self.refresh();
      } else {
        toast('Snooze failed: ' + ((r && (r.detail || r.error)) || 'unknown error'));
      }
    });
  };
  ClockPenguins.prototype._dismissAlarm = function (occ) {
    var self = this;
    call('dismiss-occurrence', { id: occ.id }).then(function (r) {
      if (r && r.success !== false) { toast('Alarm stopped'); self.refresh(); }
      else toast('Stop failed: ' + ((r && (r.detail || r.error)) || 'unknown error'));
    });
  };
  ClockPenguins.prototype._timerTap = function (ev) {
    if (ev.button !== undefined && ev.button !== 0) return;
    ev.preventDefault();
    ev.stopPropagation();
    this._stopTimer();
  };
  ClockPenguins.prototype._stopTimer = function () {
    var self = this;
    call('stop-timer', {}).then(function (r) {
      if (r && r.success !== false) { toast('Timer stopped'); self.refresh(); }
      else toast('Timer stop failed: ' + ((r && (r.detail || r.error)) || 'unknown error'));
    });
  };

  var instance = new ClockPenguins();
  global.NuxelLockscreenClock = instance;
  global.document.addEventListener('nuxel:lockscreen-shown', function () { instance.start(); });
  if (global.document.body && global.document.body.classList.contains('lockscreen-active')) instance.start();
})(window);
