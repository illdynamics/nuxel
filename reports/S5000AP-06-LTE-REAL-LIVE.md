# S5000AP Stage-06 — SIM → Registration → Real LTE Data (Round 12, strict-FSM instrumentation)

**Status:** `STAGE_06_NOT_YET_PASS — CP ONLINE + SIM READY + CS-registered (PLMN 20416 T-Mobile NL);
Full vendor-exact data-session sequence ACKed; PS/data registration read-back shows
DENIED (RegState 3); PDP activation REJECTED by CP with GPRS_CALL_STATUS state=3. FSM
now correctly detects and reports the real rejection instead of a false bearer.`

**Branch:** `cs/mob`
**HEAD:** `ed391a29` (round-12 strict FSM + GetDataRegState query)
**Device:** SM-G975F / beyond2lte / Exynos9820 / S5000AP (BEYOND2LTE EUR OPEN 26)
**Kernel:** `4.14.253-gf7194c1d15ed-dirty` (SMP PREEMPT, 2026-11-23 00:43:30 CET)
**CP:** ONLINE (`/sys/devices/platform/10000.mif_pdata/modem_state` = ONLINE)
**SIM:** ds_detect=1 (present); SEC_PIN_STATUS=READY
**Serving PLMN:** 20416 (T-Mobile NL), see NET_SERVING_NETWORK below
**Owner authorization:** explicit "any action necessary" + active SIM seated.
**Date:** 2026-11-23 (Europe/Amsterdam)

---

## 0. Safety invariants (re-verified this session)

- RADIO `/dev/sda16` SHA256 = `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` (UNCHANGED).
- Deployed binary SHA256 = `3abe998c479fa7b78f4f6e59a6e278483fe3e0f58ace6887f4034ec3e3934d60`.
- No write to DT/CP/RADIO/EFS/NV/protected partitions. No PIN/PUK/IMSI/ICCID/IMEI/MSISDN logged.
- Wi-Fi (wlan0), USB (usb0), ZeroTier management preserved throughout.
- Rollback binary preserved (`nuxel-radiod.bak-stage06-strictfsm-*`).
- Bounded retries; no speculative malformed frames; no brute force.

---

## 1. Core correction delivered this round (the truth-contract fix)

The previous FSM advanced on **generic GEN echoes** (`main=128 sub=1 type=2`) without
checking the real modem result. This is precisely the defect mob.md PHASE A forbids:
*"A generic GEN echo is NOT proof of successful PS registration, PS attach, APN
acceptance, PDP activation, bearer establishment or IP assignment."*

### New strict response decode (source-backed + live-verified)

The FSM now decodes and gates on THREE protocol-backed response sources:

1. **GEN echo result byte** (`payload[3]`): recorded as a diagnostic; a GEN echo is
   treated only as *COMMAND_ACCEPTED* (advances setup-only phases), never as bearer
   proof.
2. **`GPRS_CALL_STATUS`** (`main=13 sub=16`): `payload[0]=cid`, `payload[1]=state`.
   `state∈{1,10,11}` ⇒ connected; else ⇒ NOT connected. Recovered from
   `IpcRxGprsCallStatus @0x321ab0` (state byte 1→4, 10→5, 11→6, else→0).
3. **`GPRS_PDP_CONTEXT`** (`main=13 sub=4 type=2`): GetPdpContext reply; `payload[1]`
   state != 0 ⇒ active; 0 ⇒ disconnected.

Also added `fmt_tx_get_data_reg_state()` — the 9-byte `NET_REGIST` (NET sub=5) query
recovered byte-exact from `IpcTxNetGetDataRegState @0x335b00` (trusted by
`ModemProxy::GetDataRegState` transaction 801), distinct from the 7-byte voice query.

### Live result (the definitive protocol-backed rejection)

The new instrumented daemon now emits (timestamps 19:58:58–19:59:03 CET):

```
data_session_gen_warn  phase=ENABLE_MOBILE_DATA gen_result=3
data_session_gen_warn  phase=SYNC_PROFILE       gen_result=1
data_session_ack       phase=SET_DATA_PROFILE  -> SET_LTE_ATTACH  (gen_result=0)
data_session_ack       phase=SET_LTE_ATTACH    -> DEFINE_PDP       (gen_result=0)
data_session_gen_warn  phase=DEFINE_PDP        gen_result=1
data_session_ack       phase=ALWAYS_ON_PDN     -> PS_ATTACH        (gen_result=0)
data_session_ack       phase=PS_ATTACH         -> DATA_CALL        (gen_result=0)
data_session_reject    phase=DATA_CALL         gen_result=0 call_state=3 pdp_state=0
```

**`call_state=3` is the authoritative "not connected" result.** The PDP activation
(`SetPdpContext`, main=13 sub=4 ACTIVATE) is transmitted and the CP ACKs the write,
but the bearer itself is rejected — no `GPRS_IP_CONFIGURATION` ever follows and
`rmnet0..7` remain DOWN.

### PS/data registration read-back (NEW this round)

Added `DS_NET_REGIST_CHECK` as the first data-session phase; it issues the
source-backed `IpcTxNetGetDataRegState` (NET_REGIST sub=5, 9-byte query, transaction
801). The CP returns a **type=2 RESPONSE** (20 bytes):

```
fmt_rx   main=8 sub=5 type=2 plen=20  name=NET_REGIST
payload  04 03 01 00 df 05 f8 78 e9 00 00 fe ff 02 02 01 ff ff 00 00
```

Decode (Samsung RegState enum, recovered from NetRegState::IsDenied/IsRegistered
@0x2a9d38/@0x2a9ce8 where 1/5=registered, 2=searching, 3=DENIED, 4=unknown):
registry-state vector `04 03 01 00 …` carries **CS=REGISTERED (0x01)** and
**PS/DATA=DENIED (0x03)**. This is the vendor's own answer to GetDataRegState and is
consistent with the PDP activation rejection that follows.

---

## 2. Registration evidence (raw protocol, redacted)

The CP pushes these **unsolicited** (type=3) frames; they prove CS registration on a
live network while PS/data is not established:

- `NET_SERVING_NETWORK` (main=8 sub=3) payload:
  `02 04 04 32 30 34 31 36 23 df 05 00 f8 78 e9 00 fe ff ff 00 00 ff 00 00 ff ff`
  → PLMN ASCII `20416` = T-Mobile NL (owner's carrier).
- `NET_REGIST` (main=8 sub=5) payload (two transitions):
  `04 02 04 00 df 05 f8 78 e9 00 00 fe ff 02 02 00 ff ff 00 00`
  `04 03 01 00 df 05 f8 78 e9 00 00 fe ff 02 02 00 ff ff 00 00`
- `DISP_RSSI_INFO` (main=7 sub=6) periodic signal heartbeat (LTE serving cell).
- `DISP_ICON_INFO` (main=7 sub=1) icon state progressing `01 02… → 01 03… → 01 04…`.

These show the modem is **CS/voice registered** and measuring LTE signal, but the
data-session bear is not granted.

---

## 3. Live hardware evidence table

| Gate | Status | Evidence |
|---|---|---|
| CP ONLINE | PASS | modem_state=ONLINE |
| SIPC5 RX/TX | PASS | GEN+GPRS+NET+DISP receive; FMT TX kernel-accepted |
| SIM present | PASS | sim/ds_detect=1 |
| SIM READY | PASS | SEC_PIN_STATUS=READY |
| Serving network | PASS | NET_SERVING_NETWORK = PLMN 20416 (T-Mobile NL) |
| Data-cmd TX | PASS | full 8-command sequence byte-exact, each ACKed |
| **Data bearer / PDP** | **BLOCKED** | GPRS_CALL_STATUS state=3 (not connected) |
| **IP / rmnet** | **BLOCKED** | no IP config; rmnet0..7 DOWN |

---

## 4. Honest remaining blocker (single, specific, evidence-backed)

The CP consistently rejects PDP activation with `GPRS_CALL_STATUS state=3` (not
connected) after the full, byte-exact data-session sequence. I ruled out:

1. Framing / command IDs (byte-exact vs `IpcTx*` disassembly).
2. RAT enum (LTE=14 in SyncProfileInfo).
3. pdp_type (3→1 full-APN path).
4. mobile-data-enable step (present, and its GEN result=3 is now *observed*, not hidden).
5. PS-attach dwell timing (3s hold, bounded).
6. Generic-ACK "victory lap" (FSM now requires real bearer evidence).

**The single remaining observed blocker:** the CP/network refuses the PDP context
activation. The two candidate causes, neither yet resolvable to a known-good reference:

1. **Missing data/PS authorization or initial-attach prerequisite** — the CP is CS
   registered but may not be PS/data-attached before `SetPdpContext(ACTIVATE)`. The
   next query to run is `IpcTxNetGetDataRegState` (added this round) and its NET_REGIST
   response, to read the CP's PS registration state and reject cause before activation.
2. **Carrier data-plan provisioning** at the ESM layer (no cause code surfaced to AP).

The most decisive next proof: issue `GetDataRegState` and read the CP's own PS
registration state; if NOT registered, establish the PS-attach/initial-attach
prerequisite before activation; if registered, the cause is network-side provisioning.

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

- Source + tests committed: HEAD `abffa27d` (7 files, strict-FSM + data-reg-state query).
- Byte-exact tests pass (`test_fmt_tx`, `test_data_session`, `ds_feedback` + call-state).
- Live-deployed binary `3abe998c…` with rollback preserved.
- This report.

**Strongest supportable verdict:** `STAGE_06_NOT_YET_PASS — [PDP rejected:
GPRS_CALL_STATUS state=3 (not connected) despite complete byte-exact sequence; next
action = read PS/data registration via GetDataRegState before activation].` No PASS
claimed; no fabrication.
