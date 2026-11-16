# Nuxel S10+ GNSS — Remaining Blockers

This document lists only **genuine** blockers. Everything else (firmware
provenance, transport, power, TL framing, daemon, Maps integration) is
implemented and verified. No coordinates are fabricated; a physical GNSS fix has
**not** been obtained because the position decoder is unavailable, and that is
stated plainly.

## Blocker B0 — Sensor hub / receiver never answers (measured 2026-11-12)

**Status:** `BLOCKED — receiver silent; sensor hub never initialises`

Measured on the live handset with the native daemon and with direct node
access, *after* the transport was opened and the GPS rail enabled:

| Probe | Result |
|---|---|
| `/dev/ttyBCM` open + 3 s receive window, **no TX at all** | `rx_bytes = 0` |
| Kernel SPI counters for that open (`SSPBBD DBG SPI @ TX/RX`) | all zero |
| BBD TL frames written by the daemon | written, `rx_packets = 0` |
| `/sys/devices/virtual/sensors/ssp_sensor/mcu_test` | `NG,NG,NG` |
| `enable_irq` write `1` (→ `reset_mcu()`) | journal: `lhd is NULL or resetting`, stays `0` |
| `/dev/bbd_sensor` opened (LHD registration) + `ESW:READY` | still `NG,NG,NG`; chip-ID retries time out |
| Kernel log | `get_chipid - get chip ID retry`, `fail to initialize mcu`, `ssp_down == true` |

Consequences, stated plainly:

* The BCM4773 does not respond even to the kernel's own hello/chip-ID exchange,
  so nothing above the transport (patch download, GNSS core start, position
  solution) can be reached. The previous `POSITION_DECODER_UNAVAILABLE` framing
  was incomplete: there is **no receiver traffic to decode** in the first place.
* In stock firmware the sensor hub is brought up by `ssp_sensorhub.so` (the
  sensor HAL) before the GNSS HAL (`SensorHubWaitForMCUInit` polls `mcu_test`
  until it contains `,OK`), and the vendor `lhd` performs the per-OS sensor-hub
  patch download through the BBD RPC engine. Nuxel has neither binary, and the
  kernel's own reset path is disabled by its LHD-killer handshake (it expects a
  registered LHD process on `/dev/bbd_sensor` to be signalled, not to reset the
  MCU itself).
* `/dev/bbd_control` is the LHD→kernel channel; reads on it return nothing
  useful, so control strings alone cannot bring the hub up.

### What a position would still require

Even if a chip response appeared, producing a fix needs (a) the patch-download
RPC, (b) GNSS core start + NMEA/position RPC ids and layouts, and (c) a
continuous solution stream. None of these are in the GPL kernel. See B1.

### Candidate paths (not yet done, would need a decision)

1. **Owner-supplied vendor runtime (B1 option B)** — run the device owner's own
   `ssp_sensorhub.so` + `lhd`/`gpsd` in an isolated Android-compat runtime so the
   hub is initialised exactly as in stock, then consume its position output.
2. **Kernel-side sensor-hub bring-up** — a kernel change that performs the patch
   download RPC itself (or permits reset without a registered LHD). This needs a
   BOOT image reflash and the proprietary RPC map for the patch message.

Neither has been attempted here: both are larger, riskier changes than a
userspace deploy, and fabricating an RPC map or a coordinate is not acceptable.

---

## Blocker B1 — Missing proprietary GNSS application RPC map (position decode)

**Status:** `BLOCKED — proprietary userspace`

The Broadcom BBD **transport** is GPL and fully implemented (framing, CRC, RPC
header, sensor-vs-GNSS routing are all in `drivers/sensorhub/brcm/bbdpl/`). The
BBD **application** RPCs — the exact `RpcId` values and payload layouts for:
1. sensor-hub patch download,
2. GNSS core on/off / acquisition control,
3. the position-solution message (lat/lon/accuracy/timestamp/satellites),

live in Samsung's proprietary `lhd`, `gpsd`, and `libwrappergps`, which are not
open-sourced, not present on Nuxel, and not present in this repository. The GPL
kernel only routes "sensor" vs "non-sensor" RPCs; it does not decode GNSS
position, so these IDs cannot be recovered from it without reverse engineering.

### Required artifact (exact)

The owner-provided stock `SM-G975F`/`beyond2lte` GNSS userspace:

| Path (stock vendor/system) | Role |
|---|---|
| `vendor/bin/hw/lhd` | BBD/LHD bridge (loads patch, RPC to chip) |
| `vendor/bin/hw/gpsd` | Samsung GPS daemon (RPC → position) |
| `vendor/lib64/libwrappergps.so` | GPS wrapper (RPC encoding) |
| `vendor/lib64/vendor.samsung.hardware.gnss@2.0.so` | GNSS vendor lib |
| `vendor/etc/sensor/lhd.conf` | LHD transport/patch config |
| `vendor/etc/gnss/gps.xml`, `gps.cer` | GNSS policy/assistance config |
| `vendor/etc/init/*gps*.rc`, `*gnss*service.rc` | init/service rules |
| `system/bin/linker64` + Bionic/VNDK deps | Android runtime (for the Bionic ELFs) |

### Exact extraction steps (owner's own stock firmware — never a substitute)

1. Obtain the stock firmware for the exact device: Odin/`fus` package for
   `SM-G975F`, a `G975FXX...` build (do NOT use `SM-G975N` or another Exynos
   device).
2. Unpack/decrypt Samsung archives, then extract the `vendor` and `system`
   images **read-only** (the repo ships
   `gps/scripts/extract-s10plus-gnss.sh` for the file inventory; it does not
   unpack Samsung archives itself).
3. Run:
   ```bash
   ./gps/scripts/extract-s10plus-gnss.sh /path/to/unpacked-stock-rootfs ./gps/out
   ./gps/scripts/verify-extracted.sh ./gps/out
   ```
4. Audit every ELF (`readelf -h -l -d`): record AArch64 class, `PT_INTERP`
   (expect `/system/bin/linker64`), `DT_NEEDED`, SONAME. Samsung GNSS binaries
   are Android/Bionic + HIDL/Binder and will **not** run natively on Fedora.
5. Record file SHA-256 + source build fingerprint; populate
   `verified-firmware.json`-style provenance for the runtime (analogous to what
   was already done for the patch firmware).

### Two lawful ways forward (either, not both, and never fabricated)

- **A (preferred): lawful port of the GNSS RPC map.** If the owner has rights
  to the proprietary `lhd`/`gpsd` (they own the device and its stock image),
  the RPC map can be extracted/referenced to complete the native daemon's
  `POSITION_DECODER_UNAVAILABLE` boundary. The native BBD TL is already done;
  only the application RPC ids/layout need mapping.
- **B: isolated Android-compat runtime.** Run the owner's `lhd`/`gpsd` inside a
  throwaway, isolated Bionic/HIDL/Binder chroot/container (not the default
  Nuxel path), expose its fix to the bridge as `source=gnss`.

### What is NOT a valid fix

Mock/network/IP/Wi-Fi/GeoClue coordinates, SPI "bytes", a bound driver, or a
daemon process. These remain separate `network_*` sources and are never
relabelled GNSS.

---

## Blocker B2 — Outdoor physical test

**Status:** blocked by B1 (no decoded position to test yet).

Once B1 is resolved, run `docs/hardware/gps/post-flash-gnss-verify.sh` and the
outdoor acceptance matrix in `GPS-TEST-REPORT.md`. Requires a clear-sky
outdoor session; cached/network coordinates must be excluded; exact coordinates
stay out of committed logs.

---

## Non-blockers (already resolved)

- ~~Firmware missing~~ → firmware is kernel-embedded and hash-verified.
- ~~Kernel reflash needed~~ → not needed; driver/firmware already in running kernel.
- ~~Maps location integration broken~~ → Maps + geolocation shim are source-aware
  and honest; 48 Maps/location tests pass.
