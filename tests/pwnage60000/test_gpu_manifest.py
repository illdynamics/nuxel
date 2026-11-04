"""PWNAGE-60000 fail-closed GPU release manifest and image verifier tests."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GPU = ROOT / "release/s10plus/gpu"
MANIFEST = GPU / "gpu-manifest.json"
VERIFY = ROOT / "tools/s10plus/a67/nuxel-gpu-image-verify.sh"
BUILDER = ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_stage(tmp_path):
    m = json.loads(MANIFEST.read_text())
    stage = tmp_path / "stage"
    for entry in m["files"]:
        dst = stage / entry["install"].lstrip("/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GPU / entry["source"], dst)
        os.chmod(dst, int(entry["mode"], 8))
    for link in m["symlinks"]:
        dst = stage / link["path"].lstrip("/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(link["target"], dst)
    manifest_dst = stage / "usr/share/nuxel/gpu-manifest.json"
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANIFEST, manifest_dst)
    # PWNAGE-60000 boot-bootstrap guard, required when stage36000 exists.
    stage3600 = stage / "usr/lib/nuxel/stage36000"
    (stage3600 / "session").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh",
                 stage3600 / "apply-pwnage36000.sh")
    shutil.copy2(stage / "usr/lib/nuxel/nuxel-session.sh",
                 stage3600 / "session/nuxel-session.sh")
    return stage, m


def run_verify(stage, *args):
    env = dict(os.environ, NUXEL_GPU_REQUIRE_PROBE="0")
    return subprocess.run([str(VERIFY), str(stage), "--no-probe", *args],
                          capture_output=True, text=True, env=env)


def test_manifest_matches_release_files_and_pins():
    m = json.loads(MANIFEST.read_text())
    assert m["schema"] == "nuxel.gpu-manifest/1"
    assert m["profile"]["default_profile"] == "gpu-rendered-shm-presented"
    assert m["profile"]["fallback"] == "software-safe"
    assert "gpu-rendered-dmabuf-presented" in m["profile"]["unavailable"]
    assert "fully-accelerated" in m["profile"]["unavailable"]
    for entry in m["files"]:
        assert (GPU / entry["source"]).is_file()
        assert sha(GPU / entry["source"]) == entry["sha256"]
    pins = {}
    for line in (ROOT / "tools/s10plus/a67/gpu-build-pins.env").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            pins[k] = v.strip().strip('"')
    assert m["build"]["mesa"]["commit"] == pins["MESA_COMMIT"]
    assert m["build"]["wlroots"]["commit"] == pins["WLROOTS_COMMIT"]
    assert m["build"]["mesa"]["patch"]["sha256"] == sha(ROOT / pins["MESA_PATCH"])
    assert m["build"]["wlroots"]["patch"]["sha256"] == sha(ROOT / pins["WLROOTS_PATCH"])
    assert m["probe"]["sha256"] == sha(ROOT / m["probe"]["source"])


def test_release_copies_match_canonical_sources():
    pairs = {
        "nuxel-graphics-profile": ROOT / "tools/s10plus/a45/nuxel-graphics-profile",
        "graphics-profile.json": ROOT / "configs/nuxel/graphics/graphics-profile.json",
        "nuxel-gpu-status": ROOT / "tools/s10plus/a67/nuxel-gpu-status",
        "nuxel-wayland-gpu-wrapper.sh": ROOT / "tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh",
        "nuxel-session.sh": ROOT / "tools/s10plus/a45/nuxel-session.sh",
    }
    for name, source in pairs.items():
        assert sha(GPU / name) == sha(source), name + " is stale; run sync-gpu-release-assets.sh"


def test_sha256sums_file_is_complete():
    lines = [l for l in (GPU / "SHA256SUMS").read_text().splitlines() if l.strip()]
    assert len(lines) == 10
    for line in lines:
        digest, name = line.split(None, 1)
        assert sha(GPU / name.strip()) == digest


def test_image_verifier_passes_for_exact_stage(tmp_path):
    stage, _ = make_stage(tmp_path)
    p = run_verify(stage)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "GPU IMAGE VERIFY: PASS" in p.stdout


def test_image_verifier_rejects_hash_tamper(tmp_path):
    stage, _ = make_stage(tmp_path)
    target = stage / "usr/lib64/libgallium_dri.so"
    target.write_bytes(target.read_bytes() + b"x")
    p = run_verify(stage)
    assert p.returncode == 1
    assert "hash mismatch" in p.stderr


def test_image_verifier_rejects_stock_egl_symlink(tmp_path):
    stage, _ = make_stage(tmp_path)
    link = stage / "usr/lib64/libEGL_mesa.so.0"
    link.unlink()
    os.symlink("libEGL_mesa.so.0.0.0.nuxel-bak", link)
    p = run_verify(stage)
    assert p.returncode == 1
    assert "stock backup" in p.stderr


def test_image_verifier_rejects_unguarded_boot_bootstrap(tmp_path):
    stage, _ = make_stage(tmp_path)
    p = stage / "usr/lib/nuxel/stage36000/apply-pwnage36000.sh"
    p.write_text("#!/bin/sh\ninst session /usr/lib/nuxel/nuxel-session.sh\n")
    r = run_verify(stage)
    assert r.returncode == 1
    assert "can overwrite a newer deployed session" in r.stderr


def test_image_verifier_rejects_session_mismatch(tmp_path):
    stage, _ = make_stage(tmp_path)
    p = stage / "usr/lib/nuxel/stage36000/session/nuxel-session.sh"
    p.write_text("#!/bin/sh\n# old staged session\n")
    r = run_verify(stage)
    assert r.returncode == 1
    assert "staged and deployed nuxel-session.sh differ" in r.stderr


def test_image_verifier_rejects_software_default(tmp_path):
    stage, _ = make_stage(tmp_path)
    prof = stage / "etc/nuxel/graphics/graphics-profile.json"
    doc = json.loads(prof.read_text())
    doc["default_profile"] = "software-safe"
    prof.write_text(json.dumps(doc))
    p = run_verify(stage)
    assert p.returncode == 1
    assert "default_profile" in p.stderr or "hash mismatch" in p.stderr


def test_builder_is_fail_closed_for_release():
    s = BUILDER.read_text()
    assert 'GPU_REQUIRED="${NUXEL_REQUIRE_KBASE:-0}"' in s
    assert '[ "${NUXEL_RELEASE:-0}" = "1" ] && GPU_REQUIRED=1' in s
    assert "sha256sum -c SHA256SUMS" in s
    assert "nuxel-gpu-image-verify.sh" in s
    assert "image will use software GL" in s
    # A release build must not take the developer-tree fallback.
    assert 'if [ "$GPU_REQUIRED" = 1 ]; then' in s
