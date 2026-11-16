# FULL-PWNAGE-105000 — Performance: make the phone smoother than it is now

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-105000.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

The phone must feel **smoother than today** while everything else stays working.
Today's measured baseline: load ≈ 11.7, `sugov` kthreads 1.5–4 % each, `tz_worker`
threads stuck in `D`, **no `/dev/dri`** (so no hardware compositing), WebKit and
`nuxel-pwa-host` among top CPU consumers at idle.

## 1. Profile first, then fix

```sh
$SSH $PHONE 'uptime; mpstat -P ALL 1 3 2>/dev/null || vmstat 1 3'
$SSH $PHONE 'ps -eo pid,stat,pcpu,pmem,comm --sort=-pcpu | head -25'
$SSH $PHONE 'cat /sys/class/devfreq/*/governor 2>/dev/null; cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor'
$SSH $PHONE 'journalctl -b -p warning --no-pager | tail -80'
```
Targets: idle load < 2 on 8 cores, no uninterruptible tasks, idle CPU < 5 %,
smooth 60 Hz scrolling/gestures, no dropped frames on unlock animation.

## 2. Fix order (highest impact first)

1. **TEE stall (104400)** — `D`-state workers inflate load for everything.
2. **GPU acceleration (104700)** — get `/dev/dri`, verify EGL/GLES renderer,
   enable Phoc GPU rendering + hardware compositing for WebKit/Flatpaks.
3. **Governors/scheduler** — appropriate cpufreq/devfreq governors, no busy-poll
   kthreads; confirm `sugov` overhead drops.
4. **Idle wakeups** — find the Python daemons/WebKit processes waking the CPU;
   reduce polling intervals, use event-driven paths.
5. **Memory/pressure** — check zram/swappiness, cgroup memory limits for
   `nuxel-wayland`, WebKit process count.
6. Re-measure with the exact same commands and store before/after in evidence.

## 3. Acceptance

- Before/after table (load, top CPU, idle %, frame timings) in the report.
- No regression in GPS, audio, remote desktop, notifications or boot.
- Smoothness verified visually from Jump Desktop/VNC with a recorded screen and
  on-device `grim` captures during animation.
