// Nuxel Settings — Bluetooth, Displays and Audio (PWNAGE 29000)
//
// These three pages consume the SAME authoritative hardware providers as Quick
// Settings (bluetooth.status) or the privileged HTTP-bridge hardware providers
// (audio.*, display.status).  No state here is invented: a missing control, a
// missing DRM path or a missing controller is shown as an actionable error.
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  function bridge() {
    if (window.NuxelBridge && window.NuxelBridge.call) return window.NuxelBridge;
    try {
      if (window.parent && window.parent !== window && window.parent.NuxelBridge &&
          window.parent.NuxelBridge.call) return window.parent.NuxelBridge;
    } catch (e) {}
    return null;
  }
  function call(ns, verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, state: 'unavailable', error: 'Nuxel bridge unavailable' });
    try { return Promise.resolve(b.call(ns, verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, state: 'unavailable', error: String(e && e.message || e) }); }
  }
  function setText(id, text) { var el = $(id); if (el) el.textContent = text; }
  // PWNAGE-52000: every provider refresh is bounded.  A slow external
  // connector scan must never leave a permanent spinner or block the
  // independent Graphics Acceleration card above it.
  var _displayReq = 0;
  function callBounded(ns, verb, params, timeoutMs) {
    var req = Promise.resolve(call(ns, verb, params));
    var timer;
    var timeout = new Promise(function (resolve) {
      timer = setTimeout(function () {
        resolve({ success: false, timeout: true, state: 'timeout',
                  error: 'no response within ' + Math.round(timeoutMs / 1000) + ' s' });
      }, timeoutMs);
    });
    return Promise.race([req, timeout]).then(function (r) {
      if (timer) clearTimeout(timer);
      return r;
    }, function (e) {
      if (timer) clearTimeout(timer);
      return { success: false, error: String(e && e.message || e) };
    });
  }

  // ---- Bluetooth ---------------------------------------------------------
  function renderBluetooth(st) {
    if (!st || st.success === false) {
      setText('bt-state', 'Bluetooth provider unavailable' + (st && st.error ? (': ' + st.error) : ''));
      setText('bt-detail', 'The bridge did not answer. Retry when the service is available.');
      return;
    }
    var lines = [
      'state          : ' + (st.state || 'unknown'),
      'controller     : ' + (st.adapter_present ? ((st.hci_devices || []).join(', ')) : 'no hci0 registered'),
      'rfkill         : ' + (st.rfkill_present
        ? ('present' + (st.rfkill_soft_blocked ? ', soft-blocked' : ', unblocked') +
           (st.rfkill_hard_blocked ? ', HARD-blocked' : ''))
        : 'absent'),
      'radio name     : ' + ((st.rfkill_names && st.rfkill_names.length) ? st.rfkill_names.join(', ') : 'none'),
      'kernel driver  : ' + (st.kernel_bt_driver || 'unknown'),
      'HCI transport  : ' + (st.kernel_hci_transport === false
        ? 'MISSING (no HCI UART/USB transport in this kernel build)'
        : (st.kernel_hci_transport === true ? 'present' : 'unknown')),
      'HCD firmware   : ' + (st.firmware_present ? (st.firmware_found || []).join(', ') : 'missing'),
      'BlueZ adapters : ' + (st.adapters && st.adapters.length ? st.adapters.length : 0),
      'powered        : ' + (st.powered === true ? 'on' : (st.powered === false ? 'off' : 'unknown')),
      'discovering    : ' + (st.discovering === true ? 'active' : (st.discovering === false ? 'idle' : 'unknown'))
    ];
    if (st.adapter_address) lines.push('address        : ' + st.adapter_address);
    if (st.blocker) lines.push('blocker        : ' + st.blocker);
    if (st.detail) lines.push('detail         : ' + st.detail);
    setText('bt-state', lines.join('\n'));
    setText('bt-detail', st.blocker === 'BLOCKED_KERNEL'
      ? 'No HCI transport is present in this kernel build, so a controller cannot register hci0. The verified S10+ image enables CONFIG_BT_HCIUART + H4 and starts btattach; if this row appears on a rebuilt image, that kernel config or the btattach unit is missing.'
      : (st.blocker === 'BLOCKED_FIRMWARE'
        ? 'The Broadcom BCM43xx HCD firmware blob is missing from /lib/firmware/brcm, so the controller powers on but never registers hci0. Deploying that blob is a userspace file step (never a kernel/partition flash) and needs an owner-verified, licence-validated file.'
        : (st.adapter_present
          ? 'Controller ' + (st.hci_devices || []).join(', ') + ' is registered' +
            (st.powered === true ? ' and powered.' : ' but BlueZ does not report it powered.') +
            ' Use Scan to discover peers; pairing and connection actions report the actual BlueZ result.'
          : 'No hci0 is registered. This page reports the real blocker; it does not pretend the radio works.')));
  }
  function refreshBluetooth() {
    setText('bt-state', 'Checking Bluetooth…');
    return call('bluetooth', 'status', {}).then(renderBluetooth);
  }
  function toggleBluetooth() {
    var btn = $('bt-power');
    if (btn) btn.disabled = true;
    setText('bt-state', 'Requesting Bluetooth power change…');
    return call('bluetooth', 'status', {}).then(function (st) {
      var want = !(st && st.powered === true);
      return call('bluetooth', 'power', { enabled: want }).then(function (r) {
        if (btn) btn.disabled = false;
        setText('bt-detail', (r && r.error) ? ('Power request failed: ' + r.error) : ('Power request completed; reading back the real state.'));
        return refreshBluetooth();
      });
    }).catch(function (e) {
      if (btn) btn.disabled = false;
      setText('bt-detail', 'Power request failed: ' + (e && e.message ? e.message : e));
      return refreshBluetooth();
    });
  }

  // ---- Bluetooth device manager (PWNAGE 37000) --------------------------
  var BT_CACHE = [];
  function renderBluetoothDevices(devices) {
    var el = $('bt-devices');
    BT_CACHE = devices || [];
    if (!el) return;
    if (!devices || !devices.length) {
      setText('bt-devices', 'No devices found. Run a scan or power the controller.');
      var actions = $('bt-device-actions');
      if (actions) actions.innerHTML = '';
      return;
    }
    var lines = devices.map(function (d, i) {
      return i + '. ' + (d.mac || '?') + '  ' + (d.alias || '') +
        '  paired=' + (d.paired === true ? 'yes' : (d.paired === false ? 'no' : '?')) +
        ' trusted=' + (d.trusted === true ? 'yes' : (d.trusted === false ? 'no' : '?')) +
        ' connected=' + (d.connected === true ? 'yes' : (d.connected === false ? 'no' : '?'));
    });
    setText('bt-devices', lines.join('\n'));
    var box = $('bt-device-actions');
    if (box) {
      box.innerHTML = '';
      devices.forEach(function (d, i) {
        var mac = d.mac;
        if (!mac) return;
        var wrap = document.createElement('div');
        wrap.className = 'row';
        [['Pair', 'pair'], ['Connect', 'connect'], ['Disconnect', 'disconnect'],
         ['Trust', 'trust'], ['Remove', 'remove']].forEach(function (pair) {
          var b = document.createElement('button');
          b.type = 'button';
          b.textContent = pair[0] + ' #' + i;
          b.addEventListener('click', function () {
            btAction(pair[1], mac);
          });
          wrap.appendChild(b);
        });
        box.appendChild(wrap);
      });
    }
  }
  function refreshBluetoothDevices() {
    setText('bt-devices', 'Listing known devices…');
    return call('bluetooth', 'list-devices', {}).then(function (r) {
      if (r && r.success === false) { setText('bt-devices', 'List failed: ' + (r.error || 'unknown')); return; }
      renderBluetoothDevices(r && r.devices);
    });
  }
  function scanBluetooth() {
    setText('bt-devices', 'Scanning for Bluetooth devices (8 s)…');
    return call('bluetooth', 'scan', { duration: 8 }).then(function (r) {
      if (r && r.success === false) { setText('bt-devices', 'Scan failed: ' + (r.error || 'unknown')); return; }
      renderBluetoothDevices(r && r.devices);
      return refreshBluetoothDevices();
    });
  }
  function btAction(verb, mac) {
    setText('bt-action-result', verb + ' ' + mac + ' …');
    var params = { mac: mac };
    if (verb === 'trust') params.trusted = true;
    return call('bluetooth', verb, params).then(function (r) {
      setText('bt-action-result', verb + ' ' + mac + ': ' +
        (r && r.success === false ? ('failed: ' + (r.error || 'unknown'))
          : ((r && r.success === true) ? 'ok' : 'no confirmation') + (r && r.raw ? (' — ' + r.raw) : '')));
      return refreshBluetoothDevices();
    }).catch(function (e) {
      setText('bt-action-result', verb + ' ' + mac + ' error: ' + (e && e.message ? e.message : e));
      return refreshBluetoothDevices();
    });
  }

  // ---- Displays ----------------------------------------------------------
  function renderDisplays(st) {
    if (!st || st.success === false) {
      setText('external-display-state', 'External display provider unavailable' +
        (st && st.timeout ? ' (timed out)' : '') +
        (st && st.error ? (': ' + st.error) : '') +
        '\nThe Graphics Acceleration block above is independent and remains usable.');
      setText('external-display-detail', 'Display discovery failed or exceeded its deadline. Press Refresh connectors to retry; no GPU state was changed.');
      return;
    }
    var ports = (st.type_c_ports || []).map(function (p) {
      return (p.name || '?') + ' role=' + (p.data_role || '?') + '/' + (p.power_role || '?') +
        (p.partner ? ' partner=yes' : ' partner=no');
    });
    var ext = (st.extcon || []).map(function (e) { return (e.name || '?') + '=' + (e.state || '?'); });
    var modes = (st.supported_modes || []).map(function (m) {
      if (!m || !m.width || !m.height) return m && m.raw ? m.raw : null;
      return m.width + 'x' + m.height + (m.refresh ? ('@' + m.refresh) : '');
    }).filter(Boolean);
    var extFb = st.external_fb || {};
    var audio = st.audio || {};
    var selected = st.selected_resolution || {};
    var presetText = selected.width && selected.height
      ? (selected.width + 'x' + selected.height + '@' + (selected.refresh || 60))
      : 'auto';
    var lines = [
      'hardware state    : ' + (st.hardware_state || st.state || 'unknown'),
      'selected mode     : ' + (st.mode || 'off'),
      'external timing   : ' + presetText,
      'external rotation : ' + (st.rotation == null ? 0 : st.rotation) + '° ' +
        '(' + (st.mode_fit || 'fit') + ')',
      'Type-C partner    : ' + (st.partner ? 'yes' : 'no'),
      'USB-PD identity   : ' + (st.pd_identity ? ((st.pd_ids || 'yes') + ' type=' + (st.pd_type == null ? '?' : st.pd_type)) : 'none'),
      'DP Alt Mode link  : ' + (st.dp_link ? 'up' : 'down') + ' (secdp=' + (st.secdp == null ? '?' : st.secdp) + ', extcon DP=' + (st.extcon_dp ? '1' : '0') + ')',
      'kernel DP driver  : ' + (st.displayport_kernel || 'unknown'),
      'external fb       : ' + (st.external_fb_present ? ('/dev/fb1 via ' + (extFb.device || 'decon_t')) : 'missing'),
      'EDID/fbdev modes  : ' + (modes.length ? modes.join(', ') : 'none reported'),
      'display name      : ' + (st.display_name || 'not reported'),
      'Mirror available  : ' + (st.mirror_supported ? 'yes' : 'no'),
      'Desktop available : ' + (st.desktop_supported ? 'yes' : 'no'),
      'mirror output     : ' + (st.mirror_output || 'none'),
      'desktop output    : ' + (st.desktop_output || 'none'),
      'HDMI audio        : ' + (audio.available ? 'available' : 'unavailable') +
        (audio.blocker ? (' (' + audio.blocker + ')') : ''),
      'Type-C ports      : ' + (ports.length ? ports.join(', ') : 'none'),
      'extcon            : ' + (ext.length ? ext.join(', ') : 'none')
    ];
    if (st.last_error) lines.push('last mode error   : ' + st.last_error);
    if (st.blocker) lines.push('blocker           : ' + st.blocker);
    setText('external-display-state', lines.join('\n'));

    var detail;
    if (st.state === 'DP_LINK_READY' || st.state === 'MIRRORING' || st.state === 'SEPARATE_DESKTOP') {
      detail = 'The DP link and decon_t path are ready at ' + presetText + '. Mirror portrait keeps the phone upright, mirror landscape rotates 90°, fullscreen crops to fill the TV, and Separate desktop requires a second compositor output.';
    } else if (st.state === 'PARTNER_NO_PD') {
      detail = 'A Type-C adapter is attached but it presents no USB-PD identity. DisplayPort Alt Mode is negotiated with USB-PD structured VDM, so no DP link can start. Use a USB-C DP Alt Mode adapter that supports USB PD; a charge-only or passive adapter cannot carry video.';
    } else if (st.state === 'PD_NO_DP') {
      detail = 'USB-PD identity is present but the DP Alt Mode VDM did not complete. The adapter/CCIC mux or link training is the failing stage; no framebuffer mode was changed.';
    } else if (st.state === 'DP_NO_FB') {
      detail = 'The DP link reports up but the decon_t external framebuffer is missing. This is a kernel/driver-path failure; userspace will not fabricate an output.';
    } else if (st.state === 'DISCONNECTED') {
      detail = 'No USB-C display adapter is attached. The built-in screen and its framebuffer remain untouched.';
    } else {
      detail = 'The display daemon is not reporting a ready external path. The exact blocker is listed above; no mode was applied.';
    }
    setText('external-display-detail', detail);

    var choices = {};
    (st.mode_choices || []).forEach(function (c) { choices[c.mode] = c.supported; });
    var buttons = {
      'display-mode-mirror-portrait': 'mirror-portrait',
      'display-mode-mirror-landscape': 'mirror-landscape',
      'display-mode-fullscreen': 'fullscreen',
      'display-mode-desktop': 'desktop'
    };
    Object.keys(buttons).forEach(function (id) {
      var b = $(id);
      if (b) b.disabled = !(choices[buttons[id]] != null ? choices[buttons[id]] : st.mirror_supported);
    });
    var dBtn = $('display-mode-desktop');
    if (dBtn) dBtn.disabled = !st.desktop_supported;
    var rot = $('display-rotation');
    if (rot) rot.value = String(st.rotation == null ? 0 : st.rotation);
  }

  function refreshDisplays() {
    var req = ++_displayReq;
    setText('external-display-state', 'Checking external connector path (bounded 4 s)…');
    var started = Date.now();
    return callBounded('display', 'status', {}, 4000).then(function (st) {
      if (req !== _displayReq) return st;  // stale response after a newer refresh
      if (st && st.success !== false) st.elapsed_ms = Date.now() - started;
      renderDisplays(st);
      return st;
    });
  }

  function applyDisplayMode(mode) {
    setText('display-mode-result', 'Applying display mode (' + mode + ')…');
    return callBounded('display', 'set-mode', { mode: mode }, 22000).then(function (r) {
      if (r && r.success === true) {
        setText('display-mode-result', 'Display mode applied: ' + (r.mode || mode) +
          (r.output ? (' on ' + r.output) : '') + '.');
      } else {
        var detail = (r && (r.detail || r.error)) || 'display manager did not confirm';
        setText('display-mode-result', 'Display mode failed: ' + detail);
      }
      return refreshDisplays();
    });
  }

  function setDisplayRotation(degrees) {
    setText('display-mode-result', 'Setting external rotation to ' + degrees + '°…');
    return callBounded('display', 'set-rotation', { rotation: Number(degrees) }, 12000).then(function (r) {
      if (r && r.success === true) {
        setText('display-mode-result', 'External rotation set to ' + r.rotation + '°.');
      } else {
        setText('display-mode-result', 'Rotation failed: ' +
          ((r && (r.detail || r.error)) || 'display manager did not confirm'));
      }
      return refreshDisplays();
    });
  }

  function testDisplayNotification() {
    setText('display-mode-result', 'Submitting a test notification…');
    return callBounded('display', 'notify-test', { display_name: 'Test display' }, 5000).then(function (r) {
      setText('display-mode-result', r && r.success
        ? 'Test notification submitted to the Nuxel notification hub. Open Quick Settings to see it.'
        : ('Notification test failed: ' + ((r && (r.detail || r.error)) || 'unknown')));
    });
  }

  // ---- Audio -------------------------------------------------------------
  function renderAudio(st) {
    if (!st || st.success === false) {
      setText('audio-state', 'Audio provider unavailable' + (st && st.error ? (': ' + st.error) : ''));
      return null;
    }
    var cards = (st.cards || []).map(function (c) { return c.index + ': ' + c.name; });
    var pb = (st.playback_devices || []).map(function (d) { return d.id; });
    var cap = (st.capture_devices || []).map(function (d) { return d.id; });
    var lines = [
      'backend        : ' + (st.backend || 'unknown') + ' (sound server: ' + (st.sound_server || 'unknown') + ')',
      'cards          : ' + (cards.length ? cards.join(' | ') : 'none detected'),
      'playback       : ' + (pb.length ? pb.slice(0, 8).join(', ') + (pb.length > 8 ? '…' : '') : 'none'),
      'capture        : ' + (cap.length ? cap.slice(0, 8).join(', ') + (cap.length > 8 ? '…' : '') : 'none'),
      'volume control : ' + (st.volume_control || 'not discovered'),
      'volume         : ' + (typeof st.volume_percent === 'number' ? st.volume_percent + '%' : 'unknown') +
        ' (cap ' + (st.volume_cap_percent || 25) + '%)',
      'muted          : ' + (st.muted === true ? 'yes' : (st.muted === false ? 'no' : 'unknown')),
      'volume supported: ' + (st.volume_supported ? 'yes' : 'no'),
      'mute supported  : ' + (st.mute_supported ? 'yes' : 'no')
    ];
    if (st.mute_supported === false && st.mute_blocker) lines.push('mute blocker   : ' + st.mute_blocker);
    if (st.detail) lines.push('detail         : ' + st.detail);
    var outputs = st.outputs || [];
    if (outputs.length) {
      lines.push('outputs        : ' + outputs.map(function (o) {
        return (o.default ? '★ ' : '') + (o.description || ('id ' + o.id));
      }).join(' | '));
    }
    if (st.selected_output) lines.push('selected       : ' + st.selected_output.description);
    var hdmi = st.hdmi_audio || {};
    lines.push('HDMI/DP audio  : ' + (hdmi.available ? 'available' : 'unavailable') +
      (hdmi.pcm ? (' — ' + hdmi.pcm) : '') +
      (hdmi.sink ? (' → ' + hdmi.sink.name) : ''));
    if (hdmi.blocker) lines.push('HDMI blocker   : ' + hdmi.blocker);
    if (st.playback_available === false) lines.push('playback       : unavailable');
    setText('audio-state', lines.join('\n'));
    var hdmiBtn = $('audio-output-hdmi');
    if (hdmiBtn) hdmiBtn.disabled = !hdmi.available;
    return st;
  }
  function refreshAudio() {
    // PWNAGE-102000: Settings -> Sound now owns output discovery, route
    // selection, volume and mute through the authoritative nuxel-soundd
    // policy.  This legacy diagnostics card is absent; do not issue an old
    // provider refresh that could contend with the manager.
    if (!$('audio-state')) return Promise.resolve(null);
    setText('audio-state', 'Checking audio hardware…');
    return call('audio', 'status', {}).then(function (st) {
      renderAudio(st);
      renderVolumeFrom(st);
      return st;
    });
  }
  function renderVolumeFrom(st) {
    if (!st || !st.volume_supported) {
      setText('volume-state', (st && st.detail) ? ('Volume unsupported: ' + st.detail) : 'Volume unsupported on this audio path.');
      return;
    }
    var base = (st.muted ? 'Muted' : (st.volume_percent + '%')) + ' — ' + (st.volume_control || 'control');
    setText('volume-state', base + (st.mute_supported === false && st.mute_blocker
      ? ('\nMute unavailable: ' + st.mute_blocker) : ''));
  }

  // ---- Test Audio (PWNAGE-38000) ---------------------------------------
  var testAudioBusy = false;
  function testAudio() {
    if (testAudioBusy) return;
    testAudioBusy = true;
    var btn = $('audio-test');
    if (btn) btn.disabled = true;
    setText('test-audio-state', 'Playing nuxel-pow.mp3 through the selected output…');
    return call('audio', 'test-audio', { action: 'other', gain_percent: 100 }).then(function (r) {
      testAudioBusy = false;
      if (btn) btn.disabled = false;
      if (r && r.success === false) {
        setText('test-audio-state', 'Test audio failed: ' + (r.error || 'playback error') +
          (r.detail ? (' — ' + r.detail) : ''));
      } else {
        setText('test-audio-state', 'Playback request completed. ' +
          (r && r.detail ? r.detail : '') +
          ' Confirm audibility with the physical speaker/headphones.');
      }
      return refreshAudio();
    }).catch(function (e) {
      testAudioBusy = false;
      if (btn) btn.disabled = false;
      setText('test-audio-state', 'Test audio error: ' + (e && e.message ? e.message : e));
      return refreshAudio();
    });
  }

  // Play the same sound after a GENUINE volume change (coalesced/debounced).
  var volumeSoundTimer = null;
  function scheduleVolumeSound(previousPercent, nextPercent) {
    if (typeof previousPercent !== 'number' || typeof nextPercent !== 'number') return;
    if (previousPercent === nextPercent) return;
    if (volumeSoundTimer) clearTimeout(volumeSoundTimer);
    volumeSoundTimer = setTimeout(function () {
      volumeSoundTimer = null;
      call('sound', 'play', { action: 'volume' }).catch(function () {});
    }, 120);
  }
  function setVolume(delta) {
    return call('audio', 'status', {}).then(function (st) {
      var cur = (st && typeof st.volume_percent === 'number') ? st.volume_percent : 50;
      var cap = (st && st.volume_cap_percent) || 100;
      var next = Math.max(0, Math.min(cap, cur + delta));
      return call('audio', 'set-volume', { volume: next }).then(function (r) {
        if (r && r.success === false) {
          setText('volume-state', 'Volume unchanged: ' + (r.error || 'backend error'));
        } else {
          setText('volume-state', 'Volume set to ' + (r.volume_percent !== undefined ? r.volume_percent + '%' : next + '%'));
          scheduleVolumeSound(cur, next);
        }
        return refreshAudio();
      });
    });
  }
  function toggleMute() {
    return call('audio', 'status', {}).then(function (st) {
      if (st && st.mute_supported === false) {
        setText('volume-state', 'Mute unavailable: ' + (st.mute_blocker || 'mute is not supported on this codec path.'));
        return refreshAudio();
      }
      return call('audio', 'set-muted', { muted: !(st && st.muted === true) }).then(function (r) {
        setText('volume-state', (r && r.success === false)
          ? ('Mute unchanged: ' + (r.error || 'backend error'))
          : ((r && r.muted) ? 'Muted' : 'Unmuted'));
        return refreshAudio();
      });
    });
  }

  function setAudioOutput(target) {
    setText('test-audio-state', 'Selecting audio output: ' + target + '…');
    return callBounded('audio', 'set-output', { output: target }, 8000).then(function (r) {
      if (r && r.success === true) {
        setText('test-audio-state', 'Audio output selected: ' + (r.output || target) +
          (r.sink ? (' (' + r.sink + ')') : '') + '. Audiability must still be confirmed physically.');
      } else {
        setText('test-audio-state', 'Audio output failed: ' +
          ((r && (r.detail || r.error)) || 'provider did not confirm'));
      }
      return refreshAudio();
    });
  }

  function bind() {
    var btRefresh = $('bt-refresh');
    if (btRefresh) btRefresh.addEventListener('click', refreshBluetooth);
    var btPower = $('bt-power');
    if (btPower) btPower.addEventListener('click', toggleBluetooth);
    var btScan = $('bt-scan');
    if (btScan) btScan.addEventListener('click', scanBluetooth);
    var btList = $('bt-list');
    if (btList) btList.addEventListener('click', refreshBluetoothDevices);
    var dRef = $('display-refresh');
    if (dRef) dRef.addEventListener('click', refreshDisplays);
    var dmPortrait = $('display-mode-mirror-portrait');
    if (dmPortrait) dmPortrait.addEventListener('click', function () { applyDisplayMode('mirror-portrait'); });
    var dmLandscape = $('display-mode-mirror-landscape');
    if (dmLandscape) dmLandscape.addEventListener('click', function () { applyDisplayMode('mirror-landscape'); });
    var dmFull = $('display-mode-fullscreen');
    if (dmFull) dmFull.addEventListener('click', function () { applyDisplayMode('fullscreen'); });
    var dmDesktop = $('display-mode-desktop');
    if (dmDesktop) dmDesktop.addEventListener('click', function () { applyDisplayMode('desktop'); });
    var dmOff = $('display-mode-off');
    if (dmOff) dmOff.addEventListener('click', function () { applyDisplayMode('off'); });
    var dNotify = $('display-notify-test');
    if (dNotify) dNotify.addEventListener('click', testDisplayNotification);
    var dRot = $('display-rotation');
    if (dRot) dRot.addEventListener('change', function () { setDisplayRotation(dRot.value); });
    var aRef = $('audio-refresh');
    if (aRef) aRef.addEventListener('click', refreshAudio);
    var aTest = $('audio-test');
    if (aTest) aTest.addEventListener('click', testAudio);
    var aHdmi = $('audio-output-hdmi');
    if (aHdmi) aHdmi.addEventListener('click', function () { setAudioOutput('hdmi'); });
    var aSpeaker = $('audio-output-speaker');
    if (aSpeaker) aSpeaker.addEventListener('click', function () { setAudioOutput('speaker'); });
    var vDown = $('volume-down');
    if (vDown) vDown.addEventListener('click', function () { setVolume(-5); });
    var vUp = $('volume-up');
    if (vUp) vUp.addEventListener('click', function () { setVolume(5); });
    var vMute = $('volume-mute');
    if (vMute) vMute.addEventListener('click', toggleMute);
  }

  var bridgeTries = 0;
  function boot() {
    bind();
    if (!bridge() && bridgeTries < 12) {
      bridgeTries++;
      setTimeout(boot, 300);
      return;
    }
    bridgeTries = 0;
    refreshBluetooth();
    refreshBluetoothDevices();
    // PWNAGE-52000: connector discovery is independent and bounded.  Start it
    // only after the graphics card has had a chance to paint its first state.
    setTimeout(refreshDisplays, 250);
    refreshAudio();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
