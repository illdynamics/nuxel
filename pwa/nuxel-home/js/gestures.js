/* Single state-aware gesture owner for Home.  It deliberately ignores editable
 * and scrollable content, and yields to the launcher after a long-press drag. */
(function () {
  'use strict';
  const SLOP = 12, DISTANCE = 64;
  let start = null, consumed = false;
  const scrollable = target => target && target.closest && target.closest('input,textarea,select,[contenteditable=true],[data-gesture-scroll],.search-results,.recents-list,.quick-settings.expanded,.folder-sheet');
  function state() { return window.nuxel && window.nuxel.appSession && window.nuxel.appSession.state === 'ACTIVE' ? 'APP' : 'HOME'; }
  function down(e) {
    if (e.isPrimary === false || scrollable(e.target) || document.body.classList.contains('launcher-dragging')) return;
    start = { id: e.pointerId, x: e.clientX, y: e.clientY, half: e.clientY < innerHeight / 2, at: performance.now() }; consumed = false;
  }
  function up(e) {
    if (!start || start.id !== e.pointerId || consumed || document.body.classList.contains('launcher-dragging')) { start = null; return; }
    const dx = e.clientX - start.x, dy = e.clientY - start.y;
    if (Math.abs(dy) < DISTANCE || Math.abs(dy) < Math.abs(dx) + SLOP || state() !== 'HOME') { start = null; return; }
    consumed = true;
    if (start.half) {
      if (dy > 0 && window.qs) window.qs.open();
      else if (dy < 0 && window.qs) window.qs.collapseOrClose();
    } else if (dy < 0 && window.launcher) window.launcher.advanceDrawer();
    else if (dy > 0 && window.launcher) window.launcher.closeDrawer();
    start = null;
  }
  document.addEventListener('pointerdown', down, { capture: true, passive: true });
  document.addEventListener('pointerup', up, { capture: true, passive: true });
  document.addEventListener('pointercancel', () => { start = null; consumed = false; }, { capture: true });
})();
