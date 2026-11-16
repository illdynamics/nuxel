Other requests were checked in source and are already implemented: NFC/location/Wi-Fi icons hide when off, notification cue is `nuxel-pow.mp3`, edge FX supports notification/screen-on/off/lock/unlock toggles. Boot-audio timing and Maps/Weather location were not changed — those need their own focused passes.

**To continue:** reconnect the phone in TWRP. I'll verify identity and boot partition, back up, flash `boot-ssp-v3.img`, boot Nuxel, then run the three physical rotation cycles and the Force checkbox test with you.
I've reached the point where the remaining work is hardware-gated. Here's the honest state:

## What I found and implemented

**Root cause (measured, not guessed):** the hub answers its probe-time chip-ID (`BCM47752KUB1G`, `BR0121080900,BR010`), then the driver sets `bSspShutdown = true`. The only code path that clears it is `ESW:READY` from the Android vendor daemon `lhd` — which is Bionic (`/system/bin/linker64`) and cannot run under Nuxel. So the kernel drops every message (`sspb_down == true. returning`) and `raw_data` stays `0,0,0` forever.

**Kernel fix — built and gated, not yet flashed** (`boot-ssp-v3.img`, SHA256 `cbcc4335…45b72e`):
- `nuxel_ssp_bringup_hw()` — kernel-owned enable → `initialize_mcu()` → `sync_sensor_state()` (patch `0013`, marked `.required`)
- keeps the hub enabled after probe; forwards zero-length stream messages
- makes the shared host-req IRQ ownership/depth explicit (the native peer used to disable the line under the hub)
- adds `gyro_sensor/raw_data` (there was no live gyro node before) and `nuxel_hub_diag` / `nuxel_bringup` sysfs
- build RC=0, capability parity PASS, boot-image gate PASS; nftables/NFT_META/NFC/USBNET/userns all preserved

**Userspace — deployed live over SSH, with backups:**
- native `nuxel-ssp-bridge` (glibc, no Bionic): relays the real kernel BBD ABI, never synthesises samples
- `nuxel-orientationd` now prefers `iio-sysfs-accel-gyro`: absolute orientation from gravity, gyro as rate assist, existing hysteresis/debounce
- **per-app Force checkbox** in Settings → Apps: unchecked = starts in that orientation but can still rotate; checked = can only run in it until unchecked. Verified live: `force=true … applied=true`, then `force=false`, no stale lock in `app-defaults.json`

## What is blocked

- **Flash: not done.** `adb devices` is empty even after restarting adb; only SSH works, so device/boot-partition verification and the pre-flash backup can't be performed. The procedure and rollback target are written down verbatim in `PWNAGE-SSP-REFLASH-LOG.md` §7.4.
- **Auto-rotation: NOT TESTED — OPERATOR REQUIRED.** The phone is still on kernel `#32`, sensor is `0,0,0`, and the daemon correctly reports Auto as blocked. I won't claim rotation from a zero sensor, and nothing rotates from synthetic data.      
- **Per-app firewall flag: PARTIAL.** The config is present, but `unshare -U` still fails with `ENOSPC` on `#32` (pre-existing, fails inside `create_user_ns()` before the policy checks). I'm not claiming it fixed.

Other requests were checked in source and are already implemented: NFC/location/Wi-Fi icons hide when off, notification cue is `nuxel-pow.mp3`, edge FX supports notification/screen-on/off/lock/unlock toggles. Boot-audio timing and Maps/Weather location were not changed — those need their own focused passes.

**To continue:** reconnect the phone in TWRP. I'll verify identity and boot partition, back up, flash `boot-ssp-v3.img`, boot Nuxel, then run the three physical rotation cycles and the Force checkbox test with you.
tokens used
70,567,311
[codeseeq] stopping owned bridge process (pid=97788)

