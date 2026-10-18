#!/usr/bin/env python3
"""Static contract test for the real Terminal OSK interaction paths."""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[4]
src = (root / "pwa/nuxel-apps/terminal/terminal.js").read_text()
css = (root / "pwa/nuxel-apps/terminal/terminal.css").read_text()
failures = []

def check(name, condition):
    print(("PASS " if condition else "FAIL ") + name)
    if not condition:
        failures.append(name)

check("Shift has an explicit state and one-shot reset",
      "shiftArmed = !shiftArmed" in src and "shiftArmed = false; renderKeys()" in src)
check("symbols switch has ABC return path",
      "symbolsArmed = !symbolsArmed" in src and "symbolsArmed ? 'ABC' : '?123'" in src)
check("Backspace updates the tracked command line",
      src.count("lineBuffer = lineBuffer.slice(0, -1)") >= 2)
check("history is handled before the generic Ctrl/key byte path",
      src.index("data === 'HISTUP'") < src.index("if (ctrlArmed)"))
check("history restores the tracked line and replaces the PTY line",
      "lineBuffer = cmd" in src and "sendInput('\\u0015')" in src)
check("keyboard has a dismiss control and a tap-to-restore path",
      "key('⌄', 'HIDE'" in src and "osk.classList.add('hidden')" in src and
      "osk.classList.remove('hidden')" in src and ".osk.hidden" in css)
check("Enter, Space and printable characters still reach the PTY",
      "key('SPACE', ' '" in src and "key('⏎', '\\r'" in src and "sendInput(data)" in src)
check("physical Backspace keeps history tracking correct",
      "ev.key === 'Backspace'" in src)

print("TERMINAL-KEYBOARD: " + ("ALL PASS" if not failures else "FAILURES PRESENT"))
sys.exit(1 if failures else 0)
