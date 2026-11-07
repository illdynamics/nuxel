"""PWNAGE-85000 screen-off indicator-cache regression test."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "nuxel-bridge" / "src"))
import system_indicators as si  # noqa: E402


def test_screen_off_poll_does_not_rescan_every_request(monkeypatch):
    si._INDICATOR_CACHE["at"] = 0.0
    si._INDICATOR_CACHE["doc"] = None
    calls = []
    monkeypatch.setattr(si, "_panel_off", lambda: True)
    monkeypatch.setattr(si, "_get_indicators_uncached",
                        lambda: calls.append(1) or {"success": True, "value": 1})
    first = si.get_indicators()
    second = si.get_indicators()
    assert first == second
    assert len(calls) == 1, "1 Hz screen-off poll re-read every sysfs/proc endpoint"


def test_screen_on_uses_shorter_ttl(monkeypatch):
    assert si._INDICATOR_TTL_ON_S < si._INDICATOR_TTL_OFF_S
    assert si._INDICATOR_TTL_ON_S >= 1.0


def test_lockscreen_indicator_stops_polling_when_display_off():
    js = (ROOT / "pwa" / "nuxel-home" / "js" / "lockscreen-indicators.js").read_text()
    assert "next.display_off === true" in js
    assert "_stopTimer()" in js
    assert "_ensureTimer" in js
