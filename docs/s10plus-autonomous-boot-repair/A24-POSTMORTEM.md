# A24 POSTMORTEM — the UI RAN on hardware, and what ended the run (2026-10-15)

```
BOOT_RESULT   = FAILED_USER_RETURNED_TO_TWRP   (operator reset; panel found dark ~t=240 s)
UI_RESULT     = PROVEN RUNNING ON HARDWARE: process + framebuffer commit + animation handoff
HANDOFF       = PROVEN: PHONE_UI_FRAME_COMMITTED -> ANIMATION_STOP_SIGNALLED -> PHONE_UI_READY
COLOUR        = A23 fix confirmed in code path; A24 binary carries the ABGR default (see below)
```

## 1. What the A24 boot proved (device's own logs, read from `/data/var/lib/nuxel`)

```
ui-build      UI_REV=A24-fbdev-phone-ui-1 / INSTALLED_AT_BOOT=1
ui-stage      PHONE_UI_READY
ui-fb-ready   PHONE_UI_FRAME_COMMITTED commit=fbio_pan_display fb=1440x3040x32 abgr8888
anim-stop     PHONE_UI_FRAME_COMMITTED
boot-stage    STAGE=SYSTEM_STARTING
animation     ANIM_STAGE=MP4_PLAYER_ACTIVE
fb-anim.pid   3525          fb-anim-ready  MP4_FIRST_FRAME_COMMITTED
ui.log:
  UI_STARTED build=A23-fbdev-phone-ui-1
  FIRST_FRAME_COMMITTED fbio_pan rc=0
  ANIMATION_STOP_SIGNALLED pid=3525 186
  PHONE_UI_READY
  INPUT_DEVICE name='' mt=0 xmax=0 ymax=0      (x8: every event node lacks MT axes)
  TOUCH_POINTING_DEVICE_NONE (console channel can still drive the UI)
dmesg: NUXEL_UI_PANEL_W=1440 H=3040 STRIDE=5760 BPP=32 BUFFERS=2 SCALE=4
       NUXEL_UI_CMD_FIFO_OK /run/nuxel-ui.cmd
```

So: a **real userspace process** opened `/dev/fb0`, measured the panel, committed a frame
with `FBIOPAN_DISPLAY` (rc=0), recorded the stage machine, stopped the boot animation
(both channels: `anim-stop` file *and* SIGTERM to the pid from `fb-anim.pid`), and stayed
alive. That is `PHONE_UI_FRAME_COMMITTED` and the handoff, demonstrated on the handset --
not claimed from a buffer write.

Also newly proven: `/init`'s install step works from a BOOT-only flash
(`UI_INSTALLED rev='A24-...' (was 'A23-...')`, previous binary kept as
`/usr/lib/nuxel/nuxel-ui.prev`), and `/usr/lib/nuxel/nuxel-postboot.sh` is installed.

## 2. Three defects found by this cycle, all measured

**(a) `SCR.hw_abgr` was never initialised in the shipped build.** The A23 UI logged
`NUXEL_UI_HW_ABGR=0`, i.e. it drew with `fb_var`'s declared order while the DECON commit
path programs `ABGR_8888` (see `NUXEL-COLOUR-ORDER.md`). The player and first-light
renderers were fine (A23 defaults them to the hardware order); only the UI carried the
uninitialised field. Fixed: `SCR.hw_abgr=1` before argument parsing, with the reason
written at the assignment.

**(b) Fedora's userspace boot never completes on this image**, so the UI unit -- enabled
into `multi-user.target.wants` -- could never start, and `systemctl start nuxel-ui`
blocked forever behind the stalled graph. Full measurement in `NUXEL-BOOT-STALL.md`.

**(c) The live console was single-use.** When the Mac closed `/dev/cu.usbmodem201`, the ACM
tty raised SIGHUP to the foreground process group and the shell died for the rest of the
boot; the only recovery was a manual power cycle. This cost this cycle a 40-minute
blackout mid-diagnosis. Fixed in `tools/s10plus/a24-nuxel-console.c`: an ignored-signal
disposition survives `execve` (a handler does not), so the shell is re-exec'd through
`trap '' HUP; exec /bin/sh -i`, and a supervisor respawns it after *any* exit.

**(d) — the one that ended the run — two renderers are still fatal.** After the UI had
taken the panel, a second, deliberate `nuxel-ui --once` (used to time a frame commit) was
run for diagnosis. On its exit the kernel logged `disable regulator(1:vdd2)` and the panel
went dark; the UI instance that was still running could not bring the regulator back. The
operator therefore saw a black screen and returned the phone to TWRP, which is the correct
call. `PHONE_UI_READY` had already been reached, so this is a **test-method** failure, not
a UI failure -- but it is exactly the failure mode the mission forbids, and the UI must
make it impossible: A25 adds a single-instance lock (`/var/lib/nuxel/ui.pid` is now
respected) and a refusal to run when another instance owns `/dev/fb0`.

## 3. Regression baselines — all intact

| Baseline | Status |
|---|---|
| A16 first light + spinning penguin | unchanged code path, still runs before the MP4 |
| A18 Fedora service execution / cgroup2 / journald | untouched |
| A21/A22 original MP4 at 24.00 fps, 0 skips | `NUXEL_ANIM_HEARTBEAT_*` clean in this boot; handoff now proven |
| A23 colour order (ABGR) | player + first-light verified; UI fixed in A25 |
| A23 live console | now survives disconnects (A24 console) |

## 4. Artifacts

| Field | Value |
|---|---|
| A24 boot.img | `build/out/s10plus/debug-candidates/A24/boot.img` 51,718,144 B sha256 `5f1c31ceaebafecb460cbbe46adf821a352760e0e28fcc298c86360839c62c47` |
| A24 kernel | `Image-A24` sha256 `1366801296a9e095940db43131a479d2edee6c164719dcd1bcb9bc1e5f5818f0` |
| A24 initramfs | sha256 `145edee96e6a8ce47c46118ef9837a0b5ebc7b66ea2199e1063f324df98f7157` |
| A24 UI binary | 66,136 B sha256 `4f908f9cb11b8a89c95357a76c0b2f920528e662934e6651a8441c850ce7ebf0` (A23 order bug) |
| A25 UI binary | 66,136 B sha256 `628a3862d3a3ce951413bae6d4b38294ca8027fd3cd9e8616576e6e19c31a6f8` (ABGR default fixed) |
| BOOT backup before write | `backups/nuxel-adb/20261015T183328Z-R58M75KDB2X` |
| BOOT write/readback | dd in place, full 51,718,144-byte SHA256 readback **PASS** (`FLASH_AND_READBACK_VERIFIED`) |
| REBOOT_AT | 2026-10-15T18:33:41Z |
| gadget up | `/dev/cu.usbmodem201` 30 s after reboot |
| mode | `androidboot.mode=charger` (USB attached at boot) — hence no touch input device |

## 5. Uncertainty

* Whether the UI's *visual output* would satisfy the operator is not yet observed by a
  human; every pixel has been checked numerically from the UI's own PPM dumps, not by eye.
* The boot stall's root dependency is still unnamed; `bootreport.txt` (A24) is the
  instrument that will name it on the next boot.
* Touch cannot be evaluated on a charger-mode boot at all; it needs a USB-detached boot.
