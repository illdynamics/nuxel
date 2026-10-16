#!/usr/bin/env python3
"""Offline tests for the S10+ microSD work (briq-08i, manual area 18).

Proven offline: the card-state chain over four fixtures (no controller / internal
only / card present-unmounted / mounted read-only), the hard safety invariants
(internal mmcblk0 is never a target, /dev/block paths are refused, nothing is
ever formatted, unknown filesystems are refused, read-write needs an explicit
--yes), eject/unmount refusals, and the manual-proof fragment. Inserting and
removing a real card stays NEEDS_OWNER_TEST.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-microsd-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "modem", "microsd.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "18-microsd.md")
FAKE = {"NUXEL_DIAG_NO_SYSTEM": "1"}
fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


def json_of(out):
    return json.loads([l for l in out.splitlines() if l.startswith("{")][0])


p = run(["bash", TOOL, "selftest"])
check("fixture verdicts (none / internal-only / present / mounted-ro) match",
      p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
check("policy never formats or partitions",
      pol["safety"]["never_format"] is True and pol["safety"]["never_partition"] is True)
check("policy refuses internal storage as a card target",
      pol["safety"]["never_write_to_internal"] is True
      and "/dev/mmcblk0" in pol["safety"]["internal_target_denylist"])
check("policy defaults to a READ-ONLY mount and requires --yes for rw",
      pol["safety"]["default_mount_readonly"] is True
      and pol["safety"]["require_explicit_yes_for_rw"] is True)
check("policy forbids mkfs/partition tools",
      all(t in pol["safety"]["forbidden_tools"] for t in ["mkfs", "fdisk", "parted", "wipefs", "dd"]))
check("policy supports the usual media filesystems and refuses unknown ones",
      set(["ext4", "f2fs", "vfat", "exfat", "ntfs3"]).issubset(set(pol["filesystems"]["supported"]))
      and "REFUSE" in pol["filesystems"]["unsupported_action"])
check("policy never auto-formats and automount is read-only",
      pol["diagnostics"]["auto_format"] is False
      and pol["diagnostics"]["auto_mount_readonly"] is True)

# --- state chain ------------------------------------------------------------
d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-absent"), "status", "--json"], FAKE).stdout)
check("no controller => NO_CARD_CONTROLLER", d["state"] == "NO_CARD_CONTROLLER")
check("status always reports no card data written and no auto-format",
      d["card_data_written"] is False and d["auto_format"] is False and d["never_format"] is True)

d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-internal-only"), "status", "--json"], FAKE).stdout)
check("internal UFS only => INTERNAL_ONLY with the internal device listed",
      d["state"] == "INTERNAL_ONLY" and any("mmcblk0" in x for x in d["internal_devices"]))

d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "status", "--json"], FAKE).stdout)
check("external card present, unmounted => CARD_PRESENT_UNMOUNTED",
      d["state"] == "CARD_PRESENT_UNMOUNTED" and "/dev/mmcblk1" in d["external_devices"]
      and d["removable"] == "1")

d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-mounted"), "status", "--json"], FAKE).stdout)
check("mounted read-only card => MOUNTED_RO", d["state"] == "MOUNTED_RO")
check("owner-test fragment is pointed at from every status",
      d["owner_test"] == "docs/beta-finalization/manual-proof/18-microsd.md")

p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "cards"], FAKE)
check("`cards` marks internal storage as NEVER a target",
      "NEVER a microSD target" in p.stdout and "forbidden" in p.stdout)

# --- refusals ---------------------------------------------------------------
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "mount", "/dev/mmcblk0p1"], FAKE)
check("mount refuses internal storage (mmcblk0p1)", p.returncode != 0 and "INTERNAL UFS" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "mount", "/dev/block/sda1"], FAKE)
check("mount refuses /dev/block paths", p.returncode != 0 and "/dev/block" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "mount", "/dev/mmcblk1"], FAKE)
check("mount refuses an unknown filesystem instead of guessing",
      p.returncode != 0 and "unknown" in p.stdout and "guessed or created" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "mount", "/dev/mmcblk1", "--fstype", "ext4"], FAKE)
check("mount under a faked root performs nothing",
      p.returncode != 0 and "offline/faked root" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "mount", "/dev/mmcblk1", "--fstype", "ext4", "--rw"], FAKE)
check("a read-write mount is refused without an explicit --yes",
      p.returncode != 0 and "read-write" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "mount", "/dev/mmcblk1", "--fstype", "ntfs3", "--rw", "--yes"], FAKE)
check("a filesystem marked read-only by policy cannot be mounted rw",
      p.returncode != 0 and "read-only by policy" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "unmount", "/dev/mmcblk0"], FAKE)
check("unmount refuses internal storage", p.returncode != 0 and "INTERNAL UFS" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-present"), "eject", "/dev/mmcblk0p1"], FAKE)
check("eject refuses internal storage", p.returncode != 0 and "INTERNAL UFS" in p.stdout, p.stdout)

# --- auto-mount (insert only, read-only, never at boot) ---------------------
READY = os.path.join(FIX, "microsd-ready")
BOOTWIN = os.path.join(FIX, "microsd-boot-window")
p = run(["bash", TOOL, "--root", BOOTWIN, "automount"], FAKE)
check("auto-mount is SKIPPED inside the boot window",
      p.returncode == 0 and "boot window" in p.stdout and "NOT auto-mounted" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-absent"), "automount"], FAKE)
check("auto-mount with no card is a quiet no-op (exit 0, no failed unit)",
      p.returncode == 0 and "nothing to do" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-internal-only"), "automount"], FAKE)
check("auto-mount refuses to treat internal storage as a card",
      p.returncode == 0 and "nothing to do" in p.stdout and "INTERNAL_ONLY" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "microsd-mounted"), "automount"], FAKE)
check("auto-mount is idempotent on an already-mounted card",
      p.returncode == 0 and "already mounted" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", READY, "automount"], FAKE)
check("auto-mount refuses an unknown filesystem instead of guessing",
      p.returncode == 9 and "unknown" in p.stdout and "never guessed" not in p.stdout, p.stdout)
env = dict(FAKE); env["NUXEL_MICROSD_FSTYPE"] = "vfat"
p = run(["bash", TOOL, "--root", READY, "automount"], env)
check("auto-mount mounts READ-ONLY only (offline root: planned, nothing performed)",
      p.returncode == 0 and "read-only" in p.stdout and "no real mount performed" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", READY, "automount-status"], FAKE)
check("auto-mount status reports the boot window, the switch and the readonly-only rule",
      "boot grace window" in p.stdout and "read-only only" in p.stdout
      and "udev rule" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", READY, "automount-off"], FAKE)
check("the owner can switch auto-mount off", p.returncode == 0 and "off" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", READY, "automount"], env)
check("auto-mount refuses while the owner switch is off",
      p.returncode == 0 and "disabled by the owner" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", READY, "automount-on"], FAKE)
check("the owner can switch auto-mount back on", p.returncode == 0 and "on" in p.stdout, p.stdout)
pol = json.load(open(POLICY))
check("policy separates insert from boot and keeps boot auto-mount off",
      pol["automount"]["enabled_key"] == "diagnostics.auto_mount_on_insert"
      and pol["automount"]["boot_flag_key"] == "diagnostics.auto_mount_on_boot"
      and pol["diagnostics"]["auto_mount_on_boot"] is False)
check("policy makes auto-mount read-only-only", pol["automount"]["read_only_only"] is True)
check("policy never auto-formats", pol["diagnostics"]["auto_format"] is False)
rules = os.path.join(ROOT, "configs", "nuxel", "modem", "90-nuxel-microsd.rules")
rtxt = open(rules).read() if os.path.isfile(rules) else ""
check("udev rule targets only external mmc devices and hands off to systemd",
      'KERNEL=="mmcblk[1-9]"' in rtxt and 'SYSTEMD_WANTS}+="nuxel-microsd-automount.service"' in rtxt)
check("udev rule never matches internal storage and asks for no mount options",
      "mmcblk0" not in rtxt.split("KERNEL==")[-1] and "-o rw" not in rtxt and "mkfs" not in rtxt)
unit = os.path.join(ROOT, "configs", "nuxel", "modem", "nuxel-microsd-automount.service")
utxt = open(unit).read() if os.path.isfile(unit) else ""
check("service is oneshot, non-looping and read-only by delegation",
      "Type=oneshot" in utxt and "Restart=no" in utxt and "automount" in utxt)
_dtxt_now = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment documents auto-mount",
      "auto-mount" in _dtxt_now.lower() or "automount" in _dtxt_now.lower())

txt = open(TOOL).read()
check("tool never invokes a format/partition/burn tool",
      all(t not in txt for t in ("mkfs.", "wipefs ", "parted ", "dd if=", "sgdisk")))
check("tool never writes to a raw device", ">/dev/mm" not in txt and "> /dev/mm" not in txt)

# --- fragment ---------------------------------------------------------------
dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment gives insert and eject owner steps",
      "insert" in dtxt.lower() and "eject" in dtxt.lower())
check("fragment states media is never formatted and data is preserved",
      "never" in dtxt.lower() and "format" in dtxt.lower() and "preserv" in dtxt.lower())
check("fragment warns about internal vs external and NEEDS_OWNER_TEST",
      "INTERNAL_ONLY" in dtxt and "NEEDS_OWNER_TEST" in dtxt)

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for detection/mount logic; NEEDS_OWNER_TEST for a physical card")
