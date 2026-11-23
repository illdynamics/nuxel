# S5000AP Stage-06 — SIM → Registration → Real LTE Data (Round 14, authoritative decoder + attach prerequisites)

**Status:** `STAGE_06_NOT_YET_PASS — CP ONLINE + SIM READY + CS-REGISTERED (PLMN 20416
T-Mobile NL); PS/DATA REGISTRATION = DENIED (RegState 3, vendor-verified) despite
byte-exact full data-session sequence including NEW SetServiceDomain(CS_PS),
SetPreferredNetType(LTE) and corrected SetPdpContext activation. PDP still
GPRS_CALL_STATUS state=3 (not connected). The remaining blocker is the CP/network
PS-attach registration denial, not command framing.`

**Branch:** `cs/mob`
**HEAD:** `df3d2c19`
**Device:** SM-G975F / beyond2lte / Exynos 9820 / S5000AP (BEYOND2LTE EUR OPEN 26)
**Kernel:** `4.14.253-gf7194c1d15ed-dirty` (SMP PREEMPT, 2026-11-23 00:43:30 CET)
**CP:** ONLINE (`/sys/devices/platform/10000.mif_pdata/modem_state` = ONLINE)
**SIM:** ds_detect=1; SEC_PIN_STATUS `00 00` = READY (no PIN)
**Owner authorization:** explicit "any action necessary" + active SIM seated.
**Date:** 2026-11-23 (Europe/Amsterdam)

---

## 0. Safety invariants (re-verified this session)

- RADIO `/dev/sda16` SHA256 = `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` (UNCHANGED).
- BOOT `/dev/sda8` = `2daeb1f36095b44b318410b3f4e8b5d989dcc7bb023d1426c492dab0a3053e74` (UNCHANGED, no DT/BOOT write).
- No write to DT/CP/RADIO/EFS/NV/protected partitions. No PIN/PUK/IMSI/ICCID/IMEI/MSISDN logged.
- Wi-Fi (wlan0), USB (usb0), ZeroTier management all preserved and independent.
- Rollback binary preserved (`nuxel-radiod.bak-stage06-svcdomain-*`), pre-change binary hash recorded.
- Deployed binary SHA256 = `e50b9c820c97e0bdab9aad816c0b4cba9d4c5ad28fa706774b5d9a08d212df01`.
- Bounded retries; no speculative malformed frames; no brute force; no CP reset loops.

---

## 1. New corrections delivered this round (source-backed, live-verified)

### 1a. SetPdpContext layout bug FIXED (real protocol correction)

Re-deriving `IpcProtocol41::IpcTxSetPdpContext @0x31f6e0` (libsec-ril.so build
60889dd7) on the read-only device vendor mount revealed the ACTUAL 112-byte
activation frame layout:

```
[0..1] total_len=0x70(112)  [2] msg_seq=0  [3] ack_seq=0
[4] main=0x0d(13 GPRS)  [5] sub=0x04(4 GPRS_PDP_CONTEXT)  [6] type=0x03(NOTI)
payload[0]  = protocol wire byte (0x04 IPV4V6 / 0x05 IP / 0x06 IPV6)
payload[1]  = pdp_type = 3  (AccessNetworkType EUTRAN/LTE)
payload[2..5] = flags word 0x11 (APN-present | activate)
payload[6..37] = APN (32 bytes NUL-padded)
payload[38..69] = username (32B, zero)
payload[70..101] = password (32B, zero)
payload[102] = auth flag (0x00010201 >> ((auth-1)*8))
payload[103] = 0
payload[104] = protocol wire byte (2nd copy)
```

The pdp_type value 3 was recovered from `DataCallSetup::ToAccessNetworkType(
RadioTechnology) @0x29fa08`, whose `.rodata` table (VA 0x14708c) maps RAT 14
(LTE) → AccessNetworkType 3. The previous implementation had `payload[0]=1`
and `payload[1]=cid` — protocol/pdp_type were in the WRONG byte positions.
This is fixed and regression-tested.

### 1b. NET attach prerequisites added

Added two source-backed NET commands missing from the FSM:

- `fmt_tx_set_service_domain` (main=8 sub=8 NET_SERVICE_DOMAIN_CONFIG),
  payload=[2]=CS_PS — recovered from `IpcTxNetSetServiceDomain @0x336dc8`.
- `fmt_tx_set_preferred_net_type` (main=8 sub=10 NET_MODE_SEL),
  payload=[9]=LTE/WCDMA/GSM-auto — recovered from
  `IpcTxNetSetPreferredNetType @0x335e00`.

Both are inserted as new FSM phases before ENABLE_MOBILE_DATA.

### 1c. Authoritative NET_REGIST PS/CS decode

The NET_REGIST (main=8 sub=5) response is now decoded per `IpcRxNetRegState
@0x339818`: payload[1] = primary RegState, payload[2] = secondary RegState,
using the vendor-confirmed `NetRegState` enum from `IsRegistered @0x2a9ce8`
({1,5}=registered) and `IsDenied @0x2a9d38` ({3,13}=denied).

Live output now explicitly reports:

```
net_regist_state  ps=3 ps_name=DENIED  cs=1 cs_name=REGISTERED
```

This is the protocol-backed, vendor-decode answer: **PS/data registration is
DENIED; CS/voice registration is REGISTERED.**

---

## 2. Live data-session sequence (20:25:25 CET, deployed build e50b9c82)

The corrected full sequence, each step byte-exact and its GEN echo result observed:

| Phase | cmd (main/sub) | GEN echo result | Meaning |
|---|---|---|---|
| NET_REGIST_CHECK | 8/5 | — | ps=DENIED, cs=REGISTERED |
| SET_SERVICE_DOMAIN | 8/8 | 0 | accepted |
| SET_PREFERRED_NET | 8/10 | 0 | accepted |
| ENABLE_MOBILE_DATA | 13/29 | **3** | rejected by CP |
| SYNC_PROFILE | 13/37 | 1 | rejected by CP |
| SET_DATA_PROFILE | 13/27 | 0 | accepted |
| SET_LTE_ATTACH | 13/20 | 0 | accepted |
| DEFINE_PDP | 13/1 | 1 | rejected by CP |
| ALWAYS_ON_PDN | 13/34 | 0 | accepted |
| PS_ATTACH | 13/3 | 0 | accepted (no PS-state noti follows) |
| DATA_CALL (SetPdpContext) | 13/4 | 0 | accepted |
| → GPRS_CALL_STATUS | 13/16 | — | **state=3 (NOT connected)** |

The modem accepts the activation write (`gen_result=0`) but never establishes a
bearer: `GPRS_CALL_STATUS` (payload `03 03 00 …`) reports call-state 3, decoded
authoritatively by `IpcRxGprsCallStatus @0x321ab0` (1→4, 10→5, 11→6 = connected;
3 = not connected). No `GPRS_IP_CONFIGURATION` follows; `rmnet0..7` stay DOWN.

---

## 3. Live hardware evidence table

| Gate | Status | Evidence |
|---|---|---|
| CP ONLINE | PASS | modem_state=ONLINE |
| SIPC5 RX/TX | PASS | NET/GPRS/GEN/DISP RX + FMT TX kernel-accepted |
| SIM present | PASS | sim/ds_detect=1 |
| SIM READY | PASS | SEC_PIN_STATUS payload 00 00 |
| Serving network | PASS | NET_SERVING_NETWORK = PLMN 20416 (T-Mobile NL) |
| CS/voice registration | PASS | NET_REGIST cs=1 REGISTERED |
| Data-cmd TX | PASS | full sequence byte-exact, each ACKed |
| **PS/data registration** | **BLOCKED** | NET_REGIST ps=3 DENIED |
| **Data bearer / PDP** | **BLOCKED** | GPRS_CALL_STATUS state=3 (not connected) |
| **IP / rmnet** | **BLOCKED** | rmnet0..7 DOWN |

---

## 4. Root-cause analysis (honest, evidence-backed)

The first actionable failure is **PS/data registration denial**: the CP reports
`NET_REGIST (ps=3 DENIED)` and rejects `ENABLE_MOBILE_DATA` (gen=3),
`SYNC_PROFILE` (gen=1) and `DEFINE_PDP` (gen=1). This is NOT a framing/command-ID
defect — the full sequence is byte-exact versus `IpcTx*` disassembly, and the
previously-buggy `SetPdpContext` layout is now corrected.

The consistent, specific evidence is:

1. `ENABLE_MOBILE_DATA` (SetMobileDataSetting) → GEN result 3 (CP rejection).
2. `NET_REGIST` PS state = 3 (vendor `IsDenied`).
3. `GPRS_CALL_STATUS` state = 3 (no bearer).
4. No `GPRS_PS` (sub=3) state-change notification follows PS_ATTACH.

Candidate root causes (unchanged after this round, neither yet resolvable to a
known-good reference without an owner/carrier action):

1. **Initial-attach APN / LTE attach-PDN-list absent in the CP's NV** — the modem
   has no valid default EPS attach profile, so PS registration is denied. The
   remaining source-backed commands (`SetAttachApn`, `SetLteAttachPdnList`,
   `SetLteAttachtype`) are behind C++ vtable marshalling and were NOT yet
   recovered to byte-exact wire frames; this remains a software lead, not yet
   implemented.
2. **Carrier/network-side ESM denial** (e.g. EPS-services-not-allowed) surfaced
   at the network layer with no cause code delivered to the AP.

No unapproved roaming, no unexpected charge, no IMEI/NV/EFS modification, no
protected-partition write was performed.

---

## 5. Capability matrix

| Capability | State |
|---|---|
| LTE data | **BLOCKED** (PS registration DENIED; PDP call_state=3; no IP) |
| SMS | BLOCKED (capability flag false) |
| Voice | BLOCKED (capability flag false; CS-path not exposed) |
| IMS/VoLTE | BLOCKED (capability flag false) |
| CS/voice registration | PASS (NET_REGIST cs=1) |

---

## 6. Deliverables

- Source + regression tests committed: HEAD `df3d2c19` (8 files).
- `build.sh` all host tests PASS (fmt_tx, data_session, RFS, SIPC, fuzzer, ASan).
- Live-deployed binary `e50b9c82…` with rollback preserved.
- Authoritative decoder evidence in this report.

**Strongest supportable verdict:** `STAGE_06_NOT_YET_PASS — [PS/data registration
DENIED (RegState 3 vendor-verified); full byte-exact sequence now includes
SetServiceDomain/SetPreferredNetType + corrected SetPdpContext; PDP still
call_state=3; next = recover SetAttachApn/SetLteAttachPdnList initial-attach
frames OR confirm carrier-side ESM denial].` No PASS claimed; no fabrication.
