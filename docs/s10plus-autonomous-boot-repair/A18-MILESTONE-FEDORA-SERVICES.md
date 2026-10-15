# A18 MILESTONE — Fedora services execute on the Galaxy S10+ (2026-10-15)

```
MILESTONE_FEDORA_SERVICE_EXECUTION = PROVEN  (A18)
MILESTONE_CGROUP2_UNIFIED_USABLE    = PROVEN  (A18)
MILESTONE_ROOTFS_HANDOFF_FIXED      = PROVEN  (A18)
MILESTONE_USB_GADGET_BINDS          = PROVEN  (A18)
MILESTONE_LIVE_SHELL_OVER_USB       = NOT YET (ttyGS0 never appeared; A19)
```

Evidence: `captures/20261015T154551Z-A18-postfail/`. A18 ran 15:33:59Z → ~15:45Z.

## 1. Kernel ram console (A18 session)

```
t = 7.242538  FIRSTLIGHT_FRAME_WRITTEN
t = 7.300973  ROOTFS_MOUNTED /dev/sda31 ext4 rw          <-- root resolution FIXED
t = 7.349503  NUXEL_MARKER FEDORA_BINARY_EXECUTED
t = 7.399588  SYSTEMD_LIB already correct: … matches 848149cf… (SHA-256 + ELF verified)
t = 7.406069  CGROUP2_MOUNT_OK /newroot/sys/fs/cgroup
t = 7.407001  CGROUP2_VERIFIED controllers='memory pids'
t = 7.409944  ROOTFS_HANDOFF_STARTED -> /newroot
t = 7.459057  systemd[1]: systemd 258.11-1.fc43 running in system mode
t = 7.703026  Starting systemd-journald.service - Journal Service...
t = 7.839165  Reached target network-pre.target
t = 8.411627  Started systemd-journald.service - Journal Service.   <-- FIRST REAL SERVICE
```

| metric | A16 | **A18** |
|---|---|---|
| `Failed to spawn executor` | 29 | **0** (the single grep hit is our probe's explanatory text) |
| `Failed at step CGROUP` | 61 | **0** |
| `Failed with result` (unit failures) | 28 | **0** |
| services started | 0 | **journald + many `Starting …`** |

## 2. Persistent in-rootfs boot report (new in A18)

`<userdata>/var/log/nuxel-bootreport.txt`, written by the reporter child that starts
**before** any USB work, so it survives a failed gadget bind:

```
is-system-running: initializing          (only ~14 s of systemd: reset intervened)
--- failed units ---
0 loaded units listed.
--- running services ---
systemd-journald.service   loaded active running   Journal Service
--- cgroup ---
controllers: memory pids
self: 0::/init.scope
```

`0 failed units` with journald `active running` is the milestone.

The report also recovered the **full kernel command line**, which the ram console
truncates: `androidboot.bootloader=G975FXXSEFUL1 androidboot.hardware=exynos9820 …`
and **no `androidboot.mode=charger`** — this was a normal, non-LPM boot, which is
why `sec_ts` loaded (see `DEVICE-OBSERVATIONS.md`).

## 3. What this proves

* Both Linux-4.14 systemd blockers in `SYSTEMD-COMPATIBILITY.md` are **fixed on
  hardware**: `pidref_set_pid()` no longer returns `ENOSYS` (0 spawn failures) and
  cgroup v2 is genuinely usable in the final namespace (0 CGROUP failures).
* Rootfs handoff is correct and systemd manages units in cgroups
  (`self: 0::/init.scope`).
* The A18 root-resolution fix works on the device.

## 4. Still open

* The boot was cut short ~14 s after `switch_root` by the operator's hard reset
  (hold at t = 21.77 s, panic at 27.77 s) — this is the beginning of a parallel
  start-up, not a completed one. `is-system-running: initializing` is expected.
* `cgroup2.controllers` is only `memory pids` (no cpu/cpuset) on this 4.14 unified
  root. Worth a look; not blocking.
* **`ttyGS0` never appeared** (`nuxel-console: /dev/ttyGS0 did not appear`) even
  though the ACM gadget bound and macOS enumerated `Nuxel S10+ Live Console`. → A19.
* `sec_ts_input_open: Failed to start device` repeats (TSP `already power on`,
  SSP `ssp_down == true`) — touchscreen device exists but will not start. → Phase 6.
* `fb-hold.pid` is empty because **toybox does not set `$!`** (defect 3 below).

## 5. Three toybox 0.8.14 defects — load-bearing, now documented

Reproduced in podman with the initramfs's own `/bin/toybox`:

1. **An empty `case` alternative is a wildcard**: `case "$D" in mustang|vm|"")`
   matches `D=s10plus`. This made the `DEVICE` dispatch dead code and killed A17.
2. **`if/elif/else` also runs the `else` branch when the FIRST condition is true**:
   ```
   $ toybox sh -c 'if true; then echo THEN; elif false; then echo ELIF; else echo ELSE; fi'
   THEN
   ELSE
   ```
   That is why A18's log shows both `SYSTEMD_LIB_VERIFIED_PRESENT` and
   `SYSTEMD_LIB_IMAGE_MISSING`. Harmless here (the else only logs), but no
   `if/elif/else` chain in this initramfs can be trusted.
3. **`$!` is not set for background jobs** — the animation hold PID has been
   silently empty in A16, A17 and A18 (`TOTAL_NUXEL_MARKERS ANIMATION_HOLD_PID=`).

A19 must remove every `if/elif/else` chain and every `$!` dependency from the
boot-critical path, and every existing elif chain must be re-read with that in mind.
