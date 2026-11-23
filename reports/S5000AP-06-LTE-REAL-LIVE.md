# S5000AP Stage-06 — SIM → Registration → Real LTE Data (Round 11+, live, autonomous)

**Status:** `STAGE_06_NOT_YET_PASS — full vendor-exact data-session sequence live-ACKed; PDP
activation still rejected by CP with GPRS_CALL_STATUS state=3 (not connected).`

**Branch:** `cs/mob`  **HEAD:** `9c6051281de6a632b5ca8345882d4155e5ee630e`
**Device:** SM-G975F / beyond2lte / Exynos9820 / S5000AP (BEYOND2LTE EUR OPEN 26)
**Kernel:** `4.14.253-gf7194c1d15ed-dirty` (SMP PREEMPT, 2026-11-23 00:43:30 CET)
**CP:** ONLINE (sysfs `/sys/devices/platform/10000.mif_pdata/modem_state` = ONLINE)
**SIM:** ds_detect=1 (present); protocol READY (SEC_PIN_STATUS=READY); serving PLMN 20416 (T-Mobile NL)
**Owner authorization:** explicit "any action necessary" + active SIM seated on-device.
**Date:** 2026-11-23 (Europe/Amsterdam)

---

## 0. Safety invariants (all VERIFIED this session)

- RADIO `/dev/sda16` SHA256 = `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` (UNCHANGED).
- No write to DT/CP/RADIO/EFS/NV/protected partitions. No PIN/PUK/IMSI/ICCID/IMEI/MSISDN logged.
- Wi-Fi (wlan0), USB (usb0), ZeroTier management preserved throughout.
- Reversible userspace deployment; rollback binary preserved multiple versions.
- Bounded retries; no speculative malformed frames; no brute force.
- New deployed binary hashes: `82d914703e…` (current), prior `4511364535…`, `8bf83a72cd…`.

---

## 1. What was decoded AND fixed this session (all source-backed, vs exact vendor RIL)

Reference: `/tmp/vendor-ro/lib64/libsec-ril.so` (SM-G975F/EFUJ2), Build ID `60889dd7`,
SHA256 `b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3`.

### 1a. Framing + command IDs confirmed byte-exact (NOT the bug)
Each `IpcTx*` function's `mov w,#0xSSMM` constant yields the authoritative main/sub:

| function | main/sub word | main | sub | len |
|---|---|---|---|---|
| IpcTxDefinePdpContext @0x31f580 | — | 13 | 1 | 134 |
| IpcTxSetPdpContext @0x31f6e0 | 0x040d | 13 | 4 | 112 |
| IpcTxGetPdpContext @0x31f928 | 0x040d | 13 | 4 | 7 |
| IpcTxPsAttach @0x31fa98 | 0x030d | 13 | 3 | 10 |
| IpcTxSyncProfileInfo @0x31fb48 | 0x250d | 13 | 37 | 326 |
| IpcTxSetDataProfile @0x31ff48 | 0x1b0d | 13 | 27 | 203 |
| IpcTxSetLteAttachProfile @0x320238 | 0x140d | 13 | 20 | 201 |
| IpcTxSetDataCallEstablish @0x320a10 | 0x0203 | 3 | 2 | 8 |
| IpcTxSetMobileDataSetting @0x3214c8 | 0x1d0d | 13 | 29 | 9 |
| IpcTxSetAlwaysOnPdn @0x321550 | 0x220d | 13 | 34 | 9 |

The 7-byte on-wire FMT header is `[u16 len][u16 seq][u8 main][u8 sub][u8 type]` — the
existing `sipc_fmt_hdr` already matches (verified via `strh/strb` offsets in every function).

### 1b. RadioTechnologyType enum decoded: LTE = 14
`NetworkManager::GetGeneration(RadioTechnology)` @0x1f7ce8 indexes an 18-entry table
(= Android RADIO_TECH enum 1..17). LTE = 14. The previous SyncProfileInfo emitted RAT=0.

**FIX (HEAD 500020fe):** `fmt_tx_sync_profile_info` now writes `payload[3] = 14` (LTE).

### 1c. Explicit mobile-data-enable step added
The vendor RIL's `DoSetMobileDataSetting` is a distinct step (sub=29) that enables mobile
data before profile sync. Previous FSM conflated it with SyncProfileInfo.

**FIX (HEAD 500020fe):** added `DS_SYNC_PROFILE` phase; `DS_ENABLE_MOBILE_DATA` now emits
`SetMobileDataSetting(sub=29, enable=1, extra=1)` before `SyncProfileInfo(sub=37)`.

### 1d. SetPdpContext pdp_type corrected
`IpcTxSetPdpContext` @0x31f6e0 jump table (rodata @0x149806) is identity pdp_type→wire code.
pdp_type=1 = "full APN" path (@31f7d0, copies APN + flags bit0|bit4). pdp_type=3 is a non-APN
variant.

**FIX (HEAD f552e971):** `fmt_tx_set_pdp_context` now uses `p[0]=1` (full-APN path).

### 1e. PS-attach dwell added
The CP ACKs PsAttach with a generic GEN echo (main=128 sub=1 type=2) but completes the actual
GPRS/PS attach asynchronously. No `GPRS_PS`-done response exists.

**FIX (HEAD 9c605128):** added a 3-second hold on `DS_PS_ATTACH` (`phase_entered_ms` dwell)
so the attach completes before `SetPdpContext(ACTIVATE)`.

---

## 2. GPRS_CALL_STATUS state semantics (decoded)

`IpcRxGprsCallStatus` @0x321ab0 maps the data-call state byte (payload[1]):
- payload[1] == 1  -> internal state 4
- payload[1] == 10 -> internal state 5
- payload[1] == 11 -> internal state 6
- anything else (incl. **3**) -> internal state 0 = **not connected**

Live CP response after SetPdpContext(ACTIVATE): `GPRS_CALL_STATUS` payload
`01 03 00 00 00 00 00 00 00` = cid=1, **state=3 → not connected**.
`GPRS_PDP_CONTEXT` payload `01 14 00` = 1 context, state=0 (DISCONNECTED).
**No `GPRS_IP_CONFIGURATION` (sub=9) is ever emitted.**

---

## 3. Live hardware evidence (VERIFIED this session)

| Stage | Status | Evidence |
|---|---|---|
| CP ONLINE | PASS | modem_state=ONLINE |
| SIPC5 RX | PASS | DISP_RSSI/ICON periodic; GEN + GPRS responses |
| SIM present | PASS | sim/ds_detect=1 |
| SIM READY | PASS | SEC_PIN_STATUS=READY (payload 0000/8200/8300) |
| Serving network | PASS | NET_SERVING_NETWORK = PLMN "20416" (T-Mobile NL) |
| Registration | PASS (CS) | NET_REGIST + NET_SERVING_NETWORK present |
| Data-cmd TX | PASS | full sequence kernel-accepted (GEN echo each) |
| Data-cmd ACK | PASS | GEN (128) echo per command |
| **Data call / PDP** | **BLOCKED** | GPRS_CALL_STATUS state=3 (not connected) |
| **IP / rmnet** | **BLOCKED** | no IP config; rmnet0..7 DOWN |

Corrected live sequence now: `SetMobileDataSetting(29) → SyncProfileInfo(37,RAT=14) →
SetDataProfile(27) → SetLteAttachProfile(20) → DefinePdpContext(1) → AlwaysOnPdn(34) →
PsAttach(3) [hold 3s] → SetPdpContext(4,ACTIVATE,pdp_type=1) → GetPdpContext(4,query)`.

All 8 commands get GEN `0x80` ACK. PDP is then rejected: `GPRS_CALL_STATUS 010300…`.

---

## 4. Honest remaining blocker (unchanged after 4 source-backed fixes)

The CP consistently rejects PDP activation with state=3 (not connected) regardless of:
1. RAT value (0 → 14)
2. Mobile-data-enable step (added)
3. pdp_type (3 → 1)
4. PS-attach dwell (added 3 s)

**This rules out framing, command IDs, RAT enum, pdp_type, mobile-data-enable, and attach timing.**

The two remaining candidate root causes (neither yet provable to a known-good reference):

1. **Carrier/SIM data-plan not provisioned or active** — the network rejects the PDP context
   activation at the ESM/SM layer (no cause code surfaced to the AP; the CP just reports
   "not connected"). This is consistent with a data-disabled/not-provisioned SIM.
2. **A still-missing data-authorization / initial LTE attach prerequisite** — e.g. the
   RIL's `RIL_REQUEST_ALLOW_DATA` flow which the recovered symbol table shows has NO distinct
   `IpcTxSetAllowData`; it is instead embodied in `IpcTxSetMobileDataSetting(sub=29)` (now sent)
   plus a possible NET-family `NET_POWERON_ATTACH`/initial-attach step that is not yet emitted.

The most decisive next proof would be to confirm the SIM's data plan is active (single owner fact),
because the CP is CS-registered on a valid network but PS/data attach never completes.

---

## 5. Capability matrix

| Capability | State |
|---|---|
| LTE data | **BLOCKED** (PDP activation rejected: GPRS_CALL_STATUS state=3, no IP) |
| SMS | BLOCKED (capability flag false) |
| Voice | BLOCKED (capability flag false) |
| IMS/VoLTE | BLOCKED (capability flag false) |
| Registration | PASS (CS/voice; PS/data attach does not complete) |

---

## 6. Deliverables

- Source + tests committed: HEAD `9c605128` (and `f552e971`, `500020fe` on top of `71eecf78`).
- Byte-exact tests updated and passing (`test_fmt_tx`, `test_data_session`).
- Live-deployed binary `82d914703e…` with rollback preserved at
  `/usr/libexec/nuxel/nuxel-radiod.bak-pre-rat-fix`.
- This report.

**Strongest supportable verdict:** `STAGE_06_NOT_YET_PASS — [PDP rejected: GPRS_CALL_STATUS
state=3 (not connected) after all 8 vendor-exact commands; most likely carrier data-plan
provisioning or a missing initial-attach/allow-data prerequisite].` Not fabricated; no PASS claimed.
