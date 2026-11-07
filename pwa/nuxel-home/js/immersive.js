/* Nuxel immersive app chrome (v0.7.7-beta).
 *
 * EVERY foreground app is immersive by default: the triple buttons disappear
 * and the iframe expands over the status-bar band, so a fullscreen game or a
 * normal PWA both get the whole glass.  A short swipe up from the bottom edge
 * reveals Back/Home/Recents; a swipe down from the top edge reveals the status
 * bar.  The Home launcher and the lockscreen are deliberately excluded: Home
 * always keeps its chrome and the lockscreen never permits app navigation.
 *
 * This is the single global contract for all PWA apps.  Apps may still request
 * immersive explicitly (Nuxel Doom does), but they no longer have to: the
 * default is immersive for every ACTIVE/LAUNCHING session.
 *
 * The same-origin app iframe receives its own gesture listeners because touches
 * inside it do not bubble to the parent document.  The listeners are passive
 * and never synthesise input, so game touch controls keep working normally.
 */
(function (global) {
  'use strict';

  const BOTTOM_BAND = 34;
  const TOP_BAND = 48;
  const DISTANCE = 42;
  let navTimer = 0;
  let statusTimer = 0;
  let boundDocs = new WeakSet();

  function home() { return global.nuxel || null; }
  function activeState() {
    const state = document.body && document.body.dataset ? document.body.dataset.appState : '';
    return state === 'ACTIVE' || state === 'LAUNCHING';
  }
  function locked() {
    try { return !!(global.nuxel && typeof global.nuxel.isLocked === 'function' && global.nuxel.isLocked()); }
    catch (e) { return !!document.body.classList.contains('lockscreen-active'); }
  }
  function allowed() { return activeState() && !locked(); }

  function clearNavTimer() { if (navTimer) { clearTimeout(navTimer); navTimer = 0; } }
  function clearStatusTimer() { if (statusTimer) { clearTimeout(statusTimer); statusTimer = 0; } }

  function setNavVisible(visible, autoHideMs) {
    clearNavTimer();
    if (!allowed()) return;
    document.body.classList.add('app-nav-hidden');
    document.body.classList.toggle('app-nav-revealed', !!visible);
    const n = home();
    if (n && typeof n.setNavVisible === 'function') n.setNavVisible(!!visible);
    if (visible && autoHideMs !== 0) {
      navTimer = setTimeout(function () { setNavVisible(false, 0); }, autoHideMs || 4500);
    }
  }

  function setStatusVisible(visible, autoHideMs) {
    clearStatusTimer();
    const immersive = document.body.classList.contains('app-immersive');
    if (!immersive && visible) return; // normal apps already show the top bar
    document.body.classList.toggle('app-status-revealed', !!visible);
    if (visible && autoHideMs !== 0) {
      statusTimer = setTimeout(function () { setStatusVisible(false, 0); }, autoHideMs || 4000);
    }
  }

  function setImmersive(on) {
    on = !!on && allowed();
    document.body.classList.toggle('app-immersive', on);
    if (on) {
      document.body.classList.add('app-status-hidden');
      document.body.classList.remove('app-status-revealed');
      setNavVisible(false, 0);
    } else {
      document.body.classList.remove('app-status-hidden', 'app-status-revealed');
      clearStatusTimer();
    }
  }

  function resetChrome() {
    clearNavTimer(); clearStatusTimer();
    document.body.classList.remove('app-nav-hidden', 'app-nav-revealed');
    document.body.classList.remove('app-status-hidden', 'app-status-revealed');
    document.body.classList.remove('app-immersive');
  }

  function gestureDoc(doc) {
    if (!doc || boundDocs.has(doc)) return;
    if (!doc.documentElement) return;
    boundDocs.add(doc);
    let start = null;
    let touchStart = null;

    function begin(x, y, id) {
      if (!allowed()) return null;
      const h = doc.defaultView ? doc.defaultView.innerHeight : (doc.documentElement.clientHeight || 0);
      if (!h) return null;
      if (y >= h - BOTTOM_BAND) return { id: id, x: x, y: y, kind: 'nav' };
      if (y <= TOP_BAND) return { id: id, x: x, y: y, kind: 'status' };
      return null;
    }
    function finish(x, y, s) {
      if (!s) return;
      const dx = x - s.x, dy = y - s.y;
      if (Math.abs(dy) < DISTANCE || Math.abs(dy) < Math.abs(dx) * 1.1) return;
      if (s.kind === 'nav' && dy < 0) {
        // Toggle: first upward swipe reveals the triple buttons, the next
        // upward swipe on the revealed dock collapses them again (no timer).
        const revealed = document.body.classList.contains('app-nav-revealed');
        setNavVisible(!revealed, 0);
      } else if (s.kind === 'status') {
        // Swipe down from the top edge expands the top bar; swipe up collapses
        // it again. Swiping down again simply opens it normally.
        if (dy > 0) setStatusVisible(true, 0);
        else if (dy < 0) setStatusVisible(false, 0);
      }
    }

    doc.addEventListener('pointerdown', function (e) {
      if (e.isPrimary === false) return;
      start = begin(e.clientX, e.clientY, e.pointerId);
    }, { capture: true, passive: true });
    doc.addEventListener('pointerup', function (e) {
      if (!start || (e.pointerId !== undefined && start.id !== e.pointerId)) { start = null; return; }
      const s = start; start = null;
      finish(e.clientX, e.clientY, s);
    }, { capture: true, passive: true });
    doc.addEventListener('pointercancel', function () { start = null; }, { capture: true, passive: true });

    // WebKit can cancel the pointer stream when a gesture starts a scroll.  The
    // touch stream still delivers the end event, so mirror the bounded gesture.
    doc.addEventListener('touchstart', function (e) {
      const t = e.changedTouches && e.changedTouches[0];
      if (!t) return;
      touchStart = begin(t.clientX, t.clientY, t.identifier);
    }, { capture: true, passive: true });
    doc.addEventListener('touchend', function (e) {
      if (!touchStart) return;
      const t = Array.from(e.changedTouches || []).find(function (x) { return x.identifier === touchStart.id; });
      if (!t) { touchStart = null; return; }
      const s = touchStart; touchStart = null;
      finish(t.clientX, t.clientY, s);
    }, { capture: true, passive: true });
    doc.addEventListener('touchcancel', function () { touchStart = null; }, { capture: true, passive: true });
  }

  // The parent document owns chrome gestures while Home is showing and also
  // receives gestures from same-origin app iframes via attach().
  function attach(doc) { gestureDoc(doc || document); }

  document.addEventListener('app:lifecycle', function (event) {
    const state = event && event.detail && event.detail.state;
    if (state === 'ACTIVE' || state === 'LAUNCHING') {
      if (!allowed()) { resetChrome(); return; }
      // Global default: no triple buttons AND no top bar while any app owns
      // the foreground.  Both are recoverable with the edge gestures below.
      document.body.classList.add('app-nav-hidden', 'app-immersive', 'app-status-hidden');
      document.body.classList.remove('app-nav-revealed', 'app-status-revealed');
      const n = home();
      if (n && typeof n.setNavVisible === 'function') n.setNavVisible(false);
    } else {
      resetChrome();
      const n = home();
      if (n && typeof n.setNavVisible === 'function') n.setNavVisible(true);
    }
  });

  // App-requested immersive mode. Only the actual foreground iframe may ask.
  global.addEventListener('message', function (event) {
    if (event.origin !== global.location.origin) return;
    if (!event.data) return;
    const n = home();
    const frame = n && n.appSession && n.appSession.frame;
    if (!frame || event.source !== frame.contentWindow) return;
    if (event.data.type === 'nuxel:immersive') {
      setImmersive(!!event.data.active);
      return;
    }
    if (event.data.type === 'nuxel:nav-visible') {
      // A non-immersive app (Calendar) asks for the persistent triple buttons.
      // autoHideMs=0 means "keep them up" and never starts a timer.
      setNavVisible(!!event.data.active, 0);
      if (n && typeof n.setNavVisible === 'function') n.setNavVisible(!!event.data.active);
    }
  });

  // Tapping a revealed system button should not leave the strip up forever.
  document.addEventListener('pointerdown', function (e) {
    if (e.target && e.target.closest && e.target.closest('#system-navigation')) {
      clearNavTimer();
      navTimer = setTimeout(function () { setNavVisible(false, 0); }, 800);
    }
  }, { capture: true, passive: true });

  global.NuxelImmersive = {
    attach: attach,
    setImmersive: setImmersive,
    revealNav: function () { setNavVisible(true); },
    revealStatus: function () { setStatusVisible(true); },
    setNavVisible: setNavVisible,
    reset: resetChrome,
    get immersive() { return document.body.classList.contains('app-immersive'); },
  };
  attach(document);
})(window);
