# ANALYSIS — A15 post-failure capture (2026-10-15T13:57Z)

**Capture:** `scripts/s10plus-debug-pack/captures/20261015T135737Z-A15-postfail/`
**Source of truth:** `/proc/last_kmsg` (TWRP) = the A15 ram console, 18,303 lines,
3 boots concatenated in the ramoops buffer.

## Device / request state (verified live)

| Check | Value |
|---|---|
| adb | `R58M75KDB2X  recovery  product:omni_beyond2lte  model:Galaxy_S10_` |
| `adb shell id` | `uid=0(root)` `context=u:r:su:s0` |
| `ro.product.device` | `beyond2lte` |
| `ro.twrp.version` | `3.7.0_9-2` |
| `ro.boot.bootloader` | `G975FXXSEFUL1` |
| `ro.boot.hardware` | `exynos9820` |
| `ro.boot.revision` | `26` |
| `ro.boot.dtbo_idx` | `9` |

**Flashed-image identity (read-only readback, full-length hash):**

```
dd if=/dev/block/by-name/boot bs=512 count=98836 | sha256sum
= e23d004d083b3137bc8ff1819b7b954c50700abe9ae8fd971e4cc8bf854fc966
```
That is byte-identical to `A15/boot.img` (50,604,032 B). **The device is running
A15 and the capture below belongs to A15.** (The full 57,671,680 B partition
hash differs only because the image is shorter than the partition.)

## Ram-console map

| Lines | Boot | Evidence |
|---|---|---|
| 1–4548 | previous TWRP session | `init: Reboot start, reason: reboot,adb` |
| 4549–17571 | **NUXEL A15** | S-Boot @4550, `Starting kernel...` @5280, `Linux version 4.14.253 #1 SMP PREEMPT Thu Oct 15 13:23:12 UTC 2026` @5286 |
| 17572–18303 | current TWRP | S-Boot @17572, `recovery: Loading entire partition` |

The A15 boot ran **t = 3.2 s → 1892.1 s (~31.5 min)**.

## A15 boot milestones (measured)

```
t=2.134171  nuxel-init: NUXEL_MARKER INITRAMFS_EXECUTED
t=2.145571  no splash data — showing navy boot screen          (show_boot_splash)
t=2.147147  nuxel-init: FIRSTLIGHT exit=0
t=2.147228  nuxel-init: NUXEL_MARKER FIRSTLIGHT_FRAME_WRITTEN
t=3.171692  NUXEL_MARKER ROOTFS_MOUNTED
t=3.187644  NUXEL-SYSCALL-PROBE begin
t=3.190233  NUXEL-SPAWN-PROBE posix_spawn(/bin/sh,"exit 7") rc=0 child_status=7 [ok]
t=3.190243  NUXEL-SPAWN-PROBE pidfd_spawn(...) rc=38 ENOSYS  <-- the systemd failure
t=3.190822  NUXEL-SPAWN-PROBE fork+execve(/bin/sh,"exit 5") child_status=5 [ok]
t=3.190845  NUXEL-SPAWN-PROBE cgroup2_unified=absent   (probe ran before the mount)
t=3.220608  NUXEL_MARKER FEDORA_BINARY_EXECUTED
t=3.229491  NUXEL_MARKER SYSTEMD_PATCH_PRESENT
t=3.231460  NUXEL_MARKER CGROUP2_MOUNTED
t=3.234130  NUXEL_MARKER ROOTFS_HANDOFF_STARTED  -> switch_root
t=3.290166  systemd[1]: systemd 258.11-1.fc43 running in system mode
t=3.290488  Warning! kernel version 4.14.253 is older than systemd's required baseline 5.7
t=3.500005  Queued start job for default target multi-user.target
t=3.578945  Reached target basic.target
t=3.579269  System is tainted: old-kernel
t=905.166   systemd-tmpfiles-clean.service: Failed to spawn executor: Function not implemented
t=1217.50   INFO: task tz_worker_threa blocked for more than 600 s   (trustzone worker, benign)
```

## ROOT CAUSE 1 — the "spontaneous reboot" is NOT spontaneous; it is the operator's
## Samsung hard-reset hook

```
[1891.962448] kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!
[1891.962482] sec_debug_set_extra_info_fault = BUG / 0xffffff8008f2cdb4
[1891.962635] Internal error: Oops - BUG: 0 [#1] PREEMPT SMP
[1891.971066] CPU: 0 PID: 0 Comm: swapper/0 Tainted: G S  4.14.253 #1
[1891.971169] pc : hard_reset_hook_callback+0x144/0x150
stack: hard_reset_hook_callback+0x144
       el1_dbg -> do_debug_exception -> brk_handler -> call_break_hook -> bug_handler
       bug_handler -> die -> panic
       __hrtimer_run_queues -> hrtimer_interrupt -> exynos4_mct_tick_isr
       cpuidle_enter_state -> do_idle -> rest_init
```

`sec_hard_reset_hook` deliberately executes a BRK (→ BUG → panic → reset) when the
PMIC power key is held ~7 s with the volume key — Samsung's user-forced-reset path.
It is the only `BUG`/panic in the whole 31.5-minute log, it happens at the *end*
of the boot, and there is **no `Kernel panic - not syncing`, no watchdog bite, no
`Restarting system`** anywhere in the A15 boot. The HW watchdog
(`s3c2410-wdt ... keepalive`) is petted every 10 s right up to the end.

**Conclusion (matches the mission's warning):** the reset at t=1892 is the
operator's physical recovery action, not a boot failure of its own.
`RECOVERY_ACCESS=RESTORED` by hard reset.

### Consequence: the A15 watchdog removal worked

A14 rebooted itself at t=47.171 s (`debug-snapshot: normal reboot starting`, the
initramfs dead-man watchdog). A15 shows **no software reboot in 1892 s**. The
mission's "prolonged black screen then spontaneous reboot after 1–2 min or
longer" is explained: the screen is black from t≈2.1 s onward, the phone is
alive and healthy (systemd running, watchdog petted), and the reset observed was
the operator forcing recovery. Milestone "stable boot without spontaneous reset"
is therefore **externally proven for the A15 window**.

**The real remaining blocker is that the panel is black — not that the device
reboots.**

## ROOT CAUSE 2 — every systemd service still dies ENOSYS

All 28 distinct units fail identically, e.g.:

```
systemd[1]: dbus-broker.service: Failed to spawn executor: Function not implemented
systemd[1]: nuxel-firstlight.service: Failed to spawn executor: Function not implemented
systemd[1]: systemd-udevd.service:  Failed to spawn executor: Function not implemented
```

Distinct failing units (28): authselect-apply-changes, dbus-broker, dev-mqueue.mount,
ldconfig, modprobe@drm, nuxel-firstlight, sys-fs-fuse-connections.mount,
sys-kernel-config.mount, sys-kernel-debug.mount, sys-kernel-tracing.mount,
systemd-hwdb-update, systemd-journal-catalog-update, systemd-journal-flush,
systemd-journald, systemd-network-generator, systemd-random-seed,
systemd-remount-fs, systemd-sysctl, systemd-sysusers, systemd-tmpfiles-clean,
systemd-tmpfiles-setup-dev-early, systemd-tmpfiles-setup-dev,
systemd-tmpfiles-setup, systemd-udev-load-credentials, systemd-udev-trigger,
systemd-udevd, systemd-update-done, systemd-update-utmp, tmp.mount.

Secondary, downstream of the same root cause:

```
systemd[1]: Attaching device control BPF program to cgroup ... failed: Argument list too long
(udevadm)[3474]: Failed at step CGROUP spawning udevadm: No such file or directory
```

so `cgroup2` *is* mounted (A15 marker `CGROUP2_MOUNTED`) but the per-unit cgroup
directories are never created because the executor never runs.

The `A13 pidfd_spawn→posix_spawn` backport
(`.scratch/s10plus-cycle4/nuxel-0001-pidfd-spawn-fallback.patch`) is present as a
marker (`SYSTEMD_PATCH_PRESENT`) and the patched `libsystemd-shared` is in the
initramfs, but the **rootfs's own** `/usr/lib64/systemd/libsystemd-shared-*.so`
is what systemd 258 uses, and it still returns ENOSYS. On this kernel
`pidfd_spawn()` ENOSYS is unconditional (`waitid(P_PIDFD)` needs Linux ≥ 5.4),
so the fallback must actually be present in the library the *rootfs* loads.

## ROOT CAUSE 3 — the panel never lights during Nuxel boot (display)

Panel + DECON + DSIM **probe fine** during the Nuxel boot:

```
t=1.212  PANEL:INFO:panel_parse_dt:panel-0        (s6e3ha9_beyond2_a3_s0_*)
t=2.019  dsim-0 dsim_enable - (state:INIT -> ON)
t=2.023  PANEL:INFO:panel_core_ioctl:PANEL_IOC_SLEEP_OUT
t=2.023  PANEL:WARN:panel_sleep_out:panel already NORMAL state   (S-Boot left it on)
t=2.034  decon_initial_display was called
t=2.034  decon0 registered successfully
t=2.034  PANEL:INFO:panel_fb_notifier:FB Registeted
```

…but there is **no `decon_enable` / `decon UNBLANK` / `FRAME_DONE` for the Nuxel
boot** anywhere in 1892 s. (Compare the *TWRP* session, which shows a normal
`decon-0 UNBLANK` → `dsim_enable` → `panel_core_ioctl:FRAME_DONE` sequence.)

The first-light verdict lines were never captured, because `init.sh` reads the
program's output through a subshell pipeline:

```sh
_fbout="$(/opt/nuxel/nuxel-fb-phone 2>&1)"          # capture is fine
printf '%s\n' "${_fbout}" | while IFS= read -r _l; do diag "FIRSTLIGHT ${_l}"; done
#                        ^^^ runs in a subshell; the log shows
# "sh: <...>read: No such file or directory" here, so every one of the
# NUXEL_FB_INFO / NUXEL_FB_ANIM lines was swallowed
```

So `FIRSTLIGHT exit=0` is recorded but **no `NUXEL_FB_INFO` geometry, no
`NUXEL_FB_BUFFERS_PAINTED`, no `NUXEL_FB_ANIM`** — we cannot tell from the
capture whether the paint reached the DECON. `FIRSTLIGHT_FRAME_WRITTEN` must
therefore **not** be counted as display progress (the mission forbids equating a
userspace buffer write with visible output).

## Failure classification

* Boot chain (S-Boot → kernel → initramfs → rootfs → switch_root → systemd PID 1):
  **no regression**. Progressed further than A14 (1892 s vs 47 s).
* `BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`
* `RECOVERY_ACCESS=RESTORED`
* `RESET_CAUSE=SEC_HARD_RESET_HOOK(operator)` — not software, not watchdog, not panic.
* `DISPLAY=Verdict unknown (log swallowed)` — must be re-measured.
* `SYSTEMD_SERVICES=ENOSYS pidfd_spawn` — unchanged from A12.

## Next actions (A16)

1. Make the first-light verdict **unswallowable** (write straight to `/dev/kmsg`)
   and log the fbdev geometry + `dd`/sysfs state.
2. Force a scanout update the way the DECON expects
   (`FBIOPUT_VSCREENINFO` with `FB_ACTIVATE_NOW`, `FBIOPAN_DISPLAY`,
   `FBIOBLANK 0` unblank) and read the pixel back, logging every return code.
3. Keep the penguin **on screen** (background hold) so first light does not depend
   on systemd and cannot be missed by the operator.
