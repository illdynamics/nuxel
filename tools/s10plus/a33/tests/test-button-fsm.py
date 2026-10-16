#!/usr/bin/env python3
"""Offline tests for the S10+ hardware-button and screen-gesture state machine
(briq-03e, mission areas 16/17/20).

WHAT IS ACTUALLY PROVEN HERE
  1. The REAL state machine runs offline. The test compiles nuxel-button-fsm.h
     with -DNUXEL_FSM_MAIN and replays recorded event traces through it; it never
     re-implements the logic in Python, so a passing test means the shipped C is
     what behaves. (When no C compiler is present the replay legs are reported
     SKIP, and the run is explicitly marked partial - never silently green.)
  2. JSON <-> C <-> A32 parity. Every timing window is cross-checked three ways:
     configs/nuxel/input/button-fsm.json, the NUXEL_FSM_* defines, and the
     PROTECTED A32 source (tools/s10plus/a32/nuxel-button-manager.c). A change to
     one that is not mirrored in the others fails.
  3. The A32 baseline is untouched: the pinned hashes from
     docs/beta-finalization/baseline-protection.json (INV-4) still match.
  4. The NO FLASHING invariant is enforced in code: the power menu carries
     Recovery and Download-Mode entries that are refused at execution, and the
     manager contains no flashing surface at all.
  5. The menu the daemon shows equals the menu the spec documents.

A passing run is OFFLINE_TESTED (plus VERIFIED_IN_VM_ONLY for the build leg when
it is compiled on the UTM Fedora 43 aarch64 guest). It is NOT
VERIFIED_ON_S10PLUS: no button on a real handset was pressed by this test.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)


def _repo_root(start):
    """Walk up to the directory that owns configs/ and docs/ - never guess a
    fixed depth, so the test survives a relocated tree."""
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(os.path.dirname(A33))


ROOT = _repo_root(HERE)
SPEC = os.path.join(ROOT, "configs", "nuxel", "input", "button-fsm.json")
GATE_SPEC = os.path.join(ROOT, "configs", "nuxel", "buttons", "reboot-gate.json")
FSM_H = os.path.join(A33, "nuxel-button-fsm.h")
MANAGER_C = os.path.join(A33, "nuxel-button-manager.c")
SERVICE = os.path.join(A33, "nuxel-button-manager.service")
A32_C = os.path.join(ROOT, "tools", "s10plus", "a32", "nuxel-button-manager.c")
A32_SVC = os.path.join(ROOT, "tools", "s10plus", "a32", "nuxel-button-manager.service")
BUTTONS_JSON = os.path.join(ROOT, "configs", "nuxel", "buttons.json")
REGISTER = os.path.join(ROOT, "docs", "beta-finalization", "baseline-protection.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "system", "BUTTONS-GESTURES.md")
FIX = os.path.join(HERE, "fixtures-p3", "button-fsm")

fails, skips = [], []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" - " + str(detail)) if (detail and not ok) else ""))
    if not ok:
        fails.append(name)


def skip(name, why):
    print("SKIP %s (%s)" % (name, why))
    skips.append(name)


def read(p):
    with open(p) as f:
        return f.read()


# --------------------------------------------------------------------------- #
# 1. JSON <-> C constant parity
# --------------------------------------------------------------------------- #
spec = json.load(open(SPEC))
gate_spec = json.load(open(GATE_SPEC))
header = read(FSM_H)
manager = read(MANAGER_C)

defines = {m.group(1): int(m.group(2)) for m in
           re.finditer(r"#define\s+(NUXEL_FSM_[A-Z0-9_]+)\s+(\d+)\b", header)}
check("header defines the FSM constants", len(defines) > 20, len(defines))

pc = spec["press_classes"]
json_to_define = {
    "POWER_DEBOUNCE_MS": pc["power"]["debounce_ms"],
    "POWER_SHORT_MAX_MS": pc["power"]["short_max_ms"],
    "POWER_LONG_MIN_MS": pc["power"]["long_min_ms"],
    "POWER_VERY_LONG_MIN_MS": pc["power"]["very_long_min_ms"],
    "POWER_DOUBLE_GAP_MS": pc["power"]["double_gap_ms"],
    "BIXBY_DEBOUNCE_MS": pc["bixby"]["debounce_ms"],
    "BIXBY_SHORT_MAX_MS": pc["bixby"]["short_max_ms"],
    "BIXBY_LONG_MIN_MS": pc["bixby"]["long_min_ms"],
    "BIXBY_DOUBLE_GAP_MS": pc["bixby"]["double_gap_ms"],
    "VOLUME_DEBOUNCE_MS": pc["volume"]["debounce_ms"],
    "VOLUME_REPEAT_DELAY_MS": pc["volume"]["repeat_delay_ms"],
    "VOLUME_REPEAT_INTERVAL_MS": pc["volume"]["repeat_interval_ms"],
    "VOLUME_STEP_DIVISOR": spec["volume_step"]["divisor"],
    "VOLUME_STEP_MIN": spec["volume_step"]["min_step"],
    "EDGE_ZONE_PX": spec["gestures"]["geometry"]["edge_zone_px"],
    "BOTTOM_ZONE_PX": spec["gestures"]["geometry"]["bottom_zone_px"],
    "MIN_TRAVEL_PX": spec["gestures"]["geometry"]["min_travel_px"],
    "HOLD_MAX_DRIFT_PX": spec["gestures"]["geometry"]["hold_max_drift_px"],
    "DEFAULT_AXIS_MAX_X": spec["gestures"]["geometry"]["default_axis_max"]["x"],
    "DEFAULT_AXIS_MAX_Y": spec["gestures"]["geometry"]["default_axis_max"]["y"],
    "SWIPE_MAX_MS": spec["gestures"]["timing"]["swipe_max_ms"],
    "HOLD_MS": spec["gestures"]["timing"]["hold_ms"],
    "EDGE_BACK_MAX_MS": spec["gestures"]["timing"]["edge_back_max_ms"],
    "STALE_TRACK_MS": spec["gestures"]["timing"]["stale_track_ms"],
    "MENU_TIMEOUT_MS": spec["power_menu"]["timeout_ms"],
    "REBOOT_MIN_INTERVAL_S": gate_spec["min_interval_s"],
    "REBOOT_MAX_PER_HOUR": gate_spec["max_reboots_per_hour"],
    "KEY_POWER": spec["device"]["measured_keys"]["KEY_POWER"],
    "KEY_VOLUMEUP": spec["device"]["measured_keys"]["KEY_VOLUMEUP"],
    "KEY_VOLUMEDOWN": spec["device"]["measured_keys"]["KEY_VOLUMEDOWN"],
    "KEY_BIXBY": spec["device"]["measured_keys"]["KEY_BIXBY_assistant"],
}
for k, want in sorted(json_to_define.items()):
    got = defines.get("NUXEL_FSM_" + k)
    check("JSON == C: NUXEL_FSM_%s = %s" % (k, want), got == want, "C says %s" % got)

# --------------------------------------------------------------------------- #
# 2. A32 parity: the protected behaviour must be byte-for-byte in spirit
# --------------------------------------------------------------------------- #
a32 = read(A32_C)
check("A32 source is the reference implementation of the press windows",
      "held >= 30 && held < 2000" in a32 and "(now_ms - power_down_ms) >= 2000" in a32)
check("A32 parity: power short window (30 ms .. 2000 ms)",
      defines["NUXEL_FSM_POWER_DEBOUNCE_MS"] == 30 and defines["NUXEL_FSM_POWER_SHORT_MAX_MS"] == 2000)
check("A32 parity: power long threshold (2000 ms)",
      defines["NUXEL_FSM_POWER_LONG_MIN_MS"] == 2000 and ">= 2000 && !power_used" in a32)
check("A32 parity: bixby short window (20 ms .. 1500 ms)",
      defines["NUXEL_FSM_BIXBY_DEBOUNCE_MS"] == 20 and
      defines["NUXEL_FSM_BIXBY_SHORT_MAX_MS"] == 1500 and "held >= 20 && held < 1500" in a32)
check("A32 parity: bixby long threshold (1500 ms)",
      defines["NUXEL_FSM_BIXBY_LONG_MIN_MS"] == 1500 and ">= 1500 && !bixby_used" in a32)
check("A32 parity: volume autorepeat cadence (400 ms then 250 ms)",
      defines["NUXEL_FSM_VOLUME_REPEAT_DELAY_MS"] == 400 and
      defines["NUXEL_FSM_VOLUME_REPEAT_INTERVAL_MS"] == 250 and
      "now_ms + 400" in a32 and "now_ms + 250" in a32)
check("A32 parity: volume step = 5 % of the range (range / 20, floored at 1)",
      defines["NUXEL_FSM_VOLUME_STEP_DIVISOR"] == 20 and "(vol_max - vol_min) / 20" in a32)
check("A32 parity: assistant key code 703", defines["NUXEL_FSM_KEY_BIXBY"] == 703 and "703" in a32
      or "KEY_BIXBY 0x2bf" in a32)

# 2b. the protected A32 artefacts themselves are untouched (register hashes)
if os.path.exists(REGISTER):
    reg = json.load(open(REGISTER))
    inv4 = [i for i in reg.get("invariants", []) if i.get("id") == "INV-4-button-manager"]
    check("baseline register still has INV-4-button-manager", len(inv4) == 1)
    if inv4:
        for f in inv4[0]["files"]:
            p = os.path.join(ROOT, f["path"])
            if not os.path.exists(p):
                check("protected A32 file exists: %s" % f["path"], False)
                continue
            got = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if f["hash_mode"] == "hard" and f["path"].endswith((".c", ".service")):
                check("A32 protected asset unchanged: %s" % f["path"], got == f["sha256"],
                      "expected %s got %s" % (f["sha256"][:12], got[:12]))
            else:
                # soft-pinned shared file: report drift, do not fail the group on it
                print("INFO soft-pinned %s %s" % ("unchanged" if got == f["sha256"] else "drifted", f["path"]))
else:
    skip("A32 register hashes", "register absent")

# --------------------------------------------------------------------------- #
# 3. source hygiene / invariants that must hold in the shipped code
# --------------------------------------------------------------------------- #
check("manager never assumes a fixed /dev/input/eventN",
      not re.search(r'"/dev/input/event[0-9]', manager) and
      "/dev/input" in manager and "opendir" in manager)
check("manager selects the key device by capability",
      "dev_has_key(fd, KEY_POWER)" in manager and "EVIOCGBIT(EV_KEY" in manager)
check("manager selects the touch device by capability and DIRECT property",
      "ABS_MT_POSITION_X" in manager and "INPUT_PROP_DIRECT" in manager)
check("manager never grabs the touchscreen (no EVIOCGRAB -> libinput keeps its events)",
      "EVIOCGRAB" not in manager)
banned = [r"\bheimdall\b", r"\bodin\b", r"fastboot", r"/dev/block", r"\bdd if=",
          r"sysrq-trigger", r"reboot\s+-f", r"write to raw partition"]
for pat in banned:
    hits = re.findall(pat, manager, re.I)
    check("manager has no flashing/bootloader surface for %r" % pat, not hits, hits)
check("manager refuses Recovery and Download Mode in code",
      "NO_FLASH_INVARIANT" in manager and "enter-recovery" in manager and
      "enter-download-mode" in manager and "MENU_REFUSED" in manager)
check("every reboot/power-off goes through the gate (single chokepoint)",
      manager.count("gated_system_action") >= 3 and "nuxel_fsm_gate_decide" in manager and
      "systemctl" in manager and "execl(\"/usr/bin/systemctl\"" in manager)
check("service unit exists and is restart-guarded",
      os.path.exists(SERVICE) and "Restart=" in read(SERVICE) and
      "ExecStart=" in read(SERVICE) if os.path.exists(SERVICE) else False)
if os.path.exists(SERVICE):
    svc = read(SERVICE)
    check("service unit starts the A33 manager binary", "nuxel-button-manager" in svc)
    check("service unit documents the single-owner rule for gpio_keys",
          "gpio_keys" in svc or "single" in svc.lower())

# --------------------------------------------------------------------------- #
# 4. compile + replay: drive the REAL state machine
# --------------------------------------------------------------------------- #
cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
sim = None
if not cc:
    skip("FSM replay (compile nuxel-button-fsm.h)", "no C compiler on this host")
else:
    tmpd = tempfile.mkdtemp(prefix="nuxel-fsm-")
    sim = os.path.join(tmpd, "fsm-sim")
    p = subprocess.run([cc, "-std=c11", "-O1", "-DNUXEL_FSM_MAIN", "-x", "c", FSM_H, "-o", sim],
                       capture_output=True, text=True)
    check("the FSM core compiles standalone (no libasound, no linux/input.h)",
          p.returncode == 0 and os.path.exists(sim), p.stderr[-400:])

if sim:
    dump = subprocess.run([sim, "--menu-dump"], capture_output=True, text=True).stdout
    consts = {}
    for line in dump.splitlines():
        m = re.match(r"^([A-Z0-9_]+) (-?\d+)$", line)
        if m:
            consts[m.group(1)] = int(m.group(2))
    mism = {k: (v, defines.get("NUXEL_FSM_" + k))
            for k, v in consts.items() if ("NUXEL_FSM_" + k) in defines and defines["NUXEL_FSM_" + k] != v}
    check("sim binary agrees with the header constants", not mism, mism)
    check("sim computes the A32 volume step (5 % of range, floored at 1)",
          consts.get("VOLUME_STEP_RANGE100") == 5 and consts.get("VOLUME_STEP_RANGE31") == 1, consts)

    entries = [m.group(1) for m in re.finditer(r"^ENTRY \d+ (\S+) ", dump, re.M)]
    check("menu table in C == menu entries in button-fsm.json",
          entries == [e["id"] for e in spec["power_menu"]["entries"]], entries)
    allowed = dict((m.group(1), int(m.group(2))) for m in
                   re.finditer(r"^ENTRY \d+ (\S+) allowed=(\d)", dump, re.M))
    for e in spec["power_menu"]["entries"]:
        check("menu entry %r allowed=%d matches the spec" % (e["id"], int(e["trigger_allowed"])),
              allowed.get(e["id"]) == int(e["trigger_allowed"]))
    for must_refuse in ("recovery", "download-mode"):
        check("menu entry %r can never be triggered" % must_refuse, allowed.get(must_refuse) == 0)
    check("the refused bootloader entries are labelled with the invariant",
          "NO_FLASH_INVARIANT" in dump)

    traces = sorted(f for f in os.listdir(FIX) if f.endswith(".trace"))
    check("there are recorded event traces to replay", len(traces) >= 10, traces)
    all_actions = []
    for t in traces:
        name = t[:-len(".trace")]
        exp_path = os.path.join(FIX, name + ".expected")
        p = subprocess.run([sim, os.path.join(FIX, t)], capture_output=True, text=True)
        got = [m.group(1) for m in re.finditer(r"^ACTION t=\d+ name=(.+)$", p.stdout, re.M)]
        all_actions += got
        exp = [l.strip() for l in read(exp_path).splitlines() if l.strip()] if os.path.exists(exp_path) else None
        check("replay %s -> %s" % (name, exp), got == exp, "got %s" % got)

    check("no fixture ever dispatches a bootloader entry",
          not any(a in ("enter-recovery", "enter-download-mode") for a in all_actions), all_actions)
    check("the gated reboot class is reachable but marked as a request, not an action",
          "reboot-request" in all_actions)

    # ---- reboot gate legs (the gate is the only thing that decides) --------
    def gate(args):
        p = subprocess.run([sim, "--gate"] + args, capture_output=True, text=True)
        return p.stdout.strip()

    check("gate refuses when disabled",
          "decide=REFUSE reason=gate-disabled" in gate(["enabled=0", "restart=1", "rollback=1"]))
    check("gate refuses without a rollback path",
          "no-rollback-path" in gate(["enabled=1", "restart=1", "rollback=0", "journal=1"]))
    check("gate refuses when the minimum interval has not elapsed",
          "min-interval-not-elapsed" in gate(["enabled=1", "restart=1", "rollback=1", "journal=1",
                                              "last=999000"]))
    check("gate refuses when the hourly cap is reached",
          "hourly-cap-reached" in gate(["enabled=1", "restart=1", "rollback=1", "journal=1",
                                        "perhour=1"]))
    check("gate refuses when bg-09's policy denies the reboot",
          "policy-denies-reboot" in gate(["enabled=1", "restart=1", "rollback=1", "journal=1",
                                          "policy=0"]))
    check("gate allows only when every condition holds",
          "decide=ALLOW reason=allowed" in gate(["enabled=1", "restart=1", "rollback=1",
                                                 "journal=1", "policy=1"]))
    check("power-off is refused unless it is separately allowed",
          "poweroff-not-allowed" in gate(["enabled=1", "restart=1", "rollback=1", "journal=1",
                                          "poweroff=0", "action=poweroff"]))
    check("the shipped gate config is CLOSED by default (owner absent)",
          gate_spec["enabled"] is False and gate_spec["allow_restart"] is False
          and gate_spec["allow_poweroff"] is False)
    check("the shipped gate forbids the unsafe execution paths",
          "sysrq" in json.dumps(gate_spec) and "reboot -f" in json.dumps(gate_spec))

# --------------------------------------------------------------------------- #
# 5. documentation + spec completeness
# --------------------------------------------------------------------------- #
check("buttons.json (A32, owner-remappable) still maps bixby_short -> an action",
      '"bixby_short": "open-terminal"' in read(BUTTONS_JSON))
check("buttons.json still maps power_short -> screen-toggle (A32 invariant)",
      '"power_short": "screen-toggle"' in read(BUTTONS_JSON))
check("the FSM spec declares gestures for home/recents/back",
      [r["action"] for r in spec["gestures"]["recognizers"]] == ["back", "home", "recents"])
check("the FSM spec documents that the touch node is never grabbed",
      spec["input_selection"]["touch_device"]["grab"] is False)
check("the FSM spec forbids the rebound of an owner remap by the FSM defaults",
      "buttons.json" in spec["actions"]["comment"])
if os.path.exists(DOC):
    d = read(DOC)
    for want in ["Power", "Volume", "Bixby", "Recovery", "Download Mode", "swipe", "edge",
                 "NEEDS_OWNER_TEST", "NO FLASHING", "eventN"]:
        check("BUTTONS-GESTURES.md covers %r" % want, want.lower() in d.lower())
else:
    check("BUTTONS-GESTURES.md exists", False, DOC)

print("\n== %d failing check(s), %d skipped leg(s) ==" % (len(fails), len(skips)))
if skips:
    print("NOTE: skipped legs mean this run is PARTIAL, not green.")
sys.exit(1 if fails else 0)
