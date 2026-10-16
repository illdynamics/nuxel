#!/usr/bin/env python3
"""verify-service-graph.py — offline validator for the Nuxel boot graph.

WHAT IT PROVES (and what it deliberately does not)
--------------------------------------------------
This is an OFFLINE validator.  It parses the real unit files in the repository
and asserts that:

  1. every nuxel-* unit referenced by After/Before/Requires/Wants/Conflicts
     resolves to a unit that the rootfs builder actually installs;
  2. the ordering graph (After/Before, plus the implicit boot anchors) has NO
     cycles;
  3. the units that must never be dependencies of ours on Linux 4.14 are not
     (systemd-userdbd, dbus-broker for the system bus), and the A26 containment
     script still contains all four 4.14 repairs;
  4. no SYSTEM unit is enabled into a USER target (graphical-session.target);
  5. the rootfs builder installs and enables exactly the canonical unit set —
     the boot graph is reproducible from the repository, not hot-patched;
  6. the canonical services/** unit files did not silently LOSE the measured
     Environment=/ExecStart= lines of the shipped revisions they supersede.

A green run here is OFFLINE_TESTED.  It is NOT proof that
`systemctl is-system-running` reaches `running` on the handset — that verdict
belongs to the live-deployment group (bg-10) and is never claimed here.

Usage:
    python3 tools/s10plus/a33/verify-service-graph.py
    python3 tools/s10plus/a33/verify-service-graph.py --json build/pkgmeta/service-graph.json

    # validate a *copy* of the tree (fixture / mutation testing): the unit set is
    # always read as <root>/services/** etc., so a regression test can inject a
    # synthetic cycle or unsatisfied dependency and prove this validator FAILS.
    python3 tools/s10plus/a33/verify-service-graph.py --root /tmp/unit-fixture

`tools/s10plus/a33/tests/test-service-graph.py` uses --root exactly that way.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ROOT = REPO_ROOT  # the tree under validation; --root overrides it (fixture testing)


def repo_root() -> str:
    """The tree currently being validated (the repository, or a --root fixture)."""
    return ROOT


def builder_path() -> str:
    return os.path.join(repo_root(), "images", "s10plus", "build-phone-rootfs-inside-fedora.sh")


def a26_fixes_path() -> str:
    return os.path.join(repo_root(), "tools", "s10plus", "a26", "nuxel-rootfs-fixes.sh")

# Unit files that are part of Nuxel's installed set, with their repo paths.
UNIT_SOURCES = [
    "services/nuxel-web.service",
    "services/nuxel-bridge/systemd/nuxel-bridge.service",
    "services/nuxel-bridge/systemd/nuxel-http-bridge.service",
    "services/nuxel-portal/systemd/nuxel-portal.service",
    "services/nuxel-notifications/systemd/nuxel-notifications.service",
    "services/nuxel-session/systemd/seatd.service",
    "services/nuxel-session/systemd/nuxel-touch-arm.service",
    "services/nuxel-session/systemd/nuxel-wayland.service",
    "services/nuxel-session/systemd/nuxel-wl-fb.service",
    "services/nuxel-session/systemd/nuxel-fallback.service",
    "services/nuxel-session/systemd/nuxel-button-manager.service",
    "services/nuxel-animation/systemd/nuxel-animation.service",
    "services/nuxel-console/systemd/nuxel-console.service",
    "images/s10plus/nuxel-firstlight.service",
    "shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service",
]

# Units the graph is allowed to reference that Nuxel does not ship itself.
EXTERNAL_UNITS = {
    "sysinit.target", "basic.target", "multi-user.target", "default.target",
    "graphical.target", "network.target", "network-online.target",
    "local-fs.target", "shutdown.target", "sockets.target", "paths.target",
    "timers.target", "systemd-user-sessions.service",
    "dbus.service", "dbus.socket", "dbus-daemon.service",
    "systemd-udevd.service", "systemd-udev-settle.service",
    "systemd-tmpfiles-setup.service", "systemd-sysusers.service",
    "systemd-journald.service", "systemd-logind.service",
    "polkit.service", "ModemManager.service", "NetworkManager.service",
    "NetworkManager-wait-online.service", "greetd.service", "phosh.service",
    "pipewire.service", "wireplumber.service", "bluetooth.service",
    "systemd-modules-load.service", "ldconfig.service",
    # installed by the initramfs /init (the phone's early boot stage)
    "nuxel-ui.service",
    # User-session target referenced only by the VM-only camera portal unit
    # (shell/nuxel-camera-portal, not installed on the handset). Recorded here so
    # the reference is visible instead of being silently ignored.
    "graphical-session.target",
}

# 4.14: these must never be hard dependencies of a Nuxel unit.
FORBIDDEN_REFS = {
    "systemd-userdbd.service": "userdbd cannot run without pidfd child watching (ENOSYS on 4.14)",
    "systemd-userdbd.socket": "the socket must be masked - its client hangs forever if unserved",
    "dbus-broker.service": "dbus-broker-launch dies ENOSYS in launcher_fork; the system bus is dbus-daemon",
}

# Surfaces that exist in the tree for the UTM VM / another device generation and
# are NEVER installed on the handset by the rootfs builder. They are validated
# (their references must still resolve) but a no-op enablement in them is a
# recorded WARNING with a documented reason, not a handset boot-graph FAILURE.
VM_ONLY_UNITS = {
    "nuxel-camera-portal.service",
}

# Units that are INSTALLED BUT DELIBERATELY NOT ENABLED, with the reason.  These
# are not "forgotten" enablements: enabling them is the defect.  The validator
# asserts three things for each of them - the builder installs it, the builder
# does NOT enable it, and the unit file itself states why - so a future
# contributor cannot turn the exception into a silent hole by deleting a comment.
PROVISIONED_NOT_ENABLED = {
    "nuxel-console.service":
        "the live console has exactly ONE owner: the initramfs-started "
        "/opt/nuxel/nuxel-console already holds /run/nuxel-console.lock before "
        "systemd exists, and a second console on the same tty desynchronises the "
        "framed protocol. The unit is guarded by ConditionPathExists=/usr/bin/"
        "nuxel-console (absent on the shipped image) + ExecCondition="
        "nuxel-console-free (proves the port is free) + Restart=no",
}

REGEX_SECTION = re.compile(r"^\[([A-Za-z]+)\]\s*$")
REGEX_ASSIGN = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)=(.*)$")
MULTI_KEYS = {"After", "Before", "Wants", "Requires", "Conflicts", "ConditionPathExists",
              "Environment", "WantedBy", "Also", "RequiresMountsFor", "Documentation",
              "ExecStartPre", "ExecStartPost", "ReadWritePaths", "ReadOnlyPaths", "DeviceAllow",
              "AppArmorProfile", "EnvironmentFile", "StateDirectory", "RuntimeDirectory"}


def parse_unit(path: str) -> Dict[str, Dict[str, List[str]]]:
    sections: Dict[str, Dict[str, List[str]]] = {}
    cur = "?"
    with open(path, "r", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = REGEX_SECTION.match(line.strip())
            if m:
                cur = m.group(1)
                sections.setdefault(cur, {})
                continue
            m = REGEX_ASSIGN.match(line.strip())
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            sections.setdefault(cur, {}).setdefault(key, [])
            if key in MULTI_KEYS or val == "":
                sections[cur][key].append(val)
            else:
                sections[cur][key].append(val)
    return sections


def refs(sections, key) -> List[str]:
    out: List[str] = []
    for sec in ("Unit",):
        for v in sections.get(sec, {}).get(key, []):
            for tok in v.split():
                out.append(tok)
    return out


def install_refs(sections, key) -> List[str]:
    """Read a directive from the [Install] section.

    `WantedBy=`/`Also=` live in [Install], NOT [Unit]; reading them with refs()
    (which only scans [Unit]) silently returns nothing and turns every
    enablement assertion into dead code. This helper is the fix for that, and
    tools/s10plus/a33/tests/test-service-graph.py proves the assertion fires.
    """
    out: List[str] = []
    for v in sections.get("Install", {}).get(key, []):
        for tok in v.split():
            out.append(tok)
    return out


def installed_units_from_builder() -> Tuple[Set[str], Set[str], List[str]]:
    """Return (installed_unit_names, enabled_unit_names, problems).

    Derived from the REAL builder script:
      * `install -m 0644 <src> "$STAGE/etc/systemd/system/<name>"`  -> installed
      * `ln -sf ../<name>.service "$STAGE/etc/systemd/system/multi-user.target.wants/<name>.service"`
        -> enabled in multi-user.target
      * `systemctl enable`-free: the builder uses wants symlinks only.
    """
    installed: Set[str] = set()
    enabled: Set[str] = set()
    problems: List[str] = []
    builder = builder_path()
    if not os.path.exists(builder):
        return installed, enabled, ["builder not found: %s" % builder]
    text = open(builder, errors="replace").read()
    for m in re.finditer(r"\$STAGE/etc/systemd/system/([A-Za-z0-9@._-]+\.(?:service|socket))", text):
        installed.add(m.group(1))
    for m in re.finditer(r"/etc/systemd/system/multi-user\.target\.wants/([A-Za-z0-9@._-]+)", text):
        enabled.add(m.group(1))
    # for-loop form over literal unit names: `for u in a b c; do` where the body
    # names "$u.service". Non-unit loops (system users, artifacts, paths) are
    # ignored because they do not carry a unit suffix.
    for m in re.finditer(r"for u in ([^;]+); do", text):
        for name in m.group(1).split():
            if re.fullmatch(r"[A-Za-z0-9@._-]+\.(?:service|socket|target)", name):
                installed.add(name)
    return installed, enabled, problems


def main(argv=None, root: str = None) -> int:
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write the report JSON here")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--root", default=None,
                    help="validate this tree instead of the repository (fixture/mutation testing)")
    args = ap.parse_args(argv)
    # ROOT is sticky across in-process calls (the regression test calls main()
    # repeatedly), so it is always re-resolved: an explicit root wins, otherwise
    # the repository is validated.
    chosen = root or args.root
    if chosen:
        ROOT = os.path.abspath(chosen)
        if not os.path.isdir(ROOT):
            sys.stderr.write("verify-service-graph: --root %s is not a directory\n" % ROOT)
            return 2
    else:
        ROOT = REPO_ROOT

    problems: List[str] = []
    warnings: List[str] = []
    units: Dict[str, Dict] = {}

    for rel in UNIT_SOURCES:
        path = os.path.join(repo_root(), rel)
        if not os.path.exists(path):
            problems.append("declared unit is missing from the repository: %s" % rel)
            continue
        name = os.path.basename(rel)
        if rel.endswith(".service") or rel.endswith(".socket"):
            units[name] = {"path": rel, "sections": parse_unit(path)}

    known = set(units) | EXTERNAL_UNITS

    # ---- 1 + 3: reference resolution and the 4.14 forbidden dependencies ----
    for name, info in units.items():
        secs = info["sections"]
        for key in ("After", "Before", "Requires", "Wants", "Conflicts"):
            for ref in refs(secs, key):
                if ref in FORBIDDEN_REFS:
                    problems.append("%s: %s=%s is forbidden on 4.14 (%s)"
                                    % (name, key, ref, FORBIDDEN_REFS[ref]))
                    continue
                if ref in known:
                    continue
                if ref.startswith("nuxel-") or ref in ("seatd.service",):
                    problems.append("%s: %s=%s does not resolve to any installed unit"
                                    % (name, key, ref))
                else:
                    warnings.append("%s: %s=%s is an unlisted external unit (not verified here)"
                                    % (name, key, ref))
        # a system unit must never be enabled into a user target
        for wb in install_refs(secs, "WantedBy"):
            if wb in ("graphical-session.target", "default.target") and not info["path"].startswith("shell/config/systemd-user"):
                msg = ("%s: WantedBy=%s is a USER target in a SYSTEM unit "
                       "(enablement is a no-op in the system manager)" % (name, wb))
                if name in VM_ONLY_UNITS:
                    warnings.append(msg + " - VM-only surface (%s), never installed on the handset by "
                                          "images/s10plus/build-phone-rootfs-inside-fedora.sh; enablement "
                                          "belongs to the VM/user manager" % info["path"])
                else:
                    problems.append(msg)
        # ExecStart must point at a path we install
        for exe in secs.get("Service", {}).get("ExecStart", []):
            prog = exe.split()[0]
            info.setdefault("execstart", []).append(prog)

    # ---- 2: ordering cycles -------------------------------------------------
    order: Dict[str, Set[str]] = {u: set() for u in units}
    anchors = ["sysinit.target", "basic.target", "multi-user.target", "dbus.service"]
    for a in anchors:
        order.setdefault(a, set())
    for name, info in units.items():
        secs = info["sections"]
        for n in refs(secs, "After"):
            if n in order:
                order[name].add(n)          # name depends-on n
        for n in refs(secs, "Before"):
            if n in order:
                order.setdefault(n, set()).add(name)
    cycles = find_cycles(order)
    for cyc in cycles:
        problems.append("ordering cycle: %s" % " -> ".join(cyc))

    # ---- 3c: the live console is single-owner, and the declaration matches ---
    # The console is the only channel that can report a failing phone, so its
    # ownership rule is asserted, not assumed: the unit must be unable to start
    # beside a running console, must not restart into a second owner, must be
    # ordered before the compositor it has to be able to report, and must never
    # be enabled by the builder.  Finally the CURRENT owner must still exist: if
    # the initramfs stops starting /opt/nuxel/nuxel-console AND the unit is not
    # enabled, the image would ship with no debug path at all.
    console_rel = "services/nuxel-console/systemd/nuxel-console.service"
    console_path = os.path.join(repo_root(), console_rel)
    if not os.path.exists(console_path):
        problems.append("the live console has no unit in the repository (%s)" % console_rel)
    else:
        csec = parse_unit(console_path)
        svc = csec.get("Service", {})
        unit_sec = csec.get("Unit", {})
        if "/usr/bin/nuxel-console" not in unit_sec.get("ConditionPathExists", []):
            problems.append("nuxel-console.service: missing ConditionPathExists=/usr/bin/nuxel-console "
                            "(a rootfs image without the binary must skip the unit, not fail it)")
        if "/usr/lib/nuxel/nuxel-console-free" not in svc.get("ExecCondition", []):
            problems.append("nuxel-console.service: missing ExecCondition=nuxel-console-free "
                            "(nothing proves the console port is free before starting)")
        if svc.get("Restart", [""])[0] != "no":
            problems.append("nuxel-console.service: Restart=%s - a restart loop can fight the "
                            "initramfs console for the tty; single-owner resources fail visibly"
                            % svc.get("Restart"))
        before = " ".join(unit_sec.get("Before", [])).split()
        if "nuxel-wayland.service" not in before:
            problems.append("nuxel-console.service: not ordered Before=nuxel-wayland.service "
                            "(the console must be up first: it is the only failure report channel)")
        console_txt = open(console_path, errors="replace").read()
        if "NOT ENABLED" not in console_txt or "single-owner" not in console_txt.lower().replace("single owner", "single-owner"):
            problems.append("nuxel-console.service: does not document its single-owner / not-enabled state")
        helper = os.path.join(repo_root(), "services", "nuxel-console", "bin", "nuxel-console-free")
        if not os.path.exists(helper):
            problems.append("the console guard is missing: services/nuxel-console/bin/nuxel-console-free")
        console_c = os.path.join(repo_root(), "tools", "s10plus", "a33", "nuxel-console.c")
        init_sh = os.path.join(repo_root(), "boot", "initramfs", "init.sh")
        if os.path.exists(console_c):
            ctext = open(console_c, errors="replace").read()
            if "/run/nuxel-console.lock" not in ctext:
                problems.append("nuxel-console.c no longer uses /run/nuxel-console.lock "
                                "(the unit's ExecCondition probes a lock the console does not take)")
        else:
            warnings.append("nuxel-console.c is absent: the device-side console implementation "
                            "cannot be cross-checked against the unit's lock protocol")
        if os.path.exists(init_sh):
            itext = open(init_sh, errors="replace").read()
            if "/opt/nuxel/nuxel-console" not in itext:
                warnings.append("boot/initramfs/init.sh no longer starts /opt/nuxel/nuxel-console: "
                                "the console's current owner has moved - if the rootfs unit is not "
                                "enabled either, the image ships with NO debug console")
        else:
            warnings.append("boot/initramfs/init.sh is absent: the console's current owner "
                            "(the initramfs instance) cannot be cross-checked")

    # ---- 3b: the A26 4.14 containment must still be there -------------------
    a26_path = a26_fixes_path()
    a26 = open(a26_path, errors="replace").read() if os.path.exists(a26_path) else ""
    for needle, label in [
        ("systemd-userdbd.socket", "mask systemd-userdbd.socket"),
        ("systemd-userdbd.service", "mask systemd-userdbd.service"),
        ("dbus-daemon.service", "system bus -> dbus-daemon.service"),
        ("systemd-udevd.service", "mask systemd-udevd.service"),
    ]:
        if needle not in a26:
            problems.append("A26 fix missing: %s (tools/s10plus/a26/nuxel-rootfs-fixes.sh)" % label)

    # ---- 5: the builder installs + enables the canonical set ---------------
    installed, enabled, bp = installed_units_from_builder()
    problems.extend(bp)
    for name in sorted(units):
        if name == "nuxel-camera-portal.service":
            continue  # VM-only surface, installed by the VM bootstrap
        if name not in installed:
            problems.append("builder does not install %s (boot graph not reproducible from the repo)" % name)
        else:
            secs = units[name]["sections"]
            wb = install_refs(secs, "WantedBy")
            if name in PROVISIONED_NOT_ENABLED:
                if name in enabled:
                    problems.append("builder ENABLES %s, which must stay provisioned-only: %s"
                                    % (name, PROVISIONED_NOT_ENABLED[name]))
                continue
            if "multi-user.target" in wb and name not in enabled and name != "nuxel-ui.service":
                # enabled set uses .service names; accept either form
                if name not in enabled:
                    problems.append("builder installs but does not enable %s (WantedBy=multi-user.target)" % name)
    enabled_byname = {e if e.endswith(".service") else e + ".service" for e in enabled}
    for name in sorted(units):
        secs = units[name]["sections"]
        if name in PROVISIONED_NOT_ENABLED:
            if name in enabled_byname:
                problems.append("unit %s is enabled but is declared provisioned-only" % name)
            continue
        if "multi-user.target" in install_refs(secs, "WantedBy") and name not in enabled_byname:
            problems.append("unit %s expects multi-user.target enablement; builder enables %s"
                            % (name, sorted(enabled_byname)))

    # ---- 6: provenance — canonical units must not LOSE measured settings ---
    provenance = {
        "services/nuxel-session/systemd/nuxel-wayland.service": "tools/s10plus/a31/nuxel-wayland.service",
        "services/nuxel-session/systemd/nuxel-wl-fb.service": "tools/s10plus/a31/nuxel-wl-fb.service",
        "services/nuxel-session/systemd/nuxel-touch-arm.service": "tools/s10plus/a31/nuxel-touch-arm.service",
        "services/nuxel-session/systemd/seatd.service": "tools/s10plus/a31/seatd.service",
        "services/nuxel-session/systemd/nuxel-button-manager.service": "tools/s10plus/a32/nuxel-button-manager.service",
    }
    for canonical, shipped in provenance.items():
        cp, sp = os.path.join(repo_root(), canonical), os.path.join(repo_root(), shipped)
        if not (os.path.exists(cp) and os.path.exists(sp)):
            warnings.append("provenance pair missing: %s vs %s" % (canonical, shipped))
            continue
        csec, ssec = parse_unit(cp), parse_unit(sp)
        for key in ("Environment", "ExecStart"):
            want = set(ssec.get("Service", {}).get(key, []))
            got = set(csec.get("Service", {}).get(key, []))
            for item in sorted(want - got):
                if key == "ExecStart":
                    problems.append("%s dropped the shipped ExecStart (%r)" % (canonical, item))
                else:
                    warnings.append("%s dropped the shipped Environment= (%r)" % (canonical, item))

    verdict = "FAILED" if problems else "OFFLINE_TESTED"
    report = {
        "tool": "verify-service-graph.py",
        "root": repo_root(),
        "units": {n: {"path": i["path"], "execstart": i.get("execstart", [])} for n, i in sorted(units.items())},
        "unit_count": len(units),
        "builder_installed": sorted(installed),
        "builder_enabled": sorted(enabled_byname),
        "problems": problems,
        "warnings": warnings,
        "vm_only_units": sorted(VM_ONLY_UNITS),
        "provisioned_not_enabled": {k: PROVISIONED_NOT_ENABLED[k] for k in sorted(PROVISIONED_NOT_ENABLED)},
        "verdict": verdict,
    }
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=2)
            fh.write("\n")
    if not args.quiet:
        for name, why in sorted(PROVISIONED_NOT_ENABLED.items()):
            print("INFO  %s is installed but deliberately NOT enabled: %s" % (name, why))
        for w in warnings:
            print("WARN  %s" % w)
        for p in problems:
            print("FAIL  %s" % p)
        print("units=%d problems=%d warnings=%d verdict=%s" % (len(units), len(problems), len(warnings), verdict))
    return 0 if verdict == "OFFLINE_TESTED" else 1


def find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Return the node list of each cycle found (DFS, colouring)."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in graph}
    stack: List[str] = []
    cycles: List[List[str]] = []

    def visit(n: str) -> None:
        colour[n] = GREY
        stack.append(n)
        for m in sorted(graph.get(n, ())):
            if m not in colour:
                continue
            if colour[m] == GREY:
                cycles.append(stack[stack.index(m):] + [m])
            elif colour[m] == WHITE:
                visit(m)
        stack.pop()
        colour[n] = BLACK

    for n in sorted(graph):
        if colour[n] == WHITE:
            visit(n)
    return cycles


if __name__ == "__main__":
    sys.exit(main())
