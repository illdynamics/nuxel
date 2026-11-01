/* Nuxel Settings — PWNAGE-45000 panels
 * DND, notification LED, NFC, fingerprint, security lock and Software.
 * Every value comes from a real Bridge provider; controls remain disabled when
 * the capability probe says the hardware/backend is unavailable.
 */
(function () {
  'use strict';
  function $(id) { return document.getElementById(id); }
  function setText(id, t) { var el = $(id); if (el) el.textContent = t; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); }
  function bridge() {
    if (window.NuxelBridge && window.NuxelBridge.call) return window.NuxelBridge;
    try { if (window.parent && window.parent !== window && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    return null;
  }
  function call(ns, verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable' });
    try { return Promise.resolve(b.call(ns, verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e) }); }
  }
  function json(obj) { try { return JSON.stringify(obj, null, 2); } catch (e) { return String(obj); } }

  var loadToken = {};

  // ---- DND ----------------------------------------------------------------
  function renderDnd(st) {
    if (!st || st.success === false) {
      setText('dnd-state', 'DND provider unavailable' + (st && st.error ? ': ' + st.error : ''));
      setText('dnd-detail', 'The toggle will not paint a fake OFF state.');
      return;
    }
    setText('dnd-state', json({
      active: st.active, enabled: st.enabled, reason: st.reason,
      scheduled: st.scheduled, suppress: (st.policy || {}).suppress,
      exceptions: (st.policy || {}).exceptions,
      last_updated: st.updated_at
    }));
    setText('dnd-detail', st.active
      ? 'DND is active (' + (st.reason || 'manual') + '). Popups/sound/haptics/LED are suppressed; history is retained.'
      : 'DND is off. Notifications are delivered normally.');
    var b = $('dnd-toggle'); if (b) b.textContent = st.active ? 'Turn DND off' : 'Turn DND on';
  }
  function loadDnd() { var t = loadToken.dnd = Date.now(); return call('dnd', 'status', {}).then(function (st) { if (loadToken.dnd === t) renderDnd(st); }); }
  function toggleDnd() {
    var b = $('dnd-toggle'); if (b) b.disabled = true;
    return call('dnd', 'toggle', {}).then(function (r) { if (b) b.disabled = false; renderDnd(r); })
      .catch(function (e) { if (b) b.disabled = false; setText('dnd-detail', 'DND request failed: ' + (e && e.message || e)); });
  }

  // ---- notification LED ---------------------------------------------------
  function renderLed(st) {
    if (!st || st.success === false) { setText('led-state', 'LED provider unavailable' + (st && st.error ? ': ' + st.error : '')); return; }
    setText('led-state', json({
      state: st.state, hardware_led: st.hardware_led, kind: st.kind,
      channels: st.channels, supported_colors: st.supported_colors,
      display_fallback: st.display_fallback, reason: st.reason, max_on_ms: st.max_on_ms
    }));
    var box = $('led-color-buttons');
    if (!box) return;
    box.innerHTML = '';
    var colors = (st.hardware_led ? st.supported_colors : ['red', 'green', 'blue']);
    colors.forEach(function (c) {
      var btn = document.createElement('button');
      btn.type = 'button'; btn.textContent = 'Test ' + c;
      btn.addEventListener('click', function () {
        setText('led-result', 'Requesting ' + c + '…');
        call('led-notification', 'test', { color: c, duration_ms: 1800 }).then(function (r) {
          setText('led-result', r && r.success !== false
            ? (c + ': ' + r.state + (r.hardware_led ? ' (hardware LED)' : ' (display edge-light fallback — not a hardware LED)'))
            : ('Refused: ' + ((r && (r.error || r.reason)) || 'provider unavailable')));
        });
      });
      box.appendChild(btn);
    });
    if (!st.hardware_led) {
      var note = document.createElement('p'); note.className = 'hint';
      note.textContent = 'No physical front notification LED class on this kernel. Tests use the bounded nuxel-wl-fb display overlay and are labelled as such.';
      box.appendChild(note);
    }
  }
  function loadLed() { var t = loadToken.led = Date.now(); return call('led-notification', 'status', {}).then(function (st) { if (loadToken.led === t) renderLed(st); }); }

  // ---- NFC ----------------------------------------------------------------
  function renderNfc(st) {
    if (!st || st.success === false) { setText('nfc-state', 'NFC provider unavailable' + (st && st.error ? ': ' + st.error : '')); return; }
    setText('nfc-state', json({
      supported: st.supported, enabled: st.enabled, state: st.state,
      controller: st.controller, firmware: st.firmware, userspace: st.userspace,
      mode: st.mode, blocker: st.blocker, tag_test_supported: st.tag_test_supported
    }));
    setText('nfc-detail', st.blocker || 'NFC reader is ready; present a tag for the physical proof.');
    var t = $('nfc-toggle'), test = $('nfc-test');
    if (t) { t.disabled = !st.supported; t.textContent = st.supported ? (st.enabled ? 'Disable NFC' : 'Enable NFC') : 'NFC unavailable'; }
    if (test) test.disabled = !st.tag_test_supported;
  }
  function loadNfc() { var t = loadToken.nfc = Date.now(); return call('nfc', 'status', {}).then(function (st) { if (loadToken.nfc === t) renderNfc(st); }); }
  function toggleNfc() {
    var b = $('nfc-toggle'); if (b) b.disabled = true;
    call('nfc', 'toggle', {}).then(function (r) {
      if (b) b.disabled = false;
      renderNfc(r);
      if (r && r.success === false) setText('nfc-detail', 'NFC unchanged: ' + (r.error || r.blocker || 'not supported'));
    });
  }
  function testNfc() {
    setText('nfc-test-result', 'Waiting up to 15 s for a tag…');
    call('nfc', 'test-tag', {}).then(function (r) {
      setText('nfc-test-result', r && r.success ? ('Tag UID: ' + (r.uid || 'unknown')) : ('Tag test refused: ' + ((r && (r.error || r.blocker)) || 'unsupported')));
    });
  }

  // ---- fingerprint --------------------------------------------------------
  function renderFp(st) {
    if (!st || st.success === false) { setText('fp-state', 'Fingerprint provider unavailable' + (st && st.error ? ': ' + st.error : '')); return; }
    setText('fp-state', json({
      supported: st.supported, ready: st.ready, state: st.state, sensor: st.sensor,
      provider: st.provider, enrolled: st.enrolled, slots: st.slots, blocker: st.blocker,
      template_policy: st.template_policy
    }));
    setText('fp-detail', st.blocker || 'Secure provider ready; enrollment is available.');
    var en = $('fp-enroll'), te = $('fp-test');
    if (en) en.disabled = !st.enrollment_supported;
    if (te) te.disabled = !st.test_supported;
    setText('fp-result', st.enrollment_supported ? 'Provider ready.' : 'Enrollment/test disabled: no secure provider.');
  }
  function loadFp() { var t = loadToken.fp = Date.now(); return call('fingerprint', 'status', {}).then(function (st) { if (loadToken.fp === t) renderFp(st); }); }

  // ---- security -----------------------------------------------------------
  var selectedMode = null;
  function renderSecurity(st) {
    if (!st || st.success === false) { setText('sec-state', 'Security provider unavailable' + (st && st.error ? ': ' + st.error : '')); return; }
    setText('sec-state', json({
      mode: st.mode, locked: st.locked, reason: st.reason, credential_set: st.credential_set,
      pin_fallback_set: st.pin_fallback_set, fingerprint: st.fingerprint,
      rate_limit: st.rate_limit, kdf: st.kdf
    }));
    var box = $('sec-modes');
    if (box) {
      box.innerHTML = '';
      ['swipe', 'pattern', 'pin', 'fingerprint'].forEach(function (m) {
        var b = document.createElement('button');
        b.type = 'button'; b.dataset.mode = m;
        b.textContent = m.charAt(0).toUpperCase() + m.slice(1);
        if (m === st.mode) b.classList.add('primary');
        if (m === 'fingerprint' && !(st.fingerprint && st.fingerprint.selectable)) {
          b.disabled = true; b.title = 'Secure fingerprint provider not ready';
        }
        if (selectedMode === m) b.classList.add('primary');
        b.addEventListener('click', function () {
          selectedMode = m;
          Array.prototype.forEach.call(box.querySelectorAll('button'), function (x) { x.classList.toggle('primary', x.dataset.mode === m); });
          setText('sec-result', 'Selected ' + m + '. Enter the required credentials and apply.');
        });
        box.appendChild(b);
      });
    }
  }
  function loadSecurity() { var t = loadToken.sec = Date.now(); return call('security', 'status', {}).then(function (st) { if (loadToken.sec === t) { if (!selectedMode) selectedMode = st.mode; renderSecurity(st); } }); }
  function applySecurity() {
    var mode = selectedMode || ($('sec-modes') && $('sec-modes').querySelector('button.primary') || {}).dataset.mode || 'pin';
    var params = {
      mode: mode,
      secret: ($('sec-secret') && $('sec-secret').value) || '',
      fallback_pin: ($('sec-fallback') && $('sec-fallback').value) || '',
      current_secret: ($('sec-current') && $('sec-current').value) || '',
      confirm_downgrade: !!($('sec-downgrade') && $('sec-downgrade').checked)
    };
    if (!params.current_secret) delete params.current_secret;
    if (!params.fallback_pin) delete params.fallback_pin;
    setText('sec-result', 'Applying…');
    call('security', 'set-mode', params).then(function (r) {
      if (r && r.success === false) {
        setText('sec-result', 'Refused: ' + (r.error || r.detail || 'unknown') + (r.detail && r.detail !== r.error ? ' — ' + r.detail : ''));
      } else {
        setText('sec-result', 'Lock method applied: ' + (r.mode || mode) + '. The session is now locked.');
        ['sec-current', 'sec-secret', 'sec-fallback'].forEach(function (id) { var e = $(id); if (e) e.value = ''; });
      }
      renderSecurity(r);
    });
  }

  // ---- software -----------------------------------------------------------
  function renderSoftware(st) {
    if (!st || st.success === false) {
      setText('software-state', 'Software provider unavailable' + (st && st.error ? ': ' + st.error : ''));
      setText('flatpak-state', 'Flatpak status unknown');
      return;
    }
    setText('software-state', json({
      native_ready: st.native_ready, backend: st.native_backend, ui: st.native_ui,
      rpm: st.native.rpm, dnf: st.native.dnf, dnf5: st.native.dnf5,
      packagekitd: st.native.packagekitd, gnome_software: st.native.gnome_software,
      polkit: st.polkit, appstream: st.native.appstream
    }));
    if (open) open.disabled = !st.native_ui;
    setText('software-detail', st.native_ready
      ? 'Native RPM backend ready. Opening Software requires a polkit agent in the session; transactions always prompt.'
      : 'Native package backend is incomplete: ' + json(st.native));
    setText('flatpak-state', json({
      ready: st.flatpak_ready, blocker: st.flatpak_blocker,
      flatpak: st.flatpak.flatpak, bwrap: st.flatpak.bwrap,
      portal: st.flatpak.portal, user_namespace: st.flatpak.user_namespace
    }));
  }
  function loadSoftware() { var t = loadToken.soft = Date.now(); return call('software', 'status', {}).then(function (st) { if (loadToken.soft === t) renderSoftware(st); }); }
  function openSoftware() {
    fetch('/api/v1/apps/exec', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id: 'nuxel-settings', target: 'org.gnome.Software', source: 'settings' })
    }).then(function (r) { return r.json(); }).then(function (r) {
      setText('software-detail', r && r.success ? ('Software launched (' + (r.outcome || 'started') + ')') :
        ('Launch refused: ' + ((r && (r.error || r.detail)) || 'unknown')));
    }).catch(function (e) { setText('software-detail', 'Launch failed: ' + (e && e.message || e)); });
  }

  // ---- tab loading (only on selection, with stale-request tokens) ---------
  var loaders = { notifications: function () { return Promise.all([loadDnd(), loadLed()]); },
                  nfc: loadNfc, fingerprint: loadFp, security: loadSecurity, software: loadSoftware };
  document.querySelectorAll('.tab').forEach(function (t) {
    t.addEventListener('click', function () {
      var fn = loaders[t.dataset.tab];
      if (fn) Promise.resolve(fn()).catch(function (e) { console.warn('[settings] load failed', t.dataset.tab, e); });
    });
  });

  var wire = function (id, fn) { var e = $(id); if (e) e.addEventListener('click', fn); };
  wire('dnd-refresh', loadDnd);
  wire('dnd-toggle', toggleDnd);
  wire('nfc-refresh', loadNfc);
  wire('nfc-toggle', toggleNfc);
  wire('nfc-test', testNfc);
  wire('fp-refresh', loadFp);
  wire('sec-apply', applySecurity);
  wire('software-refresh', loadSoftware);
  wire('software-open', openSoftware);
})();
