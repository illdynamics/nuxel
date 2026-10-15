# A26 — LIVE BASELINE (first contact, 2026-10-15)

Captured from the MacBook over the CDC-ACM console while Nuxel was running.
No reboot was performed to obtain this. Tool: `scripts/s10plus-debug-pack/nuxel-live.sh`.

## Endpoint

```
$ ls /dev/cu.usbmodem*
/dev/cu.usbmodem201
$ system_profiler SPUSBDataType | grep -A5 Nuxel
  Nuxel S10+ Live Console:
    Product ID: 0x4ee7   Vendor ID: 0x18d1 (Google Inc.)
    Serial Number: NUXEL-S10PLUS-0001   Speed: Up to 5 Gb/s
```

Enumeration is **not** interchangeable with a shell: the first thing asserted was
a round-trip with a real exit status (§2 of the P1 work).

## Identity

| Item | Value (measured) |
|---|---|
| Shell | interactive root, `uid=0(root) gid=0(root)` |
| Kernel | `Linux fedora 4.14.253 #13 SMP PREEMPT Thu Oct 15 18:41:11 UTC 2026 aarch64` |
| BOOT candidate | A25 (`#13`, build time matches the A25 kernel build) |
| OS | `Fedora Linux 43 (Forty Three)`, `RELEASE_TYPE=stable` |
| PID 1 | `systemd` → `/usr/lib/systemd/systemd` |
| systemd | `258.11-1.fc43` |
| Rootfs | `/dev/sda31 ext4 rw,relatime` (cmdline `root=PARTUUID=52444E41-…`, `rootwait ro init=/init root=/dev/sda25`) |
| Board | `androidboot.hardware=exynos9820`, `androidboot.revision=26`, `region1=EUR region2=OPEN`, `androidboot.serialno=R58M75KDB2X` |
| Boot mode | **normal (non-LPM)** — no `androidboot.mode=charger`, no `lpcharge=1`; only `charging_mode=0x3030` |
| Panel | `decon-0 UNBLANK mode: 0`, `PANEL:INFO:panel_fb_notifier:UNBLANK`, `decon-0 already ON state` |
| Framebuffers | `/dev/fb0`, `/dev/fb1` (`/sys/class/graphics/`) |

## State at first contact

```
systemctl is-system-running    -> initializing        <-- the stall
systemctl list-jobs            -> 46 jobs; 45 waiting, 1 running
                                  (job 43 systemd-tmpfiles-setup-dev-early)
systemctl --failed             -> 0 loaded units listed
```
Processes: `systemd`, `nuxel-anim-play` (looping, `NUXEL_ANIM_LOOP` climbing),
`nuxel-console` ×2, `systemd-journald`, `systemd-tmpfiles`.
**`nuxel-ui` was NOT running and `/run/nuxel-ui.cmd` did not exist.**

`/var/lib/nuxel/` at first contact (note the *stale* files: the UI did run in an
earlier boot, not this one):

```
animation    ANIM_STAGE=MP4_PLAYER_ACTIVE
boot-stage   STAGE=SYSTEM_STARTING
ui-stage     PHONE_UI_READY
ui-build     A23-fbdev-phone-ui-1
ui-fb-ready  PHONE_UI_FRAME_COMMITTED commit=fbio_pan_display fb=1440x3040x32 abgr8888
ui.pid       5584                (dead)
boot-context root=/dev/sda31 device=s10plus slot=a
bootreport.txt  12917 bytes
```

`ui-fb-ready` proving `abgr8888` + `fbio_pan_display` is exactly the A24
evidence, carried over on disk; it was **not** re-proven by this boot.

## Input devices (this boot is normal mode)

`/proc/bus/input/devices` — the touch controller enumerated:

```
I: Bus=0018 Vendor=0000 Product=0000 Version=0000
N: Name="sec_touchscreen"
S: Sysfs=/devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2
H: Handlers=sec_key_notifier event2
B: PROP=2          (= INPUT_PROP_DIRECT)
B: EV=2b           (= SYN | KEY | ABS)
B: KEY=4000000000000000 0 0 80 0 420 0 0 8000 0 0
B: ABS=4263800000000003        (multitouch axes present)
N: Name="sec_touchpad"     -> event3
N: Name="sec_touchproximity" -> event4
```

`/dev/input/event0 … event10` all exist. This is a **normal-mode** boot: the
charger-mode caveat recorded in `NUXEL-INTERACTIVE-UI.md` does not apply here.

## Animation vs UI

The animation player owned the panel for the whole of this baseline and looped
without end (`NUXEL_ANIM_HEARTBEAT_LOOP` 2 → 100+); the UI never started, because
the boot graph never completed. That is the causal link proved in
`A26-SYSTEMD-BOOT-GRAPH-FIX.md`.

## Console behaviour observed (feeds the P1 work)

* Kernel telemetry is a continuous byte flood (`sec_ts`, `[SSP]`, `wl_cfg80211`,
  watchdog) interleaved with shell output at arbitrary write boundaries.
* A single long-running command (`systemctl restart systemd-udevd`) wedged the
  shared shell: every later command queued behind it and the prompt disappeared
  for minutes. Ctrl-C over the wire recovered it.
* Output was silently lost during the heaviest flood — hence the framed,
  SHA-256-verified protocol written this cycle
  (`A26-LIVE-DEPLOYMENT-VALIDATION.md`).
