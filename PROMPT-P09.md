# NUXEL — COMPONENT P09 IMPLEMENTATION PROMPT

## Clean image and workflow preparation

<!-- This file is the COMPLETE SCOPE for a FUTURE agent. It is not instructions
     to be obeyed by the author of this prompt; it IS the instruction set for the
     next implementation session. Implement ONLY component P09 in this branch. -->

---

## 0. Agent mission (this branch ONLY)

You are the Nuxel Fedora ARM64 phone OS engineering agent, working in a dedicated
Git feature branch. Implement **only component P09: Clean image and workflow
preparation** in this existing repository. This file is the complete scope for the
current run; do not implement the other screenshot items in this branch. Reuse
actual Nuxel architecture and existing services instead of creating parallel or
fake substitutes.

Target platform: **Samsung Galaxy S10+ SM-G975F / Exynos 9820**; Nuxel Fedora
ARM64 without Android framework dependencies. A MacBook host may build/test; the
live phone may not be connected. Don't assume a hardware verification that did not
happen.

Component contract (the four things P09 must deliver):

1. **Audit rootfs and image build sources for deterministic inputs.**
2. **Create reproducible userland build and validation workflow without writing device partitions.**
3. **Verify CI artifact provenance and checksum publication.**
4. **Document provisioning, build dependencies and rollback-safe staging.**

### What P09 is NOT

- P09 does **not** flash a device, write BOOT/USERDATA/recovery partitions, or
  replace the kernel/bootloader. It prepares and validates *artifacts* on the host.
- P09 does **not** fix touch/display/GPU (that is later hardware bring-up). It makes
  sure whatever image already gets built is reproducible, verified, and documented.
- P09 does **not** rebuild or rewrite `images/s10plus/build.sh`, the A25 boot
  assembler, or the kernel build — it *consumes* those outputs and adds the
  provenance/validation/staging/documentation layer around them.

---

## 1. Hard boundaries (do not violate)

- Do **not** flash a device, unlock/rewrite bootloader, partition, or replace the
  kernel/bootloader. Any dangerous hardware operation is FORBIDDEN.
- Do **not** write to physical phone partitions; build and validate only on host.
- Preserve working launcher navigation, haptics, custom icon assets, Home layouts
  and USB recovery that already exist — do not regress them.
- Reuse existing services/tools: `tools/nuxel-device-select.sh`,
  `images/s10plus/build.sh`, `images/s10plus/build-phone-rootfs-fedora.sh`,
  `ci/validate-build.sh`, `tools/verify-artifacts.sh`,
  `tools/s10plus/verify-a25-boot.py`, `tools/s10plus/verify-fedora-phone-rootfs.py`,
  `tools/s10plus/check-phone-runtime-staging.py`, `tools/package-release.sh`.
- Commit **only this component's** code, tests, documentation and report. Do not
  merge into main, switch branches, add secrets, or generate unrelated features.
- Never pass off mocks as physical checks. Distinguish host/mock tests from live
  results.

---

## 2. Real repository architecture (VERIFIED FACTS — read these now)

> These are things I audited in the working tree and can be treated as ground
> truth for this prompt. Where a value is device- or build-specific, note it so the
> future agent re-checks rather than assumes.

### 2.1 Layout (all paths relative to repo root)

- `VERSION` = `v0.6.0-beta` branch target; release workflow keys off VERSION tags.
- Top-level Makefile wires: `make assets` -> `tools/dedupe-assets.sh`;
  `make build` -> `images/build.sh`; `make validate` -> `ci/validate-build.sh`;
  `make ci` -> dedupe + build + validate; `make release` -> `tools/package-release.sh`.
- Device abstraction: `tools/nuxel-device-select.sh` resolves `--device`/`NUXEL_DEVICE`
  to a canonical dir. Aliases: `s10plus|beyond2lte -> s10plus`,
  `g7power|ocean -> g7power`, `mustang -> google-pixel-10-pro-xl`. No device is the
  silent default in the shared selector itself (per-device scripts may default).
- Per-device trees: `device/<key>/` (APKBUILD, deviceinfo, udev rules, per-device
  conf), `configs/s10plus/`, `kernel/s10plus/`, `images/s10plus/`.

### 2.2 Build & image sources for s10plus (the P09 target)

- **`images/s10plus/build.sh`** — orchestrates the S10+ boot + rootfs images under
  `build/out/s10plus/`:
  - `u-boot-beyond2lte.img` (U-Boot wrapped as Android boot-header v1),
  - `nuxel-beyond2lte-boot.img` (kernel + initramfs + merged board DTB, boot-header v1),
  - `nuxel-beyond2lte-rootfs.img` (ext4 for userdata),
  - `build-manifest.json` (device key, kernel commit, build timestamp, phase).
  - Phase 1 intentionally emits **no** dm-verity/AVB image (rootfs must stay writable
    during bring-up). Device-isolated: only writes under `build/out/s10plus/`.
  - Writes a per-artifact `sha256sums.txt` next to the images.
  - Inputs it asserts missing -> abort: kernel `Image.gz`, a beyond2lte DTB, a shared
    initramfs (search order defined in-script), and u-boot.bin.
- **`images/s10plus/build-phone-rootfs-fedora.sh`** — builds a true Fedora 43
  aarch64 Nuxel PHONE userspace from real RPMs inside Docker/podman on Apple Silicon
  (or Linux aarch64). Calls `tools/s10plus/verify-fedora-phone-rootfs.py` after.
- **`images/s10plus/build-phone-rootfs-inside-fedora.sh`** — the in-container builder
  script invoked by the wrapper above.
- **`images/mkrootfs.sh`** / **`images/s10plus/mkrootfs.sh`** — immutable rootfs
  builders (Flatpak-runtime/overlay + dm-verity) for other targets; S10+ overrides
  with its own Fedora phone builder (fail-closed, no host-arch Flatpak fallback).
- **`boot/`**, **`images/bootpack/`** (`mkbootimg.py`, `cpio_builder.py`,
  `assembler.py`) — boot image packing primitives.

### 2.3 Verification tooling that already exists (reuse, don't re-implement)

- **`ci/validate-build.sh`** — real-artifact assertions with PASS/FAIL + exit code;
  historically mustang-only but sources the shared selector and downgrades kernel
  artifact checks to warnings when no per-device kernel build exists. Check its body
  for how it treats s10plus vs mustang before assuming behaviour.
- **`tools/verify-artifacts.sh`** — FAIL-CLOSED strict verifier run by CI AFTER build,
  BEFORE packaging. It asserts non-empty files, valid boot-image headers (kernel+ramdisk+dtb),
  valid ext4 rootfs with real payload, boot splash content (MP4 + Plymouth theme), and
  device-specific rules (s10plus must use the A25 BOOT: RAW arm64 Image not Image.gz,
  initramfs EMBEDDED, merged DTB). Drives `verify-a25-boot.py` / `verify-fedora-phone-rootfs.py`.
- **`tools/s10plus/verify-a25-boot.py`** — proves the S10+ BOOT image is the A25 form.
- **`tools/s10plus/verify-fedora-phone-rootfs.py`** — strict ARM64 Fedora runtime
  verifier over staging OR ext4; no mount/chroot/Docker/libext2fs in `--ext4` mode;
  checks package binary payloads + S10+ assets (uses local `tools/s10plus/ext4lite.py`).
- **`tools/s10plus/check-phone-runtime-staging.py`** — fail-closed staging check for
  executables + per-device metadata (macOS-compatible).
- **`tools/package-release.sh`** — packages `build/out/<device>/` into
  `dist/nuxel-<version>-<device>.tar.gz`, writes `dist/SHA256SUMS.txt`, release notes;
  self-contained pure bash + tar/sha256sum (CI- and local-runnable).

### 2.4 CI / provenance wiring

- **`.github/workflows/release.yml`** — builds every supported device, runs
  `tools/verify-artifacts.sh` as the explicit FAIL-CLOSED gate before packaging. No
  `continue-on-error`; a missing/invalid artifact skips the release. The S10+ BOOT is
  the A25 image; USERDATA holds the current A34 TOUCHDOWN userspace. It validates that
  VERSION matches the tag and (for main pushes) that the tag names the merged commit.

### 2.5 Determinism-relevant artifacts already present

- **`images/s10plus/packages-manifest.json`** — schema `nuxel.packages-manifest/1`,
  records Fedora release/basearch/repos, `repomd.xml -> primary.xml` provenance with
  sha256 of repomd and compressed/decompressed primary.xml, source network + nevra counts.
- **`images/s10plus/build.sh`** writes `build-manifest.json` (device key, kernel commit,
  dtb name, phase, timestamp) and `sha256sums.txt`.

### 2.6 Things the future agent MUST re-inspect before relying on them

These are NOT confirmed by this prompt; verify in-tree:

- The exact current contents/behaviour of `ci/validate-build.sh` for s10plus (it is
  historically mustang-focused — confirm whether it validates s10plus artifacts at all).
- Whether a real per-device kernel build exists at
  `kernel/s10plus/.build/out/arch/arm64/boot/Image.gz` and a beyond2lte DTB in that tree.
- Exact initramfs search-order precedence inside `images/s10plus/build.sh`.
- Current values asserted by `verify-fedora-phone-rootfs.py` (binary list, source-parity map) —
  these must stay consistent if you change what the rootfs builder packages.
- The precise schema fields CI reads from `build-manifest.json` / `packages-manifest.json`.

---

## 3. What P09 actually changes (smallest coherent plan)

P09 adds a **clean-image + workflow-preparation** layer around the existing s10plus
build/verify/release pipeline WITHOUT rewriting those pipelines or flashing anything.

Concretely, implement:

### 3.1 Deterministic-input audit (`scripts/p09/audit-deterministic-inputs.sh`)

A host-only script that inspects real repo files and reports a determinism report:

- Enumerate every *non-deterministic* input the s10plus image build depends on, and
  pin or record each:
  - Kernel source commit (`git rev-parse` of `kernel/s10plus/.git`, else "unknown").
  - U-Boot source commit/branch.
  - Fedora package versions (from `packages-manifest.json` + a recorded RPM/Nevra list).
  - DTB selection logic and which board DTBO is merged (record the merge rule, not just "merged").
  - Initramfs provenance (which stage produced it; its sha256).
  - Build timestamp / machine — flag as the one intentionally-non-deterministic field.
- Verify `packages-manifest.json` repomd/primary checksums match what's recorded
  (download-or-reuse-cached where possible, but never fabricate a hash; if network is
  unavailable, mark that check BLOCKED with evidence).
- Emit `docs/component-reports/p09-determinism-report.md` (or print a machine-readable
  summary) listing PASS/RECORDED/BLOCKED per input.

### 3.2 Reproducible userland build + validation workflow (`scripts/p09/build-and-validate.sh`)

A host-only orchestrator that runs the *existing* builders and verifiers in order,
without touching device partitions:

1. `make assets` (dedupe single-source PWA assets).
2. Build the shared initramfs via `images/build.sh --initramfs-only` (or the s10plus
   entrypoint — confirm which is correct for a host build that does NOT flash).
3. Run `images/s10plus/build.sh --boot-images-only` first (proves boot image + manifest
   + checksums without requiring u-boot.bin), then, if Docker/podman available, the
   Fedora phone rootfs via `build-phone-rootfs-fedora.sh`.
4. Run `tools/verify-artifacts.sh --device s10plus` and
   `tools/s10plus/verify-fedora-phone-rootfs.py` (staging or ext4).
5. Write a per-run receipt: `build/out/s10plus/p09-build-receipt.json` containing device,
   kernel commit, rootfs sha256, boot image sha256, manifest sha256, verifier exit codes,
   and a machine-readable PASS/FAIL/BLOCKED verdict.

Must be **idempotent** and refuse to overwrite an existing receipt/output unless `--force`.
Must degrade gracefully: if the Fedora container isn't available, still validate whatever
host artifacts exist and mark the rest BLOCKED (not silently green).

### 3.3 CI artifact provenance + checksum publication (`scripts/p09/verify-provenance.sh`)

- Re-run `tools/verify-artifacts.sh` semantics in a device-keyed way for s10plus and
  assert that published checksums match the artifacts (compare `sha256sums.txt` / receipt
  against `package-release.sh` output).
- Ensure `dist/SHA256SUMS.txt` is reproducible from verified artifacts (document ordering).
- If a dependency blocks provenance, produce the smallest safe implementation + precise
  blocker note; don't let it stall.

### 3.4 Provisioning / dependencies / rollback-safe staging docs

- `docs/component-reports/p09.md` — the component report (see §6 for required sections).
- Document build dependencies (RPMs, Docker/podman + qemu binfmt on Apple Silicon,
  kernel build prerequisites) and rollback-safe staging: how to stage a validated image
  under `build/out/s10plus/` and how to roll back the *staging* pointer without flashing.

### 3.5 Tests (real behaviour + failure paths)

- A shell/python test suite under `tests/p09/` that exercises real code paths, e.g.:
  - `audit-deterministic-inputs.sh` reports "unknown" kernel commit when the kernel tree
    has no `.git`, and a short commit otherwise (failure path + pass path).
  - `build-and-validate.sh` refuses to overwrite an existing receipt without `--force`.
  - Receipt JSON is valid and contains required keys; verifier exit codes are recorded.
  - Provenance: fabricate a wrong sha256 in a temp checksum file and assert the verify
    step FAILS (proves it's not a static reference).
  - Determinism report lists every enumerated input with a status token.
- Prefer host-only, no-device tests. For anything that would need the phone, clearly mark
  as mock/host vs live-unverified.

---

## 4. Honest hardware verification policy

The live S10+ phone is **not assumed connected**. Follow these rules:

- Anything that requires the handset (actual boot, display/GPU/touch, modem) is
  `NOT_TESTED` or `LIVE_UNVERIFIED` unless you have actual owner-confirmed evidence.
- The strongest host-side proof available is: real artifacts present, structurally valid
  headers, valid ext4 with expected payload, ARM64 ELF binaries, package payloads matching
  recorded checksums, and reproducible receipts. That is *image correctness*, not *device boot*.
- Do NOT claim physical boot, flashing, or owner confirmation happened unless the receipt
  carries concrete evidence (serial, logged kernel messages from the device, etc.).

---

## 5. Acceptance gates (each item PASS / FAIL / BLOCKED with evidence)

1. Determinism audit script exists and runs host-only; report enumerates every non-deterministic input with a status.
2. Reproducible build+validate workflow orchestrator exists, is idempotent, refuses overwrite without `--force`, and produces a receipt.
3. Provenance/checksum verification passes against real artifacts (or BLOCKED with evidence); published checksums match.
4. Provisioning + dependencies + rollback-safe staging documented; no device writes anywhere in P09.
5. Tests exercise real behaviour AND failure paths (not only static references); suite runs host-only and exits non-zero on the injected failures.
6. Component report `docs/component-reports/p09.md` has all required sections (§6).
7. No regressions to launcher navigation / haptics / icon assets / Home layouts / USB recovery that already exist.
8. Every item above is implemented or explicitly BLOCKED with concrete evidence — nothing silently omitted.

---

## 6. Required component report (`docs/component-reports/p09.md`)

Must include, for P09 only:

- **Code paths changed** (files/dirs added or modified; what each does).
- **Commands + receipts** actually run (with exit codes and the receipt sha256).
- **PASS / FAIL / BLOCKED / NOT_TESTED** per acceptance item — with evidence, not assertions.
- **Actual device deployment status**: explicitly state whether anything was flashed/booted on a physical S10+; if none, say "not deployed to hardware" and why.
- **Unresolved issues & open questions**.
- **Safe rollback instructions** for staging (how to revert P09 changes / restore previous staging pointer) — note that flashing rollback is out of scope since nothing was flashed.

---

## 7. Rollback plan (for this component's changes on the host)

- All P09 additions are additive and isolated under `scripts/p09/`, `tests/p09/`,
  `docs/component-reports/p09*.md`, and a single receipt file. To roll back, remove or
  ignore those paths; do not touch existing build/verify scripts unless the report says so.
- The staging pointer (what image `build/out/s10plus/` currently validates) rolls back by
  restoring the previous receipt/artifacts — no partition writes involved.
- Document the exact revert commands in the component report.

---

## 8. Finish state

- Commit **only** P09's code, tests, docs and report on the checked-out branch.
- Run `git status`; finish with a clean worktree. Do not merge/switch/add secrets/push.
- The queue runner owns Git and will push this branch.
