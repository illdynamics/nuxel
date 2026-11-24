# Stage 06 — Round 34 Final Engineering Review (LTE BRING-UP CAMPAIGN)

**Branch:** cs/mob @ eccfe93f
**Date:** 2026-11-24 CET
**Device:** SM-G975F / beyond2lte / Exynos9820 / Shannon S5000AP

## Verdict: STAGE_06 LTE = NOT PASSED (hardware acceptance matrix not met)

This is an honest engineering review. Two real defects were fixed, the complete
matching vendor firmware was recovered, and the root cause was locked to a
single, specific, external dependency. LTE internet is NOT yet established, and
I will not claim 100%.

## What was delivered (real, committed)

1. Recovered the complete matching vendor firmware into `./packs` (SAMFW
   G975FXXS9DTK9) and extracted the definitive reference artifacts:
   `cbd`, `secril_config_svc`, `libsec-ril.so` (BuildID 60889dd7),
   `init.baseband.rc` + `init.*.rc`, `plmn_se13.bin`, and the ARM32 S5000AP
   CP MAIN image with the full PDNMGR/PMPM symbol table.
2. Fixed defect A — FSM stall: `DS_SET_LTE_ATTACH -> DS_MBIM_ATTACH_CONFIG`
   stalled forever when MBIM was disabled; data-session never reached
   DATA_CALL. Added an explicit MBIM-disabled skip to ALWAYS_ON_PDN.
3. Fixed defect B — byte-inexact flag: `SetLteAttachProfile` payload[0] was a
   raw flag pass-through. Fresh disasm of IpcTxSetLteAttachProfile @0x320238
   proves `payload[0] = (flag & 1) ? 3 : 4` (never 1). Corrected + unit-locked.
4. Full host suite PASS (build + 9 suites + 3000-it fuzzer + ASan/UBSan).

## Live results (deployed SHA 1e2df783…, ATTACH_FLAG=3, MBIM OFF)

- FSM runs clean: NET_REGIST_CHECK -> … -> SET_LTE_ATTACH -> (MBIM skip) ->
  ALWAYS_ON_PDN -> PS_ATTACH -> PS_REGIST_VERIFY(REGISTERED_HOME) -> DATA_CALL.
- DATA_CALL: `SetPdpContext` ACK gen_result=0, but GPRS_CALL_STATUS state=3
  (NOT connected), no GPRS_IP_CONFIGURATION, rmnet0..7 DOWN.
- PS detach (sub=3) reason 0 and 4 both rejected (gen_result=1) while registered.

## Root cause (evidence-locked, 33+ rounds + this round's firmware recovery)

The default EPS bearer is established during LTE INITIAL ATTACH using the
PERSISTENT initial-attach APN. That APN is EMPTY in both AP `nv_data.bin`
(/dev/sda3, 1 MiB, mtime 2024-02-03) and CP `.nv_core.bak` (/dev/sdd1).
`SetLteAttachProfile` (sub=20) is RAM-only — the CP string
`"PS Reset, Clear LTE Attach APN Info"` and the unchanged NV mtime confirm it
does not persist. The Samsung stock path persists the APN via cbd's QBR NV
item-ID table (`PDNMGR_FlashItems.h`), which is NOT recoverable (only item
NAMES are embedded in the CP image, not numeric IDs/offsets/CRC/signing).

## Remaining blocker (single, specific)

Persistent initial-attach APN NV provisioning requires the Samsung QBR NV
item-ID table (`PDNMGR_FlashItems.h`: SAECOMM_FLASH_LTE_INTERNET_ATTACH_ENABLED
and the APN item) + on-disk encoding + CRC/signing. Not present in the repo,
`nv_data.bin`, `.nv_core.bak`, `libsec-ril.so`, `cbd`, or the CP image. A blind
NV item-ID write risks corrupting the QBR-signed container and is refused by
the fail-closed policy (correctly).

## Regression (all PASS)

Wi-Fi wlan0 10.20.30.16 UP; ZeroTier 10.11.12.99 UP; USB usb0 10.100.10.1 UP;
SSH alive; modem_state ONLINE; nuxel-radiod active. No NV/EFS/RADIO/BOOT/DTB/
DTBO/IMEI/calibration write performed.

## Completion

LTE internet: NOT COMPLETE (blocked on the unrecoverable Samsung QBR NV
item-ID table). All Nuxel-side software that can be recovered/implemented
without that external asset is done and committed at `eccfe93f`.
