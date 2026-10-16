#!/usr/bin/env python3
"""nuxel-verbose-boot — the userspace early-boot consumer of the verbose-boot
setting (briq-02b).

WHERE IT SITS IN THE BOOT
    nuxel-verbose-boot.service runs in the early userspace boot stage, ordered
    Before=nuxel-wl-fb.service (the framebuffer bridge) and Before=nuxel-pwa-host
    (the launcher).  It touches no framebuffer memory itself: it decides, records
    and publishes.  The display path (nuxel-wl-fb) and the launcher read the state
    it publishes, which keeps the single-framebuffer-owner rule intact.

WHAT IT DOES
    1. Reads the DURABLE setting from /etc/nuxel/boot/verbose-boot.json, with
       migration from the earlier locations (an old /etc/nuxel/verbose-boot, the
       legacy /var/lib/nuxel/verbose-boot*).  An upgrade never clobbers a user's
       choice: this script only ever CREATES the new document when it is absent.
    2. Evaluates the one-time override: holding Bixby during the early boot stage
       turns verbose boot on FOR THAT BOOT ONLY.  The override is honoured ONLY
       when the early boot stage proves it can produce it, by publishing
       `bixby-hold-override=1` in /run/nuxel/boot-stage-capabilities and dropping
       the request file /run/nuxel/boot-verbose-once.  The installed stage (the
       A23 initramfs in the BOOT partition) cannot, so the override is reported as
       BOOT_UPDATE_REQUIRED with that exact reason - never faked behind a switch.
    3. Evaluates the OTHER two boot-diagnostics controls (briq-02b,bg-02
       verification pass) with one documented precedence, so the three controls
       can never contradict each other:

            off > short > verbose_boot > standard

       animation_mode=off/short comes from the durable document; otherwise an
       effective verbose_boot (config, kernel cmdline, or the one-time hold)
       shortens the animation because the operator asked for the log; otherwise
       the standard 192-frame animation with its minimum-cycle handoff runs.
       verbosity_level (0..3) only selects HOW MUCH the boot log says - it never
       turns the log on or off, so a default boot stays quiet and silent.
    4. Publishes the effective state (/run/nuxel/verbose-boot, K=V lines),
       appends the durable record (/var/lib/nuxel/verbose-boot), emits the
       NUXEL_VERBOSE_BOOT kernel marker, and - when verbose - writes
       /run/nuxel/anim-skip.request so the framebuffer bridge deliberately trades
       the animation for the earliest possible on-glass boot log (recorded in the
       handoff receipt as reason=verbose_boot_requested) and seeds
       /var/log/nuxel/boot-stage.log with a boot snapshot.

    It never fails the boot: any error is recorded and exits 0.

    --status   print the current decision without changing anything
    --root DIR operate on a fake root (offline harness; also NUXEL_ROOT)
"""
import json
import os
import shutil
import sys
import tempfile
import time

SCHEMA = 1
NEW_CFG = "/etc/nuxel/boot/verbose-boot.json"
LEGACY_PATHS = [
    "/etc/nuxel/verbose-boot",
    "/var/lib/nuxel/verbose-boot.legacy",
    "/var/lib/nuxel/verbose-boot",
]
RUN_DIR = "/run/nuxel"
STATE = "/run/nuxel/verbose-boot"
SKIP_REQUEST = "/run/nuxel/anim-skip.request"
RECORD = "/var/lib/nuxel/verbose-boot"
CAPS = "/run/nuxel/boot-stage-capabilities"
ONCE_REQUEST = "/run/nuxel/boot-verbose-once"
# animation_mode / verbosity_level (briq-02b, bg-02 verification pass).  Both are
# keys of the SAME durable document, so there is still exactly one boot-diagnostics
# setting to read, back up and roll back.
ANIMATION_MODES = ("standard", "short", "off")
VERBOSITY_MIN = 0
VERBOSITY_MAX = 3
DEFAULT_VERBOSITY = 1
BOOT_LOG = "/var/log/nuxel/boot-stage.log"
KMSG = "/dev/kmsg"
STAMP = 0

ROOT = os.environ.get("NUXEL_ROOT", "/").rstrip("/")


def P(path):
    return ROOT + path if ROOT else path


def say(msg):
    print(msg, flush=True)


def touch_kmsg(line):
    try:
        with open(P(KMSG), "w") as f:
            f.write("6,0;%s\n" % line)
    except OSError:
        pass


def read_text(path):
    try:
        with open(P(path), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def write_text(path, text, mode=0o644):
    p = P(path)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(p, mode)
        return True
    except OSError as e:
        say("!! cannot write %s: %s" % (path, e))
        return False


def atomic_write(path, text, mode=0o644):
    tmp = P(path) + ".tmp"
    try:
        os.makedirs(os.path.dirname(P(path)), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, P(path))
        return True
    except OSError as e:
        say("!! cannot write %s: %s" % (path, e))
        return False


def parse_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    s = str(v).strip().strip('"').lower()
    if s in ("1", "true", "yes", "on", "enable", "enabled"):
        return True
    if s in ("0", "false", "no", "off", "disable", "disabled", ""):
        return False
    return default


def parse_animation_mode(v, default="standard"):
    """standard | short | off, case-insensitively.  Unknown values fall back to
    the default AND are reported, so a typo in the document can never silently
    pick a different animation policy than the operator asked for."""
    if v is None:
        return default, "default"
    s = str(v).strip().strip('"').lower()
    if s in ANIMATION_MODES:
        return s, "config"
    return default, "invalid"


def parse_verbosity(v, default=DEFAULT_VERBOSITY):
    """Clamp 0..3.  A non-integer falls back to the default; an out-of-range
    integer is CLAMPED (not accepted) and the fact is reported."""
    if v is None:
        return default, "default"
    try:
        n = int(str(v).strip().strip('"'))
    except (TypeError, ValueError):
        return default, "invalid"
    if n < VERBOSITY_MIN or n > VERBOSITY_MAX:
        return max(VERBOSITY_MIN, min(VERBOSITY_MAX, n)), "clamped"
    return n, "config"


def load_durable():
    """Return (doc, source).  Never overwrites an existing new-style document;
    migrates an older location once, recording where the value came from."""
    raw = read_text(NEW_CFG)
    if raw:
        try:
            doc = json.loads(raw)
            if isinstance(doc, dict):
                doc.setdefault("schema_version", SCHEMA)
                doc.setdefault("verbose_boot", False)
                doc.setdefault("set_by", "config")
                return doc, "config"
        except ValueError:
            say("!! %s is not valid JSON - refusing to overwrite it" % NEW_CFG)
            return {"schema_version": SCHEMA, "verbose_boot": False, "set_by": "unreadable"}, "unreadable"
    for path in LEGACY_PATHS:
        raw = read_text(path)
        if raw is None:
            continue
        val = None
        try:
            doc = json.loads(raw)
            if isinstance(doc, dict):
                val = doc.get("verbose_boot", doc.get("verbose"))
        except ValueError:
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("VERBOSE_BOOT="):
                    val = line.split("=", 1)[1]
                elif line and not line.startswith("#") and "=" not in line:
                    val = line
        if val is None:
            continue
        migrated = {"schema_version": SCHEMA, "verbose_boot": parse_bool(val, False),
                    "set_by": "migrated", "updated_at": int(time.time()), "migrated_from": path}
        if atomic_write(NEW_CFG, json.dumps(migrated, indent=2) + "\n"):
            say("MIGRATED %s -> %s (verbose_boot=%s)" % (path, NEW_CFG, migrated["verbose_boot"]))
        return migrated, "migrated:" + path
    default = {"schema_version": SCHEMA, "verbose_boot": False, "set_by": "default", "updated_at": 0}
    return default, "default"


def override_capability():
    txt = read_text(CAPS) or ""
    supported = False
    for line in txt.splitlines():
        line = line.strip()
        if line.replace(" ", "") in ("bixby-hold-override=1", "bixby_hold_override=1"):
            supported = True
    if supported:
        return "supported", "the early boot stage published bixby-hold-override=1", os.path.exists(P(ONCE_REQUEST))
    reason = ("the installed early boot stage does not publish bixby-hold-override=1 "
              "(it cannot read the Bixby key state); enabling the one-time override requires a "
              "BOOT partition update, which this mission forbids (no flashing)")
    return "BOOT_UPDATE_REQUIRED", reason, os.path.exists(P(ONCE_REQUEST))


def cmdline_verbose():
    txt = read_text("/proc/cmdline") or ""
    return "nuxel.verbose_boot=1" in txt or "nuxel.verbose_boot=yes" in txt


def decide():
    doc, source = load_durable()
    cap, cap_reason, once_requested = override_capability()
    once = bool(once_requested and cap == "supported")
    kernel = cmdline_verbose()
    config_value = parse_bool(doc.get("verbose_boot"), False)
    if once:
        effective, eff_source = True, "bixby_hold_once"
    elif kernel:
        effective, eff_source = True, "cmdline"
    elif config_value:
        effective, eff_source = True, "config"
    else:
        effective, eff_source = False, "default"

    # ---- the other two boot-diagnostics controls ------------------------- #
    # ONE precedence, documented in configs/nuxel/boot/verbose-boot.json:
    #     off > short > verbose_boot > standard
    # The three controls therefore cannot contradict each other, and the
    # animation policy the bridge is told to run is a single value.
    anim_mode, anim_src = parse_animation_mode(doc.get("animation_mode"))
    verbosity, verb_src = parse_verbosity(doc.get("verbosity_level"))
    if anim_mode == "off":
        eff_anim, anim_reason = "off", "animation_mode_off"
    elif anim_mode == "short":
        eff_anim, anim_reason = "short", "animation_mode_short"
    elif effective:
        # verbose boot trades the animation for the earliest on-glass log
        eff_anim, anim_reason = "short", "verbose_boot_requested"
    else:
        eff_anim, anim_reason = "standard", "standard"
    return {"doc": doc, "config_source": source, "config_value": config_value,
            "effective": effective, "effective_source": eff_source,
            "capability": cap, "capability_reason": cap_reason,
            "once_requested": bool(once_requested), "once": once,
            "cmdline": kernel,
            "animation_mode": anim_mode, "animation_mode_source": anim_src,
            "verbosity": verbosity, "verbosity_source": verb_src,
            "effective_animation": eff_anim, "animation_reason": anim_reason,
            "skip_animation": eff_anim in ("short", "off")}


def boot_snapshot(verbosity=DEFAULT_VERBOSITY):
    """The on-glass boot log.  `verbosity` selects HOW MUCH it says (never
    whether it is shown - that is verbose_boot's job):

        0 quiet   -> the header and the kernel/boot-id identity only
        1 normal  -> + the display/launcher state files (the default)
        2 verbose -> + every subsystem state file, more lines per file
        3 debug   -> + /proc facts and the environment

    It is a bounded snapshot either way: it must never be able to block or
    flood the boot."""
    verbosity = max(VERBOSITY_MIN, min(VERBOSITY_MAX, int(verbosity)))
    lines = ["# Nuxel boot-stage log (verbose boot) — one line per boot marker",
             "# verbosity_level=%d" % verbosity,
             "== boot %s ==" % time.strftime("%Y-%m-%dT%H:%M:%S%z"),
             "kernel %s" % (read_text("/proc/version") or "unknown").strip()]
    for path in ("/proc/cmdline", "/proc/sys/kernel/random/boot_id"):
        t = read_text(path)
        if t:
            lines.append("%s: %s" % (os.path.basename(path), t.strip()))
    if verbosity >= 1:
        per_file = 4 if verbosity < 2 else 12
        for path in ("/var/lib/nuxel/animation", "/run/nuxel/verbose-boot"):
            t = read_text(path)
            if t:
                lines.extend("%s | %s" % (path, l) for l in t.strip().splitlines()[:per_file])
    if verbosity >= 2:
        for path in ("/var/lib/nuxel/display", "/run/nuxel-home.state",
                     "/run/nuxel-wl-fb.state", "/var/lib/nuxel/buttons",
                     "/run/nuxel/anim-handoff", "/run/nuxel/boot-stage-capabilities"):
            t = read_text(path)
            if t:
                lines.extend("%s | %s" % (path, l) for l in t.strip().splitlines()[:12])
    if verbosity >= 3:
        for path in ("/proc/uptime", "/proc/loadavg", "/proc/meminfo",
                     "/proc/sys/kernel/random/entropy_avail"):
            t = read_text(path)
            if t:
                head = " ".join(t.split()[:6]) if path.endswith("meminfo") else t.strip()
                lines.append("%s: %s" % (path, head))
        env = os.environ.get("NUXEL_BOOT_STAGE", "")
        lines.append("env NUXEL_BOOT_STAGE=%s" % env)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# OFFLINE HARNESS (briq-02b acceptance): does the setting survive an upgrade?
# --------------------------------------------------------------------------- #
# Runs the REAL consumer and the REAL decision code against a FAKE root, so the
# whole pre-boot path is exercised on this host with no /etc write, no systemd and
# no phone:
#
#   1. fresh install            -> default OFF, no animation skip request
#   2. user flips it ON         -> effective ON, anim-skip request published,
#                                  on-glass boot log seeded
#   3. rootfs/package UPGRADE   -> the installer's 'keep' rule must NOT clobber the
#                                  user's choice (this is the acceptance criterion);
#                                  a plain overwrite is shown to be the failure mode
#   4. legacy location          -> one-time migration into the durable document
#   5. unreadable document      -> refuses to overwrite, boot still succeeds
#   6. Bixby hold, stage cannot -> BOOT_UPDATE_REQUIRED, override REFUSED
#   7. Bixby hold, stage can    -> honoured for THAT BOOT ONLY (config untouched)
#   8. animation_mode/verbosity -> the single documented precedence
#                                  (off > short > verbose_boot > standard) and the
#                                  "verbosity never turns the log on" separation
SHIPPED_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "..", "..", "configs", "nuxel", "boot", "verbose-boot.json")
FAILED = []


def _check(name, cond, extra=""):
    global FAILED
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond:
        FAILED.append(name)
    return bool(cond)


def _root():
    d = tempfile.mkdtemp(prefix="nuxel-verbose-selftest-")
    for sub in ("etc/nuxel/boot", "run/nuxel", "var/lib/nuxel", "var/log/nuxel", "proc"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    with open(os.path.join(d, "proc/cmdline"), "w") as f:
        f.write("console=ttyGS0 nuxel.quiet=1\n")
    return d


def _boot(root):
    """Run the consumer exactly as systemd does, against `root`."""
    global ROOT
    ROOT = root
    return main([])


def _state(root, name):
    try:
        with open(os.path.join(root, "run/nuxel", name), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def selftest():
    if not os.path.isfile(SHIPPED_DEFAULT):
        _check("shipped default config exists", False, SHIPPED_DEFAULT)
        return 1
    shipped = json.load(open(SHIPPED_DEFAULT))
    _check("shipped default config has verbose_boot=false",
           parse_bool(shipped.get("verbose_boot")) is False, shipped.get("verbose_boot"))
    _check("shipped default records the Bixby override as BOOT_UPDATE_REQUIRED (not faked)",
           (shipped.get("bixby_hold_override") or {}).get("status") == "BOOT_UPDATE_REQUIRED",
           json.dumps(shipped.get("bixby_hold_override")))

    # ---- 1. fresh install -------------------------------------------------- #
    r = _root()
    _boot(r)
    st = _state(r, "verbose-boot")
    _check("fresh install: EFFECTIVE=0", "EFFECTIVE=0" in st, st)
    _check("fresh install: override capability reported as BOOT_UPDATE_REQUIRED",
           "OVERRIDE_CAPABILITY=BOOT_UPDATE_REQUIRED" in st, st)
    _check("fresh install: no animation-skip request", not os.path.exists(os.path.join(r, "run/nuxel/anim-skip.request")))
    _check("fresh install: durable record written",
           os.path.exists(os.path.join(r, "var/lib/nuxel/verbose-boot")))

    # ---- 2. the user (Settings UI / nuxelctl) turns it ON ------------------ #
    # exactly the document shape nuxelctl verbose-boot on and settings-store.js write
    user_doc = {"schema_version": 1, "verbose_boot": True, "set_by": "user", "updated_at": int(time.time()), "migrated_from": None}
    with open(os.path.join(r, NEW_CFG.lstrip("/")), "w") as f:
        json.dump(user_doc, f, indent=2)
    _boot(r)
    st = _state(r, "verbose-boot")
    _check("user ON: EFFECTIVE=1 source=config", "EFFECTIVE=1" in st and "SOURCE=config" in st, st)
    _check("user ON: animation-skip request published",
           os.path.exists(os.path.join(r, "run/nuxel/anim-skip.request")))
    _check("user ON: ANIM_HANDOFF records the deliberate trade",
           "ANIM_HANDOFF=skip-animation" in st, st)
    _check("user ON: on-glass boot log seeded",
           os.path.getsize(os.path.join(r, "var/log/nuxel/boot-stage.log")) > 0)

    # ---- 3. UPGRADE: the installer's 'keep' rule must not clobber ---------- #
    # The shipped default is installed only when the file is ABSENT (the 'keep'
    # rule in the image build), which is what makes the setting durable.
    installed = os.path.join(r, NEW_CFG.lstrip("/"))
    _check("upgrade: document present before the install step", os.path.exists(installed))
    if not os.path.exists(installed):
        shutil.copyfile(SHIPPED_DEFAULT, installed)
    after = json.load(open(installed))
    _check("upgrade (keep rule): the user's verbose_boot=true survived the reinstall",
           parse_bool(after.get("verbose_boot")) is True, after)
    _check("upgrade (keep rule): the user provenance survived", after.get("set_by") == "user", after.get("set_by"))
    _boot(r)
    _check("upgrade: next boot is still verbose", "EFFECTIVE=1" in _state(r, "verbose-boot"))

    # …and the failure mode this test exists to catch: a plain overwrite WOULD lose it.
    tmp = installed + ".clobber"
    shutil.copyfile(SHIPPED_DEFAULT, tmp)
    clobbered = json.load(open(tmp))
    _check("negative control: a plain overwrite of the shipped default WOULD lose the setting",
           parse_bool(clobbered.get("verbose_boot")) is False, clobbered.get("verbose_boot"))
    os.unlink(tmp)

    # ---- 4. migration from the legacy location ----------------------------- #
    r2 = _root()
    legacy = os.path.join(r2, "etc/nuxel/verbose-boot")
    with open(legacy, "w") as f:
        f.write("VERBOSE_BOOT=1\n")
    _boot(r2)
    migrated_path = os.path.join(r2, NEW_CFG.lstrip("/"))
    _check("legacy flag migrated into the durable document", os.path.exists(migrated_path))
    if os.path.exists(migrated_path):
        md = json.load(open(migrated_path))
        _check("migration preserved the value", parse_bool(md.get("verbose_boot")) is True, md)
        _check("migration recorded where it came from",
               md.get("migrated_from") == "/etc/nuxel/verbose-boot", md.get("migrated_from"))
    _check("migrated boot is verbose", "EFFECTIVE=1" in _state(r2, "verbose-boot"))

    # ---- 5. an unreadable document is never overwritten -------------------- #
    r3 = _root()
    bad = os.path.join(r3, NEW_CFG.lstrip("/"))
    with open(bad, "w") as f:
        f.write("{ this is not json")
    rc = _boot(r3)
    _check("unreadable document: the boot still succeeds (exit 0)", rc == 0, "rc=%s" % rc)
    _check("unreadable document: left byte-identical (refused to overwrite)",
           open(bad).read() == "{ this is not json")
    _check("unreadable document: reported as unreadable, treated as OFF",
           "CONFIG_SOURCE=unreadable" in _state(r3, "verbose-boot"))

    # ---- 6./7. the one-time Bixby-hold override ---------------------------- #
    r4 = _root()
    os.makedirs(os.path.join(r4, "run/nuxel"), exist_ok=True)
    with open(os.path.join(r4, "run/nuxel/boot-verbose-once"), "w") as f:
        f.write("once\n")
    _boot(r4)
    st = _state(r4, "verbose-boot")
    _check("override requested but stage cannot: ONCE_REQUESTED=1", "ONCE_REQUESTED=1" in st, st)
    _check("override requested but stage cannot: ONCE=0 (refused, not faked)", "ONCE=0" in st, st)
    _check("override requested but stage cannot: boot stays non-verbose",
           "EFFECTIVE=0" in st, st)

    r5 = _root()
    with open(os.path.join(r5, "run/nuxel/boot-stage-capabilities"), "w") as f:
        f.write("bixby-key-device=event2\nbixby-hold-override=1\n")
    with open(os.path.join(r5, "run/nuxel/boot-verbose-once"), "w") as f:
        f.write("once\n")
    _boot(r5)
    st = _state(r5, "verbose-boot")
    _check("stage supports it: override honoured for this boot",
           "EFFECTIVE=1" in st and "SOURCE=bixby_hold_once" in st, st)
    _check("stage supports it: nothing persisted to the durable document",
           not os.path.exists(os.path.join(r5, NEW_CFG.lstrip("/"))))
    _check("override is consumed, not just volatile (/run request removed)",
           not os.path.exists(os.path.join(r5, "run/nuxel/boot-verbose-once")))
    _boot(r5)  # a second start in the same boot must not re-apply it
    _check("override is one-time only (the next start is non-verbose)",
           "EFFECTIVE=0" in _state(r5, "verbose-boot"))

    # ---- 8. the OTHER two boot-diagnostics controls (animation_mode /
    #         verbosity_level) and their single documented precedence:
    #             off > short > verbose_boot > standard
    #         verbosity_level only chooses HOW MUCH the log says, never whether
    #         it is shown, so the three controls cannot contradict each other.
    _check("shipped default config carries animation_mode=standard",
           shipped.get("animation_mode") == "standard", shipped.get("animation_mode"))
    _check("shipped default config carries verbosity_level=1",
           shipped.get("verbosity_level") == 1, shipped.get("verbosity_level"))
    _check("shipped default documents the precedence rule",
           (shipped.get("precedence") or {}).get("rule") == "off > short > verbose_boot > standard",
           json.dumps(shipped.get("precedence")))

    def _boot_with(verbose, anim_mode=None, verbosity=None):
        """A fake root whose durable document carries exactly these controls."""
        root = _root()
        doc = {"schema_version": 1, "verbose_boot": bool(verbose), "set_by": "user",
               "updated_at": int(time.time())}
        if anim_mode is not None:
            doc["animation_mode"] = anim_mode
        if verbosity is not None:
            doc["verbosity_level"] = verbosity
        with open(os.path.join(root, NEW_CFG.lstrip("/")), "w") as f:
            json.dump(doc, f, indent=2)
        _boot(root)
        return root, _state(root, "verbose-boot"), doc

    # defaults: standard animation, no skip, verbosity unchanged by verbose_boot
    rt, st, _ = _boot_with(False)
    _check("default: EFFECTIVE_ANIMATION=standard", "EFFECTIVE_ANIMATION=standard" in st, st)
    _check("default: ANIMATION_REASON=standard", "ANIMATION_REASON=standard" in st, st)
    _check("default: VERBOSITY=1", "VERBOSITY=1" in st, st)
    _check("default: still no animation-skip request", not os.path.exists(os.path.join(rt, "run/nuxel/anim-skip.request")))

    # verbose_boot alone shortens the animation, and never rewrites verbosity
    rv, stv, docv = _boot_with(True)
    _check("verbose only: animation shortens with reason=verbose_boot_requested",
           "EFFECTIVE_ANIMATION=short" in stv and "ANIMATION_REASON=verbose_boot_requested" in stv, stv)
    _check("verbose only: the skip request names the reason",
           "reason=verbose_boot_requested" in _state(rv, "anim-skip.request"), _state(rv, "anim-skip.request"))
    _check("verbose only: VERBOSITY is still 1 (controls are independent)", "VERBOSITY=1" in stv, stv)
    _check("verbose only: the design is recorded, not the setting", json.load(open(os.path.join(rv, NEW_CFG.lstrip("/")))) == docv)

    # animation_mode=short / off, with verbose OFF, still skip - and win
    rs, sts, _ = _boot_with(False, anim_mode="short")
    _check("animation_mode=short (verbose off): skip with reason=animation_mode_short",
           "reason=animation_mode_short" in _state(rs, "anim-skip.request"), sts)
    ro, sto, _ = _boot_with(False, anim_mode="off")
    _check("animation_mode=off (verbose off): skip with reason=animation_mode_off",
           "reason=animation_mode_off" in _state(ro, "anim-skip.request"), sto)
    _check("animation_mode=off: EFFECTIVE_ANIMATION=off", "EFFECTIVE_ANIMATION=off" in sto, sto)
    rov, stov, _ = _boot_with(True, anim_mode="off", verbosity=3)
    _check("precedence: off beats verbose_boot (reason=animation_mode_off)",
           "reason=animation_mode_off" in _state(rov, "anim-skip.request"), stov)
    _check("precedence: off beats verbose_boot (animation=off, verbose still 1)",
           "EFFECTIVE=1" in stov and "EFFECTIVE_ANIMATION=off" in stov, stov)

    # an invalid animation_mode is reported and falls back to standard
    rb, stb, _ = _boot_with(False, anim_mode="turbo")
    _check("an unknown animation_mode falls back to standard and is reported",
           "EFFECTIVE_ANIMATION=standard" in stb and "ANIMATION_MODE_SOURCE=invalid" in stb, stb)
    _check("an unknown animation_mode is NOT faked into a skip request",
           not os.path.exists(os.path.join(rb, "run/nuxel/anim-skip.request")))

    # verbosity_level: honoured, clamped, refused when nonsense - and the log
    # stays OFF when verbose_boot is off
    r3v, st3v, _ = _boot_with(False, verbosity=3)
    _check("verbosity_level=3 is honoured", "VERBOSITY=3" in st3v, st3v)
    _check("verbosity_level alone does NOT turn the on-glass log on (no skip request)",
           not os.path.exists(os.path.join(r3v, "run/nuxel/anim-skip.request")))
    _check("verbosity_level alone does NOT seed the boot-stage log",
           not os.path.exists(os.path.join(r3v, "var/log/nuxel/boot-stage.log")))
    rcl, stcl, _ = _boot_with(False, verbosity=9)
    _check("verbosity_level=9 is clamped to 3 (reported as clamped)",
           "VERBOSITY=3" in stcl and "VERBOSITY_SOURCE=clamped" in stcl, stcl)
    rnv, stnv, _ = _boot_with(False, verbosity="lots")
    _check("a nonsense verbosity_level falls back to 1 and is reported",
           "VERBOSITY=1" in stnv and "VERBOSITY_SOURCE=invalid" in stnv, stnv)

    # the snapshot itself obeys the level (less text at 0, more at 3)
    q = boot_snapshot(0)
    dbg = boot_snapshot(3)
    _check("boot log snapshot: level 0 is the bounded quiet form",
           q.count("\n") <= 6 and "verbosity_level=0" in q, q)
    _check("boot log snapshot: level 3 says strictly more than level 0",
           dbg.count("\n") > q.count("\n"), "%d vs %d" % (dbg.count("\n"), q.count("\n")))
    _check("boot log snapshot: level 0 never emits subsystem state lines",
           "nuxel-wl-fb.state" not in q)

    for d in (r, r2, r3, r4, r5, rt, rv, rs, ro, rov, rb, r3v, rcl, rnv):
        shutil.rmtree(d, ignore_errors=True)
    print("\n" + ("FAILED: " + ", ".join(FAILED) if FAILED else
                  "verbose-boot offline harness passed (upgrade-safe, offline)"))
    return 1 if FAILED else 0


def main(argv):
    global STAMP
    if "--selftest" in argv:
        return selftest()
    if "--status" in argv or "--json" in argv:
        d = decide()
        if "--json" in argv:
            print(json.dumps(d, indent=2))
        else:
            print("verbose_boot=%s source=%s config=%s once=%s override=%s"
                  % (d["effective"], d["effective_source"], d["config_value"],
                     d["once"], d["capability"]))
            print("animation_mode=%s (requested %s/%s) -> effective=%s reason=%s"
                  % (d["effective_animation"], d["animation_mode"],
                     d["animation_mode_source"], d["effective_animation"],
                     d["animation_reason"]))
            print("verbosity_level=%d (%s)" % (d["verbosity"], d["verbosity_source"]))
            if d["capability"] != "supported":
                print("override: %s — %s" % (d["capability"], d["capability_reason"]))
        return 0

    d = decide()
    STAMP = int(time.time())
    os.makedirs(P(RUN_DIR), exist_ok=True)

    state = ("EFFECTIVE=%d\n"
             "SOURCE=%s\n"
             "CONFIG=%s\n"
             "CONFIG_VALUE=%d\n"
             "CONFIG_SOURCE=%s\n"
             "OVERRIDE_CAPABILITY=%s\n"
             "OVERRIDE_STATUS=%s\n"
             "OVERRIDE_REASON=%s\n"
             "ONCE_REQUESTED=%d\n"
             "ONCE=%d\n"
             "CMDLINE_VERBOSE=%d\n"
             "ANIMATION_MODE=%s\n"
             "ANIMATION_MODE_SOURCE=%s\n"
             "EFFECTIVE_ANIMATION=%s\n"
             "ANIMATION_REASON=%s\n"
             "VERBOSITY=%d\n"
             "VERBOSITY_SOURCE=%s\n"
             "ANIM_HANDOFF=%s\n"
             "TS=%d\n" % (
                 1 if d["effective"] else 0, d["effective_source"], NEW_CFG,
                 1 if d["config_value"] else 0, d["config_source"],
                 d["capability"],
                 "BOOT_UPDATE_REQUIRED" if d["capability"] != "supported" else "SUPPORTED",
                 d["capability_reason"], 1 if d["once_requested"] else 0,
                 1 if d["once"] else 0, 1 if d["cmdline"] else 0,
                 d["animation_mode"], d["animation_mode_source"],
                 d["effective_animation"], d["animation_reason"],
                 d["verbosity"], d["verbosity_source"],
                 "skip-animation" if d["skip_animation"] else "minimum-cycle", STAMP))
    write_text(STATE, state)
    atomic_write(RECORD, state + "HISTORY %d verbose=%d source=%s\n"
                 % (STAMP, 1 if d["effective"] else 0, d["effective_source"]))

    say("NUXEL_VERBOSE_BOOT=%d SOURCE=%s CONFIG=%s ONCE=%d OVERRIDE=%s"
        % (1 if d["effective"] else 0, d["effective_source"], d["config_source"],
           1 if d["once"] else 0, d["capability"]))
    say("NUXEL_BOOT_ANIMATION=%s reason=%s verbosity=%d"
        % (d["effective_animation"], d["animation_reason"], d["verbosity"]))
    touch_kmsg("NUXEL_VERBOSE_BOOT=%d source=%s config=%d once=%d override=%s"
               % (1 if d["effective"] else 0, d["effective_source"],
                  1 if d["config_value"] else 0, 1 if d["once"] else 0, d["capability"]))
    # The animation policy gets its own marker: the live group greps for it, and
    # the bridge records the same reason in the handoff receipt.
    touch_kmsg("NUXEL_BOOT_ANIMATION=%s reason=%s verbosity=%d"
               % (d["effective_animation"], d["animation_reason"], d["verbosity"]))
    if d["capability"] != "supported" and d["once_requested"]:
        say("!! bixby-hold override requested but NOT honoured: %s" % d["capability_reason"])
        touch_kmsg("NUXEL_VERBOSE_BOOT_OVERRIDE_REFUSED reason=BOOT_UPDATE_REQUIRED")
    if d["once"]:
        # ONE-TIME, enforced here and not only by /run being volatile: once the
        # request has been honoured it is consumed, so a service restart inside
        # the same boot cannot turn a one-shot recovery aid into a mode.
        try:
            os.unlink(P(ONCE_REQUEST))
        except OSError:
            pass
        touch_kmsg("NUXEL_VERBOSE_BOOT_OVERRIDE_CONSUMED once=1")

    if d["skip_animation"]:
        # The animation is traded for the earliest on-glass handoff.  WHY is a
        # single value with one documented precedence (off > short > verbose_boot
        # > standard), so the bridge never has to guess and the receipt always
        # names the reason: animation_mode_off / animation_mode_short /
        # verbose_boot_requested.  The bridge still confirms the stop before it
        # writes a single scanout byte.
        write_text(SKIP_REQUEST, "ANIM_SKIP_REQUESTED reason=%s animation_mode=%s\n"
                   % (d["animation_reason"], d["animation_mode"]))
    else:
        try:
            os.unlink(P(SKIP_REQUEST))
        except OSError:
            pass

    # The on-glass boot log is gated on verbose_boot ONLY.  verbosity_level
    # selects how much it says; animation_mode selects what the animation does.
    # Keeping those three separate is what makes them non-contradictory.
    if d["effective"]:
        os.makedirs(P(os.path.dirname(BOOT_LOG)), exist_ok=True)
        try:
            with open(P(BOOT_LOG), "a", encoding="utf-8") as f:
                f.write(boot_snapshot(d["verbosity"]))
                f.write("verbose_boot=1 source=%s verbosity=%d animation=%s (%s)\n"
                        % (d["effective_source"], d["verbosity"],
                           d["effective_animation"], d["animation_reason"]))
        except OSError as e:
            say("!! cannot append %s: %s" % (BOOT_LOG, e))
        say("REBOOT_WILL_ENABLE_VERBOSE_BOOT=1 (applies from the next boot; "
            "kernel cmdline changes still require a BOOT partition update and are NOT done)")
    if d["skip_animation"] and not d["effective"]:
        say("ANIMATION_POLICY=%s reason=%s (verbose boot is OFF: no boot log is shown)"
            % (d["effective_animation"], d["animation_reason"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
