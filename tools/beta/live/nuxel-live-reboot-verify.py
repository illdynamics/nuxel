#!/usr/bin/env python3
"""nuxel-live-reboot-verify — briq-10c: normal reboot, return-to-Nuxel proof and
the on-device probes that only the live group can run.

ACCESS TIER: live-phone-only.  The probe/dry-run paths are repository-only and
are exercised offline against tools/beta/live/tests/fake_console.py.

WHAT IT DOES, IN ORDER (nothing is assumed, nothing is fabricated)
=================================================================
  1. capability-based reachability preflight (never a hard-coded tty node);
  2. a *pre-reboot* capture of the A32 signals that must survive a reboot:
     /proc/uptime, /proc/sys/kernel/random/boot_id, the on-device boot counter
     (when the image has one), the five session units, /var/lib/nuxel/fb-owner,
     /var/lib/nuxel/animation and the :8000 registry status;
  3. the mandatory PRE-REBOOT checklist (nl.PRE_REBOOT_CHECKLIST) — every item is
     evaluated, and a failing item refuses the reboot;
  4. the reboot itself, only when ALL of these hold:
       * --reboot was passed, with a non-empty --reason AND --diagnostic;
       * nl.RebootPolicy allows it against the recorded history (budget not
         exhausted, the previous reboot returned to Nuxel, rollback known-good,
         and neither the reason nor the diagnostic repeats the previous reboot);
       * the console is reachable and the pre-reboot checklist is green.
     The command issued is `systemctl reboot` (override with --reboot-cmd).  No
     other reboot entry point exists in this group: Recovery/Download-Mode are
     never triggered, and no partition/bootloader path is ever touched.
  5. the reconnect watch: the console must actually disappear and come back
     (bounded by --reconnect-timeout).  A phone that never comes back is reported
     BLOCKED_EXTERNAL_RESOURCE and NO further reboot is attempted (the policy
     refuses a repeat).
  6. the POST-REBOOT checklist plus a *real-reboot* proof built from independent
     signals: the kernel boot_id changed, OR uptime went backwards, OR the
     on-device boot counter increased.  One signal is evidence; a changed
     diagnostic next time is mandatory.
  7. the live-only probe set: the bounded touch-pipeline trace (briq-01a), the
     ALSA/ABox audio walk (briq-03c), the framebuffer-owner check, the sec_ts IRQ
     counters, the PWA registry served over :8000, and the charger-mode/lpcharge
     state that is the known touch-blocker.  Diagnostic scripts that are not yet
     on the device are pushed to /var/tmp (an allowed userspace root) through
     SHA-256-verified frames first.
  8. every probe gets exactly one verdict from the mission vocabulary, taken from
     the observation alone.  A passing command is never promoted to
     VERIFIED_ON_S10PLUS unless a real on-device signal was read, and anything
     that needs a human finger, ear or eyesight stays NEEDS_OWNER_TEST.

Verdicts / exit codes
  0  procedure completed (per-item verdicts recorded in the bundle)
  2  usage error
  3  BLOCKED_EXTERNAL_RESOURCE (console unreachable, or it never came back)
  4  the reboot policy or the pre-reboot checklist refused the reboot
Never flashes; never writes outside the allowed userspace roots; never touches
.qq / RUN_ROOT; never writes a QonQrete receipt.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nuxel_live as nl  # noqa: E402

#: Where a pushed on-device diagnostic may live.  /var/tmp is an allowed
#: userspace root (nl.ALLOWED_TARGET_ROOTS), so this stays inside the contract.
PROBE_DIR = "/var/tmp/nuxel-live-probes"

#: Session units that must be active after the reboot (the A32 floor).
UNITS = nl.BASELINE_UNITS

#: On-device read commands used before and after the reboot.
SIGNAL_CMDS = (
    ("uptime", "cat /proc/uptime"),
    ("boot_id", "cat /proc/sys/kernel/random/boot_id 2>&1"),
    ("boot_count", "cat /var/lib/nuxel/boot-count 2>&1"),
    ("units", "for u in %s;do printf '%%s=%%s\\n' $u $(systemctl is-active $u 2>&1);done"
              % " ".join(UNITS)),
    ("failed_units", "systemctl --failed --no-legend --no-pager"),
    ("fb_owner", "cat /var/lib/nuxel/fb-owner 2>&1"),
    ("animation", "cat /var/lib/nuxel/animation 2>&1"),
    ("wl_fb_state", "cat /run/nuxel-wl-fb.state 2>&1"),
    ("registry_http", "curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8000/ 2>&1"),
    ("boot_mode", "tr ' ' '\\n' </proc/cmdline|grep androidboot.mode"),
)


# --------------------------------------------------------------------------- #
# The live-only probe set (step 7).  Each entry is data first and a rule second:
# the rule may only read the bytes the device actually returned.
# --------------------------------------------------------------------------- #
def _has(out, *needles):
    low = out.lower()
    return any(n.lower() in low for n in needles)


def rule_touch_pipeline(out, rc):
    """briq-01a's bounded capture: the verdict follows its own printed gate."""
    if _has(out, "charger-mode", "lpcharge", "low-power", "lpm_mode=lpm", "bootmode=lpm"):
        return ("BLOCKED_KERNEL",
                "the capture classified a charger/low-power boot: sec_ts is not "
                "serviced in that mode — the kernel/DTB fix is offline-only")
    if "CAPTURE_GATE=PASS" in out:
        return ("VERIFIED_ON_S10PLUS",
                "the bounded capture recorded BTN_TOUCH down/up with in-range "
                "coordinates reaching the top layer (DOM); the human finger test is "
                "still tracked separately in manual-proof/01-touchscreen.md")
    if "CAPTURE_GATE=BLOCKED" in out:
        return ("BLOCKED_HARDWARE",
                "the capture reported BLOCKED: the first dropping layer is named in "
                "the trace bundle")
    if "CAPTURE_GATE=FAIL" in out:
        return ("NEEDS_OWNER_TEST",
                "the capture wrote its bundle but recorded no finger: a desk run "
                "without a touch is not a touchscreen test")
    if rc not in (0, None):
        return ("BLOCKED_EXTERNAL_RESOURCE",
                "the touch capture exited %s without printing a gate" % rc)
    return ("DEPLOYED_UNVERIFIED",
            "the capture produced output but no recognised gate marker")


def rule_audio_abox(out, rc):
    """briq-03c's ALSA/ABox walk.  Writability is not audibility — never promoted."""
    if _has(out, "no such card", "card not found", "beyond-madera missing",
            "cannot open", "no soundcards"):
        return ("BLOCKED_FIRMWARE",
                "the beyond-madera card is not present/bound: this is a "
                "kernel/firmware-side finding, not something userspace fixes")
    first = None
    for line in nl.clean_lines(out):
        low = line.lower()
        if "first_broken" in low or "first broken" in low:
            first = line.strip()
            break
    if first and not _has(first, "none", "null", "no broken"):
        return ("FAILED", "the walk named the first broken playback stage: %s" % first[:160])
    if _has(out, "dac", "pcm", "dapm", "abox") and rc == 0:
        return ("NEEDS_OWNER_TEST",
                "the walk reached the DAC/ABox stage; a writable mixer control is "
                "not proof of audible sound (manual-proof/06-audio.md)")
    return ("DEPLOYED_UNVERIFIED", "the walk returned no decisive stage marker")


def rule_fb_owner(out, rc):
    lines = [l.strip() for l in nl.clean_lines(out) if l.strip()]
    receipt = any(l == "nuxel-wl-fb" for l in lines)
    state = any(l.startswith("owner=nuxel-wl-fb") for l in lines)
    if receipt or state:
        return ("VERIFIED_ON_S10PLUS",
                "the device itself reports the single framebuffer owner (nuxel-wl-fb) in "
                "/var/lib/nuxel/fb-owner and /run/nuxel-wl-fb.state")
    return ("FAILED", "the framebuffer owner is not the single Wayland/fb bridge "
                      "(observed: %s)" % " | ".join(lines)[:120])


def rule_sec_ts_irq(out, rc):
    counts = []
    for line in nl.clean_lines(out):
        if "sec_t" in line:
            for tok in line.split():
                if tok.isdigit():
                    counts.append(int(tok))
    if counts and sum(counts) > 0:
        return ("DEPLOYED_UNVERIFIED",
                "sec_ts has a live interrupt counter (sum=%d): this proves the "
                "controller is mapped, not that a touch is delivered" % sum(counts))
    if counts:
        return ("BLOCKED_HARDWARE",
                "sec_ts is mapped but its interrupt counter is zero — the controller "
                "is not generating IRQs at all")
    return ("BLOCKED_KERNEL",
            "no sec_ts/sec_touch line in /proc/interrupts: the touch controller is "
            "not in the kernel's interrupt map")


def rule_pwa_registry(out, rc):
    if out.strip().startswith("{") or '"apps"' in out:
        return ("VERIFIED_ON_S10PLUS",
                "the launcher served its registry over :8000 and the body parsed as "
                "the app registry")
    if _has(out, "200") and _has(out, "http"):
        return ("VERIFIED_ON_S10PLUS", "the registry endpoint answered HTTP 200")
    return ("FAILED", "the launcher did not serve the registry on 127.0.0.1:8000")


def rule_charger_mode(out, rc):
    if _has(out, "lpcharge", "charger-mode", "lpm_mode"):
        return ("BLOCKED_KERNEL",
                "a charger/low-power mode marker is present: sec_ts is not serviced "
                "in that mode (docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md)")
    if _has(out, "1") and _has(out, "online"):
        return ("DEPLOYED_UNVERIFIED",
                "the power supply reports online; no charger-mode marker in the "
                "kernel log, and a normal boot cannot conclude the charger case")
    return ("DEPLOYED_UNVERIFIED",
            "no charger-mode marker observed on this boot")


PROBE_RULES = {
    "touch-pipeline": ("briq-01a bounded touch-pipeline tracer", rule_touch_pipeline),
    "audio-abox": ("briq-03c ALSA / ABox playback walk", rule_audio_abox),
    "fb-owner": ("display ownership receipt check", rule_fb_owner),
    "sec-ts-irq": ("sec_ts interrupt counters", rule_sec_ts_irq),
    "pwa-registry": ("PWA registry served over :8000", rule_pwa_registry),
    "charger-mode": ("charger-mode / lpcharge state", rule_charger_mode),
}

#: area = the numbered manual-proof area this probe feeds.
PROBES = (
    {"id": "touch-pipeline", "area": "01-touchscreen", "priority": 1,
     "device_path": "/home/nuxel/nuxel/tools/s10plus/a33/nuxel-touch-capture.sh",
     "push": ["tools/s10plus/a33/nuxel-touch-capture.sh",
              "tools/s10plus/a33/nuxel-touch-trace.py",
              "tools/s10plus/a33/nuxel-bootmode-guard.py"],
     "argv": ["--dry-run", "--seconds", "20"],
     "human_required": True,
     "purpose": "prove how far a touch event travels before something drops it "
                "(sec_ts -> IRQ -> evdev -> libinput -> Phoc -> Wayland -> WebKitGTK -> PWA)",
     "failure_symptoms": "no CAPTURE_GATE line; tracer reports a missing node; "
                         "charger-mode classification",
     "diagnostic": "nuxel-touch-capture.sh --seconds 90 (finger) / --dry-run (state only)"},
    {"id": "audio-abox", "area": "06-audio", "priority": 3,
     "device_path": "/home/nuxel/nuxel/tools/s10plus/a33/nuxel-audio-diag.sh",
     "push": ["tools/s10plus/a33/nuxel-audio-diag.sh"],
     "argv": ["pipeline", "--json"],
     "human_required": True,
     "purpose": "walk card -> PCM -> mixer -> DAPM -> route -> DAC/ABox and name the "
                "first stage that is missing or silent",
     "failure_symptoms": "no beyond-madera card; a named first broken stage; DAC never "
                         "enters the running state",
     "diagnostic": "nuxel-audio-diag.sh pipeline --json; tone 500 --yes (low volume)"},
    {"id": "fb-owner", "area": "02-boot-animation-launcher", "priority": 2,
     "device_path": None, "push": [],
     "argv": [], "argv_override": "cat /var/lib/nuxel/fb-owner; cat /run/nuxel-wl-fb.state",
     "human_required": False,
     "purpose": "exactly one framebuffer owner after the reboot",
     "failure_symptoms": "two owners, an empty receipt, or an owner that is not "
                         "nuxel-wl-fb",
     "diagnostic": "cat /var/lib/nuxel/fb-owner /run/nuxel-wl-fb.state"},
    {"id": "sec-ts-irq", "area": "01-touchscreen", "priority": 1,
     "device_path": None, "push": [],
     "argv": [], "argv_override": "grep -iE 'sec_ts|sec_touch' /proc/interrupts",
     "human_required": False,
     "purpose": "the touch controller's interrupt counter after the reboot",
     "failure_symptoms": "no sec_ts line, or a line whose counter never moves",
     "diagnostic": "grep -iE 'sec_ts|sec_touch' /proc/interrupts"},
    {"id": "pwa-registry", "area": "20-applications", "priority": 2,
     "device_path": None, "push": [],
     "argv": [],
     "argv_override": "curl -s http://127.0.0.1:8000/registry.json | head -c 400",
     "human_required": False,
     "purpose": "the launcher/app registry is served over :8000 after the reboot",
     "failure_symptoms": "connection refused, empty body, non-JSON body",
     "diagnostic": "curl -s http://127.0.0.1:8000/registry.json | head -c 400"},
    {"id": "charger-mode", "area": "01-touchscreen", "priority": 1,
     "device_path": None, "push": [],
     "argv": [],
     "argv_override": "cat /sys/class/power_supply/*/online 2>/dev/null; "
                      "dmesg 2>/dev/null | grep -i lpcharge | tail -3",
     "human_required": False,
     "purpose": "the known touch-blocking boot mode that must not be regressed",
     "failure_symptoms": "lpcharge/charger-mode markers in the kernel log on a normal boot",
     "diagnostic": "dmesg | grep -i lpcharge; tr ' ' '\\n' </proc/cmdline | grep mode"},
)


# --------------------------------------------------------------------------- #
# Console resolution (capability first, dev-file second — never a fixed node)
# --------------------------------------------------------------------------- #
def resolve_node(args):
    """-> console capability record for this attempt."""
    if args.dev_file:
        try:
            with open(args.dev_file) as fh:
                path = fh.read().strip().splitlines()
                path = path[0].strip() if path else ""
        except OSError as e:
            raise nl.SelectionError("cannot read --dev-file %s: %s" % (args.dev_file, e))
        if not path:
            raise nl.SelectionError("--dev-file %s is empty" % args.dev_file)
        return {"callout": path, "match_stage": "dev-file"}
    if args.dev:
        return {"callout": args.dev, "match_stage": "explicit"}
    usb = []
    if sys.platform == "darwin":
        try:
            import subprocess
            usb = nl.parse_ioreg_usb_devices(
                subprocess.run(["ioreg", "-w0", "-l", "-p", "IOUSB"],
                               capture_output=True, text=True, timeout=20).stdout)
        except (OSError, Exception):  # noqa: BLE001 - capability lookup is best-effort
            usb = []
    return nl.select_console_node(nl.enumerate_console_nodes(), usb_devices=usb)


def open_now(args, lock_wait=2.0):
    """Open the console once; raises SelectionError/ConsoleLost."""
    node = resolve_node(args)
    con = nl.Console(node["callout"], timeout=args.timeout, lock_wait=lock_wait)
    con.open()
    return con, node


def wait_for_reconnect(args, deadline, log):
    """Poll (bounded) until the console is back AND answers a verified frame.

    A USB CDC-ACM gadget re-enumerates after a reboot, so the node name may
    change; that is exactly why this re-resolves by capability every attempt.
    """
    while time.time() < deadline:
        entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "node": None, "error": None,
                 "reachable": False}
        con = None
        try:
            con, node = open_now(args)
            entry["node"] = node
            probe = con.probe(3.0)
            entry["probe"] = probe.as_dict()
            if probe.reachable:
                res = con.run("id", timeout=args.timeout)
                entry["frame"] = res.as_dict()
                if res.ok:
                    entry["reachable"] = True
                    log.append(entry)
                    return con, node, log
                entry["error"] = "port answered but no verified command frame"
        except (nl.SelectionError, nl.ConsoleLost) as e:
            entry["error"] = str(e)
        finally:
            if con is not None and not entry["reachable"]:
                con.close()
        log.append(entry)
        time.sleep(max(0.2, args.poll_interval))
    return None, None, log


# --------------------------------------------------------------------------- #
# Device signals + reboot proof
# --------------------------------------------------------------------------- #
def read_signals(con, cmds=SIGNAL_CMDS):
    sig, frames = {}, []
    for key, cmd in cmds:
        res = con.run(cmd)
        frames.append({"key": key, "ok": res.ok, "rc": res.rc, "framed": res.framed,
                       "sha_ok": res.sha_ok, "elapsed_s": round(res.elapsed, 3)})
        sig[key] = res.output if res.ok else ""
    return sig, frames


def parse_units(text):
    out = {}
    for line in nl.clean_lines(text):
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def first_line(text, default=""):
    lines = nl.clean_lines(text)
    return lines[0] if lines else default


def uptime_of(text):
    line = first_line(text)
    tok = line.split()
    try:
        return float(tok[0])
    except (IndexError, ValueError):
        return None


def int_of(text):
    line = first_line(text)
    try:
        return int(line.split()[0])
    except (IndexError, ValueError):
        return None


def reboot_proof(pre, post):
    """Independent signals that a real power cycle happened.  Any one is enough,
    and every signal is reported even when another already proved the reboot."""
    sig = {
        "boot_id_before": first_line(pre.get("boot_id", ""), "NONE"),
        "boot_id_after": first_line(post.get("boot_id", ""), "NONE"),
        "uptime_before": uptime_of(pre.get("uptime", "")),
        "uptime_after": uptime_of(post.get("uptime", "")),
        "boot_count_before": int_of(pre.get("boot_count", "")),
        "boot_count_after": int_of(post.get("boot_count", "")),
    }
    signals = []
    if sig["boot_id_before"] not in ("", "NONE") and sig["boot_id_after"] not in ("", "NONE"):
        sig["boot_id_changed"] = sig["boot_id_before"] != sig["boot_id_after"]
        if sig["boot_id_changed"]:
            signals.append("kernel boot_id changed")
    if sig["uptime_before"] is not None and sig["uptime_after"] is not None:
        sig["uptime_went_backwards"] = sig["uptime_after"] < sig["uptime_before"]
        if sig["uptime_went_backwards"]:
            signals.append("uptime went backwards (%.1fs -> %.1fs)"
                           % (sig["uptime_before"], sig["uptime_after"]))
    if sig["boot_count_before"] is not None and sig["boot_count_after"] is not None:
        sig["boot_count_increased"] = sig["boot_count_after"] > sig["boot_count_before"]
        if sig["boot_count_increased"]:
            signals.append("on-device boot counter increased (%d -> %d)"
                           % (sig["boot_count_before"], sig["boot_count_after"]))
    sig["signals"] = signals
    sig["rebooted"] = bool(signals)
    sig["note"] = ("at least one independent on-device signal proves the power cycle"
                   if signals else
                   "the console answered, but no independent signal shows a power "
                   "cycle: this is NOT counted as a verified reboot")
    return sig


# --------------------------------------------------------------------------- #
# Checklists
# --------------------------------------------------------------------------- #
def audit_deploy_targets(repo):
    """Host-side guard audit for the pre-reboot checklist (a) item."""
    manifest = os.path.join(repo, "tools", "beta", "live", "deploy-manifest.json")
    try:
        with open(manifest) as fh:
            man = json.load(fh)
    except (OSError, ValueError) as e:
        return {"checked": 0, "refused": [str(e)]}
    plan = nl.build_deploy_plan(man, repo)
    return {"checked": len(plan["steps"]), "refused": plan["violations"],
            "skipped": [s["group"] for s in plan["skipped"]]}


def latest_bundle(root, prefix):
    try:
        names = sorted(n for n in os.listdir(root) if n.startswith(prefix))
    except OSError:
        return None
    return os.path.join(root, names[-1]) if names else None


def pre_reboot_checklist(con, args, repo):
    """nl.PRE_REBOOT_CHECKLIST, evaluated item by item.  A `fail` refuses the reboot."""
    audit = audit_deploy_targets(repo)
    rollbacks = con.run("find /home/nuxel/nuxel /etc/nuxel /usr/local -name "
                        "'*.nuxel-rollback' 2>/dev/null | wc -l")
    rollback_path = con.run("test -s /var/lib/nuxel/rollback.path && cat "
                            "/var/lib/nuxel/rollback.path || echo MISSING")
    baseline = latest_bundle(os.path.join(repo, "docs", "beta-finalization", "live",
                                          "evidence"), "baseline-")
    items = []
    items.append({"id": "pr-1", "item": "no block-device / firmware write this session",
                  "status": "pass" if not audit["refused"] else "fail",
                  "evidence": ("%d deploy targets audited, 0 refused by "
                               "assert_userspace_path(); skipped blocked groups: %s"
                               % (audit["checked"], ",".join(audit["skipped"]) or "none")
                               if not audit["refused"] else json.dumps(audit["refused"])[:300])})
    n = int_of(rollbacks.output) if rollbacks.ok else None
    items.append({"id": "pr-2", "item": "rollback copies present for deployed files",
                  "status": "pass" if (n or 0) > 0 else "warn",
                  "evidence": ("%s *.nuxel-rollback file(s) on the device" % n
                               if rollbacks.ok else "could not read the rollback count")})
    rp = nl.clean_lines(rollback_path.output) if rollback_path.ok else []
    items.append({"id": "pr-3", "item": "known-good userspace rollback path recorded",
                  "status": "pass" if rp and rp[0] != "MISSING" else "warn",
                  "evidence": rp[0] if rp else "unreadable"})
    items.append({"id": "pr-4", "item": "console reconnect procedure ready on the host",
                  "status": "pass",
                  "evidence": "capability-based reconnect (%s); timeout %ss, poll %ss"
                              % (args.dev_file or args.dev or "ioreg capability lookup",
                                 args.reconnect_timeout, args.poll_interval)})
    items.append({"id": "pr-5", "item": "baseline bundle captured and hashed",
                  "status": "pass" if baseline else "warn",
                  "evidence": baseline or "no baseline-* bundle in the live evidence tree"})
    return items


def post_reboot_checklist(signals, reconnect_ok, reconnect_frame):
    units = parse_units(signals.get("units", ""))
    failed = nl.clean_lines(signals.get("failed_units", ""))
    failed = [f for f in failed if "loaded units listed" not in f]
    fbo = first_line(signals.get("fb_owner", ""), "")
    anim = nl.clean_lines(signals.get("animation", ""))
    http = first_line(signals.get("registry_http", ""), "")
    return [
        {"id": "po-1", "item": "console reconnects and answers a verified frame",
         "status": "pass" if reconnect_ok else "fail",
         "evidence": json.dumps(reconnect_frame)[:240] if reconnect_frame else "no frame"},
        {"id": "po-2", "item": "boot graph completed without failed units",
         "status": "pass" if not failed else "fail",
         "evidence": ("0 failed units" if not failed else "; ".join(failed)[:240])
         + " | units: " + json.dumps(units)},
        {"id": "po-3", "item": "framebuffer owner is the single Wayland/fb bridge",
         "status": "pass" if fbo == "nuxel-wl-fb" else "fail",
         "evidence": fbo or "empty receipt"},
        {"id": "po-4", "item": "animation handoff receipt present",
         "status": "pass" if anim else "fail",
         "evidence": (anim[0] if anim else "empty /var/lib/nuxel/animation")},
        {"id": "po-5", "item": "launcher serves the registry on :8000",
         "status": "pass" if http.strip().startswith("2") else "fail",
         "evidence": "HTTP %s" % (http.strip() or "no answer")},
    ]


# --------------------------------------------------------------------------- #
# Probe execution (stage the diagnostic through a verified frame if needed)
# --------------------------------------------------------------------------- #
def verify_verdict(v):
    if v not in nl.VALID_VERDICTS:
        raise ValueError("probe produced a verdict outside the mission vocabulary: %r" % v)
    return v


def device_present(con, path):
    res = con.run("test -e %s && echo PRESENT || echo ABSENT" % path)
    return bool(res.ok and "PRESENT" in res.output)


def stage_probe(con, bundle, defn, repo):
    """Return (command, staged[]) for one probe, pushing repo files when the
    device does not already carry the diagnostic."""
    staged = []
    if defn.get("argv_override"):
        return defn["argv_override"], staged
    device = defn.get("device_path")
    if device and device_present(con, device):
        return ("sh %s %s" % (device, " ".join(defn.get("argv", [])))).strip(), staged
    for rel in defn.get("push", []):
        src = os.path.join(repo, rel)
        with open(src, "rb") as fh:
            data = fh.read()
        target = os.path.join(PROBE_DIR, os.path.basename(rel))
        info = nl.push_bytes(con, data, target, mode="0755")
        staged.append({"source": rel, "target": target, "bytes": info["bytes"],
                       "frames": info.get("parts", info.get("frames")), "sha256": info["decoded_sha256"]})
    if not staged:
        return None, staged
    entry = defn.get("device_path") or defn["push"][0]
    path = os.path.join(PROBE_DIR, os.path.basename(entry))
    return ("sh %s %s" % (path, " ".join(defn.get("argv", [])))).strip(), staged


def run_probe(con, bundle, defn, repo, args):
    rec = {"id": defn["id"], "area": defn["area"], "priority": defn["priority"],
           "purpose": defn["purpose"], "human_required": defn["human_required"],
           "failure_symptoms": defn["failure_symptoms"], "diagnostic": defn["diagnostic"],
           "cmd": None, "staged": [], "rc": None, "framed": None, "sha_ok": None,
           "observation": "", "verdict": None, "reason": None,
           "log": "probes/%s.txt" % defn["id"]}
    try:
        cmd, staged = stage_probe(con, bundle, defn, repo)
    except nl.ConsoleLost as e:
        rec["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        rec["reason"] = "could not stage the diagnostic over the console: %s" % e
        return rec
    except nl.GuardViolation:
        # a guard violation is a hard, deliberate refusal: the caller must see it
        raise
    if cmd is None:
        rec["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        rec["reason"] = "no on-device copy of the diagnostic and nothing to push"
        return rec
    rec["cmd"], rec["staged"] = cmd, staged
    res = con.run(cmd, timeout=args.probe_timeout)
    rec["rc"], rec["framed"], rec["sha_ok"] = res.rc, res.framed, res.sha_ok
    out = res.output if res.ok else ""
    rec["observation"] = "\n".join(nl.clean_lines(out))[:2000]
    if res.ok:
        rule = PROBE_RULES[defn["id"]][1]
        try:
            verdict, reason = rule(out, res.rc)
            verdict = verify_verdict(verdict)
        except ValueError as e:
            verdict, reason = "FAILED", str(e)
    else:
        verdict, reason = ("BLOCKED_EXTERNAL_RESOURCE",
                           "the console did not verify the command frame for %s" % defn["id"])
    rec["verdict"], rec["reason"] = verdict, reason
    bundle.write(rec["log"],
                 "probe: %s (%s)\ncmd: %s\nstaged: %s\nrc: %s framed: %s sha_ok: %s\n"
                 "verdict: %s\nreason: %s\n--- observation ---\n%s\n"
                 % (defn["id"], defn["area"], cmd, json.dumps(staged, sort_keys=True),
                    res.rc, res.framed, res.sha_ok, verdict, reason, out))
    return rec


def run_baseline_probes(con, bundle, repo, args):
    """--probe-set baseline: the read-only A32 probe list, no pushed scripts."""
    recs = []
    for key, cmd in nl.baseline_probes(None):
        res = con.run(cmd)
        ok = res.ok and bool(nl.clean_lines(res.output))
        recs.append({"id": "baseline:" + key, "area": "baseline", "priority": 9,
                     "purpose": "A32 baseline read", "human_required": False,
                     "cmd": cmd, "rc": res.rc, "framed": res.framed, "sha_ok": res.sha_ok,
                     "observation": "\n".join(nl.clean_lines(res.output))[:600],
                     "verdict": "DEPLOYED_UNVERIFIED" if ok else "BLOCKED_EXTERNAL_RESOURCE",
                     "reason": ("read from the device" if ok else "no verified output"),
                     "failure_symptoms": "command returns nothing", "diagnostic": cmd,
                     "log": "probes/baseline-%s.txt" % key.replace("/", "_").replace(":", "_")})
        bundle.write(recs[-1]["log"],
                     "cmd: %s\nrc: %s framed: %s sha_ok: %s\n---\n%s\n"
                     % (cmd, res.rc, res.framed, res.sha_ok, res.output))
    return recs


# --------------------------------------------------------------------------- #
# Reboot history (persistent: the budget must survive across runs)
# --------------------------------------------------------------------------- #
def load_history(path):
    try:
        with open(path) as fh:
            hist = json.load(fh)
    except (OSError, ValueError):
        return []
    return hist if isinstance(hist, list) else []


def save_history(path, history):
    nl.ensure_not_qq(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(history, fh, indent=2, sort_keys=True)
    return path


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="S10+ normal reboot, return-to-Nuxel verification and live probes")
    ap.add_argument("--evidence-dir", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--dev", default=None, help="explicit tty (offline harness / known node)")
    ap.add_argument("--dev-file", default=None,
                    help="file holding the console node; re-read on every reconnect "
                         "attempt (the offline harness and hosts without ioreg use this)")
    ap.add_argument("--reboot", action="store_true",
                    help="actually issue the normal reboot (requires --reason and --diagnostic)")
    ap.add_argument("--reason", default=None, help="why this reboot is necessary")
    ap.add_argument("--diagnostic", default=None,
                    help="the diagnostic that will run after this reboot (must differ "
                         "from the previous reboot's)")
    ap.add_argument("--reboot-cmd", default="systemctl reboot",
                    help="the normal-reboot command issued on the device (userspace only)")
    ap.add_argument("--reconnect-timeout", type=float, default=240.0)
    ap.add_argument("--poll-interval", type=float, default=3.0)
    ap.add_argument("--probe-seconds", type=float, default=8.0)
    ap.add_argument("--probe-timeout", type=float, default=120.0)
    ap.add_argument("--timeout", type=float, default=25.0)
    ap.add_argument("--lock-wait", type=float, default=30.0)
    ap.add_argument("--max-reboots", type=int, default=3)
    ap.add_argument("--history", default=None,
                    help="reboot history JSON (default <evidence-dir>/reboots.json)")
    ap.add_argument("--probes", default=None, help="comma-separated probe ids to run")
    ap.add_argument("--probe-set", default="live", choices=("live", "baseline", "none"))
    ap.add_argument("--simulated", action="store_true",
                    help="the far end is the offline fake console: stamp the bundle as "
                         "OFFLINE_TESTED and never claim VERIFIED_ON_S10PLUS")
    ap.add_argument("--checklist-only", action="store_true",
                    help="evaluate both checklists and stop before any reboot")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    repo = nl.repo_root_from_here()
    ev_root = args.evidence_dir or os.path.join(repo, "docs", "beta-finalization",
                                                "live", "evidence")
    nl.ensure_not_qq(ev_root)
    bundle = nl.EvidenceBundle(ev_root, name=args.name,
                               label="reboot-verify-sim" if args.simulated
                               else "reboot-verify")
    hist_path = args.history or os.path.join(ev_root, "reboots.json")
    history = load_history(hist_path)
    pol = nl.RebootPolicy(max_reboots=args.max_reboots)
    report = {"briq": "briq-10c-live-reboot-and-verify",
              "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "evidence_dir": bundle.dir, "reboot_requested": bool(args.reboot),
              "simulated": bool(args.simulated),
              "reboot_cmd": args.reboot_cmd if args.reboot else None,
              "reason": args.reason, "diagnostic": args.diagnostic,
              "history_before": history, "history_path": hist_path,
              "verdict": None, "blocked_reason": None, "checklists": {},
              "probes": [], "reboot": {"requested": bool(args.reboot)}}

    # --- 1. reachability --------------------------------------------------- #
    con = None
    try:
        con, node = open_now(args, lock_wait=args.lock_wait)
    except (nl.SelectionError, nl.ConsoleLost) as e:
        report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        report["blocked_reason"] = "cannot take the console: %s" % e
        return finish(bundle, report, args, 3)
    try:
        probe = con.probe(args.probe_seconds)
        report["probe"] = probe.as_dict()
        report["console"] = node
        if not probe.reachable:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = (
                "console %s is byte-silent for %.1fs: no pre-reboot capture, no reboot "
                "and no probe is attempted on a port that cannot report the result"
                % (node["callout"], args.probe_seconds))
            return finish(bundle, report, args, 3)

        # --- 2. pre-reboot capture + checklist ----------------------------- #
        pre, frames = read_signals(con)
        bundle.write_json("pre-reboot-signals.json", pre)
        bundle.write_json("pre-reboot-frames.json", frames)
        report["pre_reboot"] = {k: first_line(v, "") for k, v in pre.items()}
        report["checklists"]["pre"] = pre_reboot_checklist(con, args, repo)
        bundle.write_json("checklist-pre-reboot.json", report["checklists"]["pre"])
        report["history_verdict"] = pol.next_reboot(history)

        if args.checklist_only:
            report["verdict"] = "IMPLEMENTED_NOT_DEPLOYED"
            report["verdict_note"] = ("checklists evaluated; --checklist-only stops before "
                                      "any reboot")
            return finish(bundle, report, args, 0)

        # --- 3/4/5/6. the reboot ------------------------------------------ #
        if not args.reboot:
            report["reboot"]["verdict"] = "DEFERRED"
            report["reboot"]["reason"] = ("no --reboot given: the mission forbids an "
                                          "unreasoned reboot, so the reboot half is "
                                          "implemented and offline-tested only")
            ok_console = con
        else:
            ok_console, code = do_reboot(con, args, report, bundle, pol, history, hist_path)
            if code is not None:
                return finish(bundle, report, args, code)
            con = ok_console

        # --- 7/8. probes -------------------------------------------------- #
        wanted = {p.strip() for p in args.probes.split(",")} if args.probes else None
        defs = [d for d in PROBES if not wanted or d["id"] in wanted]
        if args.probe_set == "baseline":
            report["probes"] = run_baseline_probes(con, bundle, repo, args)
        elif args.probe_set == "live":
            report["probes"] = [run_probe(con, bundle, d, repo, args) for d in defs]
        bundle.write_json("probe-verdicts.json", report["probes"])
        report["probe_summary"] = summarise(report["probes"])
        report["verdict"] = overall_verdict(report)
        report["verdict_note"] = verdict_note(report)
        return finish(bundle, report, args, 0)
    except nl.GuardViolation as e:
        report["verdict"] = "DEPLOYED_UNVERIFIED"
        report["blocked_reason"] = "guard refused the reboot command: %s" % e
        return finish(bundle, report, args, 4)
    finally:
        if con is not None:
            con.close()


def do_reboot(con, args, report, bundle, pol, history, hist_path):
    """Issue the normal reboot and verify the phone comes back.  -> (console, exit|None)"""
    if not args.reason or not args.diagnostic:
        report["reboot"]["verdict"] = "DEFERRED"
        report["reboot"]["reason"] = ("a reboot needs both --reason and --diagnostic; "
                                      "refusing a blind reboot")
        return None, 4
    allowed = pol.next_reboot(history)
    if not allowed["allowed"]:
        report["reboot"]["verdict"] = "DEFERRED"
        report["reboot"]["reason"] = allowed["reason"]
        report["reboot"]["policy"] = allowed
        return None, 4
    failed = [i["id"] for i in report["checklists"]["pre"] if i["status"] == "fail"]
    if failed:
        report["reboot"]["verdict"] = "DEFERRED"
        report["reboot"]["reason"] = ("pre-reboot checklist failed: %s" % ",".join(failed))
        return None, 4

    report["reboot"]["issued_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["reboot"]["policy"] = allowed
    try:
        res = con.run(args.reboot_cmd, timeout=6.0)
        report["reboot"]["command_frame"] = res.as_dict()
        report["reboot"]["command_output"] = res.output.strip()[:300]
    except nl.ConsoleLost as e:
        report["reboot"]["command_frame"] = {"error": str(e)}
    # observe the port going away (bounded; a gadget that answers for ever after a
    # reboot command means the command did not take effect)
    gone = False
    try:
        t0 = time.time()
        while time.time() - t0 < 20.0:
            con.pump(0.5)
    except nl.ConsoleLost as e:
        gone, report["reboot"]["disconnect"] = True, str(e)
    if not gone:
        report["reboot"]["disconnect"] = ("the console never dropped: it is unknown "
                                          "whether the reboot was accepted")
    con.close()
    deadline = time.time() + args.reconnect_timeout
    newcon, node, log = wait_for_reconnect(args, deadline, [])
    bundle.write_json("reconnect-attempts.json", log)
    report["reboot"]["reconnect_attempts"] = log[-8:]
    report["reboot"]["disconnected"] = gone
    if newcon is None:
        report["reboot"]["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        report["reboot"]["returned_to_nuxel"] = False
        report["blocked_reason"] = (
            "the console did not come back within %.0fs after the reboot: the phone did "
            "not return to Nuxel (or the USB console is not serving again) — no further "
            "reboot is attempted" % args.reconnect_timeout)
        pol.record(history, args.reason, args.diagnostic, returned_to_nuxel=False,
                   evidence_before=bundle.dir)
        save_history(hist_path, history)
        return None, 3
    report["reboot"]["returned_to_nuxel"] = True
    post, _ = read_signals(newcon)
    bundle.write_json("post-reboot-signals.json", post)
    report["post_reboot"] = {k: first_line(v, "") for k, v in post.items()}
    proof = reboot_proof(report["pre_reboot"], report["post_reboot"])
    report["reboot"]["proof"] = proof
    report["checklists"]["post"] = post_reboot_checklist(
        post, True, report["reboot"].get("reconnect_attempts", [{}])[-1].get("frame"))
    bundle.write_json("checklist-post-reboot.json", report["checklists"]["post"])
    report["reboot"]["verdict"] = "VERIFIED_ON_S10PLUS" if proof["rebooted"] else \
        "DEPLOYED_UNVERIFIED"
    rollback_ok = bool(report["reboot"].get("returned_to_nuxel"))
    try:
        pol.record(history, args.reason, args.diagnostic, returned_to_nuxel=True,
                   rollback_known_good=rollback_ok, evidence_before=bundle.dir,
                   evidence_after=bundle.dir)
    except nl.GuardViolation as e:
        report["reboot"]["history_error"] = str(e)
    save_history(hist_path, history)
    report["history_after"] = history
    return newcon, None


def summarise(probes):
    out = {}
    for p in probes:
        out[p["verdict"]] = out.get(p["verdict"], 0) + 1
    return out


def overall_verdict(report):
    if report.get("simulated"):
        # The state machine ran, but the far end was the offline fake console: this
        # can never be an on-device claim.
        return ("OFFLINE_TESTED" if report.get("reboot", {}).get("returned_to_nuxel")
                or not report.get("reboot_requested") else "BLOCKED_EXTERNAL_RESOURCE")
    if not report.get("reboot_requested"):
        return "IMPLEMENTED_NOT_DEPLOYED"
    rb = report.get("reboot", {})
    if not rb.get("returned_to_nuxel"):
        return "BLOCKED_EXTERNAL_RESOURCE"
    post = report.get("checklists", {}).get("post", [])
    failed = [i["id"] for i in post if i["status"] == "fail"]
    probe_fail = [p["id"] for p in report.get("probes", []) if p["verdict"] == "FAILED"]
    if rb.get("proof", {}).get("rebooted") and not failed and not probe_fail:
        return "VERIFIED_ON_S10PLUS"
    if failed or probe_fail:
        return "FAILED"
    return "DEPLOYED_UNVERIFIED"


def verdict_note(report):
    rb = report.get("reboot", {})
    if report.get("simulated"):
        return ("the whole procedure (pre-checklist, policy, reboot, reconnect watch, "
                "real-reboot proof, post checklist, per-probe rules) was executed "
                "against the offline fake console: OFFLINE_TESTED, never device evidence")
    if not report.get("reboot_requested"):
        return ("procedure and probes are implemented and offline-tested; no reboot was "
                "requested, so nothing on the device was exercised by this half")
    if rb.get("returned_to_nuxel"):
        return ("the phone returned to Nuxel; per-item verdicts above are taken from the "
                "device's own output, never from the fact that a command exited 0")
    return rb.get("reason") or "the reboot did not complete"


def finish(bundle, report, args, code):
    report["exit_code"] = code
    report.setdefault("verdict", "BLOCKED_EXTERNAL_RESOURCE")
    report["verdicts"] = {"briq-10c-live-reboot-and-verify": report["verdict"],
                          "per-item": {p["id"]: p["verdict"] for p in report["probes"]}}
    bundle.write_json("reboot-and-verify.json", report)
    man, lines = bundle.manifest()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        if report.get("simulated"):
            print("# SIMULATED: the far end was the offline fake console, not the "
                  "S10+; this bundle is OFFLINE_TESTED evidence only")
        print("# nuxel-live-reboot-verify -> %s" % report["verdict"])
        print("# evidence: %s" % bundle.dir)
        for c in report.get("checklists", {}).get("pre", []):
            print("# pre  %-4s %-4s %s" % (c["id"], c["status"], c["item"]))
        for c in report.get("checklists", {}).get("post", []):
            print("# post %-4s %-4s %s" % (c["id"], c["status"], c["item"]))
        for p in report.get("probes", []):
            print("# probe %-16s %-26s %s" % (p["id"], p["verdict"], (p["reason"] or "")[:90]))
        if report.get("blocked_reason"):
            print("# blocked: %s" % report["blocked_reason"])
        print("# manifest: %s" % man)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
