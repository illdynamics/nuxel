# Nuxel S10+ GNSS / GPS agent handoff pack

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte` / Exynos 9820  
**Observed GNSS transport:** Broadcom BBD over SPI/SSP; live device modalias `spi:BCM4773`; `/dev/ttyBCM` is packet transport, **not NMEA**.

## What this pack is — and is not

This is an extraction and engineering handoff, not a prebuilt firmware flash bundle. It contains:

- the relevant Nuxel reports, runtime inventory, diagnostic, and reflash plan copied from the supplied repository;
- an extraction script for an owner-supplied, unpacked stock Android filesystem for the exact `SM-G975F` model;
- a verifier that records hashes, ELF architecture, interpreter, and `DT_NEEDED` dependencies;
- a handoff brief with the known vendor components and integration blockers.

It **does not** contain Samsung proprietary GNSS binaries or an authenticated Broadcom sensor-hub patch. The repository did not contain those files. Do not substitute a Pixel/BCM47765, older BCM4773/BCM47752, another Galaxy model, or a random file named `SensorHub.patch`. The hardware/firmware revision match is still unproven.

## Quick start

1. Obtain a stock firmware/root filesystem for **your own SM-G975F / beyond2lte**. Do not use SM-G975N, S10e, S10, Note, Pixel, or generic Exynos blobs.
2. Unpack/decrypt the Samsung firmware and mount/extract `vendor` and `system` filesystems read-only. If you already have a directory tree with `vendor/` and `system/`, use that directory directly. The script does not unpack `.tar.md5`, `.lz4`, sparse images, or `super.img` itself.
3. Run:

   ```bash
   ./scripts/extract-s10plus-gnss.sh /path/to/unpacked-stock-rootfs ./out
   ./scripts/verify-extracted.sh ./out
   ```

   If you mounted only the vendor partition, pass its mount root; the script recognizes `bin/`, `etc/`, `lib/`, and `lib64/` relative to that root and stores them under `payload/vendor/`.
4. Give `out/` and `agent/AGENT-HANDOFF.md` to the Nuxel agent. Do not flash the output as-is.

## Critical architecture warning

The S10+ vendor stack is Android userspace: `lhd`/`gpsd`/GNSS HAL are built for Android's Bionic linker, Android init/HIDL/Binder environment, and a Samsung vendor ABI. Copying those files into Fedora/Nuxel does not make them executable or compatible. The verifier is intended to expose this dependency closure, not certify portability.

For pure Nuxel, the preferred outcome remains a native BBD/LHD protocol implementation plus the exact board patch. Use the Android runtime only as a controlled protocol reference or as a separately isolated compatibility environment after legal/technical review.

## Safety

- Extraction scripts read the supplied filesystem and write only to the output directory.
- No `adb`, `fastboot`, `heimdall`, `dd`, `twrp`, `reboot`, device-node open, GPIO write, or flash operation is performed.
- Do not power the GPS rail or write `/dev/bbd_patch` until firmware identity, loader ABI, power sequencing, and rollback are confirmed.
- A `READY` file in the extraction output means files were found, **not** that GPS is operational.

## Pack contents

- `agent/AGENT-HANDOFF.md` — detailed implementation instructions and acceptance criteria.
- `agent/TARGET-FILE-MANIFEST.md` — expected runtime/config files and confidence labels.
- `scripts/extract-s10plus-gnss.sh` — read-only source extraction.
- `scripts/verify-extracted.sh` — checksums and ELF/dependency inventory.
- `repo-evidence/` — exact relevant files copied from the user-provided Nuxel repo, plus `AUDIT-FINDINGS.md`.
- `reference/UPSTREAM-REFERENCES.md` — external source URLs and what each does/does not prove.

The extractor checks build.prop identity for `SM-G975F` / `beyond2lte` and rejects a known `SM-G975N` source. Only set `ALLOW_UNVERIFIED_SOURCE=1` if the filesystem lacks build.prop and you have independently verified the exact model/build; the extraction log will flag that override.
