/* Single state-aware gesture owner for Home.
 *
 * PWNAGE-50000: Quick Settings is opened ONLY by a downward pull that starts
 * in the small top-edge band (the DOM status bar also owns that gesture).
 * The old half-screen rule opened the shade while the owner was scrolling the
 * Applications drawer, and an upward swipe while the drawer was open launched
 * Settings.  Both were removed: scrolling inside the drawer now belongs to the
 * scroll container, never to a navigation gesture. */
(function () {
  'use strict';
  const SLOP = 14, DISTANCE = 56, TOP_EDGE = 40;
  let start = null, consumed = false;
  const scrollable = target => target && target.closest && target.closest('input,textarea,select,[contenteditable=true],[data-gesture-scroll],.search-results,.recents-list,.quick-settings,.folder-sheet,#drawer-list');
  function state() { return window.nuxel && window.nuxel.appSession && window.nuxel.appSession.state === 'ACTIVE' ? 'APP' : 'HOME'; }
  function down(e) {
    if (e.isPrimary === false || scrollable(e.target) || document.body.classList.contains('launcher-dragging') || e.target.closest('#system-navigation,#dock,#home-settings,.pwa-frame,#status-bar')) return;
    start = { id: e.pointerId, x: e.clientX, y: e.clientY, topEdge: e.clientY <= TOP_EDGE, at: performance.now() };
    consumed = false;
  }
  function up(e) {
    if (!start || start.id !== e.pointerId || consumed || document.body.classList.contains('launcher-dragging')) { start = null; return; }
    const dx = e.clientX - start.x, dy = e.clientY - start.y;
    if (Math.abs(dy) < DISTANCE || Math.abs(dy) < Math.abs(dx) * 1.15 + SLOP || state() !== 'HOME') { start = null; return; }
    consumed = true;
    if (dy > 0) {
      // A pull-down only becomes Quick Settings when it began in the top-edge
      // band.  A drawer scroll may start anywhere in the list and is never a
      // shade gesture, even when the scroll direction is downward.
      if (start.topEdge && !(window.launcher && window.launcher.drawerOpen) && window.qs) window.qs.open();
    } else if (!window.launcher || !window.launcher.drawerOpen) {
      // Upward from empty Home opens the Applications drawer.  Never navigate
      // away from an already-open drawer; that swipe is a scroll.
      if (window.launcher) {
        // The opening swipe is consumed by Home.  The drawer's own guard
        // absorbs residual kinetic deltas for the next 250 ms.
        window.launcher._drawerGestureUntil = performance.now() + 300;
        window.launcher.openDrawer();
      }
    }
    start = null;
  }
  document.addEventListener('pointerdown', down, { capture: true, passive: true });
  document.addEventListener('pointerup', up, { capture: true, passive: true });
  document.addEventListener('pointercancel', () => { start = null; consumed = false; }, { capture: true });
})();
