# SSP-05_15 — ROM First-Light Status

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## Status: `ROM_GETVERSION = NOT_RUN`

No physical GPS_PWR_EN assertion and no ROM GetVersion probe were executed this
mission, consistent with `PHYSICAL_TRIAL_SAFE = FALSE`
(SSP-05_15-PHYSICAL-TRIAL-DECISION.md).

## What is established (read-only / offline)

- GPS_PWR_EN is gpg0-2 = gpio145, currently LOW (evidence in
  SSP-05_15-POWER-SEQUENCE.md).
- `nuxel-gnss-lhd.service` already demonstrated a successful bounded
  `GPS_PWR_EN` assertion + transport open at boot (journal:
  `power={'success': True, 'enabled': True}`), but its handshake polls SSP state
  (`gps: False`) and does not emit a GetVersion RPC.
- The ROM GetVersion probe is implemented in `nuxel_bbd_flash.c --rom-probe`
  (autobaud + TL-framed RPC id 0), offline-tested (framing/CRC/RX/negative all
  PASS), but its RPC id attribution to "GetVersion=0" is sourced from a
  proprietary lhd absent from this repo (SSP-05_15-ROM-ENDPOINT.md).
- `bcm477x_rpc_get_version()` in the kernel is orphaned dead code (no callers);
  the live vendor ROM GetVersion is performed by proprietary `lhd` over BBD RPC.

## Why not yet attempted

The trial requires the owner-confirmed RF-safety + vendor timing/artifact, per
Section 6/7. Neither has been provided, so a physical transition would be
speculative and unauthorized.

## Next action to reach ROM first light

1. Owner authorizes bounded GNSS-domain (RF) energisation.
2. Owner provides the BCM47752 post-power timing OR the stock `lhd` binary
   (for RPC-map + timing reference).
3. Agent closes the harness gap: a single bounded session that asserts
   GPS_PWR_EN, waits the verified settle, runs the corrected GetVersion frame,
   captures raw RX, and restores the rail.
4. Run the bounded probe; validate framing/CRC/identity; confirm post-trial
   device health.

No firmware MemoryWrite, no app-start, no repeated GPIO/regulator cycling will
be performed without separate authorization.
