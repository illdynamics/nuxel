// Nuxel Vault — UI client for the scoped Nuxel Bridge keyring API.
//
// This file never writes a secret to browser persistent storage, a URL, a log
// or a toast.  Decrypted items live in `state.items` only while the keyring is
// unlocked, and are dropped on lock/background/timeout.
import { NuxelBridge } from '../../../nuxel-common/bridge.js';

const Archive = window.NuxelVaultArchive;
const Pwgen = window.NuxelPwgen;
const AUTO_LOCK_KEY = 'nuxel-vault-autolock';
const LOCK_ON_HIDE_KEY = 'nuxel-vault-lock-on-hide';

const el = (id) => document.getElementById(id);
const state = {
  unlocked: false,
  keyringState: 'boot',
  items: [],
  detailItem: null,
  filterLogin: '',
  filterNote: '',
  autoLock: Number(localStorage.getItem(AUTO_LOCK_KEY) || 120),
  lockOnHide: localStorage.getItem(LOCK_ON_HIDE_KEY) !== '0',
  idleTimer: null,
  pollTimer: null,
  clipboardTimer: null,
  clipboard: null,
  busy: false,
};

function toast(message) {
  const t = el('toast');
  if (!t) return;
  t.textContent = String(message || '');
  t.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => t.classList.remove('show'), 2600);
}

function setBadge(text, cls) {
  const b = el('keyring-badge');
  b.textContent = text;
  b.className = 'badge ' + (cls || '');
}

function showScreen(name) {
  ['screen-boot', 'screen-unlock', 'screen-main'].forEach((id) => {
    el(id).classList.toggle('active', id === name);
  });
}

function showUnlockLayout(which) {
  showScreen('screen-unlock');
  el('unlock-welcome').hidden = which !== 'welcome';
  el('unlock-existing').hidden = which !== 'existing';
  el('provider-error').hidden = which !== 'provider';
}

function showProviderError(result, diagnostics) {
  showUnlockLayout('provider');
  const text = el('provider-error-text');
  text.textContent = (result && (result.detail || result.error)) ||
    'The system Secret Service provider is not reachable.';
  const diag = el('provider-diagnostics');
  if (diagnostics) {
    diag.hidden = false;
    diag.textContent = diagnostics;
  } else {
    diag.hidden = true;
    diag.textContent = '';
  }
  setBadge('unavailable', 'bad');
  state.keyringState = 'unavailable';
}

async function bridge(verb, params) {
  if (!NuxelBridge || typeof NuxelBridge.keyring !== 'function') {
    return { success: false, state: 'unavailable', offline: true,
      error: 'bridge_unreachable', detail: 'Nuxel Bridge client is unavailable' };
  }
  return NuxelBridge.keyring(verb, params || {});
}

function mapError(result) {
  const code = result && result.error;
  if (code === 'invalid_credentials') return 'The master password did not unlock the keyring.';
  if (code === 'rate_limited') return 'Too many failed attempts. Wait a moment before trying again.';
  if (code === 'provider_unavailable') return 'The system keyring provider is unavailable. Nothing was saved.';
  if (code === 'collection_locked') return 'The keyring is locked.';
  if (code === 'user_cancelled') return 'The keyring prompt was cancelled. The keyring remains locked.';
  if (code === 'permission_denied') return 'This app is not authorized for that keyring operation.';
  if (code === 'timeout') return 'The keyring provider did not answer in time.';
  if (code === 'item_not_found') return 'That item no longer exists.';
  if (code === 'bridge_unreachable') return result.detail || 'Nuxel Bridge is unreachable. Nothing was saved or loaded.';
  return (result && (result.detail || result.error)) || 'The keyring operation failed.';
}

/* ------------------------------------------------------------------ boot */

async function boot() {
  setBadge('checking', '');
  showScreen('screen-boot');
  const st = await bridge('status');
  if (!st.success) {
    showProviderError(st);
    return;
  }
  state.keyringState = st.state || (st.locked ? 'collection_locked' : 'unlocked');
  if (st.state === 'not_initialized') {
    showUnlockLayout('welcome');
    setBadge('not initialized', 'warn');
    return;
  }
  if (st.locked || st.state === 'collection_locked') {
    showUnlockLayout('existing');
    setBadge('locked', 'bad');
    return;
  }
  if (st.state === 'unlocked') {
    await enterMain();
    return;
  }
  showUnlockLayout('existing');
  setBadge('locked', 'bad');
}

async function enterMain() {
  state.unlocked = true;
  state.keyringState = 'unlocked';
  showScreen('screen-main');
  setBadge('unlocked', 'good');
  el('lock-now').hidden = false;
  await refreshItems();
  await refreshAuthStatus();
  await refreshBackupStatus();
  resetIdle();
  startPoll();
}

/* ---------------------------------------------------------------- items */

async function refreshItems() {
  const res = await bridge('list-items');
  if (!res.success) {
    if (res.state === 'collection_locked') {
      await lockUI('keyring locked', false);
    } else {
      toast(mapError(res));
    }
    return;
  }
  state.items = Array.isArray(res.items) ? res.items : [];
  renderAll();
}

function itemSubtitle(item) {
  if (item.type === 'note') return 'Secure note';
  return item.username || item.url || 'Login';
}

function itemIcon(item) {
  if (item.type === 'note') return 'N';
  return (item.title || 'L').trim().charAt(0).toUpperCase() || 'L';
}

function makeItemNode(item) {
  const node = document.createElement('div');
  node.className = 'item';
  node.setAttribute('role', 'button');
  node.tabIndex = 0;
  const icon = document.createElement('div');
  icon.className = 'icon';
  icon.textContent = itemIcon(item);
  const body = document.createElement('div');
  body.className = 'body';
  const title = document.createElement('div');
  title.className = 'title';
  title.textContent = item.title || 'Untitled';
  const sub = document.createElement('div');
  sub.className = 'sub';
  sub.textContent = itemSubtitle(item);
  body.appendChild(title);
  body.appendChild(sub);
  node.appendChild(icon);
  node.appendChild(body);
  if (item.favorite) {
    const star = document.createElement('div');
    star.className = 'star';
    star.textContent = '★';
    node.appendChild(star);
  }
  node.addEventListener('click', () => openDetail(item.id));
  node.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') openDetail(item.id); });
  return node;
}

function renderList(hostId, items, emptyText) {
  const host = el(hostId);
  host.textContent = '';
  if (!items.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = emptyText;
    host.appendChild(empty);
    return;
  }
  items.forEach((item) => host.appendChild(makeItemNode(item)));
}

function matches(item, query) {
  if (!query) return true;
  const q = query.toLowerCase();
  return [item.title, item.username, item.url, (item.tags || []).join(' ')]
    .some((v) => String(v || '').toLowerCase().indexOf(q) !== -1);
}

function renderAll() {
  const logins = state.items.filter((i) => i.type === 'login');
  const notes = state.items.filter((i) => i.type === 'note');
  el('stat-total').textContent = String(state.items.length);
  el('stat-logins').textContent = String(logins.length);
  el('stat-notes').textContent = String(notes.length);
  el('stat-fav').textContent = String(state.items.filter((i) => i.favorite).length);
  el('overview-state').textContent = 'unlocked';
  renderList('recent-list', state.items.slice(0, 6), 'No items yet. Add a login or a secure note.');
  renderList('login-list', logins.filter((i) => matches(i, state.filterLogin)),
    state.filterLogin ? 'No login matches that search.' : 'No logins saved yet.');
  renderList('note-list', notes.filter((i) => matches(i, state.filterNote)),
    state.filterNote ? 'No secure note matches that search.' : 'No secure notes saved yet.');
}

/* --------------------------------------------------------------- editor */

function clearEditor() {
  ['edit-id', 'edit-type', 'edit-title', 'edit-url', 'edit-username', 'edit-password',
    'edit-notes', 'edit-tags'].forEach((id) => { el(id).value = ''; });
  el('edit-favorite').checked = false;
  el('edit-password').type = 'password';
  el('edit-password-toggle').textContent = 'Show password';
  el('editor-error').textContent = '';
  el('login-fields').hidden = false;
}

function openEditor(type, item) {
  clearEditor();
  el('editor').hidden = false;
  el('edit-type').value = type;
  el('editor-title').textContent = item ? 'Edit item' : (type === 'note' ? 'New secure note' : 'New login');
  el('login-fields').hidden = type === 'note';
  if (item) {
    el('edit-id').value = item.id;
    el('edit-title').value = item.title || '';
    el('edit-url').value = item.url || '';
    el('edit-username').value = item.username || '';
    el('edit-password').value = item.password || '';
    el('edit-notes').value = item.notes || '';
    el('edit-tags').value = (item.tags || []).join(', ');
    el('edit-favorite').checked = !!item.favorite;
  }
  el('edit-title').focus();
}

function parseTags(text) {
  const seen = [];
  String(text || '').split(',').forEach((raw) => {
    const t = raw.trim();
    if (t && t.length <= 48 && seen.indexOf(t) === -1 && seen.length < 24) seen.push(t);
  });
  return seen;
}

async function saveEditor() {
  if (state.busy) return;
  const type = el('edit-type').value;
  const title = el('edit-title').value.trim();
  if (!title) { el('editor-error').textContent = 'A title is required.'; return; }
  if (title.length > 200) { el('editor-error').textContent = 'Title is too long.'; return; }
  const item = {
    schema: 'nuxel-vault-item-v1',
    type: type,
    title: title,
    url: type === 'login' ? el('edit-url').value.trim() : '',
    username: type === 'login' ? el('edit-username').value : '',
    password: type === 'login' ? el('edit-password').value : '',
    notes: el('edit-notes').value,
    tags: parseTags(el('edit-tags').value),
    favorite: el('edit-favorite').checked,
  };
  el('editor-error').textContent = '';
  state.busy = true;
  try {
    const id = el('edit-id').value;
    const res = id
      ? await bridge('update-item', { item_id: id, item: item })
      : await bridge('create-item', { item: item });
    if (!res.success) {
      if (res.state === 'collection_locked') { await lockUI('keyring locked', false); return; }
      el('editor-error').textContent = mapError(res);
      return;
    }
    el('editor').hidden = true;
    clearEditor();
    await refreshItems();
    toast(id ? 'Item updated' : 'Item saved to the keyring');
  } finally {
    state.busy = false;
  }
}

/* --------------------------------------------------------------- detail */

function addDetailRow(label, value, options) {
  const opts = options || {};
  const wrap = document.createElement('label');
  wrap.className = 'field';
  const span = document.createElement('span');
  span.textContent = label;
  wrap.appendChild(span);
  if (opts.hidden && opts.hiddenValue) {
    const button = document.createElement('button');
    button.className = 'ghost small';
    button.textContent = 'Show ' + (opts.what || 'value');
    const box = document.createElement('div');
    box.className = 'diag';
    box.style.display = 'none';
    box.textContent = opts.hiddenValue;
    button.addEventListener('click', () => {
      const showing = box.style.display !== 'none';
      box.style.display = showing ? 'none' : 'block';
      button.textContent = (showing ? 'Show ' : 'Hide ') + (opts.what || 'value');
    });
    wrap.appendChild(button);
    wrap.appendChild(box);
    return wrap;
  }
  const input = document.createElement('input');
  input.type = opts.password ? 'password' : 'text';
  input.readOnly = true;
  input.value = value == null ? '' : String(value);
  wrap.appendChild(input);
  return wrap;
}

async function openDetail(id) {
  const res = await bridge('get-item', { item_id: id });
  if (!res.success) {
    if (res.state === 'collection_locked') { await lockUI('keyring locked', false); return; }
    toast(mapError(res));
    return;
  }
  state.detailItem = res.item;
  el('detail').hidden = false;
  el('detail-title').textContent = res.item.title || 'Item';
  el('detail-meta').textContent = (res.item.type === 'note' ? 'Secure note' : 'Login') +
    (res.item.updated_at ? ' · updated ' + res.item.updated_at : '');
  const host = el('detail-fields');
  host.textContent = '';
  if (res.item.type === 'login') {
    host.appendChild(addDetailRow('Username', res.item.username));
    host.appendChild(addDetailRow('URL / origin', res.item.url));
    host.appendChild(addDetailRow('Password', res.item.password, { password: true }));
  }
  if (res.item.tags && res.item.tags.length) {
    host.appendChild(addDetailRow('Tags', res.item.tags.join(', ')));
  }
  if (res.item.notes) {
    host.appendChild(addDetailRow('Notes', '', { hidden: true, hiddenValue: res.item.notes, what: 'notes' }));
  }
  el('detail-note').textContent = res.item.favorite ? 'Favorite' : '';
  el('detail-copy-user').hidden = res.item.type !== 'login';
  el('detail-copy-pass').hidden = res.item.type !== 'login';
}

function closeDetail() {
  el('detail').hidden = true;
  el('detail-fields').textContent = '';
  el('detail-note').textContent = '';
  state.detailItem = null;
}

/* ------------------------------------------------------------- clipboard */

function clearClipboardTimer() {
  if (state.clipboardTimer) {
    clearTimeout(state.clipboardTimer);
    state.clipboardTimer = null;
  }
}

async function clearClipboardIfSame() {
  const tracked = state.clipboard;
  state.clipboard = null;
  clearClipboardTimer();
  if (!tracked) return;
  try {
    const now = await navigator.clipboard.readText();
    if (now === tracked.value) await navigator.clipboard.writeText('');
  } catch (e) { /* clipboard read unavailable: never erase a value we cannot verify */ }
}

async function copySecret(value, label) {
  if (!value) { toast('No ' + label + ' stored'); return; }
  try {
    await navigator.clipboard.writeText(String(value));
    state.clipboard = { value: String(value), at: Date.now() };
    clearClipboardTimer();
    state.clipboardTimer = setTimeout(clearClipboardIfSame, 30000);
    toast(label.charAt(0).toUpperCase() + label.slice(1) + ' copied');
  } catch (e) {
    toast('Clipboard refused; nothing was copied');
  }
}

/* ------------------------------------------------------------------ lock */

function clearSecretDom() {
  state.items = [];
  state.detailItem = null;
  state.filterLogin = '';
  state.filterNote = '';
  el('login-search').value = '';
  el('note-search').value = '';
  ['recent-list', 'login-list', 'note-list', 'detail-fields'].forEach((id) => {
    if (el(id)) el(id).textContent = '';
  });
  el('detail').hidden = true;
  el('editor').hidden = true;
  clearEditor();
  el('gen-output').textContent = '—';
  el('gen-strength').textContent = '';
  ['unlock-pass', 'create-pass', 'create-pass2', 'export-pass', 'export-pass2',
    'import-pass', 'reset-confirm'].forEach((id) => { if (el(id)) el(id).value = ''; });
  el('import-file').value = '';
  el('stat-total').textContent = '0';
  el('stat-logins').textContent = '0';
  el('stat-notes').textContent = '0';
  el('stat-fav').textContent = '0';
}

async function lockUI(reason, callServer) {
  const wasUnlocked = state.unlocked || state.keyringState === 'unlocked';
  state.unlocked = false;
  state.keyringState = 'collection_locked';
  if (state.idleTimer) { clearTimeout(state.idleTimer); state.idleTimer = null; }
  if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  clearClipboardIfSame();
  clearSecretDom();
  el('lock-now').hidden = true;
  setBadge('locked', 'bad');
  showUnlockLayout('existing');
  if (wasUnlocked && callServer) {
    const res = await bridge('lock');
    if (!res.success && res.error !== 'provider_unavailable') {
      // Local state is already locked.  The provider status will be re-read on
      // the next unlock; never claim an unlocked UI after a lock attempt.
    }
  }
  if (reason === 'timeout') toast('Vault locked after inactivity');
  else if (reason === 'hidden') toast('Vault locked when hidden');
  else if (reason === 'manual') toast('Vault locked');
}

function resetIdle() {
  if (!state.unlocked) return;
  if (state.idleTimer) clearTimeout(state.idleTimer);
  const ms = Math.max(30, Number(state.autoLock) || 120) * 1000;
  state.idleTimer = setTimeout(() => lockUI('timeout', true), ms);
}

function startPoll() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    if (!state.unlocked) return;
    const st = await bridge('status');
    if (!st.success) {
      if (st.state === 'unavailable' || st.error === 'provider_unavailable') {
        await lockUI('provider-unavailable', false);
        showProviderError(st);
      } else {
        await lockUI('keyring-status-failed', false);
      }
      return;
    }
    if (st.state !== 'unlocked' || st.locked) {
      await lockUI('keyring-locked', false);
    }
  }, 30000);
}

/* ------------------------------------------------------- auth integration */

async function refreshAuthStatus() {
  const res = await bridge('authenticator-credential-status');
  let text = 'Provider unavailable.';
  if (res.success) {
    if (res.exists === true) text = 'Linked — the Authenticator credential is present and the keyring is unlocked.';
    else if (res.exists === false) text = 'Not linked. Open Authenticator → Security to opt in.';
    else if (res.state === 'keyring_locked') text = 'The keyring is locked; Authenticator cannot auto-unlock.';
    else text = 'Status: ' + (res.state || 'unknown');
  }
  el('auth-status').textContent = text;
  el('overview-auth').textContent = text;
}

async function openAuthenticator() {
  try {
    await NuxelBridge.activateApp('org.nuxel.Authenticator', 'vault');
  } catch (e) {
    toast('Open Authenticator from Home');
  }
}

/* ---------------------------------------------------------------- backup */

function downloadEncryptedArchive(text) {
  const blob = new Blob([text], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'nuxel-vault-' + new Date().toISOString().replace(/[:.]/g, '-') + '.nvault.json';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1500);
}

async function exportArchive() {
  const pass = el('export-pass').value;
  const pass2 = el('export-pass2').value;
  const note = el('export-note');
  note.textContent = '';
  if (pass !== pass2) { note.textContent = 'The export passphrases do not match.'; return; }
  const check = Archive.checkPassphrase(pass);
  if (!check.ok) { note.textContent = 'Export passphrase refused: ' + check.problems.join(', '); return; }
  if (state.busy) return;
  state.busy = true;
  try {
    const full = [];
    for (const meta of state.items) {
      const res = await bridge('get-item', { item_id: meta.id });
      if (!res.success) {
        if (res.state === 'collection_locked') { await lockUI('keyring locked', false); return; }
        note.textContent = 'Export stopped: ' + mapError(res);
        return;
      }
      full.push(res.item);
    }
    const doc = await Archive.create(full, pass);
    downloadEncryptedArchive(Archive.encode(doc));
    el('export-pass').value = '';
    el('export-pass2').value = '';
    note.textContent = 'Encrypted archive created for ' + full.length + ' item(s). Keep it and its passphrase safe.';
  } catch (e) {
    note.textContent = e.message || 'Export failed.';
  } finally {
    state.busy = false;
  }
}

async function importArchive() {
  const note = el('import-note');
  note.textContent = '';
  const file = el('import-file').files && el('import-file').files[0];
  if (!file) { note.textContent = 'Choose an encrypted archive first.'; return; }
  if (file.size > 12 * 1024 * 1024) { note.textContent = 'Archive is too large.'; return; }
  const pass = el('import-pass').value;
  const replace = document.querySelector('input[name="import-mode"]:checked').value === 'replace';
  if (replace && !el('import-backup-ack').checked) {
    note.textContent = 'Replace requires the encrypted-backup acknowledgement.';
    return;
  }
  if (state.busy) return;
  state.busy = true;
  try {
    const text = await file.text();
    const doc = Archive.importText(text);
    const items = await Archive.unlock(doc, pass);
    if (!items.length) { note.textContent = 'The archive contains no items.'; return; }
    if (replace) {
      const reset = await bridge('reset-vault', { confirm: true });
      if (!reset.success) { note.textContent = 'Replace aborted: ' + mapError(reset); return; }
    }
    let ok = 0, failed = 0;
    for (const item of items) {
      const res = await bridge('create-item', { item: item });
      if (res.success) ok++;
      else {
        failed++;
        if (res.state === 'collection_locked') { await lockUI('keyring locked', false); return; }
      }
    }
    el('import-pass').value = '';
    el('import-file').value = '';
    el('import-backup-ack').checked = false;
    await refreshItems();
    note.textContent = failed
      ? ('Imported ' + ok + ' item(s); ' + failed + ' failed. The vault is partially updated — keep your backup.')
      : ('Imported ' + ok + ' item(s) into the Nuxel Vault keyring.');
  } catch (e) {
    note.textContent = e.message || 'Import failed.';
  } finally {
    state.busy = false;
  }
}

async function refreshBackupStatus() {
  const res = await bridge('backup-status');
  el('backup-status').textContent = res.success
    ? (res.item_count + ' item(s); encrypted export format ' + res.format + '.')
    : mapError(res);
}

/* --------------------------------------------------------------- security */

async function runDiagnostics() {
  const res = await bridge('diagnostics');
  el('diag').textContent = JSON.stringify(res, null, 2);
}

async function resetVault() {
  if (el('reset-confirm').value !== 'RESET NUXEL VAULT') {
    el('reset-note').textContent = 'Type RESET NUXEL VAULT exactly to confirm.';
    return;
  }
  if (state.busy) return;
  state.busy = true;
  try {
    const res = await bridge('reset-vault', { confirm: true });
    if (!res.success) { el('reset-note').textContent = mapError(res); return; }
    el('reset-confirm').value = '';
    await refreshItems();
    el('reset-note').textContent = 'Removed ' + (res.deleted || 0) + ' Nuxel Vault item(s). Authenticator data was not touched.';
  } finally {
    state.busy = false;
  }
}

/* -------------------------------------------------------------- generator */

function generatorOptions() {
  return {
    length: Number(el('gen-length').value),
    uppercase: el('gen-upper').checked,
    lowercase: el('gen-lower').checked,
    digits: el('gen-digits').checked,
    symbols: el('gen-symbols').checked,
    excludeAmbiguous: !el('gen-ambiguous').checked,
  };
}

function generatePassword() {
  const opts = generatorOptions();
  try {
    const password = Pwgen.generate(opts);
    const bits = Pwgen.strengthBits(password, opts);
    el('gen-output').textContent = password;
    el('gen-strength').textContent = 'Local estimate: ' + bits + ' bits (' + Pwgen.strengthLabel(bits) + '). Not a breach check.';
    state.generated = password;
    resetIdle();
  } catch (e) {
    el('gen-output').textContent = '—';
    el('gen-strength').textContent = e.message || 'Generation failed.';
    state.generated = null;
  }
}

/* --------------------------------------------------------------- wiring */

function switchTab(name) {
  document.querySelectorAll('#tabs .tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach((p) => p.classList.toggle('active', p.id === 'tab-' + name));
  if (name !== 'generator') {
    el('gen-output').textContent = '—';
    el('gen-strength').textContent = '';
    state.generated = null;
  }
  resetIdle();
}

function wire() {
  el('close').addEventListener('click', () => { lockUI('close', false); try { window.close(); } catch (e) {} });
  el('retry-provider').addEventListener('click', boot);

  el('create-go').addEventListener('click', async () => {
    const pass = el('create-pass').value;
    const pass2 = el('create-pass2').value;
    const err = el('create-error');
    err.textContent = '';
    if (pass.length < 10) { err.textContent = 'Use at least 10 characters.'; return; }
    if (pass !== pass2) { err.textContent = 'The master passwords do not match.'; return; }
    if (state.busy) return;
    state.busy = true;
    try {
      const res = await bridge('initialize', { master_password: pass, label: 'Nuxel Vault' });
      el('create-pass').value = '';
      el('create-pass2').value = '';
      if (!res.success) { err.textContent = mapError(res); return; }
      await enterMain();
    } finally {
      state.busy = false;
    }
  });
  const toggleCreate = () => {
    const p = el('create-pass'), p2 = el('create-pass2');
    const show = p.type === 'password';
    p.type = p2.type = show ? 'text' : 'password';
    el('create-toggle').textContent = show ? 'Hide' : 'Show';
  };
  el('create-toggle').addEventListener('click', toggleCreate);

  el('unlock-go').addEventListener('click', async () => {
    const pass = el('unlock-pass').value;
    const err = el('unlock-error');
    err.textContent = '';
    if (!pass) { err.textContent = 'Enter the Nuxel Vault master password.'; return; }
    if (state.busy) return;
    state.busy = true;
    try {
      const res = await bridge('unlock', { master_password: pass });
      el('unlock-pass').value = '';
      if (!res.success) {
        if (res.state === 'unavailable') showProviderError(res);
        else err.textContent = mapError(res);
        return;
      }
      await enterMain();
    } finally {
      state.busy = false;
    }
  });
  el('unlock-pass').addEventListener('keydown', (e) => { if (e.key === 'Enter') el('unlock-go').click(); });
  el('create-pass2').addEventListener('keydown', (e) => { if (e.key === 'Enter') el('create-go').click(); });
  el('unlock-toggle').addEventListener('click', () => {
    const p = el('unlock-pass');
    const show = p.type === 'password';
    p.type = show ? 'text' : 'password';
    el('unlock-toggle').textContent = show ? 'Hide' : 'Show';
  });
  el('unlock-cancel').addEventListener('click', () => {
    el('unlock-pass').value = '';
    el('unlock-error').textContent = '';
    toast('Keyring remains locked');
  });

  document.querySelectorAll('#tabs .tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  document.querySelectorAll('[data-add]').forEach((b) => b.addEventListener('click', () => {
    if (!state.unlocked) return;
    openEditor(b.dataset.add, null);
  }));

  el('lock-now').addEventListener('click', () => lockUI('manual', true));
  el('overview-lock').addEventListener('click', () => lockUI('manual', true));
  el('security-lock').addEventListener('click', () => lockUI('manual', true));

  el('login-search').addEventListener('input', () => { state.filterLogin = el('login-search').value; renderAll(); });
  el('note-search').addEventListener('input', () => { state.filterNote = el('note-search').value; renderAll(); });

  el('editor-close').addEventListener('click', () => { el('editor').hidden = true; clearEditor(); });
  el('editor-cancel').addEventListener('click', () => { el('editor').hidden = true; clearEditor(); });
  el('editor-save').addEventListener('click', saveEditor);
  el('edit-password-toggle').addEventListener('click', () => {
    const p = el('edit-password');
    const show = p.type === 'password';
    p.type = show ? 'text' : 'password';
    el('edit-password-toggle').textContent = show ? 'Hide password' : 'Show password';
  });
  el('edit-generate').addEventListener('click', () => {
    try {
      const opts = { length: 20, uppercase: true, lowercase: true, digits: true, symbols: true, excludeAmbiguous: true };
      el('edit-password').value = Pwgen.generate(opts);
      toast('Generated password placed in the field');
    } catch (e) { toast('Generator unavailable'); }
  });

  el('detail-close').addEventListener('click', closeDetail);
  el('detail-copy-user').addEventListener('click', () => {
    if (state.detailItem) copySecret(state.detailItem.username, 'username');
  });
  el('detail-copy-pass').addEventListener('click', () => {
    if (state.detailItem) copySecret(state.detailItem.password, 'password');
  });
  el('detail-edit').addEventListener('click', () => {
    const item = state.detailItem;
    if (!item) return;
    closeDetail();
    openEditor(item.type, item);
  });
  el('detail-delete').addEventListener('click', async () => {
    const item = state.detailItem;
    if (!item) return;
    if (!window.confirm('Delete "' + item.title + '"? This cannot be undone.')) return;
    const res = await bridge('delete-item', { item_id: item.id });
    if (!res.success) { toast(mapError(res)); return; }
    closeDetail();
    await refreshItems();
    toast('Item deleted');
  });

  el('gen-length').addEventListener('input', () => { el('gen-length-label').textContent = el('gen-length').value; });
  el('gen-go').addEventListener('click', generatePassword);
  el('gen-copy').addEventListener('click', () => copySecret(state.generated, 'password'));
  el('gen-use').addEventListener('click', () => {
    if (!state.generated) { toast('Generate a password first'); return; }
    const p = state.generated;
    openEditor('login', null);
    el('edit-password').value = p;
    toast('Generated password placed in the new login');
  });

  el('auth-refresh').addEventListener('click', refreshAuthStatus);
  el('auth-open').addEventListener('click', openAuthenticator);
  el('overview-auth-open').addEventListener('click', openAuthenticator);

  el('export-go').addEventListener('click', exportArchive);
  el('import-go').addEventListener('click', importArchive);
  el('backup-status-refresh').addEventListener('click', refreshBackupStatus);

  el('autolock').value = String(state.autoLock);
  el('autolock').addEventListener('change', () => {
    state.autoLock = Number(el('autolock').value) || 120;
    localStorage.setItem(AUTO_LOCK_KEY, String(state.autoLock));
    resetIdle();
  });
  el('lock-on-hide').checked = state.lockOnHide;
  el('lock-on-hide').addEventListener('change', () => {
    state.lockOnHide = el('lock-on-hide').checked;
    localStorage.setItem(LOCK_ON_HIDE_KEY, state.lockOnHide ? '1' : '0');
  });
  el('diag-refresh').addEventListener('click', runDiagnostics);
  el('reset-go').addEventListener('click', resetVault);

  ['pointerdown', 'keydown', 'input'].forEach((name) => {
    document.addEventListener(name, () => { if (state.unlocked) resetIdle(); }, { passive: true });
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && state.unlocked) {
      if (state.lockOnHide) lockUI('hidden', false);
      else resetIdle();
    }
  });
  window.addEventListener('pagehide', () => { if (state.unlocked) lockUI('pagehide', false); });
}

function bootFailure(error) {
  const box = el('boot-error');
  if (box) {
    box.hidden = false;
    box.textContent = 'Vault failed to start: ' + ((error && error.message) || error || 'unknown error');
  }
  try { console.error('[vault] startup failed:', (error && error.message) || error); } catch (e) {}
}

try { wire(); } catch (error) { bootFailure(error); }
try { boot().catch(bootFailure); } catch (error) { bootFailure(error); }

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js').catch(() => { /* shell cache is optional */ });
}
