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

  var VERSION = 'a77.1';
  var SAFETY_MS = 3000;
  var API_PATH = 'http://127.0.0.1:8080/api/v1/system/indicators';
  var ICONS = {
    charging: '/assets/nuxel-charging.png?v=a77.1',
    usb: '/assets/nuxel-connected-pc.png?v=a77.1',
    live: '/assets/nuxel-live-console-active.png?v=a77.1',
    serial: '/assets/nuxel-console-serial.png?v=p34000',
    usbConsole: '/assets/nuxel-console-usb.png?v=p34000',
    wlan: '/assets/nuxel-console-wlan.png?v=p34000',
    fileTransfer: '/assets/nuxel-file-transfer.png?v=p34000'
  };

  function el(id) { return global.document ? global.document.getElementById(id) : null; }

  function normalise(data) {
    data = data || {};
    var charging = data.charging || {};
    var usb = data.usb_data || {};
    var live = data.live_console || {};
    var transports = data.console_transports || {};
    var transfer = data.file_transfer || {};
    var mode = data.connection_mode || {};
    return {
      externalPower: Boolean(charging.external_power),
      charging: Boolean(charging.charging),
      pcConnected: Boolean(usb.pc_connected),
      liveConsole: Boolean(live.active),
      serialConsole: Boolean((transports.serial || {}).active),
      usbConsole: Boolean((transports.usb || {}).active),
      wlanConsole: Boolean((transports.wlan || {}).active),
      fileTransfer: Boolean(transfer.active),
      modeSelected: String(mode.selected || transfer.selected || 'charging'),
      modeBusy: Boolean(mode.transition_in_progress),
      sources: {
        power: String(charging.source || ''),
        usb: String(usb.source || ''),
        live: String(live.source || ''),
        serial: String((transports.serial || {}).source || ''),
        usbConsole: String((transports.usb || {}).source || ''),
        wlan: String((transports.wlan || {}).source || ''),
        transfer: String(transfer.source || '')
      }
    };
  }

  function same(a, b) {
    return a.externalPower === b.externalPower &&
           a.charging === b.charging &&
           a.pcConnected === b.pcConnected &&
           a.liveConsole === b.liveConsole &&
           a.serialConsole === b.serialConsole &&
           a.usbConsole === b.usbConsole &&
           a.wlanConsole === b.wlanConsole &&
           a.fileTransfer === b.fileTransfer &&
           a.modeSelected === b.modeSelected &&
           a.modeBusy === b.modeBusy &&
           a.sources.power === b.sources.power &&
           a.sources.usb === b.sources.usb &&
           a.sources.live === b.sources.live &&
           a.sources.serial === b.sources.serial &&
           a.sources.usbConsole === b.sources.usbConsole &&
           a.sources.wlan === b.sources.wlan &&
           a.sources.transfer === b.sources.transfer;
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
    this._pending = false;
    this._visible = false;
    this._generation = 0;

    this.container = el('lockscreen-indicators');
    this.transportContainer = el('lockscreen-transports');
    this.els = {
      charging: el('lockscreen-indicator-charging'),
      usb: el('lockscreen-indicator-usb'),
      live: el('lockscreen-indicator-live')
    };
    this.transportEls = {
      serial: el('lockscreen-transport-serial'),
      usb: el('lockscreen-transport-usb'),
      wlan: el('lockscreen-transport-wlan'),
      fileTransfer: el('lockscreen-file-transfer')
    };
    this.modeButton = el('lockscreen-connection-mode');
    this.modeOverlay = el('connection-mode-overlay');
    this.modeStatus = el('connection-mode-status');
    this.state = {
      externalPower: false, charging: false, pcConnected: false, liveConsole: false,
      serialConsole: false, usbConsole: false, wlanConsole: false,
      fileTransfer: false, modeSelected: 'charging', modeBusy: false,
      sources: { power: '', usb: '', live: '', serial: '', usbConsole: '', wlan: '', transfer: '' }
    };

    this._ensureImages();
    this._wireEvents();
    this._wireModeSelector();
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
    Object.keys(this.transportEls).forEach(function (key) {
      var node = self.transportEls[key];
      if (!node) return;
      var img = node.querySelector ? node.querySelector('img') : null;
      var icon = key === 'fileTransfer' ? ICONS.fileTransfer :
                 key === 'serial' ? ICONS.serial :
                 key === 'usb' ? ICONS.usbConsole : ICONS.wlan;
      if (img && !img.getAttribute('src')) img.setAttribute('src', icon);
    });
    if (this.modeButton) {
      var modeImg = this.modeButton.querySelector('img');
      if (modeImg && !modeImg.getAttribute('src')) modeImg.setAttribute('src', '/assets/nuxel-connection-mode.png?v=p34000');
    }
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
      if (self._visible && generation === self._generation && !same(self.state, next)) {
        self.state = next;
        self._render();
        self._trace('update power=' + (next.externalPower ? (next.charging ? 'charging' : 'power') : 'off') +
                    ' usb=' + (next.pcConnected ? 1 : 0) + ' live=' + (next.liveConsole ? 1 : 0));
      }
      self._drainPending();
    }, function (err) {
      self._inFlight = false;
      if (generation === self._generation) {
        /* PC and console are proof-only indicators.  A failed read cannot keep
           an old positive assertion glowing after detach; charging retains its
           last good power-subsystem reading. */
        if (self.state.pcConnected || self.state.liveConsole ||
            self.state.serialConsole || self.state.usbConsole ||
            self.state.wlanConsole || self.state.fileTransfer) {
          self.state = {
            externalPower: self.state.externalPower,
            charging: self.state.charging,
            pcConnected: false,
            liveConsole: false,
            serialConsole: false,
            usbConsole: false,
            wlanConsole: false,
            fileTransfer: false,
            modeSelected: self.state.modeSelected,
            modeBusy: false,
            sources: {
              power: self.state.sources.power,
              usb: 'unavailable:read-failed',
              live: 'unavailable:read-failed',
              serial: 'unavailable:read-failed',
              usbConsole: 'unavailable:read-failed',
              wlan: 'unavailable:read-failed',
              transfer: 'unavailable:read-failed'
            }
          };
          self._render();
        }
        self._trace('read-failed ' + (err && err.message ? err.message : err));
      }
      self._drainPending();
    });
  };

  LockscreenIndicators.prototype._drainPending = function () {
    if (!this._pending || !this._visible) return;
    this._pending = false;
    this._tick();
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
    if (this._inFlight) {
      this._pending = true;
      return;
    }
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
    try { global.document.addEventListener('nuxel:display-on', refresh, { passive: true }); } catch (e) {}
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
    this._pending = false;
    this._wireEvents();
    this._stopTimer();
    /* Render even when the first read equals retained state.  Besides restoring
       ARIA/class truth on every lock, this emits a fresh physical geometry
       receipt for the currently visible lockscreen. */
    this._render();
    this._tick();
    var self = this;
    this._timer = global.setInterval(function () { self._tick(); }, SAFETY_MS);
  };

  LockscreenIndicators.prototype.stop = function () {
    this._visible = false;
    this._generation++;
    this._pending = false;
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
    this._apply(this.transportEls.serial, 'active', this.state.serialConsole);
    this._apply(this.transportEls.usb, 'active', this.state.usbConsole);
    this._apply(this.transportEls.wlan, 'active', this.state.wlanConsole);
    this._apply(this.transportEls.fileTransfer, 'active', this.state.fileTransfer);
    try {
      if (this.container) {
        this.container.dataset.powerSource = this.state.sources.power;
        this.container.dataset.usbSource = this.state.sources.usb;
        this.container.dataset.liveSource = this.state.sources.live;
      }
      if (this.transportContainer) {
        this.transportContainer.dataset.serialSource = this.state.sources.serial;
        this.transportContainer.dataset.usbSource = this.state.sources.usbConsole;
        this.transportContainer.dataset.wlanSource = this.state.sources.wlan;
        this.transportContainer.dataset.transferSource = this.state.sources.transfer;
      }
    } catch (e) {}
    this._renderModeOverlay();
    this._traceGeometry();
  };

  LockscreenIndicators.prototype._renderModeOverlay = function () {
    if (!this.modeOverlay) return;
    var selected = this.state.modeSelected === 'file_transfer' ? 'file_transfer' : 'charging';
    var buttons = this.modeOverlay.querySelectorAll('[data-mode]');
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      var on = b.getAttribute('data-mode') === selected;
      try { b.classList.toggle('selected', on); } catch (e) {}
      try { b.setAttribute('aria-pressed', on ? 'true' : 'false'); } catch (e) {}
      try { b.disabled = !!this.state.modeBusy; } catch (e) {}
    }
    if (this.modeStatus) {
      if (this.state.modeBusy) this.modeStatus.textContent = 'Changing mode…';
      else if (selected === 'file_transfer') {
        this.modeStatus.textContent = this.state.fileTransfer
          ? 'File transfer active'
          : 'File transfer selected, not active';
      } else {
        this.modeStatus.textContent = 'Charging selected';
      }
    }
  };

  /* ---- PWNAGE-34000: lockscreen connection-mode selector --------------- */
  LockscreenIndicators.prototype._wireModeSelector = function () {
    var self = this;
    if (this._modeWired) return;
    this._modeWired = true;
    if (this.modeButton && this.modeOverlay) {
      this.modeButton.addEventListener('click', function (e) {
        e.stopPropagation();
        self._openModeOverlay();
      });
      var dismiss = self.modeOverlay.querySelector('#connection-mode-dismiss');
      if (dismiss) dismiss.addEventListener('click', function (e) {
        e.stopPropagation();
        self._closeModeOverlay();
      });
      var options = self.modeOverlay.querySelectorAll('[data-mode]');
      for (var i = 0; i < options.length; i++) {
        (function (btn) {
          btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var mode = btn.getAttribute('data-mode');
            self._setMode(mode === 'file_transfer' ? 'file_transfer' : 'charging');
          });
        })(options[i]);
      }
      // Tap outside the sheet dismisses it; tapping the sheet keeps it open.
      this.modeOverlay.addEventListener('pointerdown', function (e) {
        if (e.target === self.modeOverlay) self._closeModeOverlay();
      });
    }
  };

  LockscreenIndicators.prototype._openModeOverlay = function () {
    if (!this.modeOverlay) return;
    this.modeOverlay.hidden = false;
    if (this.modeButton) this.modeButton.setAttribute('aria-expanded', 'true');
    this._renderModeOverlay();
  };

  LockscreenIndicators.prototype._closeModeOverlay = function () {
    if (!this.modeOverlay) return;
    this.modeOverlay.hidden = true;
    if (this.modeButton) this.modeButton.setAttribute('aria-expanded', 'false');
  };

  LockscreenIndicators.prototype._setMode = function (mode) {
    var self = this;
    this.state.modeBusy = true;
    this._renderModeOverlay();
    // The authoritative mode actuator is the loopback HTTP bridge.  The native
    // host has no usb-mode verb and would refuse it, so always use the bridge
    // (same-origin, key-authenticated) rather than routing through NuxelHost.
    var request;
    if (typeof global.fetch === 'function') {
      request = global.fetch('http://127.0.0.1:8080/api/v1/usb-mode/set-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode }),
        cache: 'no-store',
      }).then(function (res) {
        return res.json().catch(function () { return {}; });
      }).catch(function (err) { return { success: false, error: String(err && err.message || err) }; });
    } else {
      request = Promise.resolve({ success: false, error: 'no-fetch' });
    }
    request.then(function (res) {
      self.state.modeBusy = false;
      self.state.modeSelected = (res && res.mode) ? res.mode : (res && res.selected) || self.state.modeSelected;
      self.state.fileTransfer = !!(res && res.active);
      if (!res || res.success !== true) {
        self.state.fileTransfer = false;
        if (self.modeStatus) self.modeStatus.textContent = 'Mode change failed' + ((res && res.error) ? (': ' + res.error) : '');
      }
      self._renderModeOverlay();
      self.refresh();
    }, function (err) {
      self.state.modeBusy = false;
      if (self.modeStatus) self.modeStatus.textContent = 'Mode change failed: ' + (err && err.message ? err.message : err);
      self._renderModeOverlay();
      self.refresh();
    });
  };

  LockscreenIndicators.prototype._apply = function (node, className, on) {
    if (!node || !node.classList) return;
    try {
      on ? node.classList.add(className) : node.classList.remove(className);
      if (className === 'active' && typeof node.setAttribute === 'function') {
        node.setAttribute('aria-hidden', on ? 'false' : 'true');
      }
    }
    catch (e) {}
  };

  LockscreenIndicators.prototype._traceGeometry = function () {
    var self = this;
    if (!this._visible || !this.container || !this.container.getBoundingClientRect) return;
    var schedule = global.requestAnimationFrame || function (fn) { global.setTimeout(fn, 0); };
    schedule(function () {
      try {
        var battery = el('lockscreen-battery');
        var row = self.container.getBoundingClientRect();
        var br = battery && battery.getBoundingClientRect ? battery.getBoundingClientRect() : null;
        var lock = el('lockscreen');
        var lr = lock && lock.getBoundingClientRect ? lock.getBoundingClientRect() : null;
        var cs = global.getComputedStyle ? global.getComputedStyle(self.container) : null;
        var visible = [];
        Object.keys(self.els).forEach(function (key) {
          var node = self.els[key];
          if (!node || !node.classList.contains('active') || !node.getBoundingClientRect) return;
          var r = node.getBoundingClientRect();
          visible.push(key + ':' + Math.round(r.left) + ',' + Math.round(r.top) + ',' +
                       Math.round(r.width) + 'x' + Math.round(r.height));
        });
        self._trace('geometry batteryBottom=' + (br ? Math.round(br.bottom) : -1) +
                    ' row=' + Math.round(row.left) + ',' + Math.round(row.top) + ',' +
                    Math.round(row.width) + 'x' + Math.round(row.height) +
                    ' parent=' + (self.container.parentNode && self.container.parentNode.id || '-') +
                    ' offsetParent=' + (self.container.offsetParent && self.container.offsetParent.id || '-') +
                    ' css=' + (cs ? [cs.position, cs.top, cs.bottom].join('/') : '-') +
                    ' lock=' + (lr ? [Math.round(lr.left), Math.round(lr.top), Math.round(lr.width), Math.round(lr.height)].join(',') : '-') +
                    ' vh=' + (global.innerHeight || 0) + ' active=' + visible.join('|'));
      } catch (e) {}
    });
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
    /* A68.2 cached markup nested this row in the bottom handle.  `contains()`
       accepted that stale descendant and kept absolute positioning relative to
       y=579.  Enforce the current contract: a DIRECT lockscreen child. */
    if (this.container.parentNode !== wrap) wrap.appendChild(this.container);
  };

  global.NuxelLockscreenIndicators = LockscreenIndicators;
})(window);
