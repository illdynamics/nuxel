# STATUS — cycle 6 / candidate A16 (2026-10-15)

**Mission:** boot Nuxel (Fedora 43 aarch64) on Samsung Galaxy S10+ SM-G975F
(`beyond2lte`), Exynos 9820 rev 26, bootloader G975FXXSEFUL1, TWRP 3.7.0_9-2,
ADB serial R58M75KDB2X. Earlier cycles: `STATUS.md.cycle3`, `STATUS.md.cycle4-pre-A13`,
`STATUS.md.cycle4-final`, `STATUS.md.cycle5-pre-A16`.

## Headline

**The A15 "black screen then spontaneous reboot" is solved, and the answer is not
what it looked like.**

* The reboot was **not spontaneous and not a watchdog**. The A15 ram console
  (`/proc/last_kmsg`, 18,303 lines) ends at t = 1891.96 s with
  `kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!` triggered by
  `hard_reset_hook_callback+0x144` — **Samsung's operator force-reset hook**
  (power + volume held ~7 s), i.e. the physical recovery action. It is the only
  BUG/panic in the whole boot; there is no `Restarting system`, no watchdog bite,
  and the s3c2410 watchdog is petted every 10 s right up to the end.
* **A15 did not reboot itself even once in 1892 s (~31.5 min).** The A14
  initramfs dead-man watchdog really was the A14 reboot cause, and its removal in
  A15 worked. Milestone *stable boot without spontaneous reset* is met for the
  A15 window.
* A15 progressed **further than A14**, and the remaining blockers are exactly two:
  the panel never lights, and systemd cannot spawn a single service.

## The two live blockers

1. **Display.** Panel, DSIM and DECON all probe correctly during the Nuxel boot
   (`dsim_enable` → `panel_sleep_out` "already NORMAL" → `decon_initial_display`
   → `decon0 registered` → `panel_fb_notifier: FB Registeted`), but there is **no
   `decon_enable` / UNBLANK / FRAME_DONE for the whole 1892 s** (contrast the TWRP
   session, which shows that sequence). Worse, *no* `nuxel-fb-phone` verdict line
   reached the log at all: `init.sh` read the output through
   `printf … | while IFS= read -r`, which this toybox shell cannot run
   (`sh: <...>read: No such file or directory`), so `NUXEL_FB_INFO` and every
   `NUXEL_FB_ANIM` line were dropped and only `FIRSTLIGHT exit=0` survived.
   `FIRSTLIGHT_FRAME_WRITTEN` therefore **was not display evidence** and is no
   longer counted as such.
2. **systemd service execution.** All **28** distinct units still fail with
   `Failed to spawn executor: Function not implemented` (ENOSYS). cgroup2 *is*
   mounted in A15 (`CGROUP2_MOUNTED`) but the per-unit cgroup directories are never
   created, so the secondary `Failed to attach to cgroup … No such file or
   directory` follows. The A13 `pidfd_spawn→posix_spawn` backport is marked
   `SYSTEMD_PATCH_PRESENT` (the rootfs tag `.nuxel-patches/pidfd-spawn-fallback-A13`
   is present on the device) and the local rootfs image does **not** contain that
   tag, i.e. the handset's USERDATA differs from the local image — so the patch is
   either deployed-but-ineffective or the two images have diverged. Resolving this
   needs a USERDATA readback and is the next cycle's Priority-2 task.

## Milestones (evidence-backed; "hardware" = measured on the handset)

| # | Milestone | State | Evidence |
|---|---|---|---|
| 1 | S-Boot starts the Nuxel kernel | **ACHIEVED** (A2) | S-Boot records + `Starting kernel...` |
| 2 | ARM64 kernel runs, persistent logging works | **ACHIEVED** (A2) | pstore `linux_banner: Linux version 4.14.253` |
| 3 | Initramfs unpacks | **ACHIEVED** (A7) | `NUXEL-KDIAG unpack verdict: state=7` |
| 4 | Nuxel `/init` executes | **ACHIEVED** (A8) | its own `nuxel-init:` lines in the ram console |
| 5 | USERDATA discovered | **ACHIEVED** (A12) | `USERDATA_FALLBACK /dev/sda31` |
| 6 | Fedora ext4 mounts | **ACHIEVED** (A12/A14/A15) | `ROOTFS_MOUNTED /dev/sda31 ext4` |
| 7 | `switch_root` → Fedora PID 1 | **ACHIEVED** (A12/A14/A15) | `systemd[1]: systemd 258.11-1.fc43 … arm64` |
| 8 | systemd builds its unit graph | **ACHIEVED** (A12/A15) | `Reached target basic.target` at t=3.579 s |
| 9 | Exact ENOSYS cause | **ACHIEVED** (source-exact) | `pidfd_spawn` → glibc `waitid(P_PIDFD)` needs Linux ≥ 5.4 |
| 10 | A core systemd service really runs | **REGRESSED in A15** | A15: `systemd-udevd.service: Failed to spawn executor`; only `udevadm`/`modprobe` children ever executed, and then died at step CGROUP |
| 11 | Fedora binary executes on hardware | **ACHIEVED** (A14) | `NUXEL_MARKER FEDORA_BINARY_EXECUTED` |
| 12 | Kernel-primitive measurement on hardware | **ACHIEVED** (A14/A15) | `NUXEL-SYSCALL …` + `NUXEL-SPAWN-PROBE …` |
| 13 | First-light **code** executes | **ACHIEVED but unproven** (A14/A15) | `FIRSTLIGHT exit=0`; the program's own verdict lines were swallowed in A15 |
| 14 | **Frame visible on the AMOLED** | **NOT ACHIEVED** | panel black for 1892 s |
| 15 | No spontaneous reboot past 47 s | **ACHIEVED (A15)** | 1892 s uptime; reset was the operator's hard-reset hook |
| 16 | Real systemd services start (cgroup v2) | **NOT ACHIEVED** | 28/28 units ENOSYS |
| 17 | Spinning penguin (visible) | **NOT ACHIEVED** | see 14 |
| 18 | Phoc / Phosh / touch UI | BLOCKED on 14 + 16 | — |
| 19 | NOXEL_FB/display verdict captured from hardware | **NOT ACHIEVED** | log-swallowing bug found in A15 → fixed in A16 |

## The A16 test now on the device

`A16/boot.img` sha256 `603c2e9a3fd434d451aea0b614fe5978a9ad6178ade6edc1831afc708ee36222`
is written and readback-verified on `/dev/block/sda14`; rebooted at
`2026-10-15T14:07:20Z`. It changes the initramfs only:

* first-light output goes **straight to `/dev/kmsg`** — a silent exit is impossible;
* the program logs every fb geometry field, the mmap read-back, and the return
  codes of `FBIOBLANK(UNBLANK)` / `FBIOPUT_VSCREENINFO(FB_ACTIVATE_NOW)` /
  `FBIOPAN_DISPLAY` — the three ways to make a command-mode DECON latch a frame;
* it paints **every** buffer of the virtual framebuffer and animates in all of them;
* it then re-runs itself in `hold` mode in the background so the penguin keeps
  spinning on the panel with **no dependency on systemd, Phosh or any service**.

Outcome of A16 is pending the operator's observation and, if the screen stays
black, the fresh `last_kmsg` capture — which will now contain the exact
`NUXEL_FB_*` verdict and the ioctl return codes that A15 could not give us.
