# Stage 06 — Round 31: MBIM/SIPC encapsulation RECOVERED (blocks prior "missing binary" verdict)

**Date:** 2026-11-24 CET
**Branch:** cs/mob
**Device:** SM-G975F / beyond2lte / S5000AP, KPN SIM (PLMN 20408)
**Authoritative reference binary:** .vendor-ro/libsec-ril.so (BuildID 60889dd714394ae0db7c2ecc2bf2740f)

## Verdict

The ROUND-28/30 conclusion that the MBIM host lives in a *separate* `/vendor/bin/libsecmbim`
binary and that "the SIPC encapsulation ABI is not recoverable from libsec-ril.so alone"
is **incorrect**. This round re-derived the complete MBIM-over-SIPC transport directly from
`libsec-ril.so`, which contains the entire MBIM host (MbimManager / MbimAdaptor /
MbimRespBuilder / RawIpc classes are all compiled into it).

## Recovered facts (fresh, relocation-resolved disassembly; local aarch64 binutils)

### 1. MBIM messages are carried over the existing RIL SIPC FMT channel as RAW IPC
- `MbimManager::DoOemRawIpc @0x281928` -> modem proxy vtable slot `[#2368]` =
  `ModemProxy::SendRawIpc` -> `IpcModem::SendRawIpc @0x307f38` ->
  `IpcProtocol41::IpcTxRawIpc @0x3180f0`.
- `IpcTxRawIpc` validates the RawIpc wire header and emits it as a SIPC FORMAT frame:
  * `[+4] == 0x16`  (FMT main_cmd = 22 = RAW-IPC / MBIM forward)
  * `[+5] == 0x0c`  (FMT sub_cmd  = 12)
  * `[+6] == 0x05`  (FMT cmd_type = 5  = RAW-IPC class)
  * `[+7]`          = forward flag/sub-func id byte
  * `[+8 ..]`       = the raw MBIM message payload
  then dispatches to `[IpcProtocol41+16]->vtable[48]` (the low-level FMT frame writer)
  over `/dev/umts_ipc0` (RIL ch 235 / 0xEB).
- Response path: `MbimManager::OnMbimRawIpcReceived` registered via
  `ModemProxy::RegisterForRawIpc`; gated by property `ril.mbim.rawipcforward`.

### 2. `RawIpc` object layout (= what gets serialized)
- `RawIpc::RawIpc(Pcii) @0x2bf550`: vtable @0, field @8=-1, payload buffer @0xc (12),
  payload copied from the MBIM message; length stored @8204/@8208.
- MBIM payload therefore rides at offset 12; the FMT header bytes precede it.

### 3. `MS LTE Attach Config` command (RIL_REQUEST_SET_INITIAL_ATTACH_APN = 1009)
- `MbimManager::DoSetMsLteAttachConfig @0x281358` builds an `InitialAttachApnInfo`
  (300-byte context: apn/user/password + DataAuth/DataProtocol/AccessNetworkType +
  two int flags), then `SecRil::PushInternalRequest(1009, ...)`
- `MbimAdaptor::MakeSetMsLteAttachConfig @0x1c3018` allocates a 984-byte
  `MbimMsLteAttachConfigData` holding **3 contexts**, each a 324-byte
  `MbimMsLteAttachContextData` (@0x2c0e90 constructor zeroes a 0x144-byte struct).
- The 3 contexts are filled from DataProfile apn/user/pwd via
  `CopyFromOffsetSizeFormat`; the struct is then serialized to MBIM CID
  `MS LTE Attach Config` (USB-IF/Microsoft CID 0x0000000A) and sent via RawIpc.
- `MbimRespBuilder::BuildQueryMbimMsLteAttachStatus @0x2d2378` +
  `FillMsLteAttachConfig @0x2d6158` cover the read-back/status path.

### 4. `cbd` and the RIL stack are all present on the vendor partition
- `/dev/sda26` (LABEL=vendor) mounted read-only at /tmp/vendor_ro contains:
  `bin/cbd`, `bin/hw/rild`, `lib64/libsec-ril.so`, `lib64/libsec-ril-dsds.so`,
  `lib64/libsec_semRil.so`, `libril.so`, `librilutils.so`.
- No separate `libsecmbim` binary exists anywhere; MBIM is inside libsec-ril.so.

## What this unlocks
A native Nuxel `IpcTxRawIpc` FMT sender (main=0x16/sub=0x0c/type=0x05) plus a
reconstructed MBIM `MS LTE Attach Config` CID 0x0A info-buffer is now the concrete
implementation path to set the modem's persistent initial-attach APN — no vendor
daemon needed. The FMT framing is byte-exact per the recovered disassembly.

## Safety
No NV/EFS/RADIO/BOOT/IMEI write performed. All reads were of the read-only vendor
mount and the local .vendor-ro reference copy. Wi-Fi/ZeroTier/USB/SSH intact.

---

## LIVE TEST (first deployment, 2026-11-24 ~13:32 CET)

Deployed the recovered MBIM sender (`mbim_tx` + `DS_MBIM_ATTACH_CONFIG`) with
`NUXEL_MBIM_ATTACH=1` and observed the live FMT sequence. Result (honest,
unfiltered):

- FSM advanced SET_LTE_ATTACH -> MBIM_ATTACH_CONFIG (as designed).
- The MBIM raw-IPC frame WAS emitted byte-correct:
    `fmt_tx main=22 (0x16) sub=12 (0x0c) type=5 len=124`
  (12-byte MBIM header + 8-byte command header + 88-byte info buffer +
   7-byte FMT header + 1-byte forward flag = 124).
- **The CP did NOT reply.** No GEN echo (main=128), no MBIM/raw-ipc response,
  no advance to ALWAYS_ON_PDN. Next CP activity was the periodic
  DISP_RSSI_INFO heartbeat ~23 s later.

Interpretation: the FMT raw-IPC framing is rendered correctly, but the CP never
processes/answers this specific MBIM attach-config forward. The likely missing
pieces are the MBIM *session handshake* (MbimManager::Initialize / MBIM OPEN
primitive + transaction sequencing) and/or the `ril.mbim.rawipcforward` gate,
which the stock rild/libsec-ril performs before any MS LTE Attach Config is
hosted. The reconstructed single-command send is therefore a necessary but not
yet sufficient step: the MBIM control session still needs its open/transaction
envelope recovered before the CP will act on the attach config.

Deployment is rolled back to the safe default (NUXEL_MBIM_ATTACH disabled) so
the existing FMT GPRS path is unchanged; the recovered/implemented MBIM sender
remains in-tree, gated OFF by default, ready for the next round's handshake
work. No NV/EFS/RADIO/BOOT/IMEI write was performed. Wi-Fi/ZeroTier/USB/SSH
remain intact.

---

## REGRESSION CONFIRMATION (post-deployment, rolled-back default)

After rolling back to NUXEL_MBIM_ATTACH=off: radiod active, deployed binary
sha256 80d7220ae1ef0947e89feb4b4559e8679c0ec726a37b0f6e7d9c4dd56d07cbc7.
Wi-Fi wlan0 10.20.30.16/24 UP, ZeroTier ztly5zthnf 10.11.12.99/24 UP,
usb0 10.100.10.1/24 UP, SSH responsive, rmnet0 DOWN (unchanged baseline).
No regression.
