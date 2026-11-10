/* Nuxel canonical top-bar state machine (PWNAGE-94000).
 *
 * DOM-free on purpose: the same four-level model is used by the launcher DOM
 * status bar and by the native compositor-boundary presentation adapter.
 *
 *   0 TOPBAR_HIDDEN    no bar (an immersive app keeps the whole glass)
 *   1 TOPBAR_STANDARD  standard Nuxel top bar only
 *   2 TOPBAR_EXPANDED  Quick Settings controls
 *   3 TOPBAR_EXTENDED  connection details + notification history
 *
 * Opening is progressive: advance() moves exactly one level per physical
 * gesture.  Closing is atomic: closeAll() goes from any level to 0.  There is
 * no "reverse walk" in either implementation.
 */
(function (global) {
  'use strict';

  const HIDDEN = 0, STANDARD = 1, EXPANDED = 2, EXTENDED = 3;
  const MAX = EXTENDED;

  class NuxelTopBarMachine {
    constructor(level, reason) {
      this.level = HIDDEN;
      this.sequence = 0;
      this.lastReason = 'init';
      this.transitions = [];
      this.set(level, reason || 'init');
      this.transitions.length = 0; // construction is not a user transition
    }

    static get LEVEL_HIDDEN() { return HIDDEN; }
    static get LEVEL_STANDARD() { return STANDARD; }
    static get LEVEL_EXPANDED() { return EXPANDED; }
    static get LEVEL_EXTENDED() { return EXTENDED; }
    static get MAX_LEVEL() { return MAX; }

    static clamp(level) {
      const n = Number(level);
      if (!Number.isFinite(n)) return HIDDEN;
      return Math.max(HIDDEN, Math.min(MAX, Math.round(n)));
    }

    set(level, reason) {
      const next = NuxelTopBarMachine.clamp(level);
      const changed = next !== this.level;
      if (changed) {
        this.transitions.push({ from: this.level, to: next, reason: reason || 'set' });
        if (this.transitions.length > 32) this.transitions.shift();
        this.sequence += 1;
        this.lastReason = reason || 'set';
      }
      this.level = next;
      return changed;
    }

    // Exactly one level per downward physical gesture.
    nextLevel() {
      return this.level >= MAX ? MAX : this.level + 1;
    }

    advance(reason) {
      if (this.level >= MAX) {
        this.lastReason = reason || 'advance-hold';
        return false;
      }
      return this.set(this.nextLevel(), reason || 'advance');
    }

    showStandard(reason) { return this.set(STANDARD, reason || 'standard'); }
    open(reason) { return this.set(EXPANDED, reason || 'open'); }
    expand(reason) { return this.set(this.level >= EXPANDED ? Math.min(MAX, this.level + 1) : EXPANDED, reason || 'expand'); }
    extend(reason) { return this.set(EXTENDED, reason || 'extend'); }

    // Atomic upward dismissal: any visible level -> 0 in ONE transition.
    closeAll(reason) {
      if (this.level === HIDDEN) {
        this.lastReason = reason || 'close-all-hold';
        return false;
      }
      return this.set(HIDDEN, reason || 'close-all');
    }

    get state() {
      return this.level === HIDDEN ? 'hidden'
        : this.level === STANDARD ? 'standard'
        : this.level === EXPANDED ? 'expanded' : 'extended';
    }
    get isOpen() { return this.level >= EXPANDED; }
    get expanded() { return this.level >= EXPANDED; }
    get extended() { return this.level >= EXTENDED; }
  }

  global.NuxelTopBarMachine = NuxelTopBarMachine;
  if (typeof module !== 'undefined' && module.exports) module.exports = NuxelTopBarMachine;
})(typeof window !== 'undefined' ? window : globalThis);
