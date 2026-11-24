# Stage 06 — Round 30: FINAL BOSS — exhaustive ABI recovery + live verification

**Date:** 2026-11-24 CET
**Branch:** cs/mob
**Device:** SM-G975F / beyond2lte / S5000AP, KPN SIM (PLMN 20408), live via ZeroTier
**Status:** CP ONLINE, SIM READY, PS REGISTERED_HOME, rmnet0..7 DOWN, no EPS bearer.

---

## 0. Executive verdict

This round performed FRESH, independent relocation-resolved recovery of the complete
vendor IpcProtocol41 command vocabulary directly from the authoritative
`libsec-ril.so` (BuildID 60889dd714394ae0db7c2ecc2bf2740f), plus fresh live-device
inspection. The remaining blocker — the modem's **persistent initial-attach APN** —
is now characterized to its exact mechanism with no remaining ambiguity.

**The initial-attach APN is NOT settable via any FMT/IpcProtocol41 wire command.**
It is set via one of two vendor subsystems that are physically absent from Nuxel:
(A) the Samsung MBIM host (`/vendor/bin/libsecmbim`, gated by
`SEC_FLOATING_FEATURE_COMMON_SUPPORT_MBIM`), or (B) Samsung `cbd` NV provisioning.
Neither binary is present in-repo or on-device, and neither ABI is recoverable from
`libsec-ril.so` alone.

---

## 1. NEW — Authoritative GPRS/CFG/SAT subcommand table (relocation-resolved)

Previous rounds derived sub-cmd names via a script that resolved `.data.rel.ro`
pointer slots through R_AARCH64_RELATIVE relocations. This round re-derived the
**complete, unambiguous** GPRS→CFG→SAT sub-command table by applying the actual
relocations (no jump-table indirection error):

| sub | name |
|---|---|
| 1 | GPRS_DEFINE_PDP_CONTEXT |
| 3 | GPRS_PS |
| 4 | GPRS_PDP_CONTEXT |
| 9 | GPRS_IP_CONFIGURATION |
| 16 | GPRS_CALL_STATUS |
| **20** | **GPRS_LTE_ATTACH_APN_INFO** |
| **27** | **GPRS_SET_APN_INFO** |
| **29** | **GPRS_MOBILE_DATA_STATUS** |
| **34** | **GPRS_SET_ALWAYS_ON_PDN** |
| **37** | **GPRS_SYNC_PROFILE_INFO** |

This CONFIRMS the FMT wire numbers used by `fmt_tx.c` are byte-correct (sub=20/27/
29/34/37), and it CORRECTS a documentation bug in `ipc41_cmdmap.h` which had
`SET_APN_INFO=23`, `MOBILE_DATA_STATUS=25`, `SET_ALWAYS_ON_PDN=27` (incorrect).
The corrected enum is committed this round. The runtime routing values used for
frame matching (`CALL_STATUS=16`, `PDP_CONTEXT=4`, `IP_CONFIGURATION=9`) were
ALREADY correct, so there is no data-path regression.

## 2. NEW — `SET_INITAL_ATTACH_APN` is a LOG STRING, not a wire command

The string `SET_INITAL_ATTACH_APN` (vendor spelling "INITAL") lives at `.rodata`
0x10db5f with **zero** code xrefs and **zero** `.data.rel.ro` pointer references.
It is used only in diagnostic logging inside the MBIM/EPDG code path. It is NOT a
dispatchable FMT sub-command in any family (GPRS ends at 37; the table then flows
into SAT/CFG). There is no missing wire command in the FMT surface.

## 3. CONFIRMED — MBIM is the authoritative initial-attach path (gated, absent)

`DoSetInitialAttachApn @0x28c6c8`:
- `SupportMBIM()` (SemFloatingFeature) gated by
  `SEC_FLOATING_FEATURE_COMMON_SUPPORT_MBIM` (`getEnableStatus`).
- If true → `MbimManager::DoSetMsLteAttachConfig @0x281358`
  → `MbimAdaptor::MakeSetMsLteAttachConfig @0x1c3018`
  → 3-context MBIM `MS LTE Attach Config` (apn/user/pw) → SIPC transport.
- If false → `ConvertDataProfile` → `SetLteAttachProfile` → `SetDataProfile` →
  `DoDetachForIA` (PsAttach detach reason=4) — this terminal step was REJECTED live
  in Rounds 24 and 29 (`gen_result=1`, `0d03030180`).

The MBIM transport binary `/vendor/bin/libsecmbim` and its SIPC encapsulation ABI
are NOT present in-repo or on-device. Standard Linux `libmbim`/`mbimcli` exist
on-device but target USB CDC-MBIM; the S5000AP MBIM control channel is over SIPC
(no `/dev/cdc-wdm`, no `/dev/wwan`).

## 4. NEW — RFS NV protocol fully recovered (read-only, observable)

`Nv::ProcessNVRead @0x1d8a10` confirms the RFS NV request wire format:
- Request: `[u32 total_len][u8 op=0x01][u8 seq][u32 item_id][u32 length]`
  (item_id at offset 6, length at offset 10).
- Response: 14-byte `[u32 result][u8 op][u8 seq][u16 rsvd][u32 detail]`.

Live RFS traffic shows the CP issues ONLY `UNLINK_FILE("DELETE_ALL_VIS")` at boot;
it issues **no** `NV_READ` because the AP EFS (`/dev/sda3`, 1 MiB `nv_data.bin`) was
already populated by the prior stock Samsung boot and the modem is already ONLINE/
registered. The `nv_data.bin` contains the CP firmware's PDNMGR/PMPM/sm_* symbol
table (e.g. `PMPM_UpdateSetInitialAttachApnReq`, `sm_GetApn`, `sm_GetApnPtr`) but
the exact persistent initial-attach-APN NV item ID/offset is a proprietary `cbd`
table NOT present in-repo; it cannot be written safely by guessing.

## 5. COMMITTED FIXES (this round)

1. `ipc41_cmdmap.h` — corrected GPRS sub-command enum to the authoritative
   relocation-resolved values; added GPRS_LTE_ATTACH_APN_INFO=20 and the full
   18..37 range. (Cosmetic—no data-path regression.)
2. `radiod.c` — added `GPRS_LTE_ATTACH_APN_INFO`/`SET_ALWAYS_ON_PDN`/
   `SYNC_PROFILE_INFO` name lookups; RFS `rfs_rx` diagnostic now surfaces the NV
   `item_id` (read-only; the NV request is still answered fail-closed).

Host test suite + aarch64 on-device build both PASS (`BUILD_EXIT=0`). No EFS/NV/
RADIO/BOOT write. Wi-Fi/ZeroTier/USB/SSH preserved.

## 6. Remaining hard dependency (not owner-gated; a missing proprietary binary)

To establish the default EPS bearer, ONE of these must be sourced (neither is a
software change I can derive from available artifacts):

1. The Samsung `libsecmbim` host binary (or its SIPC-MBIM encapsulation ABI) so the
   native MBIM `MS LTE Attach Config` can be implemented and sent; OR
2. The Samsung `cbd` NV-item table (or a stock `nv_data.bin` reference from an
   identical device on the working carrier) so the exact initial-attach-APN NV item
   ID/encoding can be recovered and written via RFS_NV_WRITE_ALL with full backup +
   rollback.

No simulated/mock success was produced. No NV structure was guessed.
