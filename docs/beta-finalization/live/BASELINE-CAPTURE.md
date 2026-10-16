# Nuxel S10+ Live Baseline Capture — 2026-10-17

**Host:** dextronux (Linux 6.17.1-300.fc43.x86_64, SELinux Enforcing)
**Repository:** `/x/nuxel` @ `77724291253d448a66eb53fba847b8818e6665fb`, VERSION `v0.5.0-beta-rc1`
**Console:** `/dev/ttyACM0` — 18d1:4ee7 "Nuxel S10+ Live Console" serial `NUXEL-S10PLUS-0001`

## Verdict
**REACHABLE** (verified framed channel, sha_ok=yes). Baseline read from the running device.

## Boot mode
- `androidboot.mode=` is **absent** from `/proc/cmdline` (non-charger normal boot).
- `sec_touchscreen` is registered (`/dev/input/event2`) and `sec_touchpad` (event3), `sec_touchproximity` (event4) present.
- `sec_ts` tsp status `lpm:0`, `mutual:1` — touch controller armed.
- `systemctl is-system-running` = `running`, **0 failed units**.

## Device facts
- Model: SM-G975F (`beyond2lte`), Exynos 9820, bootloader G975FXXSEFUL1, serial R58M75KDB2X (PHN/EUR/OPEN).
- Kernel: `4.14.253` (Samsung vendor); Fedora release 43; Python 3.14.7.
- Rootfs `/dev/sda25`, `~48% used` at capture time.
- Display: fb0 1440x3040, bridge out 720x1520 scale=2, XRGB8888->ABGR8888 override, `owner=nuxel-wl-fb`, `display=on`, ~24 fps, failures=0.
- Framebuffer handoff chain complete: `BOOT_WAIT_LAUNCHER -> LAUNCHER_READY -> ANIMATION_STOP_REQUESTED -> ANIMATION_STOP_CONFIRMED -> LAUNCHER_DISPLAY_OWNER`.
- Launcher: `http://127.0.0.1:8000/pwa/nuxel-home/index.html` -> HTTP 200.
- PWA files on device hash-match the repository (no drift).
- ALSA: card0 `beyond-madera`, plus `abox_vdma`/`abox_dump`.

## Evidence bundle
`docs/beta-finalization/live/evidence/baseline-20261017T002026+0200/`
(41/41 verified frames, `a32-baseline.json`, `baseline-capture.json`, raw transcript, SHA256SUMS.)

## Note on the one reported delta
The baseline tool reported `fb-owner` delta ("expected nuxel-wl-fb, observed BOOT_WAIT_LAUNCHER"). This is a **false positive**: the tool read the first line of the durable multi-line `/var/lib/nuxel/fb-owner` record instead of the last line. The last line is `LAUNCHER_DISPLAY_OWNER` and `/run/nuxel-wl-fb.state` reports `owner=nuxel-wl-fb`; the /proc fd scan confirms exactly one `/dev/fb0` holder (`nuxel-wl-fb`).
