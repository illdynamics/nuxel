// Nuxel Settings — physical mouse / touchpad / keyboard.
//
// This file is deliberately a thin UI over two REAL documents:
//   /etc/nuxel/input/input.json      pointer settings (libinput shim + GSettings)
//   /etc/nuxel/keyboard/keyboard.json layout/repeat/passthrough (existing applier)
// It never claims a write succeeded unless the launcher host confirmed it, and
// it shows the state files written by the two consumers instead of inventing a
// connected-device list.
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function host() {
    if (window.NuxelHost && window.NuxelHost.available) return window.NuxelHost;
    try {
      if (window.parent && window.parent !== window && window.parent.NuxelHost) return window.parent.NuxelHost;
    } catch (e) { /* cross-origin parent */ }
    return null;
  }
  function call(method, params) {
    var h = host();
    if (!h || typeof h.call !== 'function') return Promise.resolve({ ok: false, offline: true });
    try { return Promise.resolve(h.call(method, params || {})); }
    catch (e) { return Promise.resolve({ ok: false, error: String(e && e.message || e) }); }
  }
  function parse(text) {
    try { var d = JSON.parse(text || '{}'); return d && typeof d === 'object' ? d : {}; } catch (e) { return {}; }
  }
  function msg(text) { var e = $('pi-message'); if (e) e.textContent = text; }

  var DEFAULTS = {
    'mouse.speed': 0, 'mouse.accel_profile': 'default',
    'mouse.natural_scroll': false, 'mouse.left_handed': false, 'mouse.middle_emulation': false,
    'touchpad.speed': 0, 'touchpad.accel_profile': 'default',
    'touchpad.natural_scroll': true, 'touchpad.tap_to_click': true,
    'touchpad.two_finger_scroll': true, 'touchpad.disable_while_typing': true,
    'touchpad.left_handed': false
  };
  var KBD_DEFAULTS = {
    'keyboard.layout': 'us', 'keyboard.key_repeat': true,
    'keyboard.key_repeat_delay_ms': 500, 'keyboard.key_repeat_interval_ms': 30,
    'keyboard.hardware_passthrough': true
  };

  function val(doc, key) { return doc[key] === undefined ? DEFAULTS[key] : doc[key]; }
  function kval(doc, key) { return doc[key] === undefined ? KBD_DEFAULTS[key] : doc[key]; }
  function setCheck(id, on) { var e = $(id); if (e) e.checked = on === true; }
  function setSelect(id, value) { var e = $(id); if (e) e.value = value; }
  function setNum(id, value) { var e = $(id); if (e) e.value = String(value); }
  function setRange(inputId, outId, value) {
    var r = $(inputId); var o = $(outId);
    if (r) r.value = String(value);
    if (o) o.textContent = Number(value).toFixed(2);
  }
  function checked(id) { var e = $(id); return !!(e && e.checked); }
  function number(id, fallback) { var e = $(id); var n = e ? Number(e.value) : NaN; return isFinite(n) ? n : fallback; }
  function string(id, fallback) { var e = $(id); return e && e.value ? e.value : fallback; }

  function bindRange(inputId, outId) {
    var r = $(inputId);
    if (!r) return;
    r.addEventListener('input', function () {
      var o = $(outId); if (o) o.textContent = Number(r.value).toFixed(2);
    });
  }

  function renderPointer(doc) {
    setRange('pi-mouse-speed', 'pi-mouse-speed-val', val(doc, 'mouse.speed'));
    setSelect('pi-mouse-accel', val(doc, 'mouse.accel_profile'));
    setCheck('pi-mouse-natural', val(doc, 'mouse.natural_scroll'));
    setCheck('pi-mouse-left', val(doc, 'mouse.left_handed'));
    setCheck('pi-mouse-middle', val(doc, 'mouse.middle_emulation'));
    setRange('pi-touchpad-speed', 'pi-touchpad-speed-val', val(doc, 'touchpad.speed'));
    setSelect('pi-touchpad-accel', val(doc, 'touchpad.accel_profile'));
    setCheck('pi-touchpad-natural', val(doc, 'touchpad.natural_scroll'));
    setCheck('pi-touchpad-tap', val(doc, 'touchpad.tap_to_click'));
    setCheck('pi-touchpad-two', val(doc, 'touchpad.two_finger_scroll'));
    setCheck('pi-touchpad-dwt', val(doc, 'touchpad.disable_while_typing'));
    setCheck('pi-touchpad-left', val(doc, 'touchpad.left_handed'));
  }

  function renderKeyboard(doc) {
    setSelect('pi-keyboard-layout', kval(doc, 'keyboard.layout'));
    setCheck('pi-keyboard-repeat', kval(doc, 'keyboard.key_repeat'));
    setNum('pi-keyboard-delay', kval(doc, 'keyboard.key_repeat_delay_ms'));
    setNum('pi-keyboard-interval', kval(doc, 'keyboard.key_repeat_interval_ms'));
    setCheck('pi-keyboard-passthrough', kval(doc, 'keyboard.hardware_passthrough'));
  }

  function load() {
    return call('config.get', { name: 'input' }).then(function (r) {
      if (!r || !r.ok) throw new Error(r && r.offline ? 'host-offline' : 'input-document-unreadable');
      renderPointer(parse(r.text));
      return call('config.get', { name: 'keyboard' });
    }).then(function (r) {
      if (!r || !r.ok) throw new Error('keyboard-document-unreadable');
      renderKeyboard(parse(r.text));
      msg('Loaded. ' + (host() ? 'Changes are written to the real documents.' : 'Launcher host unavailable.'));
      return refreshState();
    }).catch(function (e) {
      msg('Could not load physical input settings: ' + (e && e.message ? e.message : e) +
          '. The panel is read-only here.');
      var ids = ['pi-save-pointer', 'pi-save-keyboard', 'pi-refresh'];
      ids.forEach(function (id) { var b = $(id); if (b) b.disabled = true; });
    });
  }

  function savePointer() {
    var speed = number('pi-mouse-speed', 0);
    var tpSpeed = number('pi-touchpad-speed', 0);
    speed = Math.max(-1, Math.min(1, speed));
    tpSpeed = Math.max(-1, Math.min(1, tpSpeed));
    msg('Saving pointer settings…');
    return call('config.get', { name: 'input' }).then(function (r) {
      var doc = (r && r.ok) ? parse(r.text) : {};
      doc.schema_version = doc.schema_version || 1;
      doc['mouse.speed'] = speed;
      doc['mouse.accel_profile'] = string('pi-mouse-accel', 'default');
      doc['mouse.natural_scroll'] = checked('pi-mouse-natural');
      doc['mouse.left_handed'] = checked('pi-mouse-left');
      doc['mouse.middle_emulation'] = checked('pi-mouse-middle');
      doc['touchpad.speed'] = tpSpeed;
      doc['touchpad.accel_profile'] = string('pi-touchpad-accel', 'default');
      doc['touchpad.natural_scroll'] = checked('pi-touchpad-natural');
      doc['touchpad.tap_to_click'] = checked('pi-touchpad-tap');
      doc['touchpad.two_finger_scroll'] = checked('pi-touchpad-two');
      doc['touchpad.disable_while_typing'] = checked('pi-touchpad-dwt');
      doc['touchpad.left_handed'] = checked('pi-touchpad-left');
      doc.set_by = 'user';
      doc.updated_at = Date.now();
      return call('config.set', { name: 'input', text: JSON.stringify(doc, null, 2) + '\n' });
    }).then(function (r) {
      if (!r || !r.ok) throw new Error('write-refused');
      msg('Pointer settings saved. The shim applies them to libinput now; the GSettings applier mirrors them for phoc.');
      return new Promise(function (resolve) { setTimeout(resolve, 700); }).then(loadStateOnly);
    }).catch(function (e) {
      msg('Pointer settings were NOT saved: ' + (e && e.message ? e.message : e));
    });
  }

  function saveKeyboard() {
    var delay = Math.max(100, Math.min(2000, Math.round(number('pi-keyboard-delay', 500))));
    var interval = Math.max(10, Math.min(200, Math.round(number('pi-keyboard-interval', 30))));
    msg('Saving physical keyboard settings…');
    return call('config.get', { name: 'keyboard' }).then(function (r) {
      var doc = (r && r.ok) ? parse(r.text) : {};
      doc.schema_version = doc.schema_version || 1;
      doc['keyboard.layout'] = string('pi-keyboard-layout', 'us');
      doc['keyboard.key_repeat'] = checked('pi-keyboard-repeat');
      doc['keyboard.key_repeat_delay_ms'] = delay;
      doc['keyboard.key_repeat_interval_ms'] = interval;
      doc['keyboard.hardware_passthrough'] = checked('pi-keyboard-passthrough');
      doc.set_by = 'user';
      doc.updated_at = Date.now();
      return call('config.set', { name: 'keyboard', text: JSON.stringify(doc, null, 2) + '\n' });
    }).then(function (r) {
      if (!r || !r.ok) throw new Error('write-refused');
      setNum('pi-keyboard-delay', delay);
      setNum('pi-keyboard-interval', interval);
      msg('Keyboard settings saved. nuxel-keyboard-apply.sh applies the XKB layout and repeat values to phoc within a second.');
      return new Promise(function (resolve) { setTimeout(resolve, 1200); }).then(loadStateOnly);
    }).catch(function (e) {
      msg('Keyboard settings were NOT saved: ' + (e && e.message ? e.message : e));
    });
  }

  function textOf(res, label) {
    if (!res || !res.ok) return label + ': unavailable' + (res && res.offline ? ' (launcher host offline)' : '');
    return label + ':\n' + String(res.text || '').trim();
  }

  function loadStateOnly() {
    return Promise.all([
      call('status.read', { name: 'input-state' }),
      call('status.read', { name: 'input-gsettings-state' }),
      call('status.read', { name: 'keyboard-state' })
    ]).then(function (rs) {
      var out = $('pi-state');
      if (!out) return;
      out.textContent = textOf(rs[0], 'Discovered devices and libinput values') + '\n\n' +
                        textOf(rs[1], 'GSettings applier') + '\n\n' +
                        textOf(rs[2], 'Keyboard applier');
    }, function () {
      var out = $('pi-state'); if (out) out.textContent = 'State reads failed; settings were not changed.';
    });
  }

  function refreshState() {
    var out = $('pi-state'); if (out) out.textContent = 'Reading device state…';
    return loadStateOnly();
  }

  function init() {
    bindRange('pi-mouse-speed', 'pi-mouse-speed-val');
    bindRange('pi-touchpad-speed', 'pi-touchpad-speed-val');
    var sp = $('pi-save-pointer'); if (sp) sp.addEventListener('click', savePointer);
    var sk = $('pi-save-keyboard'); if (sk) sk.addEventListener('click', saveKeyboard);
    var rf = $('pi-refresh');
    if (rf) rf.addEventListener('click', function () { msg('Refreshing…'); load(); });
    load();
  }

  init();
})();
