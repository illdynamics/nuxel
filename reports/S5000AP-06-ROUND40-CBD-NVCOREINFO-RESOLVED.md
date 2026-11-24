# Stage 06 — Round 40: CBD/NvCoreInfo dependency RESOLVED via independent disassembly

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06
**Device:** SM-G975F / beyond2lte / Exynos9820 / Shannon S5000AP, KPN SIM (PLMN 20408)
**Live:** ZeroTier 10.11.12.99 — CP ONLINE, SIM READY(1), PS REGISTERED_HOME, RSSI live
**Firmware:** SAMFW G975FXXS9DTK9 (.vendor-ro/libsec-ril.so, BuildID 60889dd7…), cbd BuildID aa0233da…

## Verdict

The round-39 statement "the item-360 physical offset is generated at runtime by the
vendor cbd NvCoreInfo list and cannot be recovered" is **DISPROVEN at byte level**.

Independent AArch64 disassembly (capstone 5.0.7 + pyelftools over the UNSTRIPPED
`.vendor-ro/libsec-ril.so`) proves:

1. **`cbd` / the AP does NOT compute per-item offsets for NV read/write.**
   `Nv::ProcessNVRead` @0x1d8a10 and `Nv::ProcessNvWrite` @0x1d8550 take the
   (offset,length) DIRECTLY from the CP-originated RFS request buffer (`[this+0x380]`,
   i.e. the +896 member) — `ldur w21,[x28,#6]` (offset) and `ldur w8,[x28,#10]`
   (length). The AP performs a bounded `lseek(fd, offset)` + `read/write`, then
   `fsync`, then MD5-update. No AP-side TOC lookup is involved for the data path.

2. **The AP-side TOC machinery (`Nv::InitNvOffset` @0x1d3168, `MakeDefaultCoreInfoList`
   @0x1d3c90, `readTOCRow` @0x1d3da8) is for AP-side NV lifecycle only** (default-NV
   creation, backup/restore, checksum), NOT for per-item read/write. The 32-byte TOC
   row is `[..][+0x0c]=item_key][+0x10]=type][+0x14]=offset_or_size]`; the CP fills it
   at CP boot from its own compiled-in item table.

3. **The CP sends the offset+length to the AP**; the AP never invents it. Our existing
   `rfs_nv.h` contract is therefore CORRECT. The remaining work is not "recover NvCoreInfo"
   but "serve the CP's NV_READ/NV_WRITE requests against nv_data.bin exactly like the
   vendor Nv code does".

## 1. Live baseline (this round)

- CP ONLINE (`/sys/.../modem_state`).
- SIM detect = 1; all 9 modem nodes present (`umts_boot0,cass,csd,dm0,ipc0,ipc1,ramdump0,rfs0,router`).
- wlan0 10.20.30.16, usb0 10.100.10.1, ztly5zthnf 10.11.12.99.
- radiod PID 312649 `--write-enable --arm-data-path`; live DISP_RSSI_INFO (ch235 RSSI 0x10-0x14).
- EFS/CPEFS mounted read-only (/dev/sda3 -> /mnt/vendor/efs, /dev/sdd1 -> /mnt/vendor/cpefs).

## 2. cbd binary identity

- `.forensics/cbd`: ELF64 aarch64 **shared object**, interpreter `/system/bin/linker64`,
  BuildID(sha1)=aa0233da8c71aab8410f42203d93e15e, stripped.
- NEEDED: liblog.so, libcutils.so, libc++.so, libc.so, libm.so, libdl.so.
- Uses `__libc_init` (Bionic), `property_get/set` (libcutils), `android_reboot`.
- **cbd is a Bionic/Android daemon.** It cannot run on glibc Nuxel without a full
  Bionic/linker64 compat layer + Android property service + `u:r:cbd:s0` SELinux +
  /dev/mbin0 symlink. Launching it against an already-initialized CP is forbidden and
  unnecessary — see §3.

## 3. NvCoreInfo struct (definitive)

`Nv::MakeDefaultCoreInfoList` + `NvCoreInfo::NvCoreInfo(int,int)` @0x1d25d0:

```
struct NvCoreInfo {          // sizeof = 0x18 (24 bytes)
    void*  vptr;             // +0x00  (vtable _ZTV10NvCoreInfo @0x39a9b0)
    int    field_08;         // +0x08  (initialized -1)
    int    field_0c;         // +0x0c  (arg1 = item key / name id)
    int    field_10;         // +0x10  (arg2 = offset / size)
};
```

vtable `_ZTV10NvCoreInfo` @0x39a9b0; dtors `NvCoreInfoD1Ev/D0Ev` @0x1d25f0/0x1d25f8.

## 4. TOC row format (definitive)

`Nv::InitNvOffset` @0x1d3168 reads 0x1000 bytes (4096) = 128 × 32-byte rows, loops
0x7f (127) rows; each row 32 bytes. `readTOCRow` @0x1d3da8 decodes:

```
row+0x0c -> out1 (item key / name index)   [stored NvCoreInfo +0x0c]
row+0x10 -> out2 (type code)
row+0x14 -> out3 (offset / size)          [stored NvCoreInfo +0x10]
```

Blank-row test: all bytes must be 0x00 or 0xff (the 0x00..0x1f `ldrb/cmp` chain).

## 5. NV transaction contract (independently re-verified)

Request buffer (`[this+0x380]` = +896):

```
[+0x00] op    (u8)
[+0x01] seq   (u8)
[+0x04] mode  (u8; ==1 for read sentinel)
[+0x06] offset (u32 LE)   <- ldur w21,[x28,#6]
[+0x0a] length (u32 LE)   <- ldur w8,[x28,#10]
[+0x0e] data   (length bytes)
```

AP->CP NV response (built at ProcessNvWrite @0x1d8920 tailpiece; 15 bytes):

```
[+0x00] u32 total_len = 15
[+0x04] u8  type      = 2
[+0x05] u8  op echo   = seq
[+0x06] u8  result    = 0/1
[+0x07] u32 detail    = offset
[+0x0b] u32 detail2   = bytes written / -1
```

(MD5 sidecar recomputed after write via `Nv::UpdateChecksumFile` / `ComputeChecksum`.)

## 6. Why the bearer currently fails (root cause, confirmed)

- The CP has NEVER sent an RFS NV_READ/NV_WRITE in the entire log history — only 13x
  `RFS_OP_UNLINK_FILE("DELETE_ALL_VIS")` boot markers (all correctly answered).
- The live `nv_data.bin` contains NO "internet"/APN value; the attach-APN NV item 360 is
  empty/absent in the CP's persistent store.
- On boot the CP reads item 360 (empty) into its internal attach-APN, so the default EPS
  bearer activate fails with `GPRS_CALL_STATUS state=3` (no default bearer).
- FMT `SetLteAttachProfile` (runtime) does NOT persist to NV; the persistent initial-attach
  APN is NV item 360. radiod currently refuses every NV op (fail-closed), so the APN is
  never provisioned.

## 7. Corrected plan (non-destructive)

1. Extend `radiod` to serve `RFS_OP_NV_READ` and `RFS_OP_NV_WRITE` against
   `/mnt/vendor/efs/nv_data.bin` at the CP-supplied (offset,length), exactly like the
   vendor `Nv::ProcessNvRead`/`ProcessNvWrite` (bounded, offset+length validated,
   fsync, MD5 recompute). Keep everything else fail-closed.
2. Trigger AP-originated provisioning of item 360 = "internet" via the recovered
   `pal_Security_NV_ITEM_Write("Item 360")` / `SetLteAttachProfile` persist path so the
   CP issues the actual NV_WRITE (with its own offset+length). The AP serves it.
3. Mount EFS writable for the provisioning transaction, then return to read-only.
4. Verify read-back, MD5, persistence, CP re-init, and finally the EPS bearer.

No guessed offsets. No blind writes. The offset+length always come from the CP's own
NV request. This removes the cbd/NvCoreInfo dependency as a blocker.

## 8. Safety

No NV/EFS/RADIO/BOOT/IMEI/cal write performed this round. Wi-Fi/USB/ZeroTier/SSH intact.
Analysis is 100% offline (read-only disassembly of already-recovered artifacts).
