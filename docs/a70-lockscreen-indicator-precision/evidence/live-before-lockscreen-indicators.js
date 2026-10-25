/* Nuxel lockhead status indicators (charging / PC / live console).
 *
 * Three INDEPENDENT indicators next to the animated penguin:
 *   charging      external power present + active-charge animation
 *   usb-data      a real enumerated USB data link to a host (cyan)
 *   live-console  the running nuxel-console session itself (amber/red)
 *
 * The backend is the single source of truth:
 *   phone:  NuxelHost.statusRead('system-indicators')  (sysfs + /proc)
 *   VM/desktop: GET /api/v1/system/indicators           (same module)
 *
 * Updates are event-driven where the host can provide events (visibility /
 * screen wake / online), with a slow bounded safety read while the lockscreen
 * is visible.  A failed read never turns an indicator on; it leaves the
 * last-known state until the next successful read.
 */
(function (global) {
  'use strict';

  var VERSION = 'a68.2';
  var SAFETY_MS = 15000;
  var API_PATH = 'http://127.0.0.1:8080/api/v1/system/indicators';
  var ICONS = {
    charging: '/assets/nuxel-charging.png?v=a68',
    usb: '/assets/nuxel-connected-pc.png?v=a68',
    live: '/assets/nuxel-live-console-active.png?v=a68'
  };

  function el(id) { return global.document ? global.document.getElementById(id) : null; }

  function normalise(data) {
    data = data || {};
    var charging = data.charging || {};
    var usb = data.usb_data || {};
    var live = data.live_console || {};
    return {
      externalPower: Boolean(charging.external_power),
      charging: Boolean(charging.charging),
      pcConnected: Boolean(usb.pc_connected),
      liveConsole: Boolean(live.active),
      sources: {
        power: String(charging.source || ''),
        usb: String(usb.source || ''),
        live: String(live.source || '')
      }
    };
  }

  function same(a, b) {
    return a.externalPower === b.externalPower &&
           a.charging === b.charging &&
           a.pcConnected === b.pcConnected &&
           a.liveConsole === b.liveConsole &&
           a.sources.power === b.sources.power &&
           a.sources.usb === b.sources.usb &&
           a.sources.live === b.sources.live;
  }

  /* Calls fn with a value or a rejection handler, without relying on optional
     Promise.prototype.finally (older WebKit). */
  function settle(promise, ok, fail) {
    try { promise.then(ok, fail); } catch (e) { try { fail(e); } catch (e2) {} }
  }

  function LockscreenIndicators() {
    this.version = VERSION;
    this._timer = null;
    this._inFlight = false;
    this._visible = false;
    this._generation = 0;

    this.container = el('lockscreen-indicators');
    this.els = {
      charging: el('lockscreen-indicator-charging'),
      usb: el('lockscreen-indicator-usb'),
      live: el('lockscreen-indicator-live')
    };
    this.state = {
      externalPower: false, charging: false, pcConnected: false, liveConsole: false,
      sources: { power: '', usb: '', live: '' }
    };

    this._ensureImages();
    this._wireEvents();
    this._render();
  }

  LockscreenIndicators.prototype._ensureImages = function () {
    var self = this;
    Object.keys(this.els).forEach(function (key) {
      var node = self.els[key];
      if (!node) return;
      var img = node.querySelector ? node.querySelector('img') : null;
      if (img && !img.getAttribute('src')) img.setAttribute('src', ICONS[key]);
    });
  };

  LockscreenIndicators.prototype._read = function () {
    var self = this;
    return new global.Promise(function (resolve, reject) {
      var settled = false;
      function done(value) { if (!settled) { settled = true; resolve(value); } }
      function fail(err) { if (!settled) { settled = true; reject(err); } }

      var host = global.NuxelHost;
      if (host && host.available && typeof host.statusRead === 'function') {
        settle(global.Promise.resolve(host.statusRead('system-indicators')), function (r) {
          var text = r && (r.text || r.value);
          if (r && r.ok === true && text) {
            try { done(normalise(JSON.parse(text))); return; } catch (e) { /* fall through */ }
          }
          settle(self._readHttp(), done, fail);
        }, function () { settle(self._readHttp(), done, fail); });
        return;
      }
      settle(self._readHttp(), done, fail);
    });
  };

  LockscreenIndicators.prototype._readHttp = function () {
    return new global.Promise(function (resolve, reject) {
      if (global.bridge && typeof global.bridge.getSystemIndicators === 'function') {
        settle(global.Promise.resolve(global.bridge.getSystemIndicators()), function (data) {
          if (data && data.charging) resolve(normalise(data));
          else reject(new Error('indicators:bad-bridge-payload'));
        }, reject);
        return;
      }
      if (typeof global.fetch !== 'function') {
        reject(new Error('indicators:fetch-unavailable'));
        return;
      }
      var controller = global.AbortController ? new global.AbortController() : null;
      var timer = controller ? global.setTimeout(function () { controller.abort(); }, 4000) : null;
      function finish() { if (timer !== null) { global.clearTimeout(timer); timer = null; } }
      global.fetch(API_PATH, {
        cache: 'no-store', credentials: 'omit',
        signal: controller ? controller.signal : undefined
      }).then(function (response) {
        if (!response.ok) throw new Error('indicators status ' + response.status);
        return response.json();
      }).then(function (data) {
        finish();
        if (data && data.charging) resolve(normalise(data));
        else reject(new Error('indicators:bad-http-payload'));
      }).catch(function (err) { finish(); reject(err); });
    });
  };

  LockscreenIndicators.prototype._tick = function () {
    var self = this;
    if (!this._visible || this._inFlight || this._displayOff()) return;
    var generation = this._generation;
    this._inFlight = true;
    settle(this._read(), function (next) {
      self._inFlight = false;
      if (!self._visible || generation !== self._generation) return;
      if (!same(self.state, next)) {
        self.state = next;
        self._render();
        self._trace('update power=' + (next.externalPower ? (next.charging ? 'charging' : 'power') : 'off') +
                    ' usb=' + (next.pcConnected ? 1 : 0) + ' live=' + (next.liveConsole ? 1 : 0));
      }
    }, function (err) {
      self._inFlight = false;
      if (generation === self._generation) self._trace('read-failed ' + (err && err.message ? err.message : err));
    });
  };

  LockscreenIndicators.prototype._displayOff = function () {
    try {
      return !!(global.document && global.document.body &&
                (global.document.body.classList.contains('display-off') ||
                 global.document.body.dataset.displayOff === '1'));
    } catch (e) { return false; }
  };

  LockscreenIndicators.prototype.refresh = function () {
    if (!this._visible) return;
    this._generation++;
    this._tick();
  };

  LockscreenIndicators.prototype._wireEvents = function () {
    if (this._wired) return;
    this._wired = true;
    var self = this;
    function refresh() { self.refresh(); }
    try { global.document.addEventListener('visibilitychange', refresh, { passive: true }); } catch (e) {}
    try { global.addEventListener('online', refresh, { passive: true }); } catch (e) {}
    try { global.addEventListener('focus', refresh, { passive: true }); } catch (e) {}
    try { global.addEventListener('nuxel:display-on', refresh, { passive: true }); } catch (e) {}
    try {
      if (global.NuxelHost && typeof global.NuxelHost.onEvent === 'function') {
        global.NuxelHost.onEvent(function (name) {
          if (!name || name === 'display-on' || name === 'system-indicators' ||
              name === 'usb' || name === 'power' || name === 'live-console') refresh();
        });
      }
    } catch (e) {}
  };

  LockscreenIndicators.prototype.start = function () {
    this._visible = true;
    this._generation++;
    this._wireEvents();
    this._stopTimer();
    this._tick();
    var self = this;
    this._timer = global.setInterval(function () { self._tick(); }, SAFETY_MS);
  };

  LockscreenIndicators.prototype.stop = function () {
    this._visible = false;
    this._generation++;
    this._stopTimer();
  };

  LockscreenIndicators.prototype._stopTimer = function () {
    if (this._timer !== null) { global.clearInterval(this._timer); this._timer = null; }
  };

  LockscreenIndicators.prototype._render = function () {
    this._apply(this.els.charging, 'active', this.state.externalPower);
    this._apply(this.els.charging, 'charging', this.state.charging);
    this._apply(this.els.usb, 'active', this.state.pcConnected);
    this._apply(this.els.live, 'active', this.state.liveConsole);
    try {
      if (this.container) {
        this.container.dataset.powerSource = this.state.sources.power;
        this.container.dataset.usbSource = this.state.sources.usb;
        this.container.dataset.liveSource = this.state.sources.live;
      }
    } catch (e) {}
  };

  LockscreenIndicators.prototype._apply = function (node, className, on) {
    if (!node || !node.classList) return;
    try { on ? node.classList.add(className) : node.classList.remove(className); }
    catch (e) {}
  };

  LockscreenIndicators.prototype._trace = function (msg) {
    var line = 'IND[' + VERSION + '] ' + msg;
    try {
      var diag = global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag;
      if (diag) diag.postMessage(line);
    } catch (e) {}
    try { if (global.console) global.console.log('[Indicators]', msg); } catch (e) {}
  };

  LockscreenIndicators.prototype.ensureDom = function (wrap) {
    if (!wrap || !this.container) return;
    if (!wrap.contains(this.container)) wrap.appendChild(this.container);
  };

  global.NuxelLockscreenIndicators = LockscreenIndicators;
})(window);
