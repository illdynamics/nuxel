# SSP-05_12 — Firmware Downloader Offline Readiness

**Date:** 2026-11-23
**Status:** `DOWNLOADER_OFFLINE_PASS`

Offline review of `tools/s10plus/ssp-native/nuxel_bbd_flash.c` (hash
`5fae2216...`) confirms:

- `--rom-probe` opens `/dev/ttyBCM` only; returns `EXIT_ROM_IDENTIFIED` before
  any MemoryWrite (RPC 5) / StartScratchApp (RPC 46) / ServiceStart (RPC 55).
- `--flash` and `--rom-probe` are mutually exclusive (`EXIT_USAGE`).
- Firmware identity check enforces `AsicVersion=0x004775b0`,
  `BlobLength=438895`, `entry=0x00800161` from `/dev/bbd_patch` (897113 B).
- F1 record framing, CRC-8 TL state machine, per-write reliable ACK, and
  strict success (exit 0 only after all writes ACKed + post-download
  GetVersion) are present.
- Offline read-only verification (`no args`) exits `0
  (GENUINE_VERIFIED_SUCCESS)` with no device I/O — confirmed live this session.

No actual firmware download was performed (stage boundary respected).
