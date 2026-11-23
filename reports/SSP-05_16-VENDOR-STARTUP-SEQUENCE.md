# SSP-05_16 — Vendor Startup Sequence

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Source authority

Recovered from the hash-bound stock lhd (`G975FXXS9DTK9`,
SHA-256 `6362e80d…`) via `tools/s10plus/ssp-runtime/inspect_lhd_init.py`, plus the GPL
kernel `bbd.c` / `bcm_gps_spi.c` / `bcm_gps_regs.c`. All steps below are CONFIRMED
(static) unless marked INFERRED.

## 1. lhd initializer state machine (VA 0x389fc, state table VA 0xdfc4)

States (log labels recovered from the binary's own adjacent log strings):

```
 1 FD_REQUEST_DOWNLOAD
 2 FD_WAIT4AUTOBAUD
 3 FD_SENT_AUTOBAUD
 4 waiting/default dispatch
 5 FD_GOT_SYNC
 6 FD_TIMEOUT_SYNC
 7 FD_GOT_SYNC_INIT
 8 FD_WAIT4VERSION_INIT
 9 FD_GOT_VERSION_INIT
10 FD_ROMRESET
11 FD_WAIT4DOWNLOAD_START
12 FD_WAIT4DOWNLOAD_COMPLETE
13 FD_WAIT4APP
14 FD_GOT_SYNC_CONFIRM
15 FD_WAIT4VERSION_CONFIRM
16 FD_GOT_VERSION_CONFIRM
17 DONE
```

- Initial version request: state 7/14 → 8/15, RPC id 0 (empty), reliable enqueue,
  250 ms retry timer, 5 retries.
- Version response: RPC id 3 (3 × LE32) advances 8→9 and 15→16.
- Patch download: F1 records → MemoryWrite RPC id 5 (each ack-forwarded), then
  StartScratch RPC id 46 (LE32 entry, delay 40 ms), ServiceStart RPC id 55
  (LE32 entry + 4 zero LE32, delay 100 ms).
- Final comparison: low24(ASIC)==0x4775b0 → patch ASIC must equal 0x4775b0 (else full
  equality); legacy exception only for original version 0x36a07 + ASIC 0x4774a0.

## 2. Transport framing (CONFIRMED)

- ESC `0xB0`, SOP `0x00`, EOP `0x01`; escaped ESC/XON/XOFF = `0x03/0x04/0x05`.
- Flags: ACK(1) RELIABLE(2) REL_ACK(4) REL_NACK(8) MSG_LOST(16) GARBAGE(32)
  SIZE_EXT(64) EXT(128) INTERNAL(256) IGN_SEQ(512).
- CRC-8 (GlUtlCrc table) over bytes 1..length-2, **nibble-swapped**.
- Reliable seq ACK/NACK; duplicate suppression default OFF at both constructor sites.

## 3. Kernel-side gating (CONFIRMED, the decisive ordering fact)

`bcm_rxtx_work_func` calls `bcm477x_hello()` FIRST, which requires the
MCU_REQ(gpio167)→MCU_RESP(gpio168) handshake before ANY SSI I/O. The vendor sequence
therefore is:

1. MCU rail `vdd_mcu_1p8` on.
2. MCU out of reset (probe).
3. MCU_REQ/MCU_RESP handshake succeeds.
4. THEN autobaud + GetVersion + patch download + app start.

The boot-ROM *GetVersion* is NOT reachable before step 3 in the live tree (the raw-SSI
`bcm477x_rpc_get_version` is dead code). INFERRED: this matches the physical reality
that the GNSS boot-ROM shares the same SSI slave select as the MCU and is only
addressable once the MCU is awake.

## 4. Timing (documented missing item)

The one externally-authored item not derivable from GPL/lhd is the Broadcom datasheet
value for `GPS_PWR_EN` rise → ROM autobaud-ready. All other ordering is recovered.
Readiness is best detected by the observable MCU_REQ→MCU_RESP handshake, not an
arbitrary sleep.
