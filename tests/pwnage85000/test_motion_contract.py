"""PWNAGE-85000 motion-language contract.

The shell must stay crisp and cheap on the software compositor: short
transform/opacity feedback, no layout animation, no blur, and a real
reduced-motion/off path shared by the launcher, Settings and PWAs.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "pwa" / "nuxel-common"
HOME = ROOT / "pwa" / "nuxel-home"
SETTINGS = ROOT / "pwa" / "nuxel-apps" / "settings"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tokens(css: str) -> dict:
    out = {}
    for name, value in re.findall(r"--nx-motion-([a-z]+):\s*([0-9]+)ms", css):
        out[name] = int(value)
    return out


def test_motion_tokens_exist_and_are_bounded():
    tokens = _tokens(_read(COMMON / "theme.css"))
    for name, upper in {
        "press": 110,
        "fast": 150,
        "standard": 190,
        "navigation": 220,
        "emphasis": 240,
    }.items():
        assert name in tokens, f"missing --nx-motion-{name}"
        assert 0 < tokens[name] <= upper, f"--nx-motion-{name}={tokens[name]}ms"
    assert tokens["press"] >= 70


def test_off_and_reduced_modes_exist():
    css = _read(COMMON / "theme.css")
    assert ':root[data-motion="reduced"]' in css
    assert ':root[data-motion="off"]' in css
    assert "prefers-reduced-motion: reduce" in css
    assert "--nx-motion-press: 0ms" in css
    # Reduced must still keep essential feedback, not remove state changes.
    launcher = _read(HOME / "css" / "launcher.css")
    assert ':root[data-motion="reduced"]' in launcher
    assert ':root[data-motion="off"]' in launcher


def test_core_panel_transition_uses_tokens_not_raw_160_220ms():
    style = _read(HOME / "css" / "style.css")
    qs = re.search(r"#quick-settings:not\(\.hidden\)\s*\{[^}]*\}", style)
    assert qs, "Quick Settings entry rule missing"
    assert "--nx-motion-standard" in qs.group(0)
    status = re.search(r"#status-bar\s*\{[^}]*\}", style)
    assert status and "--nx-motion-fast" in status.group(0)


def test_no_layout_animation_in_core_motion_rules():
    for rel in ("css/style.css", "css/launcher.css"):
        css = _read(HOME / rel)
        for block in re.findall(r"(?:#status-bar|\.system-navigation|#quick-settings|\.app-item|\.app-grid)[^{]*\{[^}]*\}", css):
            if "transition" not in block and "animation" not in block:
                continue
            assert not re.search(r"(?:transition|animation)[^;}]*(?:width|height|top|left|margin|padding|border-width)", block), block


def test_no_backdrop_blur_in_new_motion_surfaces():
    for path in (COMMON / "theme.css", HOME / "css" / "style.css", HOME / "css" / "launcher.css"):
        text = _read(path)
        assert "backdrop-filter" not in text
        assert "-webkit-backdrop-filter" not in text


def test_press_feedback_is_restrained():
    css = _read(HOME / "css" / "launcher.css")
    m = re.search(r"\.app-item:active\s*\{[^}]*transform:\s*scale\(([0-9.]+)\)", css)
    assert m, "app-item press feedback missing"
    scale = float(m.group(1))
    assert 0.90 <= scale <= 0.97, scale


def test_motion_preference_is_persisted_and_shared():
    js = _read(COMMON / "theme.js")
    assert "nuxel.motion" in js
    assert "applyMotion" in js
    assert "prefers-reduced-motion" in _read(COMMON / "theme.css")
    page = _read(SETTINGS / "index.html")
    assert 'id="motion-mode"' in page
    assert 'value="reduced"' in page and 'value="off"' in page
    settings_js = _read(SETTINGS / "appearance-settings.js")
    assert "motionApply" in settings_js
    assert "nuxel.motion" in settings_js
