# Captured device release assets

`release/s10plus/` holds bytes captured from the owner's physical Samsung
Galaxy S10+ (SM-G975F). The GitHub Release workflow publishes them verbatim and
verifies them with `tools/release/verify-installed-image.py`.

- `nuxel-installed-s10plus-boot.img.gz` — the exact BOOT partition read back
  from the handset on 2026-10-30 (`6e998acf…`, 57,671,680 bytes), i.e. the
  splash-fixed image that was running on the phone when this release was cut.
- `nuxel-installed-s10plus-userspace-files.txt.gz` — SHA-256 inventory of the
  installed userspace (4,238 entries: 4,062 files + 176 symlinks), captured
  from the running phone on 2026-10-30 after the PWNAGE-37000/38000 deployment.
- `INSTALLED-IMAGES.json` — provenance, header fields, payload hashes and the
  full-partition readback hash.

The captured BOOT image and userspace inventory are the bytes published with
Nuxel v0.7.4-beta. They were originally captured for the v0.7.3-beta handset image;
this release carries them forward because v0.7.4-beta is a userspace, audio,
location and documentation update, not a new BOOT/kernel build. The root filesystem is a
live mounted ext4 filesystem; no consistent block snapshot is claimed. See
[`docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md`](../docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md)
for the original capture design and
[`docs/releases/v0.7.4-beta.md`](../docs/releases/v0.7.4-beta.md) for this
release's current-state notes.
