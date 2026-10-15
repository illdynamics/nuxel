# A14 post-failure analysis — capture 20261015T130509Z-A14-postfail

**Device:** R58M75KDB2X, Galaxy S10+ (SM-G975F, beyond2lte, Exynos 9820 rev 26),
TWRP 3.7.0_9-2, root ADB, `sec_debug.reset_reason=7`, `androidboot.dtbo_idx=9`.
**Captured:** ram console `/proc/last_kmsg` (2,097,152 B,
sha256 `1d449401a55b7492170a95bf1d279614e68ad15db963a68bb51aca7fd041194e`) and
`/sys/fs/pstore/dmesg-ramoops-0` (27,215 B,
sha256 `1889a6a933ac5765dfc830e7bfea85740d399f26e828b99fdbeb370315e5e219`)
**before** anything else touched the device. pstore was not cleared.
**Last flashed candidate:** A14 (`boot.img`
sha256 `5aff1a109147d33eb017c30423c8ef3bb16d14217d509e829d65d5848d4b4009`),
written and readback-verified on 2026-10-15 11:18:5xZ; the kernel banner in this
log is `#8 SMP PREEMPT Thu Oct 15 11:17:18 UTC 2026` = the A14 build. The phone
was found back in TWRP ⇒ `BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`.

## 1. A14 went much further than any previous candidate

The ram console holds three Nuxel boot sessions (the buffer wraps; the phone was
rebooted more than once before recovery). All three show the same sequence:

| t | milestone (kmsg marker) |
|---|---|
| 2.152 s | `NUXEL_MARKER INITRAMFS_EXECUTED` |
| 2.363 s | `NUXEL_MARKER FIRSTLIGHT_FRAME_WRITTEN` (nuxel-fb-phone exit=0) |
| 3.398 s | `NUXEL_MARKER ROOTFS_MOUNTED` (`ROOTFS_MOUNTED /dev/sda31 ext4`) |
| 3.408 s | `NUXEL_MARKER SYSCALL_PROBE_DONE` (freestanding `NUXEL-SYSCALL` table) |
| 3.410 s | `NUXEL_MARKER SPAWN_PROBE_DONE` |
| 3.411 s | `NUXEL_MARKER SPAWN_PROBE_STATIC_RAN` |
| 3.437 s | `NUXEL_MARKER FEDORA_BINARY_EXECUTED` (`FEDORA_EXEC_OK uid=0`) |
| 3.443 s | `NUXEL_MARKER SPAWN_PROBE_RAN` |
| 3.444 s | `NUXEL_MARKER SYSTEMD_PATCH_PRESENT` |
| 3.447 s | `NUXEL_MARKER ROOTFS_HANDOFF_STARTED` |
| 3.79 s | `systemd[1]: systemd 258.11-1.fc43` logging through kmsg, PID 1 comm `systemd` |

**Milestone 10/11 achieved on hardware:** real Fedora child services now execute.
`systemd-udevd[3483]`, `[3505]`, `[3527]`, `[3539]` are visible in the kernel log
doing real work (`Using default interface naming scheme 'v258'`,
`sec_bat_get_property cable type = 19` from udev events). The A13
`pidfd_spawn`→`posix_spawn` library repair therefore worked; the A12
`Failed to spawn executor: Function not implemented` error does **not** appear
anywhere in this capture.

The syscall probe measures the same primitive, from the device, this boot:
```
NUXEL-SPAWN-PROBE waitid(P_PIDFD,...)      ret=-1 errno=22 EINVAL  -> glibc denies pidfd_spawn
NUXEL-SPAWN-PROBE posix_spawn(/bin/sh,…)   rc=0 child_status=7      -> ok: process really ran
NUXEL-SPAWN-PROBE pidfd_spawn(/bin/sh,…)   rc=38 ENOSYS            -> the A12 systemd error
NUXEL-SPAWN-PROBE fork+execve(/bin/sh,…)   child_status=5 [ok]
NUXEL-SPAWN-PROBE cgroup2_unified=absent
```

## 2. The next blocker is cgroups — not exec

Every unit that systemd tried to start died at the *cgroup* step:

```
<27>[ 3.820983] (journald)[3500]: systemd-journald.service: Failed to attach to cgroup /system.slice/systemd-journald.service: No such file or directory
<27>[ 3.820983] (journald)[3500]: systemd-journald.service: Failed at step CGROUP spawning /usr/lib/systemd/systemd-journald: No such file or directory
```
…identically for `systemd-udev-load-credentials`, `systemd-logind`,
`systemd-userdbd`, `systemd-userdb-load-credentials`, and repeated every ~10 s.
The spawn probe's `cgroup2_unified=absent` is the explanation: **no cgroup
hierarchy was mounted at all**, so there is no `/system.slice/…` directory to
attach to. That is an initramfs-side omission, not a kernel or systemd defect.

Secondary (not yet blocking first light): `systemd-udevd[…]: Failed to create
worker object: Function not implemented` — udevd runs, but its worker spawn path
uses a pidfd/clone3 primitive this 4.14 kernel does not have.

## 3. The spontaneous reboot: our own initramfs watchdog (software)

Answer to the mission's required Phase-2 question: **explicitly requested by
software**. The ram console contains a clean, ordered normal-reboot sequence and
no panic:

* `reboot_notifier_list -> dhd_reboot_callback` … `dbg_snapshot_reboot_handler`:
  `debug-snapshot: normal reboot starting` at **t=47.171346 s**
* `sec_debug: set magic code (0x0)` — the *normal* reboot magic (`0x0`), whereas a
  panic sets `0x66262564` (the pstore record from an older session shows exactly
  that magic).
* Three tasks, PIDs **3557, 3558, 3561**, all with `comm = init`, ran the reboot
  notifier chain within 8 ms of each other; 3561 then drove the whole shutdown
  (`Freezing user space processes` at 107.489 s, `decon_shutdown` 107.798 s,
  `reboot: Restarting system` 107.804 s).
* `comm = init` means these are **this initramfs's own shell lineage** (children
  inherit comm; the bootloader execs `/init`, so PID 1's comm is `init`). Fedora's
  systemd renames itself to `systemd` — it is visibly `[4: systemd: 1]` in the
  same log, so it is *not* the rebooter.
* 0.4 ms earlier, at **t=47.163135 s**, the initramfs dead-man watchdog's probe
  failed: `<12>[ 47.163135] [2: init: 3308] sh: 1/comm: No such file or
  directory`.
* 47.16 s = the watchdog's `sleep "${NUXEL_BOOT_WATCHDOG:-45}"` (armed at
  t≈2.15 s) **exactly**.

Mechanism, from the running code (initramfs `/init`, sha256
`c433ddd976f6903861ccc16872a4e077d120e3ec76ae3f1056cd07038b2c6709`, byte-identical
to the boot/initramfs/init.sh that produced it):

1. `( cd /proc 2>/dev/null || exit 0` runs **before** `/proc` is mounted (the
   `mount -t proc` happens ~90 lines later), so it pins the initramfs's plain
   `/proc` *directory*.
2. 45 s later `IFS= read -r _c < 1/comm` therefore hits ENOENT, `_c` ends up
   empty, and the empty string does not match the allow-list
   (`init|sh|busybox|toybox|ash|dash`) nor the `*)` escape reliably in this toybox
   `sh` — the script walks on into `sync; reboot -f`.
3. Both `WATCHDOG_FIRED` printf lines go to **stdout**, which the block redirects
   to `/dev/null`, so a firing leaves no reason in the log (that is why there is
   no `NUXEL_MARKER WATCHDOG_FIRED` in the capture).
4. The comment's "it reboots only while PID 1 is still this shell" invariant is
   also unenforceable in principle: `switch_root … /sbin/init` makes Fedora's
   systemd PID 1 with *comm `init`* — indistinguishable from the initramfs shell
   by comm alone.

The 60 s between the reboot request (47.17 s) and the actual reset (107.80 s) is
kernel-side shutdown latency (device_shutdown of abox/PCIe/SSD/panel), which is
why the operator's "black screen for 1-2 minutes, then spontaneous reboot" is the
*correct* description of a system that was already told to reboot.

Not implicated: no `Kernel panic`, no `Kernel BUG`, no watchdog bite — the
hardware watchdog was being petted every 10 s throughout
(`s3c2410-wdt … Watchdog cluster 0 keepalive!` from the softdog keeper), and the
`hard_reset_hook` BUG of the A13 attempt does not appear.
