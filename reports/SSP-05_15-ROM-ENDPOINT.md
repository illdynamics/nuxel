# SSP-05_15 — ROM Endpoint Identity & Protocol Analysis

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking
**Question (Section 4):** does the ROM GetVersion probe target the correct domain
and use the correct wire protocol?

## 0. Verdict

The endpoint **selection** (device node) is correct, but the **wire framing**
implemented by the native `--rom-probe` is **inconsistent with, and therefore
does not faithfully reproduce, the vendor boot-ROM GetVersion transaction**.
This is a demonstrated software defect that prevents any ROM response,
independent of the GPS_PWR_EN power gate. It must be corrected before a
physical ROM trial can be meaningfully run.

## 1. What the current probe actually does

`tools/s10plus/ssp-native/nuxel_bbd_flash.c --rom-probe` (rom_identity_probe):

1. Opens `/dev/ttyBCM` (correct — the raw SSI/HSI serial-over-SPI transport).
2. Writes 32 × `0x80` (autobaud) — matches the vendor autobaud intent.
3. Then calls `reliable_rpc(s, RPC_GET_VERSION=0, NULL, 0, 2500)`, which
   **TL-frames** the request:
   `tl_build(wire, seq, F_RELIABLE, rpc=[id=0][len=0], ...)` producing an
   `ESC 0xB0`, SOP `0x00`, seq/size/flags, payload, CRC, `ESC 0xB0 EOP 0x01`
   packet. It then waits for a **TL reliable ACK**.

## 2. What the vendor boot-ROM transaction actually is

`bcm_gps_spi.c → bcm477x_rpc_get_version()` (bcm_gps_regs.c:46-158) sends:

- Transaction 1: raw SSI `tx->cmd = 0x80` + 31 data bytes `0x80` (32 total).
- Transaction 2: raw SSI `tx->cmd = 0x00` (SSI half-duplex write) + 13 data
  bytes `0xB0 0x00 0x00 0x02 0x80 0x03 0x00 0x00 0x00 0x01 0xB1 0xB0 0x01`
  via `bcm_spi_sync()`.

These are **raw SSI frames** (command byte + payload), **not** BBD TL packets.
There is no ESC/SOP/EOP, no CRC, no flags, no reliable-ACK handshake at this
layer. The boot-ROM replies on the same raw SSI return path.

## 3. The demonstrated inconsistency

The native probe **mixes two different protocol stacks**:

| Layer | Vendor boot-ROM path | Native `--rom-probe` |
|---|---|---|
| Autobaud | raw SSI `0x80` × 32 | raw write `0x80` × 32 (ok) |
| GetVersion | raw SSI 14-byte transaction | **BBD TL-framed reliable RPC** |
| Response | raw SSI bytes | TL packet + reliable ACK |

The BBD TL/RPC layer (`bbd_rpc_lh.c`) is the **sensor-hub application** protocol,
not the GNSS boot-ROM protocol. Writing a TL-framed reliable RPC into the
boot-ROM autobaud window will not elicit the raw SSI GetVersion reply that the
vendor code expects.

## 4. RPC id 0 is not demonstrably "GetVersion" in GPL source

`drivers/sensorhub/brcm/bbdpl/bbd_rpc_lh.c` enum:

```
RPC_DEFINITION(IRpcA, A)           // = 0
RPC_DEFINITION(IRpcA, B)           // = 1
...
RPC_DEFINITION(IRpcSensorRequest,  Data)   // = 33
RPC_DEFINITION(IRpcSensorResponse, Data)   // = 34
```

RPC id **0 = `IRpcA.A`** (an abstract lhd-defined RPC), and there is **no
"GetVersion" entry** in the GPL BBD RPC map. The `nuxel_bbd_flash.c` comment
attributes `RPC_GET_VERSION = 0` and the `RPC_MEM_WRITE=5 / START_SCRATCH=46 /
SERVICE_START=55` ids to a "matched lhd" (SHA-256
6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe), which is
**proprietary and not present in this repository**. That attribution is
unverifiable from GPL source and must not be relied upon for the boot-ROM
GetVersion endpoint.

## 5. Correct endpoint / required hardware state

For a valid ROM GetVersion response, TWO conditions must both hold:

1. **GNSS boot-ROM powered**: `GPS_PWR_EN` (gpg0-2/gpio145) HIGH. Live value = 0.
2. **Correct wire transaction**: the raw SSI autobaud + 14-byte GetVersion frame,
   not a TL-framed reliable RPC.

Additionally, the historical evidence (GPS-BLOCKERS.md B0) shows the sensor-hub
MCU itself never answers the kernel hello/chip-ID exchange in Nuxel, because the
stock bring-up (vendor `lhd` patch download via BBD RPC) has no native
equivalent deployed. That is the deeper root cause for a full GNSS fix, but the
**boot-ROM-only GetVersion** is the immediate target of `ROM_GETVERSION` and
depends primarily on conditions 1 and 2.

## 6. Recommended offline correction (no hardware state change)

Correct the `--rom-probe` path to emit the **vendor raw SSI transaction**
verbatim on `/dev/ttyBCM`:

1. Autobaud: write 32 × `0x80`.
2. GetVersion: write the 14-byte raw sequence `0xB0 0x00 0x00 0x02 0x80 0x03
   0x00 0x00 0x00 0x01 0xB1 0xB0 0x01` (the vendor transaction_2nd payload; the
   driver's `bcm_ssi_tx` adds the SSI command byte).
3. Read raw SSI reply bytes (no TL parse) and validate a framed reply.

This is software-only, offline-implementable, and does not require GPS_PWR_EN to
be asserted to be *correct* (it will simply time out read-only until power is
applied). The current TL-framed path should be retained for the sensor-hub
firmware download (`--flash`), which is a different endpoint/protocol.

## 7. Source references

- `bcm_gps_regs.c:46-158` — vendor `bcm477x_rpc_get_version()` (raw SSI autobaud + 14-byte GetVersion).
- `bcm_gps_spi.c:396-458` — `/dev/ttyBCM` `.write` → circ buffer → `bcm_rxtx_work_func`.
- `bcm_gps_spi.c:900-990` — `bcm_rxtx_work_func` wraps user bytes in SSI via `bcm_ssi_tx`; calls `bcm477x_hello()` first.
- `bbd_rpc_lh.c:137-172` — BBD RPC enum: id 0 = `IRpcA.A`, no "GetVersion".
- `tools/s10plus/ssp-native/nuxel_bbd_flash.c:791-846` — current TL-framed ROM probe.
- `docs/hardware/gps/GPS-BLOCKERS.md:B0` — receiver silent even with rail on.

## 8. DEFINITIVE finding — `bcm477x_rpc_get_version()` is orphaned dead code

`grep -rn "bcm477x_rpc_get_version"` across the entire brcm/ directory returns
**only its own definition** (`bcm_gps_regs.c:48`). It has **zero callers**.

- It is exported (in kallsyms) but never invoked in the stock boot path.
- `get_patch_version()` (in `ssp_dev.c:1244`), referenced by `bbd.c`, is an
  UNRELATED symbol that only selects which `bbd_patch` C-array to serve from
  `/dev/bbd_patch` (old/new_old/current). It is NOT a ROM GetVersion.

Therefore the stock GNSS boot-ROM `GetVersion` is performed by the
**proprietary userspace `lhd`** over the BBD RPC layer (`/dev/ttyBCM`,
TL-framed RPC), NOT by the kernel's raw-SSI `bcm477x_rpc_get_version()`, which
is dead/debug code. This has two consequences:

1. The native `--rom-probe` is **correct to use `/dev/ttyBCM` + TL framing**
   (that is the transport the real lhd uses). My earlier concern (Section 3 of
   this report) that raw SSI bytes were required is REFINED: raw SSI is what the
   dead kernel helper used, but the *live* path is TL-framed BBD RPC.

2. The correctness of `RPC_GET_VERSION = 0` depends entirely on the proprietary
   lhd RPC map (SHA 6362e80d…), which is **not present in the repository**. The
   GPL `bbd_rpc_lh.c` enum has id 0 = `IRpcA.A` with no "GetVersion" name. So the
   id-0 attribution is **unsourced from open code** and remains an unverified
   assumption.

## 9. Bottom line for Section 4

The probe targets the **correct transport endpoint** (`/dev/ttyBCM`, the GNSS
boot-ROM BBD RPC path), but its **GetVersion RPC id/framing cannot be
source-verified** without the proprietary lhd. This is now a *documented,
unavoidable reverse-engineering gap*, not a simple framing bug. The remaining
software-only blocker is eliminated by (a) retaining `/dev/ttyBCM` ownership,
(b) asserting GPS_PWR_EN, and (c) reproducing the vendor lhd's actual GetVersion
RPC id/frame — the last of which requires the owner's own `lhd` binary or an
explicitly permitted disassembly.
