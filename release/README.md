# Captured device release assets

`release/s10plus/` holds bytes captured from the owner's physical Samsung
Galaxy S10+ (SM-G975F). The GitHub Release workflow publishes them verbatim and
verifies them with `tools/release/verify-installed-image.py`.

- `nuxel-installed-s10plus-boot.img.gz` — the exact A27 BOOT image installed on
  the handset (`48ad61af…`, 51,605,504 bytes).
- `nuxel-installed-s10plus-userspace-files.txt.gz` — SHA-256 inventory of the
  installed userspace (1,312 entries).
- `INSTALLED-IMAGES.json` — provenance, header fields, payload hashes and the
  full-partition readback hash.

The root filesystem is a live mounted ext4 filesystem; no consistent block
snapshot is claimed. See
[`docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md`](../docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md).
