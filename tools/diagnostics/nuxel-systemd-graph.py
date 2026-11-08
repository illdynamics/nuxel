#!/usr/bin/env python3
"""Nuxel systemd boot/shutdown evidence collector (PWNAGE-90000 P90-12).

Collects real measurements from the machine it runs on (the Nuxel phone when
invoked there), never from a build laptop.  Every timing in the generated
report comes from systemd/journal output or a /proc/stat-derived file age; no
missing value is replaced with zero.

Usage:
  nuxel-systemd-graph.py --output SYSTEMD-GRAPH.md \
      --assets-dir diagnostics/systemd --boot current --include-shutdown

Stdlib only.  External commands are invoked as argv arrays, never through a
shell.  Raw outputs are saved next to the report with SHA-256 metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
CRITICAL_UNITS = [
    "nuxel-wayland.service", "nuxel-wl-fb.service", "nuxel-bridge.service",
    "nuxel-http-bridge.service", "nuxel-web.service", "nuxel-ui.service",
    "nuxel-session.service", "nuxel-boot-sound.service",
    "nuxel-app-prewarm.service", "nuxel-touch-arm.service",
    "nuxel-preload-cinema.service", "nuxel-notifications.service",
    "seatd.service", "systemd-journald.service", "systemd-udevd.service",
]
READY_PATHS = [
    "/run/nuxel-launcher-ready",
    "/run/nuxel-home.state",
    "/run/nuxel/preload-cinema.receipt",
]


def run(argv: list[str], timeout: int = 30) -> dict:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, errors="replace")
        return {"argv": argv, "rc": proc.returncode,
                "out": proc.stdout or "", "err": proc.stderr or ""}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"argv": argv, "rc": -1, "out": "", "err": str(exc)}


def read(path: str, limit: int = 65536) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def write_asset(assets: Path, name: str, text: str | bytes) -> dict:
    assets.mkdir(parents=True, exist_ok=True)
    path = assets / name
    data = text.encode() if isinstance(text, str) else text
    path.write_bytes(data)
    return {"path": name, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def parse_systemd_time(text: str) -> dict:
    """Parse `systemd-analyze time`; absent phases are omitted, not zeroed."""
    phases: dict[str, float] = {}
    total = None
    m = re.search(r"Startup finished in (.*?)\.?$", text.strip(), re.M)
    line = m.group(1) if m else text.strip().splitlines()[0] if text.strip() else ""
    for value, unit, label in re.findall(r"([0-9.]+)\s*(ms|s)\s*\(([^)]+)\)", line):
        phases[label.strip()] = float(value) / (1000.0 if unit == "ms" else 1.0)
    mt = re.search(r"=\s*([0-9.]+)\s*s\s*$", line)
    if mt:
        total = float(mt.group(1))
    if not phases and not total:
        return {"raw": text.strip(), "phases_s": {}, "total_s": None,
                "available": False}
    return {"raw": text.strip(), "phases_s": phases, "total_s": total,
            "available": True}


def parse_blame(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = re.match(r"\s*([0-9.]+)(ms|s|min)\s+(\S+)", line)
        if not m:
            continue
        value, unit, unit_name = m.groups()
        seconds = float(value)
        if unit == "ms":
            seconds /= 1000.0
        elif unit == "min":
            seconds *= 60.0
        rows.append({"unit": unit_name, "seconds": round(seconds, 3),
                     "raw": line.strip()})
    return rows


def parse_critical_chain(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = re.match(r"[│├└─\s]*([^\s@]+) @([0-9.]+)s", line)
        if m:
            rows.append({"unit": m.group(1), "at_s": float(m.group(2)),
                         "raw": line.strip()})
    return rows


def parse_show(text: str) -> dict:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out


def parse_journal_shutdown(text: str) -> dict:
    """Extract an honest shutdown timeline from a previous-boot journal.

    Boot-time service restarts ("Stopping...") are not shutdown evidence.  We
    anchor on the final manager handoff ("System is rebooting/powering down",
    "Reached target Shutdown", "systemd-shutdown") and keep only the bounded
    window immediately before/after it.  If no anchor exists, the final 60 s of
    the journal is used and labelled as such.
    """
    candidates = []
    anchor_rx = re.compile(
        r"System is (?:re)?booting|System is powering down|Reached target.*"
        r"(?:Shutdown|Reboot|Power-Off)|systemd-shutdown|reboot: (?:Restarting|Power down)",
        re.I)
    event_rx = re.compile(
        r"Reached target.*(?:Shutdown|Reboot|Power-Off|System Power Off)|"
        r"Stopping .*\.\.\.|Stopped .*\.\.\.|systemd-shutdown|"
        r"Powering off|Rebooting|Unmounting .*|reboot: (?:Restarting|Power down)|"
        r"Reached target.*Final Step|Timed out (?:stopping|starting) .*|"
        r"Job .* timed out", re.I)
    anchor_ts = None
    for line in text.splitlines():
        m = re.match(r"\s*\[\s*([0-9.]+)\]", line)
        ts = float(m.group(1)) if m else None
        if ts is not None and anchor_rx.search(line):
            anchor_ts = ts
        if event_rx.search(line):
            candidates.append({"monotonic_s": ts, "line": line.strip()[:300]})
    if not candidates:
        return {"status": "NOT_CAPTURED", "events": [],
                "first_monotonic_s": None, "last_monotonic_s": None,
                "span_s": None,
                "reason": "no shutdown/handoff events in the previous-boot journal"}
    if anchor_ts is not None:
        window_start = anchor_ts - 60.0
        events = [e for e in candidates
                  if e["monotonic_s"] is not None and e["monotonic_s"] >= window_start]
        basis = "anchored on final manager handoff (60 s pre-window)"
    else:
        timed = [e for e in candidates if e["monotonic_s"] is not None]
        if timed:
            window_start = max(e["monotonic_s"] for e in timed) - 60.0
            events = [e for e in candidates
                      if e["monotonic_s"] is not None and e["monotonic_s"] >= window_start]
        else:
            events = candidates
        basis = "no explicit handoff marker; final 60 s of journal"
    if not events:
        events = candidates[-40:]
        basis += " (fallback to final 40 events)"
    timed = [e["monotonic_s"] for e in events if e["monotonic_s"] is not None]
    first_ts = min(timed) if timed else None
    last_ts = max(timed) if timed else None
    return {"status": "CAPTURED", "events": events,
            "first_monotonic_s": first_ts, "last_monotonic_s": last_ts,
            "span_s": (round(last_ts - first_ts, 3)
                       if first_ts is not None and last_ts is not None else None),
            "basis": basis}


def boot_time_epoch() -> float | None:
    try:
        uptime = float(read("/proc/uptime").split()[0])
        return time.time() - uptime
    except (OSError, ValueError, IndexError):
        return None


def file_ready_after_boot(path: str) -> dict:
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        return {"path": path, "exists": False}
    bt = boot_time_epoch()
    return {"path": path, "exists": True,
            "after_boot_s": (round(mtime - bt, 3) if bt else None),
            "mtime_utc": datetime.fromtimestamp(mtime, timezone.utc).isoformat()}


def collect(boot: str, include_shutdown: bool) -> dict:
    context = {
        "schema_version": SCHEMA_VERSION,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "timezone": time.tzname,
        "hostname": platform.node(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "systemd_version": read("/etc/systemd/system.conf").splitlines()[:0] or
                           (run(["systemctl", "--version"]).get("out", "").splitlines() or [""])[0],
        "boot_id": read("/proc/sys/kernel/random/boot_id").strip(),
        "uptime_s": read("/proc/uptime").strip(),
        "model": read("/proc/device-tree/model").strip("\x00\n "),
        "os_release": {},
        "journal_persistent": os.path.isdir("/var/log/journal"),
        "root_fs": "",
        "device_version": read("/usr/share/nuxel/VERSION").strip() or read("/opt/nuxel/VERSION").strip(),
    }
    for line in read("/etc/os-release").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            context["os_release"][k] = v.strip('"')
    context["root_fs"] = run(["findmnt", "-n", "-o", "FSTYPE", "/"]).get("out", "").strip()

    journal_boot = "0" if boot == "current" else "-1"
    analyze = {}
    raw: dict[str, dict] = {}
    if boot == "current":
        for name, argv in (
            ("boot-systemd-analyze.txt", ["systemd-analyze", "time"]),
            ("boot-blame.txt", ["systemd-analyze", "blame"]),
            ("boot-critical-chain.txt", ["systemd-analyze", "critical-chain"]),
        ):
            res = run(argv)
            raw[name] = res
            analyze[name] = res["out"]
    else:
        analyze["boot-systemd-analyze.txt"] = "NOT AVAILABLE: systemd-analyze only reports the current boot\n"

    units_raw = run(["systemctl", "list-units", "--all", "--no-legend", "--plain"])
    failed_raw = run(["systemctl", "--failed", "--no-legend", "--plain"])
    boots_raw = run(["journalctl", "--list-boots", "--no-pager"])

    unit_names = set(CRITICAL_UNITS)
    for line in units_raw["out"].splitlines():
        parts = line.split()
        if parts and ("nuxel" in parts[0].lower() or parts[0] in ("seatd.service",)):
            unit_names.add(parts[0])
    unit_props: dict[str, dict] = {}
    for unit in sorted(unit_names):
        res = run(["systemctl", "show", unit, "--no-pager",
                   "--property=ActiveState,SubState,Result,"
                   "ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,"
                   "ActiveEnterTimestampMonotonic,InactiveExitTimestampMonotonic,"
                   "TimeoutStartUSec,TimeoutStopUSec,NRestarts,Before,After,Wants,Requires,Conflicts"])
        props = parse_show(res["out"])
        start = props.get("ExecMainStartTimestampMonotonic")
        end = props.get("ExecMainExitTimestampMonotonic")
        duration = None
        try:
            if start not in (None, "", "0") and end not in (None, "", "0"):
                duration = round((int(end) - int(start)) / 1000.0, 3)
        except (TypeError, ValueError):
            duration = None
        props["_duration_ms"] = duration
        props["_unit"] = unit
        unit_props[unit] = props

    # Optional graphs.
    assets: dict[str, dict] = {}
    plot_ok = False
    if boot == "current":
        try:
            svg_path = ASSETS_DIR / "SYSTEMD-BOOT.svg"
            with svg_path.open("w", encoding="utf-8") as fh:
                proc = subprocess.run(["systemd-analyze", "plot"], stdout=fh,
                                      stderr=subprocess.PIPE, text=True, timeout=60)
            if proc.returncode == 0 and svg_path.stat().st_size > 1000:
                plot_ok = True
                assets["SYSTEMD-BOOT.svg"] = {
                    "path": svg_path.name,
                    "bytes": svg_path.stat().st_size,
                    "sha256": hashlib.sha256(svg_path.read_bytes()).hexdigest()}
            else:
                svg_path.unlink(missing_ok=True)
        except (OSError, subprocess.TimeoutExpired):
            plot_ok = False

    # Shutdown evidence from real previous-boot journal data only.
    shutdown = {"status": "NOT_CAPTURED", "events": [], "reason": "not requested"}
    shutdown_raw = ""
    if include_shutdown:
        prev = run(["journalctl", "-b", "-1", "-o", "short-monotonic", "--no-pager"], timeout=60)
        shutdown_raw = prev["out"]
        if prev["rc"] != 0 or not shutdown_raw.strip():
            shutdown = {"status": "NOT_CAPTURED", "events": [],
                        "reason": "previous-boot journal unavailable or empty; "
                                  "enable persistent journald and capture the next normal shutdown"}
        else:
            shutdown = parse_journal_shutdown(shutdown_raw)

    raw["boot-units.tsv"] = {"argv": ["systemctl", "show"], "rc": 0,
                             "out": "\n".join(
                                 "\t".join([u, p.get("ActiveState", ""), p.get("SubState", ""),
                                            p.get("Result", ""),
                                            str(p.get("_duration_ms") if p.get("_duration_ms") is not None else "NA"),
                                            p.get("ExecMainStartTimestampMonotonic", ""),
                                            p.get("ActiveEnterTimestampMonotonic", "")])
                                 for u, p in sorted(unit_props.items())) + "\n", "err": ""}
    raw["boot-list-units.txt"] = units_raw
    raw["boot-failed.txt"] = failed_raw
    raw["boots.txt"] = boots_raw
    raw["shutdown-journal-summary.txt"] = {"argv": ["journalctl", "-b", "-1"], "rc": 0,
                                           "out": "", "err": ""}
    if shutdown.get("status") == "CAPTURED":
        svg = render_shutdown_svg(shutdown.get("events", []))
        if svg:
            assets["SYSTEMD-SHUTDOWN.svg"] = write_asset(
                ASSETS_DIR, "SYSTEMD-SHUTDOWN.svg", svg)
    raw["boot-metadata-inputs.txt"] = {
        "argv": ["/proc", "os-release", "device-tree"], "rc": 0,
        "out": json.dumps({k: context[k] for k in
                           ("boot_id", "uptime_s", "kernel", "architecture",
                            "journal_persistent", "root_fs", "model")}, indent=2) + "\n",
        "err": ""}

    ready = [file_ready_after_boot(p) for p in READY_PATHS]
    result = {
        "context": context, "analyze": analyze,
        "time": parse_systemd_time(analyze.get("boot-systemd-analyze.txt", "")),
        "blame": parse_blame(analyze.get("boot-blame.txt", "")),
        "critical_chain": parse_critical_chain(analyze.get("boot-critical-chain.txt", "")),
        "units": unit_props, "ready": ready, "shutdown": shutdown,
        "plot_ok": plot_ok, "assets": assets, "raw": raw, "boot": boot,
    }
    # Save raw artifacts with checksums.
    for name, res in raw.items():
        if name == "shutdown-journal-summary.txt":
            text = (f"status={shutdown.get('status')}\nreason={shutdown.get('reason','')}\n"
                    + "".join(e["line"] + "\n" for e in shutdown.get("events", [])))
            if shutdown_raw:
                text += "\n--- raw previous-boot journal tail ---\n" + "\n".join(
                    shutdown_raw.splitlines()[-400:]) + "\n"
            assets[name] = write_asset(ASSETS_DIR, name, text)
        else:
            assets[name] = write_asset(ASSETS_DIR, name,
                                       f"$ {' '.join(res['argv'])}\nrc={res['rc']}\n"
                                       f"--- stdout ---\n{res['out']}\n--- stderr ---\n{res['err']}\n")
    result["assets"] = assets
    meta = {
        "schema_version": SCHEMA_VERSION,
        "collected_at_utc": context["collected_at_utc"],
        "boot": boot,
        "boot_id": context["boot_id"],
        "hostname": context["hostname"],
        "model": context["model"],
        "kernel": context["kernel"],
        "systemd_version": context["systemd_version"],
        "shutdown_status": shutdown.get("status"),
        "plot": bool(plot_ok),
        "assets": assets,
    }
    assets["collector-metadata.json"] = write_asset(
        ASSETS_DIR, "collector-metadata.json",
        json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return result


def fmt_s(value) -> str:
    return "NA" if value is None else f"{value:.3f}s"


def _xml(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render_shutdown_svg(events: list[dict]) -> str:
    """Simple honest timeline built only from captured journal events."""
    timed = [e for e in events if e.get("monotonic_s") is not None]
    if not timed:
        return ""
    t0 = min(e["monotonic_s"] for e in timed)
    t1 = max(e["monotonic_s"] for e in timed)
    span = max(0.001, t1 - t0)
    width, left, right = 1200, 260, 1160
    row_h = 26
    height = max(180, 70 + row_h * len(timed))
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="monospace">',
        '<rect width="100%" height="100%" fill="#0b0f14"/>',
        '<text x="20" y="30" fill="#e8eef6" font-size="18">Nuxel shutdown journal timeline '
        f'(monotonic {t0:.3f}s → {t1:.3f}s, span {span:.3f}s)</text>',
        f'<line x1="{left}" y1="50" x2="{right}" y2="50" stroke="#22303f" stroke-width="1"/>',
    ]
    for i, e in enumerate(timed):
        ts = e["monotonic_s"]
        x = left + (ts - t0) / span * (right - left)
        y = 70 + i * row_h
        label = str(e.get("line", ""))[-110:]
        out.append(f'<line x1="{x:.2f}" y1="50" x2="{x:.2f}" y2="{height-16}" '
                   f'stroke="#2b4a6b" stroke-width="1"/>')
        out.append(f'<circle cx="{x:.2f}" cy="{y}" r="3" fill="#5ac8fa"/>')
        out.append(f'<text x="20" y="{y+4}" fill="#8fa3b8" font-size="11">'
                   f'{ts:.3f}s</text>')
        out.append(f'<text x="{min(x+8, right-10):.2f}" y="{y+4}" fill="#e8eef6" '
                   f'font-size="11">{_xml(label)}</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"


def render(data: dict) -> str:
    c = data["context"]
    t = data["time"]
    s = data["shutdown"]
    lines: list[str] = []
    add = lines.append
    add("# Nuxel systemd boot & shutdown analysis")
    add("")
    add("> Generated by `tools/diagnostics/nuxel-systemd-graph.py` from the machine "
        "it was executed on. No timing is fabricated; unavailable values say `NA` "
        "or `NOT CAPTURED`.")
    add("")
    add("## 1. Device and collection context")
    add("")
    add(f"- Collected: `{c['collected_at_utc']}` (timezone `{c['timezone']}`)")
    add(f"- Host: `{c['hostname']}`, model `{c['model'] or 'NA'}`")
    add(f"- OS: `{c['os_release'].get('PRETTY_NAME', 'NA')}`")
    add(f"- Kernel: `{c['kernel']}`, architecture `{c['architecture']}`")
    add(f"- systemd: `{c['systemd_version']}`")
    add(f"- Boot ID: `{c['boot_id'][:12]}`")
    add(f"- Uptime at collection: `{c['uptime_s']}`")
    add(f"- Nuxel version on device: `{c['device_version'] or 'NA'}`")
    add(f"- Root filesystem type: `{c['root_fs'] or 'NA'}`")
    add(f"- Persistent journal: `{'yes' if c['journal_persistent'] else 'no (volatile)'}`")
    add("")
    add("## 2. Boot summary")
    add("")
    if t.get("available"):
        add("| Phase | Measured |")
        add("|---|---:|")
        for phase, value in t["phases_s"].items():
            add(f"| {phase} | {value:.3f}s |")
        add(f"| **total** | **{fmt_s(t.get('total_s'))}** |")
    else:
        add(f"`systemd-analyze time` unavailable for this boot: {t.get('raw', 'NA')}")
    add("")
    add("Nuxel UI readiness (measured from `/proc/uptime` and file mtimes):")
    add("")
    add("| Marker | Exists | After boot |")
    add("|---|---:|---:|")
    for r in data["ready"]:
        add(f"| `{r['path']}` | {'yes' if r['exists'] else 'no'} | "
            f"{r.get('after_boot_s', 'NA')} |")
    add("")
    add("## 3. Service timing table")
    add("")
    add("Activation start/elapsed are same-boot monotonic values from "
        "`systemctl show`; `NA` means the property is absent for that unit.")
    add("")
    add("| Unit | Active | Sub | Result | Exec start (ms) | Duration (ms) | NRestarts | Critical path |")
    add("|---|---|---|---|---:|---:|---:|---:|")
    crit = {row["unit"] for row in data["critical_chain"]}
    for unit, p in sorted(data["units"].items()):
        if p.get("ActiveState", "") in ("inactive", "failed") and unit not in CRITICAL_UNITS:
            continue
        dur = p.get("_duration_ms")
        add(f"| `{unit}` | {p.get('ActiveState', 'NA')} | {p.get('SubState', 'NA')} | "
            f"{p.get('Result', 'NA')} | {p.get('ExecMainStartTimestampMonotonic', 'NA')} | "
            f"{dur if dur is not None else 'NA'} | {p.get('NRestarts', 'NA')} | "
            f"{'yes' if unit in crit else 'no'} |")
    add("")
    add("### `systemd-analyze blame` (raw ordering, caveat below)")
    add("")
    add("| # | Unit | Seconds |")
    add("|---:|---|---:|")
    for i, row in enumerate(data["blame"][:25], 1):
        add(f"| {i} | `{row['unit']}` | {row['seconds']:.3f} |")
    add("")
    add("`systemd-analyze blame` is not a pure performance ranking: a unit can be "
        "waiting on a dependency, and `Type=simple` units do not expose the same "
        "activation duration. Treat it as a starting point, not a verdict.")
    add("")
    add("## 4. Boot graph")
    add("")
    if data.get("plot_ok"):
        add("![systemd boot plot](diagnostics/systemd/SYSTEMD-BOOT.svg)")
        add("")
        add("`systemd-analyze plot` is boot-only. It shows service activation "
            "windows for the current boot and is **not** a shutdown timeline.")
    else:
        add("`systemd-analyze plot` produced no usable SVG on this run (`NA`).")
    add("")
    add("## 5. Critical path narrative")
    add("")
    if data["critical_chain"]:
        add("The default-target critical chain recorded these points:")
        add("")
        add("| Unit | At (s) |")
        add("|---|---:|")
        for row in data["critical_chain"]:
            add(f"| `{row['unit']}` | {row['at_s']:.3f} |")
        add("")
    else:
        add("No parsable `systemd-analyze critical-chain` output was captured (`NA`).")
        add("")
    add("Interpretation of what gates the graphical session should be read from "
        "the chain above plus the Nuxel unit table, not from the slowest blame "
        "entry. Device-specific observations are recorded in the mission report.")
    add("")
    add("## 6. Shutdown timeline")
    add("")
    if s.get("status") == "CAPTURED":
        add(f"- Status: **CAPTURED** from the previous-boot journal")
        add(f"- First shutdown event: `{s.get('first_monotonic_s')}` s (monotonic)")
        add(f"- Last shutdown event: `{s.get('last_monotonic_s')}` s (monotonic)")
        add(f"- Observed span: `{fmt_s(s.get('span_s'))}`")
        if s.get("basis"):
            add(f"- Window: {s['basis']}")
        add("")
        if "SYSTEMD-SHUTDOWN.svg" in data.get("assets", {}):
            add("![systemd shutdown journal timeline](diagnostics/systemd/SYSTEMD-SHUTDOWN.svg)")
            add("")
            add("The SVG is built only from the captured previous-boot journal "
                "events below; it is not a boot plot.")
            add("")
        add("| Monotonic (s) | Event |")
        add("|---:|---|")
        for ev in s["events"][-60:]:
            add(f"| {ev.get('monotonic_s', 'NA')} | `{ev['line'][:240]}` |")
    else:
        add("**NOT CAPTURED**")
        add("")
        add(f"Reason: {s.get('reason', 'unknown')}.")
        add("")
        add("Next capture (safe, next normal shutdown only): persist journald "
            "(documented storage/consent change), then run:")
        add("")
        add("```sh")
        add("journalctl --list-boots")
        add("journalctl -b -1 -o short-monotonic --no-pager > /tmp/prev-boot.txt")
        add("python3 tools/diagnostics/nuxel-systemd-graph.py --boot previous --include-shutdown \\")
        add("  --output SYSTEMD-GRAPH.md --assets-dir diagnostics/systemd")
        add("```")
    add("")
    add("## 7. Evidence-ranked optimization shortlist")
    add("")
    add("1. **Nuxel UI readiness chain** — start from `nuxel-wayland.service`, "
        "`nuxel-wl-fb.service`, `nuxel-web.service` and the launcher-ready marker "
        "rather than the global blame list.")
    add("2. **Dependency waits** — inspect `Before/After/Wants/Requires` in "
        "`diagnostics/systemd/boot-units.tsv` before changing ordering.")
    add("3. **Shutdown stop intervals** — only optimize a unit whose own stop "
        "execution (not dependency wait) is measured as long in the shutdown table.")
    add("")
    add("No unit dependency was changed by this collector.")
    add("")
    add("## 8. Methodology and reproduction")
    add("")
    add("```sh")
    add("python3 tools/diagnostics/nuxel-systemd-graph.py \\")
    add(f"  --boot {data.get('boot', 'current')} --include-shutdown \\")
    add("  --output SYSTEMD-GRAPH.md --assets-dir diagnostics/systemd")
    add("```")
    add("")
    add("Raw commands are recorded verbatim in the asset files; they were invoked "
        "as argv arrays without a shell.")
    add("")
    add("## 9. Data integrity statement")
    add("")
    add("- Durations are computed only when both start and exit monotonic "
        "timestamps exist in the same boot.")
    add("- Missing properties are shown as `NA`; they are never substituted with zero.")
    add("- Shutdown data comes only from the real previous-boot journal. If it is "
        "absent, the section says `NOT CAPTURED`.")
    add("- `systemd-analyze plot` is not used as shutdown evidence.")
    add("")
    add("## 10. Privacy note")
    add("")
    add("Only unit names, systemd timing properties, kernel/model/OS identifiers "
        "and file-age markers are collected. Environment dumps, credentials, "
        "notification bodies, private URLs and application data are not read.")
    add("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    global ASSETS_DIR
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="SYSTEMD-GRAPH.md")
    ap.add_argument("--assets-dir", default="diagnostics/systemd")
    ap.add_argument("--boot", choices=["current", "previous"], default="current")
    ap.add_argument("--include-shutdown", action="store_true")
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args(argv)
    ASSETS_DIR = Path(args.assets_dir)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    data = collect(args.boot, args.include_shutdown)
    if args.json_only:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    report = render(data)
    Path(args.output).write_text(report, encoding="utf-8")
    print(f"wrote {args.output} and {len(data['assets'])} asset(s) in {ASSETS_DIR}")
    print(f"shutdown={data['shutdown']['status']} plot={'yes' if data['plot_ok'] else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
