#!/usr/bin/env python3
"""Verify the PWNAGE-31000 preload-cinema wiring and supplied-asset packaging.

This is an offline gate: it never touches the phone, a block device, a boot
image or a service.  It answers:

  * do the controller, unit, config, image builders and live manifest agree on
    the runtime paths and the supplied asset bytes?
  * is the supplied clip present, readable, non-empty, hash-verifiable and
    decodable by the installed media stack?
  * are the real MP4 properties (duration, dimensions, frame rate, audio track)
    the ones the timing/audio policy was designed around?
  * does the live manifest plan cleanly with the repository's real planner,
    including SHA-256 coverage of the 7.6 MB asset and no unintended service
    restart?
  * do the rootfs packaging paths install the asset, mpv and the controller?

Exit codes
  0  PASS, or ASSET_MISSING with --allow-missing
  2  wiring/config mismatch
  3  supplied asset missing and --allow-missing was not given
  4  asset present but invalid
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "services/nuxel-preload-cinema/nuxel-preload-cinema"
UNIT = ROOT / "services/nuxel-preload-cinema/nuxel-preload-cinema.service"
CONFIG = ROOT / "configs/nuxel/boot/preload-cinema.json"
ASSET = ROOT / "assets/nuxel-preloading-screen.mp4"
MANIFEST = ROOT / "tools/beta/live/nuxel-31000-preload-cinema-manifest.json"
PHONE_BUILDER = ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh"
VM_BUILDER = ROOT / "images/mkrootfs.sh"
ROOTFS_VERIFIER = ROOT / "tools/s10plus/verify-fedora-phone-rootfs.py"
PACKAGES = ROOT / "images/s10plus/packages-manifest.json"
IMPLEMENTATION = ROOT / "docs/pwnage-31000/IMPLEMENTATION.md"

RUNTIME_ASSET = "/usr/share/nuxel/preload/nuxel-preloading-screen.mp4"
RUNTIME_CONTROLLER = "/usr/lib/nuxel/nuxel-preload-cinema"
RUNTIME_UNIT = "/etc/systemd/system/nuxel-preload-cinema.service"
RUNTIME_CONFIG = "/etc/nuxel/boot/preload-cinema.json"
EXPECTED_SHA = "b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1"
EXPECTED_DURATION = 6.016
EXPECTED_BYTES = 7_630_092

checks: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail and not ok else ""))
    return bool(ok)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_controller_module():
    """Load the extensionless installed controller for its stdlib MP4 parser.

    ``spec_from_file_location`` returns None for a file without a .py suffix,
    so the earlier verifier silently skipped the duration check.  Use an
    explicit SourceFileLoader and register the module before exec (dataclasses
    needs sys.modules for postponed annotations).
    """
    name = "nuxel_preload_cinema_verify"
    loader = importlib.machinery.SourceFileLoader(name, str(CONTROLLER))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def inspect_with_ffprobe(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return {}
    if out.returncode != 0:
        return {"error": out.stderr.strip()[:200]}
    try:
        return json.loads(out.stdout)
    except ValueError:
        return {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allow-missing", action="store_true",
                    help="report ASSET_MISSING and exit 0 instead of 3")
    ap.add_argument("--json", action="store_true", help="print a JSON report")
    args = ap.parse_args(argv)

    for path, label in ((CONTROLLER, "controller"), (UNIT, "unit"), (CONFIG, "config"),
                        (MANIFEST, "manifest"), (PHONE_BUILDER, "phone builder"),
                        (VM_BUILDER, "VM builder"), (ROOTFS_VERIFIER, "rootfs verifier"),
                        (PACKAGES, "package manifest")):
        check("%s exists" % label, path.is_file(), str(path))
    if not all(p.is_file() for p in (CONTROLLER, UNIT, CONFIG, MANIFEST,
                                     PHONE_BUILDER, VM_BUILDER, ROOTFS_VERIFIER,
                                     PACKAGES)):
        return 2

    check("controller is executable", os.access(CONTROLLER, os.X_OK), str(CONTROLLER))
    syntax = subprocess.run([sys.executable, "-m", "py_compile", str(CONTROLLER)],
                            capture_output=True, text=True)
    check("controller compiles", syntax.returncode == 0, syntax.stderr.strip()[:240])

    controller_text = CONTROLLER.read_text(encoding="utf-8")
    unit_text = UNIT.read_text(encoding="utf-8")
    phone_text = PHONE_BUILDER.read_text(encoding="utf-8")
    vm_text = VM_BUILDER.read_text(encoding="utf-8")
    rootfs_verifier_text = ROOTFS_VERIFIER.read_text(encoding="utf-8")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    packages = json.loads(PACKAGES.read_text(encoding="utf-8"))

    check("config asset path is the runtime preload asset",
          config.get("asset") == RUNTIME_ASSET, str(config.get("asset")))
    check("controller default asset path matches config",
          RUNTIME_ASSET in controller_text, RUNTIME_ASSET)
    check("config player is the packaged /usr/bin/mpv",
          config.get("player") == "/usr/bin/mpv", str(config.get("player")))
    check("controller default player matches config",
          'DEFAULT_PLAYER = "/usr/bin/mpv"' in controller_text)
    check("start timeout covers the initramfs animation handoff",
          int(config.get("start_timeout_ms") or 0) >= 20000,
          str(config.get("start_timeout_ms")))
    check("worst-case overlay release precedes the fallback unit",
          int(config.get("start_timeout_ms") or 0)
          + int(config.get("hard_timeout_ms") or 0) < 60000,
          "%s + %s" % (config.get("start_timeout_ms"), config.get("hard_timeout_ms")))
    check("unit ExecStart is the runtime controller",
          ("ExecStart=%s" % RUNTIME_CONTROLLER) in unit_text, RUNTIME_CONTROLLER)
    check("unit is ordered after compositor and display bridge",
          "After=nuxel-wayland.service nuxel-wl-fb.service" in unit_text)
    check("unit may write the launcher status file",
          "/usr/share/nuxel/nuxel-home" in unit_text)
    check("unit is one bounded attempt per boot",
          "Restart=no" in unit_text and "StartLimitBurst=1" in unit_text)
    check("controller never opens /dev/fb0",
          not re.search(r"open\(\s*[\"']/dev/fb0", controller_text))
    check("controller never invokes the unlock action",
          not re.search(r"action_perform\(\s*[\"']unlock|system\.action.*unlock",
                        controller_text))
    check("controller disables player controls", "--input-default-bindings=no" in controller_text)
    check("controller forces audio off",
          "--no-audio" in controller_text and "--mute=yes" in controller_text
          and config.get("audio") == "never")
    check("controller preserves aspect ratio",
          "--keepaspect=yes" in controller_text and "--panscan=0" in controller_text)
    check("controller has one bounded instance lock",
          "LOCK_EX | fcntl.LOCK_NB" in controller_text)
    check("controller has a one-shot boot marker",
          "preload-cinema.done" in controller_text and "ALREADY_RAN" in controller_text)
    check("controller uses the fresh persistent display receipt",
          "/var/lib/nuxel/display" in controller_text
          and "display_state_fresh" in controller_text
          and "_fresh_for_boot" in controller_text)

    # Manifest wiring.  The asset entry is required, not merely present.
    groups = manifest.get("groups") or []
    files = [f for g in groups for f in (g.get("files") or [])]
    by_target = {f.get("target"): f for f in files}
    check("manifest installs the controller", by_target.get(RUNTIME_CONTROLLER, {}).get("source") ==
          "services/nuxel-preload-cinema/nuxel-preload-cinema")
    check("manifest installs the unit", by_target.get(RUNTIME_UNIT, {}).get("source") ==
          "services/nuxel-preload-cinema/nuxel-preload-cinema.service")
    check("manifest installs the config", by_target.get(RUNTIME_CONFIG, {}).get("source") ==
          "configs/nuxel/boot/preload-cinema.json")
    asset_entry = by_target.get(RUNTIME_ASSET) or {}
    check("manifest installs the supplied asset",
          asset_entry.get("source") == "assets/nuxel-preloading-screen.mp4",
          str(asset_entry.get("source")))
    check("manifest installs the asset with mode 0644", asset_entry.get("mode") == "0644",
          str(asset_entry.get("mode")))
    check("manifest declares the supplied asset hash",
          str(asset_entry.get("sha256") or "").lower() == EXPECTED_SHA,
          str(asset_entry.get("sha256")))
    check("manifest has no deferred non-deployable entries",
          not (manifest.get("non_deployable") or []))
    health = str((groups[0] if groups else {}).get("health_check") or "")
    check("manifest health check pins the asset hash", EXPECTED_SHA in health)
    check("manifest health check requires the packaged player", "/usr/bin/mpv" in health)

    # Use the repository's real planner/validator.
    sys.path.insert(0, str(ROOT / "tools/beta/live"))
    import nuxel_live as nl  # noqa: E402
    violations = nl.validate_manifest(manifest, str(ROOT))
    check("manifest passes validate_manifest", not violations, json.dumps(violations)[:500])
    plan = nl.build_deploy_plan(manifest, str(ROOT))
    check("manifest plans cleanly", not plan["violations"], json.dumps(plan["violations"])[:500])
    asset_steps = [s for s in plan["steps"] if s["source"] == "assets/nuxel-preloading-screen.mp4"]
    check("plan carries the asset step", bool(asset_steps),
          json.dumps([s["source"] for s in plan["steps"]]))
    if asset_steps:
        check("plan hash-covers the actual asset file",
              asset_steps[0]["source_sha256"] == EXPECTED_SHA,
              asset_steps[0]["source_sha256"])
    check("plan does not restart the compositor for a boot asset",
          plan["activation_plan"].get("restarts") == [],
          json.dumps(plan["activation_plan"].get("restarts")))
    check("plan performs the deliberate daemon-reload",
          plan["activation_plan"].get("daemon_reload") is True)

    # Packaging paths.
    check("phone builder installs the controller", "nuxel-preload-cinema" in phone_text)
    check("phone builder installs the supplied asset",
          RUNTIME_ASSET in phone_text)
    check("phone builder verifies the configured asset hash",
          "asset_sha256" in phone_text and "!= \"$_preload_want\"" in phone_text)
    check("phone builder packages mpv", re.search(r"\bmpv\b", phone_text) is not None)
    check("phone builder enables the controller only on launcher images",
          "multi-user.target.wants/nuxel-preload-cinema.service" in phone_text)
    check("VM builder installs the asset and verifies its hash",
          "nuxel-preloading-screen.mp4" in vm_text and "asset_sha256" in vm_text)
    check("rootfs verifier requires /usr/bin/mpv", "'/usr/bin/mpv'" in rootfs_verifier_text)
    check("rootfs verifier requires the runtime asset", RUNTIME_ASSET in rootfs_verifier_text)
    check("package manifest records mpv",
          any(p.get("name") == "mpv" for g in packages.get("groups", [])
              for p in g.get("packages", [])))
    check("implementation doc contains rollback instructions",
          IMPLEMENTATION.is_file() and "Rollback" in IMPLEMENTATION.read_text(encoding="utf-8"))

    # Asset inspection.
    verdict = "PASS"
    asset_report: dict = {}
    code = 0
    if not ASSET.is_file():
        verdict = "ASSET_MISSING"
        print("BLOCKED assets/nuxel-preloading-screen.mp4 is absent; controller will fall back to the lockscreen")
        code = 0 if args.allow_missing else 3
    else:
        size = ASSET.stat().st_size
        digest = sha256(ASSET)
        asset_report = {"path": str(ASSET.relative_to(ROOT)), "bytes": size,
                        "sha256": digest, "runtime_path": RUNTIME_ASSET}
        check("asset is non-empty", size == EXPECTED_BYTES, str(size))
        check("asset is readable", os.access(ASSET, os.R_OK), str(ASSET))
        check("asset matches the configured sha256",
              str(config.get("asset_sha256") or "").lower() == digest,
              "%s != %s" % (digest, config.get("asset_sha256")))
        check("asset matches the manifest sha256", digest == EXPECTED_SHA,
              "%s != %s" % (digest, EXPECTED_SHA))
        module = load_controller_module()
        duration = module.mp4_duration_seconds(ASSET) if module else None
        check("controller MP4 parser reads the real duration",
              duration is not None and abs(duration - EXPECTED_DURATION) < 0.05,
              str(duration))
        ff = inspect_with_ffprobe(ASSET)
        asset_report["duration_s"] = duration
        if ff:
            streams = ff.get("streams") or []
            video = next((s for s in streams if s.get("codec_type") == "video"), {})
            audio = [s for s in streams if s.get("codec_type") == "audio"]
            fmt = ff.get("format") or {}
            asset_report.update({
                "codec": video.get("codec_name"),
                "width": video.get("width"),
                "height": video.get("height"),
                "pix_fmt": video.get("pix_fmt"),
                "r_frame_rate": video.get("r_frame_rate"),
                "nb_frames": video.get("nb_frames"),
                "audio_streams": len(audio),
                "format_duration_s": fmt.get("duration"),
            })
            check("asset has an H.264 video stream", video.get("codec_name") == "h264",
                  json.dumps(video)[:200])
            check("asset is portrait 1080x1920",
                  video.get("width") == 1080 and video.get("height") == 1920,
                  "%sx%s" % (video.get("width"), video.get("height")))
            check("asset is 24 fps / 144 frames",
                  video.get("r_frame_rate") == "24/1" and str(video.get("nb_frames")) == "144",
                  "%s %s" % (video.get("r_frame_rate"), video.get("nb_frames")))
            check("asset audio track is present but policy disables it",
                  len(audio) == 1 and "--no-audio" in controller_text and "--mute=yes" in controller_text,
                  json.dumps(audio)[:200])
            check("asset format duration is the expected 6.016 s",
                  abs(float(fmt.get("duration") or 0) - EXPECTED_DURATION) < 0.05,
                  str(fmt.get("duration")))
        else:
            check("ffprobe inspection available", False, "ffprobe not installed")
        code = 0 if all(c["ok"] for c in checks) else 4
        if code != 0:
            verdict = "FAIL"

    report = {"schema_version": 1, "verdict": verdict, "asset": asset_report,
              "checks": checks, "config": str(CONFIG.relative_to(ROOT)),
              "manifest": str(MANIFEST.relative_to(ROOT))}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    print("VERDICT %s checks=%d failed=%d" %
          (verdict, len(checks), sum(1 for c in checks if not c["ok"])))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
