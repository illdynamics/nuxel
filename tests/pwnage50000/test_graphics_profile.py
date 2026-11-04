import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/s10plus/a45/nuxel-graphics-profile"


def fake_gpu(tmp_path):
    """Create a harmless stand-in for the kbase device/library set.

    PWNAGE-60000 makes GPU selection conditional on a bounded probe.  Unit
    tests must not depend on the host having /dev/mali0, so they point the
    helper at temp files and disable only the executable probe.  The identity
    checks (node, vendor JSON, libraries) still run.
    """
    node = tmp_path / "mali0"
    node.write_bytes(b"")
    node.chmod(0o666)
    libs = {}
    for name in ("libEGL_mesa.so.0.0.0", "libgallium_dri.so", "libwlroots-0.19.so"):
        lib = tmp_path / name
        lib.write_bytes(name.encode())
        libs[name] = lib
    vendor = tmp_path / "egl-kbase.json"
    vendor.write_text(json.dumps({"ICD": {"library_path": str(libs["libEGL_mesa.so.0.0.0"])}}))
    cache = tmp_path / "gpu-cache.json"
    return {
        "NUXEL_KBASE_NODE": str(node),
        "NUXEL_KBASE_EGL": str(libs["libEGL_mesa.so.0.0.0"]),
        "NUXEL_KBASE_GALLIUM": str(libs["libgallium_dri.so"]),
        "NUXEL_KBASE_WLROOTS": str(libs["libwlroots-0.19.so"]),
        "NUXEL_EGL_VENDOR": str(vendor),
        "NUXEL_GPU_CACHE": str(cache),
        "NUXEL_GPU_FALLBACK_MARKER": str(tmp_path / "no-fallback-marker"),
        "NUXEL_GPU_PROBE_DISABLE": "1",
    }


def run(tmp_path, doc, target="webkit", gpu=False):
    p = tmp_path / "graphics-profile.json"
    p.write_text(json.dumps(doc))
    env = dict(os.environ, NUXEL_GRAPHICS_PROFILE=str(p))
    if gpu:
        env.update(fake_gpu(tmp_path))
    return subprocess.run([sys.executable, str(TOOL), "env", target],
                          capture_output=True, text=True, env=env, check=True).stdout


def base():
    return {
        "schema_version": 1,
        "compositor": {"profile": "kbase-surfaceless", "allow_change": False},
        "webkitgtk": {"mode": "software", "fallback": "software"},
        "gtk3": {"mode": "software", "fallback": "software"},
        "gtk4": {"mode": "auto", "renderer": "auto", "fallback": "cairo"},
        "presentation": {"mode": "current-wl-fb", "target_fps": 24},
        "apps": {},
    }


def test_software_webkit_is_explicit_and_never_forced_accelerated(tmp_path):
    out = run(tmp_path, base())
    assert "WEBKIT_DISABLE_COMPOSITING_MODE=1" in out
    assert "WEBKIT_FORCE_COMPOSITING_MODE" not in out
    assert "LIBGL_ALWAYS_SOFTWARE=1" in out


def test_accelerated_webkit_does_not_leak_software(tmp_path):
    doc = base()
    doc["webkitgtk"]["mode"] = "accelerated"
    out = run(tmp_path, doc, gpu=True)
    assert "WEBKIT_DISABLE_COMPOSITING_MODE=0" in out
    assert "WEBKIT_FORCE_COMPOSITING_MODE=1" in out
    assert "LIBGL_ALWAYS_SOFTWARE" not in out
    assert "NUXEL_KBASE_WSI=1" in out


def test_invalid_mode_falls_back_closed(tmp_path):
    doc = base()
    doc["webkitgtk"]["mode"] = "gl; rm -rf /"
    out = run(tmp_path, doc)
    assert "WEBKIT_DISABLE_COMPOSITING_MODE=1" in out
    assert "NUXEL_GRAPHICS_FALLBACK_REASON=" in out


def test_gtk4_renderer_is_independent_of_webkit(tmp_path):
    doc = base()
    doc["gtk4"]["renderer"] = "cairo"
    out = run(tmp_path, doc, "gtk4")
    assert "GSK_RENDERER=cairo" in out
    assert "WEBKIT_DISABLE_COMPOSITING_MODE" not in out


def test_native_app_override_is_closed(tmp_path):
    doc = base()
    doc["apps"]["org.gnome.Loupe"] = {"toolkit": "gtk3", "profile": "software"}
    out = run(tmp_path, doc, "native:org.gnome.Loupe")
    assert "LIBGL_ALWAYS_SOFTWARE=1" in out
