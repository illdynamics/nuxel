# SSP-05_16 — ROM vs RPC Protocol Resolution

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Verdict

The prior "RPC identity confusion" is **resolved with authoritative evidence**. The
confusion was a mix of three distinct notions: (a) the kernel's raw-SSI boot-ROM DEBUG
helper, (b) the kernel's opaque BBD RPC enum, and (c) the live lhd TL-framed reliable
RPC. They are now cleanly separated, and one genuine native defect (version-response
id) is fixed.

## 1. Protocol matrix

| Target | State | Transport | Framing | GetVersion request id | GetVersion response id | Evidence |
|---|---|---|---|---|---|---|
| Boot-ROM (dead kernel helper) | pre-MCU, raw SSI | raw SPI (bcm_ssi_tx) | raw SSI cmd byte + 13B TL body, internal flags | n/a (SSI `0x80` autobaud + `0x00` stream) | raw SSI bytes | `bcm_gps_regs.c:46 bcm477x_rpc_get_version()` — **zero callers** |
| Sensor-hub app (live lhd) | MCU running (patch loaded) | `/dev/ttyBCM` | TL-reliable (ESC/SOP/EOP + CRC-8 + seq + flags) | **RPC id 0, empty** | **RPC id 3, 3×LE32** | lhd disasm `inspect_lhd_init.py` + `test_lhd_response.py` |
| GNSS app running | after ServiceStart | `/dev/ttyBCM` | TL-reliable | (patch + GNSS RPCs, proprietary) | id 3/59/etc | lhd disasm (OUT OF SCOPE for Stage 06) |
| Sensor-hub patch download | after autobaud + sync | `/dev/ttyBCM` | TL-reliable MemoryWrite id 5 | — | reliable ACK | lhd `memory_write_encoder=0x3d60c`, RPC id 5 |

## 2. The definitive RPC id split (request vs response)

From the hash-bound lhd decoder (`VA 0x3d1a8..0x3d364`, dispatch target at
relocation `0x48ae0` = `0x3d1a8`):

- **RPC id 0** is the GetVersion **REQUEST** the host sends (empty body). lhd
  serialises it in the initializer state transition `7/14 -> 8/15`; the internal-sync
  analysis records `RPC ID 0 empty body; reliable enqueue; timer 250ms`.
- **RPC id 3** is the GetVersion **RESPONSE** (body = 3 × LE32). lhd stores `w1` at
  metadata offset 2320 (the version/ASIC comparison slot) and latches `w2` as the
  "original version" when it is not `0xffffffff`.
- The unit test `test_unknown_ids_and_nonversion_response` in `test_lhd_response.py`
  lists `0,1,2,4,5,58,...` as IDs that DO NOT invoke the version callback, and only
  id 3 does.

The kernel GPL enum `bbd_rpc_lh.c` names these `IRpcA.A` (=0) and `IRpcB.A` (=3);
those are opaque placeholder names — the *semantic* "GetVersion req/resp" mapping is
owned by the proprietary lhd, now recovered above.

## 3. Demonstrated native defect + fix

`tools/s10plus/ssp-native/nuxel_bbd_flash.c on_pkt()` previously tested the reply
against `RPC_GET_VERSION` (=0), i.e. it would only "see" a version reply if the
firmware echoed the *request* id. The live firmware replies with id 3.

Fix (this mission):
- Added `#define RPC_GET_VERSION_RESPONSE 3`.
- `on_pkt()` now sets `got_version` only when `v.id == RPC_GET_VERSION_RESPONSE` (3).
- `RPC_GET_VERSION 0` retained for the request.
- Added regression `test_getversion_request_response_id_separation` (id 0 does not
  classify, id 3 does with `version_w0` = first LE32).
- All offline regression suites re-run: PASS.

## 4. ROM probe correctness against the live path

`--rom-probe` correctly:
1. Opens `/dev/ttyBCM` (the live lhd transport, TL-framed — NOT the dead raw-SSI helper).
2. Autobaud 32 × `0x80` (vendor kernel value), then 36 × `0x80` (lhd `VA 0xdfe4` value)
   as a secondary bounded variant.
3. Sends `reliable_rpc(RPC_GET_VERSION=0, empty)` — matching lhd's reliable RPC id 0.
4. Now decodes the reply as id 3 (the live response semantics).

The dead kernel helper `bcm477x_rpc_get_version()` uses a *different* frame
(`flags=F_EXT|F_INTERNAL|F_IGN_SEQ`, 2 payload bytes `00 00`) that the internal
message router — not the RPC layer — would consume. That is why it is dead/debug code:
it never elicits a GetVersion from the live ROM. The native probe does NOT reproduce
that dead framing; it follows the live lhd path, which is correct.

## 5. Remaining physical gate (unchanged, not a protocol uncertainty)

Even with the correct framing, `/dev/ttyBCM` ROM probe cannot succeed because the
kernel `bcm477x_hello()` gates all SSI I/O on the MCU_REQ/MCU_RESP handshake, and the
hub is currently `shutdown=1 resetting=1` (no firmware). This is a *power/firmware-state*
boundary, not a protocol-identifier ambiguity. See `SSP-05_16-POWER-STATE-MACHINE.md`
and `SSP-05_16-PHYSICAL-TRIAL-DECISION.md`.
