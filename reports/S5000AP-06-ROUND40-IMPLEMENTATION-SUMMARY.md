# Stage 06 — Round 40 Implementation Summary (verified results)

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06
**Device:** SM-G975F / beyond2lte / Exynos9820 / Shannon S5000AP, KPN SIM (PLMN 20408)
**Live:** ZeroTier 10.11.12.99 — CP ONLINE, SIM READY(1), PS REGISTERED_HOME, RSSI live
**BuildID:** libsec-ril.so 60889dd7…, cbd aa0233da…

## What was definitively resolved this round

1. **cbd / NvCoreInfo is NOT the per-item-offset authority.** Independent capstone
   disassembly of the unstripped `.vendor-ro/libsec-ril.so` proved `Nv::ProcessNVRead`
   (@0x1d8a10) and `Nv::ProcessNvWrite` (@0x1d8550) take (offset,length) straight from
   the CP-originated RFS request buffer (`[this+0x380]`). The AP performs bounded
   `lseek/read/write/fsync` only — it never looks up an offset in its own TOC.

2. **Recovered the exact on-wire structures** (byte-exact, cross-checked with the
   source-verified GENERIC RFS envelope that already parses `DELETE_ALL_VIS` correctly):
   - Request: `[u32 len][u8 op@4][u8 seq@5][u32 offset@6][u32 length@10][data@14]`
   - NV_WRITE response: `[u32 len=15][u8 type=2][u8 seq][u8 result][u32 offset][u32 written]`
   - NV_READ  response: `[u32 len=15+n][u8 type=1][u8 seq][u8 result][u32 offset][u32 bytes][data n]`
   - NvCoreInfo 24-byte struct, 32-byte TOC row (`+0x0c` key, `+0x10` type, `+0x14` offset).

3. **Fixed a real byte-layout defect** in the previously committed `rfs_nv_response_build`
   (it emitted type/op/seq/result instead of the vendor's type/seq/result/offset/written).

4. **Shipped a native NV backend** `efs_nv.c/h` (bounded read/write/fsync + RFC1321 MD5
   sidecar, no Android/Bionic dependency, reuses the proven nv_items.c MD5) with
   golden-vector + malformed-input regression tests.

## Verification this round

- Host build.sh: 12 test binaries + 2 fuzzers (3000 iters) + ASan/UBSan → `build+test OK`,
  `crashes=0`.
- AArch64 cross-compile (aarch64-linux-gnu-gcc 15.2, `-Werror`) of test_efs_nv and
  test_rfs_nv → clean.
- On-device gcc 15.3.1 `-Wall -Wextra -Werror` full `nuxel-radiod` link (radiod.c +
  transport + rfs + fmt_tx + data_session + mbim_tx + rfs_nv + efs_nv + nv_items +
  -lsystemd) → exit 0, no warnings.
- Live device unchanged: CP ONLINE, SIM READY, all modem nodes present, Wi-Fi/USB/ZT/SSH
  intact. No NV/EFS/IMEI/RF write performed.

## Honest remaining work (NOT fabricated)

The LTE bearer is STILL not physically established. The CP has never issued an NV_READ/
NV_WRITE in the entire log history — only 13x `DELETE_ALL_VIS` boot markers. Item 360
(initial-attach APN "internet") is absent/empty in live nv_data.bin. Establishing the
default EPS bearer now requires AP-originated provisioning that triggers a CP NV_WRITE
(via the recovered `pal_Security_NV_ITEM_Write("Item 360")` / `SetLteAttachProfile`
persist path), serviced by the now-corrected `radiod` against a writable EFS mount at the
CP-supplied offset. That service trigger and the writable-mount transition are the next
implementation step and were NOT performed this round (they are a controlled provisioning
operation, not research).

`./wonqed4real` is NOT created: it requires physical Stage-06 PASS (LTE bearer + SMS +
voice), which is not yet demonstrated.

## Truthful objective state

- NvCoreInfo/offset-mapping blocker: RESOLVED (proven non-blocker; CP supplies offsets).
- NV transaction byte contract: CORRECTED and regression-tested.
- Native EFS NV backend: IMPLEMENTED and tested (not yet exercised against live EFS).
- LTE default bearer: NOT YET PASS (requires the provisioning trigger + writable EFS step).
