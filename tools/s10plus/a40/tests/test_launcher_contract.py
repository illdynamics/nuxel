#!/usr/bin/env python3
"""Focused A40 regression gate for launcher ownership contracts.

These assertions intentionally inspect the shipped sources that are installed on
the handset.  Browser/device interaction remains a separate live acceptance
step; this gate prevents the previously observed duplicate/DOM-owned paths from
returning unnoticed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

def source(relative):
    return (ROOT / relative).read_text(encoding="utf-8")

def require(text, needle, label):
    if needle not in text:
        raise AssertionError(label + ": missing " + needle)
    print("PASS", label)

launcher = source("pwa/nuxel-home/js/launcher.js")
require(launcher, "this.dragState = 'IDLE'", "drag lifecycle has an explicit idle state")
require(launcher, "layoutBefore:", "drawer drag snapshots the model before unmount")
require(launcher, "hiddenBefore:", "drawer drag snapshots hidden shortcuts")
require(launcher, "pointerEvents = 'none'", "drag ghost cannot intercept Home hit testing")
require(launcher, "_endDrag(null, true)", "pointer cancellation takes the cancel path")
require(launcher, "if (!cancelled) this._saveLayout();", "cancelled drawer drags do not persist")

recents = source("pwa/nuxel-home/js/recents.js")
require(recents, "RECENTS state=", "Recents transitions are instrumented")
require(recents, "toggle(reason)", "Recents has one reasoned toggle transition")
require(recents, "close('select-app')", "Recents selection closes deliberately")

nav = source("pwa/nuxel-home/js/navigation.js")
require(nav, "this.holdMs = 650", "Back long press has a bounded threshold")
require(nav, "global.nuxel.terminateForeground()", "Back long press owns foreground close")

keyboard = source("pwa/nuxel-home/js/touch-keyboard.js")
require(keyboard, "el.focus({ preventScroll: true })", "keyboard restores target focus before editing")
require(keyboard, "this.panel.hidden = true", "Hide Keyboard changes OSK visibility")
require(keyboard, "haptics-tap", "keyboard requests one haptic path")

calendar_css = source("pwa/nuxel-apps/calendar/css/calendar.css")
require(calendar_css, "caret-color: #fff", "Calendar editable fields expose a real caret")
