#!/usr/bin/env python3
"""Regression: opening the drawer must not replay the opening swipe into its scroller."""
import pathlib, re
JS = pathlib.Path(__file__).resolve().parents[2] / 'pwa/nuxel-home/js/launcher.js'
G = pathlib.Path(__file__).resolve().parents[2] / 'pwa/nuxel-home/js/gestures.js'
src = JS.read_text()
assert '_drawerOpenGuardUntil = Date.now() + 250' in src
assert 'Date.now() < (this._drawerOpenGuardUntil || 0)' in src
assert 'this.drawerList.scrollTop = 0' in src
assert 'dx > 12 || dy > 12' in src
g = G.read_text()
assert 'window.launcher._drawerGestureUntil = performance.now() + 300' in g
print('PASS drawer open guard + 12px tap/scroll discrimination')
