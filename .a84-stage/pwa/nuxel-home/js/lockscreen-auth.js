/* Nuxel A80 — credential-aware lockscreen surface.
 *
 * Owns everything except the swipe penguin (kept in js/lockscreen.js):
 *
 *   pattern      a 3x3 matrix of small penguin lock-head dots; drag between
 *                dots to draw, with a live trail of what was drawn, then lift.
 *   pin          a numeric keypad (always reachable via the PIN button).
 *   fingerprint  /assets/nuxel-fingerprint.png placed exactly over the S10+
 *                under-display scanner, with a PIN fallback below it.
 *
 * Server truth is the root bridge (security_provider.py): the mode, the
 * verifier, the attempt policy and the locked flag all live there.  This file
 * never stores a secret and never decides a successful unlock by itself.
 *
 * Setup: a pattern must be drawn twice (identical) before any change is sent;
 * the bridge repeats that refusal server-side.  A fingerprint must first be
 * registered through the guarded enrollment ceremony (Vault required).
 */
(function (global) {
  'use strict';

  const VERSION = 'a84';
  const DOTS = 9;
  const PATTERN_DOT = [0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => ({
    x: 50 + (i % 3) * 100, y: 50 + Math.floor(i / 3) * 100,
  }));
  const MIN_PIN = 4;
  /* Master-password hint for the owner: the S10+ lockscreen PIN is the same
     four digits used twice (3838 -> 38383838).  Only a wrong-password error is
     annotated; the value is never sent anywhere and no attempt is made here. */
  const PIN_HINT = 'Hint: the Vault password can be your lockscreen PIN entered twice (e.g. 3838 → 38383838).';
  /* The S10+ scanner is the oval under the bottom third of the panel.  These
     proportions come from /sys/class/fingerprint/fingerprint/position
     (13.77,0.00,9.00,4.00,14.80,14.80,13.00,13.00,5.00) and match the area
     the artwork was drawn for. */
  const SCANNER = { left: 0.2, top: 0.78, width: 0.6, height: 0.2 };

  const $ = (id) => document.getElementById(id);
  const el = (id) => $(id);

  function bridgeCall(ns, verb, params) {
    const b = global.NuxelSecurityLock;
    if (b && typeof b.call === 'function') return b.call(ns, verb, params || {});
    const nb = global.NuxelBridge;
    if (nb && typeof nb.call === 'function') return nb.call(ns, verb, params || {});
    return Promise.resolve({ success: false, error: 'bridge_unreachable' });
  }

  function fingerprintStatus() {
    return bridgeCall('fingerprint', 'status', {});
  }
  function securityStatus() {
    return bridgeCall('security', 'status', {});
  }

  function buzz(ms) {
    try {
      const host = global.NuxelHost;
      if (host && host.available && typeof host.action === 'function') {
        host.action(ms > 10 ? 'haptics-error' : 'haptics-navigation');
      } else if (global.navigator && global.navigator.vibrate) {
        global.navigator.vibrate(ms || 12);
      }
    } catch (e) { /* feedback never blocks */ }
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  class LockscreenAuth {
    constructor(options) {
      options = options || {};
      this.el = el('lockscreen-auth');
      this.titleEl = el('lockscreen-auth-title');
      this.hintEl = el('lockscreen-auth-hint');
      this.errorEl = el('lockscreen-auth-error');
      this.patternEl = el('lockscreen-pattern');
      this.patternDots = el('lockscreen-pattern-dots');
      this.trail = el('lockscreen-pattern-trail');
      this.pinpad = el('lockscreen-pinpad');
      this.pinDisplay = el('lockscreen-pin-display');
      this.fpEl = el('lockscreen-fingerprint');
      this.fpStatus = el('lockscreen-fingerprint-status');
      this.fpRing = el('lockscreen-fingerprint-ring');
      this.fpArt = el('lockscreen-fingerprint-art');
      this.pinFallback = el('lockscreen-pin-fallback');
      this.onUnlock = options.onUnlock || null;
      this.onVault = options.onVault || null;
      this.onRequestPin = options.onRequestPin || null;

      /* No preview may override the hardware truth.  The fingerprint surface
         (artwork over the under-display scanner) is shown only when the bridge
         reports a READY secure provider.  On this handset no userspace matcher
         exists, so the lock screen states that plainly and the PIN below is
         the working path -- it never paints a scanner that cannot read. */
      this.preview = false;
      this.mode = 'swipe';
      this.effectiveMode = 'swipe';
      this.status = null;
      this.pin = '';
      this.sequence = [];
      this.drawing = false;
      this.pointerId = null;
      this.busy = false;
      this.setup = null;
      this._fpTimer = null;
      this._fpInFlight = false;
      if (!this.el) return;
      this._buildPattern();
      this._wirePattern();
      this._wirePin();
      this._wireFingerprint();
      this._wireFallback();
    }

    /* ------------------------------------------------------------- pattern */
    _penguinHeadSvg() {
      return '<img class="lockscreen-pattern-penguin" src="/assets/nuxel-lockhead.png?v=a81"'
        + ' alt="" draggable="false" aria-hidden="true">';
    }

    /* The matrix is a CSS grid (3 columns x 3 rows).  Each dot's real drawn
       centre is measured from its own box, and the trail SVG uses a 0..300
       viewBox, so the same two helpers give both pixel hit-testing and SVG
       coordinates on any screen size. */
    _dotElsFor(container) {
      if (!container) return [];
      return Array.prototype.slice.call(
        container.querySelectorAll('.lockscreen-pattern-dot'));
    }

    _makeDot(i, container) {
      const d = document.createElement('div');
      d.className = 'lockscreen-pattern-dot';
      d.dataset.dot = String(i);
      d.setAttribute('role', 'button');
      d.setAttribute('aria-label', 'Dot ' + (i + 1));
      d.innerHTML = this._penguinHeadSvg();
      container.appendChild(d);
      return d;
    }

    _buildPattern() {
      if (this.patternDots) {
        this.patternDots.innerHTML = '';
        this.dotEls = [];
        for (let i = 0; i < DOTS; i++) this.dotEls.push(this._makeDot(i, this.patternDots));
      }
    }

    /* SVG viewBox coordinate (0..300) for a dot's drawn centre. */
    _svgPoint(container, dotIndex) {
      const dots = this._dotElsFor(container);
      const box = container.getBoundingClientRect();
      const d = dots[dotIndex];
      if (!d || !box.width || !box.height) return [0, 0];
      const r = d.getBoundingClientRect();
      return [(r.left + r.width / 2 - box.left) / box.width * 300,
              (r.top + r.height / 2 - box.top) / box.height * 300];
    }

    _dotAtIn(container, ev) {
      if (!container) return -1;
      const box = container.getBoundingClientRect();
      if (!box.width || !box.height) return -1;
      const dots = this._dotElsFor(container);
      let best = -1;
      let bestDist = Infinity;
      for (let i = 0; i < dots.length; i++) {
        const r = dots[i].getBoundingClientRect();
        if (!r.width || !r.height) continue;
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        const dist = Math.hypot(ev.clientX - cx, ev.clientY - cy);
        /* A generous Android-style hit slop: half the dot plus a third of the
           dot again.  Dots are never closer than their own width. */
        if (dist <= r.width * 0.82 && dist < bestDist) { best = i; bestDist = dist; }
      }
      /* Nearest-dot fallback while the finger is inside the matrix: a drag
         that passes close to a dot still connects it, like Android. */
      if (best < 0) {
        for (let i = 0; i < dots.length; i++) {
          const r = dots[i].getBoundingClientRect();
          if (!r.width) continue;
          const dist = Math.hypot(ev.clientX - (r.left + r.width / 2),
                                  ev.clientY - (r.top + r.height / 2));
          if (dist <= r.width * 1.05 && dist < bestDist) { best = i; bestDist = dist; }
        }
      }
      return best;
    }

    _dotAt(ev) { return this._dotAtIn(this.patternEl, ev); }

    _drawTrail(points) {
      if (!this.trail) return;
      this.trail.setAttribute('points',
        points.map((p) => (Math.round(p[0] * 10) / 10) + ',' + (Math.round(p[1] * 10) / 10)).join(' '));
    }

    _paintSequence(container, list) {
      const dots = this._dotElsFor(container);
      dots.forEach((d) => d.classList.remove('active'));
      list.forEach((i) => { if (dots[i]) dots[i].classList.add('active'); });
      this._drawTrail(list.map((j) => this._svgPoint(container, j)));
    }

    _appendDot(i) {
      if (this.sequence.includes(i)) return;
      this.sequence.push(i);
      if (this.dotEls && this.dotEls[i]) this.dotEls[i].classList.add('active');
      buzz(8);
      this._drawTrail(this.sequence.map((j) => this._svgPoint(this.patternEl, j)));
    }

    /* Follow the finger between dots, exactly like the Android pattern trail:
       append the current position while the finger is inside the matrix. */
    _drawLiveTrail(ev) {
      if (!this.trail || !this.patternEl || !this.sequence.length) return;
      const box = this.patternEl.getBoundingClientRect();
      if (!box.width || !box.height) return;
      const x = Math.max(0, Math.min(300, (ev.clientX - box.left) / box.width * 300));
      const y = Math.max(0, Math.min(300, (ev.clientY - box.top) / box.height * 300));
      const pts = this.sequence.map((j) => this._svgPoint(this.patternEl, j));
      pts.push([x, y]);
      this._drawTrail(pts);
    }

    _resetPattern() {
      this.sequence = [];
      if (this.dotEls) this.dotEls.forEach((d) => d.classList.remove('active'));
      this._drawTrail([]);
      if (this.trail) this.trail.classList.remove('rejected');
    }

    _wirePattern() {
      if (!this.patternEl) return;
      /* Pointer event, then a click at the same dot within one gesture window:
         some synthetic/touchscreen paths deliver a click but no move, so a
         sequence of taps must still be able to connect dots (hands do this
         naturally when slowly drawing on a small screen). */
      this.patternEl.addEventListener('click', (ev) => {
        if (this.drawing || this.busy || !this.sequence.length) return;
        const i = this._dotAt(ev);
        if (i < 0) return;
        this._clickSeq = this._clickSeq || [];
        if (this._clickSeq.indexOf(i) < 0) { this._clickSeq.push(i); this._appendDot(i); }
        if (this._clickTimer) global.clearTimeout(this._clickTimer);
        this._clickTimer = global.setTimeout(() => {
          const seq = (this._clickSeq || []).join('-');
          this._clickSeq = [];
          if (seq) this._submitPattern(seq);
        }, 1100);
      });
      const down = (ev) => {
        if (this.drawing || this.busy) return;
        if (ev.button !== undefined && ev.button !== 0) return;
        const i = this._dotAt(ev);
        if (i < 0) return;
        ev.preventDefault();
        this.drawing = true;
        this.pointerId = ev.pointerId;
        if (this._clickTimer) { global.clearTimeout(this._clickTimer); this._clickTimer = null; }
        this._clickSeq = [];
        this._resetPattern();
        this._appendDot(i);
        try { this.patternEl.setPointerCapture(ev.pointerId); } catch (e) {}
      };
      const move = (ev) => {
        if (!this.drawing) return;
        ev.preventDefault();
        const i = this._dotAt(ev);
        if (i >= 0) this._appendDot(i);
        this._drawLiveTrail(ev);
      };
      const up = (ev) => {
        if (!this.drawing) return;
        this.drawing = false;
        try { this.patternEl.releasePointerCapture(this.pointerId); } catch (e) {}
        this.pointerId = null;
        if (this.sequence.length) this._submitPattern(this.sequence.join('-'));
      };
      this.patternEl.addEventListener('pointerdown', down);
      this.patternEl.addEventListener('pointermove', move);
      this.patternEl.addEventListener('pointerup', up);
      this.patternEl.addEventListener('pointercancel', () => {
        this.drawing = false;
        this._resetPattern();
      });
      /* Keyboard fallback for accessibility/VM use: press digits 1-9 while the
         pattern matrix is visible, then Enter to submit. */
      this._keyBuffer = '';
      global.addEventListener('keydown', (ev) => {
        if (this.effectiveMode !== 'pattern' || this.busy) return;
        if (/^[1-9]$/.test(ev.key)) {
          this._keyBuffer += String(Number(ev.key) - 1);
          this.sequence = this._keyBuffer.split('').map(Number);
          this.sequence.forEach((i) => this.dotEls[i] && this.dotEls[i].classList.add('active'));
          this._drawTrail(this.sequence.map((j) => [PATTERN_DOT[j].x, PATTERN_DOT[j].y]));
          ev.preventDefault();
        } else if (ev.key === 'Enter' && this._keyBuffer) {
          const seq = this._keyBuffer;
          this._keyBuffer = '';
          this._submitPattern(seq.split('').join('-'));
          ev.preventDefault();
        } else if (ev.key === 'Escape') {
          this._keyBuffer = '';
          this._resetPattern();
        }
      }, true);
    }

    _submitPattern(pattern) {
      if (this.busy) return;
      this.busy = true;
      const secret = String(pattern);
      this._trace('auth-submit via=pattern seq=' + secret.length);
      bridgeCall('security', 'unlock', { secret })
        .then((res) => { this._trace('auth-raw ' + JSON.stringify(res).slice(0, 240)); return this._afterCredential(res, secret, 'pattern'); })
        .catch((err) => this._afterCredential({ success: false, error: String(err) }, secret, 'pattern'))
        .then(() => { this.busy = false; });
    }

    /* ---------------------------------------------------------------- PIN */
    _wirePin() {
      if (this.pinpad) {
        /* Exactly ONE handler for the whole press, with Android's click
           semantics: the key fires on release (click).  WebKit delivers one
           physical touch press as pointerdown + touchstart + pointerup +
           touchend + click, with per-contact pointerIds, so any activation on
           pointerdown (the old code) had to then cancel the click - and that
           dedup could not see the click's contact, so the digit landed twice
           ("3" -> "33").  One click listener cannot double-count: every press
           produces exactly one click, however many event families precede it.
           Keyboard input stays on its own path. */
        const keyFrom = (ev) => (ev && ev.target && ev.target.closest
          ? ev.target.closest('.lockscreen-key') : null);
        /* A83: one press executes exactly one key action.  A tap can emit
           pointerup + touchend + click.  The action runs on the FIRST release
           event; the remaining duplicates of that same press are ignored by a
           short release window.  No action is ever fired from pointerdown, and
           a press that produces no click still works. */
        this._lastAct = 0;
        const act = (ev, source) => {
          const key = keyFrom(ev);
          if (!key || this.busy) return;
          const now = Date.now();
          if (now - this._lastAct < 450) return;
          this._lastAct = now;
          const id = key.id || key.dataset.pin || '';
          if (id === 'lockscreen-pin-del') { this.pin = this.pin.slice(0, -1); this._paintPin(); return; }
          if (id === 'lockscreen-pin-cancel') { this.showAuthoritative(); return; }
          if (id === 'lockscreen-pin-enter') { this._submitPin(); return; }
          const d = key.dataset.pin;
          if (d !== undefined && this.pin.length < 16) {
            this.pin += d; this._paintPin(); buzz(6);
          }
          this._trace('pin-key via=' + source + ' len=' + this.pin.length);
        };
        this.pinpad.onclick = (ev) => act(ev, 'click');
        this.pinpad.addEventListener('pointerup', (ev) => act(ev, 'pointerup'));
        this.pinpad.addEventListener('touchend', (ev) => act(ev, 'touchend'));
        this.pinpad.addEventListener('pointerdown', (ev) => {
          const key = keyFrom(ev);
          if (key) { try { key.classList.add('pressed'); } catch (e) {} }
          if (key && ev.cancelable) { try { ev.preventDefault(); } catch (e) {} }
        }, { passive: false });
        const release = (ev) => {
          const key = keyFrom(ev);
          if (key) { try { key.classList.remove('pressed'); } catch (e) {} }
        };
        this.pinpad.addEventListener('pointerup', release);
        this.pinpad.addEventListener('pointercancel', release);
        this.pinpad.addEventListener('pointerleave', release);
      }
      const key = (ev) => {
        /* A84: the keypad is also the PIN fallback of the pattern and the
           fingerprint surfaces, so keyboard digits must work whenever a
           credential surface (not swipe) is the active mode. */
        if (this.effectiveMode === 'swipe' || !this.effectiveMode || this.busy) return;
        if (/^[0-9]$/.test(ev.key)) { this.pin += ev.key; this._paintPin(); ev.preventDefault(); }
        else if (ev.key === 'Backspace') { this.pin = this.pin.slice(0, -1); this._paintPin(); ev.preventDefault(); }
        else if (ev.key === 'Enter') { this._submitPin(); ev.preventDefault(); }
      };
      global.addEventListener('keydown', key, true);
    }

    _paintPin() {
      if (!this.pinDisplay) return;
      this.pinDisplay.textContent = '●'.repeat(this.pin.length);
      this.pinDisplay.dataset.length = String(this.pin.length);
    }

    _submitPin() {
      if (this.busy) return;
      if (this.pin.length < MIN_PIN) {
        this._error('Enter at least ' + MIN_PIN + ' digits');
        return;
      }
      this.busy = true;
      const secret = this.pin;
      this._trace('auth-submit via=pin len=' + secret.length);
      bridgeCall('security', 'unlock', { secret })
        .then((res) => this._afterCredential(res, secret, 'pin'))
        .catch((err) => this._afterCredential({ success: false, error: String(err) }, secret, 'pin'))
        .then(() => { this.busy = false; });
    }

    _trace(msg) {
      try {
        const handler = global.webkit && global.webkit.messageHandlers.nuxelDiag;
        if (handler) handler.postMessage('LOCKS[a81] ' + msg);
      } catch (e) { /* observation only */ }
    }

    _afterCredential(res, secret, via) {
      this._trace('auth-result via=' + via + ' success=' + (res && res.success) +
                  ' unlocked=' + (res && res.unlocked) + ' error=' +
                  ((res && (res.error || res.detail)) || '-'));
      /* Every attempt consumes the drawn pattern: an accepted one is gone
         because the lockscreen is leaving, a rejected one must be redrawn
         from scratch. */
      this._resetPattern();
      this._keyBuffer = '';
      if (res && res.success === true && res.unlocked === true) {
        this._clearError();
        buzz(14);
        this.pin = ''; this._paintPin();
        if (this.onUnlock) return this.onUnlock({ via: via, result: res });
        return res;
      }
      if (res && res.error === 'rate_limited') {
        this._error('Too many attempts. Wait ' + (res.remaining_s || 30) + ' s.');
      } else {
        this._error('Incorrect. Try again.' + (res && res.error ? ' (' + res.error + ')' : ''));
      }
      buzz(40);
      this.pin = ''; this._paintPin();
      if (this.trail) {
        this.trail.classList.add('rejected');
        global.setTimeout(() => this.trail.classList.remove('rejected'), 420);
      }
      const anyErr = this.setupErrorEl;
      if (anyErr && via === 'pattern-setup') anyErr.textContent = 'The pattern could not be saved.';
      return res;
    }

    /* -------------------------------------------------------- fingerprint */
    _wireFingerprint() {
      if (!this.fpEl) return;
      this.fpEl.addEventListener('click', () => this.tryFingerprint());
      global.addEventListener('keydown', (ev) => {
        if (this.effectiveMode === 'fingerprint' && (ev.key === 'Enter' || ev.key === ' ')) {
          this.tryFingerprint();
          ev.preventDefault();
        }
      }, true);
    }

    _positionScanner() {
      if (!this.fpEl) return;
      /* CSS places the oval by viewport proportion; verify against the live
         viewport so the artwork is exactly on the physical scanner. */
      this.fpEl.style.setProperty('--scanner-left', (SCANNER.left * 100) + '%');
      this.fpEl.style.setProperty('--scanner-top', (SCANNER.top * 100) + '%');
      this.fpEl.style.setProperty('--scanner-width', (SCANNER.width * 100) + '%');
      this.fpEl.style.setProperty('--scanner-height', (SCANNER.height * 100) + '%');
    }

    tryFingerprint() {
      if (this.busy || this._fpInFlight || this.effectiveMode !== 'fingerprint') return;
      if (!this.status || !this.status.fingerprint || !this.status.fingerprint.enrolled) {
        this._fpMessage('No fingerprint registered yet. Use PIN or set one up.');
        return;
      }
      if (!this.status.fingerprint || !this.status.fingerprint.provider_ready) {
        this._fpMessage('Scanner not available on this build — use PIN');
        return;
      }
      this._fpInFlight = true;
      this.fpRing.classList.add('scanning');
      this._fpMessage('Hold on the scanner…');
      bridgeCall('fingerprint', 'authenticate', { unlock: true, mode: 'lockscreen' })
        .then((res) => {
          if (res && res.success === true && res.unlocked === true) {
            this.fpRing.classList.add('accepted');
            this._fpMessage('Accepted');
            if (this.onUnlock) return this.onUnlock({ via: 'fingerprint', result: res });
            return res;
          }
          this.fpRing.classList.remove('accepted');
          this._fpMessage(res && res.blocker ? 'Fingerprint unavailable — use PIN'
            : 'Not recognised — try again or use PIN');
          buzz(30);
          return res;
        })
        .catch(() => this._fpMessage('Scanner error — use PIN'))
        .then(() => {
          this._fpInFlight = false;
          this.fpRing.classList.remove('scanning');
        });
    }

    _fpMessage(text) {
      if (this.fpStatus) this.fpStatus.textContent = text;
    }

    /* --------------------------------------------------------------- setup */
    /* Lock-screen credential setup was REMOVED (A82).  A pattern/PIN is only
       set or changed in Settings -> Security, never on the glass.  openSetup()
       therefore never paints a sheet; it reports the owner-facing reason if a
       stale caller still asks.  closeSetup() stays a no-op so old callers that
       pair the two calls cannot throw. */
    openSetup() {
      this._error('Set your pattern or PIN in Settings → Security.');
      return { ok: false, error: 'set-credential-in-settings' };
    }

    closeSetup() { this.setup = null; }

    /* Compact geometry readout for console verification (no secret data).
       `build` lets an acceptance check prove WHICH surface is loaded (a stale
       cached bundle and a fresh one both answer here), and `trail` is the
       points actually painted on the SVG right now. */
    describe() {
      const trailEl = this.trail;
      const out = { build: VERSION, mode: this.mode, effective: this.effectiveMode,
                    visible: this.isVisible(),
                    status: this.status ? { mode: this.status.mode, pinned: this.status.pin_fallback_set,
                      fp: this.status.fingerprint, policy: this.status.attempt_policy } : null,
                    pinLen: this.pin.length, seq: this.sequence.slice(),
                    trail: trailEl ? String(trailEl.getAttribute('points') || '') : '' };
      const box = (id) => { const e = document.getElementById(id); if (!e) return null;
        const r = e.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }; };
      out.patternRect = box('lockscreen-pattern');
      out.dots = Array.prototype.map.call(document.querySelectorAll('#lockscreen-pattern-dots .lockscreen-pattern-dot'), (d) => {
        const r = d.getBoundingClientRect(); return { dot: d.dataset.dot, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) }; });
      out.keys = Array.prototype.map.call(document.querySelectorAll('#lockscreen-pinpad .lockscreen-key'), (k) => {
        const r = k.getBoundingClientRect(); return { k: k.dataset.pin || k.id || k.textContent.trim(), x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) }; });
      out.pinFallback = box('lockscreen-pin-fallback');
      out.fingerprint = box('lockscreen-fingerprint');
      out.fingerprintStatus = this.fpStatus ? this.fpStatus.textContent : '';
      out.pinButtonVisible = !!(this.pinFallback && !this.pinFallback.hidden);
      out.authSwitchVisible = !!(document.getElementById('lockscreen-auth-switch') &&
        !document.getElementById('lockscreen-auth-switch').hidden);
      out.error = this.errorEl ? this.errorEl.textContent : '';
      return out;
    }

    /* Root-console helper: evaluate a pattern string without a pointer drag.
       Used only by the device acceptance matrix (tools/vnc) and by the
       keyboard path; the server still verifies the credential. */
    submitPattern(seq) {
      const text = Array.isArray(seq) ? seq.join('-') : String(seq || '');
      if (!text) return false;
      this._submitPattern(text);
      return true;
    }

    /* Root-console helper: paint the fingerprint presentation for layout
       verification (preview only; it can never unlock). */
    previewFingerprint() {
      /* Kept for API compatibility; it performs no visual override. */
      return this.describe();
    }

    /* Root-console helper: type a PIN through the keypad state machine. */
    enterPin(value) {
      const digits = String(value || '').replace(/\D/g, '');
      if (!digits) return false;
      this.pin = digits.slice(0, 16);
      this._paintPin();
      this._submitPin();
      return true;
    }

    /* -------------------------------------------------------------- state */
    refresh() {
      return securityStatus().then((st) => {
        if (st && st.success !== false) {
          this.status = st;
          this.mode = st.mode || 'swipe';
        }
        return this.status;
      }).catch(() => this.status);
    }

    show() {
      if (!this.el) return;
      this._positionScanner();
      return this.refresh().then(() => {
        const st = this.status || {};
        /* A83: the server is the authority, but a transient non-answer (bridge
           still warming, mock fallback, 5xx) must never silently downgrade a
           credentialed device to the swipe penguin: that is exactly the state
           where the owner sees a lockhead instead of the keypad.  When the lock
           mode is unknown, keep the last confirmed credential mode; only a
           fresh, successful status may say "swipe". */
        const answered = !!(st.success !== false && (st.mode || st.locked !== undefined));
        let mode = st.mode || '';
        if (!answered) {
          mode = (this.mode && this.mode !== 'swipe') ? this.mode : 'pin';
          this._trace('auth-status-fallback keep=' + mode);
        }
        this.mode = mode;
        const fp = st.fingerprint || {};
        if (mode === 'fingerprint') {
          /* Keep the requested fingerprint presentation (artwork on the
             scanner) when the PIN fallback exists so the owner sees the real
             state.  Without a ready provider the surface states that plainly
             and the PIN button below it is the way in. */
          if (st.pin_fallback_set) {
            this.effectiveMode = 'fingerprint';
          } else {
            /* No fallback: never hide the only usable path. */
            this.effectiveMode = 'pin';
          }
        } else {
          this.effectiveMode = mode;
        }
        this._showMode(this.effectiveMode);
        if (this.effectiveMode === 'fingerprint') {
          const enrolled = !!fp.enrolled;
          const ready = !!fp.provider_ready;
          this._fpMessage(!ready
            ? 'Fingerprint scanner unavailable on this build (' + (fp.blocker || 'no secure provider') + ') — use PIN'
            : (!enrolled ? 'No fingerprint registered — use PIN or set one up in Settings'
               : 'Touch the scanner to unlock'));
        }
      });
    }

    _showMode(mode) {
      if (!this.el) return;
      this.effectiveMode = mode;
      this._pinIsFallback = false;
      this._clearError();
      if (mode === 'swipe') {
        this.el.hidden = true;
        if (this.onSwipeMode) this.onSwipeMode();
        return;
      }
      this.el.hidden = false;
      this.pin = ''; this._paintPin();
      this._resetPattern();
      /* A credential mode replaces the swipe handle entirely. */
      if (this.onSwipeMode) this.onSwipeMode(false);
      this.patternEl.hidden = mode !== 'pattern';
      this.pinpad.hidden = mode !== 'pin';
      this.fpEl.hidden = mode !== 'fingerprint';
      this.pinFallback.hidden = mode === 'pin';
      if (mode === 'pattern') this.pinFallback.hidden = false;
      /* The head (title/hint) is never painted on the lock screen: the owner
         asked for no "draw pattern / enter pin" instructions.  Only transient
         status (Checking…, the error when a save is asked for from the glass)
         is written there, and the element stays hidden. */
      if (this.titleEl) this.titleEl.textContent = '';
      if (this.hintEl) this.hintEl.textContent = '';
      if (mode === 'fingerprint') this._positionScanner();
    }

    _wireFallback() {
      const fb = el('lockscreen-pin-fallback');
      if (fb && !fb._wired) {
        fb._wired = true;
        fb.addEventListener('pointerdown', (ev) => { ev.preventDefault(); this.showPinFallback(); });
        fb.addEventListener('click', () => this.showPinFallback());
      }
    }

    showPinFallback() {
      /* The PIN button is the fallback for pattern/fingerprint modes.  The
         credential is the stored PIN in both cases; the server verifies it
         against the PIN/mode-aware verifier.  A82: `this.mode` is the
         authoritative mode from the last status, so re-showing it here after
         a Cancel restores the real surface (a Cancel used to leave the keypad
         up because this passed the transient effective mode instead). */
      if (this.effectiveMode === 'pin') { this._showMode('pin'); return; }
      /* A84: coming from pattern/fingerprint the keypad needs its Cancel key
         to lead back to the authoritative surface instead of to itself. */
      this._pinIsFallback = true;
      this._showMode('pin');
    }

    /* A84: show whichever credential surface the authoritative mode needs,
       WITHOUT re-reading status.  Called by the swipe gesture when a
       credential is in force: the swipe has already revealed the right
       surface, so this must be synchronous and idempotent (it is also used
       by tests). */
    showCredentialSurface() {
      if (this.mode === 'pin') { this.showPinFallback(); return this.describe(); }
      if (this.mode === 'pattern' || this.mode === 'fingerprint') {
        this.effectiveMode = this.mode;
        this._showMode(this.mode);
        return this.describe();
      }
      if (this.mode === 'swipe') { this._showMode('swipe'); return this.describe(); }
      return this.show();
    }

    /* Return from the PIN fallback to the authoritative mode (pattern /
       fingerprint / swipe).  Used by Cancel and by a Settings mode change. */
    showAuthoritative() {
      if (this._pinIsFallback) return this.show();
      if (this.mode === 'pin') return this.showPinFallback();
      if (this.mode === 'swipe') { this._showMode('swipe'); return; }
      return this.show();
    }

    _error(text) { if (this.errorEl) this.errorEl.textContent = String(text || ''); }
    _clearError() { if (this.errorEl) this.errorEl.textContent = ''; }

    /* Called by Home after a successful unlock so stale state never carries
       a typed PATTERN/PIN to the next lock. */
    hide() {
      if (this.el) this.el.hidden = true;
      this.pin = ''; this._paintPin();
      this._resetPattern();
      this._clearError();
    }

    isVisible() { return !!(this.el && !this.el.hidden); }
  }

  global.NuxelLockscreenAuth = LockscreenAuth;
  global.NUXEL_LOCKScreenAuth_VERSION = VERSION;
})(window);
