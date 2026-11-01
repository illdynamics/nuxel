/* Nuxel Clipper — local clipboard history with explicit, user-visible actions.
 * The Web Clipboard API is permission-gated; a denied read never turns into a
 * fake clip.  Manual entries and copy-to-clipboard work without that permission.
 */
(function () {
  'use strict';
  var K_CLIPS = 'nuxel.clipper.history.v1';
  var K_SETTINGS = 'nuxel.clipper.settings.v1';
  var DEFAULTS = { maxEntries: 100, dedupe: true, trim: true, autoCapture: false };
  var $ = function (id) { return document.getElementById(id); };
  var els = {
    status: $('status'), capture: $('capture'), search: $('search'), add: $('add'),
    clear: $('clear'), settingsToggle: $('settings-toggle'), settings: $('settings'),
    autoCapture: $('auto-capture'), dedupe: $('dedupe'), trim: $('trim'),
    maxEntries: $('max-entries'), count: $('count'), clips: $('clips'),
    copyLatest: $('copy-latest'), dialog: $('add-dialog'), addText: $('add-text'),
    addSave: $('add-save'), toast: $('toast')
  };
  var settings = load(K_SETTINGS, DEFAULTS);
  settings = Object.assign({}, DEFAULTS, settings || {});
  var clips = load(K_CLIPS, []);
  if (!Array.isArray(clips)) clips = [];

  function load(key, fallback) {
    try { var v = JSON.parse(localStorage.getItem(key) || 'null'); return v == null ? fallback : v; }
    catch (e) { return fallback; }
  }
  function save(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {} }
  function now() { return Date.now(); }
  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { els.toast.classList.add('hidden'); }, 2400);
  }
  function textOf(clip) { return clip && typeof clip.text === 'string' ? clip.text : ''; }
  function normalise(text) {
    var value = String(text == null ? '' : text);
    if (settings.trim) value = value.trim();
    return value;
  }
  function addClip(text, source) {
    var value = normalise(text);
    if (!value) { toast('Nothing to save'); return false; }
    if (value.length > 100000) { toast('Clip is too large (100 KB max)'); return false; }
    if (settings.dedupe) clips = clips.filter(function (c) { return textOf(c) !== value; });
    clips.unshift({ id: 'clip-' + now() + '-' + Math.random().toString(36).slice(2, 7),
      text: value, source: source || 'manual', at: now(), pinned: false });
    clips = clips.slice(0, clampMax(settings.maxEntries));
    persist();
    render();
    return true;
  }
  function clampMax(n) { n = Number(n) || 100; return Math.max(5, Math.min(200, n)); }
  function persist() { save(K_CLIPS, clips); }
  function copyText(text) {
    var value = textOf({ text: text });
    if (!value) return Promise.reject(new Error('empty clip'));
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(value).catch(function () { return legacyCopy(value); });
    }
    return legacyCopy(value);
  }
  function legacyCopy(value) {
    return new Promise(function (resolve, reject) {
      try {
        var ta = document.createElement('textarea');
        ta.value = value; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.left = '-9999px';
        document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, ta.value.length);
        var ok = document.execCommand && document.execCommand('copy');
        document.body.removeChild(ta);
        if (ok) resolve(true); else reject(new Error('clipboard write refused'));
      } catch (e) { reject(e); }
    });
  }
  function readClipboard() {
    if (!navigator.clipboard || !navigator.clipboard.readText) {
      return Promise.reject(new Error('this WebKit build has no clipboard read API'));
    }
    return navigator.clipboard.readText();
  }
  function filtered() {
    var q = String(els.search.value || '').trim().toLowerCase();
    if (!q) return clips;
    return clips.filter(function (c) { return textOf(c).toLowerCase().indexOf(q) >= 0; });
  }
  function when(at) {
    try { return new Date(at).toLocaleString(); } catch (e) { return ''; }
  }
  function render() {
    var list = filtered();
    var ordered = list.slice().sort(function (a, b) { return (b.pinned === true) - (a.pinned === true) || b.at - a.at; });
    els.count.textContent = clips.length + (clips.length === 1 ? ' clip' : ' clips');
    els.copyLatest.disabled = !clips.length;
    els.clips.textContent = '';
    if (!ordered.length) {
      var empty = document.createElement('li');
      empty.className = 'clip';
      empty.textContent = clips.length ? 'No clips match that search.' : 'No clips yet. Use “Read clipboard” or “Add text…”.';
      els.clips.appendChild(empty);
      return;
    }
    ordered.forEach(function (clip) {
      var li = document.createElement('li');
      li.className = 'clip' + (clip.pinned ? ' pinned' : '');
      var text = document.createElement('p'); text.className = 'clip-text'; text.textContent = textOf(clip);
      var meta = document.createElement('div'); meta.className = 'clip-meta';
      meta.textContent = when(clip.at) + ' · ' + (clip.source || 'manual') + (clip.pinned ? ' · pinned' : '');
      var actions = document.createElement('div'); actions.className = 'clip-actions';
      actions.appendChild(button('Copy', function () {
        copyText(textOf(clip)).then(function () { toast('Copied'); }).catch(function (e) { toast('Copy failed: ' + e.message); });
      }));
      actions.appendChild(button(clip.pinned ? 'Unpin' : 'Pin', function () {
        clip.pinned = !clip.pinned; persist(); render();
      }));
      actions.appendChild(button('Delete', function () {
        clips = clips.filter(function (c) { return c.id !== clip.id; }); persist(); render();
      }));
      li.appendChild(text); li.appendChild(meta); li.appendChild(actions);
      els.clips.appendChild(li);
    });
  }
  function button(label, fn) {
    var b = document.createElement('button'); b.type = 'button'; b.textContent = label; b.addEventListener('click', fn); return b;
  }
  function applySettingsToUI() {
    els.autoCapture.checked = settings.autoCapture === true;
    els.dedupe.checked = settings.dedupe !== false;
    els.trim.checked = settings.trim !== false;
    els.maxEntries.value = String(clampMax(settings.maxEntries));
  }
  function onCapture() {
    els.capture.disabled = true;
    els.status.textContent = 'Asking WebKit for the clipboard…';
    readClipboard().then(function (text) {
      if (addClip(text, 'clipboard')) {
        els.status.textContent = 'Clipboard captured. Stored only in Clipper.';
      }
    }).catch(function (e) {
      els.status.textContent = 'Clipboard read denied: ' + (e && e.message ? e.message : e) + '. Use “Add text…” instead.';
      toast('Clipboard read was not granted');
    }).finally(function () { els.capture.disabled = false; });
  }
  els.capture.addEventListener('click', onCapture);
  els.search.addEventListener('input', render);
  els.add.addEventListener('click', function () { els.addText.value = ''; els.dialog.showModal(); els.addText.focus(); });
  els.addSave.addEventListener('click', function (ev) {
    ev.preventDefault();
    if (addClip(els.addText.value, 'manual')) { els.dialog.close(); toast('Clip saved'); }
  });
  els.clear.addEventListener('click', function () {
    if (!clips.length) return;
    if (!window.confirm('Delete all ' + clips.length + ' clips? This cannot be undone.')) return;
    clips = []; persist(); render(); toast('Clipboard history cleared');
  });
  els.copyLatest.addEventListener('click', function () {
    if (!clips.length) return;
    copyText(textOf(clips[0])).then(function () { toast('Latest clip copied'); }).catch(function (e) { toast('Copy failed: ' + e.message); });
  });
  els.settingsToggle.addEventListener('click', function () { els.settings.classList.toggle('hidden'); });
  function settingChanged() {
    settings.autoCapture = els.autoCapture.checked;
    settings.dedupe = els.dedupe.checked;
    settings.trim = els.trim.checked;
    settings.maxEntries = clampMax(els.maxEntries.value);
    if (clips.length > settings.maxEntries) clips = clips.slice(0, settings.maxEntries);
    save(K_SETTINGS, settings); persist(); render();
  }
  [els.autoCapture, els.dedupe, els.trim, els.maxEntries].forEach(function (el) {
    el.addEventListener('change', settingChanged);
  });
  applySettingsToUI();
  render();
  if (settings.autoCapture) {
    // Best effort only: a permission denial is reported, never hidden.
    setTimeout(function () {
      readClipboard().then(function (text) {
        if (normalise(text) && !(settings.dedupe && clips.some(function (c) { return textOf(c) === normalise(text); }))) {
          addClip(text, 'auto-open'); toast('Clipboard captured');
        }
      }).catch(function () { /* no permission: manual path stays available */ });
    }, 250);
  }
  // Keep two Clipper windows (or the clipboard helper) consistent.
  window.addEventListener('storage', function (ev) {
    if (ev.key === K_CLIPS) { clips = load(K_CLIPS, []); render(); }
  });
  window.nuxelClipper = { addClip: addClip, copyText: copyText, render: render };
})();
