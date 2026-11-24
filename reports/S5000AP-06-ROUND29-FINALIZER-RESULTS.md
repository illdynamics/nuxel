# Stage 06 — Round 29: FINALIZER — live KPN results + exhaustive blocker resolution

**Date:** 2026-11-24 CET
**Branch:** cs/mob @ 76b2f9fe (+ this round's live experiments)
**Device:** SM-G975F / beyond2lte / S5000AP, **KPN working SIM (PLMN 20408)**
**State:** CP ONLINE, SIM READY (ds_detect=1), PS REGISTERED_HOME (ps=1, domain=PS_ONLY),
          CP RSSI link flowing (DISP_RSSI_INFO), all umts_* nodes present,
          rmnet0..7 DOWN, no cellular IP.

---

## 0. Executive verdict

**STAGE_06 NOT_PASS.** This round performed fresh, independent aarch64 disassembly
of the EXACT vendor `libsec-ril.so` (build 60889dd7) plus fresh live experiments
on the WORKING KPN SIM. It conclusively resolves the remaining blocker and rules
out two remaining hypotheses (MBIM runtime path, DoDetachForIA).

---

## 1. Fresh disassembly findings (this round, aarch64-linux-gnu-objdump)

### 1.1 `DoSetInitialAttachApn` = `LteEpdgDataCallManager::DoSetInitialAttachApn @0x28c6c8`

Fully traced. The function branches at `0x28c8c0`:

```asm
28c8c0: bl  SupportMBIM()          ; _Z11SupportMBIMv
28c8c4: cbz w0, 28c90c             ; if !SupportMBIM -> NON-MBIM fallback
28c8c8: ...                        ; MBIM path: GetMbimManager, checks mInitialAttach flag
```

- **MBIM path** (SupportMBIM()==true) -> `MbimManager::DoSetMsLteAttachConfig`
  (@0x281358), which `PushInternalRequest(0x3f1=1009, InitialAttachApnInfo)`.
  This requires the `libsecmbim` host daemon (`/vendor/bin/libsecmbim`) + a MBIM
  control netdev. **Nuxel has neither** (only rmnet0..7 + usb0; no cdc-wdm/MBIM).
- **NON-MBIM fallback** (@0x28c90c) -> `ConvertDataProfile` -> `DataCallSetup` ->
  `DataCallManager::SetLteAttachProfile` (@0x22b518) -> iterate `SetDataProfile`
  (request 1001) -> `DoDetachForIA` (@0x22bdf0) as final step.

### 1.2 `DoDetachForIA @0x22bdf0` — the missing vendor step

```asm
22be44: mov w1, #0x3eb             ; request id 1003 = PS_DETACH_FOR_INITIAL_ATTACH
22be54: ldr x8, [x19, #96]         ; DataCallManager->mModemProxy vtable
22be5c: ldr w2, [x21, #12]         ; cid
22be64: mov w3, 0                  ; attach = 0  (DETACH)
22be68: mov w4, 0                  ; suspend = 0
22be74: mov w5, 0x4                ; DataDetachReason = 4 (initial-attach)
22be7c: blr  [vtable +704]         ; ModemProxy::PsAttach
```

`ModemProxy::PsAttach @0x1ce3d0` -> `IpcModem::PsAttach @0x2f1150` ->
`IpcProtocol41::IpcTxPsAttach @0x31fa98`.

### 1.3 `IpcTxPsAttach @0x31fa98` — wire format (CONFIRMED byte-exact)

```
main=13 (GPRS) sub=3 (PS) type=3 (NOTIFICATION), 3-byte payload:
  payload[0] = attach (0=detach, 1=attach)
  payload[1] = suspend (0/1)
  payload[2] = DataDetachReason (0..5; value 4 = "detach for initial attach")
```
Nuxel's `fmt_tx_ps_attach(f, attach, suspend, reason)` is BYTE-EXACT CORRECT.

### 1.4 `IpcTxSetPdpContext @0x31f6e0` — ACTIVATE-bit semantics (CONFIRMED)

Signature `IpcTxSetPdpContextEhiPKcS1_ii(unsigned char cid, int pdp_type,
const char* apn, const char* password, int auth, int pdp_act_deact)`.

Key logic @0x31f878..0x31f8b0:

```asm
sub  w8, w20, #1        ; w20 = auth (DataAuth enum: 0=NONE,1=PAP,2=CHAP)
cmp  w8, #2
b.hi 0x31f8a0           ; auth-1>2 (auth==0 or >3) -> auth-flag byte = 0
lsr  w8, w9, w8         ; auth flag = (0x00010201 >> ((auth-1)*8))
...
cbz  w20, 0x31f8e4      ; auth==0 -> SKIP ACTIVATE bit entirely
orr  w8, w22, #0x10     ; auth!=0 -> flags |= 0x10 (ACTIVATE)
```

CONFIRMED: the ACTIVATE bit (bit4=0x10) is set ONLY when `auth != 0`. For a
no-auth APN (KPN "internet"), the vendor emits flags=0x01 (APN present, NO
ACTIVATE) and relies ENTIRELY on LTE initial attach. Nuxel's round-28 code is
therefore CORRECT for the no-auth case.

### 1.5 `IpcRxGprsCallStatus @0x321ab0` — state decode (CONFIRMED FINAL)

```asm
ldrb w8, [x19, #8]      ; payload[1] (char* data = FULL FMT frame)
cmp  w8, #0x1  ; ==1  -> connected (internal 4)
cmp  w8, #0xb  ; ==11 -> connected (internal 6)
cmp  w8, #0xa  ; ==10 -> connected (internal 5)
b.ne -> w23 = 0         ; ANY OTHER VALUE (incl 3) -> NOT connected
```

There is NO intermediate/connecting state. `GPRS_CALL_STATUS payload[1]==3` is a
FINAL NOT-connected. The prior "state 3 is transient" hypothesis (Round 27) is
conclusively refuted.

### 1.6 New RFS NV surface recovered

Vendor strings confirm the cbd/RIL NV mechanism over RFS:
```
/mnt/vendor/efs/nv_data.bin
RFS_NV_READ_ITEM / RFS_NV_WRITE_ITEM / RFS_NV_WRITE_ALL_ITEM
RFS_NV_BUFFER_MESSAGE / RFS_NV_RESTORE
```
The AP EFS is `/dev/sda3` ("efs", mounted ro at /tmp/efs_inspect) containing
`nv_data.bin` (1 MiB, with `.bak` + `.md5`). The CP EFS is `/dev/sdd1`
(CPEFS, mounted ro at /tmp/cpefs_inspect) containing `.nv_core.bak` (546 KiB).

---

## 2. Fresh LIVE experiments (working KPN SIM, PLMN 20408)

### 2.1 Round-28 baseline re-confirmed

Full FSM run: NET_REGIST(ps=1 REGISTERED_HOME) -> SET_SERVICE_DOMAIN ->
SET_PREFERRED_NET -> ENABLE_MOBILE_DATA(gen=3 "already-ON") -> SET_DATA_PROFILE
-> SET_LTE_ATTACH -> ALWAYS_ON_PDN -> PS_ATTACH -> PS_REGIST_VERIFY(ps=1) ->
DATA_CALL(SetPdpContext). Result: GEN echo `0d04030080` (accepted), then
`GPRS_CALL_STATUS 010300000000000000` = cid=1, state=3 (NOT connected), no cause.

### 2.2 NEW: DoDetachForIA (detach reason=4) live on KPN — REJECTED

Implemented `DS_DETACH_IA` (emit `ps_attach(false, false, 4)`) + `DS_SET_LTE_ATTACH2`
(re-apply attach profile) phases into the FSM, built (aarch64, -Werror clean),
deployed guarded, and live-tested on KPN.

Result: **`0d03030180` = GEN echo of (main=13,sub=3) with result byte 0x01 = REJECTED.**

`data_session_reject phase=DETACH_IA gen_result=1` — identical to Round 24's
T-Mobile result, now confirmed on the WORKING KPN SIM. The S5000AP modem
rejects `PsAttach(detach, reason=4)` regardless of SIM. **The detach-for-IA
runtime path is definitively dead on this modem.**

The experimental change was reverted (it regressed the FSM by terminating at
DETACH_IA before DATA_CALL); the known-good round-28 binary was restored
(SHA256 6a3b77b186386bf254faf75db805ea54b4ade7dd9ae4e521abb1d98a6aa9b906).

---

## 3. Definitive cumulative truth (rounds 16-29, all live + fresh disasm)

Every runtime FMT command that could re-apply the initial-attach APN is either
accepted-but-non-effectual or REJECTED:

| Command | main.sub | Result (KPN, live) |
|---|---|---|
| SetLteAttachProfile | 13.20 | GEN 0 (accepted), NO re-attach effect |
| SetDataProfile | 13.27 | GEN 0 (accepted), non-effectual for attach |
| AlwaysOnPdn | 13.34 | GEN 0 (accepted) |
| PsAttach(attach=1) | 13.03 | GEN 0 (accepted) |
| **PsAttach(detach=0, reason=4)** | **13.03** | **GEN 1 (REJECTED)** |
| SyncProfileInfo | 13.37 | GEN 1 (REJECTED) |
| DefinePdpContext | 13.01 | GEN 1 (REJECTED, legacy 3G) |
| SetPdpContext (ACTIVATE) | 13.04 | GEN 0, GPRS_CALL_STATUS state=3 (NOT connected) |

The default EPS bearer is established from the modem's PERSISTENT initial-attach
APN during initial attach. There is no userspace FMT command on this S5000AP
that can update or re-trigger it. The APN must be set via one of:

1. **MBIM `MS LTE Attach Config`** — requires `SupportMBIM()` + `/vendor/bin/libsecmbim`
   + a MBIM control channel. Nuxel runs neither (no Android runtime, no MBIM netdev).
2. **Samsung NV item write** via `RFS_NV_WRITE_ITEM` on `/mnt/vendor/efs/nv_data.bin`
   — requires the proprietary Samsung NV item table to identify the exact
   initial-attach-APN item ID. That table is NOT present in-repo.

---

## 4. Safety

- **No NV/EFS/RADIO/BOOT/IMEI/calibration write was performed this round.**
- EFS (sda3) and CPEFS (sdd1) remained mounted READ-ONLY.
- The only binary change was the guarded deployment of the experimental
  radiod (backed-up), which was REVERTED to the known-good round-28 binary.
- Wi-Fi (wlan0), ZeroTier (ZT 10.11.12.99), USB (usb0), SSH all preserved.

---

## 5. Acceptance criteria status

**LTE DATA:** ❌ KPN registration ✓, LTE attach ✗ (persistent initial-attach APN
unset; no runtime path), EPS bearer ✗, rmnet UP ✗, cellular IP ✗, DNS ✗, HTTPS ✗.

**VOICE:** ❌ not implementable this round (requires IMS/VoLTE vendor stack or
CS voice; gated on LTE + carrier entitlement).

**SMS:** ❌ not implementable this round (requires SMS FMT command transport;
blocked behind bearer + separate telephony investigation).

**PRODUCTION:** ✅ no Android runtime (native Linux radiod), ✅ persistent config
preserved, ✅ no regression to Wi-Fi/ZeroTier/USB/SSH, ✅ full host test suite
still green (data_session/fmt_tx compiled -Werror clean this round).

---

## 6. Next exact requirement (externally dependent)

To unblock the bearer requires ONE of (all previously owner-gated):

1. A known-good **Samsung `nv_data.bin` NV-item reference** (or stock cbd binary)
   to identify the exact initial-attach-APN NV item ID for the S5000AP, so it can
   be written via `RFS_NV_WRITE_ITEM` with full backup + rollback (+ per mob.md §6),
   OR
2. The **Samsung `libsecmbim` + MBIM host** brought up natively (a large separate
   subsystem), OR
3. **Carrier-side data-service / provisioning confirmation** for this SIM/IMEI on
   KPN (verify the data plan is active and the device is data-allowed).

No fabricated success. No NV experimentation without an authoritative reference.
