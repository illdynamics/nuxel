# S5000AP Stage-06 — SIM → Registration → Real LTE Data (Round 10+, live integration)

**Status:** `STAGE_06_NOT_YET_PASS — full vendor-exact data-session sequence live-verified
and ACKed by the CP, but the PDP activation is rejected with a decoded DISCONNECTED state
(no bearer/IP).`

**Branch:** `cs/mob`
**HEAD:** `fc95f7e1` (this session; parent `6981f7b1`, `0f5eeb74` at start).
**Device:** SM-G975F / beyond2lte / Exynos9820 / S5000AP (BEYOND2LTE EUR OPEN 26).
**Kernel:** `4.14.253-gf7194c1d15ed-dirty` (SMP PREEMPT, 2026-11-23 00:43:30 CET).
**CP:** ONLINE (sysfs `/sys/devices/platform/10000.mif_pdata/modem_state`).
**SIM:** ds_detect=1 (present); protocol READY observed in prior rounds (serving PLMN 20416 = T-Mobile NL).
**Owner authorisation:** explicit "any action necessary" + active SIM seated on-device.
**Date:** 2026-11-23 (Europe/Amsterdam).

---

## 0. Safety invariants (all VERIFIED this session)

- RADIO `/dev/sda16` SHA256 = `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` (UNCHANGED).
- No write to DT/CP/RADIO/EFS/NV/protected partitions.
- No PIN/PUK/IMSI/ICCID/IMEI/MSISDN captured or logged (logs redact identifiers).
- Wi-Fi (wlan0 10.20.30.16) + USB (usb0 10.100.10.1) + ZeroTier (10.11.12.99) management preserved throughout.
- Reversible userspace deployment: new binary `b5f26f63…`/`850b4095…`; rollback saved at
  `/usr/libexec/nuxel/nuxel-radiod.bak-stage06` (sha `e0b9780e…`), deployed hash replaced again.
- Bounded retries (max 3 per phase, no brute force, no speculative malformed frames).

---

## 1. What was accomplished this session (all source-backed + live-verified)

1. **Decoded GEN response semantics:** uniform `0x80` final byte across all 7 data-path
   commands = *generic completion ACK*, not per-command success/failure. Because the
   mobile-data command provably yields a NET_REGIST follow-up with the same 0x80, 0x80
   is the "accepted/processing" marker. A following data-plane response is required for
   truth.

2. **Completed SetDataProfile (sub=27, 203B)** — recovered the previously-zero tail:
   `payload[187]`=auth flag, `payload[189]`=pco flag, `payload[190..195]`=three carrier
   ints (0/default). Auth code NONE=1. (IpcTxSetDataProfile @0x31ff48.)

3. **Implemented SetLteAttachProfile (sub=20, 201B)** — full 194-byte payload + FSM phase.
   (IpcTxSetLteAttachProfile @0x320238.)

4. **Replaced the WRONG CDMA SetDataCallEstablish (main=3/sub=2) with the REAL GPRS
   SetPdpContext (main=13/sub=4, type=3, 112B) PDP-activation command.**
   (IpcTxSetPdpContext @0x31f6e0.)

5. **Implemented SyncProfileInfo (sub=37, 326B)** full-profile sync (incl. RAT) —
   replaces the too-simple 9-byte SetMobileDataSetting as the mobile-data step.
   (IpcTxSyncProfileInfo @0x31fb48.)

6. **Added GetPdpContextList query (sub=4, type=2)** after activation to fetch IP config.
   (IpcTxGetPdpContext @0x31f928.)

7. **Live-verified the FULL corrected sequence executes and ACKs on hardware:**
   `SyncProfileInfo(37) → SetDataProfile(27) → SetLteAttachProfile(20) →
    DefinePdpContext(1) → AlwaysOnPdn(34) → PsAttach(3) → SetPdpContext(4,ACTIVATE)
    → GetPdpContextList(4,query)`.

---

## 2. Live hardware evidence (VERIFIED, this session)

| Stage | Status | Evidence |
|---|---|---|
| CP ONLINE | PASS | modem_state=ONLINE |
| SIPC5 RX | PASS | DISP_ICON_INFO/RSSI periodic; GEN + GPRS responses |
| SIM present | PASS | sim/ds_detect=1 |
| SIM READY (protocol) | PASS (prior) | SEC_PIN_STATUS=READY + serving PLMN 20416 |
| Registration | PASS (prior) | NET_REGIST observed; RSSI present (~-77 dBm) |
| Data-session command TX | PASS | all 7 commands `fmt_tx` logged, kernel-accepted |
| Data-session ACK | PASS | GEN (128) echo per command |
| Data call activation | BLOCKED | GPRS_CALL_STATUS state 3 (disconnected) |
| PDP context / IP | BLOCKED | GPRS_PDP_CONTEXT `011400` state 0 (disconnected) |

Live RX decode (redacted):
```
GEN      0d32030080  (SyncProfileInfo echo main13/sub37, ACK)
GEN      0d1b030080  (SetDataProfile echo main13/sub27, ACK)
GEN      0d14030080  (SetLteAttach echo main13/sub20, ACK)
GEN      0d01030180  (DefinePdp echo main13/sub1, ACK)
GEN      0d22030080  (AlwaysOnPdn echo main13/sub34, ACK)
GEN      0d03030080  (PsAttach echo main13/sub3, ACK)
GEN      0d04030080  (SetPdpContext echo main13/sub4, ACK)
GPRS_CALL_STATUS  main13 sub16 plen9  "010300000000000000"  -> cid1 state3 (NOT connected)
GPRS_PDP_CONTEXT  main13 sub4 type2 plen3  "011400"          -> 1 ctx, state0 (DISCONNECTED)
```

rmnet0..7 remain DOWN; no GPRS_IP_CONFIGURATION / CALL_STATUS(connected) arrives.

---

## 3. Genuine remaining blocker (honest)

The CP accepts the entire byte-exact (vendor-disassembly-derived) data-session
sequence, then rejects the PDP activation with a *decoded DISCONNECTED* state
(GPRS_CALL_STATUS payload[1]=3 → internal state 0; GPRS_PDP_CONTEXT payload[2]=0).

Two candidate root causes (neither yet proven against a known-good live reference):
  1. **Carrier data plan not provisioned/active on this SIM** — the network rejects the
     activation (classic "data plan inactive / APN not authorised" behaviour).
  2. **A remaining undecoded profile requirement** — the exact `RadioTechnologyType` /
     `AccessNetworkType` enum values and the three `int` tail args in SyncProfileInfo/
     SetDataProfile are carrier-dependent and were emitted as their zero/unspecified
     default because their exact enum selects are not fully recoverable from the
     read-only `libsec-ril.so` alone (no paired AP+CP config source).

No IP/DNS/HTTPS/disconnect/reconnect/airplane tests can be run until a bearer exists.

---

## 4. Capability matrix

| Capability | State |
|---|---|
| LTE data | BLOCKED (PDP activation rejected by CP/carrier: DISCONNECTED) |
| SMS | BLOCKED (capability flag false) |
| Voice | BLOCKED (capability flag false) |
| IMS/VoLTE | BLOCKED (capability flag false) |
| Registration | PASS (voice/data service registered; PS attach/data call fails) |

---

## 5. System health (observed)

- Load average ~13.5, 8170 zombie (`<defunct> python3`) processes, `nuxel-bridge/api.py`
  PID 6784 consuming CPU. This predates and is not caused by the modem data path (which
  has no active bearer), but is recorded as an acceptance-relevant health item to fix.
- Memory healthy (5.7 GB available of 7.4 GB).

---

## 6. Deliverables

- Source + byte-exact tests committed: `git log` HEAD `fc95f7e1` (and parent `6981f7b1`).
- Full protocol decode doc: `tools/s10plus/s5000ap-06/docs/DATA_CALL_PROTOCOL_DECODE.md`.
- Rollback binary preserved: `/usr/libexec/nuxel/nuxel-radiod.bak-stage06`.
- This report.

**Strongest supportable verdict:** `STAGE_06_NOT_YET_PASS — [data call rejected: PDP
activation returns DISCONNECTED (cause 3 / state 0); most likely carrier data-plan
provisioning or remaining undecoded RAT enum]`. Not fabricated; no PASS claimed.
