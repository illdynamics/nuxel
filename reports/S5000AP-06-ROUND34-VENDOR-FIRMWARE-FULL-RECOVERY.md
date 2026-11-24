# Stage 06 — Round 34: full vendor firmware recovery + definitive root-cause lock

**Date:** 2026-11-24 CET
**Branch:** cs/mob
**Device:** SM-G975F / beyond2lte / S5000AP, KPN SIM (PLMN 20408), live via ZeroTier 10.11.12.99

## Verdict

STAGE_06 still NOT_PASS. This round recovered the COMPLETE matching vendor
firmware (CP + AP + vendor + BST device tree) from `./packs`, verified the
entire stack against the SAMFW G975FXXS9DTK9 package, re-derived the exact
`SetLteAttachProfile` flag semantics from fresh disassembly, fixed two real
defects in the Nuxel data-session driver (an MBIM-phase FSM stall and a
byte-inexact `payload[0]` flag decode), and re-confirmed the root cause is the
EMPTY persistent initial-attach APN in the modem NV.

## 1. Recovered vendor assets (./packs)

- `SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac/`
  - `CP_...tar.md5` -> `modem.bin` (46,062,992 bytes decompressed) = TOC container
    (BOOT / MAIN / VSS / NV / OFFSET). MAIN = ARM32 CP OS (39,895,408 bytes)
    with the full PDNMGR/PMPM symbol table.
  - `AP_...tar.md5` -> `boot.img`, `dtbo.img`, `dt.img`, `vendor.img`,
    `system.img`, `vbmeta.img`, `recovery.img`.
  - `BL_...`, `CSC_...`, `HOME_CSC_...`.
- `android_device_samsung_beyond2lte-lineage-23.2/` device tree (configs/overlay/
  `proprietary-files.txt`, `proprietary-firmware.txt`).

### Extracted vendor binaries (from vendor.img, ext4 via debugfs)
- `/bin/cbd` (494,000 B) — `cpboot-daemon`; reads `/mnt/vendor/efs/nv_data.bin`
  and forwards to the CP via `CP_REQ_NV_DATA`. No APN item dictionary inside.
- `/bin/secril_config_svc` (41,712 B) — `NetworkConfig`/`SimConfig` (network
  MODE/SIM config only; NOT APN).
- `/lib64/libsec-ril.so` (3,897,056 B) — BuildID 60889dd7… (same as rounds 17–33).
- `/lib64/libsec-ril-dsds.so`, `/lib64/libril.so`.
- `/etc/init/init.baseband.rc`, `init.exynos9820.cbd.rc`,
  `init.vendor.rilchip.rc`, `init.vendor.rilcommon.rc` — the EXACT stock modem
  boot sequence (cbd -> rild -> network_config/sim_config).
- `/etc/plmn_se13.bin` (26,390 B) — operator display-name table (contains "NL KPN").

## 2. CP firmware — recovered modem-side truth (modem.bin MAIN)

The Shannon S5000AP CP is **ARM32** (Thumb). The MAIN image carries the full
PDNMGR (Pdn Manager) / PMPM symbol table. Key recovered facts:

- `SIPC_GPRS_LTE_ATTACH_APN_INFO` (sub=20) -> `sipcProcGprsLteAttachApnInfoSet`
  -> `PMPM_HdlrGprsAttachApnInfoReq` -> `PDNMGR_SET_INITIAL_ATTACH_APN_REQ`.
  sub=20 IS the correct initial-attach-APN wire command.
- `SIPC_GPRS_SET_APN_INFO` (sub=27) = the data-profile setter (already in FSM).
- `SIPC_GPRS_PS_ATTACH_DETACH` (sub=3) -> `PMPM_HdlrGprsPsAttachDetach`.
- Flash/NV items: `SAECOMM_FLASH_LTE_INTERNET_ATTACH_ENABLED`,
  `SAECOMM_FLASH_LTE_DETACH_RE_ATTACH_REQUIRED_SUPPORT`,
  `APDNMGR_FLASH_LTE_VZW_INTERNET_ATTACH_ENABLED` (+ the header path
  `CALPSS/LteL3/PdnMgr/PDNMGR/Code/inc/PDNMGR_FlashItems.h`).
- `ati_SaveNewCoreProfile` / `ati_RequestProfileSave` — the CP's ATI
  (attach-type-indication) profile-save path.
- `"Request APN(CID=%d) is NULL & LTE attach APN(CID=%d) is NULL"` — the exact
  failure state reached when the default bearer activation finds no APN.
- `"LTE Attach APN is received"` / `"LTE Attach APN is not received"`.

## 3. New byte-exact finding — SetLteAttachProfile flag decode

Fresh disassembly of `IpcProtocol41::IpcTxSetLteAttachProfile @0x320238`:

```
320268  ldrb w8, [x29,#40]     ; flag (first arg)
320278  tst  w8, #1
320294  orr  w9, wzr, #3
320298  csinc w8, w9, wzr, ne ; (flag & 1) ? 3 : 4
3202ac  strb w8, [sp,#23]     ; payload[0]
```

=> `payload[0] = (flag & 1) ? 3 : 4`. The vendor NEVER emits 1 or 2 as
payload[0]. The prior comment ("payload[0]=3 else 1") and the direct `p[0]=flag`
pass-through were BYTE-INEXACT for flag values other than 3. Fixed in
`fmt_tx_set_lte_attach_profile` (now maps `(flag&1)?3:4`) and locked with a new
unit assertion.

Live corroboration: `NUXEL_ATTACH_FLAG=1` produced `gen_result=4` (rejected)
because the old code emitted payload[0]=1; flag=3 (payload[0]=3) is ACCEPTED
(gen_result=0) but does not trigger a re-attach.

## 4. Defects fixed this round (real code, committed)

1. **FSM stall regression** (radiod.c, data_session_tick): `DS_SET_LTE_ATTACH`
   advanced into `DS_MBIM_ATTACH_CONFIG`, which emits `false` when
   `NUXEL_MBIM_ATTACH` is unset, so the FSM stalled forever and never reached
   ALWAYS_ON_PDN/PS_ATTACH/DATA_CALL. Added an explicit MBIM-disabled skip that
   advances directly to ALWAYS_ON_PDN. (The MBIM path remains opt-in.)
2. **Byte-inexact flag decode** (fmt_tx.c): see §3.

## 5. Live re-verification (deployed, 14:51 CET)

FSM now runs clean through the full sequence to DATA_CALL:

    … SET_DATA_PROFILE -> SET_LTE_ATTACH -> MBIM_ATTACH_CONFIG(skipped)
       -> ALWAYS_ON_PDN -> PS_ATTACH -> PS_REGIST_VERIFY(REG_HOME) -> DATA_CALL
       -> data_session_reject { gen_result:0, call_state:3, pdp_state:0 }

- Every prerequisite command ACKs (GEN result 0). PS registration is a genuine
  REGISTERED_HOME (ps=1). `SetPdpContext` (sub=4) is ACCEPTED (gen_result=0).
- The default EPS bearer is still NOT connected (`GPRS_CALL_STATUS state=3`),
  and `GPRS_IP_CONFIGURATION` never arrives; rmnet0..7 stay DOWN.
- PS detach (sub=3) of ANY reason (0 and 4 both live-tested) is rejected by the
  CP with `gen_result=1` while registered — the modem will not de-register to
  apply a runtime attach-APN.

## 6. Definitive blocker (unchanged, now fully recovered)

The default EPS bearer is established during LTE INITIAL ATTACH using the
PERSISTENT initial-attach APN. That APN is EMPTY in both:

- AP EFS `/dev/sda3` `nv_data.bin` (1,048,576 B, mtime 2024-02-03, no `internet`),
- CP EFS `/dev/sdd1` `.nv_core.bak` (546,304 B, 44-byte records, no APN string).

`nv_data.bin` mtime is unchanged across this session: `SetLteAttachProfile`
(sub=20) only mutates CP RAM (cleared on PS reset per the CP log
`"PS Reset, Clear LTE Attach APN Info"`); it does NOT persist the APN to NV.

The Samsung stock ROM persists the initial-attach APN via cbd's
`CP_REQ_NV_DATA` flow writing `nv_data.bin` using the private QBR item-ID table
(`PDNMGR_FlashItems.h`), which is not recoverable from the repo, `nv_data.bin`,
`.nv_core.bak`, `libsec-ril.so`, `cbd`, or the CP image (only the item NAMES are
embedded, not the numeric IDs/offsets). A blind NV item-ID write risks
corrupting a QBR-signed container and is refused (correctly) by the fail-closed
RFS/NV policy.

## 7. Safety

No NV/EFS/RADIO/BOOT/DTB/DTBO/IMEI/calibration write performed. RADIO (/dev/sda16)
and BOOT (/dev/sda8) untouched. Wi-Fi, ZeroTier, USB, SSH intact. Host suite
(build + 9 suites + 3000-iter fuzzer + ASan/UBSan) PASS. Deployed radiod
SHA256 1e2df783f5e1d05acf1d140ba972866d31c7f2ffe0702dd57bfcae6ee8116851
(MBIM OFF, ATTACH_FLAG=3).
