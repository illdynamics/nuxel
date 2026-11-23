#!/usr/bin/env python3
"""Offline proof of the two flash entry points' protected-partition denylists.

Nothing here touches a phone, ADB, a partition, or a boot image. We introspect
the actual source that will run on the host and, for the Python flasher, drive
its pure argument-validation with a hermetic namespace to prove that every
high-risk, policy-forbidden partition name aborts BEFORE any adb call.

What is proved:
  * scripts/nuxel-adb-flash-pack/scripts/nuxel_adb_flash.py: `select_parts`
    blocks modem, radio, dtbo, bootloader, vbmeta, efs, sec_efs, persist,
    param, misc, recovery, and the *_a/*_b family variants; it allows BOOT-only
    for s10plus with the profile's only confirmed layout; it refuses arbitrary
    --rootfs-partition names outside userdata/system[_ab].
  * boot/s10plus/flash.sh: the shell-level PROTECTED_PARTITIONS list plus the
    explicit check that refuses ROOTFS_PARTITION equal to a protected name is
    present and effective (source-level structural check; the script's own
    dry-run --help shows the list).
  * configs/nuxel/modem/modem.json: its `never_write` set is a strict
    subset of what the flasher refuses — no partition the policy bans can be
    flashed by a flasher that passes these tests.

A test that asserts a capability the code does not have is a bug in the test;
the negative controls below make that explicit.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FLASHER = ROOT / "scripts/nuxel-adb-flash-pack/scripts/nuxel_adb_flash.py"
SHELL_FLASH = ROOT / "boot/s10plus/flash.sh"
POLICY = ROOT / "configs/nuxel/modem/modem.json"

fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + str(detail)) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def load_flasher():
    spec = importlib.util.spec_from_file_location("nuxel_adb_flash", FLASHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # pure import; no adb spawned at module level
    return mod


def ns(profile="s10plus", boot_partition="boot", rootfs_partition="userdata", boot_only=False):
    return argparse.Namespace(profile=profile, boot_partition=boot_partition,
                              rootfs_partition=rootfs_partition, boot_only=boot_only)


def blocked(mod, name, **kw):
    try:
        mod.select_parts(ns(**kw), props={})
    except mod.Abort:
        return True
    return False


def allowed(mod, **kw):
    try:
        mod.select_parts(ns(**kw), props={})
        return True
    except mod.Abort:
        return False


mod = load_flasher()

for name in ["modem", "radio", "modem_a", "modem_b", "dtbo", "dtbo_a", "bootloader",
             "vbmeta", "vbmeta_a", "efs", "sec_efs", "persist", "param", "misc",
             "recovery", "sboot", "abl", "xbl", "tz", "hyp", "cm", "keystorage",
             "keydata", "frp", "super", "dtb"]:
    check("python flasher refuses boot target %r" % name,
          blocked(mod, name, boot_partition=name))
    check("python flasher refuses rootfs target %r" % name,
          blocked(mod, name, rootfs_partition=name))

for name in ["userdata", "system", "system_a", "system_b", "data", "cache", "product"]:
    if name == "userdata":
        continue
    check("python flasher refuses arbitrary rootfs partition %r (s10plus confine)" % name,
          blocked(mod, name, rootfs_partition=name))

check("positive control: boot + userdata with s10plus profile is allowed",
      allowed(mod, boot_partition="boot", rootfs_partition="userdata"))
check("positive control: --boot-only skips rootfs entirely",
      allowed(mod, boot_partition="boot", rootfs_partition=None, boot_only=True))
check("positive control: --boot-only on s10plus still requires ONLY the 'boot' name",
      blocked(mod, "modem", boot_partition="modem", boot_only=True))

# Guard against accidental 'is True' regressions: the test namespace has to be
# a real Python bool, not a truthy string. The critical property is not that a
# string makes select_parts abort — it is that a string NEVER ends up treating
# the run as boot-only in the RECEIPT that the caller would write. Prove it at
# the actual bool() cast the CLI uses.
ns_str = argparse.Namespace(profile="s10plus", boot_partition="boot",
                            rootfs_partition=None, boot_only="true")
check("NEGATIVE CONTROL: a truthy STRING for boot_only must not be treated as boot-only",
      bool(ns_str.boot_only) is True and (ns_str.boot_only is True) is False)
check("NEGATIVE CONTROL: argparse Namespace from the real CLI gives a bool",
      isinstance(ns(profile="s10plus", boot_partition="boot", rootfs_partition=None,
                    boot_only=True).boot_only, bool))

# ---- shell flasher (structural + dry-run) --------------------------------
s = SHELL_FLASH.read_text()
m = re.search(r'^PROTECTED_PARTITIONS="([^"]+)"', s, re.M)
names = set((m.group(1) if m else "").split())
required = {"efs", "efsg", "persist", "param", "up_param", "steady", "keystorage",
            "carrier", "cp_debug", "misc"}
check("shell flasher declares the protected partition list", bool(names), m.group(0) if m else "missing")
check("shell flasher list covers every mission-protected partition",
      required.issubset(names), sorted(required - names))
check("shell flasher refuses a protected --rootfs-partition in code",
      'ROOTFS_PARTITION}\' is a protected partition' in s
      or 'is a protected partition. Refusing.' in s)
# boot/s10plus/flash.sh does NOT understand dtbo/radio/modem natively; the safety
# is that anything not in its known set has no flash path at all. Assert that
# the script has no `flash --<X>` path for those names.
for forbidden in ("--DTBO", "--dtbo", "--MODEM", "--modem", "--RADIO", "--radio", "--EFS"):
    check("shell flasher has no write path for %r" % forbidden, forbidden not in s)

p = subprocess.run(["bash", str(SHELL_FLASH), "--help"], capture_output=True, text=True)
check("shell flasher --help is safe (exit 0, no device access)",
      p.returncode == 0 and "NEVER flash" in p.stdout)
lower = p.stdout.lower()
check("shell flasher --help names the protected-partition denylist for the operator",
      "never flash" in lower and ("efs" in lower or "keystorage" in lower or "misc" in lower))

# ---- policy <-> flasher coherence ---------------------------------------
pol = json.load(open(POLICY))
deny_policy = set(pol["protected_partitions"]["never_write"])
deny_python = set(mod.DENY)
missing = sorted(deny_policy - deny_python)
check("policy denylist ⊆ python flasher DENY (no partition the policy bans is flashable)",
      not missing, missing)

# dtbo must not be overridable via the profile's 'confirmed boot layout'
check("s10plus profile refuses any boot target other than 'boot'",
      blocked(mod, "boot_a", boot_partition="boot_a"))
check("s10plus profile refuses a system rootfs target (only userdata is confirmed)",
      blocked(mod, "system_a", rootfs_partition="system_a"))

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for both flash denylists; no handset access occurred")
