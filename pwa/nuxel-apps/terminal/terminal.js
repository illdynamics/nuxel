// Nuxel Terminal (A32)
//
// A REAL terminal: the bytes come from /bin/sh running on a PTY owned by
// nuxel-pwa-host (forkpty), the input goes back to that same PTY.  There is no
// emulated shell, no canned prompt and no fake output anywhere in this file.
//
// Two launch paths, both ending in the same one-instance rule:
//   * the hardware Bixby button -> /run/nuxel-pwa-host.cmd "open-terminal"
//   * the launcher's Terminal tile -> this page inside .pwa-frame -> term.open
// The host opens ONE fullscreen terminal window and focuses it on repeat presses.
(function () {
  'use strict';

  var screen = document.getElementById('screen');
  var notice = document.getElementById('notice');
  var title  = document.getElementById('title');
  var buffer = '';
  var inHostWindow = false;

  function H() {
    if (window.NuxelHost && window.NuxelHost.available) return window.NuxelHost;
    try { if (window.parent && window.parent.NuxelHost) return window.parent.NuxelHost; } catch (e) {}
    return null;
  }
  function sendInput(data) {
    var h = H();
    if (!h) { showNotice('No Nuxel host: the terminal needs the launcher host process.'); return; }
    h.termInput(data);
  }
  function showNotice(msg) { notice.textContent = msg; notice.classList.remove('hidden'); }

  // The host pushes PTY output into whichever view owns the terminal window.
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

  // ---------- on-screen keyboard (there is no system keyboard without a compositor) ----------
  var LETTERS = [
    ['1','2','3','4','5','6','7','8','9','0'],
    ['q','w','e','r','t','y','u','i','o','p'],
    ['a','s','d','f','g','h','j','k','l','-'],
    ['z','x','c','v','b','n','m','.','/','_']
  ];
  var osk = document.getElementById('osk');
  function key(label, data, cls) {
    var b = document.createElement('button');
    b.textContent = label;
    if (cls) b.className = cls;
    b.addEventListener('click', function () {
      if (data === 'CTRL') { ctrlArmed = !ctrlArmed; b.classList.toggle('active', ctrlArmed); return; }
      if (ctrlArmed) { sendInput(String.fromCharCode(data.toUpperCase().charCodeAt(0) - 64)); ctrlArmed = false; refreshMods(); return; }
      sendInput(data);
    });
    return b;
  }
  var ctrlArmed = false;
  function refreshMods(){ document.querySelectorAll('.osk button.mod').forEach(function(b){ if(b.textContent!=='CTRL') b.classList.remove('active'); }); }
  LETTERS.forEach(function (row, i) {
    var r = document.createElement('div'); r.className = 'row';
    if (i === 3) r.appendChild(key('⇧', '', 'mod'));
    row.forEach(function (k) { r.appendChild(key(k, k)); });
    r.appendChild(key('⌫', '\u007f', 'mod'));
    osk.appendChild(r);
  });
  var last = document.createElement('div'); last.className = 'row';
  last.appendChild(key('CTRL', 'CTRL', 'mod'));
  last.appendChild(key('TAB', '\t', 'mod'));
  last.appendChild(key('SPACE', ' ', 'wide'));
  last.appendChild(key('⏎', '\r', 'wide'));
  last.appendChild(key('^C', '\u0003', 'mod'));
  osk.appendChild(last);

  document.getElementById('clear').addEventListener('click', function () { buffer = ''; screen.textContent = ''; });
  document.getElementById('close').addEventListener('click', function () {
    var h = H();
    if (h) h.termClose();
    var f = window.frameElement;
    if (f && f.parentNode) f.parentNode.removeChild(f);
  });

  // ---------- boot ----------
  function start() {
    var h = H();
    if (!h) { showNotice('Nuxel host unavailable — this build has no terminal backend.'); return; }
    if (inHostWindow) { sendInput('\n'); return; }        // make the shell reprint its prompt
    // Opened from the launcher tile: ask the host for the single terminal window.
    h.termOpen();
  }
  setTimeout(start, 250);
  setTimeout(function () {
    if (!inHostWindow && !buffer) {
      screen.textContent = 'Opening the Nuxel terminal…\n';
    }
  }, 1200);
})();
