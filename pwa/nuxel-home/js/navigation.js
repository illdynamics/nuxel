// Nuxel Home — authoritative in-process app-session registry and 3-button nav.
// PWA apps intentionally share one WebKit host; closing a session removes only
// that iframe and never signals the host, Phoc, framebuffer bridge, or systemd.
(function (global) {
  'use strict';
  function now() { return Date.now(); }

  class AppSessions {
    constructor() { this.byId = new Map(); this.foregroundId = null; }
    register(app, surface) {
      let s = this.byId.get(app.id);
      if (!s) {
        s = { appId: app.id, appName: app.name, type: app.type, sessionId: 'pwa-' + now() + '-' + Math.random().toString(36).slice(2, 7), state: 'running', lastFocused: now(), surface: surface || null };
        this.byId.set(app.id, s);
      }
      if (surface) s.surface = surface;
      return this.activate(app.id);
    }
    activate(id) {
      if (this.foregroundId && this.byId.has(this.foregroundId) && this.foregroundId !== id) this.byId.get(this.foregroundId).state = 'background';
      const s = this.byId.get(id); if (!s) return null;
      s.state = 'foreground'; s.lastFocused = now(); this.foregroundId = id;
      document.dispatchEvent(new CustomEvent('nuxel:sessions-changed', { detail: this.list() }));
      return s;
    }
    home() {
      if (this.foregroundId && this.byId.has(this.foregroundId)) this.byId.get(this.foregroundId).state = 'background';
      this.foregroundId = null;
      document.dispatchEvent(new CustomEvent('nuxel:sessions-changed', { detail: this.list() }));
    }
    close(id, failed) {
      const s = this.byId.get(id); if (!s) return false;
      s.state = failed ? 'failed' : 'closed';
      if (s.surface) ['frame', 'bar', 'status'].forEach(k => { if (s.surface[k]) s.surface[k].remove(); });
      this.byId.delete(id); if (this.foregroundId === id) this.foregroundId = null;
      document.dispatchEvent(new CustomEvent('nuxel:sessions-changed', { detail: this.list() }));
      return true;
    }
    get(id) { return this.byId.get(id) || null; }
    current() { return this.foregroundId ? this.get(this.foregroundId) : null; }
    list() { return Array.from(this.byId.values()).filter(s => s.state !== 'closed').sort((a,b) => b.lastFocused - a.lastFocused); }
  }

  class SystemNavigation {
    constructor() {
      this.el = document.getElementById('system-navigation');
      this.holdMs = 700; this.timer = null; this.held = false;
      this.activePointer = null;
      this.nativeDock = false;
      if (!this.el) return;
      this.el.querySelectorAll('button[data-nav]').forEach(button => {
        this._bindImage(button);
        this.bind(button);
      });
      this._resolveNativeDock();
    }
    _resolveNativeDock() {
      // On the S10+ the authoritative dock is the native layer-shell client
      // nuxel-navdock. The DOM strip is only the desktop/VM fallback; if both
      // exist the owner sees two Back and two Recents controls. Hide the DOM
      // copy before first paint and keep it hidden once the native dock proves
      // it is running. If the native dock is absent, the DOM fallback returns.
      const host = global.NuxelHost;
      if (!host || !host.available || typeof host.statusRead !== 'function') return;
      try { document.documentElement.classList.add('native-nav-pending'); } catch (e) {}
      const sync = () => {
        Promise.resolve(host.statusRead('navdock-state')).then((res) => {
          const text = (res && (res.text || res.value)) || '';
          const ready = /NAV_DOCK_READY/.test(text);
          // READY only proves the dock mapped once.  It can be hidden while the
          // lockscreen is up; the LAST visibility event is the truth.  If it is
          // hidden or the client is gone, show the DOM fallback so navigation is
          // never missing, and never leave both hosts hidden.
          const last = text.trim().split(/\n/).filter(Boolean).pop() || '';
          const visible = ready && !/NAV_DOCK_HIDE/.test(last);
          this.nativeDock = visible;
          try {
            document.documentElement.classList.toggle('native-nav-present', visible);
            document.documentElement.classList.toggle('native-nav-pending', false);
            document.documentElement.classList.add('nav-fallback-safe');
          } catch (e) {}
          this._traceNs('native-dock=' + (visible ? 'present' : 'hidden/absent'));
        }).catch(() => {
          // statusRead unavailable: the DOM strip is the only host; leave it up.
          try { document.documentElement.classList.remove('native-nav-present', 'native-nav-pending'); } catch (e) {}
        });
      };
      sync();
      if (!this._navSyncTimer) this._navSyncTimer = setInterval(sync, 2000);
    }
    _traceNs(message) {
      try {
        const diag = global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag;
        if (diag) diag.postMessage('NAVOWNER ' + message);
      } catch (e) {}
    }
    _bindImage(button) {
      const image = button.querySelector('img');
      if (!image) return;
      const show = () => button.classList.add('has-image');
      image.addEventListener('load', show);
      image.addEventListener('error', () => { image.hidden = true; button.classList.remove('has-image'); });
      if (image.complete && image.naturalWidth) show();
    }
    bind(button) {
      const action = button.dataset.nav;
      let lastPointerTapAt = 0;
      const trace = (phase) => {
        try {
          const diag = global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag;
          if (diag) diag.postMessage(`NAV ${phase} action=${action} state=${global.nuxel && global.nuxel.appSession ? global.nuxel.appSession.state : '?'} page=${global.launcher ? global.launcher.currentPage : '?'}`);
        } catch (e) { /* observation only */ }
      };
      const cancel = () => { if (this.timer) clearTimeout(this.timer); this.timer = null; this.activePointer = null; };
      button.addEventListener('pointerdown', e => {
        if (e.button !== undefined && e.button !== 0) return;
        this.held = false; this.activePointer = e.pointerId;
        button.setPointerCapture && button.setPointerCapture(e.pointerId);
        // Start the actuator request with the physical touch, rather than after
        // an app has navigated or rendered.  This keeps the click and the buzz
        // perceptually together even when the app is busy.
        this.buzz('navigation');
        this.timer = setTimeout(() => { this.held = true; this.long(action); }, this.holdMs);
      });
      button.addEventListener('pointerup', e => {
        if (this.activePointer !== null && e.pointerId !== this.activePointer) return;
        const held = this.held; cancel();
        if (!held) { lastPointerTapAt = Date.now(); this.tap(action, trace); }
      });
      button.addEventListener('pointercancel', cancel); button.addEventListener('lostpointercapture', cancel);
      // Keyboard and accessibility activations do not generate pointer events.
      button.addEventListener('click', e => {
        if (Date.now() - lastPointerTapAt < 500) return;
        this.buzz('navigation'); this.tap(action, trace);
      });
    }
    buzz(kind) {
      // Browser vibration starts in the same pointer task, and the hardware
      // request is made before navigation changes the DOM.  Together this
      // removes the perceptible post-click lag on the S10+.
      // Use exactly one actuator path: native host OR browser fallback, never both.
      if (global.NuxelHost && global.NuxelHost.available) {
        global.NuxelHost.action('haptics-' + kind);
      } else {
        try { if (global.navigator && global.navigator.vibrate) global.navigator.vibrate(kind === 'long' ? 25 : 12); } catch (e) {}
      }
    }
    tap(action, trace) {
      if (trace) trace('tap');
      if (!global.nuxel) { if (trace) trace('missing-nuxel'); return; }
      try {
        if (action === 'back') global.nuxel.back();
        else if (action === 'home') global.nuxel.home();
        else global.nuxel.recentsToggle();
      } catch (error) {
        if (trace) trace('error:' + (error && error.message ? error.message : error));
        return;
      }
      if (trace) trace('done');
    }
    long(action) {
      if (!global.nuxel) return;
      if (action === 'back') global.nuxel.terminateForeground();
      // The penguin/Home affordance always returns to Home desktop 1.  It used
      // to open Home Settings on a long press, so a slightly slow tap looked
      // like the Home button "did nothing" (or opened a secondary surface).
      else if (action === 'home') global.nuxel.home();
      this.buzz('long');
    }
  }
  global.NuxelAppSessions = AppSessions;
  global.NuxelSystemNavigation = SystemNavigation;
  document.addEventListener('DOMContentLoaded', () => {
    if (global.nuxelNavigation) return;   // exactly one DOM fallback instance
    global.nuxelNavigation = new SystemNavigation();
  });
})(window);
