# NUXEL SSP — PROMPT 00 MASTER ORCHESTRATOR — STAGE 01 CHECKPOINT

**Date:** 2026-11-22 ~15:45 CET
**Stage completed:** 01 (Read-only live reconciliation + boot/DT immutability seal)
**Next stage:** 02 (forensic patch surgery 0020/0023/0025/0026/0027)

---

## 1. Verified facts (live device + checkout)

### Device (read-only, NO writes)
- **ALIVE**, normal Nuxel boot (not TWRP). SSH `root@10.11.12.99` reachable.
- Kernel: `4.14.253-gf7194c1d15ed-dirty` built Sat Nov 21 12:30:11 CET 2026.
- Deployed patches = **0020 + 0023 ONLY**. kallsyms confirms native bring-up symbols present; **NO `nuxel_ssp_dl_*`** symbols → 0025/0026/0027 NOT deployed (safe).

### Partition map (re-verified, PARTLABEL authoritative)
- `sda12` = dtb (8 MiB), `sda13` = dtbo (8 MiB), `sda14` = boot (55 MiB), `sda15` = recovery (64.5 MiB).
- Historical `sda12/13/14/15` mapping is **exact**. `androidboot.dtbo_idx=9`.

### Immutable hashes
- dtb  `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780`
- dtbo `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23`
- boot `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c`
- recovery `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87`

### Critical boot-image discovery
The live boot image has **appended_dtb_count = 0** — NO appended FDT/DTB tail. DTB/DTBO are external partitions. Therefore BOOT repack = **replace arm64 `Image` only, preserve ramdisk + header byte-for-byte, leave sda12/sda13 untouched**. The verify tool's "no appended FDT" is *expected*, not a defect.

### SSP sensor state (the actual blocker)
- `mcu_name=BCM47752KUB1G`, `mcu_rev=BR0121080900,BR010`, `mcu_reset=OK`.
- `nuxel_hub_diag = mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443`.
- `tx=184 rx=0`: MCU asserts MCU_RESP but returns **zero RX** → no bidirectional ROM traffic.
- accel/gyro raw_data both `0,0,0`. `nuxel-gnss-lhd.service` inactive (good). Orientation daemon running, `auto` correctly blocked as "MCU not streaming".

## 2. Changed / created files
- `reports/SSP-20261122-LIVE-BASELINE.md` (new)
- `reports/SSP-BOOT-DT-IMMUTABILITY-MANIFEST.json` (new)
- `reports/SSP-ROLLBACK-READINESS.md` (new)
- `/tmp/nuxel-ssp-baseline/boot-sda14.img` (host rollback seed, sha verified)
- No device writes, no Git changes (working tree clean).

## 3. Unresolved root cause
MCU halts in reset/shutdown with `rx=0` despite 184B TX. Candidate causes (NOT established): (a) cold-start boot-ROM autobaud window never entered (rail/timing), (b) SPI clock/mode/IRQ electrical fault, (c) protocol/framing mismatch. 0025 (rail cold-cycle) and 0026 (raw-SSI ROM sync) are targeted fixes; 0027 (full downloader) has confirmed safety bugs (below).

## 4. Known 0027 defects to fix in Stage 02 (do NOT flash as-is)
1. **Self-deadlock** in `bbd_do_transfer()` failure path: `pending_mutex` acquired at entry; on failure the original unlock was removed and then `mutex_lock(&data->pending_mutex)` is called again (line 1272) while still held.
2. **Premature parser success**: `dl_next_record()` returns false on truncated/invalid records; the download loop `break`s and accepts `nwrites>0` as sufficient, skipping non-F1 records without strict rejection.
3. **Contiguous `kmalloc`** of ~438,895 B in `dl_decode_blob()` (line 817) — risk of fragmentation failure; needs `vmalloc`/streaming/bounded allocation.
4. **Stale ACK**: session ACK seq bytes not reset before each transaction; wrapped/stale seqs may satisfy later ops.
5. **Protocol claims unverified**: `dl_parse_hex_hdr` treats text `Crc` ambiguously; phase-1/phase-2 acceptances need exact framing/CRC/correlation.
6. **Duplicate content**: 0027 re-introduces 0023 changes against older base; build wrapper treats unmarked patches as optional (silent skip risk).

## 5. Next actions (Stage 02, offline only)
- Rebase/split 0027 strictly after 0020+0023; fix deadlock, parser strictness, allocation, ACK correlation.
- Make SSP patches `.required` (build fails on skip/conflict).
- Run full tests BEFORE any build/flash (Stage 03/04).
- No BOOT flash until: 2 distinct known-good rollback copies (host+TWRP), full preflight PASS, owner acknowledgment for bounded trial.

## 6. Blocker / status
- **No active blocker for Stage 02** (offline source work). Device is safe and untouched.
- `DEVICE_VERIFIED` for baseline; `ROLLBACK_READY=PENDING` (second copy + dual-byte-verify deferred to Stage 04/05).

**The 100% milestone is NOT reached.** Real sensor-originated rotation + stable reboots + intact DT + verified TWRP rollback remain the acceptance target. Proceeding to Stage 02 (offline patch surgery).
