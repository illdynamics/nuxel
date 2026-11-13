# SSP sensor-hub continuation — 2026-11-13 20:30–22:00 CET

Read `ssp.md` (previous state) first. This continues from there.

## Measured result

| Capability | Status | Evidence |
|---|---|---|
| SSH / Wi-Fi | **PASS** | `ssh nuxel` (alias added) 3/3 connects; `wlan0 Nuxel Ziggo5501109 activated`, 192.168.178.167/24 stable |
| Manual rotation — all 4 fixed modes | **FIXED, live, survives reboot** | `nuxelctl orientation set <mode>` moves the live compositor: portrait→normal, landscape→270, reverse-portrait→180, reverse-landscape→90 |
| Auto modes (auto / auto-portrait / auto-landscape) | **selectable; rotation BLOCKED (honest)** | `auto_state=blocked_sensor_unavailable`, `applied=true` on the safe pose, no false claim |
| Accelerometer / gyro streaming | **FAIL** — hub does not drive SPI MISO | every read `0xFF`; `HSI_CTRL`/`RNGDMA` all `0xFF` |
| Auto rotation (landscape detection) | **NOT POSSIBLE** — no live gravity source | cannot be tested without accel data; nothing fabricated |

## Bugs actually found and fixed this session

1. **`nuxelctl orientation set <mode>` never rotated.** The CLI defaulted
   `apply_now=False`, so the daemon changed the *policy* but applied no
   transform. Fixed in `services/nuxel-orientation/nuxel-orientationd`
   (`set` now applies unless `--no-apply`), deployed live to
   `/usr/libexec/nuxel/nuxel-orientationd` (sha256 `388831a5…`), verified
   across a reboot. This is why "landscape" showed `transform: normal`
   before.

2. **BCM47752 1.8 V rail was never actually enabled.**
   `ssp_dev.c` did `regulator_get()` but never `regulator_enable()`; the rail
   read "enabled" only because the bootloader left it on
   (`num_users == 0`). `ssp_sysfs.c set_mcu_power()` likewise skipped the
   enable when `is_enabled()` was true. Both now take a real reference.

3. **SPI controller lost its configuration across runtime suspend.**
   `spi-s3c64xx.c` gates clocks and drops the FIFO/mode config on runtime
   suspend but only re-ran `s3c64xx_spi_hwinit()` for the system-resume
   path. Now `need_hw_init` is set in runtime suspend (DOMAIN_TOP) and the
   runtime resume re-initialises. This is exactly why `10970000.spi` read
   `0xFF` after the first idle while the same kernel read real registers
   (`00914548…`) immediately after a cold boot.

All three are recorded as `kernel/s10plus/patches/0020-nuxel-ssp-hub-power-and-pm.patch`
(+ `.required`).

## Native BBD/RPC downloader (new)

`tools/s10plus/ssp-native/nuxel_bbd_download.c` — a native (glibc) host for
the BCM47752 BBD transport, reconstructed from the kernel's own reference
decoder and from the **owner's own lhd binary** (`sensors/acquired/vendor-bin-hw-lhd`,
which ships MiniDebugInfo, so every protocol function has a symbol):

* TL encode/decode: 0xB0/0x00/0x01 framing, seqId, flags, CRC-8 table,
  reliable packets — round-trip self-test passes on-device.
* RPC framing: `[rpcId 7-bit-ext][len 7-bit-ext][payload]`.
* RPC ids recovered from `RpcGlobalRequestEncoder` / `RpcMemoryAccessEncoder`:
  `0x00 GetVersion`, `0x3A GetVersionExt`, `0x2E StartScratchApp`,
  `0x05 MemoryWrite`, `0x37 ServiceStart`, `0x36 SetInterrupt`.
* Reads `/dev/bbd_patch` (897 113 B, `AsicVersion=0x004775b0`,
  `BlobLength=438895`, `PatchAddress=0x00800161`) and decodes the 438 895-byte
  `<Blob=>` payload correctly.
* Kernel hook `bbd_nuxel_peer_tl_rx()` (bbdpl/bbd_rpc_lh.c + ssp_bbd.c)
  forwards CRC-valid TL packets to the native peer on `/dev/bbd_sensor`
  with a private `0xFF` tag.

**Important measurement:** after a *cold boot* the same SPI bus does return
real hub registers. Once the bus idles the hub stops driving MISO and every
read is `0xFF`; that state persists through rail power-cycling
(`set_mcu_power` is a no-op because the regulator reports already-enabled).

## Hard hardware boundary (measured, not assumed)

* `ssp-gps-pwr-en` = **gpg0-2 = GPIO 145** (`GpioNStdbyPath` in lhd.conf) is
  driven low by the driver. Driving it high while the SSP peer is open
  **hard-resets the phone** (reproduced twice: the device reboots and
  auto-lands in recovery). It powers the GPS subsystem, not just standby.
* `MCU_RESP` (gpg4-2) reads **high even with the hub rail off** — it is a
  pull-up, so the driver's `bcm477x_hello()` handshake cannot detect a
  sleeping/halted hub.
* There is no hardware reset GPIO in DT; reset is rail-only.

Practical consequence: on this unit, with this kernel and this board, the
BCM47752 only answers immediately after a cold power-on and must then be
driven continuously by a *correct* firmware-download sequence. Doing that
requires the vendor `lhd` patch-download protocol (now partially
reconstructed) running continuously from boot, or the vendor lhd itself in
an isolated Bionic root — no Bionic runtime exists anywhere on this device.

## Deployed state

* Live kernel **#78**, `SPI hw-init after runtime-suspend`, hub rail held,
  `boot-ssp-v24` flashed (verified sha256 on device readback).
* `boot-ssp-v16…v24` images and manifests under `build/out/s10plus/ssp/images/`;
  pre-flash donor backup `backups/boot/boot-donor-20261113-2105.img`.
* `nuxel-orientationd` fix live + in the repo source.
* `nuxel-ssp-bridge` remains masked (the bridge cannot make the hub stream);
  orientation reports the honest reason instead.

## What would finish auto rotation

1. Recover a matching Bionic runtime (linker64 + libc/liblog/…) and run the
   owner's `lhd` in an isolated prefix from boot, **or**
2. complete the native download: keep the hub awake from cold boot and drive
   `GetVersion → (autobaud) → StartScratchApp → MemoryWrite blob → ServiceStart`
   continuously — the decoder, RPC ids and patch image are already here.
3. Then: calibrate the mount matrix, feed `nuxel-orientationd`, test the four
   poses physically (the handset is currently held sideways, so the first
   auto test should show a 90°/270° result).

Nothing in this report claims a sensor reading that was not measured.

## Final live verification (22:00 CET)

```
$ uname -v
#78 SMP PREEMPT Fri Nov 13 21:47:16 CET 2026
$ systemctl is-system-running
running
$ systemctl --failed            (none)
$ uptime                       up, load normal
$ df -h /                      47G/111G used
$ free -m                      5.7 GiB available

# rotation (live compositor read-back, screen capture dimensions)
portrait           -> Transform: normal, grim 720x1520     PASS
landscape          -> Transform: 270,    grim 1520x720      PASS
reverse-portrait   -> Transform: 180                        PASS
reverse-landscape  -> Transform: 90                         PASS
auto*              -> blocked_sensor_unavailable (honest)   selectable

# SSP hub (measured)
vdd_mcu_1p8 num_users   = 0  (enable returned 0; rail on from bootloader)
spi 10970000.spi PM     = suspended (fixed: re-inits on resume — clock re-set confirmed)
HSI_CTRL / RNGDMA reads = 0xFFFFFFFF  (hub not driving MISO)
accelerometer raw_data  = 0,0,0
gyro raw_data           = 0,0,0
```

`ssh nuxel` works from this Mac (alias added to ~/.ssh/config).
