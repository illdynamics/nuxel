// Shared Tri-Link console view.  The three Applications entries are separate
// documents with an explicit transport; this module never guesses or silently
// switches transport.  The actual SSH/serial session runs from the development
// host (tools/beta/live/nuxel-live-ssh.py); this surface reports the phone-side
// endpoint truth and the exact host command.
import { bridge } from '/pwa/nuxel-common/bridge.js';

const MODES = {
  serial: {
    appId: 'org.nuxel.LiveConsole',
    title: 'Serial Live Console',
    subtitle: 'USB CDC-ACM recovery console · exclusive serial owner',
    icon: '/assets/nuxel-applications-icon-pack/05-05_live-console.png',
    transport: 'serial',
  },
  usb: {
    appId: 'org.nuxel.USBSSHConsole',
    title: 'USB SSH Console',
    subtitle: 'SSH over the USB network gadget · capability-gated',
    icon: '/assets/nuxel-applications-icon-pack/06-05_usb-connection.png',
    transport: 'usb',
  },
  wifi: {
    appId: 'org.nuxel.WiFiSSHConsole',
    title: 'Wi-Fi SSH Console',
    subtitle: 'Key-only SSH over the phone\u2019s Wi-Fi address',
    icon: '/assets/nuxel-quicksettings-icon-pack/01-wifi.png',
    transport: 'wifi',
  },
};

const STATE_LABELS = {
  READY: 'READY',
  AVAILABLE: 'READY',
  CHECKING: 'CHECKING',
  SETUP: 'SETUP REQUIRED',
  BLOCKED_KERNEL_PANIC: 'UNAVAILABLE · KERNEL BLOCKER',
  BLOCKED_KERNEL: 'UNAVAILABLE · KERNEL SUPPORT MISSING',
  SUPPORTED_NOT_ENABLED: 'SETUP REQUIRED',
  UNAVAILABLE: 'UNAVAILABLE',
  UNKNOWN: 'UNKNOWN',
};

function stateKey(status) {
  if (!status) return 'checking';
  if (status === 'AVAILABLE' || status === 'READY') return 'ready';
  if (status === 'CHECKING') return 'checking';
  if (status.startsWith('BLOCKED')) return 'blocked';
  if (status === 'SUPPORTED_NOT_ENABLED' || status === 'SETUP') return 'setup';
  return 'unavailable';
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function copyText(text) {
  if (!text) return false;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) { /* fall through to the selection fallback */ }
  try {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand && document.execCommand('copy');
    area.remove();
    return !!ok;
  } catch (e) { return false; }
}

export function startTriLinkConsole(mode) {
  const cfg = MODES[mode];
  if (!cfg) throw new Error('unknown Tri-Link transport: ' + mode);
  document.body.dataset.transport = mode;
  document.body.dataset.appId = cfg.appId;

  const main = document.getElementById('tri-link-console') || document.body;
  main.innerHTML = '';

  const head = el('header', 'tl-head');
  const mark = el('div', 'tl-mark');
  const icon = el('img');
  icon.src = cfg.icon;
  icon.alt = '';
  icon.onerror = () => { icon.remove(); mark.textContent = mode === 'wifi' ? '\u224b' : (mode === 'usb' ? '\u26a1' : '\u25a3'); };
  mark.appendChild(icon);
  const titles = el('div');
  titles.appendChild(el('h1', '', cfg.title));
  titles.appendChild(el('p', 'tl-sub', cfg.subtitle));
  head.append(mark, titles);
  main.appendChild(head);

  const card = el('section', 'tl-card');
  card.setAttribute('aria-live', 'polite');
  const stateRow = el('div', 'tl-state-row');
  const state = el('span', 'tl-state', 'CHECKING');
  state.dataset.state = 'checking';
  const dot = el('span', 'tl-dot');
  dot.setAttribute('aria-hidden', 'true');
  stateRow.append(state, dot);
  card.appendChild(stateRow);

  const kv = el('dl', 'tl-kv');
  card.appendChild(kv);
  const detail = el('p', 'tl-detail', 'Reading phone-side transport state\u2026');
  card.appendChild(detail);

  const command = el('pre', 'tl-command hidden');
  card.appendChild(command);

  const actions = el('div', 'tl-actions');
  const recheck = el('button', 'primary', 'Recheck');
  recheck.type = 'button';
  const copy = el('button', '', 'Copy host command');
  copy.type = 'button';
  copy.disabled = true;
  actions.append(recheck, copy);
  card.appendChild(actions);

  const checks = el('ul', 'tl-checks hidden');
  card.appendChild(checks);
  const note = el('p', 'tl-note', 'This app verifies the phone endpoint. The authenticated interactive session runs on the development host; no key is stored on the phone.');
  card.appendChild(note);
  main.appendChild(card);

  let last = null;
  let busy = false;

  function row(term, value) {
    kv.appendChild(el('dt', '', term));
    kv.appendChild(el('dd', '', value || '\u2014'));
  }

  function render(doc, failure) {
    kv.innerHTML = '';
    checks.innerHTML = '';
    if (failure) {
      state.textContent = 'UNAVAILABLE';
      state.dataset.state = 'unavailable';
      detail.textContent = failure;
      copy.disabled = true;
      command.classList.add('hidden');
      return;
    }
    last = doc;
    const key = stateKey(doc.status);
    state.textContent = STATE_LABELS[doc.status] || doc.status || 'UNKNOWN';
    state.dataset.state = key;
    row('Transport', cfg.transport.toUpperCase());
    row('Target', doc.target || 'not configured');
    row('Auth', doc.auth || 'not applicable');
    if (doc.host_command) {
      command.textContent = doc.host_command;
      command.classList.remove('hidden');
      copy.disabled = false;
    } else {
      command.classList.add('hidden');
      copy.disabled = true;
    }
    detail.textContent = doc.detail || 'No additional detail reported.';
    (doc.checks || []).forEach((check) => {
      const li = el('li');
      li.appendChild(el('b', '', check.name || '?'));
      li.appendChild(el('span', '', (check.status || '') + (check.detail ? ' \u00b7 ' + check.detail : '')));
      checks.appendChild(li);
    });
    if ((doc.checks || []).length) checks.classList.remove('hidden');
    if (doc.status === 'BLOCKED_KERNEL_PANIC' || doc.status === 'BLOCKED_KERNEL') {
      note.textContent = 'No USB network is created by this app. The kernel/gadget blocker is documented; serial recovery remains independent.';
    }
  }

  async function refresh() {
    if (busy) return;
    busy = true;
    recheck.disabled = true;
    state.textContent = 'CHECKING';
    state.dataset.state = 'checking';
    detail.textContent = 'Reading phone-side transport state\u2026';
    try {
      const result = await bridge.call('system', 'tri-link', { transport: cfg.transport });
      if (!result || result.success === false) {
        render(null, (result && (result.error || result.detail)) || 'Nuxel bridge did not return Tri-Link status.');
      } else if (!result.transports || !result.transports[cfg.transport]) {
        render(null, 'Tri-Link status is missing the ' + cfg.transport + ' transport.');
      } else {
        render(result.transports[cfg.transport]);
      }
    } catch (error) {
      render(null, 'Tri-Link status unavailable: ' + (error && error.message ? error.message : String(error)));
    } finally {
      busy = false;
      recheck.disabled = false;
    }
  }

  recheck.addEventListener('click', refresh);
  copy.addEventListener('click', async () => {
    if (!last || !last.host_command) return;
    const ok = await copyText(last.host_command);
    copy.textContent = ok ? 'Copied' : 'Copy failed';
    setTimeout(() => { copy.textContent = 'Copy host command'; }, 1600);
  });

  refresh();
  // Bound refresh while this document is visible.  Nothing is started, no
  // privileged action is taken; this only re-reads read-only status.
  let timer = setInterval(() => { if (!document.hidden) refresh(); }, 5000);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { clearInterval(timer); timer = null; }
    else if (!timer) { timer = setInterval(refresh, 5000); refresh(); }
  });
}

// Node/offline test hook: no DOM is touched unless startTriLinkConsole() runs.
try { globalThis.NuxelTriLinkModes = MODES; } catch (e) { /* ignore */ }
