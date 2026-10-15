# A16 POSTMORTEM — what actually happened on the handset (2026-10-15)

**Candidate:** A16 (`A16/boot.img` sha256 `603c2e9a3fd434d451aea0b614fe5978a9ad6178ade6edc1831afc708ee36222`)
**Evidence:** `scripts/s10plus-debug-pack/captures/20261015T143625Z-A16-postfail/previous-boot/last_kmsg.clean.txt`
(21,854 lines, NUL-stripped copy of `/proc/last_kmsg` read from TWRP)
**Also:** `captures/20261015T143613Z-full-collection-86676/` (full read-only sweep)

## 0. Headline

A16 **did not reboot**. It booted once, rendered the first-light screen and the
animated penguin on the physical AMOLED panel, ran **systemd 258 as PID 1 for
168 s**, and was then ended by the operator's own Samsung hard-reset key combo.
The reset is the only `BUG`/panic in the entire record.

The mission's four candidate explanations (A–E in §5 of the brief) resolve to a
fifth, cleaner answer:

> **B + C.** One stable kernel boot. The animation loop is intentional and never
> stops. Behind it systemd *is* running and *is* trying to start services — and
> every single one of them is being marked failed by a library bug while the
> process it tried to start is in fact already running.

## 1. Ram-console boot map

`/proc/last_kmsg` is the Samsung ram console: a ring buffer holding several boots
concatenated. The A16 record contains four sessions, and they must not be read as
one boot.

| Lines | Session | Anchor |
|---|---|---|
| 1–4886 | earlier session (exact date unknown, kernel `14:05:01` build) | truncated head of the ring |
| 4887–5784 | S-Boot → kernel → very short session | `S-Boot 4.0 for SM-G975F` @4887, `Starting kernel...` @5601 |
| 5785–21122 | **NUXEL A16** | `S-Boot` @5785, `Starting kernel...` @6492, `Linux version 4.14.253 ... #2 SMP PREEMPT Thu Oct 15 14:05:01 UTC 2026` @6498 |
| 21123–21854 | current TWRP session | `S-Boot` @21123, `recovery: Loading entire partition.` @21679 |

The A16 kernel banner (`#2 SMP PREEMPT Thu Oct 15 14:05:01 UTC 2026`) is the
build A16 shipped (`A16/Image-A16` was built at 14:05 UTC). Boot ran
**t = 0 → 170.21 s**, i.e. 168 seconds of live Nuxel.

## 2. A16 measured boot milestones

```
t = 2.109557   nuxel-init: NUXEL_MARKER INITRAMFS_EXECUTED
t = 2.115541   nuxel-init: softdog keeper started
t = 2.122789   FB_SYSFS bits_per_pixel=32
t = 2.123439   FB_SYSFS stride=5760
t = 2.124103   FB_SYSFS virtual_size=1440,6080
t = 2.124761   FB_SYSFS modes=U:1440x3040p-0
t = 7.603860   [nuxel-fb-phone:3316] NUXEL_MARKER FIRSTLIGHT_ANIMATION_DONE
t = 7.769134   nuxel-init: FIRSTLIGHT exit=0
t = 7.769215   nuxel-init: NUXEL_MARKER FIRSTLIGHT_FRAME_WRITTEN
t = 7.769457   nuxel-init: FIRSTLIGHT hold started pid=        <-- EMPTY (see §5)
t = 8.794495   nuxel-init: ROOTFS_MOUNTED /dev/sda31 ext4 rw
t = 8.809328   NUXEL-SYSCALL-PROBE end
t = 8.811344   NUXEL-SPAWN-PROBE posix_spawn(/bin/sh,"exit 7") rc=0 child_status=7 [ok]
t = 8.811355   NUXEL-SPAWN-PROBE pidfd_spawn(...) rc=38 ENOSYS
t = 8.811930   NUXEL-SPAWN-PROBE cgroup2_unified=absent
t = 8.844367   nuxel-init: NUXEL_MARKER FEDORA_BINARY_EXECUTED
t = 8.851880   nuxel-init: SYSTEMD_PATCH already present
t = 8.852955   nuxel-init: CGROUP2_MOUNTED /newroot/sys/fs/cgroup
t = 8.855582   nuxel-init: switching root -> /newroot
t = 8.915575   systemd[1]: systemd 258.11-1.fc43 running in system mode
t = 9.131754   systemd[1]: Queued start job for default target multi-user.target.
t = 9.195179   systemd[1]: Reached target basic.target - Basic System.
t = 9.195533   systemd[1]: System is tainted: old-kernel
t = 11.080775  [nuxel-fb-phone:3342] NUXEL_MARKER FIRSTLIGHT_ANIMATION_DONE   <-- the hold process
t = 170.210293 sec_debug: sec_debug_panic_handler
t = 171.219207 sec_reboot (0, panic)
```

**Highest verified boot stage for A16:** `switch_root` completed, systemd 258.11
started as PID 1, the unit graph was built and `basic.target` was reached. No
service ever started (§4).

## 3. The reset is the operator, not a boot failure

```
t = 159.797637  hard_reset_hook : hrtimer_start
t = 164.133278  hard_reset_hook : hrtimer_start
t = 170.133418  kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!
t = 170.141163  pc : hard_reset_hook_callback+0x144/0x150
t = 171.219207  sec_reboot (0, panic)
```

`sec_hard_reset_hook` executes a `BRK` (→ BUG → panic → reset) when POWER is held
with VOLUMEDOWN — Samsung's user-forced-reset path (identical to A15). The full
sequence, in order:

```
t = 159.797637  hard_reset_hook : hrtimer_start          <- keys held
t = 164.133278  hard_reset_hook : hrtimer_start
t = 170.133418  kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!
t = 170.198902  Kernel panic - not syncing: Fatal exception in interrupt
t = 171.219207  sec_reboot (0, panic)
```

So a panic **is** in the record — but it is the *mechanism of the operator's
forced reset*, not a Nuxel failure: the BUG is raised inside the hrtimer
interrupt, which is why it is reported as a fatal exception in interrupt.
What is genuinely absent from the whole 168 s window is any **Nuxel-originated**
reset: no `debug-snapshot: normal reboot starting`, no `Restarting system`, no
watchdog bite, no hung-task panic, and the HW watchdog
(`s3c2410-wdt ... keepalive!`) was petted right up to the end.

* `BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`
* `RECOVERY_ACCESS=RESTORED`
* `RESET_CAUSE=SEC_HARD_RESET_HOOK(operator)` — the panic in the record is the hard-reset hook's own `BUG` in interrupt context, not a Nuxel-originated fault.
* `A16_RUNTIME_STABILITY=STABLE_FOR_THE_WINDOW_MEASURED` (168 s, no reset of its own).

## 4. Every service failed — while its process was already running

29 `Failed to spawn executor: Function not implemented` lines, and the same
number for `Failed to spawn '<task>' task:` / `Failed with result 'resources'`.
It is **not** spread randomly: it is exactly one per unit that has a process to
start. `A16/SHA256SUMS.txt` context: none of the 28 A15-failing units improved.

But the same window also contains the *executors themselves* running:

```
t = 9.151950   (mount)[3435]: dev-mqueue.mount: Failed to attach to cgroup /dev-mqueue.mount: No such file or directory
t = 9.151652   (mount)[3436]: sys-kernel-debug.mount: Failed at step CGROUP spawning /usr/bin/mount: No such file or directory
t = 9.315440   systemd-udevd[3457]: /usr/lib/udev/rules.d/50-udev-default.rules:13 Unknown group 'clock', ignoring.
t = 32.252235  systemd-udevd[3511]: Failed to create worker object: Function not implemented
t = 170.209871 nuxel-fb-phone [decon_wait_for_vsync]        <-- animation still running at the end
t = 170.210047 systemd-udevd [SyS_epoll_wait]   (5 udevd processes alive)
```

`systemd-udevd` processes ran for **161 seconds** while `systemd-udevd.service`
was reported failed. That is the decisive clue, and §6 of this document proves
the mechanism.

## 5. Display: first light is real, and the DECON is consuming frames

* Framebuffer geometry is the real panel: `/dev/fb0`, 32 bpp, `stride=5760`,
  `virtual_size=1440,6080`, mode `U:1440x3040p-0` (1440 x 3040 AMOLED).
* `nuxel-fb-phone` ran twice: `pid 3316` (one-shot paint, `FIRSTLIGHT exit=0`) and
  `pid 3342` (`hold` — the resident animator).
* At t = 170.21 the resident animator is in
  `nuxel-fb-phone [decon_wait_for_vsync]` — i.e. it is blocked in the DECON's
  vsync wait, which only happens on a page-flip/commit path. The DECON is
  actively scanning frames out. This is *kernel-side* evidence for what the user
  physically observed on the panel.
* `NUXEL_FB_*` verdict lines from the one-shot paint are still not in the record
  (the A16 rewrite moved the program's stdout to `/dev/kmsg`, but the `hold`
  invocation only logs one line per ~10 s and the ram console's `loglevel=4`
  drops `KERN_INFO`), so the geometry comes from the sysfs dump that `init.sh`
  performs independently — that is the part we can still trust.

**Defect seen:** `FIRSTLIGHT hold started pid=` is empty. `$!` was not captured,
so nothing could ever have supervised or stopped the animator. A17 fixes this
(`A17-INIT-4`, `ANIMATION_HOLD_PID=<pid>` marker + `/var/lib/nuxel/fb-hold.pid`).

### Milestones to record

```
MILESTONE_AMOLED_FIRST_LIGHT=PROVEN
MILESTONE_PENGUIN_ANIMATION=USER_OBSERVED
MILESTONE_FIRST_LIGHT_OBSERVED_AT=2026-10-15
```

## 6. ROOT CAUSE — `pidref_set_pid()` cannot work on Linux 4.14

A13 shipped a source patch to `src/basic/process-util.c::posix_spawn_wrapper()`
that falls back to plain `posix_spawn()` when `pidfd_spawn()` is unsupported.
Forensics on the actual handset show the patched library **was** installed and
**was** the one being loaded:

```
/mnt/ud/usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so
  sha256 502507a7b6237a03cfcff49e389d2a38836916abdea40e36e5ba4653e9bc1234
= A16 initramfs /opt/nuxel/libsystemd-shared-258.11-1.fc43.so     (identical)
```

and `aarch64-elf-objdump -T` on that file shows the fallback really is compiled in
(`posix_spawn@plt` and `pidref_set_pid@plt` are present; the original library has
neither).

So the fallback runs — and then:

```c
/* src/basic/process-util.c, the A13 fallback */
r = posix_spawn(&pid, path, NULL, &attr, argv, envp);   /* SUCCEEDS: executor is running */
if (r != 0) return -r;
r = pidref_set_pid(ret_pidref, pid);                    /* <-- THIS is the failure */
if (r < 0) return r;                                    /* returns -ENOSYS */
```

```c
/* src/basic/pidref.c::pidref_set_pid() */
fd = pidfd_open(pid, 0);                 /* Linux 5.3+; on 4.14 -> ENOSYS */
if (fd < 0) {
        if (!ERRNO_IS_RESOURCE(errno))
                return log_debug_errno(errno, "Failed to open pidfd ...");  /* -ENOSYS */
        fd = -EBADF;
}
```

`pidfd_open()` (syscall 434) does not exist on Linux 4.14, and `ENOSYS` is not
`ERRNO_IS_RESOURCE`, so `pidref_set_pid()` returns `-ENOSYS` **for a process that
was started successfully two statements earlier**. `executor.c` then logs

```
Failed to spawn executor: Function not implemented
```

fails the unit, and the orphaned executor keeps running — which is exactly the
A16 signature (`udevd` alive for 161 s, `systemd-udevd.service` "failed").

### Offline reproduction (deterministic, no phone needed)

Built in `podman`/`fedora:43` (aarch64, glibc 2.42 — the same libc the rootfs
carries) with a preload stub that makes `pidfd_spawn()`/`pidfd_open()/**
pidfd_send_signal()` return ENOSYS, i.e. a 4.14 kernel emulated on a modern one:

| Library under test | `posix_spawn_wrapper()` | child actually ran? | PID1 would log |
|---|---|---|---|
| modern kernel, no stub (control) | `rc=0` | yes | spawn-ok |
| A13/A16 shim, 4.14 stub | **`rc=-38 ENOSYS`** | **YES** | **FAILED-TO-SPAWN-EXECUTOR** |
| A17 library, 4.14 stub | `rc=0` | yes | spawn-ok |

The middle row *is* A16 on hardware, byte for byte. `NEWC`/harness lives in
`.scratch/nx17/` (`stub4k.c`, `psw_test.c`, `fix_pidref.c`).

## 7. Second, independent defect — the cgroup2 mount was shadowed

`A16` logged `CGROUP2_MOUNTED /newroot/sys/fs/cgroup`, but the very next thing
`init.sh` did was mount the pseudo-filesystems, including

```sh
mount -t sysfs sysfs "${ROOT_MNT}/sys"
```

which **stacks a fresh sysfs over `/sys`** and hides the cgroup2 mount underneath
it. In the final namespace `/sys/fs/cgroup` is an empty sysfs directory, so:

* systemd cannot create a per-unit cgroup directory,
* the executor's own cgroup attachment dies with
  `Failed to attach to cgroup /system.slice/<unit>: No such file or directory`
  and `Failed at step CGROUP spawning <bin>: No such file or directory`.

There are therefore **two** independent blockers, and fixing only the library
would not have produced a working boot. A17 fixes both.

## 8. What A16 proves, and what it does not

| Claim | Status |
|---|---|
| S-Boot executes the Nuxel kernel | PROVEN |
| ARM64 kernel runs | PROVEN |
| Built-in initramfs executes | PROVEN |
| USERDATA discovered, Fedora ext4 mounts rw | PROVEN |
| Fedora `systemd` executes as PID 1 | PROVEN (258.11, `basic.target` reached) |
| Nuxel renders on the AMOLED panel | **PROVEN** |
| Animated penguin visible | **PROVEN — user observed** |
| A16 reboots by itself | **REFUTED** — the only reset is the operator's hard-reset hook (`sec_hard_reset_hook` BUG → panic → `sec_reboot`) |
| Any Fedora service runs | **NO** — root cause now known and fixed |
| Live diagnostics during Nuxel runtime | NO (A17 adds a USB CDC-ACM console) |
| DRM/KMS, Phoc, Phosh, touchscreen | NOT PROVEN (unchanged) |
