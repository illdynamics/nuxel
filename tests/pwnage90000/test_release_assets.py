#!/usr/bin/env python3
"""v0.7.9 release-asset + version lockstep gate.

This is intentionally dependency-free so the Release workflow can run it in the
lightweight `prepare` job before the expensive kernel/rootfs matrix.  It makes
the v0.7.8 failure class (a boot cue that exists only in an untracked working
tree) impossible to ship again.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = "v0.7.9-beta"

failures: list[str] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        failures.append(name)


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def tracked(rel: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


# ---- canonical version and lockstep ---------------------------------------
check("VERSION is v0.7.9-beta", text("VERSION").strip() == EXPECTED)
check("package.json version", f'"version": "{EXPECTED[1:]}"' in text("pwa/nuxel-common/package.json"))
bridge = json.loads(text("pwa/nuxel-common/bridge-version.json"))
check("bridge-version host_version", bridge.get("host_version") == EXPECTED[1:])
for rel in ("pwa/nuxel-home/manifest.json", "pwa/nuxel-apps/settings/manifest.json",
            "pwa/nuxel-apps/nuxtore/manifest.json"):
    doc = json.loads(text(rel))
    nuxel = doc.get("nuxel", {})
    check(f"{rel} pwa_version", nuxel.get("pwa_version") == EXPECTED[1:], nuxel.get("pwa_version"))
status_bar = text("pwa/nuxel-home/js/status-bar.js")
check("status bar VERSION", f"return '{EXPECTED[1:]}'" in status_bar)
for rel in ("services/nuxel-bridge/systemd/nuxel-bridge.service",
            "services/nuxel-bridge/systemd/nuxel-http-bridge.service",
            "services/nuxel-notifications/systemd/nuxel-notifications.service"):
    check(f"{rel} host pin", f"NUXEL_BRIDGE_VERSION={EXPECTED[1:]}" in text(rel))

manifest = json.loads(text("pwa/nuxel-home/manifest.json"))
cache = manifest["nuxel"]["cache_version"]
check("service-worker cache version", f"const CACHE_VERSION = '{cache}'" in text("pwa/nuxel-home/sw.js"))

# ---- boot cue asset is real, tracked and wired into every release path -----
cue = ROOT / "assets/nuxel-boot-audio.mp3"
check("canonical boot cue exists", cue.is_file() and cue.stat().st_size > 1000,
      cue.stat().st_size if cue.exists() else "missing")
check("canonical boot cue is committed", tracked("assets/nuxel-boot-audio.mp3"))
check("legacy sound-library cue is committed", tracked("assets/nuxel-sounds/nuxel-boot-audio.mp3"))
if cue.is_file():
    twin = ROOT / "assets/nuxel-sounds/nuxel-boot-audio.mp3"
    check("canonical and sound-library boot cue bytes agree",
          twin.is_file() and cue.read_bytes() == twin.read_bytes())
pow_cue = ROOT / "assets/nuxel-pow.mp3"
check("canonical pow cue exists", pow_cue.is_file() and pow_cue.stat().st_size > 1000,
      pow_cue.stat().st_size if pow_cue.exists() else "missing")
check("canonical pow cue is committed", tracked("assets/nuxel-pow.mp3"))
if pow_cue.is_file():
    twin = ROOT / "assets/nuxel-sounds/nuxel-pow.mp3"
    check("canonical and sound-library pow cue bytes agree",
          twin.is_file() and pow_cue.read_bytes() == twin.read_bytes())

builder = text("images/s10plus/build-phone-rootfs-inside-fedora.sh")
check("rootfs builder installs both real cue files",
      'for _cue in nuxel-boot-audio.mp3 nuxel-pow.mp3' in builder)
verifier = text("tools/s10plus/verify-fedora-phone-rootfs.py")
check("rootfs verifier requires the boot cue",
      "'/usr/share/nuxel/assets/nuxel-boot-audio.mp3'" in verifier and
      "'/usr/share/nuxel/assets/nuxel-boot-audio.mp3': 'assets/nuxel-boot-audio.mp3'" in verifier)
check("live payload packages the boot cue",
      "'assets/nuxel-boot-audio.mp3'" in text("tools/s10plus/a43/package-live.py"))
check("live payload verifier requires the boot cue",
      "'assets/nuxel-boot-audio.mp3'" in text("tools/s10plus/a43/verify-live.py"))
boot_unit = text("services/nuxel-session/systemd/nuxel-boot-sound.service")
check("boot-sound unit selects the boot cue path",
      "/usr/libexec/nuxel/nuxel-sound-cue boot" in boot_unit and
      "/run/nuxel-audio-route.ready" in boot_unit)

print(f"\npwnage90000 release-asset gate: {len(failures)} failure(s)")
sys.exit(1 if failures else 0)
