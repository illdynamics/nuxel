# SSP — Stage 04 Preflight (Exhaustive Offline Verification + Zero-DT-Change BOOT Gate)

**Date:** 2026-11-22. **Model:** DeepSeek-V4-Pro-Thinking.
**Hardware:** read-only SSH to the running handset only. **No flash, no firmware, no write.**

## Verdict: **NO FLASH**

Multiple gates FAIL or remain BLOCKED. A single FAIL means NO FLASH, and there are
several. See `reports/SSP-CANDIDATE-PREFLIGHT.json` for the machine-readable per-gate
result; this document is the prose rationale.

## 1. Offline test suites — all PASS

| Suite | Command | Result |
|---|---|---|
| Native C harness | `make -C tools/s10plus/ssp-native OUT=/tmp/ssp-audit-build check` | PASS (download/flash/negative/embedded/replay) |
| Orientation pytest | `PYTHONPATH=services/nuxel-orientation python3 -m pytest -q services/nuxel-orientation/tests` | **77 passed** (68 original + 9 new) |
| Recovery unittest | `python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_*.py'` | **14 passed** |

New negative coverage added this round:

- `tools/s10plus/ssp-native/tests/test_nuxel_bbd_negative.c` (wired into the Makefile
  `check` target): F0..F5 malformed/truncated records, patch identity/version mismatch,
  bad ACK/NACK flag classification, wrong CRC, no-reply timeout (`-ETIMEDOUT`),
  NACK rejection (`SSI_ENOTACK`), cancellation (`-ECANCELED`), 8-bit sequence rollover,
  RX-parser reentrancy, partial-transfer/short-read (1-byte-at-a-time), two-instance
  independence, header-decode edge cases.
- `services/nuxel-orientation/tests/test_source_availability_and_stale.py`: 9 new
  tests for **real-source-unavailable** (missing/unreadable node, impossible IIO hint,
  halted-MCU zero vector) and **stale-data recovery** (zero snapshot is not live;
  recovers only on a genuinely new non-zero sample; goes back unavailable when the
  stream stops; `ensure_streaming` never caches a stale "was live").

## 2. Exact pinned kernel — BLOCKED (FAIL)

The exact pinned kernel **was not built**. Two independent blockers:

1. **Unrelated contamination (FAIL, blocking).** The kernel working tree
   `kernel/s10plus/.build/src` (HEAD `f7194c1d15ed…`, the correct pinned commit) has
   **40 modified files**, of which **28 are netfilter files** (`net/netfilter/xt_DSCP.c`,
   `xt_HL.c`, `xt_RATEEST.c`, `xt_TCPMSS.c` + uapi/libdss-include headers). No patch in
   `kernel/s10plus/patches/` — or anywhere else in the repo — touches any of them. They
   are foreign edits with no provenance. This violates the "no unrelated patch changes"
   requirement and makes the tree non-reproducible. Dirty-diff SHA-256:
   `7340907c93ed3618fc19f882ad977d089b4ee3ee33a3f912170ef1ed529c1938`.

2. **No build output.** No `.config` has been generated and no
   `arch/arm64/boot/Image` exists. kallsyms for the candidate is therefore unverifiable.

The corrected SSP series itself (0020 → 0023 → 0025 → 0027) applies idempotently to
the clean pinned commit and the patch SHA-256 values match the Stage-02 reconciliation
manifest exactly (see `reports/SSP-SOURCE-BUILD-MANIFEST.json`). The blocker is the
tree state, not the SSP series.

## 3. Embedded firmware identity — PASS (verified against real bytes)

`verify_embedded_patch.py kernel/.../r_os/bbd_patch_file_beyond.h` against the actual
decoded bytes (not documentation):

- ASIC `0x004775b0`, BlobLength `438895`, PatchAddress `0x00800161`,
  header Crc `193`, IEEE CRC32 `93d35bb4` — all match the expected constants.
- Blob SHA-256 `56e8b1ea4b34…`, kernel-export SHA-256 `0b53f3b04b…` (matches).

## 4. BOOT/DT immutable gate — mixed, with two hard blockers

1. **Donor revalidation: PASS.** Fresh read-only `dd | sha256sum` from the running
   handset (root@10.11.12.99, `4.14.253-gf7194c1d15ed-dirty`) reproduces the Stage-01
   hashes byte-for-byte for `dtb`/`dtbo`/`boot`/`recovery` (sda12/13/14/15). Partition
   map, BOOT v1 header (kernel_addr 0x10008000, ramdisk_addr 0x11000000, kernel_size
   45848584, ramdisk_size 2424832), and `androidboot.dtbo_idx=9` are all reaffirmed.
   The donor boot image has **zero appended DTB** — `appended_dtb_count=0`, and the
   9,394,176 bytes after the ramdisk are **100% zero partition slack** (verified: no
   `0xD00DFEED` magic, `data == b'\x00'*len`).

2. **Pack/verify: FAIL.** `tools/s10plus/pack-ssp-boot.py` searches for an appended
   FDT (`donor.find(0xD00DFEED)` after the ramdisk) and raises
   `cannot locate the appended DTB region` on this donor. Its FDT-discovery heuristic
   is wrong for this device (external dtb/dtbo partitions, no appended tail), and it
   also contains a degenerate always-true fallback
   (`donor[cand - min(cand, PAGE):cand] or True`). **This tool cannot produce a
   candidate boot image for this handset.** A correct repack for this layout is simply
   header + Image + byte-identical ramdisk + zero-fill to the partition; the DTB tail
   to "preserve byte-for-byte" does not exist.

3. **Byte-exact tail: PASS-with-caveat.** Because there is no appended DTB/hash tail,
   the preservation requirement collapses to "keep header + ramdisk bytes identical and
   zero-fill the slack". Trivially satisfiable, but not demonstrable because no
   candidate exists and the packer is broken.

4. **dtb/dtbo partition hashes: PASS.** `dtb` and `dtbo` recorded read-only and
   unchanged (`abc9d45d…` / `de3bc025…`). No dtc/dtbo output was changed.

5. **Rollback staging: PARTIAL.** Host-side seed captured and verified
   (`/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img`, 57,671,680 B,
   sha256 `0e6aa34c…` == live sda14). A second TWRP-accessible copy with dual-endpoint
   byte verification was **not** established (no recovery boot performed), so
   `ROLLBACK_READY` remains not fully satisfied.

6. **Software-only alternative: SUPPORTS NO FLASH.** The running kernel (0020+0023)
   already exposes `/dev/ttyBCM`, `/dev/bbd_sensor`, `/dev/bbd_control`,
   `/dev/bbd_patch`, and the `nuxel_bringup` ABI. The native userspace tools
   (`nuxel_bbd_flash.c --flash`, `nuxel_bbd_download.c`) target exactly those nodes, so
   the 0027 kernel-coordinated downloader (`nuxel_ssp_dl_*`) is **not proven necessary**.
   Flashing a new kernel merely to run a protocol parser that is already testable in
   userspace is avoided. (The userspace path is itself not yet proven to produce RX —
   the live diag still shows `rx=0` — but that does not make a kernel flash the
   next step.)

## 5. Known remaining hardware risks

- MCU never RX'd across a 184-byte TX; root cause unresolved.
- Vendor lhd is ARCHIVE_ONLY; not re-verified against live bytes.
- Autobaud 32-vs-36 reconciliation unresolved.
- Any future flash is bounded by the owner's BOOT-only TWRP agreement, not this report.

## 6. Decision

**NO FLASH this round.** Required next actions before stage 05: (1) restore a clean
pinned kernel tree and apply only SSP 0020/0023/0025/0027; (2) build the exact kernel
and produce `.config`, `Image`, kallsyms, and a candidate boot image; (3) replace or
fix `pack-ssp-boot.py` for the no-appended-DTB layout; (4) establish the second
TWRP-accessible rollback copy with dual-endpoint verification.
