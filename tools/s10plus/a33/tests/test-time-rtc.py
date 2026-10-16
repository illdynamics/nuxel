#!/usr/bin/env python3
"""Offline tests for timekeeping, RTC and timesync (briq-03b, mission area 5).

Proven offline (OFFLINE_TESTED):
  * the diagnostic's verdict is a correct function of observable evidence
    (6 fixtures: no RTC / no timesync backend / clock never set / partial
    evidence / everything agrees);
  * `verify` returns a real non-zero status when a check is genuinely wrong
    (no timesync backend) and 0 when every observable check passes;
  * the mark/compare reboot-persistence arithmetic is correct and REFUSES a
    compare whose boot id did not change (a same-boot pair is not a reboot);
  * the shipped policy, units and drop-ins are self-consistent (timer cadence ==
    rtc.save_interval_min, units contain no clock-writing or partition-writing
    command beyond hwclock systohc, no flashing surface anywhere).

NOT proven here — and therefore NEEDS_OWNER_TEST: that the RTC on the physical
handset actually keeps time across an ordinary reboot.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    return start


ROOT = _repo_root(HERE)
TOOL = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-time.sh")
TIME_DIR = os.path.join(ROOT, "configs", "nuxel", "time")
FIX = os.path.join(HERE, "fixtures-p3")
BASE = 1750000000

fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, root=None, extra=None):
    env = dict(os.environ)
    env["NUXEL_DIAG_NO_SYSTEM"] = "1"
    if root:
        env["NUXEL_DIAG_ROOT"] = root
        env["NUXEL_TIME_POLICY"] = "/etc/nuxel/time/time.json"
    env.update(extra or {})
    return subprocess.run(args, capture_output=True, text=True, env=env)


def verdict(root):
    p = run(["bash", TOOL, "status"], root=root)
    for line in p.stdout.splitlines():
        pass
    out = p.stdout.split("== verdict ==")[-1].strip().splitlines()
    return out[0].split()[0] if out else ""


# 1 ── fixture verdicts -------------------------------------------------------------
p = run(["bash", TOOL, "selftest"])
check("fixtures: all timekeeping verdicts match expectations", p.returncode == 0,
      "rc=%d\n%s" % (p.returncode, p.stdout + p.stderr))

cases = {
    "time-nortc": "RTC_ABSENT",
    "time-nobackend": "NO_TIMESYNC_BACKEND",
    "time-clock-unset": "CLOCK_NOT_SET",
    "time-partial": "PARTIAL_EVIDENCE",
    "time-ok": "CLOCK_OK_UNVERIFIED_PERSISTENCE",
}
for name, expect in cases.items():
    got = verdict(os.path.abspath(os.path.join(FIX, name)))
    check("fixture %s -> %s" % (name, expect), got == expect, "got %s" % got)

# 2 ── verify surfaces real failures and passes observable checks -------------------
# The committed time-ok fixture pins a STATIC RTC epoch, so checking it against
# the real wall clock would rot as real time advances past the drift bound. That
# is a broken test, not a broken device. Materialise a copy whose RTC reads
# "now - 1 s" so the evidence genuinely agrees with the clock at run time; the
# committed fixture is still used verbatim for the (clock-independent) verdict
# checks above.
def materialize_time_ok():
    d = tempfile.mkdtemp(prefix="nuxel-time-ok-")
    dst = os.path.join(d, "root")
    shutil.copytree(os.path.join(FIX, "time-ok"), dst)
    now = int(time.time()) - 1
    rtc = os.path.join(dst, "sys/class/rtc/rtc0")
    open(os.path.join(rtc, "since_epoch"), "w").write("%d\n" % now)
    open(os.path.join(rtc, "date"), "w").write(time.strftime("%Y-%m-%d\n", time.gmtime(now)))
    open(os.path.join(rtc, "time"), "w").write(time.strftime("%H:%M:%S\n", time.gmtime(now)))
    return dst


ok_root = materialize_time_ok()
p = run(["bash", TOOL, "verify"], root=ok_root)
check("verify PASSES every observable check when the evidence agrees",
      p.returncode == 0 and "fail=0" in p.stdout, p.stdout[-400:])
check("verify marks reboot persistence as NEEDS_OWNER_TEST (never a silent PASS)",
      "NEEDS_OWNER_TEST RTC persistence" in p.stdout, p.stdout[-400:])

p = run(["bash", TOOL, "verify"], root=os.path.abspath(os.path.join(FIX, "time-nobackend")))
check("verify FAILS (non-zero) when no timesync backend is active",
      p.returncode != 0 and "FAIL timesync backend active" in p.stdout, p.stdout[-400:])

# json modes are real JSON (the bridge/apps parse them)
p = run(["bash", TOOL, "status", "--json"], root=os.path.abspath(os.path.join(FIX, "time-ok")))
line = [l for l in p.stdout.splitlines() if l.startswith("{")]
check("status --json emits exactly one JSON object", len(line) == 1, p.stdout[-200:])
if line:
    try:
        doc = json.loads(line[0])
        check("status --json carries the device and verdict", doc.get("device") == "beyond2lte" and doc.get("verdict"),
              line[0])
    except Exception as exc:  # noqa: BLE001
        check("status --json parses", False, repr(exc))

# 3 ── mark/compare arithmetic, deterministic --------------------------------------
def build_pair(d, rtc_after, boot_after="boot-after"):
    """A fully faked timekeeping root whose clock advances 3600 s per `date` call."""
    if os.path.isdir(d):
        shutil.rmtree(d)
    for sub in ("sys/class/rtc/rtc0", "proc/sys/kernel/random", "usr/bin",
                "var/lib/nuxel/time", "etc/nuxel/time", "usr/share", "dev"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    shutil.copy2(os.path.join(TIME_DIR, "time.json"), os.path.join(d, "etc/nuxel/time/time.json"))
    open(os.path.join(d, "proc/sys/kernel/random/boot_id"), "w").write("boot-before\n")
    open(os.path.join(d, "sys/class/rtc/rtc0/name"), "w").write("fixture-rtc\n")
    open(os.path.join(d, "sys/class/rtc/rtc0/since_epoch"), "w").write("%d\n" % (BASE + 3600))
    open(os.path.join(d, "usr/share/fixture-clock"), "w").write("0\n")
    open(os.path.join(d, "dev/rtc0"), "w").close()
    fake_date = """#!/bin/sh
# fixture: each call advances the wall clock by 3600 s (deterministic)
c=$(cat "$(dirname "$0")/../share/fixture-clock")
c=$((c + 3600))
echo "$c" > "$(dirname "$0")/../share/fixture-clock"
case "$*" in
  "+%s") echo $((__BASE__ + c)) ;;
  *) exec /bin/date "$@" ;;
esac
""".replace("__BASE__", str(BASE))
    with open(os.path.join(d, "usr/bin/date"), "w") as f:
        f.write(fake_date)
    os.chmod(os.path.join(d, "usr/bin/date"), 0o755)
    return d, rtc_after, boot_after


with tempfile.TemporaryDirectory() as tmp:
    # 3a — RTC advanced with the wall clock: PASS
    d = os.path.join(tmp, "pass")
    build_pair(d, None)
    p = run(["bash", TOOL, "mark"], root=d)
    check("mark writes the pre-reboot RTC reading", p.returncode == 0 and
          os.path.exists(os.path.join(d, "var/lib/nuxel/time/rtc-before.json")), p.stdout[-300:])
    # simulate the reboot: new boot id, RTC advanced by the same 3600 s
    open(os.path.join(d, "proc/sys/kernel/random/boot_id"), "w").write("boot-after\n")
    open(os.path.join(d, "sys/class/rtc/rtc0/since_epoch"), "w").write("%d\n" % (BASE + 7200))
    p = run(["bash", TOOL, "compare"], root=d)
    check("compare PASSES when the RTC advanced with the wall clock",
          p.returncode == 0 and "PASS rtc_epoch advanced by" in p.stdout, p.stdout[-300:])

    # 3b — RTC did not advance at all: FAIL with the numbers, not a vague error
    d = os.path.join(tmp, "fail")
    build_pair(d, None)
    run(["bash", TOOL, "mark"], root=d)
    open(os.path.join(d, "proc/sys/kernel/random/boot_id"), "w").write("boot-after\n")
    p = run(["bash", TOOL, "compare"], root=d)
    check("compare FAILS when the RTC did not advance (drift reported numerically)",
          p.returncode == 1 and "FAIL rtc_epoch advanced by" in p.stdout, p.stdout[-300:])

    # 3c — same boot id: the pair is refused (no reboot happened)
    d = os.path.join(tmp, "sameboot")
    build_pair(d, None)
    run(["bash", TOOL, "mark"], root=d)
    open(os.path.join(d, "sys/class/rtc/rtc0/since_epoch"), "w").write("%d\n" % (BASE + 7200))
    p = run(["bash", TOOL, "compare"], root=d)
    check("compare REFUSES a pair whose boot id did not change",
          "same boot_id" in p.stdout, p.stdout[-300:])

# 4 ── shipped policy / units / drop-ins self-consistency --------------------------
policy = json.load(open(os.path.join(TIME_DIR, "time.json")))
check("policy parses and pins the backend preference",
      policy["timesync"]["preferred"] == "systemd-timesyncd" and policy["timesync"]["fallback"] == "chrony")
check("policy RTC device is auto-detected, never hard-coded",
      policy["rtc"]["device"] == "auto" and policy["rtc"]["sysfs_candidates"])
check("policy keeps environment-dependent package claims behind a probe",
      "chrony" in policy["timesync"]["package_probe"])

timer = open(os.path.join(TIME_DIR, "nuxel-rtc-check.timer")).read()
svc = open(os.path.join(TIME_DIR, "nuxel-rtc-check.service")).read()
interval = "%dmin" % policy["rtc"]["save_interval_min"]
check("timer cadence matches rtc.save_interval_min (%s)" % interval, interval in timer)
check("timer is persistent across missed runs", "Persistent=true" in timer)
check("service runs the console-visible verifier", "ExecStart=/usr/bin/nuxelctl time verify --log" in svc)
check("service is evidence-only (no clock/partition write in the unit)",
      not any(w in svc for w in ("hwclock --hctosys", "dd ", "/dev/block", "mkfs")))
check("service tolerates a recorded finding without failing the boot",
      "SuccessExitStatus=0 1" in svc)

tsd = open(os.path.join(TIME_DIR, "60-nuxel-timesyncd.conf")).read()
chrony = open(os.path.join(TIME_DIR, "nuxel-chrony.conf")).read()
check("timesyncd drop-in sets NTP servers and wider poll bounds",
      "NTP=" in tsd and "PollIntervalMaxSec=2048" in tsd)
check("chrony drop-in is honest about the package check",
      "verif" in chrony.lower() and "repoquery" in chrony)
check("chrony drop-in does not enable an unverified hardware timestamping feature",
      not any(l.strip().startswith("hwtimestamp") for l in chrony.splitlines()))

# 5 ── NO FLASHING invariant -------------------------------------------------------
tool_src = open(TOOL).read()
for pat in ("/dev/block", "dd if=", "heimdall", "fastboot", "flash"):
    check("timekeeping tool has no %r surface" % pat, pat not in tool_src.lower())


# 6 ── the Settings surface, clock permissions, last-known and suspend honesty ----
pol = json.load(open(os.path.join(TIME_DIR, "time.json")))

ss = pol.get("settings_surface", {})
keys = {f.get("key") for f in ss.get("fields", [])}
need = {"auto_time", "auto_timezone", "manual_timezone", "time_format", "ntp_servers", "last_sync"}
check("settings surface covers every required Date & time row", need.issubset(keys), sorted(need - keys))
check("settings surface names its renderer (append point, not a second store)",
      ss.get("renderer", "").startswith("briq-06d"))
atz = [f for f in ss.get("fields", []) if f.get("key") == "auto_timezone"]
check("auto timezone is gated on the location service (never inferred from an IP)",
      bool(atz) and atz[0].get("requires") == "location service enabled")
lz = [f for f in ss.get("fields", []) if f.get("key") == "manual_timezone"]
check("the timezone list is probed from tzdata, never hard-coded",
      bool(lz) and "zoneinfo" in lz[0].get("read_api", ""))
check("last-sync is read-only and never replaced by the boot time",
      bool([f for f in ss.get("fields", []) if f.get("key") == "last_sync"
            and f.get("read_only") is True
            and "never replaced" in f.get("honest_note", "")]))

cp = pol.get("clock_permissions", {})
check("clock permissions state that only root/CAP_SYS_TIME may set the clock",
      "CAP_SYS_TIME" in cp.get("set_time_requires", ""), cp.get("set_time_requires"))
check("clock permissions forbid an unprivileged app or PWA from setting the clock",
      "never" in cp and "PWA" in cp.get("never", ""))
check("the monotonic clock is documented as unaffected by clock steps",
      "CLOCK_MONOTONIC" in cp.get("monotonic", ""))

lk = pol.get("last_known_time", {})
check("last-known records a plausible-after floor and is described as a floor, not a measurement",
      lk.get("plausible_after", "").startswith("2024-") and "floor" in lk.get("uncertainty", ""))
check("a clock earlier than the last-known record is reported RTC_SUSPECT",
      "RTC_SUSPECT" in lk.get("use", ""))

sr = pol.get("suspend_resume", {})
check("suspend support is read from the kernel's own /sys/power/state",
      "/sys/power/state" in sr.get("state_source", ""))
check("suspend/resume never claims a state the kernel does not advertise",
      "not-supported-by-this-kernel" in sr.get("honest_note", ""))
check("suspend/resume timekeeping effect is stated (monotonic pauses, wall clock re-synced)",
      "CLOCK_MONOTONIC" in sr.get("clock_effect", ""))
check("tzdata availability is a probe with a documented missing case",
      "TZDATA_MISSING" in pol.get("tzdata", {}).get("if_missing", ""))

# behavioural: the tool's own surface + the last-known refusal/suspect logic
p = run(["bash", TOOL, "settings"])
check("nuxelctl time settings runs and prints the surface",
      p.returncode == 0 and "Date & time settings surface" in p.stdout, p.stdout[-200:])
check("settings reports the clock-permission requirement",
      "set_time_requires" in p.stdout and "CAP_SYS_TIME" in p.stdout)
check("settings reports suspend support from the kernel, or says UNKNOWN",
      "/sys/power/state" in p.stdout and ("advertised" in p.stdout or "UNKNOWN" in p.stdout))

with tempfile.TemporaryDirectory() as td:
    os.makedirs(os.path.join(td, "var/lib/nuxel/time"), exist_ok=True)
    rec = os.path.join(td, "var/lib/nuxel/time/last-known.json")
    if os.path.exists(rec):
        os.unlink(rec)
    # The host clock is plausible, so this records; the REFUSAL path itself is
    # exercised by the forged future record below (which must report RTC_SUSPECT).
    p = run(["bash", TOOL, "last-known", "--record"], root=td)
    check("last-known --record writes a floor record with an explicit warning",
          os.path.exists(rec) and "floor" in open(rec).read().lower(), p.stdout[-200:])
    # now forge a record in the FUTURE and confirm the tool reports RTC_SUSPECT
    with open(rec, "w") as f:
        json.dump({"schema_version": 1, "observed_epoch": int(time.time()) + 864000,
                   "observed_iso": "2999-01-01T00:00:00Z", "kind": "last-known-lower-bound"}, f)
    p = run(["bash", TOOL, "last-known"], root=td)
    check("a clock earlier than the last-known record is reported RTC_SUSPECT",
          "RTC_SUSPECT" in p.stdout, p.stdout[-200:])
    # a record that does not exist is reported as such, never invented
    os.unlink(rec)
    p = run(["bash", TOOL, "last-known"], root=td)
    check("no record is reported as 'no record yet', never as a fabricated time",
          "no record yet" in p.stdout, p.stdout[-200:])

print("\n== %d failing check(s) ==" % len(fails))
sys.exit(1 if fails else 0)
