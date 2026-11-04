#!/usr/bin/env python3
"""Matched S10+ userspace benchmark for PWNAGE-60000 (runs on the phone).

  python3 bench-pwnage60000.py --label gpu-shm --seconds 60 --run 1 --out /root/pwnage-60000/bench

Samples /proc/<pid>/stat once per second and charges CPU ticks only to the
measured UI processes.  It does not alter the session, brightness, clocks or
thermal policy.  The device load average is reported but is NOT used as a CPU
metric: 11 Samsung TrustZone/secure-monitor kthreads sit in D state on this
kernel and inflate it.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone

CATEGORIES = {
    "phoc": ("phoc",),
    "nuxel-wl-fb": ("nuxel-wl-fb",),
    "WebKitWebProcess": ("WebKitWebProces", "WebKitWebProcess"),
    "nuxel-pwa-host": ("nuxel-pwa-host",),
    "WebKitNetworkProcess": ("WebKitNetworkPr", "WebKitNetworkProcess"),
}
HZ = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


def read(path, limit=1 << 20):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def comm(pid):
    return read("/proc/%d/comm" % pid, 64).strip()


def category(name):
    for cat, prefixes in CATEGORIES.items():
        if any(name.startswith(p) for p in prefixes):
            return cat
    return None


def proc_ticks(pid):
    try:
        fields = read("/proc/%d/stat" % pid, 4096).split()
        return int(fields[13]) + int(fields[14])
    except (OSError, IndexError, ValueError):
        return None


def proc_map_has(pid, needle):
    return needle in read("/proc/%d/maps" % pid, 8 << 20)


def proc_fds(pid):
    links = []
    try:
        for f in os.listdir("/proc/%d/fd" % pid):
            try:
                t = os.readlink("/proc/%d/fd/%s" % (pid, f))
                if t.startswith("/newroot/"):
                    t = t[len("/newroot"):]
                links.append(t)
            except OSError:
                pass
    except OSError:
        pass
    return links


def snapshot():
    now = time.time()
    procs = {}
    for e in os.listdir("/proc"):
        if not e.isdigit():
            continue
        pid = int(e)
        name = comm(pid)
        cat = category(name)
        if not cat:
            continue
        ticks = proc_ticks(pid)
        if ticks is None:
            continue
        procs[pid] = {"cat": cat, "ticks": ticks, "comm": name}
    state = {}
    text = read("/run/nuxel-wl-fb.state", 8192).strip()
    for tok in text.split():
        if "=" in tok:
            k, _, v = tok.partition("=")
            state[k] = v
    return now, procs, state, text


def thermal_max():
    vals = []
    # /sys/class/thermal/thermal_zoneN are symlinks; os.walk does not follow
    # them, so glob the canonical entries explicitly.
    for path in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        try:
            v = int(read(path, 64).strip())
            if 0 < v < 200000:
                vals.append(v / 1000.0)
        except ValueError:
            pass
    return max(vals) if vals else None


def battery():
    out = {}
    for key in ("current_now", "voltage_now", "capacity", "status"):
        out[key] = read("/sys/class/power_supply/battery/%s" % key, 128).strip()
    return out


def state_num(state, key):
    try:
        return float(state.get(key, "nan"))
    except ValueError:
        return float("nan")


def process_evidence():
    ev = {"processes": {}, "renderer": None, "transport": None}
    for e in os.listdir("/proc"):
        if not e.isdigit():
            continue
        pid = int(e)
        name = comm(pid)
        cat = category(name)
        if not cat:
            continue
        if cat in ev["processes"]:
            continue
        fds = proc_fds(pid)
        ev["processes"][cat] = {
            "pid": pid,
            "comm": name,
            "gallium_mapped": proc_map_has(pid, "libgallium"),
            "libEGL_mesa_mapped": proc_map_has(pid, "libEGL_mesa"),
            "mali_fds": sum(1 for t in fds if t == "/dev/mali0"),
            "dmabuf_fds": sum(1 for t in fds if "dmabuf" in t or "/dev/dri" in t),
            "fd_scan": "ok",
        }
        env = read("/proc/%d/environ" % pid, 131072)
        for item in env.split("\0"):
            if item.startswith("NUXEL_GRAPHICS_PROFILE_ACTIVE="):
                ev["processes"][cat]["profile_active"] = item.split("=", 1)[1]
            elif item.startswith("WEBKIT_DISABLE_COMPOSITING_MODE="):
                ev["processes"][cat]["webkit_disable_compositing"] = item.split("=", 1)[1]
            elif item.startswith("WEBKIT_FORCE_COMPOSITING_MODE="):
                ev["processes"][cat]["webkit_force_compositing"] = item.split("=", 1)[1]
    try:
        with open("/run/nuxel/graphics-gpu-probe.json", "r") as f:
            p = json.load(f)
        ev["renderer"] = p.get("renderer")
        ev["gl_version"] = p.get("gl_version")
    except Exception:
        pass
    wk = ev["processes"].get("WebKitWebProcess") or {}
    ev["transport"] = ("shm" if wk.get("dmabuf_fds", 0) == 0
                       else "dmabuf-candidate")
    return ev


def job_submit_probe(seconds=2.0):
    pid = None
    for e in os.listdir("/proc"):
        if e.isdigit() and comm(int(e)).startswith("WebKitWebProces"):
            pid = int(e)
            break
    if not pid:
        return {"available": False, "reason": "WebKitWebProcess absent"}
    try:
        p = subprocess.run(["strace", "-f", "-e", "trace=ioctl", "-p", str(pid)],
                           capture_output=True, text=True, timeout=seconds + 2,
                           start_new_session=True)
        text = (p.stdout or "") + (p.stderr or "")
        return {"available": True, "rc": p.returncode,
                "window_s": seconds,
                "kbase_job_submit_hits": text.count("0x40108002"),
                "raw_tail": text[-2000:]}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--out", default="/root/pwnage-60000/bench")
    ap.add_argument("--workload", choices=("none", "scroll"), default="none")
    ap.add_argument("--workload-binary", default=None)
    ap.add_argument("--no-keep-awake", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    ev = process_evidence()
    # The session's power policy blanks the panel after inactivity.  That stops
    # the framebuffer bridge entirely (display=off), so a 60 s sample would
    # measure a dark phone.  Send screen-on through the documented control FIFO
    # every 10 s.  This is identical for both profiles and is recorded.
    keep_awake = not args.no_keep_awake
    def wake():
        if not keep_awake:
            return
        try:
            fd = os.open("/run/nuxel-wl-fb.cmd", os.O_WRONLY | os.O_NONBLOCK)
            try:
                os.write(fd, b"screen-on\n")
            finally:
                os.close(fd)
        except OSError:
            pass
    wake()
    workload = None
    if args.workload == "scroll":
        binary = args.workload_binary or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "nuxel-scroll-workload")
        env = dict(os.environ)
        env.setdefault("XDG_RUNTIME_DIR", "/run/nuxel-wayland")
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        workload = subprocess.Popen([binary, str(max(args.seconds - 5, 1)),
                                     "360", "620"], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, env=env)
    t0, procs0, state0, text0 = snapshot()
    last = dict(procs0)
    per_cat = {k: 0.0 for k in CATEGORIES}
    thermal = []
    load = []
    start_wall = datetime.now(timezone.utc).isoformat()
    for sec in range(args.seconds):
        time.sleep(1.0)
        if keep_awake and (sec % 10) == 0:
            wake()
        _, procs, state, text = snapshot()
        for pid, info in procs.items():
            prev = last.get(pid)
            if prev and prev["cat"] == info["cat"]:
                delta = info["ticks"] - prev["ticks"]
                if delta > 0:
                    per_cat[info["cat"]] += delta
            last[pid] = info
        # Keep the last tick of a disappeared PID; no negative delta is added.
        tv = thermal_max()
        if tv is not None:
            thermal.append(tv)
        try:
            load.append(float(read("/proc/loadavg", 128).split()[0]))
        except (ValueError, IndexError):
            pass
    workload_result = None
    if workload is not None:
        try:
            wout, werr = workload.communicate(timeout=5)
            workload_result = {"rc": workload.returncode,
                               "stdout": (wout or "").strip()[-500:],
                               "stderr": (werr or "").strip()[-500:]}
        except subprocess.TimeoutExpired:
            workload.kill()
            workload_result = {"rc": 124, "stdout": "", "stderr": "workload timeout"}
    t1, procs1, state1, text1 = snapshot()
    duration = max(t1 - t0, 0.001)
    cpu = {k: round(v / (HZ * duration) * 100.0, 2) for k, v in per_cat.items()}
    total = round(sum(cpu.get(k, 0) for k in
                      ("phoc", "nuxel-wl-fb", "WebKitWebProcess", "nuxel-pwa-host")), 2)
    def delta(key):
        v = state_num(state1, key) - state_num(state0, key)
        return round(v, 3) if v == v else None
    doc = {
        "schema": "nuxel.bench/1",
        "mission": "PWNAGE-60000",
        "label": args.label,
        "run": args.run,
        "seconds": args.seconds,
        "start": start_wall,
        "end": datetime.now(timezone.utc).isoformat(),
        "cpu_pct_one_core": cpu,
        "active_ui_total_pct_one_core": total,
        "evidence": ev,
        "state_start": text0,
        "state_end": text1,
        "state_delta": {
            "frames": delta("total"),
            "blits": delta("blits"),
            "present_skipped": delta("present_skipped"),
            "damage_blits": delta("damage_blits"),
            "decon_pan_ok": delta("decon_pan_ok"),
            "decon_pan_failed": delta("decon_pan_failed"),
        },
        "timings_ms": {k: (v if v == v else None) for k, v in {
            "capture_avg": state_num(state1, "capture_avg_ms"),
            "compare_avg": state_num(state1, "compare_avg_ms"),
            "blit_avg": state_num(state1, "blit_avg_ms"),
            "damage_blit_avg": state_num(state1, "damage_avg_ms"),
            "pan_avg": state_num(state1, "pan_avg_ms"),
        }.items()},
        "thermal_c_max": max(thermal) if thermal else None,
        "loadavg_max": max(load) if load else None,
        "battery_start": battery(),
        "battery_end": battery(),
        "job_submit_probe": job_submit_probe(),
        "workload": args.workload,
        "workload_result": workload_result,
        "keep_awake": keep_awake,
    }
    path = os.path.join(args.out, "%s-run%d.json" % (args.label, args.run))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
        f.write("\n")
    print(path)
    print(json.dumps({"label": args.label, "run": args.run,
                      "cpu": cpu, "total": total,
                      "renderer": ev.get("renderer"),
                      "transport": ev.get("transport"),
                      "state_delta": doc["state_delta"]}, sort_keys=True))


if __name__ == "__main__":
    main()
