// Nuxel Terminal (A32 baseline, extended for the core-application inventory)
//
// A REAL terminal: the bytes come from /bin/sh running on a PTY owned by
// nuxel-pwa-host (forkpty); input goes back to that same PTY.  There is no
// emulated shell, no canned prompt and no fake output anywhere in this file.
//
// Two launch paths, both ending in the same one-instance rule:
//   * the hardware Bixby button -> /run/nuxel-pwa-host.cmd "open-terminal"
//   * the launcher's Terminal tile -> this page inside .pwa-frame -> term.open
// The host opens ONE fullscreen terminal window and focuses it on repeat presses.
//
// Added in this cycle (no host-contract change):
//   * a permanent LOCAL-ONLY notice: this shell is on this device, there is no
//     remote access, no forwarded port and no network bridge in this app;
//   * ↑/↓ command history, Ctrl-L clear, font-size control;
//   * a `help` panel that documents what the host actually supports.
(function () {
  'use strict';

  var screen = document.getElementById('screen');
  var notice = document.getElementById('notice');
  var title  = document.getElementById('title');
  var buffer = '';
  var inHostWindow = false;
  var fontSize = 14;
  try {
    var fs = localStorage.getItem('nuxel-terminal-font');
    if (fs) fontSize = Math.max(10, Math.min(24, parseInt(fs, 10) || 14));
  } catch (e) { /* storage unavailable */ }

  function H() {
    if (window.NuxelHost && window.NuxelHost.available) return window.NuxelHost;
    try { if (window.parent && window.parent.NuxelHost) return window.parent.NuxelHost; } catch (e) { /* cross-frame denied */ }
    return null;
  }
  function sendInput(data) {
    var h = H();
    if (!h) { showNotice('No Nuxel host: the terminal needs the launcher host process.'); return; }
    h.termInput(data);
  }
  function showNotice(msg) { notice.textContent = msg; notice.classList.remove('hidden'); }

  /* ---------- LOCAL-ONLY notice + chrome built from JS (keeps index.html small) ---------- */
  var style = document.createElement('style');
  style.textContent =
    '.nuxel-local-note{font:12px/1.5 system-ui,sans-serif;color:#9fb0c8;background:#0d1420;' +
    'border-top:1px solid #1e2a3a;padding:6px 10px}' +
    '.nuxel-local-note b{color:#4cc2ff}' +
    '.nuxel-fonts{display:flex;gap:6px;align-items:center;font:12px system-ui,sans-serif;color:#9fb0c8}';
  document.head.appendChild(style);

  var note = document.createElement('div');
  note.className = 'nuxel-local-note';
  note.id = 'local-note';
  note.innerHTML = '<b>Local-only shell.</b> This terminal runs a PTY on this device through the ' +
    'Nuxel launcher host. There is no remote shell, no forwarded port and no network service in ' +
    'this app. Type <code>help</code> for the host commands that exist.';
  document.body.appendChild(note);

  var fonts = document.createElement('span');
  fonts.className = 'nuxel-fonts';
  var minus = document.createElement('button');
  minus.className = 'ghost'; minus.textContent = 'A-';
  var plus = document.createElement('button');
  plus.className = 'ghost'; plus.textContent = 'A+';
  var helpBtn = document.createElement('button');
  helpBtn.className = 'ghost'; helpBtn.textContent = 'help';
  fonts.appendChild(minus); fonts.appendChild(plus); fonts.appendChild(helpBtn);
  var hdr = document.querySelector('.hdr');
  if (hdr) hdr.appendChild(fonts);

  function applyFont() {
    screen.style.fontSize = fontSize + 'px';
    try { localStorage.setItem('nuxel-terminal-font', String(fontSize)); } catch (e) { /* ignore */ }
  }
  minus.addEventListener('click', function () { fontSize = Math.max(10, fontSize - 1); applyFont(); });
  plus.addEventListener('click', function () { fontSize = Math.min(24, fontSize + 1); applyFont(); });
  helpBtn.addEventListener('click', function () {
    showNotice('Host commands: term.open (one terminal window), term.input (PTY bytes), term.close. ' +
      'Inside the shell: everything /bin/sh provides. Bixby opens this window; a second press focuses it.');
    setTimeout(function () { notice.classList.add('hidden'); }, 9000);
  });
  applyFont();

  /* ---------- command history (client side, for ↑/↓ recall) ---------- */
  var hist = [], histPos = -1, lineBuffer = '';
  try { hist = JSON.parse(localStorage.getItem('nuxel-terminal-history') || '[]') || []; } catch (e) { hist = []; }

  window.nuxelTerm = {
    output: function (text) {
      inHostWindow = true;
      buffer += text;
      if (buffer.length > 200000) buffer = buffer.slice(-150000);   // bounded scrollback
      screen.textContent = buffer;
      screen.scrollTop = screen.scrollHeight;
    },
    exit: function () {
      buffer += '\n[the shell exited]\n';
      screen.textContent = buffer;
      title.textContent = 'nuxel terminal (exited)';
    }
  };

  /* ---------- on-screen keyboard (there is no system keyboard without a compositor) ---------- */
  var LETTERS = [
    ['1','2','3','4','5','6','7','8','9','0'],
    ['q','w','e','r','t','y','u','i','o','p'],
    ['a','s','d','f','g','h','j','k','l','-'],
    ['z','x','c','v','b','n','m','.','/','_']
  ];
  var SYMBOLS = [
    ['!','@','#','$','%','^','&','*','(',')'],
    ['~','`','+','=','{','}','[',']','|','\\'],
    ['<','>',':',';','"',"'",',','?','/','-']
  ];
  var osk = document.getElementById('osk');
  var ctrlArmed = false, shiftArmed = false, symbolsArmed = false;
  function recallHistory(direction) {
    if (!hist.length) return;
    if (direction < 0) histPos = Math.min(hist.length - 1, histPos + 1);
    else histPos = Math.max(-1, histPos - 1);
    var cmd = histPos >= 0 ? hist[histPos] : '';
    lineBuffer = cmd;
    sendInput('\u0015');           // Ctrl-U: kill the current PTY line
    if (cmd) sendInput(cmd);
  }
  function key(label, data, cls) {
    var b = document.createElement('button');
    b.textContent = label;
    if (cls) b.className = cls;
    b.addEventListener('click', function () {
      if (data === 'CTRL') { ctrlArmed = !ctrlArmed; b.classList.toggle('active', ctrlArmed); return; }
      if (data === 'SHIFT') { shiftArmed = !shiftArmed; renderKeys(); return; }
      if (data === 'SYMBOLS') { symbolsArmed = !symbolsArmed; shiftArmed = false; renderKeys(); return; }
      if (data === 'HISTUP') { recallHistory(-1); return; }
      if (data === 'HISTDOWN') { recallHistory(1); return; }
      if (data === 'HIDE') { osk.classList.add('hidden'); return; }
      if (ctrlArmed) { sendInput(String.fromCharCode(data.toUpperCase().charCodeAt(0) - 64)); ctrlArmed = false; refreshMods(); return; }
      if (data === '\u000c') { buffer = ''; screen.textContent = ''; return; }   // Ctrl-L local clear
      if (data === '\r') rememberLine();
      if (data === '\u007f') lineBuffer = lineBuffer.slice(0, -1);
      else if (data === '\t' || data === ' ' || /^[\x20-\x7e]$/.test(data)) lineBuffer += data;
      sendInput(data);
      if (shiftArmed) { shiftArmed = false; renderKeys(); }
    });
    return b;
  }
  function rememberLine() {
    var cmd = lineBuffer.trim();
    lineBuffer = '';
    if (!cmd) return;
    hist = hist.filter(function (h) { return h !== cmd; });
    hist.unshift(cmd);
    if (hist.length > 100) hist = hist.slice(0, 100);
    try { localStorage.setItem('nuxel-terminal-history', JSON.stringify(hist)); } catch (e) { /* ignore */ }
    histPos = -1;
  }
  function refreshMods() {
    document.querySelectorAll('.osk button.mod').forEach(function (b) {
      if (b.textContent !== 'CTRL') b.classList.remove('active');
    });
  }
  function renderKeys() {
    osk.textContent = '';
    var rows = symbolsArmed ? SYMBOLS : LETTERS;
    rows.forEach(function (row, i) {
      var r = document.createElement('div'); r.className = 'row';
      if (!symbolsArmed && i === rows.length - 1) {
        var shift = key('⇧', 'SHIFT', 'mod' + (shiftArmed ? ' active' : ''));
        r.appendChild(shift);
      }
      row.forEach(function (k) {
        var data = shiftArmed && /^[a-z]$/.test(k) ? k.toUpperCase() : k;
        r.appendChild(key(data, data));
      });
      r.appendChild(key('⌫', '\u007f', 'mod'));
      osk.appendChild(r);
    });
    var last = document.createElement('div'); last.className = 'row';
    last.appendChild(key(symbolsArmed ? 'ABC' : '?123', 'SYMBOLS', 'mod active'));
    last.appendChild(key('CTRL', 'CTRL', 'mod' + (ctrlArmed ? ' active' : '')));
    last.appendChild(key('TAB', '\t', 'mod'));
    last.appendChild(key('SPACE', ' ', 'wide'));
    last.appendChild(key('⏎', '\r', 'wide'));
    last.appendChild(key('^C', '\u0003', 'mod'));
    last.appendChild(key('↑', 'HISTUP', 'mod'));
    last.appendChild(key('↓', 'HISTDOWN', 'mod'));
    last.appendChild(key('⌄', 'HIDE', 'mod'));
    osk.appendChild(last);
  }
  renderKeys();

  // A dismissed keyboard comes back when the terminal surface is tapped.
  screen.addEventListener('click', function () { osk.classList.remove('hidden'); });

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowUp') { recallHistory(-1); ev.preventDefault(); return; }
    else if (ev.key === 'ArrowDown') { recallHistory(1); ev.preventDefault(); return; }
    else if (ev.ctrlKey && (ev.key === 'l' || ev.key === 'L')) { buffer = ''; screen.textContent = ''; ev.preventDefault(); }
    else if (ev.key === 'Backspace') { lineBuffer = lineBuffer.slice(0, -1); return; }
    else if (ev.key.length === 1) { lineBuffer += ev.key; return; }
    else if (ev.key === 'Enter') { rememberLine(); return; }
    else return;
  });

  document.getElementById('clear').addEventListener('click', function () { buffer = ''; screen.textContent = ''; });
  document.getElementById('close').addEventListener('click', function () {
    var h = H();
    if (h) h.termClose();
    var f = window.frameElement;
    if (f && f.parentNode) f.parentNode.removeChild(f);
  });

  /* ---------- boot ---------- */
  function start() {
    var h = H();
    if (!h) { showNotice('Nuxel host unavailable — this build has no terminal backend.'); return; }
    if (inHostWindow) { sendInput('\n'); return; }        // make the shell reprint its prompt
    h.termOpen();                                        // launcher tile: ask for the single window
  }
  setTimeout(start, 250);
  setTimeout(function () {
    if (!inHostWindow && !buffer) {
      screen.textContent = 'Opening the Nuxel terminal…\n';
    }
  }, 1200);

  // headless smoke-test hook
  window.nuxelTerminal = { history: hist, fontSize: function () { return fontSize; }, applyFont: applyFont };
})();
