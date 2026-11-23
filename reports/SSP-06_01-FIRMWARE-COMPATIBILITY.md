# SSP-06_01 — Firmware Identity (re-verified against the live device this mission)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01 (final unblock)

## 0. Verdict

```
FIRMWARE_IDENTITY = CONFIRMED
SAME BYTES ON THE DEVICE AS IN THE RUNNING KERNEL AS IN THE REPOSITORY SOURCE
```

This mission upgraded the previous “recompute from the repository header” check to a
**three-way byte comparison** that includes the firmware the running kernel actually
serves:

1. `/dev/bbd_patch` on the live handset (read-only, via `sudo cat`);
2. the kernel source tree used to build the running kernel
   (`r_os/bbd_patch_file_beyond.h`);
3. the repository build manifest.

## 1. Three-way comparison

| Artefact | SHA-256 | Size |
|---|---|---|
| `/dev/bbd_patch` container (live device) | `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72` | 897113 B |
| `bbd_patch_file_beyond.h` container (kernel source tree) | `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72` | 897113 B |
| Decoded `<Blob=…>` firmware payload (both) | `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d` | 438895 B |

Decoded blob comparison: `IDENTICAL_BLOB = True` (byte-for-byte).

## 2. Header fields (live device)

```
<FormatVersion=0x00010003>
<Crc=193>
<BlobLength=438895>
<AsicVersion=0x004775B0>
<ChangeList=4294967295>
<PatchAddress=0x00800161>
```

(479 records, all tag `0xF1`, first destination `0x00800000`.) `<Crc>` is a vendor
field, not IEEE CRC-32; it is carried, not reinterpreted.

## 3. What was verified on the device, this mission

The downloader's own parser was compiled unchanged except for the patch path and a
verify-only short-circuit (host harness, no device I/O), then run against the
**device's** `/dev/bbd_patch` bytes:

```
bbd-flash: container 897113 B asic=0x004775b0 blobLen=438895 entry=0x00800161 crc_hdr=0x000000c1 decoded=438895
bbd-flash: patch verified: 479 records (BCM47752, entry=0x00800161)
bbd-flash: first memory-write dest=0x00800000 (entry=0x00800161)
bbd-flash: exit 0 (GENUINE_VERIFIED_SUCCESS)
```

i.e. the exact downloader that the trial would use **accepts the exact bytes the
handset would hand it**. This removes the previous “matches the header but not
proven to match the running kernel” caveat.

Note on `Crc=193`: decimal 193 = `0xC1`; the harness prints the header field
verbatim (`crc_hdr=0x000000c1`). No CRC conformance is claimed.

## 4. Structural facts re-derived

| Fact | Value | How |
|---|---|---|
| ASIC version | `0x004775b0` | header + parser |
| Entry (PatchAddress) | `0x00800161` | header + parser |
| First F1 destination | `0x00800000` (≠ entry) | record walk |
| Record count | 479, all `0xF1` | record walk |
| Blob length | 438895 | declared == decoded |
| Record walk | exact (offset == length) | parser |

## 5. Remaining runtime-only unknowns (unchanged)

- RAM load window (`0x00800000…`) accepted by *this* die at runtime.
- Stepping-specific acceptance (ASIC match ≠ stepping match).
- ROM/application acceptance of the record stream (post-download GetVersion).

These are properties of the physical die, not of the bytes, and are only settled by
the bounded trial.

## 6. Provenance

- Device: `SM-G975F` (`beyond2lte`), stock build `G975FXXS9DTK9`; matched vendor
  `lhd` SHA-256 `6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`.
- Running kernel: `4.14.253-gf7194c1d15ed-dirty` (built from this tree).
- Device copy preserved at `/var/lib/nuxel/ssp-06_01/staging/bbd_patch_file_beyond.h.gz`
  (gzip of the exact kernel-tree header; decompressed SHA-256 =
  `0b53f3b0…`).
