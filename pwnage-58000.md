# PWNAGE-58000 — Kickstarter: Prove the Idle-Wakeup Reduction on the S10+

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**OS:** Fedora 43 ARM64, systemd 258.11  
**Kernel:** downstream Linux 4.14.253; verify the running build  
**Starting state:** Nuxel booted normally, Wi-Fi SSH available  
**TWRP:** NO  
**Kernel flash:** NO  
**Priority:** High

## Mission

Close the two open items from the merged idle-wakeup work (`794c879`, merge `4140450`, PR #27):

1. The performance service and journald drop-in are now wired into the rootfs builder, but the packaged image and the live handset must be proven to contain the exact bytes.
2. The idle-wakeup reductions have not been measured on the physical handset.

Deliver a reproducible, honest measurement of the committed change. Do not add a broad power-management feature, do not change governors, thermal policy or kernel configuration, and do not claim battery-life improvement without a real power measurement.

## Why 58000 exists

`794c879` reduced polling and syscall churn across:

- the PWA status/location/notification/NFC pollers;
- `nuxel-pwa-host` indicator fallback polling;
- `nuxel-orientationd` snapshot/probe/fsync/idle-tick work;
- the USB monitor’s idle cadence.

It also added:

```text
services/nuxel-performance/bin/nuxel-perf-tune.sh
services/nuxel-performance/systemd/nuxel-perf-tune.service
configs/nuxel/performance/journald.conf
```

At merge time the service and journald policy were committed as source but not installed by `images/s10plus/build-phone-rootfs-inside-fedora.sh`, so a fresh image would not contain them. The idle change was also unmeasured on hardware. PWNAGE-58000 is the proof and shipping pass.

## Starting state to verify first

Do not assume. Record:

```sh
date -u +%Y-%m-%dT%H:%M:%SZ
uname -a
cat /proc/version
cat /etc/os-release
cat /proc/cmdline
git rev-parse HEAD
cat VERSION
systemctl is-system-running
systemctl --failed --no-pager
```

If `/proc/cmdline` contains `androidboot.mode=charger`, stop and reboot normally. Charger/LPM mode disables input before userspace and invalidates the measurement.

## First 30 minutes

1. **Confirm the checkout wiring.**
   - `images/s10plus/build-phone-rootfs-inside-fedora.sh` installs the script at `/usr/lib/nuxel/nuxel-perf-tune.sh`, the unit at `/etc/systemd/system/nuxel-perf-tune.service`, the drop-in at `/etc/systemd/journald.conf.d/50-nuxel-performance.conf`, and the `multi-user.target.wants` symlink.
   - `tools/s10plus/verify-fedora-phone-rootfs.py` requires those exact paths and byte parity.
   - `tools/s10plus/a33/verify-service-graph.py` knows about the unit.
   - `tests/pwnage58000/test_pwnage58000.py` passes.
2. **Capture the live baseline.**
   - `sysctl vm.dirty_writeback_centisecs vm.dirty_expire_centisecs vm.swappiness`
   - `/sys/block/*/queue/scheduler`
   - `systemd-analyze cat-config systemd/journald.conf`
   - `journalctl --disk-usage`
3. **Back up any existing live copies** under `/var/backups/nuxel/p58000-<stamp>/` and hash them.
4. **Install the exact checkout bytes** over Wi-Fi SSH, verify SHA-256, run `sh -n` and `systemd-analyze verify`.
5. **Enable and start the service**, restart `systemd-journald`, and capture `journalctl -u nuxel-perf-tune.service -b`.
6. **Reboot once** and prove the unit ran in the new boot.
7. **Freeze the measurement conditions**: normal boot, not charging unless the arm says so, display state documented, thermal state recorded, no package updates and no continuous SSH log stream.

## Measurement contract

Run at least three matched baseline and candidate arms for:

- display-off idle;
- display-on static Home;
- optionally locked fixed portrait.

For each arm capture `/proc/stat`, `/proc/uptime`, `/proc/loadavg`, `/proc/interrupts`, `/proc/softirqs`, `/proc/vmstat`, `/sys/power/wakeup_count` if present, cpuidle counters, per-process schedstat/io/context switches, journal growth, thermal zones and battery nodes.

Calculate and report separately:

- CPU jiffies;
- context switches;
- interrupts/softirqs;
- journal lines and disk growth;
- battery current if the kernel exposes `current_now`;
- event-path response after deployment.

Commit a bounded, read-only probe and analyzer under `tools/pwnage58000/`. The probe must not write `/dev`, `/sys` or `/proc`, must not restart services, and must not reboot.

The L1 gate is a candidate median at least 10% below the matched baseline in CPU jiffies **or** context switches, with all three runs directionally consistent, no L2 regression above 5%, and no functional regression.

If the gate is not met, report `NOT_IMPROVED`. If conditions were not matched, report `INCONCLUSIVE`. If current/power is unavailable, report `BLOCKED_KERNEL` for that metric. Do not invent a battery-life number.

## What must not change

- Fixed rotations and the display transform mapping.
- Touch calibration.
- The single `/dev/fb0` owner.
- The presenter’s “no double rotation” contract.
- USB mode truth.
- Navigation and host actions.
- Journal storage mode (`Storage=`) — never add it.
- Kernel flash, DTB, recovery, modem, EFS or partitions.

## Acceptance

- [ ] The builder installs and enables `nuxel-perf-tune.service`.
- [ ] The builder installs `50-nuxel-performance.conf` as a drop-in, not a global override.
- [ ] The fresh-image verifier requires the exact bytes.
- [ ] The live device and checkout hashes match.
- [ ] The unit is enabled and ran at boot.
- [ ] The journald drop-in is effective and `journalctl --verify` is clean.
- [ ] Baseline and candidate arms were run under matched conditions.
- [ ] Raw samples and the derived table are preserved.
- [ ] CPU, context-switch, interrupt, journal and battery verdicts are separate.
- [ ] The final result uses `IMPROVED`, `NOT_IMPROVED`, `INCONCLUSIVE` or `BLOCKED_KERNEL`.
- [ ] No functional regression.
- [ ] Reboot persistence is proven.
- [ ] Rollback is tested and documented.

## Deliverables

1. Wiring diff and verifier output.
2. Exact installed paths and SHA-256 hashes.
3. Pre/post scheduler, sysctl and journald values.
4. `journalctl --verify` and disk-usage evidence.
5. Committed probe/analyzer under `tools/pwnage58000/`.
6. Raw samples and derived results.
7. Functional regression results.
8. Reboot and rollback evidence.
9. Honest final verdict.

## Do not

- Do not flash anything.
- Do not use TWRP.
- Do not fabricate samples, battery current or wakeup counts.
- Do not report a poll-interval reduction as a power reduction.
- Do not add deep suspend or autosleep.
- Do not change CPU governors, thermal limits, watchdogs or SELinux.
- Do not rewrite `/etc/systemd/journald.conf`.
- Do not claim success from one run.

**Definition of done:** the exact committed assets are in a fresh image and on the handset, the unit runs at boot, journald is bounded, the idle change is measured against a controlled baseline, and the report states the real result — including a negative one.
