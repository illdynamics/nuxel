/* Nuxel Edge Panel gesture recognizer (PWNAGE-103000).
 *
 * Integrated into the EXISTING gesture owner (js/gestures.js) as an
 * extension point; this module does not add a competing document-level
 * pointer or touch listener that could race Quick Settings, the drawer or app
 * scrolling.  Home calls NuxelEdgePanelGesture.pointerDown/Move/Up/Cancel from
 * gestures.js, which is the single recognizer that already arbitrates the
 * top-edge shade pull and the bottom-up drawer.
 *
 * A deliberate inward swipe:
 *   - must start within EDGE_BAND logical px of the left/right viewport edge;
 *   - must travel >= MIN_INWARD px horizontally toward the centre;
 *   - must be horizontally dominant (abs(dx) >= 1.5 * abs(dy) + slop);
 *   - must not start in the status bar, the nav dock or a scroll container;
 *   - opens exactly ONE panel per physical swipe (open latch + hold window).
 *
 * Pure state machine; DOM-free so the acceptance matrix is unit-testable.
 */
(function (global) {
  'use strict';

  var EDGE_BAND = 30;        // logical px; from the DT edge estimate (~120 px / DPR)
  var MIN_INWARD = 42;
  var DOMINANCE = 1.5;
  var SLOP = 10;
  var HOLD_MS = 450;         // post-open latch: residual motion cannot re-open
  var MAX_DURATION_MS = 1200;

  function createRecognizer(opts) {
    opts = opts || {};
    var edgeBand = opts.edgeBand || EDGE_BAND;
    var now = opts.now || function () { return Date.now(); };
    var st = null;
    var latchUntil = 0;
    var lastOutcome = 'idle';

    function viewport() {
      if (opts.viewport) return opts.viewport();
      if (typeof global.innerWidth === 'number' && typeof global.innerHeight === 'number') {
        return { w: global.innerWidth, h: global.innerHeight };
      }
      return { w: 360, h: 760 };
    }

    function excludedAt(x, y, target) {
      var vp = viewport();
      if (y <= (opts.topBand || 0) + 4) return 'top-edge';
      if (y >= vp.h - (opts.bottomBand || 0) - 2) return 'bottom-edge';
      if (target && target.closest &&
          target.closest('#status-bar,#system-navigation,#dock,.quick-settings,.drawer-list,' +
                         'input,textarea,select,[contenteditable=true]')) return 'owned-surface';
      return null;
    }

    function pointerDown(x, y, target, at) {
      st = null;
      lastOutcome = 'idle';
      if (now() < latchUntil) { lastOutcome = 'latched'; return false; }
      if (global.NuxelEdgeLighting && global.NuxelEdgeLighting.isPanelOpen && global.NuxelEdgeLighting.isPanelOpen()) {
        // An open panel is the surface: its own scroller/backdrop owns input.
        lastOutcome = 'panel-open';
        return false;
      }
      var vp = viewport();
      var side = null;
      if (x >= 0 && x <= edgeBand) side = 'left';
      else if (x <= vp.w && x >= vp.w - edgeBand) side = 'right';
      if (!side) { lastOutcome = 'not-edge'; return false; }
      var why = excludedAt(x, y, target);
      if (why) { lastOutcome = why; return false; }
      st = { x0: x, y0: y, side: side, t0: at || now() };
      return true;
    }

    function evaluate(arm, dx, dy) {
      if (!arm) return { committed: false, reason: 'no-arm' };
      if (arm.side === 'left' ? dx < 0 : dx > 0) return { committed: false, reason: 'wrong-direction' };
      var inward = arm.side === 'left' ? dx : -dx;
      if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > SLOP) return { committed: false, reason: 'vertical' };
      if (inward < MIN_INWARD) return { committed: false, reason: 'short' };
      if (Math.abs(dx) < DOMINANCE * Math.abs(dy) + SLOP) return { committed: false, reason: 'diagonal' };
      return { committed: true, reason: 'open', side: arm.side };
    }

    function pointerMove(x, y) {
      if (!st) return null;
      if (now() - st.t0 > MAX_DURATION_MS) { st = null; lastOutcome = 'too-slow'; return null; }
      var v = evaluate(st, x - st.x0, y - st.y0);
      if (!v.committed) return null;
      st = null;               // the gesture is consumed: never re-evaluate it
      var side = v.side;
      latchUntil = now() + HOLD_MS;
      lastOutcome = 'open:' + side;
      return { side: side };
    }

    function pointerUp(x, y) {
      if (!st) return null;
      var s = st;
      st = null;               // the arm is consumed by this release either way
      if (now() - s.t0 > MAX_DURATION_MS) { lastOutcome = 'too-slow'; return null; }
      var v = evaluate(s, x - s.x0, y - s.y0);
      if (!v.committed) { lastOutcome = v.reason; return null; }
      latchUntil = now() + HOLD_MS;
      lastOutcome = 'open:' + v.side;
      return { side: v.side };
    }

    function cancel(reason) {
      st = null;
      lastOutcome = 'cancel:' + (reason || 'cancel');
    }

    return {
      pointerDown: pointerDown,
      pointerMove: pointerMove,
      pointerUp: pointerUp,
      cancel: cancel,
      reset: function () { st = null; latchUntil = 0; lastOutcome = 'reset'; },
      outcome: function () { return lastOutcome; },
      _latchUntil: function () { return latchUntil; },
      armed: function () { return st ? st.side : null; },
      config: { edgeBand: EDGE_BAND, minInward: MIN_INWARD, dominance: DOMINANCE, holdMs: HOLD_MS }
    };
  }

  var api = {
    createRecognizer: createRecognizer,
    EDGE_BAND: EDGE_BAND,
    MIN_INWARD: MIN_INWARD,
    DOMINANCE: DOMINANCE
  };
  global.NuxelEdgePanelGesture = api;
})(typeof window !== 'undefined' ? window : this);
