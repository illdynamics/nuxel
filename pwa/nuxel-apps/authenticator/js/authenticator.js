// Nuxel Authenticator — UI over the encrypted vault.  No network code exists in
// this app: the only storage is the AES-GCM envelope in localStorage, and the
// only crypto is WebCrypto.
(function () {
  'use strict';
  var V = window.AuthVault, T = window.NuxelTotp;
  var KEY = 'nuxel-authenticator-envelope-v1';
  var el = function (id) { return document.getElementById(id); };
  var state = { env: null, key: null, accounts: [], filter: '', tick: null, codes: {} };

  function toast(m) {
    var t = el('toast'); t.textContent = m; t.classList.add('show');
    clearTimeout(toast._t); toast._t = setTimeout(function () { t.classList.remove('show'); }, 2800);
  }
  function esc(s) { return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function loadEnv() { try { var raw = localStorage.getItem(KEY); return raw ? JSON.parse(raw) : null; } catch (e) { return null; } }
  function storeEnv(env) { try { localStorage.setItem(KEY, JSON.stringify(env)); } catch (e) { toast('could not save the vault: ' + e.message); } }

  /* ---------------- lock screen ---------------- */

  function renderLock() {
    var exists = !!state.env;
    el('lock-title').textContent = exists ? 'Unlock vault' : 'Create vault';
    el('lock-hint').textContent = exists
      ? 'Enter the passphrase. It is never stored anywhere — losing it means the secrets are unrecoverable, by design.'
      : 'Choose a passphrase for this device. There is no recovery, no reset e-mail and no cloud copy.';
    el('confirm-row').style.display = exists ? 'none' : 'flex';
    el('lock-go').textContent = exists ? 'Unlock' : 'Create vault';
    el('lock-error').textContent = '';
    el('pass').value = ''; el('pass2').value = '';
    el('screen-lock').style.display = 'block';
    el('screen-main').style.display = 'none';
    el('header-state').textContent = exists ? 'locked' : 'no vault';
    el('header-state').className = 'badge ' + (exists ? 'warn' : 'bad');
  }

  function showMain() {
    el('screen-lock').style.display = 'none';
    el('screen-main').style.display = 'block';
    el('header-state').textContent = 'unlocked';
    el('header-state').className = 'badge ok';
    renderAccounts();
    startTicker();
    el('vault-kdf').textContent = state.env.kdf.name + '-' + state.env.kdf.hash + ' · ' + state.env.kdf.iterations + ' iterations';
    el('vault-count').textContent = state.accounts.length + ' account(s)';
  }

  async function lockAction() {
    var pass = el('pass').value, pass2 = el('pass2').value;
    el('lock-error').textContent = '';
    try {
      if (!state.env) {
        if (pass !== pass2) throw new Error('the two passphrases do not match');
        var v = await V.create(pass);
        state.env = v.envelope; state.key = v.key; state.accounts = [];
        storeEnv(state.env); showMain(); toast('Vault created');
        return;
      }
      var un = await V.unlock(state.env, pass);
      state.key = un.key; state.accounts = un.accounts;
      showMain(); toast('Unlocked');
    } catch (e) {
      el('lock-error').textContent = e.message;
    }
  }

  /* ---------------- codes ---------------- */

  function visible() {
    var q = state.filter.toLowerCase();
    return state.accounts.filter(function (a) {
      return !q || (a.issuer + ' ' + a.account).toLowerCase().indexOf(q) !== -1;
    });
  }

  function group(code) {
    // 6 digits -> 3+3, 8 digits -> 4+4; anything else is left untouched.
    if (/^\d{6}$/.test(code)) return code.slice(0, 3) + ' ' + code.slice(3);
    if (/^\d{8}$/.test(code)) return code.slice(0, 4) + ' ' + code.slice(4);
    return code;
  }

  async function renderCodes() {
    var now = Math.floor(Date.now() / 1000);
    var host = el('codes');
    var list = visible();
    if (!list.length) {
      host.innerHTML = '<p class="hint">' + (state.accounts.length ? 'No account matches that filter.' :
        'The vault is empty. Add an account with “Add account”, or paste an otpauth:// URI.') + '</p>';
      return;
    }
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      var counter = Math.floor(now / a.period);
      // The code only changes when the counter changes, so the HMAC is computed
      // once per period per account (the ticker runs 2x/s for the countdown).
      var cacheKey = a.id + ':' + counter;
      var code = state.codes[cacheKey];
      if (!code) {
        try {
          code = await T.totp(T.base32Decode(a.secret), now, { algorithm: a.algorithm, digits: a.digits, period: a.period });
        } catch (e) { code = 'ERROR'; }
        state.codes = {};                 // drop the previous counter: bounded memory
        state.codes[cacheKey] = code;
      }
      var left = T.secondsRemaining(now, a.period);
      var pct = Math.round(T.progress(now, a.period) * 100);
      var node = document.getElementById('otp-' + a.id);
      if (!node) {
        node = document.createElement('div');
        node.className = 'otp'; node.id = 'otp-' + a.id;
        node.innerHTML =
          '<div class="top"><span class="iss">' + esc(a.issuer || 'Unnamed issuer') + '</span>' +
          '<span class="acc">' + esc(a.account) + '</span></div>' +
          '<div class="code"><span class="grp"></span></div>' +
          '<div class="bar"><i></i></div>' +
          '<div class="meta"><span class="alg"></span><span class="left"></span><span class="sec"></span></div>' +
          '<div class="row" style="margin-top:8px"><button class="copy">Copy</button><button class="del danger ghost">Delete</button></div>';
        node.querySelector('.copy').addEventListener('click', function () { copyCode(a.id); });
        node.querySelector('.del').addEventListener('click', function () { del(a.id); });
        host.appendChild(node);
      }
      node.querySelector('.grp').textContent = group(code);
      node.querySelector('.code').className = 'code' + (left <= 5 ? ' expiring' : '');
      node.querySelector('.bar > i').style.width = pct + '%';
      node.querySelector('.alg').textContent = a.algorithm + ' · ' + a.digits + ' digits · ' + a.period + 's';
      node.querySelector('.left').textContent = left + 's left';
      node.querySelector('.sec').textContent = (a.notes || '');
    }
    // Remove rows for accounts that no longer exist / are filtered out.
    Array.prototype.forEach.call(host.querySelectorAll('.otp'), function (n) {
      var id = n.id.replace('otp-', '');
      if (!list.filter(function (a) { return a.id === id; }).length) n.remove();
    });
    el('header-code-count').textContent = list.length + ' code(s)';
  }

  function startTicker() {
    if (state.tick) clearInterval(state.tick);
    state.tick = setInterval(function () { renderCodes(); }, 500);
    renderCodes();
  }

  function copyCode(id) {
    var node = document.getElementById('otp-' + id);
    if (!node) return;
    var text = node.querySelector('.grp').textContent.replace(/\s+/g, '');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { toast('Code copied'); },
        function () { toast('Clipboard refused — the code is ' + text); });
    } else {
      toast('Clipboard unavailable — the code is ' + text);
    }
  }

  function del(id) {
    var a = state.accounts.filter(function (x) { return x.id === id; })[0];
    if (!a) return;
    if (!window.confirm('Delete “' + (a.issuer || a.account) + '”? This removes the secret from the vault. There is no undo and no cloud copy.')) return;
    state.accounts = V.removeAccount(state.accounts, id);
    state.codes = {};
    save(); renderAccounts(); toast('Account deleted');
  }

  async function save() {
    if (!state.key) return;
    state.env = await V.save(state.env, state.accounts, state.key);
    storeEnv(state.env);
    el('vault-count').textContent = state.accounts.length + ' account(s)';
  }

  /* ---------------- add account ---------------- */

  function addFromForm() {
    var raw = {
      issuer: el('add-issuer').value, account: el('add-account').value, secret: el('add-secret').value,
      algorithm: el('add-alg').value, digits: Number(el('add-digits').value), period: Number(el('add-period').value)
    };
    var res = V.addAccount(state.accounts, raw);
    if (!res.ok) { el('add-error').textContent = 'Refused: ' + res.problems.join('; '); return; }
    state.accounts = res.accounts;
    el('add-error').textContent = '';
    ['add-issuer', 'add-account', 'add-secret'].forEach(function (i) { el(i).value = ''; });
    save().then(function () { renderAccounts(); toast('Account added'); });
  }

  function addFromUri() {
    try {
      var p = T.parseOtpauth(el('add-uri').value);
      var res = V.addAccount(state.accounts, p);
      if (!res.ok) { el('uri-error').textContent = 'Refused: ' + res.problems.join('; '); return; }
      state.accounts = res.accounts;
      el('uri-error').textContent = ''; el('add-uri').value = '';
      save().then(function () { renderAccounts(); toast('Imported ' + p.account); });
    } catch (e) {
      el('uri-error').textContent = 'Refused: ' + e.message;
    }
  }

  function renderAccounts() {
    el('vault-count').textContent = state.accounts.length + ' account(s)';
    renderCodes();
  }

  /* ---------------- import / export / maintenance ---------------- */

  function exportVault() {
    if (!state.env) return;
    var text = V.exportEnvelope(state.env);
    var blob = new Blob([text], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'nuxel-authenticator-vault.json';
    document.body.appendChild(a); a.click(); a.remove();
    el('io-note').textContent = 'Exported the ENCRYPTED envelope (' + text.length + ' bytes). It is useless without the passphrase.';
  }

  function importVault() {
    var f = el('import-file').files[0];
    if (!f) { el('io-note').textContent = 'Choose a vault file first.'; return; }
    var fr = new FileReader();
    fr.onload = function () {
      try {
        var env = V.importEnvelope(String(fr.result));
        el('io-note').textContent = 'Envelope accepted (' + env.kdf.iterations + ' iterations). Enter its passphrase to unlock it.';
        state.env = env; state.key = null; state.accounts = [];
        storeEnv(env); renderLock();
        toast('Vault imported — unlock it with its passphrase');
      } catch (e) {
        el('io-note').textContent = e.message;
      }
    };
    fr.readAsText(f);
  }

  async function rekey() {
    var current = el('rk-current').value, next = el('rk-new').value, again = el('rk-new2').value;
    try {
      if (!state.key) throw new Error('unlock the vault first');
      var un = await V.unlock(state.env, current);
      if (next !== again) throw new Error('the new passphrases do not match');
      var policy = V.checkPassphrase(next);
      if (!policy.ok) throw new Error('new passphrase refused: ' + policy.problems.join(', '));
      // A new passphrase gets a FRESH salt and key: the envelope must carry the
      // matching KDF parameters or the vault would be unopenable afterwards.
      var created = await V.create(next);
      state.env = Object.assign({}, state.env, { kdf: created.envelope.kdf });
      state.key = created.key;
      state.accounts = un.accounts;
      await save();
      el('rk-note').textContent = 'Re-keyed with a fresh salt and key. The old passphrase no longer opens this vault.';
      ['rk-current', 'rk-new', 'rk-new2'].forEach(function (i) { el(i).value = ''; });
      toast('Vault re-keyed');
    } catch (e) { el('rk-note').textContent = e.message; }
  }

  function wipe() {
    if (el('wipe-confirm').value.trim() !== 'DELETE VAULT') {
      el('wipe-note').textContent = 'Type DELETE VAULT exactly to confirm.';
      return;
    }
    try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
    state = { env: null, key: null, accounts: [], filter: '', tick: null, codes: {} };
    if (state.tick) clearInterval(state.tick);
    el('codes').innerHTML = '';
    el('wipe-note').textContent = 'Vault deleted from this device. There is no cloud copy to restore from.';
    renderLock(); toast('Vault deleted');
  }

  async function runSelfTest() {
    el('selftest-run').disabled = true;
    el('selftest-summary').textContent = 'running the RFC 6238 vectors…';
    el('selftest-summary').className = 'pill warn';
    var r = await V.selfTest();
    var rows = r.results.map(function (x) {
      return '<tr><td>' + esc(x.vector) + '</td><td>' + esc(x.expected) + '</td><td>' + esc(x.got) +
        '</td><td>' + (x.ok ? 'PASS' : 'FAIL') + '</td></tr>';
    }).join('');
    el('selftest-body').innerHTML = rows;
    el('selftest-summary').textContent = r.ok
      ? 'All ' + r.results.length + ' RFC 6238 vectors PASS — codes are computed by the same code path the list above uses.'
      : 'VECTOR FAILURE — do not trust codes from this build.';
    el('selftest-summary').className = 'pill ' + (r.ok ? 'ok' : 'bad');
    el('selftest-run').disabled = false;
  }

  /* ---------------- wiring ---------------- */

  // The sub-tabs only ever swap the four panels INSIDE #screen-main.  #screen-lock
  // and #screen-main are themselves .panel elements, so a global query here would
  // hide the whole app - hence the scoped selector.
  function tabs() {
    var root = el('screen-main');
    Array.prototype.forEach.call(root.querySelectorAll('.tab'), function (b) {
      b.addEventListener('click', function () {
        Array.prototype.forEach.call(root.querySelectorAll('.tab'), function (x) { x.classList.remove('active'); });
        Array.prototype.forEach.call(root.querySelectorAll('.panel'), function (x) { x.classList.remove('active'); });
        b.classList.add('active'); el('tab-' + b.dataset.tab).classList.add('active');
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    tabs();
    el('lock-go').addEventListener('click', lockAction);
    el('pass').addEventListener('keydown', function (e) { if (e.key === 'Enter') lockAction(); });
    el('pass2').addEventListener('keydown', function (e) { if (e.key === 'Enter') lockAction(); });
    el('lock-now').addEventListener('click', renderLock);
    el('search').addEventListener('input', function () { state.filter = el('search').value; renderCodes(); });
    el('add-form-go').addEventListener('click', addFromForm);
    el('add-uri-go').addEventListener('click', addFromUri);
    el('export-go').addEventListener('click', exportVault);
    el('import-go').addEventListener('click', importVault);
    el('rekey-go').addEventListener('click', rekey);
    el('wipe-go').addEventListener('click', wipe);
    el('selftest-run').addEventListener('click', runSelfTest);
    el('close').addEventListener('click', function () { try { window.close(); } catch (e) {} });
    el('selftest-summary').textContent = 'not run in this session';

    state.env = loadEnv();
    renderLock();
  });
}());
