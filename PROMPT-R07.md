# PROMPT — Component R07: Fix remaining boot instability

> **This file is a prompt for a FUTURE implementation session. It is NOT an
> implementation, and running this worktree does not execute it.** The future
> agent reads this file, then implements **only component R07** in the checked-out
> feature branch `nuxel/r07-boot-instability`.

---

## Agent mission (this branch ONLY)

You are the Nuxel Fedora ARM64 phone OS engineering agent, working in a dedicated
Git feature branch. Implement **only component R07: Fix remaining boot instability**
in this existing repository. Do not implement other screenshot/remaining items; keep
all work inside R07's scope and its own files/tests/reports.

**Target platform:** Samsung Galaxy S10+ `SM-G975F` / Exynos 9820, "beyond2lte" —
Nuxel Fedora ARM64 (Fedora 43 aarch64, systemd 258.11) running **without** the
Android framework. Kernel is the downstream Samsung **4.14.253** `Image`.

**Environment constraints:**
- A MacBook host may build/cross-build/test offline. The live phone may **not** be
  connected during this run.
- Do **not** assume a hardware verification happened. Every device-specific claim in
  your report must be gated on real evidence, otherwise it is `NOT_TESTED` or
  `BLOCKED`.

---

## What "remaining boot instability" means here (context)

Boot has already progressed far: the kernel loads, `/init` resolves root without the
kernel cmdline (A5/cmdline-independence), the systemd graph reaches
`is-system-running = running` (A26), and `nuxel-ui.service` starts on its own. The
**remaining** instability is a set of *containment* fixes that keep the phone from
rebooting itself or wedging mid-boot, plus the ability to **measure** boot/shutdown
timelines and **prove** repeated successful boots — without masking the failures they
paper over.

The concrete, already-diagnosed failure modes this component must correctly address
(or explicitly BLOCK if not yet reachable) are:

1. **`sd-event` pidfd ENOSYS incompatibility on Linux 4.14.** systemd 258 dropped the
   legacy `waitid()` child watcher and requires `pidfd_open()` (Linux 5.3+). On this
   4.14 kernel every call returns `ENOSYS`. This is what made:
   - `systemd-userdbd` fail to run (`Failed to watch child … Function not implemented`) —
     which, via a broken `nsswitch.conf` `[SUCCESS=merge]`, hung **every** NSS lookup.
   - `dbus-broker-launch` die with `-38 ENOSYS` in `launcher_fork`.
   - `systemd-udevd` fork ~17,700 workers in 50 s (`Failed to create worker object:
     Function not implemented`) and never reap them.
   These were **contained** (not fixed) by the A26 rootfs fixes. The durable fix is a
   source patch teaching `sd-event`'s child watcher to degrade to `waitid()` when
   `pidfd_open` returns ENOSYS — done twice before in the A17 change set; R07's job is
   to confirm whether that third edit exists and, if so, un-mask the units cleanly.

2. **Watchdog / retry policy that can reboot a healthy systemd.** The A14 boot-time
   watchdog (removed at A15) could force-reboot a *running* Fedora because it slept
   before `/proc` was mounted and read `1/comm` from the wrong procfs. Samsung's own
   kernel-side `softdog.soft_margin=100 soft_panic=1`, `hung_task_*`, and
   `hard_reset_hook` are still active; R07 must not reintroduce a watchdog that kills a
   healthy boot, but should review the current initramfs `softdog keeper` policy.

3. **The `asix`/`wl_cfg80211_netdev_notifier_call: wdev null` uevent storm.** As udevd
   was un-masking toward full operation it re-added a device thousands of times (same
   UUID each). With udevd masked nothing consumes it. R07 should identify and stop it
   at the driver level **before** relying on an un-masked udevd, not mask around it.

4. **USB recovery console ownership.** The single-owner CDC-ACM live console is started
   from the initramfs (`nuxel-console.c`, flock on `/run/nuxel-console.lock`) and is the
   **only** lifeline today (no ECD/RNDIS/bulk-transfer path exists yet). R07 must not
   let a second instance, a restart loop, or a mid-command cable pull break it.

---

## Required workflow (the four component items)

### 1. Capture kernel-to-userspace boot and shutdown timelines
- Instrument `/init` (`boot/initramfs/init.sh`) so its existing marker channel
  (`INITRAMFS_EXECUTED`, `USERDATA_DISCOVERED`, `FEDORA_MOUNTED`, `ROOTFS_HANDOFF_STARTED`,
  …) is the authoritative **kernel→userspace** timeline. These markers already go to
  `/dev/kmsg` (Samsung `console=ram`) and survive a bootloop; read them from recovery as
  `/proc/last_kmsg`. Do not invent new marker semantics — extend only where gaps exist.
- Capture the **shutdown** path: record how a clean `systemctl poweroff/reboot` is
  observed today (there is no shutdown telemetry proven yet). Where it is missing, add
  a minimal, non-masking hook and persist a timestamped record to USERDATA **and** the
  BOOT-partition tail (dd-readable), reusing the existing `diag_persist()` pattern.

### 2. Isolate failing/restarting units and dependency deadlocks
- Use the **offline** validator `tools/s10plus/a33/verify-service-graph.py` (and its
  fixture-mutation test `tools/s10plus/a33/tests/test-service-graph.py`) to prove the
  boot graph has no cycles, every referenced unit resolves, and the A26 4.14 containment
  edits are still present. These tests already inject defects and must keep failing when a
  defect is injected — require that proof in your run.
- On device (if reachable) capture `systemctl --failed`, `systemctl list-jobs`, and any
  unit in a `activating`/`deactivating`/`restart` state; correlate each with its journal.
  A unit that *restarts* is a failure, not success — do not let `Restart=always` hide it.

### 3. Correct ordering, watchdog and retry policy without masking failures
- If the `sd-event` child-watch compat patch exists in the tree, un-mask
  `systemd-userdbd`, `dbus-broker` (back to systemd) and `systemd-udevd` **in order** and
  re-prove `is-system-running = running`. If it does **not** exist, ship the smallest safe
  containment (the A26 rootfs fixes), keep `*.nuxel-orig` backups, and BLOCK the durable
  un-mask with concrete evidence that pidfd is unavailable (`ENOSYS`) on this kernel.
- Review every shipped unit's `Restart=` / `TimeoutStartSec=` policy. Remove any retry
  that masks a genuine failure (e.g. a console service looping `Restart=always` while it
  cannot own its tty). A bounded, visible failure beats an infinite loop for a debug
  resource like the USB console.
- Do **not** touch BOOT/USERDATA/EFS/DTBO/PIL/bootloader from a running session.

### 4. Protect USB recovery console and measure repeated successful boots
- Keep the console single-owner: `nuxel-console.service` must keep its
  `ConditionPathExists=/usr/bin/nuxel-console`, its flock-based `ExecCondition=…free`,
  and `Restart=no`. A mid-command cable pull must be reported as `console lost`, not a
  traceback. If tools/s10plus/a24-nuxel-console.c's ignore-SIGHUP + re-exec supervisor is
  the current mechanism, verify it still holds; extend only if needed.
- **Measure repeated successful boots.** Define a concrete success metric (e.g. count of
  consecutive boots reaching `PHONE_UI_READY` / `is-system-running = running`, minus any
  watchdog reset). Record the baseline you observe and how many repeats were run. If the
  phone is not connected, state this as `NOT_TESTED` with the exact command you would run.

---

## Repo architecture to reuse (do NOT reimplement or fake)

| Concern | Real location in this repo |
|---|---|
| Initramfs `/init`, marker channel, diag persistence | `boot/initramfs/init.sh` (+ archived variants in `boot/initramfs/`) |
| Boot-image repair / cmdline rewrite tooling | `scripts/fix-boot.sh`, `tools/s10plus/patch-boot-from-upload.py`, `tools/s10plus/patch-rootfs-image.py` |
| s10plus boot image & tests | `boot/s10plus/{flash.sh,recovery.sh,build-candidate.sh}`; `boot/s10plus/tests/` |
| A26 4.14 containment fixes (currently shipped config) | `tools/s10plus/a26/nuxel-rootfs-fixes.sh`, run by `images/s10plus/build-phone-rootfs-inside-fedora.sh` |
| Offline boot-graph validator + fixture tests | `tools/s10plus/a33/verify-service-graph.py`, `tools/s10plus/a33/tests/test-service-graph.py` |
| Single-owner USB CDC-ACM console (initramfs) | `tools/s10plus/a24-nuxel-console.c`; `nuxel-console.service` in `services/nuxel-console/systemd/` |
| Charger/LPM boot-mode guard + guarded reboot | `tools/s10plus/a33/nuxel-bootmode-guard.py`, `configs/nuxel/touch/{nuxel-bootmode-guard,nuxel-bootmode-reboot}.service` |
| sd-event/pidfd history (A17 edits) | `docs/s10plus-autonomous-boot-repair/A17-POSTMORTEM.md` + prior change sets; check for existing child-watch compat code |
| Boot-stall / bootloop diagnosis | `docs/s10plus-autonomous-boot-repair/{NUXEL-BOOT-STALL,A26-SYSTEMD-BOOT-GRAPH-FIX,ROOT-CAUSE}.md`, `docs/s10plus-bootloop-repair/` |

---

## Verified facts vs. things the future agent MUST inspect

### Verified (measured live on the handset or proven offline in prior cycles — cite these)
- On Linux 4.14, systemd 258's `pidfd_open` returns ENOSYS; `systemd-userdbd`,
  `dbus-broker-launch`, and `systemd-udevd` all fail via this path (`A26-SYSTEMD-BOOT-GRAPH-FIX.md`).
- The graph was brought to `is-system-running = running` by containment:
  `authselect/nsswitch.conf` → `files`; mask `systemd-userdbd.{socket,service}`; switch
  system bus to `dbus-daemon.service`; mask `systemd-udevd` (+3 sockets), `udev_log=err`.
- The old A14 reboot watchdog was removed at A15 because it could kill a running systemd.
- `/init`'s cmdline-independence (device-tree model + `PARTNAME=userdata` uevent) is proven;
  boot-diag evidence persists to USERDATA and the BOOT-partition tail, readable with `dd`.
- The USB console is single-owner via flock (`/run/nuxel-console.lock`) and only lifeline.

### NOT verified — inspect before claiming (do not assume)
- Whether the **third** `sd-event` child-watch compat edit actually exists in this tree yet
  (it was "tracked below" as still-open). Search for it; do not assume it is present.
- The current live value of `systemctl is-system-running`, failed/restarting units, and the
  real repeated-boot success baseline **on this exact branch** — re-measure on device if
  connected, else mark `NOT_TESTED`.
- Whether the `asix`/`wl_cfg80211_netdev_notifier_call: wdev null` storm is still present or
  already stopped at the driver level.
- The shutdown-timeline telemetry: whether any exists today (likely none) — verify, then add.

---

## Implementation steps (order; adapt to what you find)

1. **Source audit.** Read `boot/initramfs/init.sh`, `verify-service-graph.py`, the A26
   rootfs fixes script, and the console unit/c source. Record existing behaviour in
   `docs/component-reports/r07.md` before changing anything.
2. **Boot graph integrity.** Run the offline validator + its fixture test; confirm green
   baseline and that each injected defect fails as documented. Fix any cycle/unsatisfied-dep
   you introduce while working.
3. **sd-event / pidfd path.** Locate or implement the child-watch `waitid()` fallback for
   ENOSYS (reuse the A17 edits). If implemented: un-mask userdbd → dbus(systemd) → udevd in
   order and re-prove the graph. If not: keep the A26 containment, add a precise blocker with
   evidence (`pidfd_open` ENOSYS on 4.14), and stop — do not ship half-un-masked units.
4. **Watchdog & retry policy.** Review `Restart=`/timeout policies across shipped units;
   remove any that mask failure (especially the console). Keep the initramfs `softdog keeper`
   but confirm it never fires on a healthy systemd (it exits once systemd owns PID 1).
5. **UEvent storm.** Identify and stop the `asix`/`wl_cfg80211_netdev_notifier_call: wdev null`
   storm at the driver level before depending on an un-masked udevd, if it is still present.
6. **Timeline + shutdown telemetry.** Extend `/init`'s marker channel where gaps exist; add a
   minimal shutdown-timestamp hook persisting to USERDATA + BOOT tail via `diag_persist()`.
7. **Console protection.** Verify/extend the single-owner console (ignore-SIGHUP, flock,
   `Restart=no`, `console lost` on cable pull). Never run a second framebuffer client or open
   `/dev/fb0` from diagnostics (closing it powers the panel down).
8. **Tests.** Add unit/integration tests that exercise real code paths and failure modes — not
   static references. Prefer extending existing offline tests; for AArch64 native code,
   cross-build or document precise toolchain restrictions; never pass off a mock as a physical
   check.
9. **Report & commit.** Write `docs/component-reports/r07.md`; commit **only** R07's files/tests/
   report on this branch. Do not merge, switch branches, add secrets, or touch unrelated work.

---

## Tests (must exercise real behaviour and failure paths)

- Extend `tools/s10plus/a33/tests/test-service-graph.py` fixture cases to cover any new unit:
  injected restart-loop that masks a console-tty conflict → must FAIL; unsatisfied dep → FAIL;
  forbidden 4.14 dependency → FAIL.
- Add an offline test for the `/init` timeline functions under test (device-tree model decode,
  `block_by_partname userdata`, BOOT-tail diag slot) using the same extraction pattern as
  `boot/s10plus/tests/test-init-cmdline-independence.sh`.
- If native code is added/changed, add a build/compile check and, where feasible on host, a unit
  test of pure logic; document AArch64 cross-build toolchain precisely.
- Never claim physical boot success unless measured on the handset this run.

---

## Acceptance gates (each must be met or explicitly BLOCKED with evidence)

- [ ] Boot/shutdown timeline captured (`NOT_TESTED` documented if no shutdown telemetry is possible).
- [ ] Failing/restarting units and dependency deadlocks isolated; validator green + fixture failures proven.
- [ ] Ordering/watchdog/retry policy corrected **without masking** any failure (no `Restart=always` hiding a real fault).
- [ ] USB recovery console still single-owner and survives cable pull as `console lost`.
- [ ] Repeated successful boots measured, or explicitly recorded as `NOT_TESTED` with the exact command.
- [ ] Every item above is implemented or BLOCKED/NOT_TESTED with concrete evidence — nothing omitted.
- [ ] No BOOT/USERDATA/EFS/DTBO/PIL/bootloader written from a live session; no flashing/reboot of hardware claimed.
- [ ] `docs/component-reports/r07.md` written; worktree clean after committing only R07.

---

## Honest hardware verification (do NOT fabricate)

- Live phone may be **disconnected**. If it is connected, capture: `/proc/last_kmsg` marker
  timeline, `systemctl is-system-running`, `systemctl --failed`, process count under udevd,
  and consecutive-boot success count — cite exact commands + outputs.
- If disconnected, write a BLOCKED/NOT_TESTED evidence report stating precisely which checks
  were pending and the exact commands you would run on-device. State the actual deployment
  status; never claim a physical pass or a reboot that did not happen.
- Any hardware operation here is **read-only-ish** (reading logs, measuring timers). Flashing,
  bootloader/partition writes, kernel replacement, or unsafe LED/amplifier settings remain
  **forbidden**.

---

## Rollback

- Keep `*.nuxel-orig` backups of any edited unit/config/script; the A26 rootfs fixes script is
  the reference pattern (idempotent, keeps originals).
- If un-masking udevd/userdbd/dbus-regresses, re-mask them and restore the previous boot image
  SHA from a pre-write backup (record the baseline SHA before any device change).
- Commit only R07 on `nuxel/r07-boot-instability`; the queue runner owns git. Leave a clean
  worktree.

---

**Deliverables in this commit:** source/service/config changes, tests, and
`docs/component-reports/r07.md`. Nothing else. COMPONENT R07 ONLY.
