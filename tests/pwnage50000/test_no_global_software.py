from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_session_does_not_unconditionally_disable_webkit():
    s = (ROOT / "tools/s10plus/a45/nuxel-session.sh").read_text()
    assert "WEBKIT_DISABLE_COMPOSITING_MODE=1" not in s.split("nuxel-graphics-profile env webkit", 1)[0]
    assert "nuxel-graphics-profile env webkit" in s


def test_native_launch_uses_profile_helper_not_hardcoded_software():
    s = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    assert "_graphics_env_for" in s
    assert "GSK_RENDERER=cairo" not in s
    assert "LIBGL_ALWAYS_SOFTWARE=1" not in s


def test_graphics_defaults_are_software_webkit_and_independent_gtk4():
    s = (ROOT / "configs/nuxel/graphics/graphics-profile.json").read_text()
    assert '"mode": "software"' in s
    assert '"webkitgtk"' in s and '"gtk4"' in s
