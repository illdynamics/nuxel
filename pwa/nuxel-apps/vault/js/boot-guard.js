// Minimal startup guard: shows a visible error instead of a forever spinner.
(function () {
  'use strict';
  function show(message) {
    var box = document.getElementById('boot-error');
    if (!box) return;
    box.hidden = false;
    box.textContent = 'Vault failed to start: ' + String(message || 'unknown error');
  }
  window.addEventListener('error', function (event) {
    if (event && event.target && event.target.tagName === 'SCRIPT') {
      show('script failed to load: ' + (event.target.src || 'unknown'));
    } else if (event && event.message) {
      show(event.message);
    }
  }, true);
  window.addEventListener('unhandledrejection', function (event) {
    var reason = event && event.reason;
    show((reason && reason.message) || reason || 'promise rejected');
  });
}());
