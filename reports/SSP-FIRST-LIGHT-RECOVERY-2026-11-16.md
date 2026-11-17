# SSP recovery and UI repair — 2026-11-16

**Sensor recovery remains blocked.** Twelve fresh samples show accelerometer
and gyroscope `0,0,0`; no physical sensor or auto-rotation success is claimed.
UI fixes are deployed, and a newly built hardware-denied isolation probe passes
on the actual phone. No firmware transmission, GPIO/reset/power sequencing,
partition mount, reboot or flash was performed.

## Identity and evidence

Work began on `feat/ssp` at `dc100f32`, which already includes `3d34aef8` and
`ac6a06ba`. The owner's modified `ssp.md` and untracked recovery kit were
preserved. The previous build directory was inspected without overwriting it.

`LIVE_VERIFIED(2026-11-16 21:10–21:24 UTC)` through
`ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@10.11.12.99`:

- `uname -a`: `4.14.253-gf7194c1d15ed-dirty #3 SMP PREEMPT Sat Nov 14 09:51:04 CET 2026 aarch64`.
- `/proc/device-tree/model`: Samsung BEYOND2LTE EUR OPEN 26 / EXYNOS9820.
- Hub diagnostic: `mcu_probe=1 shutdown=1 resetting=0 sensor_state=0x3feff enable=0x0 shub_irq=443`.
- Kernel diagnostic: `host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 irq_cnt=0 tx=32 rx=0`.
- Hub nodes exist; no transport node was opened outside the hardware-denied probe.
- Twelve timestamped reads of raw accelerometer/gyro and SSP fields: all zero,
  SSP enable zero. Later final reads remain zero. See
  [samples](evidence/ssp-recovery-20261116/live-samples.json).
- `systemctl --failed`: no failed units at the final check. Button manager,
  Wayland session and orientation daemon remain active.

The sample capture imported `ssp_live_snapshot.COMMAND`, used the supplied SSH
identity explicitly, and added UTC timestamps to each result. The script's
stock CLI has no identity-file option. Hostnames are redacted in committed
sample evidence; original diagnostics remain owner-local under
`build/ssp-recovery-v2-20261116/`.

## UI fixes and deployment

The boot log showed the saved S10+ profile `[9,10]` loaded while the Home bar
had width zero under the lockscreen. Earlier source already had configuration
change/unlock handlers and a ResizeObserver. This continuation additionally
makes wake, unlock, configuration and observed-size changes apply layout
synchronously: a previously queued animation frame must not prevent the
newly visible bar from being aligned. Routine provider updates remain coalesced.

The real WebKit fixture also exposed fractional rounding: at width 356, the
free interval ends at 272.8, but a rounded translation put the right edge at
273. The planner now uses inward pixel bounds and preserves the translation's
precision. Final WebKit result: hidden width 0, visible width 356, right cluster
178..272, blocked zones 9/10, **PASS**, without opening Settings. This is an
isolated layout fixture on the handset, **not** an owner-confirmed unlock or a
cold-boot acceptance test. The phone remained credential-locked.

The fixture source is `tools/s10plus/a32/tests/safe-zones-browser.html`; it
loads the real served CSS/layout scripts, replaces provider calls with no-ops,
starts hidden, reveals the bar, and dispatches the normal visibility event.
It reports to `parent.__nuxelSafeZoneBrowserTest`. The temporary served fixture
and iframe were removed, and the launcher was reloaded. Earlier fixture
attempts failed due to a missing CSS class and deferred offscreen animation
frames; only the corrected final result is marked PASS.

The JSON power-menu configuration already omitted screenshot, but the active
A45 button manager compiles the A34 C menu table, which still included it.
Removed that entry and rebuilt A45 with the updated header using on-device
GCC 15.3.1 and ALSA. The running executable now reports 15 entries with no
screenshot. The Power+VolumeDown screenshot chord still passes its FSM test.

Deployed Home files: `index.html`, `js/status-bar.js`, `js/safe-zones.js`,
`manifest.json`, `sw.js`, under `/usr/share/nuxel/pwa/nuxel-home/`.
Cache version: `v087-safezones-startup-2`; both layout script URLs are versioned.
[Live hashes/menu](evidence/ssp-recovery-20261116/ui-deployment.txt) and
[WebKit geometry](evidence/ssp-recovery-20261116/webkit-layout.json).

Rollback, if needed, uses the saved handset files:

```sh
cp /var/lib/nuxel/backups/ui-ssp-20261116-2110/nuxel-button-manager /usr/lib/nuxel/nuxel-button-manager.restore
chmod 0755 /usr/lib/nuxel/nuxel-button-manager.restore
mv /usr/lib/nuxel/nuxel-button-manager.restore /usr/lib/nuxel/nuxel-button-manager
systemctl restart nuxel-button-manager.service
tar -C /usr/share/nuxel -xf /var/lib/nuxel/backups/ui-ssp-20261116-2110/ui-assets-before.tar
# Reload Home normally after restoring its assets.
```

## Matching runtime search

`ARCHIVE_REPRODUCED`: the four acquired vendor anchors match the audited SHA-256s.
The existing `build/ssp-runtime-topbar-20261116/android-extracted` tree has:

- vendor fingerprint `samsung/beyond2ltexx/beyond2:10/QP1A.190711.020/G975FXXS9DTK9:user/release-keys`;
- vendor build ID `QQ3A.200805.001`, userdebug/test-keys, incremental
  `eng.root.20211031.021211` (a repackaged vendor, not a pristine stock identity);
- system fingerprint `halium/lineage_halium_arm64/halium_arm64:10/QQ3A.200805.001/1580:userdebug/test-keys`, security patch 2023-02-05.

These do **not** establish an exact Samsung system/vendor match. The existing
Halium audit records 28 staged files and static closure, but that does not prove
namespace/ABI compatibility. Its old `ssp-lhd-nodev-20261116/syscalls.log`
shows libraries mapped, denied power/control opens, then `SIGSEGV` at NULL and
exit 1. This is historical local evidence, not a trial run in this session.
No mismatched Android runtime was newly executed.

`LIVE_VERIFIED`: `/mnt/system-ro`, `/mnt/vendor-ro`, `/mnt/android/system`
were empty directories after this boot, not mounted stock partitions. No stock
`/system/bin/linker64` is exposed. This extraction path was stopped as the
mission requires; rebooting into TWRP cannot manufacture missing system bytes.
Local repository/Downloads searches found the earlier Halium archive and
unrelated Android emulator images, not the matching Samsung AP archive.

`UPSTREAM_RESEARCH`: Samsung's [build history](https://doc.samsungmobile.com/SM-G975F/005016190410/eng.html)
corroborates G975FXXS9DTK9, but provides no verified matching runtime archive
here. The [vendor manifest](https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk)
and [lhd configuration](https://raw.githubusercontent.com/Evolution-X-Devices/vendor_samsung_beyond2lte/bka/proprietary/vendor/etc/sensor/lhd.conf)
corroborate component paths, not the acquired binary build. Android's
[linker namespace documentation](https://source.android.com/docs/core/architecture/vndk/linker-namespace)
explains why filenames alone do not establish resolution. [Halium](https://docs.halium.org/en/latest/project/Scope.html)
and [libhybris](https://github.com/libhybris/libhybris) provide compatibility
infrastructure, not a provenance match for these missing libraries.

**Indispensable next artifact:** owner-held SM-G975F G975FXXS9DTK9 AP firmware
archive or corresponding system/vendor backup, with original source/build
metadata. Obtain it from the original firmware download/backup or an authorized
Samsung firmware source/service. Extract `system.img[.lz4]` and `vendor.img[.lz4]`
offline; compare all four vendor anchor hashes before using its system runtime.
The fingerprint is a search lead, not permission to skip this comparison.
Include linker64, Bionic/APEX contents, VNDK-29 and transitive libraries,
`ld.config*.txt`, build properties, source URLs/archive hashes. No flashing is
needed for extraction. A mismatching vendor must be rejected and its original
matching build sought instead.

## Isolation implementation and live verification

Hardened `run_isolated.py` to require manifest coverage of every staged file,
reject unlisted loader configuration/libraries, symlinks (including internal
ones), special files and malformed paths, and diagnose missing mountpoint
directories before invoking bwrap. Added regression tests and a cross-build
Makefile for the probe/logging shim. Neither helper introduces hardware stubs.

A fresh static AArch64 probe ran in bwrap with only itself and the original
`lhd` as a read-only file fixture. There was **no Android linker**, so this
fixture cannot execute lhd. It proves isolation only:

- UID/GID 65534, `CapEff=0`, `NoNewPrivs=1`;
- read-only runtime;
- all hub nodes, MCU/GPS power paths, block device and host-root paths denied;
- separate namespaces and no hardware mounts in the recorded command/trace.

First attempt failed because `/proc` and other mountpoint directories were
absent in the read-only root. Created empty directories; repeated probe passed.
On-device static compilation initially failed because libc.a is absent; the
host's AArch64 GNU toolchain successfully produced the static binary instead.

Evidence: [probe output](evidence/ssp-recovery-20261116/isolation-stdout.log),
[result](evidence/ssp-recovery-20261116/isolation-result.json),
[trace excerpt](evidence/ssp-recovery-20261116/isolation-syscalls-excerpt.txt).
Full traces, including failed attempts, remain in the owner-local build folder.

## Protocol gate

`ARCHIVE_REPRODUCED`: kernel checkout HEAD is
`f7194c1d15eded1c2a1a4dc63825b26103435cc0`. Its R-OS embedded header is present
locally, despite being absent from the supplied ZIP. Source verification gives:
897113 export bytes; SHA-256
`0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72`;
ASIC `0x004775b0`; decoded length 438895; address `0x00800161`;
IEEE CRC32 `0x93d35bb4`. Header CRC `0xc1` has an unestablished algorithm.
This is source identity, not proof of the current physical ROM or ACK behavior.

| Protocol element | Current evidence | Next requirement |
|---|---|---|
| TL escape/CRC framing | Existing simulated tests and kernel decoder | Matched live response transcript |
| Patch bytes/address | Host source verifier | Confirm silicon/ROM compatibility |
| Download start/write/start-service ACK | Not established | Matched vendor trace/reference state machine |
| NACK/retry/timeout/abort | Not established end-to-end | Deterministic peer tests plus bounded approved trial |
| GPIO/power effects | Configuration names MCU and GPS controls | Device-specific recovery plan and explicit approval |

`--download` remains fail-closed. Newly built production binaries were not used
for live queries or transmission. A firmware approval request would be premature:
protocol and rollback prerequisites are not yet established. No new boot image
was produced or flashed; existing BOOT remains untouched.

## Reproducible validation

```sh
make -C tools/s10plus/ssp-native OUT=/tmp/nuxel-ssp-v2-native-20261116 clean check
make -C tools/s10plus/ssp-native OUT=/tmp/nuxel-ssp-v2-aarch64-20261116 CC=aarch64-linux-gnu-gcc all
make -C tools/s10plus/ssp-runtime OUT=/tmp/nuxel-ssp-helpers-20261116 all check
python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p test_recovery_v2.py
python3 -S NUXEL_SSP_CONTINUATION_PACK/test_ssp_runtime_audit.py
python3 -S NUXEL_SSP_CONTINUATION_PACK/ssp_runtime_audit.py --repo-root . --report-dir /tmp/ssp-new-audit
python3 -S tools/s10plus/ssp-native/verify_embedded_patch.py kernel/s10plus/.build/src/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h
python3 -m pytest services/nuxel-orientation/tests services/nuxel-gnss/tests -q
node tools/s10plus/a32/tests/safe-zones-boot-test.js
node tools/s10plus/a32/tests/safe-zones-test.js
python3 tools/s10plus/a34/tests/test-a34-power-menu.py
bash tools/s10plus/a34/tests/test-screenshot-chord.sh
bash tools/s10plus/a34/tests/test-fsm-power-bixby.sh
```

Results: native simulated suite and two patch tests PASS; recovery 9/9 PASS;
sandbox 6/6 PASS; ELF-audit tests 6 PASS, 1 skipped on macOS (no system ELF);
audit itself returns expected status 3, 28 unresolved occurrences/14 unique
library names and absent linker; orientation/GNSS 81/81 PASS; all listed UI/FSM
tests PASS. Two old orientation persistence tests initially failed by attempting
real compositor application in an empty fake root. They now use the existing
`--no-apply` option and explicitly retain `blocked_sensor_unavailable`; actual
apply/rollback remains covered by the existing runtime-trial tests.

Host compiler: Apple clang 17.0.0 arm64 for native simulations; GCC 15.2.0
AArch64 cross-toolchain for target helpers/production builds. Build/source
hashes: [manifest](evidence/ssp-recovery-20261116/build-sha256.json).
No proprietary runtime binaries were added to Git.

## Physical acceptance status

| Test | Result | What is needed |
|---|---|---|
| Accelerometer and gyro streaming | FAIL: twelve zero vectors each | Matched runtime and validated hub initialization |
| Six-face / timed gyro turns | NOT RUN | Real stream plus operator movement |
| Sensor IRQ/timestamp flow | FAIL: zero RX/current IRQ count | Verified hub response |
| Physical automatic rotation/touch mapping | NOT RUN | Real stream and axis calibration |
| Sensor suspend/resume, warm/cold boot | NOT RUN | Streaming prerequisite, then bounded hardware tests |
| Home visible after normal unlock/cold boot | Awaiting operator confirmation | Unlock without visiting Settings; cold boot later |

Automatic rotation is not marked available and no synthetic readings were
introduced. Continue with the exact runtime artifact; then repeat manifest
review, isolation probe, hardware-denied lhd trial, protocol/recovery review
and explicit approval before any firmware/reset operation.
