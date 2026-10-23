# A50 — 01: Baseline and measurement method

## Method
- **Transport**: capability-selected USB CDC-ACM live console, framed +
  SHA-256-verified commands (`tools/beta/live/nuxel_live.py` via
  `docs/performance/A50/tools/a50-run.py`). No `adb`, no network.
- **Display-on baseline**: wake through the button-manager control FIFO
  (`action screen-on`), then read the bridge's own per-second `FRAMES_OK` state
  and `/proc/<pid>/stat` deltas. Short single-shot reads were used because the
  charging cable makes `/dev/kmsg` flood the console and shred long samplers.
- **Screen-off baseline**: read `/run/nuxel-wl-fb.state`, sysfs backlight/DECON,
  `/proc/stat`, and per-process CPU with the panel off.

## Metrics and raw data
- Raw console captures: `docs/performance/A50/raw/01..20-*.txt`.
- Machine-readable: `docs/performance/A50/A50-BASELINE.json`.
- Sampler scripts: `docs/performance/A50/tools/a50-sample*.sh` (push via base64;
  long runs are unreliable while charging — prefer the quick single-shot probe
  files `probes-*.txt`).

## Confounders (recorded, not hidden)
1. Device **charging** through the console cable (battery 93 %, USB PDIC) →
   battery/charger/Wi-Fi driver kmsg flood.
2. Wi-Fi periodic scans every ~30 s.
3. Screen auto-off idle timer (60 s) cycles the panel during measurement.
4. No physical/camera access → glass-visible latency is **not** claimed; only
   the software-visible per-frame cost (74–79 ms) is measured.
5. SoC thermal zones appear clamped at a 25 °C floor; battery/ac readings are
   the trustworthy live temperatures.

## Reproducible harness
`tools/perf/a50-benchmark.sh` (bounded, read-only, `--baseline`/`--candidate`
modes, machine-readable JSON + Markdown, `UNAVAILABLE` for missing sensors,
exit codes PASS/REGRESSION/BLOCKED/INCOMPLETE). It reuses the existing
`nuxel-display-frame-trace.sh` FRAMES_OK counter rather than inventing a new
daemon.
