# Captured device release assets

`release/s10plus/` holds bytes captured from the owner's physical Samsung
Galaxy S10+ (SM-G975F). The GitHub Release workflow publishes them verbatim and
verifies them with `tools/release/verify-installed-image.py`.

- `nuxel-installed-s10plus-boot.img.gz` — the exact BOOT partition read back
  from the handset on 2026-11-01 (`2cbc5085…`, 57,671,680 bytes): the
  kbase/userns/NFC kernel that runs today.
- `nuxel-installed-s10plus-userspace-files.txt.gz` — SHA-256 inventory of the
  installed userspace (5,873 entries: 5,656 files + 217 symlinks), captured
  from the running phone after the PWNAGE-47000..54000 deployment.
- `INSTALLED-IMAGES.json` — provenance, header fields, payload hashes and the
  full-partition readback hash, written by
  `tools/release/update-installed-manifest.py` from the captured bytes.
- `gpu/` — the hash-pinned kbase Mesa (`libEGL_mesa.so.0.0.0`,
  `libgallium_dri.so`), wlroots 0.19 linear-dmabuf build, graphics-profile
  helper and profiles that are installed into a clean image, with `SHA256SUMS`.
  These are the exact bytes running on the phone; the rootfs builder fails
  closed if they are missing (`NUXEL_REQUIRE_KBASE=1`) or altered.

The captured BOOT image and userspace inventory are the bytes published with
Nuxel v0.7.5-beta, captured from the handset on 2026-11-01. Reproduce them
read-only with `tools/release/capture-installed-image.sh root@<phone>`; the
release workflow gates them with
`tools/release/verify-installed-image.py` before publishing. The root
filesystem is a live mounted ext4 filesystem; no consistent block snapshot is
claimed. See
[`docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md`](../docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md)
for the capture design and
[`docs/releases/v0.7.5-beta.md`](../docs/releases/v0.7.5-beta.md) for this
release's current-state notes.
