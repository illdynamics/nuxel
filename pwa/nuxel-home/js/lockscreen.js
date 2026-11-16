/* Nuxel A45.1 Penguin Lockscreen — swipe the actual nuxel-lockhead.png upward
 * to unlock.
 *
 * A84: the lockhead is ALWAYS on the glass, in every mode.
 *   swipe / unlock  swipe up anywhere in the lower band -> directly unlocked.
 *   pin             swipe/tap the lockhead -> numeric keypad panel.
 *   pattern         swipe/tap the lockhead -> 9-dot matrix (centre of glass)
 *                   with a PIN button fallback.
 *   fingerprint     swipe/tap the lockhead -> scanner surface with a PIN
 *                   button; with no working matcher it goes to the PIN screen.
 * With the panel closed the swipe travels with the finger; crossing the
 * threshold on top of the credential panel swallows that contact so the
 * keypad never receives a stray tap.  This is the real drag state machine:
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

  const VERSION = 'v0.8.6-beta';
  const WALLPAPER = { w: 768, h: 1376 };
  /* The illustrated penguin's approximate opaque bounds in wallpaper pixels,
     measured from the shipped asset.  Only the vertical extent matters here:
     the lockhead must land below PENGUIN_BOTTOM_Y, and the scheduler penguins
     (timer over the illustration, alarm between illustration and handle) are
     measured from these same constants rather than hardcoded viewport px. */
  const PENGUIN_TOP_Y = 470;
  const PENGUIN_BOTTOM_Y = 990;
  const PENGUIN_CENTER_Y = Math.round((PENGUIN_TOP_Y + PENGUIN_BOTTOM_Y) / 2);
  const ALARM_GAP = 12;        /* logical px below the wallpaper penguin */
  const MIN_SPACING = 32;      /* logical px between the penguin and the handle */
  const THRESHOLD_FRACTION = 0.22; /* of viewport height, per mission 11 */
  const DRAG_SLOP = 4;         /* px before a contact is a drag */
  const SAFE_TOP = 24;         /* px of usable travel reserved above the handle */
  const RETURN_MS = 160;       /* snap-back animation (snappier) */
  const DISMISS_MS = 70;       /* accepted unlock: one short acknowledgement */
  const DOCK_BOTTOM = 26;      /* px between the docked lockhead and the edge */
  const PANEL_DISMISS_SWIPE = 96; /* downward swipe (panel open) closes it */

  function modeLabel(mode) {
    if (mode === 'pin') return 'PIN keypad';
    if (mode === 'pattern') return 'pattern';
    if (mode === 'fingerprint') return 'fingerprint';
    return 'unlock';
  }

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
      this.mode = 'swipe';
      this.panelOpen = false;
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
      this._initAuth();
      this._positionHandle();
      try {
        document.addEventListener('nuxel:display-on', () => {
          this._updateClock();
          this._updateBattery();
          this._updateTouchWarning();
        });
      } catch (e) { /* observation only */ }
    }

    /* A80 credential surface: pattern / PIN / fingerprint overlays.  The swipe
       penguin is only the unlock gesture in swipe mode; in any credentialed
       mode it is removed from the glass and the credential UI takes over. */
    _initAuth() {
      if (typeof global.NuxelLockscreenAuth !== 'function') {
        this._trace('auth-init-missing: NuxelLockscreenAuth=' + typeof global.NuxelLockscreenAuth);
        return;
      }
      try {
        this.auth = new global.NuxelLockscreenAuth({
          onUnlock: (request) => {
            const controller = global.nuxel;
            if (controller && typeof controller.completeCredentialUnlock === 'function') {
              return controller.completeCredentialUnlock(this, request);
            }
            return { ok: false, error: 'no-authorized-controller' };
          },
          onSwipeMode: () => this._setSwipeAffordance(true),
          /* The lockhead owns the glass in every mode; these callbacks just
             re-dock it and remember whether the credential panel is open. */
          onPanelMode: (open, mode) => this._onPanelMode(open, mode),
          onModeChange: (mode) => this._onModeChange(mode),
        });
      } catch (err) {
        this.auth = null;
        this._trace('auth-init-failed ' + (err && err.message ? err.message : err));
      }
    }

    _setSwipeAffordance(visible) {
      /* A87: the lockhead is shown exactly where the owner needs it.
         * swipe mode              -> always visible (it IS the unlock gesture)
         * credential, panel closed -> visible (swipe/tap it to open the panel)
         * credential, panel OPEN   -> hidden.  The owner asked for no lockhead
           under the PIN prompt, and an invisible docked handle also stopped
           stray touches near the bottom edge from being swallowed as a swipe. */
      if (this.panelOpen && this.mode && this.mode !== 'swipe') visible = false;
      else visible = true;
      if (this.wrap) {
        this.wrap.hidden = !visible;
        this.wrap.setAttribute('aria-hidden', visible ? 'false' : 'true');
        try { this.wrap.inert = !visible; } catch (e) { /* older engines */ }
      }
      if (this.hint) this.hint.hidden = !visible;
      /* There is deliberately NO "Set up pattern / PIN" entry point on the lock
         screen any more: credentials are set/changed in Settings -> Security
         only.  The element remains in the DOM (hidden, disabled, inert) for
         stale callers, and the auth surface never paints it. */
      const sw = document.getElementById('lockscreen-auth-switch');
      if (sw) sw.hidden = true;
    }

    /* A84: keep the lockhead on the glass and dock it for the current mode.
       A credential mode may start its panel OPEN (fingerprint with no
       matcher goes straight to PIN, Settings may open a panel), so the dock
       must honour the panel state rather than assume "closed". */
    _applyHandleDock() {
      if (!this.wrap || !this.el) return;
      const panel = !!(this.panelOpen && this.mode && this.mode !== 'swipe');
      this.el.classList.toggle('lockscreen-panel-open', panel);
      /* A87: with a credential panel OPEN the lockhead is not painted at all
         (the owner explicitly does not want it below the PIN prompt).  Closed
         and swipe locks always show it. */
      const showHandle = !panel;
      this.wrap.hidden = !showHandle;
      if (showHandle) this.wrap.removeAttribute('aria-hidden');
      else this.wrap.setAttribute('aria-hidden', 'true');
      try {
        this.wrap.inert = !showHandle;
        if (this.handle) this.handle.inert = !showHandle;
      } catch (e) { /* older engines */ }
      if (this.handle) {
        if (showHandle) this.handle.removeAttribute('aria-hidden');
        else this.handle.setAttribute('aria-hidden', 'true');
      }
      /* Resting position depends on the panel: closed -> the classic lower
         band; open -> the bottom dock below the credential panel. */
      this._positionHandle();
      if (this.hint) {
        const text = panel ? '' : (this.mode === 'swipe'
          ? 'swipe up to unlock'
          : 'tap the lockhead to open ' + modeLabel(this.mode));
        this.hint.hidden = !text;
        this.hint.textContent = text;
      }
      try {
        this.handle.setAttribute('aria-label', panel
          ? 'Credential panel open'
          : (this.mode === 'swipe' ? 'Drag the penguin upward to unlock'
                                   : 'Tap/put your finger on the penguin to open ' + modeLabel(this.mode)));
      } catch (e) { /* older engines */ }
      try { this._previewPanelOverlap(); } catch (e) { /* observation only */ }
    }

    _onModeChange(mode) {
      const previous = this.mode;
      this.mode = mode || 'swipe';
      /* The panel owner's own onPanelMode callback carries the authoritative
         panel state; reading isPanelOpen() here raced it (a new panel reported
         "closed" because this ran before the surface was painted). */
      if (!this.auth) this.panelOpen = false;
      this._trace('mode=' + this.mode + ' panel=' + (this.panelOpen ? 1 : 0) +
                  ' direct=' + (this.mode === 'swipe' ? 1 : 0));
      this._applyHandleDock();
      /* A credential panel that just closed/changed could have a stale gesture
         in flight; never carry one across a mode change. */
      if (this.gesture) this._cancelGesture('mode-change');
      /* A88: when the panel is closed and the OWNER changes the method (e.g.
         Settings -> swipe only / PIN), the live lock must be re-armed in that
         method right away.  Without this the lock provider stayed unlocked
         from before the switch, so only the next 4 s reconcile or a reboot
         brought the lockhead back. */
      if (!this.panelOpen && previous && previous !== this.mode && this.locked) {
        try {
          if (this.auth && typeof this.auth.refresh === 'function') {
            Promise.resolve(this.auth.refresh()).catch(() => null);
          }
        } catch (e) { /* observation only */ }
        this._trace('mode-rearmed ' + previous + '->' + this.mode);
      }
    }

    _onPanelMode(open, mode) {
      this._trace('PANEL-CALL ' + open + ' ' + mode);
      this.mode = mode || this.mode;
      this.panelOpen = !!open;
      this._trace('panel=' + (this.panelOpen ? 'open' : 'closed') + ' mode=' + this.mode + ' was=' + this.panelOpen);
      /* evidence only: what the panel-owner sees after this callback */
      this._trace('panel-check open=' + this.panelOpen);
      this._applyHandleDock();
    }

    /* A swipe starting on the penguin while the panel is open does nothing (the
       touch belongs to the panel); while it is closed it opens the credential
       panel instead of unlocking. */
    _openCredentialPanel() {
      if (!this.auth || !this.auth.openPanel) return false;
      const opened = this.auth.openPanel() === true;
      this._trace('panel=opened-by-lockhead opened=' + (opened ? 1 : 0) + ' mode=' + this.mode +
                  ' sw=' + (this.auth.effectiveMode || '-') + ' panelFlag=' + (this.panelOpen ? 1 : 0));
      return opened;
    }

    /* Ask the credential surface to render the current authoritative mode.
       Returns a promise so callers can order it after the lock state write. */
    _syncAuthMode() {
      if (!this.auth) return Promise.resolve(null);
      return Promise.resolve(this.auth.show()).then((st) => {
        this._trace('auth-sync mode=' + ((st && st.mode) || '-') +
                    ' effective=' + (this.auth.effectiveMode || '-') +
                    ' visible=' + (this.auth.isVisible ? (this.auth.isVisible() ? 1 : 0) : 'n/a'));
        /* A83: the auth surface's effective mode (the one actually painted) is
           decided inside auth.show(); never re-derive it from a status object
           that may be a non-answer, or the caller would reveal the swipe handle
           over a live keypad. */
        const answeredMode = (st && st.success !== false && st.mode) ? st.mode : '';
        const mode = this.auth.effectiveMode || answeredMode || (st && st.mode) ||
          (this.mode && this.mode !== 'swipe' ? this.mode : 'pin');
        this.mode = mode;
        if (this.auth) this.panelOpen = !!(this.auth.isPanelOpen && this.auth.isPanelOpen());
        this._setSwipeAffordance(true);
        this._applyHandleDock();
        return st;
      });
    }

    /* Lock-screen credential setup was removed: a pattern/PIN may only be set
       from Settings -> Security.  These stay as explicit, honest refusals so a
       stale caller (or a console) cannot reopen a setup sheet on the glass. */
    openAuthSetup() { return { ok: false, error: 'set-credential-in-settings' }; }

    requestPinFallback() {
      if (this.auth) this.auth.showPinFallback();
    }

    openPatternSetup() { return this.openAuthSetup(); }

    authVisible() { return !!(this.auth && this.auth.isVisible()); }

    /* The S10+ underside scanner sits where the docked lockhead rests.  A
       finger pressed there in fingerprint mode must behave like the
       fingerprint button: open the scanner panel, or go straight to the PIN
       screen when no matcher is enrolled/ready. */
    handleFingerprintPress() {
      if (!this.locked || !this.auth || this.mode !== 'fingerprint') return false;
      try { return this.auth.openPanel() === true; } catch (e) { return false; }
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

    _positionClockLanes(penguinBottomCss, handleTop) {
      if (!this.el) return;
      const penguinSize = Math.max(72, Math.min(104, (global.innerWidth || 360) * 0.17));
      const timerCenterY = this._coverCssY(PENGUIN_CENTER_Y);
      const alarmCenterY = Math.min(
        Math.max(penguinBottomCss + ALARM_GAP + penguinSize / 2, timerCenterY + penguinSize),
        handleTop - penguinSize / 2 - ALARM_GAP);
      this.el.style.setProperty('--lockscreen-timer-center-y', Math.round(timerCenterY) + 'px');
      this.el.style.setProperty('--lockscreen-alarm-center-y', Math.round(alarmCenterY) + 'px');
      this._trace('lanes timerY=' + Math.round(timerCenterY) + ' alarmY=' + Math.round(alarmCenterY) +
                  ' penguinBottom=' + Math.round(penguinBottomCss) + ' handleTop=' + Math.round(handleTop));
    }

    _positionHandle() {
      /* A84: the lockhead is always on the glass.
         * swipe / closed panel -> the classic resting place in the lower band
           (below the illustrated penguin, above the bottom edge).
         * credential panel open -> docked at the BOTTOM, below the panel, so it
           can never overlap the keypad/matrix (the a83 "Unlock does nothing"
           cause) and the panel keeps the centre of the glass. */
      if (this._reducedMotion === undefined) this._reducedMotion = false;
      const vw = global.innerWidth || 360;
      const vh = global.innerHeight || 760;
      const handleSize = Math.max(96, Math.min(124, vw * 0.3));
      const penguinSize = Math.max(72, Math.min(104, vw * 0.17));
      const penguinBottomCss = this._coverCssY(PENGUIN_BOTTOM_Y);
      const restingTop = Math.min(
        Math.max(penguinBottomCss + ALARM_GAP + penguinSize + MIN_SPACING, vh * 0.62),
        vh - handleSize - 24);
      this.el.style.setProperty('--lockscreen-scanner-top', restingTop + 'px');
      this.el.style.setProperty('--lockscreen-scanner-size', handleSize + 'px');
      let desiredTop;
      if (this.panelOpen && this.mode && this.mode !== 'swipe') {
        /* A87: parked at the bottom.  The handle is hidden while the panel is
           open; this position is only a fallback if it is ever revealed. */
        desiredTop = vh - handleSize - DOCK_BOTTOM;
        if (desiredTop < vh * 0.5) desiredTop = vh * 0.5;
      } else {
        /* Reserve a lane for the alarm penguin between the illustrated penguin
           and the lockhead, so all three (timer, alarm, handle) coexist without
           overlap and the handle never covers the illustration. */
        const alarmBottomCss = penguinBottomCss + ALARM_GAP + penguinSize;
        desiredTop = Math.min(
          Math.max(alarmBottomCss + MIN_SPACING, vh * 0.62),
          vh - handleSize - 24);
      }
      const docked = !!(this.panelOpen && this.mode && this.mode !== 'swipe');
      const size = docked ? Math.min(handleSize, 84) : handleSize;
      this.handle.style.width = size + 'px';
      this.handle.style.height = size + 'px';
      this.wrap.style.top = desiredTop + 'px';
      this.wrap.style.bottom = 'auto';
      this.baseTop = desiredTop;
      this.restY = 0;
      if (docked) this.el.style.setProperty('--lockscreen-handle-dock-y', Math.round(desiredTop) + 'px');
      this._positionClockLanes(penguinBottomCss, docked ? vh * 0.62 : desiredTop);
      this._trace('position top=' + Math.round(desiredTop) + ' penguinBottom=' + Math.round(penguinBottomCss) +
                  ' vh=' + vh + ' handle=' + size + ' docked=' + (docked ? 1 : 0));
    }

    /* Root-console evidence: where is the credential panel and does the docked
       lockhead overlap any of its hit targets?  (No secrets, geometry only.) */
    _previewPanelOverlap() {
      if (!this.el || typeof this.el.getBoundingClientRect !== 'function') return;
      const hb = this.handle.getBoundingClientRect();
      const targets = ['lockscreen-pinpad', 'lockscreen-pattern', 'lockscreen-fingerprint',
                       'lockscreen-pin-fallback'];
      const hits = targets.filter((id) => {
        const el = document.getElementById(id);
        if (!el || el.hidden) return false;
        const r = el.getBoundingClientRect();
        return !(r.right <= hb.left || r.left >= hb.right || r.bottom <= hb.top || r.top >= hb.bottom);
      });
      this.panelOverlap = hits;
      if (this.panelOpen) this._trace('panel-overlap=[' + hits.join(',') + ']');
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

    _targetInCredential(target) {
      if (!target || typeof target.closest !== 'function') return false;
      try {
        const el = target.closest('#lockscreen-auth');
        return !!(el && !el.hidden);
      } catch (e) { return false; }
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
          /* A84/A83: a touch that starts on the credential panel is a key/dot
             press, never a swipe on the lockhead underneath the glass. */
          if (this.panelOpen && e.target.closest('#lockscreen-auth')) return;
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
        /* A84 routing, decided from the state at contact time:
           'unlock'     swipe mode             -> unlock directly
           'open-panel' credential, panel closed -> open the credential panel
           'dismiss'    panel open, lockhead     -> close the panel
        */
        route: this.mode === 'swipe' ? 'unlock' : (this.panelOpen ? 'dismiss' : 'open-panel'),
        panelOpen: this.panelOpen,
        /* Did this contact begin over the credential panel?  Crossing the
           threshold over the panel must swallow the contact (_pointerMove). */
        onCredential: this._targetInCredential(e && e.target),
        swallow: false,
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
      /* A84: a contact that started OUTSIDE the credential panel (on the
         lockhead or in the lower band) and now travels over the open panel is
         swallowed at the threshold: the keypad must never receive a stray
         tap/click from an unlock swipe, while the swipe itself still counts. */
      if (this.panelOpen && !g.onCredential && e && Number.isFinite(e.clientX) &&
          Number.isFinite(e.clientY) && this._crossesPanel(e.clientX, e.clientY)) {
        g.swallow = true;
      }
      /* The handle follows the finger in real time.  This is presentation only;
         the authoritative distance is g.distance above. */
      const clamped = Math.max(0, Math.min(dy, g.threshold + 120));
      this.handle.style.transform = 'translateY(' + (-clamped) + 'px)';
    }

    _crossesPanel(x, y) {
      const box = document.getElementById('lockscreen-auth');
      if (!box || box.hidden || typeof box.getBoundingClientRect !== 'function') return false;
      const r = box.getBoundingClientRect();
      if (!r || !r.width || !r.height) return false;
      return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
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
      /* A84: route at RELEASE.  _pointerDown's route is only a snapshot taken
         before any panel opened; once this contact has opened a panel (its own
         lockhead swipe) a downward continuation must close it, not re-open. */
      if (this.panelOpen && g.route === 'open-panel' && this.mode !== 'swipe') {
        g.route = 'dismiss';
        this._trace('gesture=route-dismiss id=' + g.id);
      }
      if (g.swallow) {
        /* Never synthesise unlock: the gesture was consumed by the panel. */
        g.requested = true;
        g.consumed = true;
        this._trace('gesture=swallow id=' + g.id + ' reason=credential-panel');
      }
      if (g.route === 'dismiss') {
        /* Panel open and the docked lockhead was swiped down: close the panel
           (same feel as a sheet).  A plain tap returns to rest. */
        if (dy <= -PANEL_DISMISS_SWIPE) {
          if (this.auth && this.auth.closePanel) {
            /* closePanel() notifies onPanelMode -> _onPanelMode, which clears
               this.panelOpen and redocks the lockhead.  Without it only the
               local flag changed and the panel stayed painted. */
            try { this.auth.closePanel(); } catch (e) { /* ignore */ }
          }
          if (this.panelOpen) {
            this.panelOpen = false;
            this._applyHandleDock();
          }
        }
        this._returnToRest('panel-lockhead');
        return;
      }
      if (reached) {
        if (g.route === 'open-panel') {
          /* Credential mode, panel closed: the lockhead swipe opens the panel
             (it never unlocks without the credential). */
          this._cancelSwipePresentation(g);
          const opened = this._openCredentialPanel();
          this._trace('gesture=open-panel id=' + g.id + ' up=' + Math.round(dy) +
                      ' opened=' + (opened ? 1 : 0));
          this._returnToRest('panel-open');
          return;
        }
        this._requestUnlock(g);
      } else {
        /* A tap on the lockhead in a credential mode also opens the panel
           (the owner may not know the upward swipe). */
        if (g.route === 'open-panel' && Math.abs(dy) < DRAG_SLOP) {
          const opened = this._openCredentialPanel();
          this._trace('gesture=tap-open id=' + g.id + ' opened=' + (opened ? 1 : 0));
          this._returnToRest('panel-open-tap');
          return;
        }
        this._returnToRest('release-below-threshold');
      }
    }

    _cancelSwipePresentation(g) {
      if (!this.handle) return;
      this.handle.classList.remove('grabbed');
      this.handle.classList.remove('armed');
      this.handle.classList.remove('unlocking');
      this.handle.style.transition = 'transform .16s ease-out';
      this.handle.style.transform = 'translateY(0)';
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
        /* A84: 'swipe' = unlock directly on this gesture.  Anything else means
           Home already opened a credential path and this exact gesture is the
           proof that opened it (never a second unlock prompt). */
        route: g.route || 'unlock',
        direct: (g.route || 'unlock') === 'unlock',
        mode: this.mode,
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
      if (!g.released || !g.requested || g.consumed) return false;
      const route = (request && request.route) || 'unlock';
      if (route === 'unlock' && !g.reached) return false;
      if (route === 'unlock' && !(Number(request.distance) >= Number(request.threshold))) return false;
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
      /* A80: the authoritative lock mode decides whether the penguin gesture
         or a credential surface is presented.  Fail closed: if the bridge
         cannot answer, keep the swipe handle (it still re-verifies). */
      Promise.resolve(this._syncAuthMode()).catch(() => {
        /* A86: a failed sync keeps the last confirmed credential mode (or PIN);
           showing the swipe penguin here unlocked a credential-mode phone. */
        if (this.mode !== 'swipe') this.mode = this.mode || 'pin';
        else this.mode = 'pin';
        this.panelOpen = false;
        this._setSwipeAffordance(true);
        this._applyHandleDock();
      });
      this._wiggleOnce(this._displayOff() ? 2500 : 900);
      try { document.dispatchEvent(new CustomEvent('nuxel:lockscreen-shown')); } catch (e) {}
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
      this.panelOpen = false;
      try { document.body.classList.remove('lockscreen-active'); } catch (e) {}
      try { this.el.classList.remove('lockscreen-panel-open'); } catch (e) {}
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
      if (this.auth) { try { this.auth.hide(); } catch (e) {} }
      this._setSwipeAffordance(true);
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

    /* Called when Settings changes the lock mode while the session is locked
       (or immediately after the credential is stored). */
    refreshAuthMode() {
      if (!this.locked) return Promise.resolve(null);
      return this._syncAuthMode();
    }

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
