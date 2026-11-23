# SSP-05_16 — Stage 06 Firmware-Download Handoff

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Purpose

Stage 06 is the *firmware download + sensor-hub application start* phase. It is NOT to
be executed by this mission. This handoff captures every confirmed prerequisite so that
Stage 06 starts from evidence, not guesses.

## 1. Confirmed controller identity

- `mcu_name = BCM47752KUB1G`, `mcu_rev = BR0121080900,BR010` (live sysfs).
- ASIC `0x4775b0` (firmware header + lhd comparison slot).

## 2. Confirmed firmware

| Field | Value |
|---|---|
| Blob SHA-256 | `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d` |
| BlobLength | 438895 |
| Record count | 479 (all `0xF1` = LE32 dest + data) |
| AsicVersion | `0x004775B0` |
| Entry | `0x00800161` |
| Source | kernel embedded `r_os/bbd_patch_file_beyond.h` (served read-only via `/dev/bbd_patch`) |

## 3. Confirmed transport

- `/dev/ttyBCM` (TL-framed reliable RPC; kernel wraps in SSI; gated by MCU handshake).
- `/dev/bbd_control` (ESW:READY / SSI:PassThru=1 / BBD:PassThru=0).
- `/dev/bbd_patch` (read-only firmware supply).

## 4. Confirmed initialization sequence (vendor-recovered)

1. `vdd_mcu_1p8` on (already enabled).
2. MCU out of reset (probe already done; `mcu_probe=1`).
3. MCU_REQ(gpio167)=1 → MCU_RESP(gpio168)=1 handshake (kernel `bcm477x_hello`).
4. Autobaud (32 × `0x80`, then 36 × `0x80` fallback).
5. GetVersion request RPC id 0 → response RPC id 3 (w0 == ASIC 0x4775b0).
6. Patch download: 479 × MemoryWrite RPC id 5, each reliable-ACKed.
7. StartScratch RPC id 46 (LE32 entry) +40 ms; ServiceStart RPC id 55 (LE32 entry + 4 zero LE32) +100 ms.
8. Post-download GetVersion (id 0 → id 3) confirming w0 == 0x4775b0.

## 5. Response handling (verified)

- TL: ESC/SOP/EOP, CRC-8 nibble-swap over bytes 1..len-2, reliable ACK/NACK, duplicate
  suppression OFF by default.
- Version response = RPC id 3, 3 × LE32 (w0 = version/ASIC word).

## 6. Download failure modes

- NACK → reject (do not retry blindly; preserve evidence).
- Reliable-ACK timeout (2.5 s) → inhibit app start; restore BBD:PassThru=0.
- CRC/malformed → log, resync, no-verdict.
- Partial transfer → never exit success; never emit ESW:READY.

## 7. Application-start prerequisites

All 479 MemoryWrites ACKed before StartScratch/ServiceStart. Post-download GetVersion
must validate before ESW:READY is emitted.

## 8. Rollback / recovery

- Recovery bound: MCU_REQ=0, GPS_PWR_EN=0, `BBD:PassThru=0` in `finally`; kernel
  `bbd_mcu_reset` available. Five known-good BOOT images retained; DTB/DTBO/recovery
  untouched. No BOOT flash planned for Stage 06.

## 9. Authorization boundaries (NOT to be exceeded without explicit grant)

- No GPS_PWR_EN assertion, no MemoryWrite, no MCU app-start without owner RF + timing +
  bounded-trial grant.
- No BOOT/DTB/DTBO/recovery write.
- No ESW:READY unless post-download GetVersion validates.
