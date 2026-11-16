#!/usr/bin/env python3
"""Edge Panel recognizer acceptance matrix (portrait + landscape, arbitration).

Every case is a pure state-machine evaluation; physical finger ergonomics on the
curved panel remain NEEDS_OWNER_PHYSICAL_TEST and are not claimed here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, node_json, finish, ROOT  # noqa: E402

res = node_json(r"""
const G = global.NuxelEdgePanelGesture;
let clock = 1000;
const mk = (w, h, top, bottom) => G.createRecognizer({
  viewport: () => ({ w, h }), topBand: top, bottomBand: bottom, now: () => clock
});
const out = { config: G.createRecognizer({}).config, cases: {} };
function run(name, rec, w, h, seq, advance) {
  out.cases[name] = { opened: null, outcome: 'pending' };
  const r = [];
  clock += 5000;   // independent physical gesture: past the post-open latch
  let opened = null;
  for (const ev of seq) {
    clock += (advance == null ? 40 : advance);
    if (ev.t === 'down') {
      // Frames cannot travel backwards: a latched gesture waits out the hold.
      if (clock < rec._latchUntil()) clock = rec._latchUntil() + 1;
      const target = { closest: (sel) => ev.owned ? {} : null };
      const ok = rec.pointerDown(ev.x, ev.y, target, clock);
      if (!ok) { r.push(['down:refused', rec.outcome()]); return; }
      r.push(['down', ok]);
    } else if (ev.t === 'move') {
      const o = rec.pointerMove(ev.x, ev.y); if (o) opened = o; r.push(['move', o]);
    } else if (ev.t === 'up') {
      const o = rec.pointerUp(ev.x, ev.y); if (o) opened = o; r.push(['up', o]);
    } else if (ev.t === 'cancel') {
      rec.cancel('touchcancel'); r.push(['cancel', null]);
    }
  }
  out.cases[name] = { opened: opened, outcome: rec.outcome(), steps: r };
}
// Portrait 360x760: left inward swipe starting at x=8, travelling 60 px.
run('left-open', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 8, y: 400 }, { t: 'move', x: 40, y: 402 }, { t: 'move', x: 76, y: 404 }, { t: 'up', x: 76, y: 404 }]);
run('right-open', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 352, y: 400 }, { t: 'move', x: 320, y: 401 }, { t: 'move', x: 286, y: 403 }, { t: 'up', x: 286, y: 403 }]);
run('touchend-only-open', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 6, y: 380 }, { t: 'up', x: 70, y: 386 }]);
run('vertical-scroll-at-edge', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 6, y: 500 }, { t: 'move', x: 12, y: 440 }, { t: 'up', x: 12, y: 440 }]);
run('short-side-tap', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 8, y: 400 }, { t: 'up', x: 30, y: 402 }]);
run('diagonal', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 8, y: 300 }, { t: 'up', x: 60, y: 360 }]);
run('outward', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 20, y: 400 }, { t: 'up', x: -30, y: 400 }]);
run('top-edge-shade', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 8, y: 10 }, { t: 'up', x: 100, y: 10 }]);
run('bottom-dock', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 8, y: 745 }, { t: 'up', x: 100, y: 745 }]);
run('owned-surface', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 8, y: 400, owned: true }, { t: 'up', x: 80, y: 400 }]);
run('cancel-resets', mk(360, 760, 28, 24), 360, 760, [
  { t: 'down', x: 8, y: 400 }, { t: 'cancel' }, { t: 'up', x: 90, y: 400 }]);
run('landscape-left', mk(760, 360, 24, 20), 760, 360, [
  { t: 'down', x: 10, y: 200 }, { t: 'move', x: 40, y: 201 }, { t: 'move', x: 74, y: 203 }, { t: 'up', x: 74, y: 203 }]);
run('landscape-right', mk(760, 360, 24, 20), 760, 360, [
  { t: 'down', x: 752, y: 200 }, { t: 'up', x: 690, y: 204 }]);
run('stale-360-in-landscape', mk(760, 360, 24, 20), 760, 360, [
  { t: 'down', x: 600, y: 180 }, { t: 'up', x: 660, y: 182 }]);
// One physical swipe produces exactly one open, even with a residual secondup.
{
  const rec = mk(360, 760, 28, 24);
  rec.pointerDown(8, 400, null, clock);
  const first = rec.pointerMove(80, 403);
  const second = rec.pointerMove(120, 403);
  const up = rec.pointerUp(120, 403);
  out.cases['single-open'] = { first: first, second: second, up: up, outcome: rec.outcome() };
}
// 20 open/close cycles per side (recognizer state only).
{
  const rec = mk(360, 760, 28, 24);
  let opens = 0, sideWrong = 0;
  for (let i = 0; i < 20; i++) {
    clock += 600;
    rec.pointerDown(6, 300, null, clock); const a = rec.pointerMove(70, 302); if (a && a.side === 'left') opens++;
    clock += 600;
    rec.pointerDown(354, 300, null, clock); const b = rec.pointerMove(290, 302); if (b && b.side === 'right') opens++; else sideWrong++;
    clock += 600;
  }
  out.cases['twenty-cycles'] = { opens: opens, sideWrong: sideWrong, armed: rec.armed() };
}
console.log(JSON.stringify(out));
""")

c = res['cases']
check('recognizer band config is 30 px / 42 px inward / 1.5 dominance',
      res['config']['edgeBand'] == 30 and res['config']['minInward'] == 42 and res['config']['dominance'] == 1.5,
      res['config'])
for name, side in (('left-open', 'left'), ('right-open', 'right'),
                   ('landscape-left', 'left'), ('landscape-right', 'right')):
    check('%s opens exactly once on the %s side' % (name, side),
          c[name]['opened'] and c[name]['opened']['side'] == side, c[name]['outcome'])
check('a swipe released without pointermove still opens (touch path)',
      c['touchend-only-open']['opened'] and c['touchend-only-open']['opened']['side'] == 'left')
check('vertical scroll starting at the edge does not open', c['vertical-scroll-at-edge']['opened'] is None,
      c['vertical-scroll-at-edge']['outcome'])
check('short side touch does not open', c['short-side-tap']['opened'] is None)
check('diagonal swipe does not open', c['diagonal']['opened'] is None, c['diagonal']['outcome'])
check('outward swipe does not open', c['outward']['opened'] is None)
check('top-edge Quick Settings pull is not stolen', c['top-edge-shade']['opened'] is None)
check('bottom dock area is not stolen', c['bottom-dock']['opened'] is None)
check('owned surfaces (status/nav/dock/inputs) are not stolen', c['owned-surface']['opened'] is None)
check('pointercancel/touchcancel resets state without opening',
      c['cancel-resets']['opened'] is None and c['cancel-resets']['outcome'].startswith('cancel'))
check('stale 360px bounds never open in landscape', c['stale-360-in-landscape']['opened'] is None)
check('one physical swipe = one open event',
      c['single-open']['first'] and c['single-open']['first']['side'] == 'left' and
      c['single-open']['second'] is None and c['single-open']['up'] is None)
check('20 open cycles per side, no stuck armed state',
      c['twenty-cycles']['opens'] == 40 and c['twenty-cycles']['sideWrong'] == 0 and
      c['twenty-cycles']['armed'] is None, c['twenty-cycles'])

# gestures.js must remain the single owner and wire the recognizer.
g = (ROOT / 'pwa/nuxel-home/js/gestures.js').read_text()
check('gestures.js integrates the Edge Panel recognizer', 'NuxelEdgePanelGesture' in g)
check('gestures.js has no second document touchstart owner outside the existing one',
      g.count("addEventListener('pointerdown'") == 1 and g.count("addEventListener('touchstart'") == 1)
check('gestures.js cancels recognizer on pointercancel/touchcancel/blur/orientation',
      all(k in g for k in ("'pointercancel'", "'touchcancel'", "'blur'", "'orientationchange'")))
check('gestures.js keeps the existing drawer/Quick Settings rules', 'openDrawer' in g and 'qs.open()' in g)
finish('PWNAGE-103000 Edge Panel recognizer')
