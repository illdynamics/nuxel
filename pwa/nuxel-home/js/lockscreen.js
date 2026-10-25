/* Nuxel A45.1 Penguin Lockscreen — swipe the actual nuxel-lockhead.png upward
 * to unlock.  This is the real drag state machine:
 *
 *   IDLE -> TOUCH_CAPTURED -> DRAGGING -> THRESHOLD_REACHED -> UNLOCKING -> UNLOCKED
 *   DRAGGING -> CANCELLED -> RETURN_TO_REST -> IDLE
 *
 * A45.1 hotfix: this IIFE now binds `global` to window.  The previous revision
 * referenced a bare `global` that does not exist in WebKit; the first access
 * (`_buzz()` at the release) threw ReferenceError, so the unlock request was
 * never sent.  The drag itself already worked because its listeners were bound
 * before the throwing constructor call.  Everything visual is unchanged.
 *
 * The lockhead follows the finger (pointer capture), snaps back on an incomplete
 * drag, and only unlocks after crossing an upward threshold.  It is placed BELOW
 * the penguin already illustrated in nuxel-lockscreen.jpg (cover-crop aware), so
 * the resting handle never covers the wallpaper penguin.
 */
(function (global) {
  'use strict';

  const VERSION = 'a45.1';
  const WALLPAPER = { w: 768, h: 1376 };
  /* The illustrated penguin's approximate opaque bounds in wallpaper pixels,
     measured from the shipped asset.  Only the vertical extent matters here:
     the lockhead must land below PENGUIN_BOTTOM_Y. */
  const PENGUIN_BOTTOM_Y = 990;
  const MIN_SPACING = 32;      /* logical px between the penguin and the handle */
  const THRESHOLD_FRACTION = 0.22; /* of viewport height, per mission 11 */
  const DRAG_SLOP = 4;         /* px before a contact is a drag */
  const SAFE_TOP = 24;         /* px of usable travel reserved above the handle */
  const RETURN_MS = 240;       /* snap-back animation */
  const DISMISS_MS = 120;      /* let the accepted unlock animation finish */

  class Lockscreen {
    constructor() {
      this.el = document.getElementById('lockscreen');
      this.handle = document.getElementById('lockscreen-handle');
      this.wrap = document.getElementById('lockscreen-handle-wrap');
      this.hint = document.getElementById('lockscreen-hint');
      this.timeEl = document.getElementById('lockscreen-time');
      this.dateEl = document.getElementById('lockscreen-date');
      this.batteryEl = document.getElementById('lockscreen-battery');
      this.indicators = null;
      this.locked = false;
      this.state = 'IDLE';
      this.startY = 0;
      this.currentY = 0;
      this.restY = 0;
      this.baseTop = 0;
      this.unlocked = false;
      this.pointerId = null;
      this.gesture = null;
      this.gestureSeq = 0;
      this._bound = false;
      this._returnTimer = null;
      this._dismissTimer = null;
      this._wiggleTimer = null;
      this._wiggleStopTimer = null;
      this._reducedMotion = !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches);

      if (!this.el || !this.handle) return;
      this._bindHandle();
      this._startClock();
      this._startBattery();
      this._startWiggle();
      this._initIndicators();
      this._positionHandle();
    }

    /* A68 status indicators (charging / PC-connected / live console).  They
       are three independent state machines driven by real Linux state; each one
       lights independently and can combine with any other. */
    _initIndicators() {
      if (typeof global.NuxelLockscreenIndicators !== 'function') return;
      try {
        this.indicators = new global.NuxelLockscreenIndicators();
        if (this.indicators && this.el) this.indicators.ensureDom(this.el);
      } catch (err) {
        this.indicators = null;
        this._trace('indicators-init-failed ' + (err && err.message ? err.message : err));
      }
    }

    _startIndicators() {
      if (this.indicators) {
        try { this.indicators.start(); } catch (err) { this._trace('indicators-start-failed ' + (err && err.message ? err.message : err)); }
      }
    }

    _stopIndicators() {
      if (this.indicators) {
        try { this.indicators.stop(); } catch (err) { this._trace('indicators-stop-failed ' + (err && err.message ? err.message : err)); }
      }
    }

    /* Wake is an event: refresh immediately without waiting for the safety
       interval.  Kept here so the lockscreen owns indicator lifecycle. */
    refreshIndicators() {
      if (this.indicators && typeof this.indicators.refresh === 'function') {
        try { this.indicators.refresh(); } catch (err) { this._trace('indicators-refresh-failed ' + (err && err.message ? err.message : err)); }
      }
    }

    /* Map a wallpaper pixel coordinate to CSS under background-size: cover. */
    _coverCssY(imageY) {
      const vw = global.innerWidth || 360;
      const vh = global.innerHeight || 760;
      const scale = Math.max(vw / WALLPAPER.w, vh / WALLPAPER.h);
      const scaledH = WALLPAPER.h * scale;
      const cropY = Math.max(0, (scaledH - vh) / 2);
      return imageY * scale - cropY;
    }

    _positionHandle() {
      const vw = global.innerWidth || 360;
      const vh = global.innerHeight || 760;
      const handleSize = Math.max(96, Math.min(124, vw * 0.3));
      const penguinBottomCss = this._coverCssY(PENGUIN_BOTTOM_Y);
      /* Rest the handle clearly below the wallpaper penguin, with real spacing,
         while keeping it inside the visible lockscreen. */
      const desiredTop = Math.min(Math.max(penguinBottomCss + MIN_SPACING, vh * 0.62), vh - handleSize - 24);
      this.handle.style.width = handleSize + 'px';
      this.handle.style.height = handleSize + 'px';
      this.wrap.style.top = desiredTop + 'px';
      this.wrap.style.bottom = 'auto';
      this.baseTop = desiredTop;
      this.restY = 0;
      this._trace('position top=' + Math.round(desiredTop) + ' penguinBottom=' + Math.round(penguinBottomCss) +
                  ' vh=' + vh + ' handle=' + handleSize);
    }

    /* The threshold is in viewport CSS pixels (the same space as clientY).  It
       is 22% of the usable height, but never larger than the travel the handle
       actually has above its resting position. */
    _effectiveThreshold() {
      const vh = global.innerHeight || 760;
      const baseTop = Number.isFinite(this.baseTop) ? this.baseTop : vh * 0.62;
      const available = Math.max(0, baseTop - SAFE_TOP);
      const desired = vh * THRESHOLD_FRACTION;
      return Math.max(1, Math.round(Math.min(desired, available)));
    }

    _bindHandle() {
      if (this._bound) return;
      this._bound = true;
      const h = this.handle;

      h.addEventListener('pointerdown', (e) => this._pointerDown(e));
      h.addEventListener('pointermove', (e) => this._pointerMove(e));
      h.addEventListener('pointerup', (e) => this._finishPointer(e, 'pointerup'));
      h.addEventListener('pointercancel', () => this._cancelGesture('pointercancel'));
      h.addEventListener('lostpointercapture', () => this._lostCapture());

      /* Capture-phase fallbacks: a release outside the original icon rectangle
         must still complete the gesture even if pointer capture is unavailable
         or was lost.  The per-gesture `released` guard makes this idempotent. */
      global.addEventListener('pointermove', (e) => this._pointerMove(e), true);
      global.addEventListener('pointerup', (e) => this._finishPointer(e, 'window-pointerup'), true);
      global.addEventListener('pointercancel', () => this._cancelGesture('window-pointercancel'), true);
    }

    _pointerDown(e) {
      if (e && e.isTrusted === false) return; /* never accept untrusted script gestures */
      if (!this.locked || this.state === 'UNLOCKING' || this.state === 'UNLOCKED') return;
      if (e.button !== undefined && e.button !== 0) return;
      if (this.gesture) return; /* one gesture at a time */

      if (this._returnTimer) { global.clearTimeout(this._returnTimer); this._returnTimer = null; }
      if (this._dismissTimer) { global.clearTimeout(this._dismissTimer); this._dismissTimer = null; }

      this.pointerId = e.pointerId;
      this.startY = e.clientY;
      this.currentY = e.clientY;
      this.state = 'TOUCH_CAPTURED';
      this.gesture = {
        id: ++this.gestureSeq,
        startX: e.clientX,
        startY: e.clientY,
        threshold: this._effectiveThreshold(),
        distance: 0,
        reached: false,
        released: false,
        requested: false,
        consumed: false,
        acknowledged: false,
      };
      this.handle.style.transition = '';
      this.handle.style.transform = 'translateY(0)';
      this.handle.classList.remove('unlocking');
      this.handle.classList.remove('armed');
      this.handle.classList.add('grabbed');
      try { h_capture(this.handle, e.pointerId); } catch (err) { /* capture is a fallback, not a requirement */ }
      this._trace('gesture=down id=' + this.gesture.id + ' pointer=' + e.pointerId +
                  ' down=(' + Math.round(e.clientX) + ',' + Math.round(e.clientY) + ')' +
                  ' threshold=' + this.gesture.threshold + ' vh=' + (global.innerHeight || 760) +
                  ' state=' + this.state);
    }

    _pointerMove(e) {
      const g = this.gesture;
      if (!g || g.released) return;
      if (e && e.isTrusted === false) return;
      if (this.pointerId !== null && e.pointerId !== undefined && e.pointerId !== this.pointerId) return;
      this.currentY = e.clientY;
      const dy = this.startY - this.currentY; /* signed upward travel */
      g.distance = dy;
      if (dy > DRAG_SLOP) {
        if (this.state === 'TOUCH_CAPTURED') this.state = 'DRAGGING';
      }
      const reached = dy >= g.threshold;
      if (reached && !g.reached) {
        g.reached = true;
        this.state = 'THRESHOLD_REACHED';
        this.handle.classList.add('armed');
        this._trace('gesture=threshold id=' + g.id + ' up=' + Math.round(dy) +
                    ' threshold=' + g.threshold + ' reached=1 state=' + this.state);
      } else if (!reached && g.reached) {
        g.reached = false;
        if (this.state === 'THRESHOLD_REACHED') this.state = 'DRAGGING';
        this.handle.classList.remove('armed');
      }
      /* The handle follows the finger in real time.  This is presentation only;
         the authoritative distance is g.distance above. */
      const clamped = Math.max(0, Math.min(dy, g.threshold + 120));
      this.handle.style.transform = 'translateY(' + (-clamped) + 'px)';
    }

    _finishPointer(e, source) {
      const g = this.gesture;
      if (!g || g.released) return;
      if (this.pointerId !== null && e && e.pointerId !== undefined && e.pointerId !== this.pointerId) return;
      g.released = true;
      /* The release event carries the final coordinate.  Use it even when the
         last pointermove was coalesced or capture had to fall back to window. */
      if (e && Number.isFinite(e.clientY)) this.currentY = e.clientY;
      const dy = this.startY - this.currentY;
      g.distance = dy;
      const reached = dy >= g.threshold;
      if (reached) g.reached = true;
      this._trace('gesture=release id=' + g.id + ' pointer=' + this.pointerId +
                  ' up=' + Math.round(dy) + ' threshold=' + g.threshold +
                  ' reached=' + (reached ? 1 : 0) + ' source=' + source +
                  ' state=' + this.state + ' locked=' + (this.locked ? 1 : 0) +
                  ' visible=' + (this.el.hidden ? 0 : 1));
      this._releaseCapture();
      if (reached) {
        this._requestUnlock(g);
      } else {
        this._returnToRest('release-below-threshold');
      }
    }

    _lostCapture() {
      const g = this.gesture;
      if (!g || g.released) return;
      if (this.state === 'UNLOCKING' || this.state === 'UNLOCKED') return;
      this._cancelGesture('lostpointercapture');
    }

    _cancelGesture(reason) {
      if (this.state === 'UNLOCKING' || this.state === 'UNLOCKED') return;
      const g = this.gesture;
      if (g) g.released = true;
      this._releaseCapture();
      this._trace('gesture=cancel id=' + (g ? g.id : '-') + ' reason=' + reason +
                  ' locked=' + (this.locked ? 1 : 0) + ' visible=' + (this.el.hidden ? 0 : 1));
      this._returnToRest(reason);
    }

    _releaseCapture() {
      const id = this.pointerId;
      this.pointerId = null;
      if (id === null || !this.handle.releasePointerCapture) return;
      try { this.handle.releasePointerCapture(id); } catch (err) { /* best effort */ }
    }

    _returnToRest(reason) {
      const g = this.gesture;
      if (g) g.released = true;
      this.state = 'CANCELLED';
      this.handle.classList.remove('grabbed');
      this.handle.classList.remove('armed');
      this.handle.classList.remove('unlocking');
      this.handle.style.opacity = '';
      this.handle.style.transition = 'transform .22s ease-out';
      this.handle.style.transform = 'translateY(0)';
      if (this._returnTimer) global.clearTimeout(this._returnTimer);
      this._returnTimer = global.setTimeout(() => {
        this._returnTimer = null;
        this.handle.style.transition = '';
        this.state = 'IDLE';
        this.gesture = null;
        this.pointerId = null;
        this._trace('state=IDLE reason=' + reason);
      }, RETURN_MS);
    }

    _requestUnlock(g) {
      if (!this.locked || this.state === 'UNLOCKING' || this.state === 'UNLOCKED' || g.requested) return;
      g.requested = true;
      this.state = 'UNLOCKING';
      this.handle.classList.remove('grabbed');
      this.handle.classList.remove('armed');
      this.handle.classList.remove('wiggling');
      this.handle.classList.add('unlocking');
      this.handle.style.transition = 'transform .28s ease-out, opacity .28s ease-out';
      this._buzz();

      const request = Object.freeze({
        source: 'penguin-lockscreen',
        gestureId: g.id,
        pointerId: this.pointerId,
        direction: 'up',
        distance: Math.round(g.distance),
        threshold: Math.round(g.threshold),
        completed: true,
        stateBefore: 'LOCKED_SCREEN_ON',
      });
      this._trace('gesture=unlock-request id=' + g.id + ' up=' + request.distance +
                  ' threshold=' + request.threshold + ' state=' + this.state +
                  ' locked=' + (this.locked ? 1 : 0) + ' visible=' + (this.el.hidden ? 0 : 1));

      let pending;
      try {
        const controller = global.nuxel;
        if (controller && typeof controller.unlockFromLockscreen === 'function') {
          /* The trusted launcher controller validates this one-shot gesture,
             asks the native host for its authoritative acknowledgement and
             performs the lock-state transition. */
          pending = controller.unlockFromLockscreen(this, request);
        } else if (global.NuxelHost && global.NuxelHost.available &&
                   typeof global.NuxelHost.action === 'function') {
          /* Compatibility path for a standalone launcher document: the existing
             host `unlock` action is the only supported unlock verb. */
          pending = global.NuxelHost.action('unlock');
        } else {
          pending = Promise.resolve({ ok: false, error: 'no-authorized-controller' });
        }
      } catch (err) {
        pending = Promise.reject(err);
      }
      Promise.resolve(pending).then((res) => {
        if (res && res.ok === true) this._unlockAccepted(g, res);
        else this._unlockRejected(g, res);
      }, (err) => this._unlockRejected(g, err));
    }

    _unlockAccepted(g, res) {
      if (g.acknowledged) return;
      g.acknowledged = true;
      this._trace('gesture=unlock-ack id=' + g.id + ' backend=' +
                  ((res && (res.state || res.via)) || 'ok') +
                  ' stateAfter=UNLOCKED lockedAfter=0 visibleAfter=0');
      /* Hide only after the controller/native host has acknowledged. */
      if (this._dismissTimer) global.clearTimeout(this._dismissTimer);
      this._dismissTimer = global.setTimeout(() => {
        this._dismissTimer = null;
        this.hide();
      }, DISMISS_MS);
    }

    _unlockRejected(g, err) {
      if (g.acknowledged) return;
      g.acknowledged = true;
      const detail = err && (err.error || err.message || err) ? (err.error || err.message || err) : 'unknown';
      this._trace('gesture=unlock-rejected id=' + g.id + ' error=' + String(detail).slice(0, 120) +
                  ' stateAfter=' + this.state + ' lockedAfter=' + (this.locked ? 1 : 0) +
                  ' visibleAfter=' + (this.el.hidden ? 0 : 1));
      this._returnToRest('unlock-rejected');
    }

    /* Called by NuxelHome.unlockFromLockscreen.  It is deliberately internal to
       the active lockscreen instance and consumes the gesture id exactly once. */
    acceptGestureUnlock(request) {
      const g = this.gesture;
      if (!this.locked || this.state !== 'UNLOCKING' || !g) return false;
      if (!request || request.source !== 'penguin-lockscreen') return false;
      if (request.gestureId !== g.id) return false;
      if (!g.released || !g.reached || !g.requested || g.consumed) return false;
      if (!(Number(request.distance) >= Number(request.threshold))) return false;
      if (Number(request.threshold) !== Math.round(g.threshold)) return false;
      g.consumed = true;
      return true;
    }

    show(reason) {
      if (!this.el) return;
      if (this._returnTimer) { global.clearTimeout(this._returnTimer); this._returnTimer = null; }
      if (this._dismissTimer) { global.clearTimeout(this._dismissTimer); this._dismissTimer = null; }
      this.el.hidden = false;
      this.locked = true;
      this.unlocked = false;
      this.state = 'IDLE';
      try { document.body.classList.add('lockscreen-active'); } catch (e) {}
      this._blurInputs();
      this.gesture = null;
      this.pointerId = null;
      this.handle.classList.remove('unlocking');
      this.handle.classList.remove('armed');
      this.handle.classList.remove('grabbed');
      this.handle.classList.remove('wiggling');
      this.handle.style.transition = '';
      this.handle.style.transform = '';
      this.handle.style.opacity = '';
      this._positionHandle();
      this._updateClock();
      this._updateBattery();
      this._startIndicators();
      this._trace('show version=' + VERSION + ' reason=' + (reason || 'unknown') +
                  ' locked=1 visible=1 threshold=' + this._effectiveThreshold());
    }

    hide() {
      if (!this.el) return;
      if (this._returnTimer) { global.clearTimeout(this._returnTimer); this._returnTimer = null; }
      if (this._dismissTimer) { global.clearTimeout(this._dismissTimer); this._dismissTimer = null; }
      this.el.hidden = true;
      this.locked = false;
      this.unlocked = true;
      this.state = 'UNLOCKED';
      try { document.body.classList.remove('lockscreen-active'); } catch (e) {}
      this.gesture = null;
      this.pointerId = null;
      this.handle.classList.remove('grabbed');
      this.handle.classList.remove('armed');
      this.handle.classList.remove('unlocking');
      this.handle.classList.remove('wiggling');
      this.handle.style.transition = '';
      this.handle.style.transform = '';
      this.handle.style.opacity = '';
      this._stopIndicators();
      this._trace('hide version=' + VERSION + ' state=UNLOCKED locked=0 visible=0');
    }

    isLocked() { return this.locked; }

    _buzz() {
      try {
        if (global.NuxelHost && global.NuxelHost.available &&
            typeof global.NuxelHost.action === 'function') {
          global.NuxelHost.action('haptics-navigation');
        } else if (global.navigator && global.navigator.vibrate) {
          global.navigator.vibrate(14);
        }
      } catch (e) { /* feedback must never block the unlock */ }
    }

    _displayOff() {
      try { return document.body.classList.contains('display-off'); } catch (e) { return false; }
    }

    _blurInputs() {
      // The compositor OSK is bound to text-input focus.  Dropping focus on
      // lock hides it without touching the typed value in any field.
      try {
        const active = document.activeElement;
        if (active && typeof active.blur === 'function') active.blur();
        const sel = global.getSelection && global.getSelection();
        if (sel && sel.removeAllRanges) sel.removeAllRanges();
      } catch (e) { /* best effort */ }
    }

    _updateClock() {
      if (!this.timeEl || !this.dateEl || this._displayOff()) return;
      const d = new Date();
      this.timeEl.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const opts = { weekday: 'long', month: 'long', day: 'numeric' };
      this.dateEl.textContent = d.toLocaleDateString([], opts);
    }

    _startWiggle() {
      if (this._reducedMotion || this._wiggleTimer) return;
      // Low-frequency scheduler: at most one short compositor-friendly wiggle
      // per ~9 s.  It never runs while dragged, unlocked, or display-off.
      this._wiggleTimer = global.setInterval(() => {
        if (!this.locked || this.state !== 'IDLE' || this._displayOff()) return;
        if (!this.handle || this.handle.classList.contains('grabbed')) return;
        this.handle.classList.add('wiggling');
        if (this._wiggleStopTimer) global.clearTimeout(this._wiggleStopTimer);
        this._wiggleStopTimer = global.setTimeout(() => {
          this._wiggleStopTimer = null;
          if (this.handle) this.handle.classList.remove('wiggling');
        }, 1400);
      }, 9000);
    }

    _startClock() {
      this._updateClock();
      global.setInterval(() => this._updateClock(), 1000);
    }

    _updateBattery() {
      if (!this.batteryEl || this._displayOff()) return;
      const paint = (level, charging) => {
        if (!this.batteryEl) return;
        const ok = Number.isFinite(Number(level)) && Number(level) >= 0 && Number(level) <= 100;
        const shown = ok ? Math.round(Number(level)) : null;
        this.batteryEl.textContent = (charging ? '⚡ ' : '') + (shown === null ? '—' : shown + '%');
      };
      paint(null, false);
      // A69-01: ONE authoritative, immediate source. The host reads
      // /sys/class/power_supply/<type=Battery>/capacity directly through
      // nuxel-pwa-host and is available the moment the launcher document is
      // alive — it does NOT wait for the HTTP bridge daemon. Try the host path
      // first, then the HTTP bridge for the charging glyph. An absent reading
      // stays the neutral em dash, never a fabricated 0%.
      const hostReady = global.NuxelHost && global.NuxelHost.available &&
                        typeof global.NuxelHost.statusRead === 'function';
      if (hostReady) {
        Promise.resolve(global.NuxelHost.statusRead('battery-capacity')).then((r) => {
          const t = (r && (r.text || r.value)) || '';
          const m = t.match(/([-+]?\d+(?:\.\d+)?)/);
          if (m) paint(m[1], false);
        }).catch(() => {});
      }
      try {
        if (typeof bridge !== 'undefined' && bridge && typeof bridge.getPhoneStatus === 'function') {
          Promise.resolve(bridge.getPhoneStatus()).then((st) => {
            const bat = st && st.battery;
            // Only the bridge path knows charging state; accept a valid level
            // and charging flag. A bridge mock/absence yields no battery object
            // and is ignored, leaving the host value (or —) in place.
            if (bat && Number.isFinite(Number(bat.level))) paint(Number(bat.level), !!bat.charging);
          }).catch(() => {});
        } else if (!hostReady && global.NuxelHost && typeof global.NuxelHost.statusRead === 'function') {
          global.NuxelHost.statusRead('battery-capacity').then((r) => {
            const t = (r && (r.text || r.value)) || '';
            const m = t.match(/([-+]?\d+(?:\.\d+)?)/);
            paint(m ? m[1] : null, false);
          }).catch(() => {});
        }
      } catch (e) { /* show — rather than a fabricated number */ }
    }

    _startBattery() {
      this._updateBattery();
      // First-boot convergence: re-check after 1s and 3s so the lockscreen
      // reflects the kernel value as soon as it is readable, then settle to a
      // slow event-pace poll. No minutes-long unknown window.
      global.setTimeout(() => this._updateBattery(), 1000);
      global.setTimeout(() => this._updateBattery(), 3000);
      global.setInterval(() => this._updateBattery(), 20000);
    }

    _trace(msg) {
      const line = 'LOCKS[' + VERSION + '] ' + msg;
      try {
        const diag = global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag;
        if (diag) diag.postMessage(line);
      } catch (e) { /* observation only */ }
      try { if (global.console) global.console.log('[Lockscreen]', msg); } catch (e) {}
    }
  }

  function h_capture(el, id) {
    if (el.setPointerCapture) el.setPointerCapture(id);
  }

  global.NuxelLockscreen = Lockscreen;
})(window);
