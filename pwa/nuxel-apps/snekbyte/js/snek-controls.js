/* Shared, DOM-free input and fixed-step clock. No timers or dependencies. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SnekControls = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  function equal(a, b) { return a[0] === b[0] && a[1] === b[1]; }
  function cardinal(d) { return Array.isArray(d) && d.length === 2 &&
    Number.isInteger(d[0]) && Number.isInteger(d[1]) && Math.abs(d[0]) + Math.abs(d[1]) === 1; }

  function createQueue() {
    var pending = [];
    function expire(now) {
      // A projected turn depends on its predecessors. Expire the whole chain,
      // never just its first turn. Two slowest-rate turns normally take <=400ms.
      if (pending.length && now - pending[0].at > 500) pending.length = 0;
    }
    return {
      offer: function (dir, heading, now, trace) {
        expire(now);
        var projected = pending.length ? pending[pending.length - 1].dir : heading;
        if (!cardinal(dir)) return 'invalid';
        if (equal(dir, projected)) return 'duplicate';
        if (dir[0] === -projected[0] && dir[1] === -projected[1]) return 'reverse';
        if (pending.length === 2) return 'full'; // preserve accepted FIFO, reject newest
        pending.push({ dir: dir.slice(), at: now, trace: trace });
        return 'accepted';
      },
      take: function (now) { expire(now); return pending.shift() || null; },
      clear: function () { pending.length = 0; },
      size: function () { return pending.length; }
    };
  }

  function createSwipe(accept) {
    var id = null, x = 0, y = 0;
    return {
      start: function (pointer, px, py) {
        if (id !== null) return false;
        id = pointer; x = px; y = py; return true;
      },
      move: function (pointer, px, py, event) {
        if (id !== pointer) return false;
        var dx = px - x, dy = py - y, ax = Math.abs(dx), ay = Math.abs(dy);
        if (Math.max(ax, ay) < 14 || Math.max(ax, ay) < Math.min(ax, ay) * 1.25) return false;
        var dir = ax > ay ? [dx > 0 ? 1 : -1, 0] : [0, dy > 0 ? 1 : -1];
        if (!accept(dir, event)) return false;
        x = px; y = py; return true;
      },
      end: function (pointer) { if (id === pointer) id = null; },
      clear: function () { id = null; }
    };
  }

  function createClock(rate) {
    var period = 1000 / rate, last = null, acc = 0;
    return {
      reset: function (now) { last = now === undefined ? null : now; acc = 0; },
      setRate: function (next, now) {
        if (!Number.isFinite(next) || next <= 0) throw new Error('Invalid tick rate');
        period = 1000 / next; this.reset(now);
      },
      advance: function (now, step) {
        var elapsed = last === null ? 0 : Math.max(0, now - last);
        last = now;
        acc += Math.min(elapsed, 250);
        var steps = 0, dropped = Math.max(0, elapsed - 250);
        while (acc + 1e-7 >= period && steps < 3) {
          acc = Math.max(0, acc - period); steps++;
          if (step() === false) { acc = 0; break; }
        }
        if (acc >= period) { dropped += acc - (acc % period); acc %= period; }
        return { steps: steps, droppedMs: dropped };
      },
      period: function () { return period; }
    };
  }
  return { createQueue: createQueue, createSwipe: createSwipe, createClock: createClock };
}));
