# SSP-05_16 — BBD Transport Ownership Map

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Node inventory (live-confirmed)

| Node | Major | Minor | Own/perms | Role | Kernel source |
|---|---|---|---|---|---|
| `/dev/ttyBCM` | 10 | 91 | root:audio 0660 | raw SSI/HSI serial-over-SPI stream; user bytes are TL-framed by userspace, then wrapped in SSI by `bcm_ssi_tx` | `bcm_gps_spi.c` (misc "ttyBCM") |
| `/dev/bbd_sensor` | 236 | 1 | root 0600 | sensor packet Rx to gpsd/lhd | `bbd.c` `bbd_on_read(BBD_MINOR_SENSOR)` |
| `/dev/bbd_control` | 236 | 2 | root 0600 | control strings from lhd (ESW:READY, BBD:PassThru, SSI:PassThru, GPSD:*, SSP:*) | `bbd.c bbd_control()` |
| `/dev/bbd_patch` | 236 | 3 | root 0600 | serves embedded firmware patch (C array) read-only | `bbd.c bbd_patch_read()` |
| `/dev/bbd_urgent_patch` | 236 | 4 | root 0600 | serves `/spu/sensorhub/urgent.patch` (signature-verified) | `bbd.c bbd_urgent_patch_read()` |

## 1. `/dev/ttyBCM` — the SSI/HSI transport (TX/RX path)

`bcm_spi_write()` (`.write=0x458`) enqueues user bytes into `priv->write_buf` circ
buffer and schedules `bcm_rxtx_work_func`.

`bcm_rxtx_work_func()`:
1. `bcm477x_hello()` — asserts MCU_REQ (gpio167), waits MCU_RESP (gpio168) up to 100 ms.
   **If no MCU_RESP, calls `bbd_mcu_reset(true)` and returns WITHOUT any SSI I/O.**
2. Rx: if `host_req` (gpio15) high, `bcm_ssi_rx()` → `bbd_parse_asic_data()`.
3. Tx: copies write_buf → `bcm_ssi_tx()` (wraps user bytes with SSI command/len).
4. `bcm477x_bye()` — deasserts MCU_REQ.

**Consequence:** no `/dev/ttyBCM` write can reach the chip until the MCU handshake
succeeds. The hub is currently `shutdown=1 resetting=1` (no firmware), so MCU_RESP
never stabilises HIGH during `hello`, and all SSI I/O is gated off. This is the root
cause of "receiver silent" (GPS-BLOCKERS.md B0), reproduced and explained here.

## 2. Control-string dispatch (`/dev/bbd_control`)

`bbd_control()` (strstr prefix match, order matters):

| String | Effect |
|---|---|
| `ESW:READY` | `on_mcu_ready(true)`, release patch wake-lock |
| `ESW:NOTREADY` | `on_mcu_ready(false)`, clear sensor circ buffer |
| `ESW:CRASHED` | clear sensor circ buffer, `on_mcu_ready(false)`, `on_control` |
| `SSI:PassThru=1` | acquire patch wake-lock (firmware download armed) |
| `BBD:PassThru=0` | (passthru off) |
| `BBD:DEBUG=0/1`, `SSI:DEBUG=*`, `PZC:DEBUG=*` | debug toggles |
| `SSP:GET_HW_REV` / `SSP:GET_AP_REV` | call `on_control` to fetch hw/ap rev (used by patch read) |

## 3. Ownership arbitration

- `/dev/ttyBCM` is a single stream: exactly one owner may drive the SSI link. The
  `nuxel-ssp-bridge.service` is **masked** on-device, so nothing else holds it during a
  bounded native session. Opening the node arms the IRQ; a second concurrent owner would
  interleave `.write()` bytes into the shared circ buffer and corrupt TL framing.
- `/dev/bbd_sensor`, `/dev/bbd_control`, `/dev/bbd_patch` are separate minor devices
  with independent circ buffers; there is no silent cross-consume beyond the kernel's
  routing (sensor Rx → `bbd_sensor`, reset requests → `bbd_control`).

**Recommendation (prepared, reversible, userspace-only):** the native session harness
must take an exclusive advisory lock over `/dev/ttyBCM` (flock) and refuse to start if
already held, and always restore MCU_REQ=0 / GPS_PWR_EN=0 in `finally`. The current
`nuxel_lhd.py` already restores the rail in `finally`; the flock is a small additive
guard to be folded into the Stage 06 downloader, not required for Stage 05 completion.

## 4. Patch Routing

`/dev/bbd_patch` serves the embedded `bbd_patch` array (see
`SSP-05_16-STOCK-FIRMWARE-DISCOVERY.md`). It is read-only; writing has no effect. The
firmware is *downloaded* by userspace reading this array, decoding the F1-record
stream, and issuing MemoryWrite (RPC id 5) records over `/dev/ttyBCM` — not by writing
to `/dev/bbd_patch`.
