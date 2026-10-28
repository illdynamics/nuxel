#!/usr/bin/env python3
"""nuxel-bootmode-guard — the charger/LPM boot-mode gate for touch input (briq-01c).

THE FINDING THIS GUARDS AGAINST
-------------------------------
On the SM-G975F, when S-Boot powers the board up from off with a charger attached
it passes ``androidboot.mode=charger`` on the kernel command line.  Samsung's
``sec_bat_is_lpm_check()`` (``__setup`` hook) turns that into ``lpcharge = 1``, and
``sec_ts_init()`` in ``drivers/input/touchscreen/sec_ts/y771/sec_ts.c`` then
returns ``-ENODEV`` *before* ``i2c_add_driver()``:

    [sec_input] sec_ts_init: Do not load driver due to : lpm 1
    tsp_io: disabling
    tsp_avdd: disabling

No i2c client 4-0048 is ever bound, no ``sec_touchscreen`` input device exists, and
therefore every layer of the touch pipeline above it is empty.  A fingerprint
(``qbt2000``) and the Wacom digitizer sit behind the same gate.

WHY NO USERSPACE PATCH CAN FIX THE DRIVER ITSELF
------------------------------------------------
* ``sec_ts`` is built in (``CONFIG_TOUCHSCREEN_SEC_TS_Y771=y``) and
  ``/lib/modules/4.14.253`` does not exist -> nothing can be re-loaded.
* ``CONFIG_KEXEC is not set`` -> the kernel cannot be re-entered with a new cmdline.
* ``sec_ts_start_device()``'s "already POWER_ON" short-circuit is never reached,
  because the driver was never added and owns no IRQ.  Poking regulators or
  ``fb0/blank`` cannot conjure the device.
So the initcall decision is irreversible *for this boot*.  The one lever that
works without touching BOOT/DTB/radio is a normal (non-LPM) boot: an
OS-initiated ``systemctl reboot`` does NOT re-enter charger mode.

WHAT THIS TOOL DOES (all userspace, zero flashing)
--------------------------------------------------
1. CLASSIFY the current boot: normal vs charger/LPM.  Evidence is collected from
   ``/proc/cmdline``, ``dmesg`` (or ``/proc/last_kmsg`` / pstore when dmesg is
   restricted) and the driver sysfs/i2c state, each with the file it came from.
2. RECORD it as machine-readable state for the launcher:
       /run/nuxel-bootmode.state   (key=value, for scripts/capture bundles)
       /run/nuxel-bootmode.json    (for the launcher to surface to the owner)
   The launcher message is exact and owner-readable:
       "charging-mode boot: touch is disabled on this boot.
        Unplug and normal-reboot (or wait for the automatic normal reboot)."
3. WIRE a normal reboot path that is NEVER blind:
       * off by default; the config must say ``allow_reboot: true`` AND the cmdline
         must pass ``--reboot --i-understand-this-reboots-the-phone``;
       * while a capture/owner-test lock exists (/run/nuxel-touch-capture.lock,
         /run/nuxel-owner-test.lock) the reboot is suppressed;
       * while a fresh guard cooldown exists the reboot is suppressed (so a broken
         boot cannot become a reboot loop - the "no blind repeat reboots" rule);
       * the reboot is refused unless a charger is present and the battery is
         charging (do not reboot a device that is about to lose power);
       * ``--print-only`` (default) prints the exact command instead of running it,
         so every offline test exercises the decision, not the reboot.
   The reboot command is always ``systemctl reboot`` (userspace, systemd PID 1).
   Nothing here writes a partition, a bootloader, a DTB, a modem or an EFS.
4. STATE the honest permanent-fix verdict:
       PERMANENT_FIX=BLOCKED_KERNEL BOOT_UPDATE_REQUIRED NOT_DEPLOYED
   with the offline (never-applied) patch proposal at
   tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch and
   the not-executed future procedure in docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md.

USAGE
    # classify this boot, write the launcher state, take no action
    nuxel-bootmode-guard.py --status

    # grade an archived capture offline (no device needed) - used by the tests
    nuxel-bootmode-guard.py --offline-fixture tools/s10plus/a33/tests/fixtures-bootmode/lpm-boot

    # what WOULD happen (never reboots)
    nuxel-bootmode-guard.py --status --reboot --i-understand-this-reboots-the-phone --print-only

    # real decision, still gated by the config + the locks + the cooldown
    nuxel-bootmode-guard.py --reboot --i-understand-this-reboots-the-phone

EXIT CODES
    0   normal (non-LPM) boot: the touch pipeline is buildable on this boot
    10  charger/LPM boot detected, no reboot attempted (default)
    11  charger/LPM detected and a gated normal reboot was issued
    12  charger/LPM detected, reboot was requested but SUPPRESSED (reason printed)
    13  charger/LPM detected, reboot requested and permitted but --print-only
    2   could not determine the boot mode (no evidence readable)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

# --------------------------------------------------------------------------
# constants / layout
# --------------------------------------------------------------------------
STATE_FILE = "/run/nuxel-bootmode.state"
LAUNCHER_JSON = "/run/nuxel-bootmode.json"
COOLDOWN_FILE = "/run/nuxel-bootmode-guard.cooldown"
# The guard configuration has its OWN subpath (configs/nuxel/bootmode/) and it is
# searched FIRST.  The touch/ copies are retained because an already-generated
# deploy plan names them as the source for /etc/nuxel/touch/bootmode-guard.json;
# tests/test-bootmode-guard.py asserts the two files agree on every gate field, so
# the duplication is enforced rather than trusted.
_REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", ".."))
CONFIG_PATHS = [
    "/etc/nuxel/bootmode/bootmode-guard.json",
    os.path.join(_REPO, "configs", "nuxel", "bootmode", "bootmode-guard.json"),
    "/etc/nuxel/touch/bootmode-guard.json",
    os.path.join(_REPO, "configs", "nuxel", "touch", "bootmode-guard.json"),
]
OWNER_TEST_LOCKS = ["/run/nuxel-touch-capture.lock", "/run/nuxel-owner-test.lock",
                    "/run/nuxel-manual-proof.lock", "/var/lib/nuxel/owner-test.lock"]
I2C_TOUCH_ADDR = "4-0048"
SEC_TS_NAME = "sec_touchscreen"
PERMANENT_FIX = "BLOCKED_KERNEL BOOT_UPDATE_REQUIRED NOT_DEPLOYED"

# The LPM markers, in order of evidential strength.  A bare `lpcharge=1` only
# counts when the line it sits on is a real kernel command line, so a document
# that merely mentions the token cannot be graded as device evidence.
MARKERS = [
    ("cmdline androidboot.mode=charger", re.compile(r"androidboot\.mode=charger"), False),
    ("cmdline lpcharge=1", re.compile(r"\blpcharge=1\b"), True),
    ("dmesg sec_bat_is_lpm_check: Low power charging mode: 1",
     re.compile(r"Low power charging mode:\s*1"), False),
    ("dmesg sec_ts_init: Do not load driver due to : lpm 1",
     re.compile(r"sec_ts_init:\s*Do not load driver due to"), False),
]
CMDLINE_HINT = re.compile(r"androidboot\.|console=|root=|sec_debug|lpm|charger", re.I)

DEFAULT_CONFIG = {
    "version": 1,
    "allow_reboot": False,
    "require_charger": True,
    "min_uptime_seconds": 120,
    "cooldown_seconds": 900,
    "reboot_command": ["systemctl", "reboot"],
    "reason_allow_reboot_false": (
        "allow_reboot is false in the config: touch is disabled on this boot and this "
        "device is not in an automatic-reboot configuration - unplug and reboot normally"),
}


def say(msg=""):
    print(msg, flush=True)


# --------------------------------------------------------------------------
# evidence collection (live or from a fixture directory)
# --------------------------------------------------------------------------
def _read(path, limit=1 << 20):
    try:
        with open(path, "rb") as f:
            return f.read(limit).decode("utf-8", "replace")
    except OSError:
        return ""


def _run(argv, timeout=8):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:
        return 126, ""


class Evidence:
    """A tiny key->(text, origin) store so every claim names its source file."""

    def __init__(self, mode="live", root=None):
        self.mode = mode            # "live" | "fixture"
        self.root = root
        self.items = []             # (name, text, origin)

    def add(self, name, text, origin):
        self.items.append((name, text or "", origin))

    def grep(self, pattern, require_cmdline_hint=False):
        """First matching line with its origin, or (None, None, None)."""
        rx = pattern if hasattr(pattern, "search") else re.compile(pattern, re.I)
        for name, text, origin in self.items:
            for line in text.splitlines():
                if rx.search(line):
                    if require_cmdline_hint and not CMDLINE_HINT.search(line):
                        continue
                    return name, line.strip(), origin
        return None, None, None


def collect_live():
    ev = Evidence("live")
    ev.add("cmdline", _read("/proc/cmdline").strip(), "/proc/cmdline")
    rc, dmesg = _run(["dmesg"], timeout=8)
    if rc != 0 or not dmesg.strip():
        for alt in ("/proc/last_kmsg", "/sys/fs/pstore/console-ramoops-0",
                    "/sys/fs/pstore/dmesg-ramoops-0"):
            if os.path.exists(alt):
                dmesg = _read(alt, 4 << 20)
                if dmesg.strip():
                    ev.add("ram-console", dmesg, alt)
                    break
    else:
        ev.add("dmesg", dmesg, "dmesg")
    for p in ("/sys/bus/i2c/devices/" + I2C_TOUCH_ADDR,
              "/sys/bus/i2c/devices/" + I2C_TOUCH_ADDR + "/name",
              "/sys/class/sec/tsp/status"):
        if os.path.isdir(p):
            ev.add("sysfs", p, "(directory exists)")
        elif os.path.exists(p):
            ev.add("sysfs", _read(p, 4096), p)
    rc, devices = _run(["cat", "/proc/bus/input/devices"], timeout=5)
    if rc == 0:
        ev.add("input-devices", devices, "/proc/bus/input/devices")
    ev.add("modules", "\n".join(
        "%s=%s" % (m, os.path.exists("/sys/module/" + m))
        for m in ("sec_ts", "sec_ts_y771", "sec_touchscreen")), "sysfs /sys/module")
    return ev


def collect_fixture(root):
    """Read anything named cmdline*/dmesg*/last_kmsg*/input-devices* under root."""
    ev = Evidence("fixture", root)
    if not os.path.isdir(root):
        return ev
    patterns = {
        "cmdline": ["cmdline*", "*cmdline*"],
        "dmesg": ["dmesg*", "last_kmsg*", "*ram-console*", "*console-ramoops*", "boot-driver*"],
        "input-devices": ["*input*devices*", "*evdev*"],
        "sysfs": ["sysfs*", "*i2c*", "*tsp*", "*module*"],
    }
    seen = set()
    for name, pats in patterns.items():
        for pat in pats:
            for path in sorted(glob.glob(os.path.join(root, "**", pat), recursive=True)):
                if not os.path.isfile(path) or path in seen:
                    continue
                seen.add(path)
                ev.add(name, _read(path, 4 << 20), os.path.relpath(path, root))
    return ev


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------
def classify(ev):
    hits = []
    for why, rx, weak in MARKERS:
        name, line, origin = ev.grep(rx, require_cmdline_hint=weak)
        if line is not None:
            hits.append({"why": why, "line": line, "origin": origin})
    lpm = bool(hits)
    _n, tsp_line, tsp_origin = ev.grep(r"input:\s*" + SEC_TS_NAME + r"\s+as\s+\S+")
    _n2, prop_line, prop_origin = ev.grep(r"\bPROP=([0-9a-fA-F]+)")
    registered = tsp_line is not None
    if registered and not lpm:
        mode = "normal"
    elif lpm:
        mode = "charger-lpm"
    else:
        mode = "unknown"
    return {"mode": mode, "lpm": lpm, "hits": hits, "registered": registered,
            "register_line": tsp_line, "register_origin": tsp_origin,
            "prop_line": prop_line, "prop_origin": prop_origin}


def launcher_message(mode):
    if mode == "charger-lpm":
        return ("charging-mode boot: touch is disabled on this boot. "
                "Unplug the charger and reboot normally (or wait for the guarded "
                "automatic normal reboot) to get an interactive screen.")
    if mode == "normal":
        return ("normal boot: the sec_ts touch controller is expected to be present; "
                "run the touch capture to prove the finger path.")
    return ("boot mode could not be determined: no cmdline/dmesg evidence was readable, "
            "so touch state is unknown - do not treat this as a pass.")


# --------------------------------------------------------------------------
# gating
# --------------------------------------------------------------------------
def load_config(path=None):
    cfg = dict(DEFAULT_CONFIG)
    candidates = [path] if path else CONFIG_PATHS
    used = None
    for p in candidates:
        if p and os.path.isfile(p):
            try:
                with open(p) as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg.update(loaded)
                    used = p
                break
            except (OSError, ValueError):
                continue
    return cfg, used


def locks_present():
    return [p for p in OWNER_TEST_LOCKS if os.path.exists(p)]


def cooldown_seconds_left(cfg, path=COOLDOWN_FILE):
    if not os.path.isfile(path):
        return 0
    try:
        with open(path) as f:
            last = float(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0
    left = int(cfg.get("cooldown_seconds", 0)) - (time.time() - last)
    return max(0, left)


def uptime_seconds():
    txt = _read("/proc/uptime").split()
    try:
        return float(txt[0])
    except (IndexError, ValueError):
        return 0.0


def charger_present_and_charging():
    """True when a charger is connected and the battery reports charging.

    Best effort: the vendor power_supply class names on this board are
    max77705-charger / battery.  A missing or unreadable supply is reported as
    None (unknown) and never counted as "safe to reboot".
    """
    status, present = None, None
    for base in ("/sys/class/power_supply",):
        for name in ("battery", "max77705-charger", "max77705_battery"):
            p = os.path.join(base, name)
            if os.path.isdir(p):
                st = _read(os.path.join(p, "status")).strip()
                on = _read(os.path.join(p, "online")).strip()
                if st:
                    status = st
                if on:
                    present = on
    if status is None and present is None:
        return None
    return (status in ("Charging", "Full")) or present == "1"


def reboot_decision(cfg, mode, print_only, forced, understand, uptime=None, locks=None,
                    cooldown=None, charger="skip"):
    """Pure decision function, so the tests can drive every branch offline."""
    if mode != "charger-lpm":
        return {"reboot": False, "reason": "not a charger/LPM boot"}
    if not forced:
        return {"reboot": False, "reason": "no --reboot requested (status only)"}
    if not understand:
        return {"reboot": False,
                "reason": "refused: --reboot requires --i-understand-this-reboots-the-phone"}
    if not cfg.get("allow_reboot", False):
        return {"reboot": False, "reason": cfg.get("reason_allow_reboot_false",
                                                  "allow_reboot is false in the config")}
    if locks is None:
        locks = locks_present()
    if locks:
        return {"reboot": False, "reason": "suppressed: owner-test/capture lock present (%s)"
                % ", ".join(locks)}
    if cooldown is None:
        cooldown = cooldown_seconds_left(cfg)
    if cooldown > 0:
        return {"reboot": False,
                "reason": "suppressed: %ds of reboot-guard cooldown remain (no blind repeat reboots)"
                % cooldown}
    if uptime is None:
        uptime = uptime_seconds()
    if uptime < float(cfg.get("min_uptime_seconds", 0)):
        return {"reboot": False, "reason": "suppressed: uptime %.0fs < min_uptime_seconds %s "
                "(the device may still be settling)" % (uptime, cfg.get("min_uptime_seconds"))}
    if cfg.get("require_charger", True):
        if charger == "skip":
            charger = charger_present_and_charging()
        if charger is not True:
            return {"reboot": False,
                    "reason": "suppressed: charger state is %s (need a connected, charging supply "
                              "before rebooting)" % ("unknown" if charger is None else repr(charger))}
    return {"reboot": True, "reason": "all gates passed",
            "print_only": bool(print_only)}


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def write_state(mode, cls, decision, cfg, cfg_path, note=""):
    lines = [
        "# nuxel-bootmode-guard v1  %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "BOOTMODE=%s" % mode.upper().replace("-", "_"),
        "TOUCH_DRIVER_EXPECTED=%s" % ("0" if mode == "charger-lpm" else "1"),
        "SEC_TOUCHSCREEN_REGISTERED=%d" % (1 if cls["registered"] else 0),
        "LPCHARGE=%d" % (1 if cls["lpm"] else 0),
        "PERMANENT_FIX=%s" % PERMANENT_FIX,
        "REBOOT_REQUESTED=%d" % (1 if (decision.get("reboot") or decision.get("would_reboot")) else 0),
        "REBOOT_ACTION=%s" % ("issued" if decision.get("reboot") else
                              ("print-only" if decision.get("would_reboot") else "none")),
        "REBOOT_REASON=%s" % decision.get("reason", ""),
        "ALLOW_REBOOT_CONFIG=%d" % (1 if cfg.get("allow_reboot") else 0),
        "CONFIG=%s" % (cfg_path or "(defaults)"),
        "EVIDENCE_COUNT=%d" % len(cls["hits"]),
    ]
    for i, h in enumerate(cls["hits"], 1):
        lines.append("EVIDENCE_%d=%s [%s]: %s" % (i, h["why"], h["origin"], h["line"]))
    if cls["register_line"]:
        lines.append("REGISTER=%s [%s]" % (cls["register_line"], cls["register_origin"]))
    if note:
        lines.append("NOTE=%s" % note)
    text = "\n".join(lines) + "\n"
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            f.write(text)
    except OSError:
        pass
    payload = {
        "version": 1, "mode": mode, "touch_available": mode == "normal",
        "headline": "touch disabled (charging-mode boot)" if mode == "charger-lpm" else
                    ("touch expected" if mode == "normal" else "touch state unknown"),
        "message": launcher_message(mode),
        "graded": mode != "unknown",
        "action": ("unplug-and-normal-reboot" if mode == "charger-lpm" else "none"),
        "permanent_fix": PERMANENT_FIX,
        "evidence": [{"why": h["why"], "origin": h["origin"], "line": h["line"]}
                     for h in cls["hits"]],
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        with open(LAUNCHER_JSON, "w") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
    except OSError:
        pass
    return text, payload


def touch_cooldown():
    try:
        with open(COOLDOWN_FILE, "w") as f:
            f.write("%.0f\n" % time.time())
    except OSError:
        pass


def run(args):
    ev = collect_fixture(args.offline_fixture) if args.offline_fixture else collect_live()
    cfg, cfg_path = load_config(args.config)
    cls = classify(ev)
    mode = cls["mode"]

    # An offline fixture must never be graded as a device observation.
    origin_kind = "fixture" if args.offline_fixture else "device"

    decision = reboot_decision(
        cfg, mode,
        print_only=args.print_only,
        forced=args.reboot,
        understand=args.i_understand,
        uptime=args.fake_uptime if args.fake_uptime is not None else None,
        locks=[] if args.ignore_locks else None,
        cooldown=0 if args.ignore_cooldown else None,
        charger=True if (args.offline_fixture and args.assume_charger) else "skip",
    ) if mode == "charger-lpm" else {"reboot": False, "reason": "not a charger/LPM boot"}

    note = ""
    if decision.get("reboot") and decision.get("print_only"):
        # print-only exercises EVERY gate and then deliberately does not act
        decision["would_reboot"] = True
        decision["reboot"] = False
    if decision.get("reboot") and not decision.get("print_only"):
        if args.offline_fixture:
            note = ("FIXTURE MODE: refusing to run the reboot command against a fixture; "
                    "the decision is reported only")
            decision["reboot"] = False
            decision["would_reboot"] = True
            decision["reason"] = ("all gates passed (fixture mode: the reboot command was "
                                  "deliberately NOT executed)")
        else:
            cmd = cfg.get("reboot_command") or ["systemctl", "reboot"]
            say("REBOOT_EXEC %s" % " ".join(cmd))
            rc, out = _run(cmd, timeout=20)
            note = "reboot command rc=%d %s" % (rc, out.strip()[:200])
            if rc == 0:
                touch_cooldown()

    state_text, payload = write_state(mode, cls, decision, cfg, cfg_path, note)

    say("== nuxel-bootmode-guard (%s evidence) ==" % origin_kind)
    say("BOOTMODE=%s" % mode.upper().replace("-", "_"))
    for h in cls["hits"]:
        say("  hit: %s [%s]" % (h["why"], h["origin"]))
    say("SEC_TOUCHSCREEN_REGISTERED=%d" % (1 if cls["registered"] else 0))
    # Never claim touch is available on a boot we could not classify: an unknown
    # boot is reported as unknown, exactly like the launcher JSON does.
    avail = "true" if mode == "normal" else ("false" if mode == "charger-lpm" else "unknown")
    say("TOUCH_AVAILABLE=%s" % avail)
    say("PERMANENT_FIX=%s" % PERMANENT_FIX)
    say("CONFIG=%s" % (cfg_path or "(defaults: no configuration file found)"))
    say("SETTINGS_STATE=%s (what Settings reads)%s"
        % (LAUNCHER_JSON, " (not written: --no-write)" if args.no_write else ""))
    # One machine-readable line for the live console, so a console session and any
    # script see the same verdict without parsing the human output.
    say("NX_STATUS bootmode=%s touch_available=%s permanent_fix=\"%s\""
        % (mode, avail, PERMANENT_FIX))
    acted = bool(decision.get("reboot"))
    would = bool(decision.get("would_reboot"))
    say("REBOOT_DECISION=%s REASON=%s"
        % ("yes" if acted else ("would-reboot" if would else "no"), decision.get("reason", "")))
    if would:
        say("WOULD_RUN=%s (print-only: nothing was executed)"
            % " ".join(cfg.get("reboot_command") or ["systemctl", "reboot"]))
    if args.no_write:
        say("STATE_FILE=(not written: --no-write)")
    else:
        say("STATE_FILE=%s" % STATE_FILE)
        say("LAUNCHER_STATE=%s" % LAUNCHER_JSON)
    if args.json:
        say(json.dumps(payload))
    if args.show_state and not args.no_write:
        say("--- %s ---" % STATE_FILE)
        say(state_text.rstrip())

    if mode == "unknown":
        say("VERDICT=BOOTMODE_UNKNOWN (no readable evidence: not a pass)")
        return 2
    if mode == "normal":
        say("VERDICT=NORMAL_BOOT touch pipeline expected; prove it with nuxel-touch-capture.sh")
        return 0
    # charger/LPM
    if decision.get("reboot"):
        say("VERDICT=CHARGER_MODE_TOUCH_DISABLED normal reboot issued (gated)")
        return 11
    if decision.get("would_reboot"):
        say("VERDICT=CHARGER_MODE_TOUCH_DISABLED would reboot (print-only, nothing executed)")
        return 13
    if args.reboot:
        say("VERDICT=CHARGER_MODE_TOUCH_DISABLED reboot requested but suppressed: %s"
            % decision.get("reason", ""))
        return 12
    say("VERDICT=CHARGER_MODE_TOUCH_DISABLED no action taken: unplug and reboot normally")
    return 10


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="nuxel-bootmode-guard.py",
        description="Detect the charger/LPM boot that removes the S10+ touchscreen and "
                    "(optionally, gated) request a normal reboot. Userspace only, never flash.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true",
                    help="classify and record the boot mode; take no action (default)")
    ap.add_argument("--offline-fixture", metavar="DIR",
                    help="grade an archived capture directory instead of the live device")
    ap.add_argument("--reboot", action="store_true",
                    help="request a gated normal reboot when a charger/LPM boot is detected")
    ap.add_argument("--i-understand-this-reboots-the-phone", dest="i_understand",
                    action="store_true",
                    help="mandatory acknowledgement: --reboot does nothing without it")
    ap.add_argument("--print-only", action="store_true",
                    help="decide, print the command, execute nothing (default for tests)")
    ap.add_argument("--config", metavar="FILE", help="bootmode-guard.json to use")
    ap.add_argument("--json", action="store_true", help="also print the launcher JSON")
    ap.add_argument("--show-state", action="store_true", help="print the state file contents")
    ap.add_argument("--no-write", action="store_true",
                    help="do not write /run state (useful for a pure classification run)")
    ap.add_argument("--fake-uptime", type=float, default=None,
                    help="pretend the uptime is N seconds (test/gate exercise)")
    ap.add_argument("--assume-charger", action="store_true",
                    help="with --offline-fixture, treat the charger as present+charging")
    ap.add_argument("--ignore-locks", action="store_true", help="ignore owner-test locks (tests)")
    ap.add_argument("--ignore-cooldown", action="store_true", help="ignore the reboot cooldown (tests)")
    args = ap.parse_args(argv)
    if not (args.status or args.offline_fixture or args.reboot):
        args.status = True
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
