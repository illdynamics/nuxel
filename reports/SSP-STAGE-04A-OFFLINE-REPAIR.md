# SSP Stage 04A — external offline repair and revalidation (2026-11-22)

## Verdict: **STILL NO FLASH / STAGE 05 PHYSICAL NOT AUTHORIZED BY THIS ARCHIVE**

This audit applies to the user-provided `nuxel-cs-ssp.zip` (~366 MiB ZIP, ~814 MiB extracted) and the uploaded Stage-05 Markdown prompt. The ZIP contains 21,015 path entries. The source archive excluded the kernel `.build/src` checkout, generated `.config`, uncompressed candidate `Image`, and the full verified BOOT donor image. The analysis has **no SSH/TWRP/device access**, and cannot establish a second TWRP-accessible rollback copy or freshly verify the physical partition map. None of those missing facts is filled in by guessing.

**Preserved evidence:** `reports/SSP-CANDIDATE-PREFLIGHT.json` remains `NO_FLASH`; `reports/SSP-SOURCE-BUILD-MANIFEST.json` remains the historical Stage-04 observation. They MUST NOT be edited to PASS without new evidence.

## Exact findings in Stages 00–04

- **00/01 baseline and rollback:** recorded live BOOT/DTB/DTBO/RECOVERY hashes, model, boot parameters and kernel identity; one independently hashed host rollback seed; a second TWRP-readable rollback seed **not proven**.
- **02 patch reconciliation:** four SSP `.patch` files are present and their SHA-256 digests match Stage-02's corrected series: `0020 62a33964...`, `0023 b21abad6...`, `0025 ab293ae6...`, `0027 cc33f15e...`. This proves bytes are in the archive, **not** that the exact kernel tree is clean or buildable today. Stage-02's patch documentation still names `-v2` files whereas the installed patch files use the production names; digests agree.
- **03 parity/cold start:** container identity, host reference framing and negative cases were studied; transport ACK is NOT equivalent to application-level MemoryWrite acceptance; autobaud `32` kernel vs `36` userspace/vendor-reference remains source-unresolved; no verified physical ROM reply.
- **04 tests:** the C native harness, simulated replay, orientation suite and recovery tests are reproducible offline. Live physical sensor readings are not.
- **04 source build:** the historical dev checkout's 28 foreign `netfilter` modifications remain uncorrected in the missing `.build/src`. A *fresh checkout on a case-sensitive filesystem* is required; do not destroy the original dirty source tree or suppress the contamination gate. Current ZIP has no runnable exact source checkout and cannot produce a new verified ARM64 `Image`.
- **04 BOOT repack:** corrected in this replacement for the known full-partition external-DT layout. This is an offline code correction, **not** a built, validated BOOT candidate.
- **04 rollback and justification:** physical second-copy and TWRP endpoint hash checks remain open. The running kernel reportedly already has native BBD passthrough; an independently reviewed software-only experiment may avoid another BOOT flash entirely. The fact userspace transport exists does not prove the MCU responds.

## Actual replacements in this ZIP

1. **`tools/s10plus/pack-ssp-boot.py`**: removed heuristic searching `0xD00DFEED`, weak magic-based kernel offset discovery and `or True` fallback; parse BOOT-v1 canonical header, full-size donor and external-DTB zero slack; verify complete trusted donor SHA; only kernel-size header field changes; copy donor ramdisk bytes without recompressing; require raw ARM64 Image; check capacity, addresses, aligned payload and zero slack; reject appended DTB, unexpected trailer, donor/header/ramdisk changes; JSON package manifest states `flash_authorized:false`. No device write capability.
2. **`kernel/s10plus/build-kernel.sh`**: `NUXEL_SSP_STRICT=1` invokes a fail-closed pinned-source/foreign-diff audit before patch application and forbids `NUXEL_SKIP_PATCHES=1`. Required SSP patch verification now checks an **exact per-file receipt**, rather than the former global `grep -q APPLIED` (a false-positive). An SSP required patch will never be counted verified merely because a file it creates already exists. Other build workflows remain unchanged unless strict mode is requested.
3. **`tools/s10plus/ssp-stage04/audit_kernel_source.py`**: read-only check of `git HEAD`, changed tracked paths and untracked files versus active patch targets; never resets or cleans source. `--allow-patch-touched` does NOT verify patch content; exact patch receipts and compilation remain separate.
4. **`tools/s10plus/ssp-stage04/verify_stage05_gate.py`**: rejects previous `NO_FLASH` JSON, missing, partial or caveated gate results. Even with all reported gates PASS, explicitly says further independent live safety checks are needed.
5. **New synthetic negative-case tests:** `test_pack_ssp_boot.py` (9), `test_kernel_source_audit.py` (4), `test_stage05_gate.py` (3). These tests do not require real vendor firmware or physical partition images.
6. **Revised Stage-05 agent prompt:** `pwn/ssp-stage05-revised-20261122.md` and standalone downloadable `05_CONTROLLED_PHYSICAL_FIRST_LIGHT_AND_TWRP_REVISED.md`. Distinguishes intentionally entering TWRP from a failed normal Nuxel boot, includes exact BOOT-only agreement, rollback and finite diagnose/rebuild/reflash workflow, and explicitly prevents flashing while any Stage-04 gate fails.

## Offline tests executed in this audit

| Check | Result | Meaning |
|---|---|---|
| `make -C tools/s10plus/ssp-native OUT=/tmp/nuxel-ssp-stage04-audit-build check` | PASS | Native C, protocol negative tests, simulated replay |
| `python3 -m pytest -q services/nuxel-orientation/tests` | **77 passed** | Offline orientation/policy tests |
| `python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_*.py'` | **14 passed** | Recovery toolkit offline |
| `python3 -S tools/s10plus/ssp-stage04/test_pack_ssp_boot.py` | **9 passed** | Synthetic external-DTB packaging invariants |
| `python3 -S tools/s10plus/ssp-stage04/test_kernel_source_audit.py` | **4 passed** | Synthetic git/source hygiene checks |
| `python3 -S tools/s10plus/ssp-stage04/test_stage05_gate.py` | **3 passed** | Refusal of incomplete/historical preflight |
| `bash -n kernel/s10plus/build-kernel.sh` | PASS | Shell syntax only |
| `verify_stage05_gate.py --preflight reports/SSP-CANDIDATE-PREFLIGHT.json` | **FAIL as required** | Gate correctly refuses known `NO_FLASH` |
| Exact pinned kernel build / new kernel Image | **NOT RUN** | Source + toolchain/device donor not present |
| Independent `verify-boot-image.py` on actual candidate | **NOT RUN** | No actual candidate or complete live merged-DT evidence |
| Second TWRP rollback copy | **NOT RUN** | No TWRP access from this environment |

## Practical remaining sequence

1. Use the user's actual development host to provide a fresh **case-sensitive**, pinned kernel checkout, or correct the existing tree *without losing unrelated edits*. Run strict audit and record exact patch receipts. Do not fabricate the missing `.build` source from the ZIP.
2. Decide whether the already-deployed userspace BBD path is adequate; a BOOT flash is not justified solely by availability of 0027.
3. When a new kernel is proven necessary, complete exact full build, config/memory/kernel-symbol audit, and produce actual raw `Image`.
4. Repack from the full-size freshly SHA-verified live donor; independently validate using `verify-boot-image.py` and separately acquired DTB/DTBO/merged FDT hashes and selected overlay index. Protect BOOT header (except kernel-size field), ramdisk, and zero-fill; keep external DT unchanged.
5. In TWRP create/verify a second independently accessible known-good rollback copy BEFORE candidate write; revalidate live target mapping. Record full preflight **new** receipt with all mandatory gates PASS; `verify_stage05_gate.py` exit 0 only establishes *reported* requirements, not hardware authenticity.
6. Only if preflight and live evidence justify a BOOT-only write, follow the revised `05` TWRP agreement. Unexpected TWRP return/hang = candidate failure, evidence and known-good recovery; never blind retry. Continue with a newly verified corrected candidate only within the fixed session limit. If Nuxel already boots and kernel flash is unnecessary, avoid flashing entirely.

## Important additional observation

`0027` remains a production-critical protocol and kernel-locking change that needs validation against the **exact actual kernel source**. In the patch, `dl_fire_rpc` and `dl_reliable_rpc` form payload bytes *before* checking advertised payload sizes; currently known call sites appear bounded, but this order is fragile and should be reviewed. Do not invent a revised 0027 hash without compiler-based regression verification. The vendor ROM autobaud discrepancy, physical rail timing, whether a transport ACK is sufficient and real MCU response all remain **unverified**.

## Decision

**The offline repair files are ready to drop into the project; the phone is NOT thereby flash-ready.** This is deliberate fail-closed engineering. Do not interpret the existence of the deliverable ZIP, candidate packer or revised prompt as a Stage-05 hardware GO signal.
