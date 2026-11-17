# SSP recovery continuation — 2026-11-17

Sensor recovery remains blocked on the matching Samsung Android runtime.
Twelve fresh hardware samples are zero for both accelerometer and gyroscope.
No firmware transmission, GPIO reset, power sequencing, partition mounting,
reboot or flashing was performed. No vendor daemon was executed this session.

## Existing UI fixes verified on the live phone

`LIVE_VERIFIED(2026-11-17 05:30 UTC, kernel #3, root SSH)`:
The November 16 fixes in `ab4dc685` are already deployed byte-for-byte.
The boot-session log records profile s10plus, blocked zones [9,10], initially
width zero under the lockscreen, then width 360 upon credential unlock. A
read-only `ui-eval ssp1117geometry` probe through `/run/nuxel-pwa-host.cmd`
measured the visible right cluster at x=177..276 with translateX(-68px).
The exclusion begins at x=276 (zones 9/10 plus padding). There were no dropped
clusters. This confirms the current unlocked Home layout. A new cold boot and
human acceptance were not performed; no additional UI patch was warranted by
this evidence. The prior hidden-to-visible WebKit fixture remains historical.

`/proc/$(systemctl show -p MainPID --value nuxel-button-manager)/exe --menu-dump`
reports 15 entries without screenshot, proving the actual running executable
uses the corrected menu table. Screenshot chord regression still passes.
See [live UI and hub evidence](evidence/ssp-recovery-20261117/live-ui-hub.txt).

## Current hardware evidence

`LIVE_VERIFIED(2026-11-17 05:30–05:32 UTC)` using the supplied key and IP:

- Kernel `4.14.253-gf7194c1d15ed-dirty #3`, built November 14 09:51:04 CET.
- Device-tree model Samsung BEYOND2LTE EUR OPEN 26 / EXYNOS9820.
- BBD/ttyBCM nodes exist; only their metadata was inspected.
- Hub `shutdown=1`, `enable=0x0`, `irq_cnt=0`, `rx=0`, `tx=32`.
- All twelve accelerometer and gyro samples are `0,0,0`.
- No failed systemd units; button manager, Wayland and orientation are active.

Reproduce, choosing a fresh output path:

```sh
python3 -S NUXEL_SSP_RECOVERY_V2/ssp_live_snapshot.py \
  --host 10.11.12.99 --identity-file ~wicked/.ssh/wicked_wqn_id_rsa \
  --output /tmp/ssp-new-samples.json --samples 12 --interval .75 --capture-readonly
```

[Timestamped samples](evidence/ssp-recovery-20261117/live-samples.json) and
[final device checks](evidence/ssp-recovery-20261117/final-live.txt).
This is not a physical six-face test: no working stream is available yet.
Automatic rotation, physical turn correlation, suspend/resume and sensor boot
regressions remain NOT VERIFIED. No fabricated availability or samples added.

## Runtime acquisition result and exact next dependency

`ARCHIVE_REPRODUCED`: fresh audit returns expected status 3 with absent
`/system/bin/linker64` and 28 unresolved DT_NEEDED occurrences (14 names).
[Full gap](evidence/ssp-recovery-20261117/runtime-audit.md).
The local extracted vendor properties cite G975FXXS9DTK9, Android 10 / SDK 29,
but also a repackaged userdebug build `eng.root.20211031.021211`. The local
system properties identify Halium `QQ3A.200805.001/1580`, not Samsung stock.
This remains a build lead, not proven system/vendor provenance. The earlier
Halium daemon crash is REPORT_ONLY for this session; it was not repeated.

`LIVE_VERIFIED`: `/mnt/system-ro`, `/mnt/vendor-ro`, `/mnt/android/system`
are empty, with no stock linker exposed. Stop this extraction path per mission
Stage 1C. No unknown partitions were mounted. Searches of the recovery kit,
repository build/packs artifacts and Downloads found no matching Samsung AP
archive or system/vendor image. No new matching artifact has been supplied.

**Required:** original owner-held SM-G975F AP archive or system/vendor backup,
with build/source metadata. Start with G975FXXS9DTK9 from the original firmware
backup/download or an authorized Samsung firmware source/service. Extract
system.img[.lz4] and vendor.img[.lz4] offline; verify all four acquired vendor
anchor hashes before accepting its runtime. Include Bionic/APEX contents,
linker64, VNDK-29 and transitive libraries, ld.config files and build properties.
No flashing is required for extraction. A hash mismatch means the build must
be investigated, not combined with the existing daemon.

`UPSTREAM_RESEARCH`: the [vendor manifest](https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk)
corroborates components, not an exact build match. [Android linker namespaces](https://source.android.com/docs/core/architecture/vndk/linker-namespace)
explain why static dependency names alone cannot prove ABI/runtime closure.
The Samsung history URL used in the prior report could not be retrieved by
the web tool this session; no new official stock download was established.

## Engineering changes and validation

Added `--identity-file` to the supplied sampler, UTC bounds on each sample,
finite-number validation, and proper report-file closing. New offline tests
verify SSH argv preservation (including spaces), timestamps, no key-path
leakage into evidence, and rejection of NaN/infinity. The first test run
exposed an unclosed report handle; corrected it and reran all 11 kit tests.

All existing commits preserved on `feat/ssp`, starting HEAD `ab4dc685`;
`3d34aef8` remains an ancestor. No pre-existing working changes were discarded.

`ARCHIVE_REPRODUCED` validation:

| Suite | Result |
|---|---|
| V2 recovery toolkit | 11 passed (original 9 plus 2) |
| Native simulations / patch tests | PASS |
| Isolation contracts | 6 passed |
| Runtime audit unit tests | 6 passed, 1 skipped (macOS has no system ELF) |
| Orientation and GNSS | 81 passed |
| Safe-zone boot/geometry, power menu, screenshot chord, button FSM | PASS |
| Embedded kernel patch identity | PASS |
| Runtime dependency closure | INCOMPLETE, expected exit 3 |

Exact commands and logs: [test manifest](evidence/ssp-recovery-20261117/tests.json).
Kernel source HEAD is `f7194c1d15eded1c2a1a4dc63825b26103435cc0`;
[patch verifier output](evidence/ssp-recovery-20261117/test-11.txt) confirms the
897113-byte export hash `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72`.
This establishes source identity, not physical ROM compatibility or ACKs.

Fresh AArch64 production tools and isolation helpers built with GCC 15.2.0;
host simulation compiler Apple clang 17.0.0 arm64. Probe has no interpreter;
logging shim has no DT_NEEDED entries. [Build hashes](evidence/ssp-recovery-20261117/build-sha256.json).
Builds used separate `/tmp/nuxel-ssp-{native,aarch64,helpers}-20261117` directories;
old shipped binaries were not executed. The November 16 actual isolation probe
passed historically; repeating it would not supply the missing Android runtime.

The downloader's `--download` refusal remains intact. Complete matched
ACK/NACK/retry/abort evidence and a device-specific recovery plan are still
missing. No firmware approval request is justified yet. Once the matching
archive is available, resume offline extraction, anchor verification, recursive
runtime audit, hardware-denied probe/lhd trial, then protocol and recovery review
with explicit owner approval before hardware writes.
