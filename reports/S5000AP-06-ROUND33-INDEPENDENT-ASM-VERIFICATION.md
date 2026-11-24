# Stage 06 — Round 33: independent aarch64 disassembly verification + CP EFS NV format

**Date:** 2026-11-24 CET
**Branch:** cs/mob
**Device:** SM-G975F / beyond2lte / S5000AP, KPN SIM (PLMN 20408), live via ZeroTier

## Scope

Fresh, independent disassembly of `.vendor-ro/libsec-ril.so`
(BuildID 60889dd714394ae0db7c2ecc2bf2740f) to VERIFY (not assume) the prior
rounds, plus first-pass forensic of the CP EFS NV container. No NV/EFS write.
Device state unchanged (CP online, SIM ready, PS REGISTERED_HOME, no bearer).

## Verdict

STAGE_06 still NOT_PASS. This round replaced several "recovered in a prior round"
claims with fresh byte-level confirmation and added two new, hard facts. The
blocker remains the PERSISTENT initial-attach APN, now confirmed empty in BOTH
the AP EFS (`/dev/sda3` nv_data.bin) and the CP EFS (`/dev/sdd1` .nv_core.bak).

## 1. IpcTxSyncProfileInfo (sub=37) — serialization is byte-exact

Disassembled `IpcProtocol41::IpcTxSyncProfileInfo @0x31fb48` (736 bytes). The
emitted 326-byte frame matches `fmt_tx_sync_profile_info` field-for-field:

- payload[0]=1, payload[1..2]=region(u16), payload[3]=RAT(14=LTE),
- APN at payload[4..104] (101 B), protocol home/roam at payload[109]/[110],
- auth flag at payload[311], proto copies at [312]/[313], pco at [314].

=> The sub=37 GEN=1 rejection is SEMANTIC (CP refuses profile sync in this
state), NOT a Nuxel serialization defect. This removes "serialization bug" as
a remaining hypothesis.

## 2. IpcTxPsAttach (sub=3) — detach reason encoding byte-exact

`IpcTxPsAttach @0x31fa98`: 10-byte frame, payload[0]=attach(1)/detach(0),
payload[1]=suspend, payload[2]=DataDetachReason clamped to 1..4. `fmt_tx_ps_attach`
matches exactly. `DoDetachForIA` passes reason=4 (confirmed from
`DataCallManager::DoDetachForIA @0x22bdf0`, vtable slot #88, w5=4). The reason=4
rejection is therefore a genuine CP semantic rejection.

## 3. IpcTxSetPdpContext (sub=4) — ACTIVATE bit gated on auth!=0 (confirmed)

`IpcTxSetPdpContext @0x31f6e0`:
```
31f878: sub w8, w20, #0x1        ; w20 = auth (int arg5)
31f8a4: cbz w20, 31f8e4          ; if auth==0 -> return with flags=0x01 (NO ACTIVATE)
31f8a8: orr w8, w22, #0x10       ; else flags |= 0x10 (ACTIVATE)
```
For KPN `internet` (DataAuth NONE=0) the vendor never sets ACTIVATE and relies
on LTE INITIAL ATTACH for the default bearer. This is the exact mechanism by
which an empty initial-attach APN yields GPRS_CALL_STATUS state=3.

## 4. DoSetInitialAttachApn base class is a stub (confirmed)

`DataCallManager::DoSetInitialAttachApn @0x22bad8` (68 B): checks a global
version word (`cmp w8,#2; b.lt -> ret 0`), else only logs and returns 0. It
never transmits. The real implementation is the derived
`LteEpdgDataCallManager::DoSetInitialAttachApn @0x28c6c8` (1984 B) whose tail
sequence is SetLteAttachProfile(sub=20) -> DoDetachForIA(PsAttach detach=4).

## 5. Vendor strings confirming root cause (new)

`strings .vendor-ro/libsec-ril.so`:
- "Reset attach apn after radio power up for LSI model"
- "IsEsmFlagZeroNetwork is true. Set attach apn to null"
- "Attach Apn is changed, but no detach"

These lock in: (a) the attach APN is reset to null after radio power-up for LSI
(Exynos) models, and (b) for ESM-flag-zero networks the vendor sets attach APN
to null — i.e. the AP must supply the APN via a different path, which on this
modem is the persistent NV.

## 6. CP EFS NV container format (new forensic)

CP EFS is `/dev/sdd1` (mounted ro `/tmp/cpefs_inspect`), containing
`.nv_core.bak` (546,304 = 0x855c0 B). Format observation:

- Header `04 00 00 00` + padding.
- Repetitive 44-byte (0x2c) records: `[u32 size][u32 crc][u32 flags][...]`
  with size values {0x01,0x46,0x47,0x7d,0x7e,0x7f,0x80,...} and crc words like
  0x4160d5bf / 0x417719cf.
- NO ASCII APN string present (`internet`/`ims`/`IMSI` absent); the only ASCII
  runs are CP diag function names (`sm_SetApn`, `sm_GetApn`, `sm_SetApnLength`,
  `PMPM_SendEsmReattachInd`, etc.).

=> The CP modem NV has NO stored initial-attach APN. This is consistent with the
AP EFS nv_data.bin finding (also no APN string).

## Definitive requirement

To establish the default EPS bearer, the CP NV initial-attach APN item must be
provisioned to "internet". This requires the Samsung `cbd` NV item-ID table
(string->numeric-ID + on-disk encoding), which is proprietary and not present
in: the repo, `nv_data.bin`, `.nv_core.bak`, `libsec-ril.so`, or any public
source (sourcegraph global code search returns zero matches for
`PDNMGR_SET_STATELESSINFO_ATTACHINFO` / `PDNMGR_SET_PDNCONTEXT_APN`).

A blind NV item-ID write would risk NV/EFS corruption and is refused by the
existing fail-closed RFS/NV policy (correctly). The item-ID table or a
known-good identical-device reference image (same SM-G975F + S5000AP + KPN)
is the single external asset that would unlock the bearer.

## Safety

No NV/EFS/RADIO/BOOT/DTB/DTBO/IMEI/calibration write performed this round.
RADIO sda16 and BOOT sda8 unchanged. Wi-Fi wlan0, ZeroTier 10.11.12.99, USB,
SSH all intact. Host test suite (build + 9 unit suites + 3000-it fuzzer +
ASan/UBSan) PASS. Deployed radiod unchanged (80d7220a…, MBIM OFF).
