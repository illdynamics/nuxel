(function () {
  'use strict';
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); }
  function validate(p) {
    if (!p || p.schema !== 'nuxel.device-profile/1') throw new Error('unsupported profile schema');
    if (!p.id || !p.device || !p.capabilities || typeof p.capabilities !== 'object') throw new Error('profile is missing required fields');
    return p;
  }
  function cls(state) {
    if (/supported$|supported_kernel|supported_policy/.test(state)) return 'ok';
    if (/blocked|not_supported/.test(state)) return /not_supported/.test(state) ? 'unsupported' : 'blocked';
    return 'fallback';
  }
  function render(p) {
    $('badge').textContent = 'profile: ' + p.id;
    $('device').innerHTML = '<h2>Device</h2>' +
      '<div class="row"><span>Model</span><b>' + esc(p.device) + '</b></div>' +
      '<div class="row"><span>Codename</span><b>' + esc(p.codename) + '</b></div>' +
      '<div class="row"><span>SoC</span><b>' + esc(p.soc) + '</b></div>' +
      '<div class="row"><span>Kernel</span><b>' + esc(p.kernel) + '</b></div>' +
      '<div class="row"><span>OS</span><b>' + esc(p.os) + '</b></div>';
    var rows = Object.keys(p.capabilities).map(function (k) {
      var c = p.capabilities[k] || {};
      return '<div class="row"><span>' + esc(k.replace(/_/g, ' ')) + '</span><span class="state-tag ' +
        cls(c.state || '') + '">' + esc(c.state || 'unknown') + '</span></div>' +
        '<p class="hint">' + esc(c.evidence || '') + (c.note ? ' — ' + esc(c.note) : '') + '</p>';
    }).join('');
    $('caps').innerHTML = '<h2>Capabilities</h2>' + rows;
  }
  fetch('profile.json', { cache: 'no-store' }).then(function (r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function (p) { render(validate(p)); $('report').textContent = 'Profile validated. Read-only; no hardware state was changed.'; })
    .catch(function (e) { $('report').textContent = 'Profile unavailable or invalid: ' + e.message; $('badge').textContent = 'profile: invalid'; });
  $('close').addEventListener('click', function () {
    try { if (window.parent && window.parent.NuxelLauncherClose) { window.parent.NuxelLauncherClose(); return; } } catch (e) {}
    if (window.frameElement && window.frameElement.parentNode) window.frameElement.parentNode.removeChild(window.frameElement);
  });
})();
