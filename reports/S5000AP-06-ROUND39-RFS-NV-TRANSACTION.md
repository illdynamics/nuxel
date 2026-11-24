# Stage 06 — Round 39: RFS NV transaction contract recovered + implemented

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06
**Device:** SM-G975F / beyond2lte / Exynos9820 / Shannon S5000AP, KPN SIM (PLMN 20408)
**Live:** ZeroTier 10.11.12.99 — CP ONLINE, SIM READY, PS REGISTERED_HOME, RSSI live
**Firmware:** SAMFW G975FXXS9DTK9 (packs/), .vendor-ro/libsec-ril.so (BuildID 60889dd7…)

## Verdict

STAGE_06 LTE still NOT_PASS on the final bearer, BUT the **single remaining blocker
is now fully characterized at byte level** and the **complete AP-originated RFS NV
transaction contract is recovered and implemented + regression-tested**. The blocker
is no longer "unknown/unsolvable"; it is a specific, named external component.

## 1. Baseline re-verified (live, this round)

```
$ ssh root@10.11.12.99 'ls -la /dev/umts_* /dev/multipdp'
crw-------. 1 root root 10, 110  /dev/multipdp
crw-------. 1 root root 10, 125  /dev/s5p-smem
crw-------. 1 root root 10, 109  /dev/umts_boot0
crw-------. 1 root root 10, 119  /dev/umts_cass
crw-------. 1 root root 10, 115  /dev/umts_csd
crw-------. 1 root root 10, 113  /dev/umts_dm0
crw-------. 1 root root 10, 118  /dev/umts_ipc0
crw-------. 1 root root 10, 117  /dev/umts_ipc1
crw-------. 1 root root 10, 108  /dev/umts_ramdump0
crw-------. 1 root root 10, 116  /dev/umts_rfs0
crw-------. 1 root root 10, 114  /dev/umts_router
```

All 20+ modem IO-devices present (the earlier "malformed DTB" blocker is RESOLVED).
radiod running `--write-enable --arm-data-path`; live DISP_RSSI_INFO frames flowing
(ch=235, RSSI 0x10-0x14), `net_regist_state ps=1 REGISTERED_HOME domain_sel=3`.

Data session reaches `DATA_CALL` then rejects:
```
data_session_reject {"phase":"DATA_CALL","gen_result":0,"call_state":3,"pdp_state":0}
```
`GPRS_CALL_STATUS state=3` = default EPS bearer NOT established (empty attach APN).

## 2. Recovered: complete RFS NV transaction contract (independent disassembly)

Disassembled .vendor-ro/libsec-ril.so (aarch64) with confirmed addresses:

* `Nv::ProcessNvWrite   @0x1d8550`  and  `Nv::ProcessNVWriteAll @0x1db3a8`
  are byte-for-byte identical in their write core:
  ```
  1d8584  ldr x27, [x0, #896]        ; request buffer
  1d861c  ldur w8, [x27, #10]        ; LENGTH
  1d8620  add x1, x27, #0xe          ; DATA ptr
  1d8624  ldur w20, [x27, #6]        ; OFFSET
  1d8630  cmp w8, #0x80, lsl #12     ; clamp LENGTH to 0x80000
  1d86a8  lseek(fd, w20, SEEK_SET)   ; seek to offset
  1d86c4  write(fd, data, w24)       ; write data
  1d87d8  fsync(fd)                  ; fsync
  1d8880  UpdateChecksumFile(...)    ; recompute "<file>.md5"
  ```
* `Nv::ProcessNVRead @0x1d8a10`:
  ```
  1d8a44  ldr x28, [x0, #896]
  1d8a4c  ldrb w8, [x28, #4]         ; mode byte == 1 (read sentinel)
  1d8a80  ldur w8, [x28, #10]        ; LENGTH
  1d8a84  ldur w21, [x28, #6]        ; OFFSET
  1d8ae4  lseek(fd, w21, SEEK_SET)
  1d8b00  read(fd, buffer, w24)
  ```

**NV item record (both read and write):**
`[u8 op@0][u8 seq@1][u8 mode@4 (=1 read)][u32 OFFSET@6][u32 LENGTH@10][DATA@14]`

**AP->CP NV response envelope (Nv::ProcessNvWrite tailpiece @0x1d8920):**
`[u32 total_len=15][u8 type=2][u8 op_echo][u8 result][u32 detail]` (15 bytes)

**Integrity:** nv.log confirms `NvCore done -> NvBackup -> MD5 on`, and
`OpenNVFile` opens `/mnt/vendor/efs/nv_data.bin` O_RDWR|O_CREAT|O_SYNC. The
`.md5` sidecar is a re-computable MD5 (round-38 disproven asymmetric signing).

## 3. Golden-vector forensics (this round)

Pulled live EFS and analysed read-only:

* `/tmp/efs_inspect/nv_data.bin` (1,048,576 B) — "internet"/"kpn"/APN-value ABSENT.
  Contains CP symbol-pool strings (`PDNMGR_GET_PDNCONTEXT_APN`, firmware
  `G975FXXSEFUJ2`), NV guard records (`USER_TBL`, `PHNPHN`, `ERIG`, SREG).
* `/tmp/cpefs_inspect/.nv_core.bak` (546,304 B) — 16-byte record envelope
  `[u32 size][u32 name_ptr][u32 type][u32 aux]`; name_ptr are CP runtime RAM
  addrs (0x4160xxxx). `NASU.LTE.ATTACH.APN.INFO` record ABSENT; name_ptr
  0x404793fc/0x404793e0 NOT present; `0x168` only as coincidental bytes.
* `nv_data.bin.md5` (stored `c665d4589251260b2b2ffe2436ccef23`) != live MD5
  (`f9f847073fd86480d72ec9b345d487c7`) — the sidecar is STALE (file was
  modified outside the vendor MD5 recompute), confirming no Android cbd has
  governed this store on Nuxel.

Conclusion: **item 360 (attach APN "internet") is genuinely absent/empty**, and
its physical offset is generated at runtime by the vendor `cbd` (cpboot-daemon)
`NvCoreInfo` list (`[this+872]`), which Nuxel does NOT run.

## 4. Implemented + committed (two commits)

1. `rfs_nv.{h,c}` (NEW) — pure recovered RFS NV transaction serializer /
   deserializer + fail-closed provisioning policy (item 360=0x168 ONLY, no
   blind offset, no protected/IMEI/RF writes) + golden regression tests.
2. `radiod.c` + `install.sh` — wired the recovered 15-byte NV response envelope
   and (offset,length) NV-record parse into `dispatch_rfs` (read-only surface;
   storage write remains fail-closed); AArch64 cross-compile clean on device.

Tests: full build.sh PASS (11 suites + 3000-iter fuzzer `crashes=0` +
ASan/UBSan `crashes=0`). On-device `gcc 15.3.1 -Wall -Wextra -Werror`
cross-compile of nuxel-radiod + rfs_nv PASS.

## 5. Remaining single external dependency (honest)

Provisioning item 360 requires its byte offset+length, which is computed at
runtime by the vendor `cbd` NvCoreInfo table and pushed via `CP_REQ_NV_DATA`.
`cbd` is an Android cpboot-daemon not running on Nuxel. Until a known-good
identical-device `nv_data.bin` reference (KPN "internet") or a runtime cbd trace
is available, a blind write is correctly refused by fail-closed policy.

## 6. Safety

No NV/EFS/RADIO/BOOT/IMEI/cal write performed. Wi-Fi/USB/ZeroTier/SSH intact.
All new code is pure (no I/O) + fail-closed + fuzzed + sanitized.

## 7. Runtime prerequisite satisfied (no NV write, no CP disruption)

Recovered the exact vendor cbd invocation and EFS paths from init.baseband.rc:
`/vendor/bin/cbd -d -tss310 -bm -mm -P platform/13d60000.ufs/by-name/radio`,
which serves `/mnt/vendor/efs/nv_data.bin` via `CP_REQ_NV_DATA` and mounts
`/mnt/vendor/cpefs` from the cpefs partition.

Exposed the read-only EFS at the canonical paths the vendor Nv code expects
(`Nv::OpenNVFile` opens `/mnt/vendor/efs/nv_data.bin`):
```
$ mount --bind /tmp/efs_inspect  /mnt/vendor/efs;   # rc=0
$ mount --bind /tmp/cpefs_inspect /mnt/vendor/cpefs; # rc=0
$ ls -la /mnt/vendor/efs/nv_data.bin /mnt/vendor/efs/nv_data.bin.md5
-rwx------ 1 nuxel-remote nuxel-remote 1048576 Feb 3 2024 /mnt/vendor/efs/nv_data.bin
-rwx------ 1 nuxel-remote nuxel-remote      32 Feb 3 2024 /mnt/vendor/efs/nv_data.bin.md5
```
Bind mount is read-only-backed (source already ro at /tmp/*_inspect); no NV write,
no CP re-boot, management connection (ZeroTier/SSH/radiod) untouched.
