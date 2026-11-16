// Nuxel Camera — completed frontend (A52).
//
// Correctness fixes vs the historical v0.6.3 app:
//   * selected camera device persists independently of stream lifetime
//     (front/rear toggle no longer loses `facingMode` before teardown);
//   * captures are saved as real files through the bridge `camera.capture`
//     verb (never localStorage-as-a-photo-database, never a growing data-URL
//     array, never silently discarding old photos on quota errors);
//   * Photo/Video are distinct behaviours (MediaRecorder for video);
//   * no 1440x3120 hard-coded "ideal" (screen vs sensor resolution);
//   * honest hardware states: NO_CAMERA / PERMISSION_DENIED / hardware
//     present-but-unverified are surfaced, never a synthetic "working" preview.
'use strict';

(function () {
  'use strict';

  var APP_ID = (document.querySelector('meta[name="nuxel-app-id"]') || {}).content
    || 'org.nuxel.Camera';

  var els = {};
  var state = {
    stream: null,
    recorder: null,
    mode: 'photo',           // 'photo' | 'video'
    selectedDeviceId: null,  // persisted independent of stream lifetime
    timer: 0,                // capture timer seconds (0/3/10)
    recording: false,
    recordStart: 0,
    recordTimerId: null,
    permission: 'unknown',   // 'unknown' | 'granted' | 'denied'
    hardware: 'unknown',     // 'unknown' | 'present' | 'absent'
    captureVerified: false,  // authoritative: bridge never claims a frame
    busy: false,
    lastCapture: null,
  };

  function $(id) { return document.getElementById(id); }
  function toast(msg) {
    var t = $('camera-toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.add('hidden'); }, 2600);
  }
  function setStatus(msg, kind) {
    var el = $('camera-status');
    if (!el) return;
    el.textContent = msg;
    el.className = 'camera-status ' + (kind || 'info');
    el.classList.toggle('hidden', !msg);
  }

  function bridge() {
    return (typeof window !== 'undefined' && window.NuxelBridge)
      ? window.NuxelBridge : null;
  }
  function bridgeCall(ns, verb, params, fallback) {
    var b = bridge();
    if (!b || typeof b.call !== 'function') return Promise.resolve(fallback);
    return b.call(ns, verb, params).catch(function () { return fallback; });
  }

  // ---- lifecycle / state --------------------------------------------------
  function updateModeUI() {
    var sel = $('switch-mode');
    if (sel) sel.textContent = state.mode === 'photo' ? '\u{1F3A5}' : '\u{1F4F7}';
    var rec = $('record-indicator');
    if (rec) rec.classList.toggle('hidden', !state.recording);
  }

  function updateIndicator() {
    var ind = $('camera-active-indicator');
    if (ind) ind.classList.toggle('hidden', !(state.stream || state.recording));
  }

  async function requestPermission() {
    // Real, revocable permission flow through the Nuxel portal/bridge.
    var res = await bridgeCall('permissions', 'request', {
      capability: 'camera:capture',
    }, { state: 'denied' });
    state.permission = (res && res.state === 'granted') ? 'granted' : 'denied';
    return state.permission;
  }

  async function checkHardware() {
    var res = await bridgeCall('camera', 'status', {}, { camera_present: false, capture_verified: false });
    state.hardware = (res && res.camera_present) ? 'present' : 'absent';
    state.captureVerified = !!(res && res.capture_verified);
    state.diagnostics = res || {};
    // A65-12: concise top-level truth. The raw V4L2/FIMC-IS audit is moved to
    // the collapsible "Technical diagnostics" panel so the viewfinder never
    // opens onto a debug wall by default.
    if (state.hardware === 'absent') {
      setStatus('Camera hardware not detected.', 'error');
    } else if (!state.captureVerified) {
      setStatus('Camera hardware detected, but live preview is not available on this kernel.', 'warn');
    } else {
      setStatus('Camera ready.', 'ok');
    }
    renderDiagnostics();
    return res;
  }

  function renderDiagnostics() {
    var panel = $('camera-diagnostics-body');
    if (!panel) return;
    var d = state.diagnostics || {};
    var lines = [];
    if (d.camera_present !== undefined) lines.push('camera_present=' + (d.camera_present ? 'true' : 'false'));
    if (d.capture_verified !== undefined) lines.push('capture_verified=' + (d.capture_verified ? 'true' : 'false'));
    if (d.source) lines.push('source=' + d.source);
    if (Number.isFinite(d.video_node_count)) lines.push('video_node_count=' + d.video_node_count);
    if (d.detail) lines.push('detail=' + d.detail);
    if (d.error) lines.push('error=' + d.error);
    panel.textContent = lines.length ? lines.join('\n') : 'No camera diagnostics received from the bridge.';
  }

  async function retryCamera() {
    // Bounded retry: stop any hung stream, re-check permission + hardware, then
    // attempt a fresh preview. Never leaves the shutter busy or a stale stream.
    if (state.busy) return;
    state.busy = true;
    var retryBtn = $('camera-retry');
    if (retryBtn) { retryBtn.disabled = true; retryBtn.classList.add('busy'); }
    setStatus('Retrying camera…', 'info');
    stopStream();
    try {
      if (state.permission !== 'granted') {
        await requestPermission();
        if (state.permission === 'denied') {
          setStatus('Camera permission denied — no camera is activated. Grant access in Settings \u2192 Privacy \u2192 Camera.', 'error');
          return;
        }
      }
      await checkHardware();
      if (state.hardware === 'absent') {
        setStatus('Camera hardware unavailable (NO_CAMERA).', 'error');
        return;
      }
      var ok = await startCamera();
      if (!ok && !state.captureVerified) {
        setStatus('Camera hardware detected, but live preview is not available on this kernel.', 'warn');
      } else if (!ok) {
        setStatus('Camera could not start.', 'error');
      }
    } finally {
      state.busy = false;
      if (retryBtn) { retryBtn.disabled = false; retryBtn.classList.remove('busy'); }
    }
  }

  // ---- device selection (front/rear fixed) --------------------------------
  function currentFacing() {
    try {
      var track = state.stream && state.stream.getVideoTracks()[0];
      var settings = track && track.getSettings && track.getSettings();
      if (settings && settings.facingMode) return settings.facingMode;
      if (settings && settings.deviceId) return settings.deviceId;
    } catch (e) { /* ignore */ }
    return state.selectedDeviceId || null;
  }

  async function nextFacing() {
    // Remember the ACTIVE device BEFORE teardown so we can pick the other one.
    var previous = currentFacing();
    var devices = [];
    try {
      devices = await navigator.mediaDevices.enumerateDevices();
    } catch (e) { /* ignore */ }
    var videoDevices = devices.filter(function (d) { return d.kind === 'videoinput'; });
    var next = null;
    if (videoDevices.length >= 2) {
      var idx = videoDevices.findIndex(function (d) {
        return d.deviceId === previous || d.label === previous
          || (previous === 'environment' && !/front|user/i.test(d.label))
          || (previous === 'user' && /front|user/i.test(d.label));
      });
      next = videoDevices[(idx + 1) % videoDevices.length];
    } else {
      // Fall back to facingMode toggle when device IDs are unavailable.
      next = { facing: previous === 'environment' ? 'user' : 'environment' };
    }
    return next;
  }

  async function startCamera() {
    if (state.permission === 'denied') return false;
    try {
      var constraints = { video: {}, audio: state.mode === 'video' };
      if (state.selectedDeviceId) {
        constraints.video = { deviceId: { exact: state.selectedDeviceId } };
      } else {
        constraints.video = { width: { ideal: 1280 }, height: { ideal: 720 } };
      }
      var stream = await navigator.mediaDevices.getUserMedia(constraints);
      // Stop any previous stream only after the new one is ready.
      stopStream();
      state.stream = stream;
      var video = $('video-preview');
      if (video) {
        video.srcObject = stream;
        await video.play().catch(function () {});
        video.classList.remove('hidden');
      }
      var ph = $('viewfinder-placeholder');
      if (ph) ph.classList.add('hidden');
      // Persist the selected device for the next toggle, before teardown later.
      try {
        var track = stream.getVideoTracks()[0];
        if (track && track.getSettings) state.selectedDeviceId = track.getSettings().deviceId || null;
      } catch (e) { /* ignore */ }
      updateIndicator();
      return true;
    } catch (e) {
      setStatus('Camera not available: ' + (e && e.message ? e.message : e), 'error');
      stopStream();
      return false;
    }
  }

  function stopStream() {
    if (state.stream) {
      try { state.stream.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {}
      state.stream = null;
    }
    var video = $('video-preview');
    if (video) {
      video.srcObject = null;
      video.classList.add('hidden');
    }
    var ph = $('viewfinder-placeholder');
    if (ph) ph.classList.remove('hidden');
    updateIndicator();
  }

  // ---- capture ------------------------------------------------------------
  async function capturePhoto() {
    if (state.busy) return;
    var video = $('video-preview');
    if (!state.stream || !video || !video.videoWidth) {
      setStatus('No live camera frame to capture', 'error');
      return;
    }
    state.busy = true;
    setCaptureDisabled(true);
    try {
      var canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      var ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      // toBlob -> ArrayBuffer -> base64 (bounded), never an ever-growing data-URL array.
      var blob = await new Promise(function (resolve) {
        canvas.toBlob(resolve, 'image/jpeg', 0.92);
      });
      if (!blob) throw new Error('encode failed');
      var buf = await blob.arrayBuffer();
      var data_b64 = base64FromBuffer(new Uint8Array(buf));
      var res = await bridgeCall('camera', 'capture', {
        kind: 'photo', mime: 'image/jpeg', data_b64: data_b64,
      }, { success: false, error: 'bridge offline' });
      if (res && res.success) {
        state.lastCapture = res.capture || null;
        toast('Photo saved');
        flashShutter();
        if (navigator.vibrate) { try { navigator.vibrate(50); } catch (e) {} }
        refreshThumbnail();
      } else {
        setStatus((res && res.error) || 'Save failed', 'error');
      }
    } catch (e) {
      setStatus('Capture failed: ' + (e && e.message ? e.message : e), 'error');
    } finally {
      state.busy = false;
      setCaptureDisabled(false);
    }
  }

  function flashShutter() {
    var f = document.createElement('div');
    f.style.cssText = 'position:fixed;inset:0;background:#fff;z-index:5;animation:fadeOut .3s ease;pointer-events:none;';
    document.body.appendChild(f);
    setTimeout(function () { f.remove(); }, 300);
  }

  function base64FromBuffer(bytes) {
    var CHUNK = 0x8000;
    var out = '';
    for (var i = 0; i < bytes.length; i += CHUNK) {
      out += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    return btoa(out);
  }

  // ---- video --------------------------------------------------------------
  async function startRecording() {
    if (!state.stream) return;
    var mime = pickRecorderMime();
    var rec;
    try {
      rec = new MediaRecorder(state.stream, mime ? { mimeType: mime } : undefined);
    } catch (e) {
      setStatus('Video recording unavailable: ' + (e && e.message ? e.message : e), 'error');
      return;
    }
    var chunks = [];
    rec.ondataavailable = function (ev) { if (ev.data && ev.data.size) chunks.push(ev.data); };
    rec.onerror = function () { setStatus('Recording error', 'error'); stopRecording(true); };
    rec.onstop = async function () {
      var type = rec.mimeType || mime || 'video/webm';
      var blob = new Blob(chunks, { type: type });
      var buf = await blob.arrayBuffer();
      var data_b64 = base64FromBuffer(new Uint8Array(buf));
      var res = await bridgeCall('camera', 'capture', {
        kind: 'video', mime: type, data_b64: data_b64,
      }, { success: false, error: 'bridge offline' });
      if (res && res.success) { toast('Video saved'); refreshThumbnail(); }
      else setStatus((res && res.error) || 'Video save failed', 'error');
    };
    state.recorder = rec;
    state.recording = true;
    state.recordStart = Date.now();
    rec.start(1000);
    updateModeUI(); updateIndicator();
    state.recordTimerId = setInterval(function () {
      var el = $('record-time');
      if (el) {
        var s = Math.floor((Date.now() - state.recordStart) / 1000);
        el.textContent = String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
      }
    }, 250);
  }

  function pickRecorderMime() {
    var candidates = ['video/mp4', 'video/webm', 'video/webm;codecs=vp8'];
    if (!window.MediaRecorder) return null;
    for (var i = 0; i < candidates.length; i++) {
      try { if (MediaRecorder.isTypeSupported(candidates[i])) return candidates[i]; } catch (e) {}
    }
    return null;
  }

  function stopRecording(discard) {
    if (state.recordTimerId) { clearInterval(state.recordTimerId); state.recordTimerId = null; }
    state.recording = false;
    if (state.recorder && state.recorder.state !== 'inactive') {
      if (discard) { try { state.recorder.onstop = null; } catch (e) {} }
      try { state.recorder.stop(); } catch (e) {}
    }
    state.recorder = null;
    updateModeUI(); updateIndicator();
  }

  // ---- gallery / thumbnail -------------------------------------------------
  async function refreshThumbnail() {
    var thumb = $('gallery-btn');
    if (!thumb) return;
    if (state.lastCapture) {
      thumb.textContent = state.mode === 'photo' ? '\u{1F5BC}\uFE0F' : '\u{1F3A5}';
      return;
    }
    var res = await bridgeCall('camera', 'list-captures', { kind: '' }, { captures: [] });
    if (res && Array.isArray(res.captures) && res.captures.length) {
      thumb.textContent = '\u{1F5BC}\uFE0F';
    }
  }

  function openGallery() {
    // Delegate to the standalone Photos app: single verified library.
    var b = bridge();
    if (b && typeof b.openApp === 'function') {
      b.openApp('org.nuxel.Photos');
      return;
    }
    if (window.location) {
      window.location.href = '/pwa/nuxel-apps/photos/index.html';
    }
  }

  // ---- UI wiring -----------------------------------------------------------
  function setCaptureDisabled(disabled) {
    var btn = $('capture-btn');
    if (btn) { btn.disabled = disabled; btn.classList.toggle('busy', disabled); }
  }

  function bindEvents() {
    var cap = $('capture-btn');
    if (cap) cap.addEventListener('click', function () {
      if (state.busy) return;
      if (state.mode === 'photo') capturePhoto();
      else {
        if (state.recording) stopRecording(false);
        else startRecording();
      }
    });

    var sw = $('switch-camera');
    if (sw) sw.addEventListener('click', async function () {
      var next = await nextFacing();
      stopStream();
      if (next && next.deviceId) state.selectedDeviceId = next.deviceId;
      else if (next && next.facing) {
        // facingMode fallback: clear exact device, use facing
        state.selectedDeviceId = null;
        state._facingFallback = next.facing;
      }
      if (state.selectedDeviceId) await startCamera();
      else {
        // facing-mode fallback path
        try {
          var s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: state._facingFallback || 'environment' } });
          stopStream();
          state.stream = s;
          var video = $('video-preview');
          video.srcObject = s; await video.play().catch(function(){}); video.classList.remove('hidden');
          $('viewfinder-placeholder').classList.add('hidden');
          updateIndicator();
        } catch (e) { setStatus('Camera switch failed: ' + (e.message || e), 'error'); }
      }
    });

    var sm = $('switch-mode');
    if (sm) sm.addEventListener('click', function () {
      if (state.recording) stopRecording(false);
      state.mode = state.mode === 'photo' ? 'video' : 'photo';
      updateModeUI();
      // Reopen stream with/without audio as the mode requires.
      stopStream();
      startCamera();
    });

    var gb = $('gallery-btn');
    if (gb) gb.addEventListener('click', openGallery);

    var retry = $('camera-retry');
    if (retry) retry.addEventListener('click', function () {
      if (state.busy) return;
      retryCamera();
    });

    // Power/privacy: release the camera when hidden or the page unloads.
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { stopRecording(true); stopStream(); }
    });
    window.addEventListener('pagehide', function () { stopRecording(true); stopStream(); });
    window.addEventListener('beforeunload', function () { stopRecording(true); stopStream(); });
  }

  async function init() {
    els = {};
    await requestPermission();
    if (state.permission === 'denied') {
      setStatus('Camera permission denied — no camera is activated. Grant access in Settings \u2192 Privacy \u2192 Camera.', 'error');
      return;
    }
    var hw = await checkHardware();
    if (state.hardware === 'absent') {
      setStatus('Camera hardware unavailable (NO_CAMERA). The S10+ FIMC-IS camera stack is not accessible through a standard Linux capture path.', 'error');
    } else if (!state.captureVerified) {
      setStatus('Camera hardware is enumerated but capture is NOT verified on this device (vendor FIMC-IS interface). Live preview may be unavailable.', 'warn');
    }
    bindEvents();
    updateModeUI();
    refreshThumbnail();
    // Attempt a real preview; an honest error replaces the placeholder on failure.
    await startCamera();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
