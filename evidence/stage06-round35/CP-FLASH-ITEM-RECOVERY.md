# Stage 06 Round 35 — CP firmware flash-item recovery (definitive findings)

**Firmware:** ./packs SAMFW G975FXXS9DTK9 (matching live SM-G975F S5000AP)
**CP image:** modem.bin (46,062,992 B) = TOC container {BOOT|MAIN|VSS|NV|OFFSET}
  - MAIN = ARM32 Thumb OS, file offset 0x37000, load addr 0x40010000, size 39,895,408
**Branch:** cs/mob-round35-stage06

## 1. TOC structure
Sections (name, load, size, crc, id):
- BOOT  load=0x40000000 size=0x1e40 id=1
- MAIN  load=0x40010000 size=0x260c170 id=2   (ARM32 CP OS)
- VSS   load=0x47800000 size=0x5df6a0 id=3
- NV    load=0x45600000 size=0x100000 id=4     (NV image, 1 MiB)
- OFFSET load=0 size=0x85600 id=5

## 2. PDNMGR_FLASH_* item identifiers (recovered, file 0x6c3684 region)
Each flash item is described by THREE strings {group, ds-name, PDNMGR-id}, with a
0x41a2xxxx/0x419cxxxx descriptor pointer interleaved:

- "Main.PS.Stack" + "PDNMGR_FLASH_INT_DDS"
- "Main.IMS.Stack" + "PDNMGR_FLASH_IMS_DDS"
- "!SAEL3_DS.CLASS1_BACKOFFTIMER_VALUE" + "!SAEL3.CLASS1_BACKOFFTIMER_VALUE" + "PDNMGR_FLASH_CLASS1_BACKOFFTIMER_VALUE"
- "!SAEL3_DS.CLASS3_BACKOFFTIMER_VALUE" + ...
- "!SAEL3_DS.LTE_VZW_EXCESSIVE_PDN_MAX_CONN" + ... + "PDNMGR_FLASH_LTE_VZW_EXCESSIVE_PDN_MAX_CONN"
- "!SAEL3_DS.LTE_VZW_EXCESSIVE_PDN_MAX_CONN_T" ...
- "!SAEL3_DS.LTE_VZW_EXCESSIVE_PDN_WAIT_TIME" ...
- "!SAEL3.Cfg.INTERNET_ATTACH_ENABLED"  @ 0x6c3d10  <- key, followed by 0x41a23350 then "PDNMGR_FLASH_LTE_VZW_INTERNET_ATTACH_ENABLED"
- "ds_NASL3.PLMN.Equivalent.Plmn.List" + "PDNMGR_FLASH_EQUIV_PLMN_LIST"
- "PDNMGR_FLASH_EQUIV_PLMN_COUNT"
- "!SAEL3_DS.SAE_VOICE_DOMAIN_PREF" + "PDNMGR_FLASH_VOICE_DOMAIN_PREF"
- "NASU.DOMESTIC.DATA.STATUS" + "PDNMGR_FLASH_DOMESTIC_DATA_STATUS"
- "NASU.ROAMING.DATA.STATUS" + "PDNMGR_FLASH_ROAMING_DATA_STATUS"
- "!SAEL3_DS.IMS_OVER_WLAN_STATUS" + "PDNMGR_FLASH_IMS_OVER_WLAN_STATUS"

## 3. SAECOMM_FLASH_* identifiers (SAECOMM L3 layer, file 0xebb3bc region)
Full list recovered (24 items) with QBR keys. Critical two:
- "!SAEL3.Cfg.INTERNET_ATTACH_ENABLED" -> "SAECOMM_FLASH_LTE_INTERNET_ATTACH_ENABLED"  (BOOLEAN flag)
- "ds_NASL3.PLMN.Equivalent.Plmn.List" ... etc

## 4. THE definitive storage key for initial-attach APN
`NASU.LTE.ATTACH.APN.INFO`  (and dual-sim `DS_NASU.LTE.ATTACH.APN.INFO`)
file offsets 0x46b640 / 0x46b65c / 0x6c31c4 / 0x6c31e0
This is the QBR persistent-storage key that holds the LTE initial-attach APN
(APN name + auth + protocol). This is the item that is EMPTY in the running
modem's NV (per rounds 25-34), causing GPRS_CALL_STATUS state=3 (no default EPS
bearer).

## 5. NV subsystem structure
- NV_ITEM0..NV_ITEM35  (file 0x41aa9c..0x460564): RF/calibration NV region
  (CAL.LTE.CAL_ITEM* / ET.COMMON.TX_ET_*) — PROTECTED, must not touch.
- NV_ITEM_Read / NV_ITEM_Write (file 0x210542e / 0x5ca4f1 region): NV I/O entry points.
- NV_READ / NV_WRITE / NV_READ_RSP / NV_WRITE_RSP / NV_WRITE_NTF (file 0x21a887c..0x21eca68):
  CP<->AP NV transfer protocol handlers (RFS/CP_REQ_NV_DATA path).

## 6. Initial-attach APN call chain (strings recovered, all present)
- SIPC_GPRS_LTE_ATTACH_APN_INFO (sub=20) -> sipcProcGprsLteAttachApnInfoSet  (0x33cce6)
- PMPM_UpdateSetInitialAttachApnReq (0x16196) / PMPM_UpdateGprsAttachApnInfoReq (0x161b8)
- PMPM_PreprocSetInitialAttachApnReq (0x168f2) / PMPM_PreProcGprsAttachApnInfoReq (0x16915)
- PMPM_HdlrSetInitialAttachApnReq (0x16d5a / 0x3c2044) / PMPM_HdlrGprsAttachApnInfoReq (0x16d7a / 0x3c2064)
- PMPM_SendNsSetInitialAttachApnRsp (0x700698)
- PMPM_SendEsmAttachApnStatusUpdReq (0x701588)
- PMPM_ReplaceNullApnDuringInitialAttach (0x16484)
- sm_SetApn / sm_GetApn / sm_SetApnLength / sm_GetApnLength / sm_GetApnPtr / sm_ComapreWithSessionApn
- PMPM_EncodeAPN / PMPM_UpdateAPNTable / PMPM_SetConvertedApnType / PMPM_AddApnProfile / PMPM_DeleteApnProfile

## 7. Status of QBR numeric-ID recovery
Names recovered fully. Numeric QBR item IDs + on-disk encoding (CRC/sign) are
NOT yet proven. QBR container is signed (round-34 evidence). A blind write is
refused by fail-closed policy (correct).

Next step: disassemble NV_ITEM_Read/Write + QBR hash to recover numeric IDs
and confirm write-path feasibility WITHOUT touching protected RF/cal NV.
