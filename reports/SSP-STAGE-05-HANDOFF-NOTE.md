# SSP Stage-05 Handoff Note (from 04_5 final remediation)

**Decision:** `READY_FOR_STAGE_05_SOFTWARE_ONLY`
**Date:** 2026-11-22

## Exact next action

Stage 05 begins as a **software-only, separately reviewed, bounded MCU first-light trial** through the existing userspace transport — **no BOOT flash, no partition write, no power-rail/reset experiment**.

Transport (already present and verified in the running kernel):
- `/dev/ttyBCM` (10,91)
- `/dev/bbd_sensor` (236,1), `/dev/bbd_control` (236,2), `/dev/bbd_patch` (236,3)
- `nuxel_bringup` write-only sysfs node at `/sys/class/sensors/ssp_sensor/nuxel_bringup`

Tools (present, offline-verified): `nuxel_bbd_flash` (--flash), `nuxel_bbd_download`, `nuxel_bbd_host`.

Bounded trial constraints (must be in explicit owner authorization):
- One MCU init attempt per trial; no auto-reset storms; no regulator_force_disable loops; no shared-rail changes.
- Instrument SPI mode/CS/CS-duration, host↔MCU request/response, IRQ counters, runtime-PM state, regulator consumers.
- Reconcile vendor 32-vs-36-byte autobaud. Distinguish transport ACK from MemoryWrite/operation acceptance.
- Target a validated ROM GetVersion response (frame+CRC+payload+ASIC), not `0xffffffff`/`mcu_resp` GPIO.
- On malformed frame/NACK/CRC/version mismatch/timeout: stop. Leave Nuxel bootable and `SSP_NOT_READY`.

## Only if software path is exhausted AND a kernel change is genuinely justified

Then (and only then) reopen the flash gates:
1. Fresh clean pinned kernel clone at full commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0` on a case-sensitive volume.
2. `NUXEL_SSP_STRICT=1` full build; exact per-file patch receipts (all four SHA-256 already in manifest).
3. `pack-ssp-boot.py` against fresh-verified BOOT donor `0e6aa34c...` (only kernel_size changes).
4. Independent `verify-boot-image.py` with separate-DTB/DTBO + merged-FDT evidence.
5. Establish second TWRP-accessible rollback copy BEFORE any write (host seed already verified at `/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img`).

## Hard guardrails carry forward (unchanged)

- At most TWO distinct BOOT candidate flashes per Stage-05 session; new owner approval beyond.
- If candidate unexpectedly returns to TWRP/hangs → candidate FAILED, restore known-good BOOT via verified path.
- Never touch dtb/dtbo/recovery/bootloader/modem; external DTB (`sda12`) and DTBO (`sda13`) hashes must match baseline before/after every candidate.
- This donor's BOOT has NO appended DTB; any BOOT with appended FDT/changed ramdisk is forbidden.

**No candidate was flashed and none needs to be flashed to proceed with the software-only first-light trial.**
