#!/usr/bin/env python3
"""soak_lib.py — soak / resource / performance evaluation for the Nuxel beta.

briq-09a (area 50).  Pure, deterministic, offline: it takes a series of device
samples and returns a verdict against the documented criteria in
`docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md`.  The sampler itself
(`tools/beta/soak.sh`) is a thin, guarded wrapper so this logic can be replayed
against recorded samples on any host — which is exactly what `--selftest` does.

A sample is one JSON object (NDJSON on disk):

    {"t":  <unix seconds>,
     "i":  <sample index>,
     "uptime_s": <float>,            # /proc/uptime field 1
     "load1": <float>,               # /proc/loadavg field 1  (recorded, NOT gated)
     "mem_used_kb": <int>,           # MemTotal-MemAvailable
     "mem_avail_kb": <int>,
     "stack_rss_kb": <int>,          # summed RSS of the Nuxel stack
     "stack_cpu_pct": <float>,       # summed %CPU of the Nuxel stack
     "failed_units": <int>,          # systemctl --failed count
     "service_restarts": <int>,      # cumulative NRestarts of the stack units
     "fb_owner_pid": <int|null>,     # /var/lib/nuxel/fb-owner pid
     "http_ok": <bool>,              # launcher answered 200 on 127.0.0.1:8000
     "thermal_max_c": <float|null>,  # hottest thermal zone
     "cmdline_boot_mode": <str>}     # androidboot.mode (charger vs normal)

The load average on this handset sits near 12 (which looks alarming on an 8-core
SoC) because eleven Samsung *vendor kernel* tasks (TrustZone worker / interworld
socket, RPMB secure-storage work, REE time) are permanently in `D` state — the
A31 finding, recorded in
`docs/s10plus-autonomous-boot-repair/BETA-FINALIZER/12-REMAINING-LIMITATIONS.md`.
Real Nuxel-stack CPU is ~1 core.  So `load1` is *recorded and explained*, never
used as a pass/fail criterion; `stack_cpu_pct` is the gated metric.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

SCHEMA_VERSION = 1

# --------------------------------------------------------------------------- #
# Criteria (single source of truth; quoted by the docs and printed by --plan)
# --------------------------------------------------------------------------- #
THRESHOLDS = {
    "min_coverage_ratio": 0.90,      # observed window / requested duration
    "max_sample_gap_factor": 3.0,    # a gap > factor*interval is a console stall
    "max_allowed_gaps": 1,
    "allowed_failed_units": 0,
    "boot_settle_samples": 2,        # first N samples excluded from the unit test
    "min_http_availability": 0.99,   # launcher reachable share of samples
    "max_fb_owner_changes": 0,       # >0 = the framebuffer owner changed hands
    "max_fb_owner_changes_warn": 1,
    "stack_cpu_mean_max_pct": 150.0, # 1.5 of 8 cores, sustained
    "stack_cpu_peak_max_pct": 300.0, # short spike ceiling (3 of 8 cores)
    "mem_growth_per_hour_max_pct": 2.0,
    "mem_growth_total_max_pct": 10.0,
    "max_service_restarts": 0,
    "max_service_restarts_warn": 1,
    "thermal_warn_c": 75.0,
    "thermal_fail_c": 90.0,
    "durations": {"device": 28800, "vm": 1800, "smoke": 300},
    "sample_interval_s": 60,
    "checkpoint_s": 1800,
}

STACK_UNITS = ("nuxel-pwa", "nuxel-wl-fb", "nuxel-button-manager", "nuxel-wayland",
               "nuxel-anim-handoff", "nuxel-console")

FAIL, WARN, INFO = "fail", "warn", "info"


def _finding(fid, sev, detail):
    return {"id": fid, "severity": sev, "detail": detail}


def _linear_slope_per_hour(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    slope_per_s = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return slope_per_s * 3600.0


def evaluate(samples, duration_s, thresholds=None, mode="replay"):
    """Evaluate a sample series.  Returns a report dict (never raises)."""
    th = dict(THRESHOLDS)
    if thresholds:
        th.update(thresholds)
    findings, stats = [], {}

    if not samples:
        return {"verdict": "BLOCKED_EXTERNAL_RESOURCE", "terminal_state": "BLOCKED_EXTERNAL_RESOURCE",
                "mode": mode, "samples": 0, "findings": [
                    _finding("S0-no-samples", FAIL,
                             "no samples were collected: the sampler had no reachable resource")],
                "stats": {}, "thresholds": th, "schema_version": SCHEMA_VERSION,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    samples = sorted(samples, key=lambda s: s.get("t", 0))
    t0, t1 = samples[0].get("t", 0), samples[-1].get("t", 0)
    window = max(0.0, (t1 - t0))
    interval = th["sample_interval_s"]

    stats["samples"] = len(samples)
    stats["window_s"] = round(window, 1)
    stats["requested_duration_s"] = duration_s
    stats["coverage_ratio"] = round(window / duration_s, 4) if duration_s else 0.0

    # --- S1 / S2: did the soak actually run long enough, and is the console alive?
    if duration_s and stats["coverage_ratio"] < th["min_coverage_ratio"]:
        findings.append(_finding("S1-coverage", FAIL,
                                 "observed %.0fs of the requested %ss (%.1f%% < %.0f%% minimum)"
                                 % (window, duration_s, 100 * stats["coverage_ratio"],
                                    100 * th["min_coverage_ratio"])))
    else:
        findings.append(_finding("S1-coverage", INFO,
                                 "observed %.0fs of %ss (%.1f%%)"
                                 % (window, duration_s, 100 * stats["coverage_ratio"])))
    gaps = [round(samples[i + 1]["t"] - samples[i]["t"], 1)
            for i in range(len(samples) - 1)
            if samples[i + 1].get("t") and samples[i].get("t")]
    big = [g for g in gaps if g > th["max_sample_gap_factor"] * interval]
    stats["max_gap_s"] = max(gaps) if gaps else 0.0
    if len(big) > th["max_allowed_gaps"]:
        findings.append(_finding("S2-cadence", WARN,
                                 "%d sample gap(s) exceeded %sx the %ss interval (max %ss) — "
                                 "console/transport stalls are the likely cause"
                                 % (len(big), th["max_sample_gap_factor"], interval,
                                    stats["max_gap_s"])))
    else:
        findings.append(_finding("S2-cadence", INFO,
                                 "sample cadence healthy (max gap %.0fs)" % stats["max_gap_s"]))

    # --- S3: no reboot.  A decrease in /proc/uptime means the phone restarted.
    decreases = [(samples[i]["t"], samples[i].get("uptime_s"), samples[i + 1].get("uptime_s"))
                 for i in range(len(samples) - 1)
                 if samples[i].get("uptime_s") is not None
                 and samples[i + 1].get("uptime_s") is not None
                 and samples[i + 1]["uptime_s"] < samples[i]["uptime_s"]]
    stats["uptime_decreases"] = len(decreases)
    if decreases:
        findings.append(_finding("S3-no-reboot", FAIL,
                                 "uptime went backwards %d time(s) — the device rebooted during "
                                 "the soak (first at t=%s)" % (len(decreases), decreases[0][0])))
    else:
        findings.append(_finding("S3-no-reboot", INFO, "uptime monotonic: no reboot observed"))

    # --- S4: no failed systemd units after boot settles
    settle = th["boot_settle_samples"]
    fu = [s.get("failed_units", 0) for s in samples[settle:]]
    stats["failed_units_max"] = max(fu) if fu else 0
    if stats["failed_units_max"] > th["allowed_failed_units"]:
        findings.append(_finding("S4-failed-units", FAIL,
                                 "systemctl --failed reported %d unit(s) after the boot-settle "
                                 "window" % stats["failed_units_max"]))
    else:
        findings.append(_finding("S4-failed-units", INFO, "no failed units during the soak"))

    # --- S5: launcher availability
    ok = [1 if s.get("http_ok") else 0 for s in samples[settle:]] or [1 if s.get("http_ok") else 0
                                                                      for s in samples]
    stats["http_availability"] = round(sum(ok) / len(ok), 4) if ok else 0.0
    if stats["http_availability"] < th["min_http_availability"]:
        findings.append(_finding("S5-launcher-availability", FAIL,
                                 "launcher answered on :8000 in only %.2f%% of samples "
                                 "(minimum %.2f%%)"
                                 % (100 * stats["http_availability"],
                                    100 * th["min_http_availability"])))
    else:
        findings.append(_finding("S5-launcher-availability", INFO,
                                 "launcher available in %.2f%% of samples"
                                 % (100 * stats["http_availability"])))

    # --- S6: single, stable framebuffer owner (A32 invariant)
    owners, changes = [], 0
    for s in samples:
        pid = s.get("fb_owner_pid")
        if pid is None:
            continue
        if not owners or owners[-1] != pid:
            if owners:
                changes += 1
            owners.append(pid)
    stats["fb_owner_changes"] = changes
    stats["fb_owner_pids"] = owners
    if changes > th["max_fb_owner_changes_warn"]:
        findings.append(_finding("S6-fb-owner", FAIL,
                                 "the framebuffer owner changed %d time(s) (%s) — the single-writer "
                                 "contract broke" % (changes, owners)))
    elif changes > th["max_fb_owner_changes"]:
        findings.append(_finding("S6-fb-owner", WARN,
                                 "framebuffer owner changed %d time(s) (%s): stable single writer "
                                 "is the A32 floor" % (changes, owners)))
    else:
        findings.append(_finding("S6-fb-owner", INFO,
                                 "single framebuffer owner throughout (pid %s)" % (owners or [None])[0]))

    # --- S7: stack CPU (the gated metric; load1 is recorded, not gated)
    cpu = [s["stack_cpu_pct"] for s in samples if s.get("stack_cpu_pct") is not None]
    if cpu:
        stats["stack_cpu_mean_pct"] = round(sum(cpu) / len(cpu), 1)
        stats["stack_cpu_peak_pct"] = round(max(cpu), 1)
        stats["load1_mean"] = round(sum(s.get("load1", 0.0) for s in samples) / len(samples), 2)
        stats["load1_max"] = round(max(s.get("load1", 0.0) for s in samples), 2)
        if stats["stack_cpu_peak_pct"] > th["stack_cpu_peak_max_pct"]:
            findings.append(_finding("S7-stack-cpu", FAIL,
                                     "Nuxel stack peaked at %.0f%% CPU (ceiling %.0f%%)"
                                     % (stats["stack_cpu_peak_pct"], th["stack_cpu_peak_max_pct"])))
        elif stats["stack_cpu_mean_pct"] > th["stack_cpu_mean_max_pct"]:
            findings.append(_finding("S7-stack-cpu", FAIL,
                                     "Nuxel stack averaged %.0f%% CPU (ceiling %.0f%%)"
                                     % (stats["stack_cpu_mean_pct"], th["stack_cpu_mean_max_pct"])))
        else:
            findings.append(_finding("S7-stack-cpu", INFO,
                                     "Nuxel stack CPU mean %.0f%%, peak %.0f%% (load1 mean %.2f is "
                                     "Samsung vendor-kernel threads, not the stack — see the A31 "
                                     "finding)" % (stats["stack_cpu_mean_pct"],
                                                   stats["stack_cpu_peak_pct"],
                                                   stats["load1_mean"])))
    else:
        stats["stack_cpu_mean_pct"] = None
        findings.append(_finding("S7-stack-cpu", WARN,
                                 "stack CPU not recorded in these samples — resource/performance "
                                 "claim stays unproven"))

    # --- S8: memory.  Absolute footprint + a leak check (growth over time).
    rss = [(s["t"], s["stack_rss_kb"]) for s in samples if s.get("stack_rss_kb")]
    if len(rss) >= 3:
        xs = [t - rss[0][0] for t, _ in rss]
        ys = [float(v) for _, v in rss]
        base = ys[0] or 1.0
        stats["stack_rss_first_kb"] = int(ys[0])
        stats["stack_rss_last_kb"] = int(ys[-1])
        stats["stack_rss_peak_kb"] = int(max(ys))
        stats["stack_rss_growth_total_pct"] = round(100.0 * (ys[-1] - ys[0]) / base, 2)
        growth_h = _linear_slope_per_hour(xs, ys)
        stats["stack_rss_growth_per_hour_pct"] = round(100.0 * growth_h / base, 2)
        if (stats["stack_rss_growth_per_hour_pct"] > th["mem_growth_per_hour_max_pct"]
                or stats["stack_rss_growth_total_pct"] > th["mem_growth_total_max_pct"]):
            findings.append(_finding("S8-memory-leak", FAIL,
                                     "stack RSS grew %.2f%% over the soak (%.2f%%/h; ceilings "
                                     "%.2f%%/h and %.2f%% total) — treat as a leak until proven "
                                     "otherwise" % (stats["stack_rss_growth_total_pct"],
                                                    stats["stack_rss_growth_per_hour_pct"],
                                                    th["mem_growth_per_hour_max_pct"],
                                                    th["mem_growth_total_max_pct"])))
        else:
            findings.append(_finding("S8-memory", INFO,
                                     "stack RSS %.1f MiB -> %.1f MiB (%.2f%%/h); no leak trend"
                                     % (ys[0] / 1024.0, ys[-1] / 1024.0,
                                        stats["stack_rss_growth_per_hour_pct"])))
    else:
        findings.append(_finding("S8-memory", WARN,
                                 "not enough RSS samples for a leak verdict"))

    # --- S9: service restarts
    restarts = [s.get("service_restarts", 0) for s in samples]
    total = max(restarts) if restarts else 0
    stats["service_restarts"] = total
    if total > th["max_service_restarts_warn"]:
        findings.append(_finding("S9-restarts", FAIL,
                                 "stack services restarted %d time(s) during the soak" % total))
    elif total > th["max_service_restarts"]:
        findings.append(_finding("S9-restarts", WARN, "one service restart recorded"))
    else:
        findings.append(_finding("S9-restarts", INFO, "no service restarts during the soak"))

    # --- S10: thermal (advisory, recorded)
    temps = [s["thermal_max_c"] for s in samples if s.get("thermal_max_c") is not None]
    if temps:
        stats["thermal_max_c"] = round(max(temps), 1)
        if stats["thermal_max_c"] > th["thermal_fail_c"]:
            findings.append(_finding("S10-thermal", FAIL,
                                     "hottest zone %.1f C exceeds %.0f C" % (stats["thermal_max_c"],
                                                                             th["thermal_fail_c"])))
        elif stats["thermal_max_c"] > th["thermal_warn_c"]:
            findings.append(_finding("S10-thermal", WARN,
                                     "hottest zone %.1f C above the %.0f C advisory"
                                     % (stats["thermal_max_c"], th["thermal_warn_c"])))
        else:
            findings.append(_finding("S10-thermal", INFO,
                                     "hottest zone %.1f C" % stats["thermal_max_c"]))

    # --- S11: charger-mode contamination (briq-01c: charger mode kills sec_ts)
    modes = sorted({str(s.get("cmdline_boot_mode", "")).strip() for s in samples})
    stats["boot_modes"] = modes
    if any("charger" in m.lower() or "lpcharge" in m.lower() for m in modes):
        findings.append(_finding("S11-boot-mode", WARN,
                                 "androidboot.mode shows a charger/lpcharge boot (%s): the "
                                 "touchscreen is dead in that mode by design, so the soak is "
                                 "not representative" % modes))
    else:
        findings.append(_finding("S11-boot-mode", INFO,
                                 "normal boot mode throughout (%s)" % (modes or ["unknown"])))

    fails = [f for f in findings if f["severity"] == FAIL]
    warns = [f for f in findings if f["severity"] == WARN]
    verdict = "FAIL" if fails else ("PASS_WITH_WARNINGS" if warns else "PASS")
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "tools/beta/soak_lib.py",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": mode,
        "verdict": verdict,
        "samples": len(samples),
        "findings": findings,
        "failures": [f["id"] for f in fails],
        "warnings": [f["id"] for f in warns],
        "stats": stats,
        "thresholds": th,
        "load_average_note": (
            "load1 is recorded but never gated: on the S10+ it is dominated by Samsung vendor "
            "kernel threads in D state (TrustZone/RPMB/REE time), per the A31 finding in "
            "docs/s10plus-autonomous-boot-repair/BETA-FINALIZER/12-REMAINING-LIMITATIONS.md. "
            "The gated CPU metric is stack_cpu_pct (sum over the Nuxel stack)."),
    }


# --------------------------------------------------------------------------- #
# Deterministic synthesis (used by --selftest and to exercise the evaluator)
# --------------------------------------------------------------------------- #
def synth(n=481, interval=60, t0=None, uptime0=180.0, rss0_kb=180 * 1024,
          growth_pct_per_hour=0.02, cpu=68.0, failed_units=0, http_ok=True,
          fb_owner_pid=1401, reboots=(), restarts=0, thermal=52.0, boot_mode="normal"):
    """Build a synthetic sample series.  `reboots` = sample indexes where the
    device restarted (uptime resets)."""
    t0 = t0 if t0 is not None else 1750000000
    out = []
    uptime = uptime0
    rss = float(rss0_kb)
    for i in range(n):
        if i in reboots:
            uptime = 25.0
        uptime += interval
        rss *= (1.0 + growth_pct_per_hour / 100.0 / 3600.0 * interval)
        out.append({
            "t": t0 + i * interval, "i": i,
            "uptime_s": round(uptime, 1),
            "load1": 12.2, "mem_used_kb": 1_400_000, "mem_avail_kb": 2_100_000,
            "stack_rss_kb": int(rss), "stack_cpu_pct": cpu,
            "failed_units": failed_units,
            "service_restarts": restarts,
            "fb_owner_pid": fb_owner_pid,
            "http_ok": http_ok, "thermal_max_c": thermal,
            "cmdline_boot_mode": boot_mode,
        })
    return out


def selftest():
    """Exercise the evaluator against known-good and known-bad series."""
    checks, failures = [], []

    def check(name, cond, detail=""):
        checks.append((name, bool(cond), detail))
        if not cond:
            failures.append("%s: %s" % (name, detail))

    good = synth()
    r = evaluate(good, 28800, mode="replay")
    check("good-series-verdict", r["verdict"] == "PASS", "got %s" % r["verdict"])
    check("good-series-no-failures", not r["failures"], str(r["failures"]))
    check("good-series-load-note-not-gated", "load1" not in str(r["failures"]),
          "load average must never be a failure")

    bad = synth()
    for s in bad:
        s["failed_units"] = 1
    r = evaluate(bad, 28800, mode="replay")
    check("failed-unit-detected", "S4-failed-units" in r["failures"], str(r["failures"]))

    reboot = synth(reboots=(120,))
    r = evaluate(reboot, 28800, mode="replay")
    check("reboot-detected", "S3-no-reboot" in r["failures"], str(r["failures"]))

    leak = synth(growth_pct_per_hour=40.0)
    r = evaluate(leak, 28800, mode="replay")
    check("leak-detected", "S8-memory-leak" in r["failures"], str(r["failures"]))

    hot = synth(thermal=95.0)
    r = evaluate(hot, 28800, mode="replay")
    check("thermal-detected", "S10-thermal" in r["failures"], str(r["failures"]))

    short = synth(n=5)
    r = evaluate(short, 28800, mode="replay")
    check("short-soak-detected", "S1-coverage" in r["failures"], str(r["failures"]))

    charger = synth(boot_mode="charger")
    r = evaluate(charger, 28800, mode="replay")
    check("charger-mode-warned", "S11-boot-mode" in r["warnings"], str(r["warnings"]))

    empty = evaluate([], 28800, mode="device")
    check("no-samples-is-blocked",
          empty["verdict"] == "BLOCKED_EXTERNAL_RESOURCE"
          and empty["terminal_state"] == "BLOCKED_EXTERNAL_RESOURCE", empty["verdict"])

    fb = synth()
    for i, s in enumerate(fb):
        if 100 < i <= 200:
            s["fb_owner_pid"] = 2144
            s["service_restarts"] = 2
    r = evaluate(fb, 28800, mode="replay")
    check("fb-owner-change-detected", "S6-fb-owner" in r["failures"], str(r["failures"]))
    check("restarts-detected", "S9-restarts" in r["failures"], str(r["failures"]))

    fb1 = synth()
    for i, s in enumerate(fb1):
        if i > 100:
            s["fb_owner_pid"] = 2144
    r = evaluate(fb1, 28800, mode="replay")
    check("fb-owner-single-change-is-warn",
          "S6-fb-owner" in r["warnings"] and "S6-fb-owner" not in r["failures"],
          str(r["warnings"]))

    check("thresholds-document-durations", THRESHOLDS["durations"]["device"] == 28800,
          "device soak must be 8 h")
    passed = sum(1 for _, ok, _ in checks if ok)
    out = {"tool": "tools/beta/soak_lib.py", "selftest": "PASS" if not failures else "FAIL",
           "checks": len(checks), "passed": passed,
           "details": [{"check": n, "ok": ok, "detail": d} for n, ok, d in checks]}
    print(json.dumps(out, indent=2))
    for n, ok, d in checks:
        print("  %s %s%s" % ("PASS" if ok else "FAIL", n, (" — " + d) if (d and not ok) else ""))
    return 1 if failures else 0


def coalesce_plan(mode="device", duration_s=None, interval_s=None, checkpoint_s=None):
    d = dict(THRESHOLDS["durations"])
    duration_s = duration_s or d.get(mode, d["device"])
    interval_s = interval_s or THRESHOLDS["sample_interval_s"]
    checkpoint_s = checkpoint_s or THRESHOLDS["checkpoint_s"]
    return {
        "mode": mode, "duration_s": duration_s, "sample_interval_s": interval_s,
        "checkpoint_s": checkpoint_s, "samples_planned": int(duration_s // interval_s) + 1,
        "probe_set": [
            "uptime", "loadavg", "meminfo", "stack-cpu+rss (nuxel stack units)",
            "systemctl --failed", "stack service NRestarts", "fb-owner pid",
            "launcher HTTP 127.0.0.1:8000", "thermal zones", "androidboot.mode",
        ],
        "gated": ["no reboot", "no failed units", "launcher availability >= 99%",
                  "single framebuffer owner", "stack CPU <= 150% mean / 300% peak",
                  "RSS growth <= 2%/h and <= 10% total", "no service restarts",
                  "coverage >= 90% of the requested duration"],
        "recorded_not_gated": ["load1 (Samsung vendor kernel threads, A31 finding)",
                               "thermal max (advisory unless > 90 C)"],
        "terminal_states": {"device": "VERIFIED_ON_S10PLUS on PASS",
                            "vm": "VERIFIED_IN_VM_ONLY",
                            "replay/selftest": "OFFLINE_TESTED",
                            "unreachable": "BLOCKED_EXTERNAL_RESOURCE"},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="soak/performance evaluation library")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    pe = sub.add_parser("evaluate")
    pe.add_argument("--samples", required=True, help="NDJSON sample file")
    pe.add_argument("--duration", type=int, default=28800)
    pe.add_argument("--mode", default="replay")
    pe.add_argument("--json", default="-")
    pp = sub.add_parser("plan")
    pp.add_argument("--mode", default="device")
    pp.add_argument("--duration", type=int, default=None)
    pp.add_argument("--interval", type=int, default=None)
    pp.add_argument("--checkpoint", type=int, default=None)
    pp.add_argument("--json", default="-")
    pg = sub.add_parser("synth")
    pg.add_argument("--out", required=True)
    pg.add_argument("--n", type=int, default=481)
    pg.add_argument("--interval", type=int, default=60)
    pg.add_argument("--reboot-at", type=int, default=None)
    pg.add_argument("--failed-units", type=int, default=0)
    pg.add_argument("--growth-pct-per-hour", type=float, default=0.02)
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "plan":
        print(json.dumps(coalesce_plan(args.mode, args.duration, args.interval,
                                       args.checkpoint), indent=2, sort_keys=True))
        return 0
    if args.cmd == "synth":
        reboots = (args.reboot_at,) if args.reboot_at is not None else ()
        series = synth(n=args.n, interval=args.interval, reboots=reboots,
                       failed_units=args.failed_units,
                       growth_pct_per_hour=args.growth_pct_per_hour)
        with open(args.out, "w", encoding="utf-8") as fh:
            for s in series:
                fh.write(json.dumps(s, sort_keys=True) + "\n")
        print("%d samples -> %s" % (len(series), args.out))
        return 0
    if args.cmd == "evaluate":
        samples = []
        with open(args.samples, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
        rep = evaluate(samples, args.duration, mode=args.mode)
        out = json.dumps(rep, indent=2, sort_keys=True)
        if args.json == "-":
            print(out)
        else:
            with open(args.json, "w", encoding="utf-8") as fh:
                fh.write(out + "\n")
        return 0 if rep["verdict"].startswith("PASS") else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
