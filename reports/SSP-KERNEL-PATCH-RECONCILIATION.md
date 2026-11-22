# SSP — KERNEL PATCH RECONCILIATION (Stage 02)

**Date:** 2026-11-22
**Scope:** Offline forensic reconciliation of SSP kernel patches 0020 / 0023 / 0025 /
0026 / 0027 against the pinned downstream source.
**Model:** DeepSeek-V4-Pro-Thinking (carrying MASTER 00 + Stage 01 baseline).
**Device state:** untouched.  No flash, no firmware, no rail/GPIO/reset in this stage.

## Pinned source

- Repo: `https://github.com/Linux4/android_kernel_samsung_exynos9820`
- Commit: `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253 downstream)
- Defconfig: `exynos9820-beyond2lte_defconfig`
- Toolchain used to verify compilation: `aarch64-unknown-linux-gnu-gcc` (GCC 15.2.0)

## 1. Findings (larger than originally listed)

The original series is **not** a clean stack.  Three independent structural defects
were found and are all fixed in the corrected output below.

### R1 — 0020 and 0023 massively overlap (hidden duplication)

The "reconciled" 0023 does **not** layer cleanly on 0020.  Both patches edit
`drivers/sensorhub/brcm/ssp_dev.c` and `ssp_sysfs.c` at identical locations:

- `ssp_dev.c`: `initialize_variable()` `bSspShutdown=true → false` (byte-identical),
  `ssp_parse_dt()` `regulator_enable()` (byte-identical), `ssp_probe()` register comment.
- `ssp_sysfs.c`: `set_mcu_power()` `regulator_enable()` change, and the
  `nuxel_hub_diag` / `nuxel_bringup` / `nuxel_stream` sysfs attributes plus
  `nuxel_ssp_start_stream()`.

0020 ships a **stub** of these attributes (`nuxel_bringup` returns `-EOPNOTSUPP`);
0023 ships the **real** version (`nuxel_ssp_bringup_hw()`).  Applying both is
impossible (conflict), and the README's claim "0023 = de-duplicated 0013 only,
layer on 0020" is false.

**Resolution:** 0020 is reduced to the genuinely independent SPI controller fix
(`drivers/spi/spi-s3c64xx.c` `need_hw_init`); 0023 becomes the single authority
for every SSP driver file (the 0020 SSP hunks are folded into it).

### R2 — self-deadlock in `bbd_do_transfer()` (present in 0023 AND 0027)

On the failed-send path the code held `pending_mutex` from entry, then:

```c
mutex_unlock(&data->comm_mutex);
mutex_lock(&data->pending_mutex);   /* self-deadlock: already held */
...
mutex_unlock(&data->pending_mutex);
clean_msg(msg);
mutex_unlock(&data->pending_mutex); /* unbalanced */
```

`pending_mutex` is a raw (non-recursive) mutex.  This is a guaranteed hang on any
failed frame.  Also `clean_msg()` is `kfree(msg)` and ran while still touching
`msg->list`.

**Resolution:** `list_del()` under the already-held lock; release `pending_mutex`
then `comm_mutex`; `clean_msg()` only after both are released.  Verified balanced
1 lock / 1 unlock and no free-while-locked by `tests/test_ssp_lock_deadlock_static.py`.

### R3 — 0027 duplicates 0023's native-peer content

0027 was authored against the *old* (0013+0020 experimental) base, not against
0023.  It re-declares `nuxel_ssp_data`, `nuxel_ssp_register_data()`,
`bbd_nuxel_peer_*()`, `nuxel_bbd_peer_send()`, the `bbd_do_transfer()` changes, and
`callback_bbd_on_mcu_{ready,reset,packet}()` — all of which 0023 already provides.
It also re-defines the `ssp_bcm_spi_tx/rx/irq_count` globals.  Applying 0023 then
0027 yields duplicate symbol definitions.

**Resolution:** 0027 is rebased to contain **only** the downloader
(`dl_*` stack + `nuxel_ssp_dl_download()` + the bring-up integration point).  It
no longer re-declares any native-peer symbol.

## 2. The corrected, strictly-ordered series

Living tree also updated: `kernel/s10plus/patches/` (corrected versions installed,
each with a `.required` sidecar; 0020-old and 0026 retired; originals preserved in
`reports/ssp-stage02/originals/`).

| # | Patch | Role | .required |
|---|-------|------|-----------|
| 0020 | `0020-nuxel-ssp-spi-runtime-reinit.patch` | SPI re-init after runtime suspend | yes |
| 0023 | `0023-nuxel-ssp-native-bringup-reconciled-v2.patch` | native peer + bring-up (deadlock + bool fix) | yes |
| 0025 | `0025-nuxel-ssp-rail-force-coldcycle.patch` | `mcu_power` rail force-disable (sysfs only) | yes |
| 0026 | *(retired)* | subsumed by 0027 phase-1 | — |
| 0027 | `0027-nuxel-ssp-kernel-firmware-download-v2.patch` | kernel downloader (rebased, corrected) | yes |

## 3. Corrections in 0027 (each traced to the original defect)

1. **Self-deadlock** — fixed in 0023 (see R2); 0027 no longer contains a second copy.
2. **Premature parser success** — `dl_next_record()` now returns an explicit
   `TRUNCATED` / `MALFORMED` / `F1` / `OTHER` status; the download loop hard-fails
   on `TRUNCATED`/`MALFORMED` and never reaches WHOAMI.  Non-F1 records are
   structurally validated but not dispatched.
3. **Fragile ~439 KB contiguous `kmalloc`** — replaced with bounded `kvmalloc()`
   (slab fallback to vmalloc) plus a `DL_MAX_BLOB` (512 KiB) cap; the decoded length
   is validated against the container's `BlobLength`.
4. **Stale ACK correlation** — per-operation `op_seq`/`op_rel_seq` snapshots are
   committed before send and cleared on teardown; unsigned-char wrap is inherent;
   a `REL_NACK` for the outstanding op is a definitive failure; duplicate/arbitrary
   `bcm_ssi_rx()` data is ignored.
5. **`Crc` text ambiguity** — `PatchAddress`/`BlobLength` require an explicit hex
   parse; `BlobLength` is cross-checked against the decoded byte count; no conflation
   of the text `Crc` field with IEEE CRC32.

## 4. Verification results (this stage)

- **Apply / idempotence:** full series applies forward 0020 → 0023 → 0025 → 0027
  and reverses 0027 → … → 0020 back to the exact pinned tree (empty `git diff` for
  `drivers/sensorhub/` + `drivers/spi/`).
- **No duplicate symbols:** each symbol has exactly one definition; declarations
  are `extern`/forward only.
- **Compilation (changed files):** `ssp_bbd.o`, `ssp_dev.o`, `ssp_sysfs.o`,
  `ssp_i2c.o`, `bbd.o`, `bcm_gps_mem.o`, `bcm_gps_spi.o`, `bcm_gps_regs.o`,
  `bbd_rpc_lh.o`, `gyro_lsm6dsl.o` build with GCC 15.2 (aarch64) with **no new
  errors or warnings**.  `ssp_bbd.o` is warning-free.
- **Negative-case tests:** `tests/test_ssp_patch_negative_cases.py` (8/8 PASS) and
  `tests/test_ssp_lock_deadlock_static.py` (PASS) — see receipts below.

## 5. Patch SHA256 manifest

```
62a339642a8c039471c360da9a9175fd7e1b3e5e821cf3013ae953b0d6f73200  0020-nuxel-ssp-spi-runtime-reinit.patch
b21abad67fdee4734bfbc8c259295ff85f326fb16aabd68dc15dd208f92ca1db  0023-nuxel-ssp-native-bringup-reconciled-v2.patch
ab293ae63951fe0e3753dd30e56478439c6db1523efbd174b58deee6d32d6e99  0025-nuxel-ssp-rail-force-coldcycle.patch
cc33f15e034b823c0b019d02f4948df2013715fdf86473f0ce4fab94c51e289d  0027-nuxel-ssp-kernel-firmware-download-v2.patch
```

Original (pre-surgery) SHA256 for comparison:
```
8029e73052ba419b3f9fe093c18bc250a7f0cd40c60bf85c3857c883452fd076  0020 (old)
68b9ecc4876281062ea5023c4261618ffe0c2b75a438835057e1c6525c7e8af6  0023 (old)
b59357926d64443d8b0a0707222e209e0fdcc9a23d28ab7810dcb5bc19be49bd  0025 (old)
863785bbe7331e131f37c59c95aa4bf7ead7bd280336286f4ef45ae4885d3759  0027 (old)
```

## 6. Gate status

- **RECONCILIATION GATE (Stage 02):** the 0027 blockers are corrected, reviewed and
  compile/apply-verified.  **This does not authorize a BOOT flash.**
- Still REQUIRED before any flash (Stage 03/04):
  - Vendor frame/CRC/sequence/ACK semantics parity against `bcm_gps_regs.c` and
    `bbd_rpc_lh.c` (the vendor `bcm477x_rpc_get_version()` has a broken inverted
    poll loop and must not be used as a sync authority).
  - `rpc_id` transport-ACK vs operation-level result distinction.
  - KASAN/lockdep build on the pinned tree (optional instrumentation).
  - Two distinct known-good rollback copies + full BOOT preflight (Stage 04).

## 7. Additional discovered defect (fixed in 0023)

`struct ssp_data` declared `bool IsNoRespCnt;` but `callback_bbd_on_mcu_reset()`
did `data->IsNoRespCnt++` — incrementing a `bool` (never a real counter,
`-Wbool-operation`).  Corrected to `u32 IsNoRespCnt`.
