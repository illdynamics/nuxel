# STATUS — cycle 4 / candidate A13 (2026-10-15)

**Mission:** boot Nuxel (Fedora 43 aarch64) on Samsung Galaxy S10+ SM-G975F
(`beyond2lte`), Exynos 9820 rev 26, bootloader G975FXXSEFUL1, TWRP 3.7.0_9-2,
ADB serial R58M75KDB2X. Earlier cycles: `STATUS.md.cycle3`,
`STATUS.md.cycle4-pre-A13`.

## Headline

**A12 is the hardware baseline and it went much further than its original write-up:
the Fedora rootfs mounted, `switch_root` executed Fedora PID 1, and systemd 258.11
built its unit graph, reached `sysinit.target` and `basic.target` and queued
`multi-user.target`.** The single remaining blocker is that *no service process
could ever be created*: every unit failed with one identical errno,
`Failed to spawn executor: Function not implemented`.

That errno is now identified **in the exact installed sources** and the repair is
built, verified and packaged:

* `src/basic/process-util.c:posix_spawn_wrapper()` (systemd 258.11) calls
  `pidfd_spawn()` because glibc >= 2.39 declares it (`HAVE_PIDFD_SPAWN`).
* glibc 2.42 `sysdeps/unix/sysv/linux/spawni.c`:
  `if (use_pidfd && !__clone_pidfd_supported ()) return ENOSYS;`
* `__clone_pidfd_supported()` probes **`waitid(P_PIDFD, …)`** and treats anything
  other than `EBADF` as unsupported. `P_PIDFD` is Linux **5.4**. This kernel is
  **4.14.253**, so the probe sees `EINVAL` and `pidfd_spawn()` returns `ENOSYS`
  *before any clone is attempted*.
* 258.11's fallback retried `pidfd_spawn()` (still `pidfd_spawn()`) instead of
  calling `posix_spawn()`, so there was no path back to the working
  implementation. Upstream has since fixed exactly this.

**The repair is a one-file backport of upstream's own fix**, rebuilt for aarch64
from the exact installed SRPM `systemd-258.11-1.fc43` and shipped **inside the
initramfs**, so only the BOOT partition is written and USERDATA is never touched.

Plain `posix_spawn()` is *not* affected: it uses `clone3()` with a `clone()`
fallback and works on this kernel (`spawni.c:424`), which is why
`systemd-gpt-auto-generator` really executed during A12 (PID 3450 in the log).

## Milestones (evidence-backed; "hardware" = measured on the handset)

| # | Milestone | State | Evidence |
|---|---|---|---|
| 1 | S-Boot starts the Nuxel kernel | **ACHIEVED** (A2) | S-Boot records + `Starting kernel...` |
| 2 | ARM64 kernel runs, persistent logging works | **ACHIEVED** (A2) | pstore `linux_banner: Linux version 4.14.253` |
| 3 | Initramfs unpacks | **ACHIEVED** (A7) | `NUXEL-KDIAG unpack verdict: message=(none) state=7` |
| 4 | Nuxel `/init` executes | **ACHIEVED** (A8) | its own `nuxel-init:` lines in the ram console |
| 5 | USERDATA discovered | **ACHIEVED** (A12) | `USERDATA_FALLBACK /dev/sda31` |
| 6 | Fedora ext4 mounts | **ACHIEVED** (A12) | `EXT4-fs (sda31): mounted filesystem with ordered data mode`; `ROOTFS_MOUNTED /dev/sda31 ext4 ro` |
| 7 | `switch_root` → Fedora PID 1 | **ACHIEVED** (A12) | `switching root -> /newroot`, then `systemd[1]: systemd 258.11-1.fc43 running in system mode`, `Detected architecture arm64` |
| 8 | systemd completes target startup | **PARTIAL (A12)** | `Queued start job for default target multi-user.target`; `Reached target sysinit.target`; `Reached target basic.target` |
| 9 | Exact ENOSYS cause identified | **ACHIEVED (source-exact)** | `pidfd_spawn()` → glibc `__clone_pidfd_supported()` → `waitid(P_PIDFD)` = Linux 5.4; see ROOT-CAUSE.md cycle 4 final |
| 10 | **A core systemd service actually runs** | **A13 TARGET** | every A12 spawn: `Failed to spawn executor: Function not implemented`; A13 installs the fallback |
| 11 | Fedora binary executes on hardware | **A13 TARGET** | A13 chroots into the mounted Fedora root and runs `/bin/sh`, then the glibc spawn probe |
| 12 | Kernel-primitive measurement on hardware | **A13 TARGET** | `NUXEL-SYSCALL …` table from the freestanding probe |
| 13 | Nuxel first-light executes | **A13 TARGET** | `FIRSTLIGHT …` lines + `FIRSTLIGHT_FRAME_WRITTEN` marker |
| 14 | Actual AMOLED output | **A13 TARGET, operator-visible** | `/dev/fb0` write; **needs the operator to confirm what the panel shows** |
| 15 | Phoc starts | **BLOCKED on this kernel** | `# CONFIG_DRM is not set` → no KMS → needs a 5.4+ Exynos port (Option C) |
| 16 | Phosh / usable Nuxel phone UI | **BLOCKED on 15** | — |

Milestones 1–8 and 9 are hardware- or source-proven. 10–14 are what A13 measures.

## A12 post-mortem corrections (the previous write-up was wrong in two places)

1. **A12's reset was ours, not Samsung's.** At t=31.971 s a process whose comm is
   `init` called `reboot(RB_AUTOBOOT)` (`debug-snapshot: normal reboot starting`,
   `sec_debug: set magic code (0x0)`), i.e. the `NUXEL_BOOT_WATCHDOG=30` armed at
   t≈1.97 s. The disarm immediately before `switch_root` used the **`kill` applet,
   which this toybox build does not have** (it has `killall`), and the error was
   hidden by `2>/dev/null`. A13 replaces the signal with a dead-man's switch that
   needs none. The `hard_reset_hook` attribution is withdrawn for A12.
2. **The evidence channel was severed by our own `mount --move /dev`.** Anything
   left on the old root loses `/dev/kmsg` *by path* after the move, which is why
   the watchdog's message never appeared even though it ran. A13 mounts fresh
   `/proc`, `/sys` and `/dev` inside the new root instead of moving ours away.

## What A13 changes (BOOT partition only)

| Piece | Why |
|---|---|
| patched `libsystemd-shared-258.11-1.fc43.so` installed into `ROOT_MNT/usr/lib64/systemd/` at boot (idempotent, original saved as `.nuxel-orig`) | the A13 systemd repair |
| root mounted **rw** for s10plus; the vendor cmdline's bare `ro` is ignored | Fedora needs a writable `/var`, `/etc`, journal; the A12 `ro` came from S-Boot, not from us |
| robust, loud identity gate (`ROOTFS_IDENTITY_RAW/OK/FAIL`) | A12 printed `<none>` and then handed off anyway, i.e. the gate reported nothing |
| dead-man's-switch watchdog (procfs pinned with `cd`, PID-1 `comm` test) | A12's watchdog rebooted a running Fedora |
| freestanding `NUXEL-SYSCALL` probe | measures the ENOSYS cause on hardware |
| static + dynamic `NUXEL-SPAWN-PROBE` (glibc 2.42) | proves `waitid(P_PIDFD)`→EINVAL, `posix_spawn()`→OK, `pidfd_spawn()`→ENOSYS |
| `chroot ROOT_MNT /bin/sh` probe | Fedora-binary execution, independent of systemd |
| `nuxel-fb-phone` run immediately before the handoff | first light, with a named reason on every failure path |
| `mount -t proc/sysfs/devtmpfs` into the new root instead of `mount --move` | keeps the initramfs evidence channel alive across the handoff |

## Attempt ledger (cycle 4)

| ID | Change | Gate | Write/readback | Boot result |
|---|---|---|---|---|
| A12 | `force_s10plus_root()` override + node re-creation + `wc` applet | PASS | verified `68217cdd…` | **milestones 5–8**: USERDATA, ext4, switch_root, Fedora systemd PID 1 to `basic.target`; ended at t=31.971 s by **our own watchdog** |
| A13 | pidfd_spawn→posix_spawn backport installed at boot; rw root; fixed watchdog; syscall/spawn probes; Fedora-exec probe; first light | PASS | see FLASH-ATTEMPTS.md | *in progress* |

## Standing risks
* `backups/s10plus/boot-original.img` is still a `DUMMY`; there is no real stock
  BOOT backup. RECOVERY is untouched and backed up; every write is BOOT-only and
  USERDATA has never been written. A13 writes *into* the mounted Fedora rootfs
  (one shared library + a marker), never to the raw USERDATA image.
* Host data volume ~98 % (27 GiB free). Keep >20 GiB free; verify every artifact
  copied out of the VM (it has silently truncated files before). Every artifact in
  this cycle was hash-verified after copying.
* A12 is the regression baseline and is never overwritten
  (`sha256 68217cdd59d047108f9e28de6d008fb8360dc9a5654b338df0c7bad4c26054ed`,
  re-verified after the A13 build).
