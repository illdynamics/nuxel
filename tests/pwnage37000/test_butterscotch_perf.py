"""PWNAGE-37000 Butterscotch performance-profile regression checks.

These are repo-side, deterministic assertions for the lightweight arcade
profile. They complement the physical-device measurements by pinning the exact
source invariants that the optimization pass establishes:

  * no backdrop blur / blur filters anywhere in the home UI (CSS or inline JS)
  * no persistent compositing hints on always-present hidden panels
  * DOM navigation artwork is small, locally referenced, crisp pixel art
  * Quick Settings does not duplicate Bluetooth/Location bridge calls on open
  * panel/glow shadows stay crisp (no large software-rasterised blurs)
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "pwa" / "nuxel-home"

CSS_FILES = [
    "css/style.css",
    "css/launcher.css",
    "css/search.css",
    "css/status-bar.css",
    "css/home-settings.css",
    "css/widgets.css",
    "css/lockscreen.css",
]
JS_FILES = [
    "js/app.js",
    "js/apps.js",
    "js/bridge.js",
    "js/host-bridge.js",
    "js/home-settings.js",
    "js/launcher.js",
    "js/layout-model.js",
    "js/lockscreen-indicators.js",
    "js/lockscreen.js",
    "js/navigation.js",
    "js/osd.js",
    "js/qs.js",
    "js/recents.js",
    "js/safe-zones.js",
    "js/scroll-indicators.js",
    "js/search.js",
    "js/settings-store.js",
    "js/status-bar.js",
    "js/system-monitor.js",
    "js/touch-keyboard.js",
    "js/widgets.js",
]


def _read(rel: str) -> str:
    return (HOME / rel).read_text(encoding="utf-8")


def _png_dim(rel: str):
    data = (HOME / rel).read_bytes()[:26]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


@pytest.mark.parametrize("rel", CSS_FILES)
def test_css_has_no_backdrop_blur(rel):
    assert "backdrop-filter" not in _read(rel)
    assert "-webkit-backdrop-filter" not in _read(rel)


@pytest.mark.parametrize("rel", JS_FILES)
def test_js_has_no_backdrop_blur(rel):
    assert "backdrop-filter" not in _read(rel)


@pytest.mark.parametrize("rel", CSS_FILES + JS_FILES)
def test_no_blur_filters_anywhere(rel):
    text = _read(rel)
    # Only CSS filter functions count; `.blur()` (DOM focus removal) is not a
    # visual filter and appears legitimately throughout the input code.
    assert not re.search(r"(?:backdrop-)?filter\s*:[^;{}]*blur\(", text), \
        f"{rel} still contains a blur filter"


def test_no_persistent_will_change_on_hidden_panels():
    style = _read("css/style.css")
    # The Quick Settings panel is hidden until opened; it must not hold a layer.
    qs_rule = re.search(r"#quick-settings\s*\{[^}]*\}", style)
    assert qs_rule is None or "will-change" not in qs_rule.group(0)
    status = _read("css/status-bar.css")
    recents_rule = re.search(r"\.recents-view\s*\{[^}]*\}", status)
    assert recents_rule is None or "will-change" not in recents_rule.group(0)


def test_dom_nav_art_is_small_and_local():
    index = _read("index.html")
    for name in ("button-left", "button-middle", "button-right"):
        m = re.search(
            r'<button[^>]*data-nav[^>]*>\s*<img\s+src="([^"]*' + name + r'\.png[^"]*)"',
            index)
        assert m, f"nav button {name} img not found"
        src = m.group(1).split("?")[0]
        assert src.startswith("assets/"), f"{name} must reference the local small asset"
        rel = "assets/" + src.split("/")[-1]
        dim = _png_dim(rel)
        assert dim is not None, f"{rel} is missing"
        w, h = dim
        assert w <= 128 and h <= 128, f"{rel} is oversized ({w}x{h})"
        assert (HOME / rel).stat().st_size < 64_000, f"{rel} is too large"


def test_quick_settings_open_does_not_duplicate_provider_calls():
    qs = _read("js/qs.js")
    render = re.search(r"_render\(\)\s*\{[^}]*\}", qs)
    assert render, "qs._render body not found"
    body = render.group(0)
    assert body.count("_syncBluetooth()") <= 1
    assert body.count("_syncLocation()") <= 1


def test_panel_and_glow_shadows_stay_crisp():
    # Blur radii (the third value in `x y r` shadows) must stay small. A
    # `0 0 0 8px` ring is a spread, not a blur; skip x-offset 0/y-offset 0.
    for rel in CSS_FILES + JS_FILES:
        text = _read(rel)
        for decl in re.findall(r"box-shadow:\s*([^;{}]+)", text):
            parts = [p.strip() for p in decl.split(",")]
            for part in parts:
                nums = re.findall(r"\b(\d+)px\b", part)
                if len(nums) >= 3:
                    x, y, blur = int(nums[0]), int(nums[1]), int(nums[2])
                    if x == 0 and y == 0:
                        continue
                    assert blur <= 8, f"{rel}: large shadow blur {decl}"
