/* Nuxel A45 Penguin Lockscreen — swipe the actual nuxel-lockhead.png upward to
 * unlock.  This is a real drag state machine:
 *
 *   IDLE -> TOUCH_CAPTURED -> DRAGGING -> THRESHOLD_REACHED -> UNLOCKING -> UNLOCKED
 *   DRAGGING -> CANCELLED -> RETURN_TO_REST -> IDLE
 *
 * The lockhead follows the finger (pointer capture), snaps back on an incomplete
 * drag, and only unlocks after crossing an upward threshold.  It is placed BELOW
 * the penguin already illustrated in nuxel-lockscreen.jpg (cover-crop aware), so
 * the resting handle never covers the wallpaper penguin.
 */
(function () {
  'use strict';

  const WALLPAPER = { w: 768, h: 1376 };
  /* The illustrated penguin's approximate opaque bounds in wallpaper pixels,
     measured from the shipped asset.  Only the vertical extent matters here:
     the lockhead must land below PENGUIN_BOTTOM_Y. */
  const PENGUIN_BOTTOM_Y = 990;
  const MIN_SPACING = 32;      /* logical px between the penguin and the handle */
  const THRESHOLD_FRACTION = 0.22; /* of viewport height, per mission 11 */

  class Lockscreen {
    constructor() {
      this.el = document.getElementById('lockscreen');
      this.handle = document.getElementById('lockscreen-handle');
      this.wrap = document.getElementById('lockscreen-handle-wrap');
      this.hint = document.getElementById('lockscreen-hint');
      this.timeEl = document.getElementById('lockscreen-time');
      this.dateEl = document.getElementById('lockscreen-date');
      this.batteryEl = document.getElementById('lockscreen-battery');
      this.locked = false;
      this.state = 'IDLE';
      this.startY = 0;
      this.currentY = 0;
      this.restY = 0;
      this.unlocked = false;

      if (!this.el || !this.handle) return;
      this._bindHandle();
      this._startClock();
      this._startBattery();
      this._positionHandle();
    }

    /* Map a wallpaper pixel coordinate to CSS under background-size: cover. */
    _coverCssY(imageY) {
      const vw = window.innerWidth || 360;
      const vh = window.innerHeight || 760;
      const scale = Math.max(vw / WALLPAPER.w, vh / WALLPAPER.h);
      const scaledH = WALLPAPER.h * scale;
      const cropY = Math.max(0, (scaledH - vh) / 2);
      return imageY * scale - cropY;
    }

    _positionHandle() {
      const vw = window.innerWidth || 360;
      const vh = window.innerHeight || 760;
      const handleSize = Math.max(96, Math.min(124, vw * 0.3));
      const penguinBottomCss = this._coverCssY(PENGUIN_BOTTOM_Y);
      /* Rest the handle clearly below the wallpaper penguin, with real spacing,
         while keeping it inside the visible lockscreen. */
      const desiredTop = Math.min(Math.max(penguinBottomCss + MIN_SPACING, vh * 0.62), vh - handleSize - 24);
      this.handle.style.width = handleSize + 'px';
      this.handle.style.height = handleSize + 'px';
      this.wrap.style.top = desiredTop + 'px';
      this.wrap.style.bottom = 'auto';
      this.restY = 0;
      this._trace('position top=' + Math.round(desiredTop) + ' penguinBottom=' + Math.round(penguinBottomCss) +
                  ' vh=' + vh + ' handle=' + handleSize);
    }

    _bindHandle() {
      const h = this.handle;
      h.addEventListener('pointerdown', (e) => {
        if (e.button !== undefined && e.button !== 0) return;
        this.state = 'TOUCH_CAPTURED';
        this.startY = e.clientY;
        this.currentY = e.clientY;
        try { h.setPointerCapture(e.pointerId); } catch (err) { /* best effort */ }
        h.classList.add('grabbed');
        this._trace('state=' + this.state);
      });
      h.addEventListener('pointermove', (e) => {
        if (this.state !== 'TOUCH_CAPTURED' && this.state !== 'DRAGGING' &&
            this.state !== 'THRESHOLD_REACHED') return;
        this.currentY = e.clientY;
        const dy = this.startY - this.currentY;   // upward travel, positive
        const threshold = window.innerHeight * THRESHOLD_FRACTION;
        if (dy > 4) this.state = 'DRAGGING';
        if (dy >= threshold) this.state = 'THRESHOLD_REACHED';
        /* The handle follows the finger in real time. */
        const clamped = Math.max(0, Math.min(dy, threshold + 120));
        h.style.transform = 'translateY(' + (-clamped) + 'px)';
      });
      const finish = (e) => {
        if (this.state !== 'TOUCH_CAPTURED' && this.state !== 'DRAGGING' &&
            this.state !== 'THRESHOLD_REACHED') return;
        const threshold = window.innerHeight * THRESHOLD_FRACTION;
        const dy = this.startY - this.currentY;
        const reached = dy >= threshold;
        this._trace('release state=' + this.state + ' dy=' + Math.round(dy) + ' reached=' + reached);
        if (reached && this.state === 'THRESHOLD_REACHED') {
          this._unlock();
        } else {
          this.state = 'CANCELLED';
          this._trace('state=CANCELLED');
          h.style.transition = 'transform .22s ease-out';
          h.style.transform = 'translateY(0)';
          h.classList.remove('grabbed');
          setTimeout(() => { h.style.transition = ''; this.state = 'IDLE'; this._trace('state=IDLE'); }, 240);
        }
      };
      h.addEventListener('pointerup', finish);
      h.addEventListener('pointercancel', () => { this._cancelDrag(); });
      h.addEventListener('lostpointercapture', () => { if (this.state === 'DRAGGING' || this.state === 'THRESHOLD_REACHED') this._cancelDrag(); });
    }

    _cancelDrag() {
      if (this.state === 'UNLOCKING' || this.state === 'UNLOCKED') return;
      this.state = 'CANCELLED';
      this.handle.classList.remove('grabbed');
      this.handle.style.transition = 'transform .22s ease-out';
      this.handle.style.transform = 'translateY(0)';
      setTimeout(() => { this.handle.style.transition = ''; this.state = 'IDLE'; }, 240);
    }

    _unlock() {
      if (this.state === 'UNLOCKING' || this.state === 'UNLOCKED') return;
      this.state = 'UNLOCKING';
      this._trace('state=UNLOCKING');
      this.handle.classList.remove('grabbed');
      this.handle.classList.add('unlocking');
      this._buzz();
      if (global.NuxelHost && NuxelHost.available) {
        try { NuxelHost.action('unlock'); } catch (e) { /* best effort */ }
      }
      setTimeout(() => { this.hide(); }, 280);
    }

    show(reason) {
      if (!this.el) return;
      this.el.hidden = false;
      this.locked = true;
      this.unlocked = false;
      this.state = 'IDLE';
      this.handle.classList.remove('unlocking');
      this.handle.style.transform = '';
      this._positionHandle();
      this._updateClock();
      this._updateBattery();
      this._trace('show reason=' + (reason || 'unknown'));
    }

    hide() {
      if (!this.el) return;
      this.el.hidden = true;
      this.locked = false;
      this.unlocked = true;
      this.state = 'UNLOCKED';
      this._trace('hide state=UNLOCKED');
    }

    isLocked() { return this.locked; }

    _buzz() {
      if (global.NuxelHost && NuxelHost.available) {
        try { NuxelHost.action('haptics-navigation'); } catch (e) { /* best effort */ }
      } else if (global.navigator && navigator.vibrate) {
        try { navigator.vibrate(14); } catch (e) { /* best effort */ }
      }
    }

    _updateClock() {
      if (!this.timeEl || !this.dateEl) return;
      const d = new Date();
      this.timeEl.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const opts = { weekday: 'long', month: 'long', day: 'numeric' };
      this.dateEl.textContent = d.toLocaleDateString([], opts);
    }

    _startClock() {
      this._updateClock();
      setInterval(() => this._updateClock(), 1000);
    }

    _updateBattery() {
      if (!this.batteryEl) return;
      let pct = '—';
      let charging = false;
      if (global.NuxelHost && NuxelHost.available) {
        try {
          NuxelHost.statusRead('battery-state').then((r) => {
            const t = (r && (r.text || r.value)) || '';
            const m = t.match(/percent[=:]\s*(\d+)/i);
            if (m) pct = m[1];
            charging = /charging|charging=1/i.test(t);
            this.batteryEl.textContent = (charging ? '⚡ ' : '') + pct + '%';
          }).catch(() => {});
        } catch (e) { /* best effort */ }
      }
      this.batteryEl.textContent = (charging ? '⚡ ' : '') + pct + '%';
    }

    _startBattery() {
      this._updateBattery();
      setInterval(() => this._updateBattery(), 20000);
    }

    _trace(msg) {
      try {
        const diag = global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag;
        if (diag) diag.postMessage('LOCKS ' + msg);
      } catch (e) { /* observation only */ }
      try { console.log('[Lockscreen]', msg); } catch (e) {}
    }
  }

  window.NuxelLockscreen = Lockscreen;
})();
