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
  const RETURN_MS = 160;       /* snap-back animation (snappier) */
  const DISMISS_MS = 70;       /* accepted unlock: one short acknowledgement */

  class Lockscreen {
    constructor() {
      this.el = document.getElementById('lockscreen');
      this.handle = document.getElementById('lockscreen-handle');
      this.wrap = document.getElementById('lockscreen-handle-wrap');
      this.hint = document.getElementById('lockscreen-hint');
      this.timeEl = document.getElementById('lockscreen-time');
      this.dateEl = document.getElementById('lockscreen-date');
      this.batteryEl = document.getElementById('lockscreen-battery');
      this.touchWarningEl = document.getElementById('lockscreen-touch-warning');
      this.touchWarningDetailEl = document.getElementById('lockscreen-touch-warning-detail');
      this.indicators = null;
      /* Battery truth state.  The gauge can briefly expose 0 while the
         charger/PMIC re-initialises; a 100% -> 0% paint is therefore a bug, not
         a reading.  A new 0 (or any >30 point swing) has to be observed more
         than once before it replaces a known-good value. */
      this.batteryLevel = null;
      this.batteryCharging = false;
      this.batteryStatus = '';
      this.batteryText = '';
      this._batteryInFlight = false;
      this._batteryZeroCount = 0;
      this._batteryBigCandidate = null;
      this._batteryBigCount = 0;
      this._touchInFlight = false;
      this._touchTimer = null;
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
      this._startTouchWarning();
      this._initIndicators();
      this._positionHandle();
      try {
        document.addEventListener('nuxel:display-on', () => {
          this._updateClock();
          this._updateBattery();
          this._updateTouchWarning();
        });
      } catch (e) { /* observation only */ }
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
      /* The owner should not have to hit the 108 px artwork exactly.  A swipe
         that starts anywhere in the lower band (full screen width) is the same
         unlock gesture; the handle still follows the finger. */
      this.el.addEventListener('pointerdown', (e) => this._lockscreenPointerDown(e));
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

    _lockscreenPointerDown(e) {
      if (!this.locked || this.gesture) return;
      if (this.handle && typeof this.handle.contains === 'function' &&
          e && e.target && this.handle.contains(e.target)) return; /* handle owns it */
      /* PWNAGE-34000: the connection-mode button/overlay are a limited system
         action.  Tapping them must open/control the mode sheet, not start an
         unlock gesture and not accidentally dismiss the lockscreen. */
      if (e && e.target && typeof e.target.closest === 'function') {
        try {
          if (e.target.closest('#lockscreen-connection-mode, #connection-mode-overlay')) return;
        } catch (err) { /* ignore closest failures */ }
      }
      const y = Number(e && e.clientY);
      const baseTop = Number.isFinite(this.baseTop) ? this.baseTop : (global.innerHeight || 760) * 0.62;
      if (Number.isFinite(y) && y >= baseTop - 80) this._pointerDown(e);
    }

    _pointerDown(e) {
      if (e && e.isTrusted === false) return; /* never accept untrusted script gestures */
      if (e && typeof e.preventDefault === 'function' && e.cancelable !== false) {
        try { e.preventDefault(); } catch (err) { /* touch-action also applies */ }
      }
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
      this.handle.style.transition = 'transform .16s ease-out';
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
      this._updateTouchWarning();
      this._startIndicators();
      this._wiggleOnce(this._displayOff() ? 2500 : 900);
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
      if (this.touchWarningEl) {
        this.touchWarningEl.hidden = true;
        try { this.touchWarningEl.classList.remove('visible'); } catch (e) {}
      }
      /* The status bar paused its provider polls while covered.  Tell it to
         refresh once, now that it is visible again. */
      try { document.dispatchEvent(new CustomEvent('nuxel:lockscreen-hidden')); } catch (e) {}
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
      const timeText = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const opts = { weekday: 'long', month: 'long', day: 'numeric' };
      const dateText = d.toLocaleDateString([], opts);
      /* Do not dirty the DOM 60 times a minute to repaint an unchanged clock. */
      if (this.timeEl.textContent !== timeText) this.timeEl.textContent = timeText;
      if (this.dateEl.textContent !== dateText) this.dateEl.textContent = dateText;
    }

    /* PWNAGE-37000B: ONE greeting wiggle per lock/wake, not an endless timer.
       The old 12 s interval produced a 1.1 s continuous repaint of the
       lockhead and kept the display bridge committing unchanged glass.  The
       penguin still greets the owner, then the lockscreen is truly idle. */
    _wiggleOnce(delayMs) {
      if (this._reducedMotion || this._wiggleTimer) return;
      this._wiggleTimer = global.setTimeout(() => {
        this._wiggleTimer = null;
        if (!this.locked || this.state !== 'IDLE' || this._displayOff()) return;
        if (!this.handle || this.handle.classList.contains('grabbed')) return;
        this.handle.classList.add('wiggling');
        if (this._wiggleStopTimer) global.clearTimeout(this._wiggleStopTimer);
        this._wiggleStopTimer = global.setTimeout(() => {
          this._wiggleStopTimer = null;
          if (this.handle) this.handle.classList.remove('wiggling');
        }, 900);
      }, delayMs == null ? 900 : delayMs);
    }

    _startClock() {
      this._updateClock();
      // Align to the next minute boundary instead of waking the WebProcess
      // every second.  The clock keeps displaying HH:MM, so a minute cadence is
      // the exact resolution it needs.
      const tick = () => {
        if (this.locked && !this._displayOff()) this._updateClock();
        const now = new Date();
        const delay = Math.max(1000, 60000 - (now.getSeconds() * 1000 + now.getMilliseconds()));
        this._clockTimer = global.setTimeout(tick, delay);
      };
      const now = new Date();
      this._clockTimer = global.setTimeout(tick,
        Math.max(1000, 60000 - (now.getSeconds() * 1000 + now.getMilliseconds())));
    }

    _acceptBattery(level, charging, status) {
      const n = Number(level);
      if (!Number.isFinite(n) || n < 0 || n > 100) return false;
      const next = Math.round(n);
      const st = String(status == null ? '' : status).trim().toLowerCase();
      const prev = this.batteryLevel;

      if (next === 0) {
        /* "Full" can never truthfully be 0%.  A charging/known-good pack also
           needs three consecutive zero samples before the UI believes it, so a
           one-sample fuel-gauge reset cannot paint 0%. */
        if (st === 'full') { this._batteryZeroCount = 0; return false; }
        if (prev !== null && prev >= 5) {
          this._batteryZeroCount++;
          if (this._batteryZeroCount < 3) return false;
        }
      } else {
        this._batteryZeroCount = 0;
      }

      /* A confirmed zero (three samples) is already debounced; do not demand
         a fourth sample from the separate large-swing guard. */
      const zeroConfirmed = next === 0 && (prev === null || prev < 5 || this._batteryZeroCount >= 3);
      if (!zeroConfirmed && prev !== null && next !== prev && Math.abs(next - prev) > 30) {
        if (this._batteryBigCandidate === next) this._batteryBigCount++;
        else { this._batteryBigCandidate = next; this._batteryBigCount = 1; }
        if (this._batteryBigCount < 2) return false;
      } else {
        this._batteryBigCandidate = null;
        this._batteryBigCount = 0;
      }

      this.batteryLevel = next;
      this.batteryCharging = !!charging || st === 'charging' || st === 'full';
      this.batteryStatus = st;
      return true;
    }

    _paintBattery() {
      if (!this.batteryEl) return;
      const shown = Number.isFinite(this.batteryLevel) ? Math.round(this.batteryLevel) : null;
      const glyph = this.batteryCharging ? '⚡ ' : '';
      const text = glyph + (shown === null ? '—' : shown + '%');
      if (this.batteryText === text) return; /* no DOM write, no repaint */
      this.batteryText = text;
      this.batteryEl.textContent = text;
    }

    _readBatteryFromHost() {
      const host = global.NuxelHost;
      if (!host || !host.available || typeof host.statusRead !== 'function') {
        return global.Promise.resolve(null);
      }
      return global.Promise.all([
        global.Promise.resolve(host.statusRead('battery-capacity')),
        global.Promise.resolve(host.statusRead('battery-status')),
      ]).then((readings) => {
        const cap = readings[0] || {};
        const st = readings[1] || {};
        const raw = String(cap.text == null ? '' : cap.text).trim();
        if (cap.ok !== true || !raw) return null;
        const m = raw.match(/([-+]?\d+(?:\.\d+)?)/);
        if (!m) return null;
        const level = Number(m[1]);
        if (!Number.isFinite(level) || level < 0 || level > 100) return null;
        const status = String(st.text == null ? '' : st.text).trim();
        return { level: level, status: status, charging: status.toLowerCase() === 'charging' };
      }).catch(() => null);
    }

    _readBatteryFromBridge() {
      try {
        if (typeof bridge !== 'undefined' && bridge && typeof bridge.getPhoneStatus === 'function') {
          return global.Promise.resolve(bridge.getPhoneStatus()).then((phone) => {
            const bat = phone && phone.battery;
            if (!bat || bat.available === false || bat.level == null) return null;
            const level = Number(bat.level);
            if (!Number.isFinite(level) || level < 0 || level > 100) return null;
            return { level: level, status: bat.charging ? 'charging' : '', charging: !!bat.charging };
          }).catch(() => null);
        }
      } catch (e) { /* bridge is optional */ }
      return global.Promise.resolve(null);
    }

    _updateBattery() {
      if (!this.locked || !this.batteryEl || this._displayOff() || this._batteryInFlight) return;
      this._batteryInFlight = true;
      const finish = (reading) => {
        if (reading) this._acceptBattery(reading.level, reading.charging, reading.status);
        this._paintBattery();
        this._batteryInFlight = false;
      };
      const host = global.NuxelHost;
      const hostReady = host && host.available && typeof host.statusRead === 'function';
      if (hostReady) {
        return this._readBatteryFromHost().then((reading) => {
          if (reading) { finish(reading); return; }
          return this._readBatteryFromBridge().then(finish, () => finish(null));
        }, () => this._readBatteryFromBridge().then(finish, () => finish(null)));
      }
      return this._readBatteryFromBridge().then(finish, () => finish(null));
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

    /* Charger/LPM boot detection.  The state file is append-only and the touch
       arming service logs NO_TOUCH_DEVICE on every retry when the kernel did not
       bind sec_ts; a successful arming ends with ARMED_OK.  We only react to the
       last line, so an old boot's receipt can never create a false warning. */
    _readTouchState() {
      const host = global.NuxelHost;
      if (!host || !host.available || typeof host.statusRead !== 'function') {
        return global.Promise.resolve(null);
      }
      return global.Promise.resolve(host.statusRead('touch-arm-state')).then((r) => {
        if (!r || r.ok !== true) return null;
        return String(r.text == null ? '' : r.text);
      }).catch(() => null);
    }

    _updateTouchWarning() {
      if (!this.locked || !this.touchWarningEl || this._touchInFlight) return;
      this._touchInFlight = true;
      this._readTouchState().then((text) => {
        this._touchInFlight = false;
        if (text === null) return; /* no evidence: never invent a warning */
        const lines = text.split(/\r?\n/).filter((line) => line.trim().length);
        const last = lines.length ? lines[lines.length - 1].trim() : '';
        const noTouch = /NO_TOUCH_DEVICE|SCAN_FAIL|ARM_OPEN_FAIL/.test(last);
        const armed = /ARMED_OK/.test(last);
        const show = noTouch && !armed;
        this.touchWarningEl.hidden = !show;
        try { this.touchWarningEl.classList.toggle('visible', show); } catch (e) {}
        if (show && this.touchWarningDetailEl) {
          this.touchWarningDetailEl.textContent =
            'Charging-mode boot: unplug the charger, then hold POWER to restart.';
        }
        this._trace('touch-warning show=' + (show ? 1 : 0) + ' last=' + last.slice(0, 96));
      }, () => { this._touchInFlight = false; });
    }

    _startTouchWarning() {
      this._updateTouchWarning();
      if (this._touchTimer) return;
      this._touchTimer = global.setInterval(() => {
        if (this.locked) this._updateTouchWarning();
      }, 10000);
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
