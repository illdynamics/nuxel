"""PWNAGE-60000: production GPU-SHM profile, bounded fallback and validation."""
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/s10plus/a45/nuxel-graphics-profile"
SHIPPED = ROOT / "configs/nuxel/graphics/graphics-profile.json"


def fake_gpu(tmp_path, probe=None):
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
    env = {
        "NUXEL_KBASE_NODE": str(node),
        "NUXEL_KBASE_EGL": str(libs["libEGL_mesa.so.0.0.0"]),
        "NUXEL_KBASE_GALLIUM": str(libs["libgallium_dri.so"]),
        "NUXEL_KBASE_WLROOTS": str(libs["libwlroots-0.19.so"]),
        "NUXEL_EGL_VENDOR": str(vendor),
        "NUXEL_GPU_CACHE": str(tmp_path / "gpu-cache.json"),
        "NUXEL_GPU_FALLBACK_MARKER": str(tmp_path / "no-fallback-marker"),
    }
    if probe is None:
        env["NUXEL_GPU_PROBE_DISABLE"] = "1"
    else:
        env["NUXEL_GPU_PROBE"] = str(probe)
    return env


def write_probe(tmp_path, body):
    p = tmp_path / "probe.sh"
    p.write_text("#!/bin/sh\n" + body + "\n")
    p.chmod(0o755)
    return p


def run(doc, tmp_path, target="webkit", extra=None, path=SHIPPED):
    if doc is None:
        cfg = SHIPPED
    else:
        cfg = tmp_path / "profile.json"
        cfg.write_text(json.dumps(doc))
    env = dict(os.environ, NUXEL_GRAPHICS_PROFILE=str(cfg))
    for k in list(env):
        if k.startswith("NUXEL_GPU") or k.startswith("NUXEL_KBASE") or k.startswith("NUXEL_EGL"):
            env.pop(k, None)
    env.update(extra or {})
    return subprocess.run([sys.executable, str(TOOL), "env", target],
                          capture_output=True, text=True, env=env)


def parse(out):
    result = {}
    for line in out.splitlines():
        if line.startswith("export "):
            key, _, raw = line[7:].partition("=")
            result[key] = shlex.split(raw)[0] if raw else ""
    return result


def shipped():
    return json.loads(SHIPPED.read_text())


def test_shipped_default_is_gpu_shm_with_software_fallback(tmp_path):
    p = run(None, tmp_path, "webkit", fake_gpu(tmp_path))
    assert p.returncode == 0, p.stderr
    env = parse(p.stdout)
    assert env["NUXEL_GRAPHICS_PROFILE_REQUESTED"] == "gpu-rendered-shm-presented"
    assert env["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "gpu-rendered-shm-presented"
    assert "NUXEL_GRAPHICS_FALLBACK_REASON" not in env
    assert env["WEBKIT_FORCE_COMPOSITING_MODE"] == "1"
    assert env["WEBKIT_DISABLE_COMPOSITING_MODE"] == "0"
    assert env["NUXEL_KBASE_WSI"] == "1"
    assert "LIBGL_ALWAYS_SOFTWARE" not in env


def test_missing_gpu_device_falls_back_to_software_with_reason(tmp_path):
    p = run(None, tmp_path, "webkit", {})
    assert p.returncode == 0
    env = parse(p.stdout)
    assert env["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "software-safe"
    assert env["WEBKIT_DISABLE_COMPOSITING_MODE"] == "1"
    assert "GPU startup validation failed" in env["NUXEL_GRAPHICS_FALLBACK_REASON"]


def test_compositor_fallback_marker_forces_software(tmp_path):
    extra = fake_gpu(tmp_path)
    marker = tmp_path / "gpu-fallback"
    marker.write_text("")
    extra["NUXEL_GPU_FALLBACK_MARKER"] = str(marker)
    env = parse(run(None, tmp_path, "webkit", extra).stdout)
    assert env["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "software-safe"
    assert "fallback marker" in env["NUXEL_GRAPHICS_FALLBACK_REASON"]


def test_probe_accepts_panfrost_and_caches(tmp_path):
    counter = tmp_path / "calls"
    probe = write_probe(tmp_path, "echo x >> %s\necho GL_RENDERER=Mali-G76\\ MC12\\ \\(Panfrost\\)\nexit 0" % shlex.quote(str(counter)))
    extra = fake_gpu(tmp_path, probe=probe)
    first = parse(run(None, tmp_path, "webkit", extra).stdout)
    assert first["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "gpu-rendered-shm-presented"
    second = parse(run(None, tmp_path, "webkit", extra).stdout)
    assert second["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "gpu-rendered-shm-presented"
    assert counter.read_text().count("x") == 1, "second launch must use the per-boot cache"


def test_probe_rejects_llvmpipe(tmp_path):
    counter = tmp_path / "calls"
    probe = write_probe(tmp_path, "echo x >> %s\necho GL_RENDERER=llvmpipe\\ \\(LLVM\\ 19.1.0\\)\nexit 0" % shlex.quote(str(counter)))
    extra = fake_gpu(tmp_path, probe=probe)
    env = parse(run(None, tmp_path, "webkit", extra).stdout)
    assert env["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "software-safe"
    assert "kbase EGL probe failed" in env["NUXEL_GRAPHICS_FALLBACK_REASON"]
    second = parse(run(None, tmp_path, "webkit", extra).stdout)
    assert "cached kbase EGL probe failure" in second["NUXEL_GRAPHICS_FALLBACK_REASON"]
    assert counter.read_text().count("x") == 1, "negative result must be cached briefly"


def test_missing_probe_fails_closed(tmp_path):
    # A release image and the compositor boot gate must not treat a missing
    # probe as "GPU works".  Probe-disable is the explicit developer escape.
    extra = fake_gpu(tmp_path)
    extra.pop("NUXEL_GPU_PROBE_DISABLE", None)
    extra["NUXEL_GPU_PROBE"] = str(tmp_path / "missing-probe")
    env = parse(run(None, tmp_path, "webkit", extra).stdout)
    assert env["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "software-safe"
    assert "probe missing" in env["NUXEL_GRAPHICS_FALLBACK_REASON"]


def test_probe_timeout_falls_back(tmp_path):
    probe = write_probe(tmp_path, "sleep 5\nexit 0")
    extra = fake_gpu(tmp_path, probe=probe)
    extra["NUXEL_GPU_PROBE_TIMEOUT"] = "0.3"
    started = time.time()
    env = parse(run(None, tmp_path, "webkit", extra).stdout)
    assert time.time() - started < 3.0
    assert env["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "software-safe"
    assert "rc=124" in env["NUXEL_GRAPHICS_FALLBACK_REASON"]


def test_cache_invalidated_when_policy_changes(tmp_path):
    counter = tmp_path / "calls"
    probe = write_probe(tmp_path, "echo x >> %s\necho GL_RENDERER=Mali-G76\\ MC12\\ \\(Panfrost\\)\nexit 0" % shlex.quote(str(counter)))
    extra = fake_gpu(tmp_path, probe=probe)
    parse(run(None, tmp_path, "webkit", extra).stdout)
    assert counter.read_text().count("x") == 1
    time.sleep(0.02)
    doc = shipped()
    doc["profiles"]["gpu-rendered-shm-presented"]["note"] += " (touch)"
    run(doc, tmp_path, "webkit", extra)
    assert counter.read_text().count("x") == 2, "policy change must invalidate the probe cache"


def test_gtk3_and_gtk4_do_not_leak_webkit_vars(tmp_path):
    for target in ("gtk3", "gtk4"):
        env = parse(run(None, tmp_path, target, fake_gpu(tmp_path)).stdout)
        assert "WEBKIT_DISABLE_COMPOSITING_MODE" not in env
        assert "WEBKIT_FORCE_COMPOSITING_MODE" not in env
        assert "NUXEL_KBASE_WSI" not in env


def test_invalid_modes_and_injections_are_quoted(tmp_path):
    doc = shipped()
    doc["profiles"]["gpu-rendered-shm-presented"]["note"] = "$(touch /tmp/pwned)\n; rm -rf /"
    env = parse(run(doc, tmp_path, "webkit", fake_gpu(tmp_path)).stdout)
    assert env["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "gpu-rendered-shm-presented"
    # The note is not emitted at all; even a fallback reason must survive one
    # shlex round trip as a single literal value.
    doc["profiles"]["gpu-rendered-shm-presented"]["available"] = False
    doc["profiles"]["gpu-rendered-shm-presented"]["reason"] = "$(touch /tmp/pwned)\n; rm -rf /"
    env = parse(run(doc, tmp_path, "webkit", fake_gpu(tmp_path)).stdout)
    assert env["NUXEL_GRAPHICS_PROFILE_ACTIVE"] == "software-safe"
    assert "$(touch /tmp/pwned)" in env["NUXEL_GRAPHICS_FALLBACK_REASON"]


def test_validate_rejects_unknown_profile_and_bad_override(tmp_path):
    doc = shipped()
    doc["apps"]["bad app"] = {"profile": "nope", "toolkit": "gtk9"}
    cfg = tmp_path / "profile.json"
    cfg.write_text(json.dumps(doc))
    p = subprocess.run([sys.executable, str(TOOL), "validate"], capture_output=True,
                       text=True, env=dict(os.environ, NUXEL_GRAPHICS_PROFILE=str(cfg)))
    assert p.returncode == 1
    out = json.loads(p.stdout)
    assert not out["ok"]
    assert any("invalid app id" in e for e in out["errors"])
    assert any("not defined" in e for e in out["errors"])


def test_validate_rejects_missing_fallback_and_fake_full_acceleration(tmp_path):
    doc = shipped()
    doc["webkitgtk"]["fallback"] = "does-not-exist"
    doc["profiles"]["fully-accelerated"]["available"] = True
    cfg = tmp_path / "profile.json"
    cfg.write_text(json.dumps(doc))
    p = subprocess.run([sys.executable, str(TOOL), "validate"], capture_output=True,
                       text=True, env=dict(os.environ, NUXEL_GRAPHICS_PROFILE=str(cfg)))
    out = json.loads(p.stdout)
    assert p.returncode == 1
    assert any("fallback" in e for e in out["errors"])
    assert any("fully-accelerated" in e for e in out["errors"])


def test_status_reports_requested_active_and_gpu_separately(tmp_path):
    extra = fake_gpu(tmp_path)
    env = dict(os.environ, NUXEL_GRAPHICS_PROFILE=str(SHIPPED), **extra)
    p = subprocess.run([sys.executable, str(TOOL), "status", "--no-probe"],
                       capture_output=True, text=True, env=env)
    out = json.loads(p.stdout)
    assert out["default_profile"] == "gpu-rendered-shm-presented"
    assert out["active"]["webkit"]["profile_requested"] == "gpu-rendered-shm-presented"
    assert out["active"]["webkit"]["profile_active"] == "gpu-rendered-shm-presented"
    assert out["active"]["webkit"]["fallback_active"] is False
    assert out["gpu"]["ready"] is True
    assert out["profiles"]["gpu-rendered-dmabuf-presented"]["available"] is False
    assert out["profiles"]["fully-accelerated"]["available"] is False
