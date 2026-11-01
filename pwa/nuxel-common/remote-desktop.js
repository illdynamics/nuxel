// Shared Nuxel GUI Tri-Link controller (PWNAGE-47000).
//
// One Bridge namespace, one status model, three documents.  This module never
// fabricates READY/CONNECTED: it renders exactly what system.remote-desktop
// reports, and a failed bridge call is shown as an error.
import { bridge } from '/pwa/nuxel-common/bridge.js';

const STATE_LABEL = {
  OFF: 'OFF', STARTING: 'STARTING', READY: 'READY', WAITING_FOR_CLIENT: 'WAITING FOR CLIENT',
  CONNECTED: 'CONNECTED', STOPPING: 'STOPPING', BLOCKED: 'BLOCKED', BLOCKED_KERNEL_PANIC: 'BLOCKED · KERNEL PANIC EVIDENCE',
  UNSUPPORTED: 'UNSUPPORTED', UNSUPPORTED_NO_SCRCPY_BINARY: 'UNSUPPORTED · NO OFFICIAL SCRCPY PACKAGE',
  NO_ANDROID_TARGET: 'NO ANDROID TARGET', NOT_APPLICABLE_NATIVE_NUXEL: 'NOT APPLICABLE · NATIVE NUXEL',
  ERROR: 'ERROR',
};
const STATE_KEY = {
  READY: 'ready', CONNECTED: 'connected', STARTING: 'starting', WAITING_FOR_CLIENT: 'waiting', STOPPING: 'starting',
  OFF: 'off', BLOCKED: 'blocked', BLOCKED_KERNEL_PANIC: 'blocked', UNSUPPORTED: 'unsupported',
  UNSUPPORTED_NO_SCRCPY_BINARY: 'unsupported', NO_ANDROID_TARGET: 'blocked', NOT_APPLICABLE_NATIVE_NUXEL: 'unsupported',
  ERROR: 'error',
};

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}
async function copyText(text) {
  if (!text) return false;
  try { if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(text); return true; } } catch (e) {}
  try {
    const a = document.createElement('textarea'); a.value = text; a.style.position='fixed'; a.style.opacity='0';
    document.body.appendChild(a); a.select(); const ok = document.execCommand && document.execCommand('copy'); a.remove(); return !!ok;
  } catch (e) { return false; }
}
function confirmDialog(title, body) {
  return new Promise((resolve) => {
    const wrap = el('div', 'rd-modal');
    const card = el('div', 'rd-modal-card');
    card.appendChild(el('h2', '', title));
    card.appendChild(el('p', '', body));
    const row = el('div', 'rd-actions');
    const cancel = el('button', '', 'Cancel'); cancel.type = 'button';
    const ok = el('button', 'danger', 'Start remote access'); ok.type = 'button';
    cancel.onclick = () => { wrap.remove(); resolve(false); };
    ok.onclick = () => { wrap.remove(); resolve(true); };
    row.append(cancel, ok); card.appendChild(row); wrap.appendChild(card); document.body.appendChild(wrap);
    ok.focus();
  });
}

export function startRemoteApp(cfg) {
  document.body.dataset.appId = cfg.appId;
  const main = document.getElementById('remote-app') || document.body;
  main.innerHTML = '';
  const head = el('header', 'rd-head');
  const mark = el('div', 'rd-mark');
  const icon = el('img'); icon.src = cfg.icon; icon.alt = '';
  icon.onerror = () => { icon.remove(); mark.textContent = cfg.glyph || '⇄'; };
  mark.appendChild(icon);
  const titles = el('div');
  titles.appendChild(el('h1', '', cfg.title));
  titles.appendChild(el('p', 'rd-sub', cfg.subtitle));
  head.append(mark, titles); main.appendChild(head);

  const banner = el('div', 'rd-banner');
  const bannerText = el('span'); bannerText.innerHTML = '<span class="dot"></span>REMOTE DESKTOP ACTIVE';
  const kill = el('button', 'danger', 'Stop all'); kill.type = 'button';
  banner.append(bannerText, kill); main.appendChild(banner);

  const card = el('section', 'rd-card');
  const stateRow = el('div', 'rd-state-row');
  const state = el('span', 'rd-state', 'CHECKING'); state.dataset.state = 'starting';
  const pill = el('span', 'rd-pill', cfg.sessionLabel || '');
  stateRow.append(state, pill); card.appendChild(stateRow);
  const reason = el('p', 'rd-detail', 'Reading remote-access status…'); card.appendChild(reason);
  const kv = el('dl', 'rd-kv'); card.appendChild(kv);

  const seg = el('div', 'rd-seg'); card.appendChild(seg);
  const actions = el('div', 'rd-actions');
  const start = el('button', 'primary', 'Start'); start.type = 'button';
  const stop = el('button', 'danger', 'Stop'); stop.type = 'button'; stop.disabled = true;
  const recheck = el('button', '', 'Recheck'); recheck.type = 'button';
  const copy = el('button', 'ghost', 'Copy connection details'); copy.type = 'button';
  actions.append(start, stop, recheck, copy); card.appendChild(actions);
  const command = el('pre', 'rd-command rd-hidden'); card.appendChild(command);
  const checks = el('ul', 'rd-checks rd-hidden'); card.appendChild(checks);
  const note = el('p', 'rd-note'); card.appendChild(note);
  main.appendChild(card);

  let last = null; let busy = false; let confirmedStart = false;
  let timer = null;

  function row(term, value) {
    kv.appendChild(el('dt', '', term));
    kv.appendChild(el('dd', '', value == null || value === '' ? '—' : String(value)));
  }
  function render(doc, failure) {
    kv.innerHTML = ''; checks.innerHTML = ''; seg.innerHTML = ''; command.classList.add('rd-hidden');
    if (failure) {
      state.textContent = 'ERROR'; state.dataset.state = 'error';
      reason.textContent = failure;
      banner.classList.remove('on'); start.disabled = true; stop.disabled = true; copy.disabled = true;
      return;
    }
    last = doc;
    const svc = doc.services && doc.services[cfg.service];
    if (!svc) { render(null, 'Bridge response is missing ' + cfg.service + '.'); return; }
    const key = STATE_KEY[svc.state] || 'error';
    state.textContent = STATE_LABEL[svc.state] || svc.state || 'UNKNOWN';
    state.dataset.state = key;
    reason.textContent = svc.reason || 'No additional detail reported.';
    const active = doc.privacy && doc.privacy.active;
    banner.classList.toggle('on', !!active);
    kill.disabled = !active;
    start.disabled = busy || svc.state !== 'OFF' && svc.state !== 'ERROR';
    stop.disabled = busy || !['READY','WAITING_FOR_CLIENT','CONNECTED','STARTING'].includes(svc.state);
    copy.disabled = false;

    row('Session', svc.session_mode_label || svc.session_mode || '—');
    row('Preferred', (svc.preferred_transport || '—').toUpperCase());
    row('Active', svc.active_transport ? String(svc.active_transport).toUpperCase() : '—');
    row('Phone LAN', doc.network && doc.network.address ? doc.network.address + ' (' + (doc.network.interface || '?') + ')' : 'not discovered');
    row('Listener', svc.bind_address ? svc.bind_address + ':' + svc.port + (svc.listener_verified ? ' ✓' : ' (closed)') : '—');
    row('Auth', svc.authentication || '—');
    row('Encrypted', svc.encrypted ? 'yes · ' + (svc.encrypted_detail || '') : 'no');
    if (svc.version) row('Version', svc.version);
    if (svc.tls_fingerprint) row('TLS SHA-256', svc.tls_fingerprint);
    if (cfg.service !== 'scrcpy') row('Clients', String(svc.authenticated_clients || 0) + (svc.client_status_available === false ? ' (provider unavailable)' : ''));
    if (svc.active_users && svc.active_users.length) row('Remote users', svc.active_users.join(', '));
    if (svc.started_at) row('Started', new Date(svc.started_at * 1000).toLocaleString());
    if (cfg.service === 'scrcpy') {
      row('ADB', svc.adb_available ? (svc.adb_version || 'available') : 'missing');
      row('Targets', String(svc.target_count || 0));
      row('scrcpy', svc.scrcpy_available ? (svc.scrcpy_version || 'available') : 'no official Fedora 43 aarch64 package');
    }
    if (svc.usb) row('USB route', svc.usb.status + (svc.usb.reason ? ' · ' + svc.usb.reason : ''));

    (cfg.transports || []).forEach((t) => {
      const b = el('button', (svc.preferred_transport === t.id ? 'selected' : ''));
      b.type = 'button';
      b.innerHTML = t.label + '<small>' + (t.detail || '') + '</small>';
      const blocked = t.id === 'usb' && svc.usb && svc.usb.available === false;
      b.disabled = blocked || busy;
      b.onclick = async () => {
        if (blocked) return;
        busy = true; b.disabled = true;
        try {
          const r = await bridge.call('system', 'remote-desktop', { action: 'set-transport', service: cfg.service, transport: t.id });
          if (!r || r.success === false) render(null, (r && (r.error || r.detail)) || 'Transport change refused.');
          else await refresh();
        } catch (e) { render(null, 'Transport change failed: ' + (e.message || e)); }
        finally { busy = false; }
      };
      seg.appendChild(b);
    });

    if (svc.protocols) {
      const missing = svc.missing_protocols || [];
      (svc.protocols.protocols || []).slice(0, 40).forEach(() => {});
      if (cfg.service === 'vnc') {
        const li = el('li'); li.appendChild(el('b', '', 'Phoc protocols'));
        li.appendChild(el('span', '', missing.length ? 'MISSING ' + missing.join(', ') : 'screencopy + virtual pointer/keyboard advertised'));
        checks.appendChild(li);
      }
    }
    if (cfg.service === 'scrcpy') {
      const li = el('li'); li.appendChild(el('b', '', 'Native Nuxel'));
      li.appendChild(el('span', '', svc.native_nuxel_note || 'scrcpy is Android-only'));
      checks.appendChild(li);
      const link = el('a', 'rd-link', 'Open VNC Screen Sharing for native Nuxel →');
      link.href = '/pwa/nuxel-apps/remote-vnc/index.html';
      note.innerHTML = ''; note.appendChild(link);
    } else {
      note.innerHTML = cfg.note || '';
    }
    if (checks.children.length) checks.classList.remove('rd-hidden');
    if (last && last.services && last.services[cfg.service] && last.services[cfg.service].last_error && svc.state === 'ERROR') {
      command.textContent = svc.last_error; command.classList.remove('rd-hidden');
    }
  }

  async function remoteCall(action, extra) {
    const params = Object.assign({ action, service: cfg.service }, extra || {});
    return bridge.call('system', 'remote-desktop', params);
  }
  async function refresh() {
    if (busy) return;
    busy = true; recheck.disabled = true;
    try {
      const doc = await remoteCall('status');
      if (!doc || doc.success === false) render(null, (doc && (doc.error || doc.detail)) || 'Nuxel Bridge did not return remote-desktop status.');
      else render(doc);
    } catch (e) { render(null, 'Remote-desktop status unavailable: ' + (e.message || e)); }
    finally { busy = false; recheck.disabled = false; }
  }
  async function doStart() {
    if (!confirmedStart) {
      const ok = await confirmDialog('Start ' + cfg.title + '?',
        cfg.confirmText || 'This exposes remote control of this phone over the selected transport while it is running. The listener is authenticated and restricted to the owner LAN/tunnel. Nuxel never starts it at boot.');
      if (!ok) return;
      confirmedStart = true;
    }
    busy = true; start.disabled = true;
    try {
      const r = await remoteCall('start', { transport: (last && last.services && last.services[cfg.service] && last.services[cfg.service].preferred_transport) || cfg.defaultTransport });
      if (!r || r.success === false) render(null, (r && (r.error || r.detail)) || 'Start was refused.');
      else await refresh();
    } catch (e) { render(null, 'Start failed: ' + (e.message || e)); }
    finally { busy = false; confirmedStart = false; }
  }
  async function doStop() {
    busy = true; stop.disabled = true;
    try {
      const r = await remoteCall('stop');
      if (!r || r.success === false) render(null, (r && (r.error || r.detail)) || 'Stop was refused.');
      else await refresh();
    } catch (e) { render(null, 'Stop failed: ' + (e.message || e)); }
    finally { busy = false; }
  }
  start.onclick = doStart; stop.onclick = doStop; recheck.onclick = refresh;
  copy.onclick = async () => {
    const r = await remoteCall('connection-info');
    const text = r && r.success ? [
      'Nuxel ' + cfg.title,
      'Session: ' + (last && last.services[cfg.service] ? last.services[cfg.service].session_mode_label : ''),
      r.ssh_tunnel_command ? 'SSH tunnel (Mac): ' + r.ssh_tunnel_command : '',
      r.jump_url ? 'Jump Desktop URL: ' + r.jump_url : '',
      r.tls_fingerprint ? 'TLS SHA-256: ' + r.tls_fingerprint : '',
      'Password: not included; set it in the secure provider flow.',
    ].filter(Boolean).join('\n') : 'Connection details unavailable';
    const ok = await copyText(text);
    copy.textContent = ok ? 'Copied' : 'Copy failed';
    setTimeout(() => { copy.textContent = 'Copy connection details'; }, 1600);
  };
  kill.onclick = async () => {
    kill.disabled = true;
    try { await bridge.call('system', 'remote-desktop', { action: 'stop-all' }); await refresh(); }
    catch (e) { render(null, 'Kill switch failed: ' + (e.message || e)); }
  };

  refresh();
  timer = setInterval(() => { if (!document.hidden) refresh(); }, 5000);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { if (timer) { clearInterval(timer); timer = null; } }
    else { if (!timer) timer = setInterval(refresh, 5000); refresh(); }
  });
}
