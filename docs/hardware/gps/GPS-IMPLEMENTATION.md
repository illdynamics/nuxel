# Nuxel S10+ GNSS — Implementation & Architecture

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte` / Exynos 9820
**GNSS:** Broadcom BCM4773 (MCU `BCM47752KUB1G`, GNSS `AsicVersion=0x004775B0`) over SPI (`spi17.0`, `brcm gps spi`), Broadcom BBD/LHD RPC transport `/dev/ttyBCM`.
**Status:** `PARTIAL — hardware path implemented and live-verified; GNSS position decode blocked on proprietary Samsung lhd/gpsd userspace`

---

## 1. Executive summary of findings

This implementation run corrected the central assumption in the handoff. The
handoff stated `BLOCKED_FIRMWARE` (missing Broadcom sensor-hub patch). That is
**not true**. The patch firmware is **compiled into and served by the running
kernel**; the actual missing component is the proprietary **userspace**
(`lhd`/`gpsd`/`libwrappergps`) that encodes the GNSS application RPC map.

### 1.1 Hardware-proven facts (captured from the live device)

| Fact | Evidence |
|---|---|
| SPI binding | `/sys/bus/spi/drivers/brcm gps spi/spi17.0` → `ssp,BCM4773` DT node |
| Kernel config | `CONFIG_BCM_GPS_SPI_DRIVER=y`, `CONFIG_SENSORS_SSP_BBD=y`, `CONFIG_SENSORS_SSP_BEYOND=y` (built-in) |
| MCU identity | `/sys/devices/virtual/sensors/ssp_sensor/mcu_name` = `BCM47752KUB1G` |
| FW identity | `/dev/bbd_patch` serves `AsicVersion=0x004775B0`, `Name=bcm_sensorhub_a1`, `BlobLength=438895` |
| FW SHA-256 (file) | `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72` |
| FW SHA-256 (blob) | `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d` |
| HW revision | DT `ssp-ap-type=2` (beyond2lte), `ssp-ap-rev=1` → selects `bbd_old` patch variant |
| GPS power | `GPS_PWR_EN` GPIO exported at `/sys/devices/virtual/sec/gps/GPS_PWR_EN/value` (active-high, 0=off) |
| Live power test | 0→1 on lease acquire, 0 restored on cleanup (no unsafe state) |
| Vendor runtime | absent (`/vendor`, `/system`, `lhd`, `gpsd`, `linker64` all missing) |
| Source tree | `/root/kbuild/` = full GPL 4.14.253 kernel incl. `drivers/sensorhub/brcm/bbdpl/` |

### 1.2 The one real blocker

The Broadcom BBD **transport layer** (framing, CRC, RPC routing) is GPL and
fully specified in `drivers/sensorhub/brcm/bbdpl/bbd_rpc_lh.c`. The GNSS
**application layer** — the specific RPC IDs for patch download, GNSS
start/stop, and the position-solution message with its payload layout — live in
the proprietary Samsung `lhd`/`gpsd`/`libwrappergps`, which is **not
open-sourced, not on the device, and not in this repository**. The GPL kernel
only routes "sensor" vs "non-sensor" RPCs; it does **not** decode the GNSS
position message, so those IDs cannot be obtained from it without reverse
engineering (out of scope and not fabricated here).

---

## 2. State machine

```
ABSENT ──nodes present──▶ FIRMWARE_READY ──/dev/bbd_patch read──▶ TRANSPORT_READY
   ▲                                                                    │
   │ cleanup                                                           │ SSI:PassThru=1 + patch stream + ESW:READY
   │                                                                    ▼
   └────────────────────────────────────────────────────────── PATCH_LOADED
                                                                   │
                                                          GPSD:CORE_ON (proprietary)
                                                                   │
                                                                   ▼
                                                    BBD_HANDSHAKE_OK (GPS: true)
                                                                   │
                                                       (proprietary RPC map)
                                                                   │
                                                                   ▼
                                                    SOLUTION_STREAMING → FIX_VALID
```

Each state is gated by **evidence**, never by file presence:
- `FIX_VALID` requires a parsed receiver-originated coordinate with a valid
  provider timestamp and accuracy — currently unreachable without the
  proprietary RPC map, so the daemon reports
  `POSITION_DECODER_UNAVAILABLE` honestly.

---

## 3. Data flow (proven from kernel source)

### 3.1 RX (chip → daemon)
`bcm_ssi_rx()` → `bbd_parse_asic_data()` **strips the BBD TL framing** and,
for non-sensor (GNSS) RPCs, calls `bcm_on_packet_received()` → `/dev/ttyBCM`
read buffer. The daemon reads the **de-framed RPC record stream** and parses
the 7/8-bit `{RpcId, RpcLen, data}` header.

### 3.2 TX (daemon → chip)
The daemon writes raw bytes to `/dev/ttyBCM`; `bcm_spi_write()` forwards them
**raw** to the chip (the kernel does NOT frame TX). The daemon must build the
BBD TL frame itself (ESCAPE`B0` SOP`00` ... ESCAPE`B0` EOP`01` + CRC-8 with
nibble-swap). This is exactly the code in `bbd_rpc_lh.c` whose TX half was
commented out in-kernel because it moved to userspace `lhd`.

### 3.3 Control
Control strings are written NUL-terminated to `/dev/bbd_control` → `bbd_control()`
dispatches them (`SSI:PassThru=1/0`, `ESW:READY`, `GPSD:CORE_ON/OFF`, etc.).

### 3.4 Firmware
`lhd` reads the embedded patch from `/dev/bbd_patch` (read-only) and downloads
it to the chip through a BBD RPC during the `SSI:PassThru=1` state.

---

## 4. Implemented components

| File | Role | Status |
|---|---|---|
| `services/nuxel-gnss/src/nuxel_bbd_tl.py` | BBD TL framing, CRC-8, RPC framing/parse (GPL port) | implemented + 8 unit tests |
| `services/nuxel-gnss/src/nuxel_control.py` | control strings, power/patch constants, patch parser | implemented + 5 unit tests |
| `services/nuxel-gnss/src/nuxel_lhd.py` | native daemon: power lease, FW provenance, transport, control, bounded handshake, cleanup | implemented + live-verified |
| `services/nuxel-gnss/tests/test_nuxel_bbd_tl.py` | framing/CRC/RPC unit tests (incl. kernel `sample1` vector) | 8 passed |
| `services/nuxel-gnss/tests/test_nuxel_control_firmware.py` | firmware parser + identity tests | 5 passed |
| `docs/hardware/gps/evidence/verified-firmware.json` | firmware provenance + hashes | written |
| `docs/hardware/gps/evidence/bcm_sensorhub_a1.hex.txt` | owner firmware artifact (provenance only) | captured |

---

## 5. Architecture decision

**Chosen: Native Nuxel daemon (handoff option A), up to the proven communication
boundary.** The firmware loader, power sequencing, transport and BBD TL are all
implemented natively and verified. The final position decode is **deferred** to
one of two explicitly-documented, lawful follow-ups (see Blockers), because the
GNSS application RPC map is proprietary and must not be guessed.

**Rejected:**
- *Isolated Android runtime (option B)* — cannot run `lhd`/`gpsd` without the
  owner's own vendor binaries + a Binder/HIDL/Bionic shim; deferred, not the
  default.
- *Fabricating a position decoder* — rejected outright (violates the no-fabrication rule).

---

## 6. Safety & lifecycle guarantees

- One process owns `/dev/ttyBCM` (kernel `-EBUSY` enforces single owner).
- Power is leased with a refcount and readback-verified; the rail is always
  restored to its initial state on cleanup (`finally`).
- Control off (`GPSD:CORE_OFF`) is issued before fd close.
- All hardware tests are bounded by deadlines; no unbounded waits.
- No `chmod 666`, no SELinux weakening, no partition writes, no reboot.

---

## 7. No-flash determination (kernel reflash NOT required)

- The SPI driver, BBD nodes, and firmware are **already present** in the
  running kernel (`CONFIG_*` built-in). **No kernel or device-tree reflash is
  required.**
- Firmware is served by the existing kernel; nothing needs to be placed in
  `/system`/`/vendor` for the firmware itself.
- The only reflash-relevant item is the *optional* vendor `lhd`/`gpsd` runtime
  (owner-supplied, Android/Bionic), which — if pursued — would go on the system
  image, not boot/kernel. See the reflash manifest.
