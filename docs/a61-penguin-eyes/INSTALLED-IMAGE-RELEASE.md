> **Current capture (v0.7.3-beta, 2026-10-30).** This document records the
> original A61/A27 capture design. The checked-in `release/s10plus/` assets were
> refreshed from the live phone on 2026-10-30: the BOOT image is now
> `6e998acf…` (57,671,680 bytes, the complete partition) and the userspace
> inventory is `da024bd0…` gz / 4,238 entries. See
> [`docs/releases/v0.7.3-beta.md`](../releases/v0.7.3-beta.md).

# Release output: the exact image installed on the S10+

**Captured:** 2026-10-23 (Europe/Amsterdam) from the owner's Samsung Galaxy S10+
(SM-G975F, beyond2lte, serial `R58M75KDB2X`), repository HEAD
`d5347532d61a5c1aed708bdf2b7005e1b71a1fb0` on `nuxel/A55-pwnage-4000`.

## What the workflow used to publish

The `s10plus` job rebuilt a source image in CI and published that rebuild. The
rebuild is an **A25** boot image (`kernel ad37422c…`, `initramfs be7c2f83…`,
`boot.img 9a71dcc0…`). The handset is **not** running that image: it is running
the A27 boot image flashed on 2026-10-16 (`boot.img 48ad61af…`,
`kernel e104da7e…`, `ramdisk 83c4f8cc…`). Publishing only the rebuild was
therefore not "the exact installed image".

## What the workflow publishes now

`release/s10plus/` contains a capture taken directly from the phone and is
verified fail-closed by `tools/release/verify-installed-image.py` before any
release is created:

| Asset | Bytes | SHA-256 |
|---|---:|---|
| `nuxel-installed-s10plus-boot.img.gz` | 51,605,504 (22,610,918 gz) | boot `48ad61afa91b6fe50278443ecae0695724f706a80de383e0acb021d030620cea`; gz `174cd2d1…` |
| `nuxel-installed-s10plus-userspace-files.txt.gz` | 366,654 (129,475 gz) | `fa8c3d61…`; gz `20aa0946…` (A77 refresh, 2026-10-26) |
| `INSTALLED-IMAGES.json` | — | provenance + all hashes |

The boot capture is the first 51,605,504 bytes of `/dev/sda14`, i.e. exactly the
A27 image that boots the handset. The full partition is 57,671,680 bytes; the
remaining 6,066,176 bytes are stale tail bytes from an older, larger candidate
(S-Boot reads only the header-declared sizes). The full-partition readback hash
`07041ba7…` is recorded in the manifest for verification.

The userspace inventory is `sha256sum` + `stat` over every Nuxel-installed file
under `/usr/lib/nuxel`, `/usr/libexec/nuxel`, `/usr/bin`, `/usr/local/bin`,
`/usr/share/nuxel`, `/usr/share/applications`, `/etc/nuxel`, `/etc/systemd/system`,
`/etc/dbus-1` and `/etc/polkit-1` — 2,959 entries after the A77 refresh
(2,831 regular files + 128 symlinks; the earlier capture listed regular files
only).

## Why the root filesystem is not shipped as a byte image

`/dev/sda31` is a live, mounted read-write ext4 filesystem. A block-device stream
taken while the phone is running is not a consistent filesystem snapshot, and an
unfrozen capture would silently mix writes from running services. The release
therefore ships the exact boot image (the actual flashed image) plus a hash
inventory of the installed userspace, and does **not** present a live rootfs
stream as an exact image. A consistent rootfs snapshot needs an owner-approved
freeze or a maintenance-window remount and is deliberately out of scope here.

## Workflow gate

`.github/workflows/release.yml` now:

1. runs `python3 tools/release/verify-installed-image.py --json` before
   packaging and fails the release job on any mismatch;
2. copies the captured image, the userspace inventory and
   `INSTALLED-IMAGES.json` into `dist/`;
3. includes them in `SHA256SUMS.txt` and in `RELEASE-NOTES.md`, explicitly
   labelling the CI-built A25 image as a source rebuild rather than the
   installed image;
4. uploads `dist/*.img.gz`, `dist/*.txt.gz` and `INSTALLED-IMAGES.json` to the
   GitHub **Latest** release (beta tag/title retained).

## Verification performed

```
$ python3 tools/release/verify-installed-image.py --quiet
installed-image: PASS — release asset is the exact image installed on the phone
```

The verifier checks the gzip stream, decompressed size and SHA-256, the
`ANDROID!` v1 header, `header_version=1`, `header_size=1648`, page size 2048,
the load addresses, `nuxel.device=s10plus`, a raw arm64 `Image` (never gzip),
and kernel/ramdisk hashes. The captured image was also parsed independently and
its kernel payload was compared against the A27 flash receipt.
