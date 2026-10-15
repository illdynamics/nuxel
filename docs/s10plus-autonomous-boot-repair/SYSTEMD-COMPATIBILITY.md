# SYSTEMD COMPATIBILITY ON THE S10+ (Linux 4.14.253, Fedora 43 / systemd 258.11)

This is the reference for *why* the Fedora userspace in Nuxel cannot start
services on the Samsung Exynos 9820 kernel, what was actually changed, and how to
verify it without a phone.

## 1. The two independent blockers

Both must be fixed. Fixing either alone leaves the phone unable to start a single
service.

### Blocker 1 — `pidfd_spawn()` needs `waitid(P_PIDFD)` (Linux 5.4)

`src/core/execute.c::executor_spawn()` starts every unit via
`posix_spawn_wrapper()`. In 258.11 that function calls glibc's `pidfd_spawn()`,
and glibc returns `ENOSYS` unconditionally when its
`__clone_pidfd_supported()` probe fails (it needs `waitid(P_PIDFD, ...)`, added
in Linux 5.4, *independently* of `clone3()`). 258.11 then retried
`pidfd_spawn()` after clearing `POSIX_SPAWN_SETCGROUP` instead of falling back.

> Measured on the handset: `NUXEL-SPAWN-PROBE pidfd_spawn(...) rc=38 ENOSYS`
> (A12, A15, A16 ram consoles).

**Fix (edit 1):** upstream systemd's own later change — fall back to plain
`posix_spawn()` when `ERRNO_IS_NOT_SUPPORTED(r)`. `posix_spawn()` uses
`clone3()` with a `clone()` fallback and works on 4.14.

### Blocker 2 — `pidfd_open()` needs Linux 5.3 (THE ONE THAT WAS MISSED)

`posix_spawn_wrapper()`'s fallback calls `pidref_set_pid(ret_pidref, pid)`, and
`src/basic/pidref.c` does:

```c
fd = pidfd_open(pid, 0);
if (fd < 0) {
        /* Graceful fallback in case the kernel is out of fds */
        if (!ERRNO_IS_RESOURCE(errno))
                return log_debug_errno(errno, "Failed to open pidfd for pid " PID_FMT ": %m", pid);
        fd = -EBADF;
}
```

`pidfd_open()` is syscall 434, added in Linux 5.3. On 4.14 it is `ENOSYS`, which
is **not** `ERRNO_IS_RESOURCE`, so this returns `-ENOSYS`.

Consequence, and the reason A13–A16 all looked like "spawn is impossible":

```
posix_spawn(...)          -> 0        the executor IS running
pidref_set_pid(...)       -> -ENOSYS  reported back to PID1
=> execute.c: "Failed to spawn executor: Function not implemented"
=> the unit is marked failed; the executor is orphaned and keeps running
```

A `PidRef` without a pidfd is an **explicitly supported state** (`pidref.h`
documents `-EBADF` for "no pidfd"; `pidref_acquire_pidfd_id()` already tolerates
`ERRNO_IS_NEG_NOT_SUPPORTED`, and every consumer — `pidref_kill`, `pidref_wait`,
`pidref_verify` — degrades to PID-only operation).

**Fix (edit 2):** degrade to a PID-only `PidRef` on `ENOSYS`/`EOPNOTSUPP`/`ENOTTY`
instead of failing. Nothing else in the code path needs a pidfd.

### Blocker 3 (not a library bug) — cgroup v2 was never really mounted

systemd 258 requires the unified cgroup v2 hierarchy; cgroup v1 support is gone.
A16 mounted cgroup2 under `/sys/fs/cgroup` and then ran
`mount -t sysfs sysfs /sys`, which **stacked a new sysfs over the mount and hid
it**. In the final namespace `/sys/fs/cgroup` was an empty sysfs directory, so no
per-unit cgroup directory could be created and every executor died with
`Failed at step CGROUP spawning <bin>: No such file or directory`.

**Fix (init.sh):** mount cgroup2 *after* the sysfs mount (last thing before
`switch_root`) and then **verify** by reading `/sys/fs/cgroup/cgroup.controllers`
— not by trusting the mount exit status.

## 2. Kernel configuration prerequisites (verified in `A16`/`A17` `.config`)

```
CONFIG_CGROUPS=y        CONFIG_MEMCG=y           CONFIG_CGROUP_SCHED=y
CONFIG_CGROUP_PIDS=y    CONFIG_CGROUP_FREEZER=y  CONFIG_CPUSETS=y
CONFIG_CGROUP_DEVICE=y  CONFIG_CGROUP_CPUACCT=y  CONFIG_CGROUP_BPF=y
CONFIG_NAMESPACES=y
```

Note `CONFIG_CGROUP_BPF=y` but `bpf-restrict-fs: BPF LSM hook not enabled`
(`CONFIG_BPF_LSM` is not set). systemd 258 warns about this and proceeds:

```
Unit systemd-journald.service configures device ACL, but the local system doesn't
seem to support the BPF-based device controller. Proceeding WITHOUT applying ACL
```

That is a warning, not a blocker. `Attaching device control BPF program to cgroup
... failed: Argument list too long` (E2BIG from `bpf()`) is the same story.

## 3. The change set (A17)

| # | File | Change |
|---|---|---|
| 1 | `src/basic/process-util.c` | `posix_spawn_wrapper()`: fall back to plain `posix_spawn()` when `pidfd_spawn()` is not supported (A13, unchanged) |
| 2 | `src/basic/pidref.c` | `pidref_set_pid()`: degrade to a PID-only `PidRef` when `pidfd_open()` is not supported **(new in A17)** |
| 3 | `boot/initramfs/init.sh` | cgroup2 mounted after sysfs + verified; library deployment is SHA-256/ELF verified, atomic, rollback-capable, and marked only after post-install re-verification |

Built from the **exact installed SRPM** `systemd-258.11-1.fc43.src.rpm` with
`rpmbuild` so every other byte tracks Fedora:

```
.scratch/nx17/nuxel-systemd-edit.py     # the two source edits, anchored + fail-loud
.scratch/nx17/build-systemd4.sh         # podman/container driver
podman exec sd258 sh /b/nx17/build-systemd4.sh
```

Artifact delivered (BOOT-partition-only update, no rootfs write):

```
usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so
  bytes  5,072,280
  sha256 848149cf4b506aef00c0f777840c8e0b5306b65dcf1ae0a1b8c1a63057b4d981
```

`posix_spawn_wrapper` and `pidref_set_pid` both live in `libbasic`, which is
linked into `libsystemd-shared`; `systemd` and `systemd-executor` are unchanged
and reference neither `pidfd_spawn` nor the patched helpers directly.

## 4. Verification without a phone (do this before every flash)

`podman`/`fedora:43` is aarch64 with glibc 2.42 — the same libc generation the
rootfs carries — so the whole spawn path can be exercised offline.

```sh
# .scratch/nx17/stub4k.c  : pidfd_spawn/pidfd_open/pidfd_send_signal -> ENOSYS
# .scratch/nx17/psw_test.c: calls the real posix_spawn_wrapper() from libsystemd-shared
podman exec sd258 sh -c 'cd /b/nx17 && \
  LD_PRELOAD=/b/nx17/libstub4k.so ./psw_test -'
```

Measured results:

| Library | `posix_spawn_wrapper()` | child really ran | PID1 logs |
|---|---|---|---|
| modern kernel, no stub | `rc=0` | yes | spawn-ok |
| A13/A16 shim, 4.14 stub | `rc=-38 (Function not implemented)` | **yes** | **Failed to spawn executor** |
| **A17 library, 4.14 stub** | **`rc=0`** | **yes** | **spawn-ok** |

The middle row reproduces A16 on hardware exactly, including the "child ran but
the unit failed" anomaly. That is the proof the fix is the right one.

## 5. What still has to be proven on hardware

The offline harness proves the library's behaviour; it cannot prove that Fedora's
unit graph completes. Hardware success criteria for A17:

1. `SYSTEMD_LIB_INSTALLED_VERIFIED` or `SYSTEMD_LIB_VERIFIED_PRESENT` marker.
2. `CGROUP2_VERIFIED` with a non-empty `controllers=` list.
3. **No** `Failed to spawn executor` in the ram console.
4. Units reaching `Started`/`Reached target` beyond the four path/timer units
   A16 managed: specifically `systemd-udevd.service`, `systemd-journald.service`,
   `dbus-broker.service`, `systemd-logind.service`.
5. A live shell on the USB console (§LIVE-DEBUG-CONNECTIVITY.md) whose
   `systemctl --failed` list is short.
