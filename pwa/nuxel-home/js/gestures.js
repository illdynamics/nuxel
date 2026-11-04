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
    // The status bar owns the top-edge shade pull.  It marks this flag when it
    // fires so the release fallback here cannot apply the same swipe twice
    // (which turned "open compact" into "open expanded").
    window.__nuxelQsGestureConsumed = false;
  }
  function finish(x, y, topEdge) {
    const dx = x, dy = y;
    if (Math.abs(dy) < DISTANCE || Math.abs(dy) < Math.abs(dx) * 1.15 + SLOP || state() !== 'HOME') return false;
    consumed = true;
    if (dy > 0) {
      // A pull-down only becomes Quick Settings when it began in the top-edge
      // band.  A drawer scroll may start anywhere in the list and is never a
      // shade gesture, even when the scroll direction is downward.
      if (topEdge && !(window.launcher && window.launcher.drawerOpen) && window.qs &&
          !window.__nuxelQsGestureConsumed) window.qs.open();
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
    return true;
  }
  function up(e) {
    if (!start || start.id !== e.pointerId || consumed || document.body.classList.contains('launcher-dragging')) { start = null; return; }
    finish(e.clientX - start.x, e.clientY - start.y, start.topEdge);
    start = null;
  }
  document.addEventListener('pointerdown', down, { capture: true, passive: true });
  document.addEventListener('pointerup', up, { capture: true, passive: true });
  document.addEventListener('pointercancel', () => { start = null; consumed = false; }, { capture: true });

  /* PWNAGE-62000: WebKit cancels the pointer stream as soon as a vertical
     touch becomes a scroll.  The old pointer-only drawer gesture therefore
     never saw pointerup on the phone and the Applications drawer stopped
     opening.  Touch events still deliver touchend for a scroll-origin swipe,
     so mirror the same bounded gesture here.  This path is passive and does
     not call preventDefault, preserving native kinetic scrolling. */
  let touchStart = null;
  function touchDown(e) {
    touchStart = null;
    consumed = false;
    // NOTE: an app tile is a valid origin for the upward drawer swipe.  The
    // distance/angle gate in finish() still distinguishes it from a tap, so
    // rejecting .app-item here only broke the common "swipe up from an icon"
    // path (WebKit cancels the pointer stream as soon as the pan starts).
    const t = e.changedTouches && e.changedTouches[0];
    if (!t || state() !== 'HOME') return;
    if (scrollable(e.target) || document.body.classList.contains('launcher-dragging') ||
        e.target.closest('#system-navigation,#dock,#home-settings,.pwa-frame,#status-bar')) return;
    touchStart = { id: t.identifier, x: t.clientX, y: t.clientY,
                   topEdge: t.clientY <= TOP_EDGE };
    window.__nuxelQsGestureConsumed = false;
  }
  function touchUp(e) {
    if (!touchStart) return;
    const t = Array.from(e.changedTouches || []).find(x => x.identifier === touchStart.id);
    if (!t) { touchStart = null; return; }
    const startAt = touchStart;
    touchStart = null;
    if (consumed || document.body.classList.contains('launcher-dragging')) return;
    finish(t.clientX - startAt.x, t.clientY - startAt.y, startAt.topEdge);
  }
  document.addEventListener('touchstart', touchDown, { capture: true, passive: true });
  document.addEventListener('touchend', touchUp, { capture: true, passive: true });
  document.addEventListener('touchcancel', () => { touchStart = null; consumed = false; }, { capture: true, passive: true });
})();
