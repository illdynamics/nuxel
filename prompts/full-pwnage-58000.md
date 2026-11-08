# FULL PWNAGE-58000 — Prove and Ship the Nuxel Idle-Wakeup Reduction

## Rootfs wiring, journald bounds, reproducible handset measurement, regression proof and an honest power verdict

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**OS:** Fedora 43 ARM64, systemd 258.11  
**Kernel baseline:** downstream Linux 4.14.253 (`4.14.253-gf7194c1d15ed-dirty` on the 2026-11-01 evidence; verify the running build)  
**Compositor baseline:** Phoc 0.54.0 with the patched wlroots 0.19.3 kbase path  
**Priority:** High  
**Starting state:** Nuxel booted normally, Wi-Fi SSH available  
**TWRP required:** NO  
**Kernel/DTB/partition flash:** NO — no kernel flash; this task is userspace and measurement only  
**Primary objective:** make the already-committed idle changes reproducible in the image, measure them on the physical handset, and report a truthful result.

---

# 0. Mission

Finish and verify the idle-wakeup work that was merged as commit `794c879` (merge commit `4140450`, PR #27).

That change reduced steady-state polling and syscall churn in the PWA, native host, orientation daemon and USB monitor. It also added two runtime assets:

```text
services/nuxel-performance/bin/nuxel-perf-tune.sh
services/nuxel-performance/systemd/nuxel-perf-tune.service
configs/nuxel/performance/journald.conf
```

Two things were explicitly left open and are the scope of PWNAGE-58000:

1. The service and journald drop-in were committed as source but were not installed into `images/s10plus/build-phone-rootfs-inside-fedora.sh`, so a fresh image did not contain or enable them.
2. The idle-wakeup reductions have **not been measured on the physical handset**.

This prompt closes both gaps.

The build wiring is now part of the repository change that accompanies this prompt. The implementation agent must verify that wiring, prove the packaged image contains the exact bytes, run the service on the handset, and measure the result against a controlled baseline.

Do not turn this into a broad power-management feature. Do not change CPU governors, thermal policy, watchdogs, SELinux, block-device contents or kernel configuration. Do not claim battery-life improvement, wakeup reduction or power savings that were not measured.

**The deliverable is evidence, not optimism.**

---

# 1. Verified starting point

The following is known from the repository and the preceding handset work. Treat it as the baseline to verify, not as a result to repeat blindly.

## 1.1 The merge that introduced the changes

| Item | Value |
|---|---|
| Feature commit | `794c879` — `perf(idle): cut idle wakeups across PWA, host, daemon and USB monitor` |
| Merge commit | `4140450` — merge of PR #27 |
| Files changed | 22 |
| Diff | +319 / −49 |
| Physical measurement at merge time | **NONE** |

The commit message states these changes:

- PWA status/location/notification/NFC poll intervals were lengthened.
- `nuxel-pwa-host` indicator fallback moved from 1000 ms to 5000 ms, and detached `systemctl`/`foreign-toplevel` children are reaped with `g_child_watch_add`.
- `nuxel-orientationd` reuses its cached sensor/display snapshot, skips identical JSON rewrites, skips `fsync` for tmpfs status files, and relaxes idle ticks.
- `nuxel-usb-mode.sh` polls at 1 s only during an active file transfer and 5 s otherwise.
- A one-shot `nuxel-perf-tune.service` and a journald size/retention drop-in were added.

## 1.2 Exact code behaviour to preserve

The current source contains at least these measurable decisions. Verify them in the checkout instead of trusting this summary.

| Area | Committed behaviour |
|---|---|
| PWA status bar | phone status 30 s, location 30 s, system indicators 15 s, notifications 30 s, NFC 60 s |
| PWA app status | `app.js` status read 5 s |
| PWA navigation | navigation sync 10 s |
| PWA cache token | `p56000` script tokens and `v83-p56000-perf` cache namespace |
| Native host | indicator signature fallback 5 s; uevent remains the primary path; detached children reaped |
| Orientation daemon | cached sensor/display snapshot; no identical JSON rewrite; no fsync on `/run`; remote sync 30 s; output check 5 s; sensor re-probe 30 s; 0.5 s loop tick when Auto is inactive |
| USB monitor | 5 s cadence while charging or disconnected; 1 s only during an active `file_transfer` session |
| Performance service | one-shot boot unit; sets no-op scheduler on non-rotational devices; `dirty_writeback_centisecs=1500`; `dirty_expire_centisecs=4500`; `vm.swappiness=10` |
| Journald | `SystemMaxUse=512M`, `SystemMaxFileSize=64M`, `RuntimeMaxUse=64M`, `SyncIntervalSec=5m` |

## 1.3 What was still missing before this task

- `images/s10plus/build-phone-rootfs-inside-fedora.sh` did not install the performance script or unit.
- It did not install the journald drop-in.
- It did not create the `multi-user.target.wants` symlink.
- `tools/s10plus/verify-fedora-phone-rootfs.py` did not require those files.
- `tools/s10plus/a33/verify-service-graph.py` did not know about `nuxel-perf-tune.service`.
- No physical handset measurement existed for the new idle cadence.

PWNAGE-58000 must first verify that those gaps are now closed in the checkout, then measure the result.

---

# 2. Non-negotiable operating rules

1. Start with the phone booted normally into Nuxel, reachable over Wi-Fi SSH. Do not start in TWRP.
2. Do not flash a kernel, DTB, boot image, recovery, modem, EFS or any partition. This mission does not authorize a flash.
3. Do not modify the working fixed-rotation mapping, the touch calibration path, the single `/dev/fb0` owner, the compositor transform or the presenter’s no-double-rotation contract.
4. Do not fabricate sensor data, battery percentage, current, wakeup counts, CPU time, journal size or measurement results.
5. Do not touch cpufreq governors, thermal protection, kernel watchdogs, SELinux policy, block-device contents or partition tables.
6. Do not enable deep suspend or `autosleep`. Previous evidence shows deep suspend is not part of the working baseline and would take down `wlan0`, breaking the Wi-Fi SSH path used for the mission. Inspect `/sys/power/state` and report what the kernel actually advertises; do not force a new suspend mode.
7. Do not rewrite `/etc/systemd/journald.conf`. Ship and verify a drop-in at `/etc/systemd/journald.conf.d/50-nuxel-performance.conf`. Never add `Storage=`.
8. Do not treat a short capacity change as power measurement. The fuel gauge’s `capacity` value is coarse and may update slowly.
9. Do not claim an improvement from one run. Use matched conditions, repeated runs and report spread.
10. Every source or live change must have a rollback. A reboot must restore any non-persistent kernel tuning.

---

# 3. Build and deployment contract

The implementation must prove that a fresh image contains the tuning assets and that the live device actually ran them.

## 3.1 Expected install paths

| Repository source | Image path | Mode |
|---|---|---|
| `services/nuxel-performance/bin/nuxel-perf-tune.sh` | `/usr/lib/nuxel/nuxel-perf-tune.sh` | `0755` |
| `services/nuxel-performance/systemd/nuxel-perf-tune.service` | `/etc/systemd/system/nuxel-perf-tune.service` | `0644` |
| `configs/nuxel/performance/journald.conf` | `/etc/systemd/journald.conf.d/50-nuxel-performance.conf` | `0644` |
| enablement | `/etc/systemd/system/multi-user.target.wants/nuxel-perf-tune.service` | symlink to `../nuxel-perf-tune.service` |

## 3.2 Builder checks

Inspect `images/s10plus/build-phone-rootfs-inside-fedora.sh` and verify all three installs and the enablement symlink are explicit. The builder must not install the journald policy over the packaged `/etc/systemd/journald.conf`.

A fresh rootfs build, or a staging build using the same builder logic, must pass:

```sh
python3 tools/s10plus/verify-fedora-phone-rootfs.py --staging <STAGE>
# or, for a completed image:
python3 tools/s10plus/verify-fedora-phone-rootfs.py --ext4 <IMAGE>
```

The verifier must require the exact source bytes for the script, unit and drop-in. A file that merely exists is not enough.

## 3.3 Unit checks

The unit is a one-shot boot service and must remain safe if the script is absent:

```sh
systemctl cat nuxel-perf-tune.service
systemctl is-enabled nuxel-perf-tune.service
systemctl is-active nuxel-perf-tune.service
systemctl show nuxel-perf-tune.service -p Type -p ExecStart -p RemainAfterExit -p TimeoutStartUSec -p Nice
journalctl -u nuxel-perf-tune.service -b --no-pager
systemd-analyze verify /etc/systemd/system/nuxel-perf-tune.service
```

Required properties:

- `Type=oneshot`
- `ExecStart=/usr/lib/nuxel/nuxel-perf-tune.sh`
- `ConditionPathExists=/usr/lib/nuxel/nuxel-perf-tune.sh`
- `RemainAfterExit=yes`
- `TimeoutStartSec=20`
- `Nice=10`
- `WantedBy=multi-user.target`
- enabled in `multi-user.target.wants`

A failed service must be visible as a failed unit. It must not block the boot transaction indefinitely and must not restart in a loop.

## 3.4 Journald checks

```sh
systemd-analyze cat-config systemd/journald.conf
systemctl status systemd-journald.service --no-pager
journalctl --disk-usage
journalctl --verify
journalctl -u systemd-journald.service -b --no-pager | tail -50
```

Required effective values from the drop-in:

```text
SystemMaxUse=512M
SystemMaxFileSize=64M
RuntimeMaxUse=64M
SyncIntervalSec=5m
```

If `systemd-analyze cat-config` merges multiple files, prove the drop-in is present in the merged output and is not overridden later. Do not edit the global file to force the result.

---

# 4. Safety, backup and rollback

Before changing the live device, create a timestamped backup directory and record SHA-256 hashes for every file that will be added or replaced. Use a path under `/var/backups/nuxel/` and copy evidence off-device.

At minimum preserve:

```text
/usr/lib/nuxel/nuxel-perf-tune.sh
/etc/systemd/system/nuxel-perf-tune.service
/etc/systemd/system/multi-user.target.wants/nuxel-perf-tune.service
/etc/systemd/journald.conf.d/50-nuxel-performance.conf
```

Also capture the current live values before the service runs:

```sh
sysctl vm.dirty_writeback_centisecs vm.dirty_expire_centisecs vm.swappiness
for q in /sys/block/*/queue/scheduler; do printf '%s: ' "$q"; cat "$q"; done
for p in /sys/devices/system/cpu/cpufreq/policy*; do
    printf '%s: ' "$p"; cat "$p/scaling_governor" 2>/dev/null || true
done
```

Because the tuning is not written to a persistent sysctl file, an ordinary reboot restores the kernel defaults. Record the pre-service values anyway, so a controlled A/B run does not depend on a reboot.

Rollback procedure:

1. Stop and disable the unit:
   ```sh
   systemctl disable --now nuxel-perf-tune.service
   ```
2. Remove the enablement symlink and the installed unit, script and drop-in only if they were added by this deployment.
3. Restore the captured scheduler and sysctl values, or reboot normally.
4. Restart `systemd-journald` only after removing the drop-in:
   ```sh
   systemctl restart systemd-journald.service
   ```
5. Restore any backup of the PWA/host/daemon files if the live deployment changed them.
6. Re-verify the display, touch, fixed rotations and service graph after rollback.

Do not use `dd`, `mkfs`, partition tools or bootloader interfaces at any point.

---

# 5. Measurement methodology

The measurement must answer four separate questions:

1. Did the new boot service actually apply its declared knobs?
2. Did the journald drop-in take effect and bound journal growth?
3. Did steady-state idle CPU time, context switches or interrupt activity fall versus a controlled baseline?
4. Did the user-visible event paths stay responsive?

These are separate verdicts. A green service check does not prove a wakeup reduction. A lower poll rate does not prove lower battery drain.

## 5.1 Establish an immutable test identity

Record and save:

```sh
date -u +%Y-%m-%dT%H:%M:%SZ
uname -a
cat /proc/version
cat /etc/os-release
cat /proc/cmdline
git rev-parse HEAD
cat VERSION
sha256sum /usr/lib/nuxel/nuxel-perf-tune.sh \
          /etc/systemd/system/nuxel-perf-tune.service \
          /etc/systemd/journald.conf.d/50-nuxel-performance.conf
systemctl is-system-running
systemctl --failed --no-pager
```

If `/proc/cmdline` contains `androidboot.mode=charger`, stop. That is a charger/LPM boot with input disabled before userspace. Reboot normally and restart the measurement. Do not measure on a charger-mode boot.

Ensure the phone is not charging during the battery-current arm unless the arm explicitly measures charging. Record `status`, `capacity`, `voltage_now` and `current_now` if the latter exists.

## 5.2 Define the baseline honestly

There are two valid ways to obtain a baseline. Use one and document which.

### Method A — controlled live A/B for the kernel knobs and journald

1. Capture the current live scheduler/sysctl/journald state.
2. Stop and disable `nuxel-perf-tune.service` and remove the journald drop-in for the baseline arm, restoring the captured values.
3. Run the baseline arms.
4. Reinstall/enable the candidate assets, restart `systemd-journald`, and reboot into the normal candidate state.
5. Run the same arms under identical conditions.

This method isolates the boot-service and journald contribution. It does not isolate the PWA/host/daemon source changes.

### Method B — exact userspace comparison

If a trustworthy pre-58000 userspace backup exists, deploy it to a rollback directory and compare it against the current checkout. If the pre-change bytes are not available, do not invent a baseline. Report `NOT_COMPARABLE` for the PWA/host/daemon contribution.

A comparison against a different kernel, different boot mode, charging state, thermal state or background workload is not a valid baseline.

## 5.3 Test arms

Run each arm three times. Alternate baseline/candidate order to reduce drift, and record the order. Let the phone settle for at least 5 minutes after boot, service completion and display state change.

| Arm | Display | Touch/input | Network | USB | Duration |
|---|---|---|---|---|---|
| L1 — display-off idle | panel off via `nuxelctl display off` | none | Wi-Fi associated, SSH session open but no traffic | unplugged | 10 min |
| L2 — display-on static Home | Home visible, static | no touch | Wi-Fi associated | unplugged | 10 min |
| L3 — locked fixed portrait | locked, confidence | none | Wi-Fi associated | unplugged | 10 min, optional |
| R1 — interaction regression | normal | real touch/rotate/USB | normal | attach/detach | functional, not a power sample |

Do not use Auto rotation as an L1/L2 workload while the sensor hub is unavailable. The daemon will correctly report an unavailable source; that is not a wakeup reduction result.

## 5.4 Sample the right counters

Commit a bounded, read-only probe under `tools/pwnage58000/` (for example `idle-probe.sh`) and an analyzer that emits CSV/JSON. The probe must never write `/dev`, `/sys` or `/proc`, never restart a service and never reboot.

At each sample, capture:

- `/proc/stat` (per-CPU and aggregate jiffies)
- `/proc/uptime`
- `/proc/loadavg`
- `/proc/interrupts`
- `/proc/softirqs`
- `/proc/vmstat`
- `/sys/power/wakeup_count` if readable
- `/sys/power/state` and `/sys/power/mem_sleep` if present
- `/sys/devices/system/cpu/cpu*/cpuidle/state*/{name,usage,time,disable}`
- `/proc/<pid>/stat`, `/proc/<pid>/status`, `/proc/<pid>/schedstat`, `/proc/<pid>/io` for the Nuxel stack
- `journalctl -k --since ...` line counts, not full duplicate logs
- `journalctl --disk-usage`
- `/sys/class/thermal/thermal_zone*/temp`
- `/sys/class/power_supply/*/{capacity,status,voltage_now,current_now}` if present
- `systemctl --failed --no-pager` and `systemctl show <unit> -p NRestarts`

Processes to track:

```text
nuxel-pwa-host
WebKitWebProcess / WebKitNetworkProcess
phoc
nuxel-wl-fb
nuxel-orientationd
nuxel-usb-mode.sh / its monitor process
nuxel-bridge / nuxel-http-bridge
nuxel-web
systemd-journald
```

Use the real process names from the device, not a guessed list. Record a `ps` snapshot with PIDs at the start and end of each arm.

## 5.5 Sampling snippet

The following is a shape, not a complete harness. The committed probe must be bounded and must serialize output cleanly.

```sh
sample() {
    printf '=== %s ===\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    cat /proc/uptime
    cat /proc/loadavg
    cat /proc/stat
    cat /proc/interrupts
    cat /proc/softirqs
    cat /proc/vmstat
    [ -r /sys/power/wakeup_count ] && cat /sys/power/wakeup_count
    [ -r /sys/power/state ] && cat /sys/power/state
    [ -r /sys/power/mem_sleep ] && cat /sys/power/mem_sleep
    journalctl --disk-usage
}
```

Do not sample with `top`, `powertop` or a full `ps` every second; the observer becomes the workload. A 10–30 s cadence is sufficient for a 10-minute arm. Record the actual cadence.

## 5.6 Derived metrics

For each arm calculate:

- total CPU jiffies delta and per-CPU delta;
- context switches from `/proc/<pid>/status` (`voluntary_ctxt_switches`, `nonvoluntary_ctxt_switches`);
- scheduling run time from `/proc/<pid>/schedstat`;
- I/O bytes from `/proc/<pid>/io`;
- interrupt and softirq deltas, sorted by source;
- journal lines per minute and `journalctl --disk-usage` growth;
- cpuidle state usage/time deltas;
- battery current mean and variance if `current_now` exists;
- thermal maximum and drift;
- failed units and service restart count;
- display-off/on and event-path latencies (separate interactive test).

Report median, minimum, maximum and spread for each arm. Do not report only the best run.

## 5.7 What counts as a meaningful result

The project gate for L1 display-off idle is:

- candidate median CPU jiffies **or** context switches at least 10% lower than the matched baseline; and
- all three candidate runs are directionally consistent with the baseline median; and
- no L2 regression greater than 5% in the same metric; and
- no functional regression.

If the threshold is not met, the verdict is `NOT_IMPROVED` or `INCONCLUSIVE`. That is a valid and useful outcome. Do not change the threshold after seeing the data.

For journald, the gate is:

- the drop-in is effective;
- `journalctl --verify` is clean;
- `journalctl --disk-usage` remains below the configured `SystemMaxUse`;
- growth is measured and reported versus the baseline arm;
- no systemd-journald restart loop or corruption appears.

For battery current, the gate is:

- `current_now` is readable and stable in sign across the arm; or
- the verdict is `BLOCKED_KERNEL` for current/power. Capacity alone is not a current or power measurement.

## 5.8 Confounders that invalidate a run

Reject or annotate the run if any of these occurred:

- charger connected or charger-mode boot;
- thermal throttling or a thermal zone above the device’s normal idle band;
- a service restart, failed unit, or manual `systemctl restart` during the arm;
- SSH/console traffic during the arm (the probe itself may write locally, but do not stream a continuous log over Wi-Fi);
- package installation, Flatpak update, media playback or a background WebKit reload;
- display state changed during the arm;
- kernel log flood from an unrelated driver;
- device rebooted or uptime went backwards.

---

# 6. Live deployment procedure

Use the existing Nuxel userspace deployment conventions. A scp/rsync of source files is not proof: every installed file must be hash-compared to the checkout and every service must be checked after install.

## 6.1 Preflight

1. Confirm normal boot and Wi-Fi SSH.
2. Confirm the display is on and the launcher is reachable.
3. Confirm the framebuffer owner is unchanged:
   ```sh
   cat /run/nuxel-wl-fb.state
   fuser -v /dev/fb0 2>/dev/null || true
   ```
4. Confirm the fixed rotation mapping still works in portrait and landscape.
5. Confirm the bridge and orientation daemon are healthy:
   ```sh
   systemctl is-active nuxel-bridge nuxel-http-bridge nuxel-orientationd
   journalctl -u nuxel-orientationd -b --no-pager | tail -40
   ```

## 6.2 Install assets

Create a staging directory on the device, copy the three source files plus any changed PWA/host/daemon files, verify hashes, then install atomically.

```sh
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="/var/backups/nuxel/p58000-$stamp"
install -d -m 0700 "$backup"

# Preserve anything that already exists.
for f in \
  /usr/lib/nuxel/nuxel-perf-tune.sh \
  /etc/systemd/system/nuxel-perf-tune.service \
  /etc/systemd/journald.conf.d/50-nuxel-performance.conf
do
  [ -e "$f" ] && cp -a "$f" "$backup/" || true
done

install -d -m 0755 /usr/lib/nuxel /etc/systemd/journald.conf.d
install -m 0755 services/nuxel-performance/bin/nuxel-perf-tune.sh \
  /usr/lib/nuxel/nuxel-perf-tune.sh
install -m 0644 services/nuxel-performance/systemd/nuxel-perf-tune.service \
  /etc/systemd/system/nuxel-perf-tune.service
install -m 0644 configs/nuxel/performance/journald.conf \
  /etc/systemd/journald.conf.d/50-nuxel-performance.conf
```

Use the repository checkout as the source on the deploying host; do not retype file contents on the phone.

## 6.3 Verify hashes and syntax

On the host:

```sh
sha256sum services/nuxel-performance/bin/nuxel-perf-tune.sh \
          services/nuxel-performance/systemd/nuxel-perf-tune.service \
          configs/nuxel/performance/journald.conf
```

On the device:

```sh
sha256sum /usr/lib/nuxel/nuxel-perf-tune.sh \
          /etc/systemd/system/nuxel-perf-tune.service \
          /etc/systemd/journald.conf.d/50-nuxel-performance.conf
sh -n /usr/lib/nuxel/nuxel-perf-tune.sh
systemd-analyze verify /etc/systemd/system/nuxel-perf-tune.service
```

The three hash pairs must match exactly.

## 6.4 Enable, reload and run

```sh
systemctl daemon-reload
systemctl enable nuxel-perf-tune.service
systemctl reset-failed nuxel-perf-tune.service || true
systemctl restart systemd-journald.service
systemctl start nuxel-perf-tune.service
systemctl status nuxel-perf-tune.service --no-pager
journalctl -u nuxel-perf-tune.service -b --no-pager
```

The service must log which knobs it applied. Expected lines include `nuxel-perf-tune: vm.dirty_writeback_centisecs=1500`, `vm.dirty_expire_centisecs=4500`, `vm.swappiness=10`, and scheduler changes for non-rotational devices.

If a knob is refused, that is a result. Record the read-back value; do not force the write with `echo` outside the script.

## 6.5 Verify the effective state

```sh
sysctl vm.dirty_writeback_centisecs vm.dirty_expire_centisecs vm.swappiness
for q in /sys/block/*/queue/scheduler; do printf '%s: ' "$q"; cat "$q"; done
systemd-analyze cat-config systemd/journald.conf | grep -A12 '50-nuxel-performance'
journalctl --disk-usage
journalctl --verify
```

## 6.6 Reboot once

A reboot is required to prove the unit is enabled at boot rather than only started manually.

After reboot:

```sh
systemctl is-enabled nuxel-perf-tune.service
systemctl is-active nuxel-perf-tune.service
journalctl -u nuxel-perf-tune.service -b --no-pager
systemctl --failed --no-pager
```

Confirm the service ran in the new boot and applied the same values. Also confirm the launcher, display, touch, Wi-Fi and fixed rotations survived.

---

# 7. Interaction regression tests

Power tuning is only acceptable if behaviour is unchanged. Run these after deployment and after the reboot.

## 7.1 Display and touch

- [ ] Portrait and landscape fixed modes still apply and verify.
- [ ] Touch remains aligned in all four fixed modes.
- [ ] There is still exactly one `/dev/fb0` owner.
- [ ] Panel off/on still works via `nuxelctl display off` and `nuxelctl display on`.
- [ ] The presenter logs `presenter_rotation=0` and `double_rotation=0`.
- [ ] No blank frame or static frame after screen-on.

## 7.2 Navigation and host actions

- [ ] Back, Home and Recents work.
- [ ] Long Back still produces its distinct action.
- [ ] Home/Recents remain responsive after a long idle period.
- [ ] No zombie accumulation from detached systemctl/foreign-toplevel children.

## 7.3 Status and notifications

- [ ] Battery, charging state, wired USB, console and notification indicators update on a real event.
- [ ] A status change appears promptly even though the fallback poll is now 5 s; the uevent path must still be the primary source.
- [ ] No stale notification or location state after display-on.
- [ ] NFC remains truthful (`UNSUPPORTED_ON_DEVICE` or the real provider state; never a fake ON).

## 7.4 USB

- [ ] Charging mode is stable while charging.
- [ ] File-transfer mode is detected and the monitor uses its 1 s cadence only while active.
- [ ] A physical unplug is reflected in persisted state and the UI.
- [ ] No mode flap during a transient re-enumeration.
- [ ] MTP still works if it was working before; do not claim it if the host lacks the client.

## 7.5 Journald

- [ ] Boot still completes; PID 1 and udevd behaviour is unchanged.
- [ ] `journalctl --verify` is clean.
- [ ] Disk use is bounded and reported.
- [ ] No log-storage mode change was introduced.

---

# 8. Regression matrix

Record every row as PASS, FAIL, BLOCKED or NOT RUN with evidence.

| # | Check | Command / source | Expected |
|---|---|---|---|
| 1 | Builder installs the script | `images/s10plus/build-phone-rootfs-inside-fedora.sh` | explicit `install -m 0755` line |
| 2 | Builder installs the unit | same | explicit `install -m 0644` line |
| 3 | Builder installs the drop-in | same | explicit drop-in path, not global config |
| 4 | Builder enables the unit | same | `multi-user.target.wants` symlink |
| 5 | Rootfs verifier requires the files | `tools/s10plus/verify-fedora-phone-rootfs.py` | files listed in `FILES` and `SOURCE_PARITY` |
| 6 | Service-graph validator tracks the unit | `tools/s10plus/a33/verify-service-graph.py` | unit in `UNIT_SOURCES` |
| 7 | Unit syntax | `systemd-analyze verify` | clean |
| 8 | Unit is enabled | `systemctl is-enabled` | `enabled` |
| 9 | Unit ran at boot | `journalctl -u ... -b` | expected knob lines |
| 10 | Scheduler values | `/sys/block/*/queue/scheduler` | `noop` selected on non-rotational devices, or honest refusal |
| 11 | Sysctl values | `sysctl` | declared values or honest refusal |
| 12 | Journald effective config | `systemd-analyze cat-config` | declared bounds |
| 13 | Journal integrity | `journalctl --verify` | clean |
| 14 | Journal disk use | `journalctl --disk-usage` | below `512M`; growth measured |
| 15 | L1 idle CPU delta | probe | candidate vs baseline; report direction and spread |
| 16 | L1 context-switch delta | probe | candidate vs baseline |
| 17 | L2 idle CPU delta | probe | no regression greater than 5% |
| 18 | Interrupt/softirq delta | probe | reported by source; no unexplained flood |
| 19 | Battery current | probe | readable and stable, or `BLOCKED_KERNEL` |
| 20 | Thermal drift | probe | no abnormal rise |
| 21 | Failed units | `systemctl --failed` | none |
| 22 | Restart count | `systemctl show -p NRestarts` | no new restart loop |
| 23 | Display/touch | physical | unchanged |
| 24 | Fixed rotations | physical | unchanged |
| 25 | USB state truth | physical | unchanged |
| 26 | Reboot persistence | reboot + checks | unit ran and knobs applied |
| 27 | Rollback | stop/disable + reboot | baseline restored |
| 28 | Reboot restores tuning | reboot + checks | tuning reapplied |

---

# 9. Failure handling

## 9.1 The unit fails

Read `journalctl -u nuxel-perf-tune.service -b`. Determine whether the failure is:

- a missing script (should be impossible; `ConditionPathExists` should skip);
- a refused sysctl (kernel support or permissions);
- a refused scheduler write;
- a permissions or SELinux denial;
- a unit syntax/ordering problem.

Do not change the script to hide the refusal. Report the exact failing knob and the read-back value.

## 9.2 Journald refuses the drop-in

Check:

```sh
systemd-analyze cat-config systemd/journald.conf
journalctl -u systemd-journald.service -b
```

If another drop-in overrides the values, report the ordering and effective result. Do not delete unrelated drop-ins.

## 9.3 A functional regression appears

Stop. Restore the backup, disable the unit, restart affected services, and retest. Do not continue the measurement until the functional regression is explained.

## 9.4 Measurement is noisy

Increase the arm duration or repeat count, not the number of knobs. Do not run the phone under a charger, under a package update, with a continuous SSH log stream or with a hot thermal state. If matched conditions cannot be achieved, report `INCONCLUSIVE`.

## 9.5 The phone is in charger/LPM mode

Stop. Reboot normally. Do not measure, and do not attempt to fix input by userspace writes. The charger-mode behaviour is documented as a distinct boot mode.

---

# 10. Acceptance criteria

## 10.1 Build and deployment

- [ ] The rootfs builder installs the script, unit and journald drop-in.
- [ ] The builder creates the `multi-user.target.wants` symlink.
- [ ] The rootfs verifier requires the exact bytes.
- [ ] The service-graph validator includes the unit.
- [ ] A clean image built from the checkout contains the files.
- [ ] The live device has the same bytes as the checkout.
- [ ] The unit is enabled and ran at boot.
- [ ] The journald drop-in is effective and `journalctl --verify` is clean.

## 10.2 Measurement

- [ ] A baseline and candidate arm were run under matched conditions.
- [ ] Every arm has at least three runs.
- [ ] The probe and analysis artifacts are committed under `tools/pwnage58000/`.
- [ ] Raw samples are preserved, not overwritten.
- [ ] CPU, context-switch, interrupt, journal and battery-current verdicts are separate.
- [ ] The result states one of: `IMPROVED`, `NOT_IMPROVED`, `INCONCLUSIVE`, or `BLOCKED_KERNEL`.
- [ ] No battery-life percentage or hours claim is made without a battery-power measurement.
- [ ] No deep-suspend or autosleep change is claimed.

## 10.3 Regression

- [ ] All fixed rotations still work.
- [ ] Touch remains aligned.
- [ ] Exactly one `/dev/fb0` owner remains.
- [ ] Navigation and host actions still work.
- [ ] USB state remains truthful.
- [ ] Status/notification updates remain event-driven.
- [ ] No failed units or restart loop.
- [ ] Reboot restores the unit and tuning.
- [ ] Rollback is tested and documented.

**Definition of done:** the exact committed performance and journald assets are reproducible in a fresh image, the unit runs at boot on the physical handset, the journald policy is effective and bounded, the idle-wakeup change is measured against a controlled baseline with raw evidence, and the deliverable reports the real result — including `NOT_IMPROVED` or `INCONCLUSIVE` if that is what the data shows.

---

# 11. Deliverables

1. Build-wiring diff and verification output.
2. Exact image paths and SHA-256 hashes.
3. Live pre/post values for scheduler, sysctl and journald.
4. `systemd-analyze verify` and effective-config output.
5. `journalctl --verify` output and disk-usage measurements.
6. Committed idle probe and analyzer under `tools/pwnage58000/`.
7. Raw baseline and candidate samples, with conditions.
8. Derived CSV/JSON plus a human-readable result table.
9. Functional regression results for display, touch, navigation, USB and services.
10. Reboot-persistence evidence.
11. Rollback evidence.
12. A final verdict using the exact vocabulary above.

---

# 12. Final instruction to the implementation agent

Start from the current checkout, not from the contents of the earlier commit message.

First prove the builder, verifier and service-graph wiring. Then deploy the exact bytes to the normally booted handset over Wi-Fi SSH. Enable and run the service, verify the journald drop-in, reboot once, and confirm the unit ran in the new boot.

Then measure. Use matched conditions, at least three runs per arm, and preserve the raw counters. Compare CPU time, context switches, interrupts, journal growth and battery current separately. Do not turn a lower poll interval into an unmeasured power claim.

If the data shows no improvement, say `NOT_IMPROVED`. If the conditions were not matched, say `INCONCLUSIVE`. If the kernel exposes no current measurement, say `BLOCKED_KERNEL` for that metric. A truthful negative result is the correct outcome of PWNAGE-58000; a fabricated reduction is not.
