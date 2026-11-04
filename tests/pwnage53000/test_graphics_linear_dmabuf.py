"""PWNAGE-53000 regression tests: the linux-dmabuf modifier-mismatch crash.

The exact failure: wlroots advertised every renderer format/modifier pair
(including ARM tiled/SPARSE) while the kbase exporter allocated a physically
LINEAR udmabuf.  Mesa therefore selected e.g. AB24 + 0x0800000000000062; the
compositor import blocked and Phoc was reported as "crashed".

These tests are source-level invariants so they run on any host.  The live
on-device test is tools/s10plus/a67/pwnage53000-live-test.sh.
"""
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
A67 = ROOT / "tools" / "s10plus" / "a67"
PATCH = A67 / "wlroots-kbase-linear-dmabuf.patch"
PROFILE = ROOT / "tools" / "s10plus" / "a45" / "nuxel-graphics-profile"


def test_linear_patch_exists_and_filters_modifiers():
    text = PATCH.read_text()
    assert "linear_formats" in text
    assert "DRM_FORMAT_MOD_LINEAR" in text
    # It must build a new set instead of copying the renderer table verbatim.
    assert "wlr_drm_format_set_add(&linear_formats" in text
    assert "wlr_drm_format_set_copy(&linux_dmabuf->default_formats" not in text


def test_linear_patch_handles_null_egl_device():
    text = PATCH.read_text()
    # Mesa returns a null EGL device instead of failing the query; the guard
    # must treat both as "no DRM identity" on kbase.
    assert "EGL_NO_DEVICE_EXT" in text
    assert "egl->device = EGL_NO_DEVICE_EXT" in text


def test_dmabuf_global_only_for_kbase_env():
    text = (A67 / "wlroots-kbase-dmabuf.patch").read_text()
    assert 'getenv("MESA_KBASE_NODE")' in text
    assert "wlr_linux_dmabuf_v1_create_with_formats" in text


def test_mesa_exporter_is_linear_udmabuf_and_opt_in():
    text = (A67 / "mesa-kbase-wayland-wsi.patch").read_text()
    assert "UDMABUF_CREATE" in text
    assert 'getenv("NUXEL_KBASE_WSI")' in text
    # Never advertise a fake DRM node.
    assert "/dev/dri" not in text


def _profile_env(tmp_path, target):
    cfg = tmp_path / "profile.json"
    cfg.write_text(json.dumps({
        "schema_version": 2,
        "default_profile": "software-safe",
        "profiles": {
            "software-safe": {"available": True, "measured": True,
                              "webkitgtk": "software", "gtk3": "software"},
            "gpu-rendered-shm-presented": {"available": True, "measured": True,
                                            "webkitgtk": "gpu-rendered-shm-presented",
                                            "gtk3": "enabled"},
            "gpu-rendered-dmabuf-presented": {"available": False, "reason": "no drmMainDevice",
                                               "webkitgtk": "software", "gtk3": "software"},
            "fully-accelerated": {"available": False, "reason": "no scanout dma",
                                   "webkitgtk": "software", "gtk3": "software"},
        },
        "webkitgtk": {"profile": "software-safe"},
        "gtk3": {"profile": "software-safe"},
    }))
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
    env = {"NUXEL_GRAPHICS_PROFILE": str(cfg), "PATH": "/usr/bin:/bin",
           "NUXEL_KBASE_NODE": str(node),
           "NUXEL_KBASE_EGL": str(libs["libEGL_mesa.so.0.0.0"]),
           "NUXEL_KBASE_GALLIUM": str(libs["libgallium_dri.so"]),
           "NUXEL_KBASE_WLROOTS": str(libs["libwlroots-0.19.so"]),
           "NUXEL_EGL_VENDOR": str(vendor),
           "NUXEL_GPU_CACHE": str(tmp_path / "gpu-cache.json"),
           "NUXEL_GPU_FALLBACK_MARKER": str(tmp_path / "no-fallback-marker"),
           "NUXEL_GPU_PROBE_DISABLE": "1"}
    out = subprocess.run([str(PROFILE), "env", target], capture_output=True,
                         text=True, env=env, check=True).stdout
    return dict(line[7:].split("=", 1) for line in out.splitlines() if line.startswith("export "))


def test_software_profile_keeps_software_fallback(tmp_path):
    env = _profile_env(tmp_path, "profile:software-safe")
    assert env["LIBGL_ALWAYS_SOFTWARE"] == "1"
    assert env["WEBKIT_DISABLE_COMPOSITING_MODE"] == "1"


def test_gpu_shm_profile_is_not_mislabelled_as_dmabuf(tmp_path):
    env = _profile_env(tmp_path, "profile:gpu-rendered-shm-presented")
    assert env["WEBKIT_FORCE_COMPOSITING_MODE"] == "1"
    assert env["NUXEL_KBASE_WSI"] == "1"
    assert "LIBGL_ALWAYS_SOFTWARE" not in env


def test_unavailable_profiles_fall_back_loudly(tmp_path):
    for name in ("gpu-rendered-dmabuf-presented", "fully-accelerated"):
        env = _profile_env(tmp_path, "profile:" + name)
        assert env["WEBKIT_DISABLE_COMPOSITING_MODE"] == "1"
        assert "unavailable" in env["NUXEL_GRAPHICS_FALLBACK_REASON"]


def test_bridge_allows_new_graphics_keys():
    text = (ROOT / "services" / "nuxel-bridge" / "src" / "api.py").read_text()
    for key in ("GDK_GL", "LIBGL_DRIVERS_PATH", "__EGL_VENDOR_LIBRARY_FILENAMES"):
        assert key in text
