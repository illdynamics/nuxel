// Nuxel Settings — Keyboard / legacy text-input v1 compatibility.
//
// The switch writes ONLY keyboard.text_input_v1 in
// /etc/nuxel/keyboard/keyboard.json.  nuxel-keyboard-apply.sh is the real
// consumer: it writes /run/nuxel-text-input-v1.enabled, which phoc polls to
// create or remove the opt-in zwp_text_input_manager_v1 global.  This file does
// not execute shell commands and does not claim success until the host reports
// the document write.
(function () {
  'use strict';

  var KEY = 'keyboard.text_input_v1';
  var cb = document.getElementById('keyboard-text-input-v1');
  var out = document.getElementById('keyboard-text-input-v1-state');
  var refresh = document.getElementById('keyboard-text-input-v1-refresh');
  if (!cb) return;

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
    return h.call(method, params);
  }

  function show(text) {
    if (out) out.textContent = text;
  }

  function parse(text) {
    try {
      var doc = JSON.parse(text || '{}');
      return doc && typeof doc === 'object' ? doc : {};
    } catch (e) {
      return {};
    }
  }

  function statusText(disabled, result) {
    var text = result && result.ok && result.text ? String(result.text) : '';
    var m = text.match(/^keyboard\.text_input_v1=(.*)$/m);
    var verdict = m ? m[1].trim() : 'not recorded yet';
    return (disabled ? 'Shim disabled in Settings. ' : 'Shim enabled in Settings. ') +
      'Applier verdict: ' + verdict;
  }

  function readStatus(disabled) {
    return call('status.read', { name: 'keyboard-state' }).then(function (res) {
      show(statusText(disabled, res));
    }, function () {
      show('Could not read the keyboard applier state.');
    });
  }

  function load() {
    show('Reading keyboard document…');
    call('config.get', { name: 'keyboard' }).then(function (res) {
      if (!res || !res.ok) {
        show(res && res.offline ? 'Launcher host unavailable — setting cannot be changed here.'
                                : 'Keyboard document is not readable.');
        cb.disabled = true;
        return;
      }
      var doc = parse(res.text);
      cb.checked = doc[KEY] === true;
      readStatus(!cb.checked);
    }, function () {
      show('Launcher host refused the keyboard document read.');
      cb.disabled = true;
    });
  }

  cb.addEventListener('change', function () {
    var enabled = cb.checked;
    show('Saving ' + (enabled ? 'enabled' : 'disabled') + '…');
    call('config.get', { name: 'keyboard' }).then(function (res) {
      if (!res || !res.ok) throw new Error('document-unreadable');
      var doc = parse(res.text);
      doc[KEY] = enabled;
      doc.schema_version = doc.schema_version || 1;
      doc.set_by = 'user';
      doc.updated_at = Date.now();
      return call('config.set', { name: 'keyboard', text: JSON.stringify(doc, null, 2) });
    }).then(function (res) {
      if (!res || !res.ok) throw new Error('write-refused');
      show('Saved. The applier will update phoc within a second; newly launched apps pick it up now.');
      setTimeout(function () { readStatus(!enabled); }, 1400);
    }).catch(function () {
      cb.checked = !enabled;
      show('Save failed; the setting was not changed.');
    });
  });

  if (refresh) refresh.addEventListener('click', load);
  load();
})();
