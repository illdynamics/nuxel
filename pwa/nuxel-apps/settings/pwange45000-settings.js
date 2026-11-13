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
  var lastNfcTag = null;
  function renderNfc(st) {
    if (!st || st.success === false) { setText('nfc-state', 'NFC provider unavailable' + (st && st.error ? ': ' + st.error : '')); return; }
    if (st.nfc && typeof st.nfc === 'object' && st.nfc.state) st = st.nfc;  // /system/nfc vs hardware-state envelope
    setText('nfc-state', json({
      supported: st.supported, enabled: st.enabled, state: st.state,
      controller: st.controller, firmware: st.firmware, userspace: st.userspace,
      mode: st.mode, blocker: st.blocker, tag_test_supported: st.tag_test_supported,
      tag_writes_supported: st.tag_writes_supported,
      write_requires_confirmation: st.write_requires_confirmation
    }));
    setText('nfc-detail', st.blocker || 'NFC reader is ready; present a tag for the physical proof.');
    var t = $('nfc-toggle'), test = $('nfc-test');
    if (t) { t.disabled = !st.supported; t.textContent = st.supported ? (st.enabled ? 'Disable NFC' : 'Enable NFC') : 'NFC unavailable'; }
    if (test) test.disabled = !(st.tag_test_supported && st.enabled);
    syncNfcWriteControls(st);
  }
  function syncNfcWriteControls(st) {
    var kind = $('nfc-write-kind'), value = $('nfc-write-value'), confirm = $('nfc-write-confirm'), btn = $('nfc-write');
    var tag = lastNfcTag || {};
    var writable = !!(tag.writable === true || (tag.type2 && tag.type2.writable === true));
    var ready = !!(st && st.enabled && writable && confirm && confirm.checked);
    if (btn) {
      btn.disabled = !ready;
      btn.title = !st || !st.enabled ? 'Enable NFC and scan a tag first'
        : (!writable ? 'The presented tag is not a writable Type 2 tag'
          : (!confirm || !confirm.checked ? 'Confirm the overwrite first' : 'Write the selected NDEF record'));
    }
    if (kind) kind.disabled = !writable;
    if (value) value.disabled = !writable;
    if (confirm) confirm.disabled = !writable;
  }
  function loadNfc() {
    var t = loadToken.nfc = Date.now();
    return call('nfc', 'status', {}).then(function (st) {
      if (loadToken.nfc !== t) return;
      // A provider error is still a real result; never replace it with a mock.
      renderNfc(st);
    }, function (err) {
      if (loadToken.nfc === t) renderNfc({ success: false, error: String(err && err.message || err) });
    });
  }
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
    call('nfc', 'test-tag', { timeout_s: 15, read_ndef: true }).then(function (r) {
      if (r && r.success && r.tag) {
        lastNfcTag = r.tag;
        var nd = r.tag.ndef || {};
        var txt = (nd.records || []).map(function (x) { return x.kind + ': ' + x.preview; }).join(' | ');
        setText('nfc-test-result', 'Tag UID: ' + (r.tag.uid || 'unknown') +
          (r.tag.technology ? (' · ' + r.tag.technology) : '') +
          (txt ? ('\n' + txt) : '') +
          (r.tag.ndef_error ? ('\nNDEF: ' + r.tag.ndef_error) : '') +
          (r.tag.writable ? '\nWritable Type 2 tag: write workflow available.' : '\nTag is not writable.'));
      } else {
        setText('nfc-test-result', 'Tag test refused: ' + ((r && (r.error || r.blocker)) || 'unsupported'));
      }
      loadNfc();
    });
  }
  // ---- NFC debug window (read-only) ---------------------------------------
  var nfcDebugBusy = false;
  function nfcLog(line) {
    var out = $('nfc-debug-out');
    if (!out) return;
    var stamp = new Date().toLocaleTimeString();
    out.textContent += '\n[' + stamp + '] ' + line;
    out.scrollTop = out.scrollHeight;
  }
  function nfcSet(id, v) { setText(id, v == null || v === '' ? '—' : String(v)); }
  function nfcDebugTest() {
    if (nfcDebugBusy) return;
    var dur = Number(($('nfc-debug-duration') || {}).value) || 20;
    nfcDebugBusy = true;
    var btn = $('nfc-test2'); if (btn) btn.disabled = true;
    nfcLog('Test: waiting up to ' + dur + ' s for a tag…');
    nfcSet('nfc-dbg-state', 'scanning');
    nfcSet('nfc-dbg-result', 'waiting');
    call('nfc', 'status', {}).then(function (st) {
      if (st && st.nfc && typeof st.nfc === 'object' && st.nfc.state) st = st.nfc;
      nfcSet('nfc-dbg-controller', (st && st.controller) || (st && st.transport && st.transport.path) || 'unknown');
      if (st && st.enabled === false) nfcLog('NFC is OFF: enable it first (the radio must be on to read a tag).');
    });
    call('nfc', 'test-tag', { timeout_s: dur, read_ndef: true }).then(function (r) {
      nfcDebugBusy = false;
      if (btn) btn.disabled = false;
      nfcSet('nfc-dbg-state', (r && r.state) || 'unknown');
      if (r && r.success && r.tag) {
        var tag = r.tag; var nd = tag.ndef || {};
        var records = (nd.records || []).map(function (x) { return x.kind + ': ' + x.preview; });
        nfcSet('nfc-dbg-result', 'TAG READ OK');
        nfcSet('nfc-dbg-uid', tag.uid || 'unknown');
        nfcSet('nfc-dbg-tech', [tag.technology, tag.protocol, tag.writable ? 'writable' : 'read-only'].filter(Boolean).join(' · '));
        nfcSet('nfc-dbg-ndef', records.length ? records.join(' | ') : (tag.ndef_error || 'no NDEF'));
        nfcLog('Tag read: uid=' + (tag.uid || '?') + ' tech=' + (tag.technology || '?')
          + (tag.ndef_error ? ' ndef=' + tag.ndef_error : ''));
        if (records.length) nfcLog('NDEF: ' + records.join(' | '));
        lastNfcTag = tag;
        syncNfcWriteControls({ enabled: true });
      } else {
        var why = (r && (r.error_code || r.error || r.detail)) || 'no tag';
        nfcSet('nfc-dbg-result', 'NO TAG READ');
        nfcLog('No tag read: ' + why
          + (why === 'NO_TAG' ? ' — re-hold the card flat on the back of the phone.' : ''));
      }
      loadNfc();
    }, function (err) {
      nfcDebugBusy = false;
      if (btn) btn.disabled = false;
      nfcSet('nfc-dbg-result', 'ERROR');
      nfcLog('Test failed: ' + (err && err.message || err));
    });
  }
  function nfcDebugCancel() { call('nfc', 'cancel', {}).then(function () { nfcLog('Stop requested.'); }); }
  function nfcDebugClear() {
    var out = $('nfc-debug-out'); if (out) out.textContent = 'NFC debug ready.';
    ['nfc-dbg-result', 'nfc-dbg-uid', 'nfc-dbg-tech', 'nfc-dbg-ndef'].forEach(function (id) { nfcSet(id, ''); });
  }

  function writeNfc() {
    var kind = $('nfc-write-kind'), value = $('nfc-write-value'), confirm = $('nfc-write-confirm');
    if (!lastNfcTag) { setText('nfc-write-result', 'Scan the expendable tag first.'); return; }
    if (!confirm || !confirm.checked) { setText('nfc-write-result', 'Confirm that this expendable tag may be overwritten.'); return; }
    var v = value ? value.value : '';
    if (!v) { setText('nfc-write-result', 'Enter the text or URI to write.'); return; }
    setText('nfc-write-result', 'Writing and verifying read-back…');
    call('nfc', 'write', { confirm: true, kind: kind ? kind.value : 'text', value: v, language: 'en' }).then(function (r) {
      if (r && r.success && r.verified) {
        setText('nfc-write-result', 'Write verified by read-back: ' + (r.written || kind.value) + ' record.');
        if (r.tag) lastNfcTag = r.tag;
        if (confirm) confirm.checked = false;
      } else {
        setText('nfc-write-result', 'Write failed: ' + ((r && (r.error || r.error_code)) || 'unknown error'));
      }
      loadNfc();
    });
  }

  // ---- fingerprint --------------------------------------------------------
  var fpState = null;
  var fpCeremony = null;
  function renderFp(st) {
    if (!st || st.success === false) {
      setText('fp-state', 'Fingerprint provider unavailable' + (st && st.error ? ': ' + st.error : ''));
      return;
    }
    fpState = st;
    setText('fp-state', json({
      state: st.state, ready: st.ready, sensor: st.sensor && st.sensor.name,
      sensor_type: st.sensor && st.sensor.sensor_type, enrollment_record: st.enrollment_record,
      vault_state: st.vault_state, provider: st.provider, blocker: st.blocker
    }));
    setText('fp-detail', st.blocker || (st.vault_state === 'ready'
      ? 'Vault ready. Enrollment can be completed.'
      : 'Set the Vault password before enrolling a fingerprint.'));
    renderFpSecurity(st);
  }
  function renderFpSecurity(st) {
    st = st || fpState;
    if (!st) return;
    var record = (st.enrollment_record_verified === true) ? 'verified in Vault'
      : (st.enrollment_record === true ? 'record present (Vault locked)'
        : (st.vault_state === 'ready' ? 'none' : 'not verifiable until the Vault is unlocked'));
    var state = {
      state: st.state, eligible: st.enrollment_supported, enrolled: st.enrolled,
      record: record, vault: st.vault_state, scanner_ready: st.ready,
      unlock_supported: st.unlock_supported, blocker: st.blocker
    };
    setText('sec-fp-state', json(state));
    var start = $('sec-fp-start');
    if (start) start.textContent = st.enrolled ? 'Re-enroll fingerprint' : 'Set up fingerprint';
    var enable = $('sec-fp-unlock-enable');
    if (enable) enable.disabled = !(st.enrolled && st.vault_state === 'ready');
    var del = $('sec-fp-delete');
    if (del) del.disabled = !st.enrolled;
  }
  function loadFp() {
    var t = loadToken.fp = Date.now();
    return call('fingerprint', 'status', {}).then(function (st) {
      if (loadToken.fp === t) renderFp(st);
    }, function (err) {
      if (loadToken.fp === t) renderFp({ success: false, error: String(err && err.message || err) });
    });
  }
  function startFpEnrollment() {
    setText('sec-fp-result', 'Starting the secure enrollment ceremony…');
    call('fingerprint', 'ceremony-start', { label: 'Fingerprint' }).then(function (r) {
      if (!r || r.success !== true) {
        var msg = (r && (r.detail || r.error)) || 'unavailable';
        setText('sec-fp-result', 'Enrollment refused: ' + msg);
        if (r && r.guidance && r.guidance.open_app) setText('sec-fp-result',
          'Enrollment refused: ' + msg + '  → open ' + r.guidance.open_app + ' to set that up.');
        return;
      }
      fpCeremony = r;
      var box = $('sec-fp-ceremony');
      if (box) box.hidden = false;
      var commit = $('sec-fp-commit'); if (commit) commit.disabled = true;
      setText('sec-fp-ceremony-status', '0 / 2 touches — ' + (r.instruction || ''));
    });
  }
  function fpTouch(edge) {
    if (!fpCeremony) { setText('sec-fp-result', 'Start the enrollment first.'); return; }
    call('fingerprint', 'ceremony-touch', { edge: edge, token: fpCeremony.token }).then(function (r) {
      if (!r || r.success !== true) {
        setText('sec-fp-ceremony-status', 'Touch refused: ' + ((r && (r.detail || r.error)) || 'unknown'));
        return;
      }
      setText('sec-fp-ceremony-status', r.edges + ' / 2 edge-to-edge touches');
      var commit = $('sec-fp-commit'); if (commit) commit.disabled = !r.enough;
      var lab = $('sec-fp-edge-label'); if (lab) lab.textContent = 'Touch at an edge';
    });
  }
  function fpCommit() {
    if (!fpCeremony) return;
    call('fingerprint', 'ceremony-commit', { token: fpCeremony.token }).then(function (r) {
      if (r && r.success === true) {
        setText('sec-fp-result', 'Fingerprint registered in the Vault (record only; template stays in the TEE).');
        fpCeremony = null;
        var box = $('sec-fp-ceremony'); if (box) box.hidden = true;
        call('security', 'set-biometric-unlock', { enrolled: true }).then(function (){
          loadSecurity(); loadFp();
        });
      } else {
        setText('sec-fp-ceremony-status', 'Enrollment failed: ' + ((r && (r.detail || r.error)) || 'unknown'));
      }
    });
  }
  function fpDelete() {
    call('fingerprint', 'delete', {}).then(function () {
      call('security', 'set-biometric-unlock', { enrolled: false }).then(function () {
        setText('sec-fp-result', 'Fingerprint record removed from the Vault.');
        loadSecurity(); loadFp();
      });
    });
  }
  function fpEnableUnlock() {
    call('security', 'set-biometric-unlock', { enabled: true }).then(function (r) {
      if (r && r.success === false) {
        setText('sec-fp-result', 'Refused: ' + ((r && (r.detail || r.error)) || 'unknown'));
      } else {
        setText('sec-fp-result', 'Fingerprint is now set. When the scanner provider is available the lockscreen shows it; the PIN button stays below it.');
        loadSecurity();
      }
      loadFp();
    });
  }

  // ---- security -----------------------------------------------------------
  var selectedMode = null;
  var patternSeq = [];
  var patternDrawing = false;
  var PATTERN_POS = [0,1,2,3,4,5,6,7,8].map(function (i) {
    return { x: 50 + (i % 3) * 100, y: 50 + Math.floor(i / 3) * 100 };
  });
  function drawPatternTrail() {
    var line = $('sec-pattern-trail');
    if (!line) return;
    line.setAttribute('points', patternSeq.map(function (i) {
      return PATTERN_POS[i].x + ',' + PATTERN_POS[i].y;
    }).join(' '));
    Array.prototype.forEach.call(document.querySelectorAll('#sec-pattern-dots .pattern-dot'), function (d) {
      d.classList.toggle('active', patternSeq.indexOf(Number(d.dataset.dot)) >= 0);
    });
    var set = $('sec-pattern-set');
    if (set) set.disabled = patternSeq.length < 4;
    setText('sec-pattern-status', patternSeq.length
      ? 'Pattern: ' + patternSeq.join('-') + ' — draw it once more? No: press Set pattern, then confirm on the lockscreen.'
      : 'Draw a pattern (at least 4 dots).');
  }
  function buildPatternEditor() {
    var box = $('sec-pattern-dots');
    if (!box || box.children.length) return;
    PATTERN_POS.forEach(function (p, i) {
      var d = document.createElement('div');
      d.className = 'pattern-dot';
      d.dataset.dot = String(i);
      d.style.left = p.x + '%';
      d.style.top = p.y + '%';
      d.innerHTML = '<img src="/assets/nuxel-lockhead.png" alt="">';
      box.appendChild(d);
    });
  }
  function patternPoint(ev) {
    var ed = $('sec-pattern-editor');
    if (!ed) return -1;
    var r = ed.getBoundingClientRect();
    var gx = (ev.clientX - r.left) / r.width * 300;
    var gy = (ev.clientY - r.top) / r.height * 300;
    for (var i = 0; i < 9; i++) {
      if (Math.hypot(gx - PATTERN_POS[i].x, gy - PATTERN_POS[i].y) <= 34) return i;
    }
    return -1;
  }
  function wirePatternEditor() {
    buildPatternEditor();
    var ed = $('sec-pattern-editor');
    if (!ed || ed._wired) return;
    ed._wired = true;
    ed.addEventListener('pointerdown', function (ev) {
      var i = patternPoint(ev); if (i < 0) return;
      ev.preventDefault();
      patternDrawing = true; patternSeq = [i];
      try { ed.setPointerCapture(ev.pointerId); } catch (e) {}
      drawPatternTrail();
    });
    ed.addEventListener('pointermove', function (ev) {
      if (!patternDrawing) return;
      var i = patternPoint(ev);
      if (i >= 0 && patternSeq.indexOf(i) < 0) { patternSeq.push(i); ev.preventDefault(); drawPatternTrail(); }
    });
    ed.addEventListener('pointerup', function () { patternDrawing = false; });
    ed.addEventListener('pointercancel', function () { patternDrawing = false; });
  }

  function renderSecurity(st) {
    if (!st || st.success === false) { setText('sec-state', 'Security provider unavailable' + (st && st.error ? ': ' + st.error : '')); return; }
    setText('sec-state', json({
      mode: st.mode, locked: st.locked, reason: st.reason, credential_set: st.credential_set,
      pin_fallback_set: st.pin_fallback_set, attempt_policy: st.attempt_policy,
      unlimited_attempts: st.unlimited_attempts, fingerprint: st.fingerprint,
      rate_limit: st.rate_limit, kdf: st.kdf
    }));
    var box = $('sec-modes');
    if (box) {
      box.innerHTML = '';
      ['swipe', 'pattern', 'pin', 'fingerprint'].forEach(function (m) {
        var b = document.createElement('button');
        b.type = 'button'; b.dataset.mode = m;
        b.textContent = m === 'swipe' ? 'Swipe' : (m === 'pin' ? 'PIN' : m.charAt(0).toUpperCase() + m.slice(1));
        if (m === st.mode) b.classList.add('primary');
        if (m === 'fingerprint' && !(st.fingerprint && st.fingerprint.selectable)) {
          b.disabled = true; b.title = 'Set a PIN and enable fingerprint first';
        }
        if (m === 'pattern' && !st.pin_fallback_set && st.mode === 'swipe') {
          /* a pattern can be the first credential; setup confirms twice */
        }
        b.addEventListener('click', function () { chooseMode(m); });
        box.appendChild(b);
      });
    }
    var pu = $('sec-policy-unlimited'), pl = $('sec-policy-limited');
    if (pu) pu.classList.toggle('primary', st.attempt_policy === 'unlimited');
    if (pl) pl.classList.toggle('primary', st.attempt_policy === 'limited');
    setText('sec-fp-result', st.fingerprint && st.fingerprint.enrolled
      ? (st.fingerprint.provider_ready ? 'Fingerprint registered; scanner ready.'
        : 'Fingerprint registered in the Vault; the scanner provider is unavailable on this build, so PIN is used.')
      : 'No fingerprint registered yet.');
  }
  function loadVaultStatus() {
    return call('fingerprint', 'vault-status', {}).then(function (vs) {
      if (vs && vs.state) setText('sec-fp-result', vs.initialized
        ? (vs.unlocked ? 'Vault unlocked: ready for fingerprint enrollment.'
          : 'Vault is locked: unlock it before enrolling a fingerprint.')
        : 'Vault has no master password yet: set it in the Vault app before enrolling a fingerprint.');
    });
  }
  function loadSecurity() {
    var t = loadToken.sec = Date.now();
    return call('security', 'status', {}).then(function (st) {
      if (loadToken.sec !== t) return;
      if (!selectedMode) selectedMode = st.mode;
      renderSecurity(st);
      renderFpSecurity();
    });
  }
  function announceMode() {
    try { document.dispatchEvent(new CustomEvent('nuxel:security-mode-changed')); } catch (e) {}
    try { if (window.parent && window.parent !== window) window.parent.postMessage({ type: 'nuxel-security-mode-changed' }, window.location.origin); } catch (e) {}
  }
  function chooseMode(m) {
    selectedMode = m;
    if (m === 'pattern') { wirePatternEditor(); patternSeq = []; drawPatternTrail(); setText('sec-result', 'Draw the pattern in the matrix, then press Set pattern (you will confirm it once more on the lockscreen).'); return; }
    if (m === 'pin') { var p = $('sec-pin'); if (p) p.focus(); setText('sec-result', 'Enter the new PIN twice, then press Set PIN.'); return; }
    if (m === 'fingerprint') { setText('sec-result', 'Set a PIN first, then register the fingerprint above and press Enable fingerprint unlock.'); return; }
    var cur = currentSecret();
    if (!cur) { setText('sec-result', 'Enter the current unlock credential to switch to Swipe.'); return; }
    call('security', 'set-mode', { mode: 'swipe', confirm_downgrade: true, current_secret: cur }).then(function (r) {
      setText('sec-result', r && r.success ? 'Swipe unlock enabled: the credential was removed.' :
        ('Refused: ' + ((r && (r.error || r.detail)) || 'unknown')));
      if (r && r.success) { var c = $('sec-current'); if (c) c.value = ''; }
      announceMode(); loadSecurity();
    });
  }
  function currentSecret() { var e = $('sec-current'); return e ? e.value : ''; }
  function setPin() {
    var p = $('sec-pin'), p2 = $('sec-pin2');
    var v = p ? p.value : '', v2 = p2 ? p2.value : '';
    if (!v) { setText('sec-pin-result', 'Enter a PIN first.'); return; }
    if (v !== v2) { setText('sec-pin-result', 'The two PINs do not match. Nothing was changed.'); return; }
    var params = { pin: v, pin_confirm: v2 };
    var cur = currentSecret(); if (cur) params.current_secret = cur;
    call('security', 'set-pin', params).then(function (r) {
      if (r && r.success) {
        setText('sec-pin-result', 'PIN saved.');
        if (p) p.value = ''; if (p2) p2.value = '';
        var c = $('sec-current'); if (c) c.value = '';
      } else {
        setText('sec-pin-result', 'Refused: ' + ((r && (r.detail || r.error)) || 'unknown'));
      }
      announceMode(); loadSecurity();
    });
  }
  function usePinMode() {
    call('security', 'status', {}).then(function (st) {
      if (!st || st.success === false) { setText('sec-pin-result', 'Security provider unavailable.'); return; }
      if (st.mode === 'pin') { setText('sec-pin-result', 'PIN unlock is already active.'); return; }
      if (!st.pin_fallback_set) { setText('sec-pin-result', 'Set a PIN first (twice), then activate PIN unlock.'); return; }
      /* Switching into PIN mode reuses the stored PIN; the current mode's
         credential proves the owner before anything changes. */
      call('security', 'set-mode', { mode: 'pin', secret: '', current_secret: currentSecret() || undefined })
        .then(function (r) {
          if (r && r.success) { setText('sec-pin-result', 'PIN unlock is now active.'); }
          else setText('sec-pin-result', 'Refused: ' + ((r && (r.detail || r.error)) || 'unknown'));
          announceMode(); loadSecurity();
        });
    });
  }
  function setPatternFromEditor() {
    if (patternSeq.length < 4) { setText('sec-pattern-status', 'Use at least 4 dots.'); return; }
    var first = patternSeq.join('-');
    var cur = currentSecret();
    setText('sec-pattern-status', 'Draw the SAME pattern again in the matrix to confirm.');
    /* local second-entry: the user must redraw; enable confirm on next identical draw */
    if (!wirePatternEditor._first) {
      wirePatternEditor._first = first;
      patternSeq = []; drawPatternTrail();
      $('sec-pattern-set').textContent = 'Confirm pattern';
      return;
    }
    if (wirePatternEditor._first !== first) {
      setText('sec-pattern-status', 'The patterns did not match. Start again.');
      wirePatternEditor._first = null; patternSeq = []; drawPatternTrail();
      $('sec-pattern-set').textContent = 'Set pattern';
      return;
    }
    var params = { pattern: first, pattern_confirm: first };
    if (cur) params.current_secret = cur;
    call('security', 'set-pattern', params).then(function (r) {
      if (r && r.success) {
        setText('sec-pattern-status', 'Pattern set. The session is locked; draw the pattern on the lockscreen to unlock.');
        wirePatternEditor._first = null; patternSeq = []; drawPatternTrail();
        $('sec-pattern-set').textContent = 'Set pattern';
        var c = $('sec-current'); if (c) c.value = '';
        call('security', 'lock', { reason: 'pattern-set' }).then(function () { announceMode(); loadSecurity(); });
      } else {
        setText('sec-pattern-status', 'Refused: ' + ((r && (r.detail || r.error)) || 'unknown'));
        wirePatternEditor._first = null; $('sec-pattern-set').textContent = 'Set pattern';
      }
    });
  }
  function setPolicy(policy) {
    call('security', 'set-attempt-policy', { policy: policy }).then(function (r) {
      setText('sec-policy-result', r && r.success
        ? (policy === 'unlimited' ? 'Unlimited attempts: the phone can no longer lock you out.'
          : 'Limited attempts: a delay starts after repeated failures.')
        : ('Refused: ' + ((r && (r.error || r.detail)) || 'unknown')));
      loadSecurity();
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
                  nfc: loadNfc, fingerprint: function () { return Promise.all([loadFp(), loadSecurity()]); },
                  security: function () { return Promise.all([loadSecurity(), loadFp(), loadVaultStatus()]); },
                  software: loadSoftware };
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
  wire('nfc-test2', nfcDebugTest);
  wire('nfc-debug-cancel', nfcDebugCancel);
  wire('nfc-debug-clear', nfcDebugClear);
  wire('nfc-write', writeNfc);
  var nfcConfirm = $('nfc-write-confirm');
  if (nfcConfirm) nfcConfirm.addEventListener('change', function () { syncNfcWriteControls(null); });
  wire('fp-refresh', loadFp);
  wire('sec-pin-set', setPin);
  wire('sec-pin-mode', usePinMode);
  wire('sec-pattern-set', setPatternFromEditor);
  wire('sec-pattern-clear', function () { wirePatternEditor._first = null; patternSeq = []; drawPatternTrail(); $('sec-pattern-set').textContent = 'Set pattern'; });
  wire('sec-policy-unlimited', function () { setPolicy('unlimited'); });
  wire('sec-policy-limited', function () { setPolicy('limited'); });
  wire('sec-fp-start', startFpEnrollment);
  wire('sec-fp-commit', fpCommit);
  wire('sec-fp-delete', fpDelete);
  wire('sec-fp-unlock-enable', fpEnableUnlock);
  wire('sec-fp-vault', function () { if (window.NuxelBridge && window.NuxelBridge.activateApp) window.NuxelBridge.activateApp('org.nuxel.Vault', 'fingerprint'); });
  wire('fp-security-tab', function () {
    var tab = document.querySelector('.tab[data-tab="security"]');
    if (tab) tab.click();
  });
  document.querySelectorAll('#sec-fp-ceremony [data-edge]').forEach(function (b) {
    b.addEventListener('click', function () { fpTouch(b.dataset.edge); });
  });
  var oval = $('sec-fp-oval');
  if (oval) oval.addEventListener('click', function () { fpTouch(oval.dataset.edge || 'left'); });
  wire('software-refresh', loadSoftware);
  wire('software-open', openSoftware);
})();
