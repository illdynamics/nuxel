# Stage 06 — Round 28: ACTION — implementation + live KPN results (conclusive root cause)

**Date:** 2026-11-24 CET
**Branch:** cs/mob @ f2ecd111
**Device:** SM-G975F beyond2lte, KPN working SIM (PLMN 20408)
**State:** CP ONLINE, SIM READY, PS REGISTERED_HOME, all umts_* nodes present,
          CP RSSI link active (DISP_RSSI_INFO flowing), rmnet0..7 DOWN, no cellular IP.

## Summary of ACTIONS this round (implement → build → test → deploy → execute)

1. Re-derived the full IpcProtocol41 data-path from the EXACT vendor
   `.vendor-ro/libsec-ril.so` (build 60889dd7) with aarch64-linux-gnu-objdump.
2. Implemented a real correctness fix in the production FMT serializer,
   built host unit tests (all PASS), cross-built aarch64, deployed guarded
   (running binary preserved), restarted radiod, and live-tested on KPN.
3. Ran a controlled single-variable live matrix on the working KPN SIM.

## IMPLEMENTATION 1 — SetPdpContext ACTIVATE-bit + DataAuth semantics (shipped)

`IpcTxSetPdpContext @0x31f6e0` (disassembled this round):
- `DataCallSetup::ToDataAuth @0x29f970` definitively decodes the DataAuth enum:
  NONE=0, PAP=1, CHAP=2, PAP_CHAP=3.
- The ACTIVATE bit (flags bit4=0x10) is OR'd in ONLY when the DataAuth int is
  NON-ZERO (`cbz w20, ...`; `orr w8,w22,#0x10`). For a no-auth APN the vendor
  emits flags=0x01 (APN present, NO activate) and payload[102]=0x00, relying on
  LTE initial attach.
- Nuxel previously hardcoded flags=0x11 and mapped none->auth_code=1 (PAP).

Fix (commit f2ecd111): SetPdpContext now converts the region auth code (1=NONE)
to the DataAuth enum (0=NONE) and sets the ACTIVATE bit only for auth!=0; the
auth flag byte at payload[102] is now 0x00 for NONE. SetDataProfile/
SetLteAttachProfile keep the region-code convention (NONE=1) because the live
modem GEN-rejects SetDataProfile payload[0]=0 (gen_result=1) and accepts 1.

Host unit tests: 6 suites RESULT=PASS + FSM PASS + FUZZ_RESULT=PASS.
Deployed binary SHA256 dbdefd52af3ca8f635bf46ac524266bb7611a172a95967e501ae92d2ac45d6a0.

## LIVE RESULTS (working KPN SIM) — conclusive negative on FMT surface

Every variable now produces the IDENTICAL modem reply:
`GPRS_CALL_STATUS 010300000000000000` = cid=1, call_state=3, pdp_state=0, NO cause.

| Candidate | Value | Result |
|---|---|---|
| SetPdpContext ACTIVATE | flags 0x01 (no-activate) | call_state=3 |
| SetPdpContext ACTIVATE | flags 0x11 (activate, PAP) | call_state=3 |
| attach CID | 1 (single-sim) | call_state=3 |
| attach CID | 5 (DSDS/dual) | call_state=3 |
| pdp_type wire | 1 (full APN) | call_state=3 |
| pdp_type wire | 4 (EUTRAN) | call_state=3 |
| auth | NONE / PAP / CHAP | call_state=3 |

The sequence ACKs byte-exact every command (GEN 0x8003/0x80 generic-OK) and PS
registration is genuinely REGISTERED_HOME, yet the CP replies "not connected"
immediately with no ESM cause. No GPRS_IP_CONFIGURATION, no rmnet UP, no IP.

## Authoritative re-verification (this round, fresh disasm)

- `IpcRxGprsCallStatus @0x321ab0`: payload[1] state {1->4, 10->5, 11->6} =
  connected; ANY other value (incl. 3) -> 0 = NOT connected. There is NO
  intermediate "connecting" state; state=3 is a final NOT-connected. (The
  Round-28 mission hypothesis that state 3 is transient is conclusively refuted.)
- The data-call FMT path is byte-exact correct vs libsec-ril.so. There is NO
  missing IpcProtocol41 GPRS wire command in the default-bearer path.

## ROOT CAUSE (definitive, newly recovered)

The modem's PERSISTENT initial-attach APN is not set, because on stock Android
it is provided by a DIFFERENT subsystem that Nuxel does not run:

1. `cbd` (Samsung Control Boot Daemon) is NOT present/running on Nuxel. On stock
   it loads AP EFS `nv_data.bin` (partition /dev/sda3, filesystem "efs") into the
   CP over the RFS channel (/dev/umts_rfs0). The AP EFS contains carrier APN NV
   (the PDNMGR/PMPM tables) but NO "internet" APN string is present in the
   current nv_data.bin (verified by full scan).
   References in libsec-ril.so: cbd handles NV/RFS via /dev/umts_rfs0.
2. The real vendor data/attach path is MBIM, not IpcProtocol41 GPRS:
   `LteEpdgDataCallManager::DoSetInitialAttachApn @0x28c6c8` ->
   `MbimManager::DoSetMsLteAttachConfig @0x281358` ->
   `MbimAdaptor::MakeSetMsLteAttachConfig @0x1c3018` (MBIM MS LTE Attach Config
   with ipType/apn/user/roaming/source/compression/authProtocol).
   `SupportMBIM()` is true on this modem; MBIM is carried over SIPC, and there is
   no standalone MBIM netdev on Nuxel (only rmnet0..7 + usb0).
3. The vendor log string `EPDG regi but initial attach didn't go through LTE yet`
   exactly matches the observed symptom.

Therefore the remaining blocker is the modem-side persistent initial-attach APN,
NOT Nuxel serialization. Two concrete, owner-authorized follow-up paths exist:

  (A) Implement the MBIM `MS LTE Attach Config` command (the real vendor
      mechanism), or
  (B) Implement a cbd-equivalent NV load of nv_data.bin over RFS, after writing
      the correct "internet" initial-attach APN NV item (full backup + MD5 +
      rollback, per mob.md section 6). Both are now authorized.

## Safety

No NV/EFS/RADIO/BOOT/IMEI write performed this round. Wi-Fi, ZeroTier (10.11.12.99),
USB and SSH all preserved. Deployed binary rollback: /usr/libexec/nuxel/
nuxel-radiod.bak-round28-20261124T120808 (hash 6a3b77b18...). Service restored to
default NUXEL_ATTACH_CID=1 config. Source and deployed binary are synchronized
(commit f2ecd111 -> deployed dbdefd52...).
