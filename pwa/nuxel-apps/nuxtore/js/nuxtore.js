// NuxTore — the Nuxel local app catalog (offline-first, no store submission).
//
// The page reads the catalog that ships inside the OS image, re-verifies every
// signature and every staged file digest in the page, and gates each install.
// There is no fetch to the internet, no upload path and no auto-install path.
(function () {
  'use strict';

  var Cat = window.NuxToreCatalog;
  var Crypt = window.NuxToreCrypto;

  // Repo root relative to this app dir (/pwa/nuxel-apps/nuxtore/).
  var ROOT = '../../../';

  var STATE_KEY = 'nuxtore-state-v1';
  var policyLocal = 'nuxtore-allow-unsigned';
  var state = Cat.emptyState();
  var report = null;
  var catalog = null;
  var publicKeys = {};
  var catBase = 'catalog/';

  var el = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s === undefined || s === null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function host() {
    if (window.NuxelHost && window.NuxelHost.available) return window.NuxelHost;
    try { if (window.parent && window.parent.NuxelHost) return window.parent.NuxelHost; } catch (e) {}
    return null;
  }

  // ---- persistence ---------------------------------------------------------
  function loadState() {
    try {
      var raw = localStorage.getItem(STATE_KEY);
      if (raw) state = JSON.parse(raw);
      if (!state.installed) state = Cat.emptyState();
    } catch (e) { state = Cat.emptyState(); }
    var h = host();
    if (h) h.configGet('nuxtore-state').then(function (res) {
      if (res && res.ok && res.text) {
        try {
          var remote = JSON.parse(res.text);
          if (remote && remote.installed) { state = remote; render(); }
        } catch (e) { /* keep local */ }
      }
    });
  }

  function saveState(line) {
    if (line) state.log = (state.log || []).concat([{ at: new Date().toISOString(), line: line }]).slice(-200);
    try { localStorage.setItem(STATE_KEY, JSON.stringify(state)); } catch (e) {}
    var h = host();
    if (h) h.configSet('nuxtore-state', JSON.stringify(state));
  }

  function allowUnsigned() {
    try { return localStorage.getItem(policyLocal) === '1'; } catch (e) { return false; }
  }

  // ---- data access ---------------------------------------------------------
  async function fetchJson(url) {
    var res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status + ' for ' + url);
    return res.json();
  }

  async function readBundle(rel) {
    try { return await fetchJson(catBase + rel); }
    catch (e) { return null; }
  }

  var MAX_HASH_BYTES = 4 * 1024 * 1024;
  async function readFile(path) {
    try {
      var res = await fetch(ROOT + path, { cache: 'no-store' });
      if (!res.ok) return null;
      var buf = await res.arrayBuffer();
      if (buf.byteLength > MAX_HASH_BYTES) return null;   // too large to hash in-page
      return new Uint8Array(buf);
    } catch (e) { return null; }
  }

  async function loadKey(keyId) {
    if (!keyId || publicKeys[keyId]) return publicKeys[keyId];
    try {
      var res = await fetch(catBase + 'keys/' + keyId + '.ed25519.pub', { cache: 'no-store' });
      if (!res.ok) return null;
      object_set(publicKeys, keyId, (await res.text()).trim());
      return publicKeys[keyId];
    } catch (e) { return null; }
  }
  function object_set(o, k, v) { o[k] = v; }

  // ---- verification --------------------------------------------------------
  async function verifyAll(deep) {
    el('seal').textContent = deep ? 'catalog: verifying every file…' : 'catalog: verifying…';
    el('seal').className = 'seal';
    try {
      catalog = await fetchJson(catBase + 'nuxtore-catalog.json');
    } catch (e) {
      el('seal').textContent = 'catalog: unreadable';
      el('seal').className = 'seal bad';
      el('sb-source').textContent = 'source: catalog/nuxtore-catalog.json not readable (' + e.message + ')';
      document.querySelectorAll('.panel').forEach(function (p) { if (p.id !== 'tab-about') p.innerHTML = ''; });
      el('tab-available').innerHTML = '<div class="empty">The local catalog could not be read. This is expected only when the' +
        ' page is opened outside the Nuxel PWA host (for example from a plain file:// path).</div>';
      return;
    }
    var pub = await loadKey(catalog.publisher && catalog.publisher.key_id);
    report = await Cat.verifyCatalog(catalog, {
      publicKeys: publicKeys,
      readBundle: readBundle,
      readFile: deep ? readFile : null,
      verifyFiles: !!deep
    });
    if (pub) el('sb-engine').textContent = 'signatures: ' + (await Crypt.ed25519Supported()
      ? 'Ed25519 available in this engine'
      : 'Ed25519 NOT implemented by this engine — offline verifier required');
    el('seal').textContent = report.ok
      ? ('catalog: ' + report.packages.length + ' packages, integrity OK' + (deep ? ' (deep)' : ''))
      : 'catalog: INTEGRITY FAILURE';
    el('seal').className = 'seal ' + (report.ok ? 'ok' : 'bad');
    el('sb-source').textContent = 'source: local catalog ' + (catalog.catalog_id || '') +
      ' · generated ' + (catalog.generated || '—') + (deep ? ' · files re-hashed' : ' · bundles verified');
    el('sb-policy').textContent = 'policy: signature ' +
      (catalog.policy.require_signature ? 'required' : 'optional') + ' · http ' +
      (catalog.policy.allow_http ? 'allowed' : 'refused') + ' · external publish ' +
      (catalog.policy.allow_external_publish ? 'ALLOWED (policy violation!)' : 'forbidden');
    el('keyid').textContent = (catalog.publisher && catalog.publisher.key_id) || '—';
    el('policy').textContent = JSON.stringify(catalog.policy, null, 2);
    el('notice').textContent = catalog.notice || '—';
    window.__nuxtoreReport = report;
    window.__nuxtoreCatalog = catalog;
    render();
  }

  // ---- rendering -----------------------------------------------------------
  function matches(pkg, q, cat) {
    if (cat && pkg.category !== cat) return false;
    if (!q) return true;
    var hay = [pkg.id, pkg.name, pkg.version, pkg.category, pkg.summary, pkg.description,
               (pkg.source || {}).provenance, (pkg.requires || []).join(' ')].join(' ').toLowerCase();
    return hay.indexOf(q.toLowerCase()) !== -1;
  }

  function badgeFor(p) {
    if (p.hardFail) return '<span class="badge bad">integrity failure</span>';
    if (p.verdict === Cat.VERDICT.SIGNED_VERIFIED) return '<span class="badge ok">signed · verified</span>';
    if (p.verdict === Cat.VERDICT.UNVERIFIED_ENGINE) return '<span class="badge warn">signature not checkable here</span>';
    return '<span class="badge warn">unsigned</span>';
  }

  function cardFor(p, ctx) {
    var s = state.installed[p.id];
    var canRemove = !!s && p.installer && p.installer.app_id === p.id;
    var decision = Cat.installDecision(p, { allowUnsigned: allowUnsigned(), confirmedId: null });
    var actions = [];
    if (s) {
      actions.push('<span class="badge ok">installed ' + esc(s.version) + '</span>');
      if (canRemove) actions.push('<button data-remove="' + esc(p.id) + '" class="danger">Remove</button>');
    } else {
      actions.push('<button data-install="' + esc(p.id) + '"' + (decision.allowed ? ' class="primary"' : '') +
                   '>' + (decision.allowed ? 'Install' : 'Install…') + '</button>');
    }
    actions.push('<button data-verify="' + esc(p.id) + '">Verify files</button>');
    return '<div class="card" data-pkg="' + esc(p.id) + '">' +
      '<h3>' + esc(p.name) + ' <span class="meta">' + esc(p.version) + '</span> ' + badgeFor(p) + '</h3>' +
      '<div class="sub">' + esc(p.summary) + '</div>' +
      '<div class="row">' + actions.join('') + '</div>' +
      '<p class="prov">provenance: ' + esc((p.source || {}).provenance || '—') + '</p>' +
      '<p class="meta">' + esc(p.category) + ' · ' + Cat.formatBytes(p.size_bytes) + ' · ' +
        p.file_count + ' files · ' + esc(p.license || '—') + '</p>' +
      '<p class="digest">sha256 ' + esc(p.sha256) + '</p>' +
      (p.problems.length ? '<p class="hint" style="color:#ef9a9a">' + p.problems.map(esc).join('<br>') + '</p>' : '') +
      (ctx.hint ? '<p class="hint">' + ctx.hint + '</p>' : '') +
      '</div>';
  }

  function render() {
    if (!report) return;
    var q = el('search').value.trim();
    var cat = el('category').value;
    var plan = Cat.plan(state, report);
    var pkgs = report.packages.filter(function (p) { return matches(p, q, cat); });
    var byId = {};
    plan.installed.forEach(function (e) { byId[e.pkg.id] = { installed: true, version: e.installedVersion }; });

    var inst = pkgs.filter(function (p) { return state.installed[p.id] && !p.hardFail; });
    var avail = pkgs.filter(function (p) { return !state.installed[p.id] && !p.hardFail; });
    var blocked = pkgs.filter(function (p) { return p.hardFail; });

    el('c-installed').textContent = plan.counts.installed;
    el('c-available').textContent = plan.counts.available;
    el('c-blocked').textContent = plan.counts.blocked;

    el('tab-installed').innerHTML = inst.length ? inst.map(function (p) { return cardFor(p, {}); }).join('')
      : '<div class="empty">No packages from this catalog are installed yet. Open <b>Available</b> to install one.</div>';
    el('tab-available').innerHTML = avail.length ? avail.map(function (p) { return cardFor(p, {}); }).join('')
      : '<div class="empty">Nothing matches this filter.</div>';
    el('tab-blocked').innerHTML = blocked.length ? blocked.map(function (p) {
        return cardFor(p, { hint: 'Refused by the install gate. Integrity failures are never installable, ' +
          'even with unsigned installs enabled.' });
      }).join('')
      : '<div class="empty">No package failed verification. ' +
        'The deliberately unsigned <code>org.example.UnsignedDemo</code> entry in this catalog is refused by the ' +
        'gate (it appears under Available as “unsigned”), which is the behaviour the offline test suite asserts.</div>';

    var log = (state.log || []).slice(-60).reverse().map(function (l) {
      return esc((l.at || '—')) + '  ' + esc(l.line);
    }).join('\n');
    el('activity').textContent = log || 'No local activity yet.';
    renderCategories();
  }

  function renderCategories() {
    var sel = el('category');
    if (sel.dataset.filled === '1') return;
    var cats = {};
    report.packages.forEach(function (p) { cats[p.category] = 1; });
    Object.keys(cats).sort().forEach(function (c) {
      var o = document.createElement('option'); o.value = c; o.textContent = c; sel.appendChild(o);
    });
    sel.dataset.filled = '1';
  }

  // ---- install / remove ----------------------------------------------------
  function findPkg(id) {
    if (!report) return null;
    var hit = null;
    report.packages.forEach(function (p) { if (p.id === id) hit = p; });
    return hit;
  }

  function openSheet(p) {
    var d = Cat.installDecision(p, { allowUnsigned: allowUnsigned(), confirmedId: null });
    var sigLine = p.signatureState === 'valid' ? 'signature verified (' + (p.notes.filter(function (n) {
      return n.indexOf('signed by') === 0; })[0] || '') + ')'
      : p.signatureState === 'engine-unsupported' ? 'signature present but this engine cannot check Ed25519'
      : 'NO SIGNATURE — unsigned package';
    var gate = '';
    if (!d.allowed) {
      gate = '<div class="gate"><label style="display:block"><b>Install blocked</b><br>' + esc(d.reason) + '</label>' +
        (p.verdict === Cat.VERDICT.UNSIGNED_REFUSED || p.verdict === Cat.VERDICT.UNVERIFIED_ENGINE
          ? '<label><input type="checkbox" id="gate-allow"> Enable unsigned installs (policy allows it: ' +
            (catalog.policy.allow_unsigned_with_confirmation ? 'yes' : 'no') + ')</label>' +
            '<input type="text" id="gate-confirm" placeholder="type ' + esc(p.id) + ' to confirm">'
          : '') + '</div>';
    } else if (p.hardFail) {
      gate = '<div class="gate"><label><b>Integrity failure.</b> This package contradicts its own digest or ' +
        'signature and can never be installed from NuxTore.</label></div>';
    }
    el('sheet').innerHTML =
      '<h2>' + esc(p.name) + ' <span class="meta">' + esc(p.version) + '</span></h2>' +
      '<div class="sub">' + esc(p.summary) + '</div>' +
      '<p class="hint">' + esc(p.description) + '</p>' +
      '<p class="metap"><b>Package id</b><br><span class="digest">' + esc(p.id) + '</span></p>' +
      '<p><b>Bundle digest</b><br><span class="digest">' + esc(p.sha256) + '</span></p>' +
      '<p><b>Signatures</b><br>' + esc(sigLine) + '</p>' +
      '<p><b>Provenance</b><br>' + esc((p.source || {}).provenance || '—') + '</p>' +
      '<p><b>License</b><br>' + esc(p.license || '—') + '</p>' +
      '<p><b>Size</b> ' + Cat.formatBytes(p.size_bytes) + ' · <b>Files</b> ' + p.file_count + '</p>' +
      (p.requires.length ? '<p><b>Requires</b></p><ul class="reqs">' + p.requires.map(function (r) {
        return '<li>' + esc(r) + '</li>'; }).join('') + '</ul>' : '') +
      (p.capabilities.length ? '<p><b>Capabilities</b></p><ul class="reqs">' + p.capabilities.map(function (r) {
        return '<li>' + esc(r) + '</li>'; }).join('') + '</ul>' : '') +
      gate +
      '<div class="row"><button class="primary" id="do-install"' + (d.allowed ? '' : ' disabled') + '>Install</button>' +
      '<button id="do-cancel" class="ghost">Cancel</button></div>' +
      '<p class="hint">Install registers the staged package in the local Nuxel app registry. No file is downloaded ' +
      'and no network request is made.</p>';
    el('drawer').classList.add('open');
    var allowBox = el('gate-allow');
    var confirmBox = el('gate-confirm');
    function refresh() {
      var unsigned = allowUnsigned();
      if (allowBox) { try { localStorage.setItem(policyLocal, allowBox.checked ? '1' : '0'); } catch (e) {} }
      var dd = Cat.installDecision(p, { allowUnsigned: allowUnsigned(), confirmedId: confirmBox ? confirmBox.value.trim() : null });
      el('do-install').disabled = !dd.allowed;
      var w = document.getElementById('gate-warn');
      if (dd.warning && !w) {
        var n = document.createElement('p');
        n.id = 'gate-warn'; n.className = 'hint'; n.style.color = '#ffcc80'; n.textContent = dd.warning;
        el('sheet').insertBefore(n, el('sheet').querySelector('.row'));
      }
    }
    if (allowBox) allowBox.addEventListener('change', refresh);
    if (confirmBox) confirmBox.addEventListener('input', refresh);
    el('do-cancel').addEventListener('click', closeSheet);
    el('do-install').addEventListener('click', function () { doInstall(p); });
  }

  function closeSheet() { el('drawer').classList.remove('open'); }

  async function doInstall(p) {
    var decision = Cat.installDecision(p, { allowUnsigned: allowUnsigned(),
      confirmedId: (el('gate-confirm') && el('gate-confirm').value.trim()) || null });
    if (!decision.allowed) {
      saveState('REFUSED install ' + p.id + ' — ' + decision.reason);
      render();
      return;
    }
    // Best-effort registry hint: the authoritative registry is the launcher's.
    var b = window.NuxelBridge;
    var regNote = 'registry: recorded locally';
    if (b && typeof b.call === 'function') {
      try {
        var res = await b.call('apps', 'register', {
          app_id: p.installer.app_id, name: p.name, start_url: p.installer.start_url,
          version: p.version, sha256: p.sha256 });
        regNote = 'registry: ' + (res && res.mock ? 'local-only (bridge offline)' : 'registered with the bridge');
      } catch (e) { regNote = 'registry: local-only (' + (e && e.message) + ')'; }
    }
    state = Cat.applyInstall(state, p, new Date().toISOString());
    saveState('install ' + p.id + ' ' + p.version + ' — ' + decision.reason + ' — ' + regNote);
    closeSheet();
    render();
  }

  function doRemove(p) {
    state = Cat.applyRemove(state, p.id, new Date().toISOString());
    saveState('remove ' + p.id + ' — staged files kept on disk (no destructive uninstall)');
    render();
  }

  async function verifyOne(id) {
    var p = findPkg(id);
    if (!p) return;
    var raw = null;
    report.packages.forEach(function (x) { if (x.id === id) raw = x; });
    if (!raw) return;
    var pkg = (catalog.packages || []).filter(function (x) { return x.id === id; })[0];
    var res = await Cat.verifyPackage(pkg, { policy: catalog.policy, publicKeys: publicKeys,
                                             readBundle: readBundle, readFile: readFile, verifyFiles: true });
    var idx = report.packages.indexOf(raw);
    if (idx >= 0) report.packages[idx] = res;
    saveState('verify ' + id + ' → ' + res.verdict + (res.problems.length ? ' (' + res.problems.join('; ') + ')' : ''));
    el('seal').textContent = report.ok ? 'catalog: integrity OK (one package re-hashed)'
                                       : 'catalog: INTEGRITY FAILURE';
    el('seal').className = 'seal ' + (report.ok ? 'ok' : 'bad');
    render();
  }

  // ---- wiring --------------------------------------------------------------
  document.querySelectorAll('.tab').forEach(function (t) {
    t.addEventListener('click', function () {
      document.querySelectorAll('.tab').forEach(function (x) { x.classList.remove('active'); });
      document.querySelectorAll('.panel').forEach(function (x) { x.classList.remove('active'); });
      t.classList.add('active');
      el('tab-' + t.dataset.tab).classList.add('active');
    });
  });
  el('search').addEventListener('input', render);
  el('category').addEventListener('change', render);
  el('sortmode').addEventListener('change', render);
  el('reverify').addEventListener('click', function () { verifyAll(true); });
  el('drawer').addEventListener('click', function (ev) { if (ev.target === el('drawer')) closeSheet(); });
  el('close').addEventListener('click', function () {
    var f = window.frameElement;
    if (f && window.parent !== window && window.parent.NuxelLauncherClose) window.parent.NuxelLauncherClose();
    else if (f && f.parentNode) f.parentNode.removeChild(f);
  });
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.dataset) return;
    if (t.dataset.install) {
      var p = findPkg(t.dataset.install);
      if (p) openSheet(p);
    } else if (t.dataset.remove) {
      var r = findPkg(t.dataset.remove);
      if (r) doRemove(r);
    } else if (t.dataset.verify) {
      verifyOne(t.dataset.verify);
    }
  });

  loadState();
  verifyAll(false);
})();
