# Captured device release assets

`release/s10plus/` holds bytes captured from the owner's physical Samsung
Galaxy S10+ (SM-G975F). The GitHub Release workflow publishes them verbatim and
verifies them with `tools/release/verify-installed-image.py`.

- `nuxel-installed-s10plus-boot.img.gz` — the exact A27 BOOT image installed on
  the handset (`48ad61af…`, 51,605,504 bytes).
- `nuxel-installed-s10plus-userspace-files.txt.gz` — SHA-256 inventory of the
  installed userspace (2,959 entries: 2,831 files + 128 symlinks), refreshed
  from the running phone after the A77 deployment (v0.6.6-beta sources);
  it is republished unchanged with v0.7.2-beta; the PWNAGE-30000..36000 live userspace deltas were deployed from the same v0.7.2-beta sources.
- `INSTALLED-IMAGES.json` — provenance, header fields, payload hashes and the
  full-partition readback hash.

The BOOT image is unchanged by the v0.7.2-beta release; its
partition and image hashes were re-verified on 2026-10-26. The root filesystem
is a live mounted ext4 filesystem; no consistent block snapshot is claimed. See
[`docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md`](../docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md).
