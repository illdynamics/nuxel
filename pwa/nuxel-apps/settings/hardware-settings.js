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
        ? 'MISSING (CONFIG_BT_HCIUART is not set)'
        : (st.kernel_hci_transport === true ? 'present' : 'unknown')),
      'HCD firmware   : ' + (st.firmware_present ? (st.firmware_found || []).join(', ') : 'missing'),
      'BlueZ adapters : ' + (st.adapters && st.adapters.length ? st.adapters.length : 0),
      'powered        : ' + (st.powered === true ? 'on' : (st.powered === false ? 'off' : 'unknown'))
    ];
    if (st.blocker) lines.push('blocker        : ' + st.blocker);
    if (st.detail) lines.push('detail         : ' + st.detail);
    setText('bt-state', lines.join('\n'));
    setText('bt-detail', st.blocker === 'BLOCKED_KERNEL'
      ? 'The BCM4375 radio and its HCD can be powered, but this 4.14.253 kernel was built with CONFIG_BT_HCIUART not set. bcm43xx_bluetooth is only the power/rfkill driver, so no HCI transport can register hci0 and scanning cannot return devices. This is a kernel-configuration blocker, not a missing blob or a UI bug; fixing it requires a scoped kernel rebuild (never a userspace fake).'
      : (st.blocker === 'BLOCKED_FIRMWARE'
        ? 'The Broadcom BCM43xx HCD firmware blob is missing from /lib/firmware/brcm, so the controller powers on but never registers hci0. Deploying that blob is a userspace file step (never a kernel/partition flash) and needs an owner-verified, licence-validated file.'
        : (st.adapter_present ? 'Use the Bluetooth Quick Setting or this button to power the controller.' : 'No hci0 is registered. This page reports the real blocker; it does not pretend the radio works.')));
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

  // ---- Displays ----------------------------------------------------------
  function renderDisplays(st) {
    if (!st || st.success === false) {
      setText('display-state', 'Display provider unavailable' + (st && st.error ? (': ' + st.error) : ''));
      return;
    }
    var ports = (st.type_c_ports || []).map(function (p) {
      return (p.name || '?') + ' role=' + (p.data_role || '?') + '/' + (p.power_role || '?') +
        (p.partner ? (' partner=' + p.partner) : ' (no partner)');
    });
    var ext = (st.extcon || []).map(function (e) { return (e.name || '?') + '=' + (e.state || '?'); });
    var lines = [
      'state             : ' + (st.state || 'unknown'),
      'DRM present       : ' + (st.drm_present ? 'yes' : 'no'),
      'kernel CONFIG_DRM : ' + (st.drm_kernel || 'unknown'),
      'kernel CONFIG_TYPEC: ' + (st.typec_kernel || 'unknown'),
      'displayport driver: ' + (st.displayport_kernel || 'unknown'),
      'Type-C ports      : ' + (ports.length ? ports.join(', ') : 'none'),
      'extcon            : ' + (ext.length ? ext.join(', ') : 'none'),
      'Mirror supported  : ' + (st.mirror_supported ? 'yes' : 'no'),
      'Desktop supported : ' + (st.desktop_supported ? 'yes' : 'no')
    ];
    if (st.blocker) lines.push('blocker           : ' + st.blocker);
    setText('display-state', lines.join('\n'));
    setText('display-detail', st.drm_present
      ? 'An external DRM output path exists; further connector/mode enumeration is needed.'
      : 'No DRM/KMS exists on this kernel (CONFIG_DRM is not set) and the image renders via the framebuffer backend. USB-C DisplayPort Alt Mode video therefore cannot be driven by userspace today — Mirror/Desktop are honestly unavailable, not hidden.');
  }
  function refreshDisplays() {
    setText('display-state', 'Checking display path…');
    return call('display', 'status', {}).then(renderDisplays);
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
    setText('audio-state', lines.join('\n'));
    return st;
  }
  function refreshAudio() {
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
  function setVolume(delta) {
    return call('audio', 'status', {}).then(function (st) {
      var cur = (st && typeof st.volume_percent === 'number') ? st.volume_percent : 10;
      var next = Math.max(0, Math.min((st && st.volume_cap_percent) || 25, cur + delta));
      return call('audio', 'set-volume', { volume: next }).then(function (r) {
        setText('volume-state', (r && r.success === false)
          ? ('Volume unchanged: ' + (r.error || 'backend error'))
          : ('Volume set to ' + (r.volume_percent !== undefined ? r.volume_percent + '%' : next + '%')));
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

  function bind() {
    var btRefresh = $('bt-refresh');
    if (btRefresh) btRefresh.addEventListener('click', refreshBluetooth);
    var btPower = $('bt-power');
    if (btPower) btPower.addEventListener('click', toggleBluetooth);
    var dRef = $('display-refresh');
    if (dRef) dRef.addEventListener('click', refreshDisplays);
    var aRef = $('audio-refresh');
    if (aRef) aRef.addEventListener('click', refreshAudio);
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
    refreshDisplays();
    refreshAudio();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
