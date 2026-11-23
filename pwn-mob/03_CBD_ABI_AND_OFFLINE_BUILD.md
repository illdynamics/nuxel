# 03 — DEEPSEEK PRO THINKING: Exact Samsung CBD + S5000AP Kernel ABI, Compile Offline

Apply `00_MASTER_SAFETY_AND_TRUTH.md` and gates 01/02. This is the **highest-value engineering round**. Do not flash, run modem-power ioctls, alter DTB/DTBO, or write radio partitions.

## Verify the actual ABI

Pin the exact currently running Exynos9820 downstream kernel revision. Starting historical reference: `Linux4/android_kernel_samsung_exynos9820@f7194c1d15eded1c2a1a4dc63825b26103435cc0`. Inspect `drivers/misc/modem_v1/` (controller `modem_ctrl_s5000ap.c`, `modem_prj.h`, ioctl dispatch in I/O core, SHMEM/SBD, `sipc5.h`, boot request structs, secure boot, RFS). Compare compiled configuration, commit provenance, boot image hash, exact device-tree *read-only* bindings and Samsung bootloader expectations. Do not infer UAPI from the research text's isolated `IOCTL_MODEM_STATUS _IO('o',0x27)` without cross-checking headers and actual target compiler ABI.

Build annotated UAPI matrix with ioctl numeric values, direction, field sizes, pointer widths, alignment/padding/endian, boot-state enums, kernel handler per request, expected pre/post state, where secure boot is handled, error codes/timeouts and actual device path. Build 32/64 compatibility tests; ARM64 cross-compile and host compile; compare struct layouts and generated ioctl constants, not just names. Do not probe live risky ioctls to discover semantics.

## Reuse Samsung source before rewriting anything

Source candidates:
- `https://github.com/LineageOS/android_hardware_samsung_slsi-linaro_exynos` / `cpboot_v3` — pin exact SHA and branch.
- `https://github.com/LineageOS/android_device_samsung_exynos9820-common` — examine `cbd` `protocol=sipc` and `use_legacy_sipc_ioctl=true`, with exact branch and revision.
- Matching SM-G975F DTK9 proprietary runtime/Bionic vendor libraries only where lawfully owner-provided and compatible.

Explain *why* chosen CBD is ABI-exact or not. Determine toolchain, build flags, dependencies (Bionic vs glibc), SELinux/systemd alternatives, firmware image sections and image read path. Prefer an isolated matching Samsung cbd under owner-compatible runtime over an unverified fresh native loader. Do not assume `cpboot_v3` from newest Lineage branch automatically matches historical Android 10 vendor kernel.

## Build deliverables

Implement an offline `nuxel-s5000ap-uapi-check` fixture plus a **read-only** `s5000ap-status` using verified header. Build a reusable `cbd` binary or compatibility shim, or a **strictly dry-run** `nuxel-cpbootd` if matching source is genuinely incompatible. Dangers disabled by compile-time and runtime opt-in defaults. All boot call plans generated from pinned ABI; no guessed firmware pointer/offset or secure-boot sequence. Every transfer length checked against file and mapped memory ranges; signed source not modified.

`nuxel-cpbootd` if necessary: single exclusive owner of `/dev/umts_boot0`, bounded stage deadlines, idempotent failure cleanup, no daemon restart storm, no hidden modem partition writes, no unattended CP boot or RF-on. Tests include malformed pointers/container sizes, partial reads, short writes, timeout/errno, overlapping segments, wrong endianness, double invocation/races, missing endpoints, CP crash injection using mocks ONLY, and negative proof that hardware-changing ioctl surface cannot execute during dry-run.

Create `reports/S5000AP-03-BOOT-CONTRACT-ABI.md`, `reports/S5000AP-03-BUILD-RECEIPT.md`, pinned dependency manifests, clean reproducible source commits, archived test logs and a stage-by-stage **proposed** first CP boot operation table (operation, source/structure proof, expected kernel state, timeout, abort rule). Don't claim ONLINE yet.

### Delegate to Flash

A. Pinned kernel UAPI extraction and comparative header/layout assertions. B. `cbd` dependency/build container reproducibility. C. Offline negative tests/fuzzer and source static analyzer. D. Coverage/manifest review. Thinking selects architecture and rejects incompatible candidates.

### GO/NO-GO for next round

Proceed to controlled CP boot ONLY if (a) correct firmware provenance, (b) CP UAPI verified, (c) a specific compatible boot transaction recovered, (d) bounded binary built and tested, (e) recovery and state-observation procedures reviewed and (f) owner explicitly approves this one CP trial. If any item unresolved, continue offline and name exact blocker; don't improvise.
