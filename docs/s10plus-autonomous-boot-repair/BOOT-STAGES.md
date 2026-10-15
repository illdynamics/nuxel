# BOOT-STAGES (cycle 3)

| Stage | State | Evidence |
|---|---|---|
| A — Samsung S-Boot | **WORKS for BOOT-partition loads** | `load_kernel: loading boot image from 218112..` -> `kernel size = 0x2ae6000, ramdisk size = 0x7f0000` -> `[UFDT] BOOT IMG HDR V1.. FINDING DTB ENTRY` -> `Little Find DTB Entry[0]: Rev:(S:0, E:255, X:0, D:26)` -> `DT Overlay Complete!` (DTBO entry[9]) -> `dtb_update: packing` -> `Updating device tree @0x8a000000: done` -> `Starting kernel...` |
| A2 — image format handoff | **WORKING (recovery reference)** | TWRP record from 330752: `kernel size = 0x2ac3800, ramdisk size = 0xa66800`, full kernel log |
| B — ARM64 kernel entry | **PROVEN ON HARDWARE** | pstore `dmesg-ramoops-0`: `linux_banner: Linux version 4.14.253 (nuxel@nuxel-phosh)`; kernel log to t=1.96 s with full driver probe |
| B2 — initrd handed over | **LENGTH correct, CONTENT wrong** | `Freeing initrd memory: 8128K` = exactly our payload, yet `rootfs image is not initramfs (junk in compressed archive)` |
| C — initramfs `/init` | **NOT OBSERVED** | no `nuxel-init:` / `NUXEL_MARKER` line in any capture (and, until A6, no `/dev/console` existed so this could not have been observed either way) |
| C2 — initramfs output channel | **REPAIRED IN A6** | `/dev/console` (c 5:1) + `/dev/null` (c 1:3) now in the archive |
| D — USERDATA discovered / Fedora rootfs mounted | not reached | — |
| E — Fedora userspace / init system | not reached | systemd 258.11 vs Linux 4.14.253 is a known open risk |
| F — display / Phoc / Phosh | not reached | A2 kernel dump shows `decon0/2`, `dsim0-wq`, `130b0000.displa`, `panel-bl-thread` (drivers only) |

## Ram-console semantics (unchanged, still the basis for negative results)
* S-Boot replaces `/chosen/bootargs` with its own cmdline: `console=ram`,
  `loglevel=4`, `sec_debug.level=0`, `androidboot.debug_level=0x4f4c`. The
  boot-image header `cmdline` never reaches `/proc/cmdline`.
* `loglevel=4` filters ordinary chatter, but panic/oops text is level 0-3 and
  passes, and writes to `/dev/console` bypass the printk filter entirely.
* A normal BOOT-partition boot has **no `bootmode=` token**; the recovery boot has
  `bootmode=2`. `init/do_mounts.c` gates Samsung's `mount_sar_ramdisk()` fallback
  on `androidboot_bootmode != 2`, which is why `SAR_RD` runs only on our boots.

## What this means for reading a negative result
"No output" is now a meaningful negative result again, because A6 supplies
`/dev/console`. Before A6 it was not: `kernel_init_freeable()` opens
`/dev/console` from the initramfs, and every Nuxel boot logged
`Warning: unable to open an initial console.`


---

# BOOT-STAGES (cycle 3, after A7 — hardware-measured)

| Stage | State | Evidence |
|---|---|---|
| A — S-Boot accepts and jumps to the image | **PROVEN** | `load_kernel: loading boot image from 218112.. kernel size = 0x2b66000, ramdisk size = 0x80000` -> `[UFDT] BOOT IMG HDR V1` -> `Starting kernel...` |
| B — ARM64 kernel entry | **PROVEN** | kernel logs to t=242 s (A7), pstore dumps |
| C — **initramfs unpacks** | **PROVEN (A7)** | `NUXEL-KDIAG unpack verdict: message=(none) state=7` for the built-in archive — twice per boot |
| D — **`/init` executes** | **PROVEN (A7)** | `RAMDISK:` = 0, `SAR_RD` = 0, `init group exit` = 0, `Failed to execute /init` = 0 ⇒ `/init` present, `prepare_namespace()` skipped, exec succeeded |
| D2 — initramfs *output* observable | **FIXED IN A8** | `/dev/console` is ENODEV on this device; A8 writes evidence to `/dev/kmsg` and ships `dev/kmsg` in the archive |
| E — initramfs proves what it did | **A8 UNDER TEST** | `NUXEL_MARKER …` lines + `early heartbeat: block devices …` + the BOOT-slack diagnostic record |
| F — USERDATA discovered / Fedora rootfs mounted | NOT YET | — |
| G — Fedora userspace / init system | NOT YET | systemd 258.11 vs Linux 4.14.253: known open risk |
| H — display / Phoc / Phosh | NOT YET | drivers only |

## The external initrd is not merely wrong, it is absent (measured)
```
NUXEL-KDIAG populate_rootfs: … external_initrd=1 start=ffffffc009000000 end=ffffffc009080000 len=524288
NUXEL-KDIAG initrd head: 5b 20 20 20 20 31 2e 30 34 35 36 36 35 5d 20 5b   ascii "[    1.0"
NUXEL-KDIAG unpack attempt: first=0x5b this_header=0 remaining=524288 method=(none)
```
`0xffffffc009000000` is the linear-map alias of S-Boot's fixed `0x89000000`, the
length is our header's ramdisk size rounded to 2048, and the bytes are the kernel's
own console text. The bootloader declares the initrd but does not load it on the
normal BOOT-partition path (the `bootmode=2` recovery path does load it — hence
TWRP boots). **A7's embedded initramfs makes the boot independent of this.**

## New: the boot is time-limited by the vendor kernel
A7's boots ended at t=37 s, t=68 s and t=242 s, never with a Nuxel-userspace
failure:
* `hard_reset_hook_callback+0x144/0x150` -> `Fatal exception in interrupt`
  (`Kernel panic - not syncing: Fatal exception in interrupt`);
* `hung_task: blocked tasks` with `tz_worker_threa` (EXYNOS thermal),
  `scsi_srpmb_work`, `ree_time` blocked for >120 s.
Neither is on our code path: they are the vendor "boot did not signal success"
mechanisms. Consequence for every future candidate: **the initramfs must reach its
evidence-writing step and hand off within ~40 s.** A8 enforces this itself with
`NUXEL_BOOT_WATCHDOG=45`.


---

# BOOT-STAGES (cycle 4, after A12 — hardware-measured, and after A13 — offline)

| Stage | State | Evidence |
|---|---|---|
| A — S-Boot accepts and jumps to the image | **PROVEN** | `[UFDT] BOOT IMG HDR V1`, `Little Find DTB Entry[0]: Rev:(S:0, E:255, X:0, D:26)`, `DT Overlay Complete!` (DTBO entry[9]), `Starting kernel...` |
| B — ARM64 kernel entry | **PROVEN** | `Booting Linux on physical CPU 0x0`, `Linux version 4.14.253 … #6`, logs to t=31.97 s |
| C — initramfs unpacks | **PROVEN (A7)** | built-in archive `state=7` |
| D — `/init` executes | **PROVEN (A8/A12)** | `NUXEL_MARKER INITRAMFS_EXECUTED` at t=1.970 s |
| E — output channel | **PROVEN (A8)** | `/dev/kmsg` works; `/dev/console` is ENODEV on this handset |
| F — USERDATA discovered | **PROVEN (A12)** | `USERDATA_FALLBACK /dev/sda31`, `Nuxel-init: root block device: /dev/sda31` |
| G — Fedora ext4 mounts | **PROVEN (A12)** | `EXT4-fs (sda31): mounted filesystem with ordered data mode`; `NUXEL_MARKER ROOTFS_MOUNTED` |
| H — rootfs identity | **BROKEN in A12** | logged `rootfs os-release: <none>` and then handed off anyway; no `ROOTFS_NOT_FEDORA` and no `[FATAL]` line, so the gate reported neither outcome. A13 replaces it with `ROOTFS_IDENTITY_RAW/OK/FAIL` |
| I — `switch_root` → Fedora PID 1 | **PROVEN (A12)** | `switching root -> /newroot` then `systemd[1]: systemd 258.11-1.fc43 running in system mode`, `Detected architecture arm64.` |
| J — systemd builds its graph | **PROVEN (A12)** | `Queued start job for default target multi-user.target`; slices, sockets, timers and mounts created |
| K — systemd reaches targets | **PROVEN (A12)** | `Reached target sysinit.target`, `Reached target basic.target`, `Reached target sockets.target`, `Reached target timers.target` |
| L — **service process creation** | **BLOCKED (A12) → A13 repair** | every spawn: `Failed to spawn executor: Function not implemented` (+ `Failed to spawn 'start' task`, `result 'resources'`). Cause identified: glibc `pidfd_spawn()` → `waitid(P_PIDFD)` = Linux 5.4 |
| L2 — evidence channel across the handoff | **BROKEN in A12, fixed in A13** | A12 `mount --move /dev /newroot/dev` detached `/dev/kmsg` by path; the watchdog's message was lost. A13 mounts fresh `/proc`, `/sys`, `/dev` inside the new root instead |
| M — Nuxel first light (framebuffer) | **A13 TARGET** | `show_boot_splash()` in A12 already proved a **char device at `/dev/fb0` or `/dev/graphics/fb0` exists** (it logged the "no splash data" branch, which is only reachable after the `[ -c ]` test passes) |
| N — DRM/KMS, Phoc, Phosh | **BLOCKED** | `# CONFIG_DRM is not set` in this kernel; the display path is fbdev (`s3cfb.bootloaderfb=0xca000000`, panel `s6e3ha9`, `init_decon: xres 1440 yres 3040`, `system rev : 26`) |

## Boot boundaries in `captures/20261015T100000Z-A12-postfail/last_kmsg.txt`

The capture contains **four kernel instances** (the ram console is not cleared
between them). Claims must be attributed per instance:

| Lines | Kernel | Notes |
|---|---|---|
| 1–2155 | `4.14.253 #5` (09:50:39) | A11: `root mount failed`, `[FATAL]` |
| 2156–10357 | `4.14.113-g55f042627` (Feb 2023) | the stock **recovery** kernel (TWRP session) |
| 10358–17630 | `4.14.253 #6` (09:56:05) | **the A12 boot**: initramfs, ext4, switch_root, systemd to `basic.target`, our watchdog reboot at t=31.971 s |
| 17631–21730 | `4.14.253 #6` (restart) | S-Boot's own retry after the reboot; only bootloader text |

`grep -c` over the whole file therefore mixes sessions. The A12 conclusions above
were taken only from lines 10358–17630.

---

# CYCLE 5 UPDATE — where A14 actually reached (hardware-measured)

| Stage | A12 | A13 | A14 | A15 target |
|---|---|---|---|---|
| S-Boot starts our kernel | yes | yes | yes | yes |
| kernel runs, ram console works | yes | yes | yes | yes |
| initramfs unpacks | yes | yes | yes | yes |
| `/init` executes | yes | yes | yes | yes |
| first-light payload runs | no | (stalled) | **yes, t=2.363 s** | yes + geometry log |
| USERDATA discovered | yes | no | yes | yes |
| Fedora ext4 mounted | yes | no | yes | yes |
| syscall/spawn probes | no | no | **yes** | yes |
| Fedora binary executes | no | no | **yes** | yes |
| `switch_root` → systemd PID 1 | yes | no | yes | yes |
| systemd unit graph | to `basic.target` | no | yes | yes |
| a real child service runs | **no** (ENOSYS) | no | **yes** (`systemd-udevd`) | yes |
| units attach to cgroups | n/a | n/a | **no** (`Failed at step CGROUP`) | yes |
| boot survives past 30–47 s | no (our watchdog, 31.97 s) | no (operator reset) | **no (our watchdog, 47.17 s)** | yes |
| frame visible on the panel | no | no | **unverified (operator: black)** | operator confirms |
| penguin animation | no | no | no | yes |

---

# CYCLE 6 UPDATE — where A15 actually reached (hardware-measured, 1892 s)

| Stage | A12 | A13 | A14 | **A15** | A16 (on device) |
|---|---|---|---|---|---|
| S-Boot starts our kernel | yes | yes | yes | yes | yes |
| kernel runs, ram console works | yes | yes | yes | yes | yes |
| initramfs unpacks | yes | yes | yes | yes | yes |
| `/init` executes | yes | yes | yes | yes | yes |
| first-light payload runs | no | (stalled) | yes, t=2.363 s | exit 0 at t=2.147 s but **verdict log swallowed** | verdict written straight to `/dev/kmsg` |
| USERDATA discovered | yes | no | yes | yes | yes |
| Fedora ext4 mounted | yes | no | yes | yes | yes |
| syscall/spawn probes | no | no | yes | yes | yes |
| Fedora binary executes | no | no | yes | yes | yes |
| `switch_root` → systemd PID 1 | yes | no | yes | yes | yes |
| systemd unit graph | to `basic.target` | no | yes | **yes, basic.target t=3.579 s** | yes |
| a real child service runs | no (ENOSYS) | no | yes (`systemd-udevd`) | **no — 28/28 units ENOSYS** | no |
| units attach to cgroups | n/a | n/a | no | **no** (`cgroup2` mounted, dirs never created) | no |
| boot survives past 30–47 s | no (our watchdog, 31.97 s) | no (operator reset) | no (our watchdog, 47.17 s) | **YES — 1892 s, zero software resets** | pending |
| frame visible on the panel | no | no | unverified | **no (operator: black)** | pending |
| penguin animation | no | no | no | no | implemented, resident |

### The reset question is answered

A15 was never reset by software. The single `BUG` in the log is
`drivers/samsung/sec_hard_reset_hook.c:157` from `hard_reset_hook_callback`, the
AP's operator-forced-reset path. `debug-snapshot: normal reboot starting` and
`Restarting system` do not appear anywhere in the A15 boot. So "stage: survives
past 30–47 s" moves from *no* to *yes*, and the mission's Priority-1 question
("identify whether the restart is explicitly requested by software, caused by a
kernel panic, initiated by a watchdog, or still undetermined") is answered:
**none of those — it was the operator's hard-reset hook, i.e. the human recovery
action under the standing agreement.**

---

# CYCLE 7 — A17 boot stages and the state machine (2026-10-15)

## Measured stages

| Stage | A16 (measured) | A17 (expected / to confirm) |
|---|---|---|
| S-Boot executes kernel | t≈0 (S-Boot @5785, `Starting kernel...` @6492) | same |
| initramfs `/init` runs | t=2.109557 `INITRAMFS_EXECUTED` | same |
| framebuffer present | t=2.122789 `FB_SYSFS bits_per_pixel=32 stride=5760 virtual_size=1440,6080 modes=U:1440x3040p-0` | same |
| first light painted | t=7.603860 `FIRSTLIGHT_ANIMATION_DONE` (pid 3316) | same |
| animation hold resident | t=7.769 (pid published as *empty* — defect) | `ANIMATION_HOLD_PID=<pid>` |
| rootfs mounted | t=8.794495 `ROOTFS_MOUNTED /dev/sda31 ext4 rw` | same |
| Fedora userspace executes | t=8.844367 `FEDORA_BINARY_EXECUTED` | same |
| systemd library verified | t=8.851880 `SYSTEMD_PATCH already present` (marker only) | `SYSTEMD_LIB_VERIFIED_PRESENT` or `SYSTEMD_LIB_INSTALLED_VERIFIED` (SHA-256+ELF) |
| cgroup2 usable | t=8.852955 `CGROUP2_MOUNTED` — **a lie in the final namespace** | `CGROUP2_MOUNTED` **after** `CGROUP2_VERIFIED controllers=…` post-sysfs-mount |
| live diagnostics up | not implemented | `LIVE_CONSOLE_STARTED` |
| handoff | t=8.855582 `ROOTFS_HANDOFF_STARTED` → `switch_root` | same + `BOOT_STAGE_SYSTEM_STARTING` |
| systemd PID 1 | t=8.915575 `systemd 258.11-1.fc43 running in system mode` | same |
| unit graph | t=9.195179 `Reached target basic.target` | same, **plus real services active** |
| service execution | **never**: 29× `Failed to spawn executor: Function not implemented` while the executors ran anyway | **zero** of those; `systemd-udevd`/`systemd-journald`/`dbus-broker` `active` |
| phone UI | not attempted | not attempted (no DRM/KMS) |

## The A17 state machine

Stage names are written to `<rootfs>/var/lib/nuxel/boot-stage` and mirrored on the
boot channel:

```
FIRST_LIGHT ─► SYSTEM_STARTING ─► PHONE_UI_STARTING ─► PHONE_UI_READY ─► ANIMATION_STOPPED
```

A17 implements `FIRST_LIGHT` and `SYSTEM_STARTING` plus the supervision primitive
(hold PID published). Transitions past `SYSTEM_STARTING` require evidence
(§PHONE-UI-HANDOFF.md) and must not be declared from file presence. If a
graphical session fails, the machine returns to `FIRST_LIGHT` rather than showing
an unexplained black screen.
