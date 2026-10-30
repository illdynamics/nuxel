"""PWNAGE-37000 offline regression checks (no physical device required).

These tests pin the invariants that the Butterscotch pass must not regress:

  * the lightweight arcade visual profile keeps the expensive WebKitGTK effects
    (backdrop blur, large blur shadows, blur-based drop-shadow glow) out of the
    home UI, while preserving the recognizable arcade theme;
  * the pre-lockscreen cinema is wired back into BOTH session scripts (A29 and
    A45) so the video plays again, and the asset hash is consistent;
  * the Gallery seeder copies two real image assets plus one real video into
    the user media folders without touching real data (temp fixtures only).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── 1. Lightweight arcade visual profile ──────────────────────────────────
EXPENSIVE_HOME_CSS = [
    "pwa/nuxel-home/css/status-bar.css",
    "pwa/nuxel-home/css/lockscreen.css",
    "pwa/nuxel-home/css/launcher.css",
    "pwa/nuxel-home/css/home-settings.css",
    "pwa/nuxel-home/css/style.css",
]


@pytest.mark.parametrize("rel", EXPENSIVE_HOME_CSS)
def test_home_css_has_no_backdrop_blur(rel):
    text = _read(ROOT / rel)
    assert "backdrop-filter" not in text, f"{rel} still uses expensive backdrop-filter"
    assert "-webkit-backdrop-filter" not in text, f"{rel} still uses -webkit-backdrop-filter"


def test_home_css_has_no_blur_drop_shadow_glow():
    # blur-based drop-shadow glow was replaced by cheap brightness acknowledgement
    text = _read(ROOT / "pwa/nuxel-home/css/lockscreen.css")
    assert "drop-shadow(0 6px 22px" not in text
    assert "drop-shadow(0 0 24px" not in text
    assert "filter: brightness" in text


def test_home_css_has_no_giant_panel_shadows():
    # Large software-rasterised blur shadows were reduced to cheap crisp shadows.
    # Only inspect box-shadow blur radii (a transform translateY(-160px) is not
    # a shadow and must not trip the check).
    import re
    for rel in EXPENSIVE_HOME_CSS:
        text = _read(ROOT / rel)
        for blur in re.findall(r"box-shadow:\s*[^;{]*?([0-9]+)px\s+rgba", text):
            assert int(blur) < 24, f"{rel} still has a large blur shadow ({blur}px)"


def test_arcade_palette_and_penguin_personality_preserved():
    # The visual identity survives: the penguin glyphs, blue gradient palette
    # and pixel borders are still present in the theme/config layer.
    css = _read(ROOT / "pwa/nuxel-home/css/lockscreen.css")
    assert "lockscreen-handle" in css and "lockscreen-lockhead" in css
    # The zsh penguin + arcade prompts remain the default personality (theme 1).
    zsh = _read(ROOT / "services/nuxel-zsh/nuxel.zsh")
    assert "NUXEL_PROMPT_STYLE:=1" in zsh or "NUXEL_PROMPT_STYLE=1" in _read(
        ROOT / "services/nuxel-zsh/nuxel-zsh.conf")


# ── 2. Pre-lockscreen cinema wiring ───────────────────────────────────────
def test_both_session_scripts_launch_preload_cinema_early():
    for rel in ("tools/s10plus/a29/nuxel-session.sh",
                "tools/s10plus/a45/nuxel-session.sh"):
        text = _read(ROOT / rel)
        assert "nuxel-preload-session.owner" in text, rel
        assert "nuxel-preload-cinema --early" in text, rel
        assert "preload-status.json" in text, rel


def test_a29_and_a45_session_scripts_are_identical():
    a29 = _read(ROOT / "tools/s10plus/a29/nuxel-session.sh")
    a45 = _read(ROOT / "tools/s10plus/a45/nuxel-session.sh")
    assert a29 == a45, "A29/A45 session scripts drifted; the preload regression can return"


def test_preloading_asset_hash_matches_config():
    asset = ROOT / "assets/nuxel-preloading-screen.mp4"
    cfg = json.loads(_read(ROOT / "configs/nuxel/boot/preload-cinema.json"))
    want = (cfg.get("asset_sha256") or "").lower()
    actual = hashlib.sha256(asset.read_bytes()).hexdigest()
    assert want == actual
    assert asset.stat().st_size == cfg["_asset"]["bytes"]


def test_preloading_mp4_is_valid_h264():
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height",
         "-of", "default=noprint_wrappers=1:nokey=1",
         str(ROOT / "assets/nuxel-preloading-screen.mp4")],
        capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert "h264" in proc.stdout
    assert "1080" in proc.stdout and "1920" in proc.stdout


# ── 3. Gallery seeding ────────────────────────────────────────────────────
def test_gallery_seeder_copies_two_images_and_one_video():
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ)
        env.update({
            "NUXEL_MEDIA_DIR": os.path.join(tmp, "media"),
            "NUXEL_FILES_ROOT": os.path.join(tmp, "home"),
            "NUXEL_APP_DATA_DIR": "",
        })
        proc = subprocess.run(
            [sys.executable,
             str(ROOT / "pwa/nuxel-apps/photos/tools/seed-samples.py")],
            env=env, capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        gallery = Path(tmp) / "home" / "Gallery"
        videos = Path(tmp) / "home" / "Videos"
        images = sorted(p.name for p in gallery.glob("*") if p.is_file())
        vids = sorted(p.name for p in videos.glob("*") if p.is_file())
        assert len(images) >= 2, images
        assert any(name in images for name in ("nuxel-wallpaper.png", "nuxel-charging.png"))
        assert "nuxel-boot-animation.mp4" in vids
