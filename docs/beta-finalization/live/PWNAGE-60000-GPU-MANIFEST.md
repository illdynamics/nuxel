# PWNAGE-60000 GPU pin manifest

Canonical artifact: `release/s10plus/gpu/gpu-manifest.json`  
Checksums: `release/s10plus/gpu/SHA256SUMS`  
Generator: `tools/s10plus/a67/gen-gpu-manifest.py`  
Source pins: `tools/s10plus/a67/gpu-build-pins.env`

## Sources

| Component | Pin |
|---|---|
| Mesa (JimVulkan/mesa-unified-drivers) | `a5010bb447ae34e697cb917c2d387272063e9fd8`, `26.3.0-devel (git-a5010bb447)` |
| Mesa patch | `tools/s10plus/a67/mesa-kbase-wayland-wsi.patch` |
| wlroots 0.19.3 | tag peeled commit `88a869855742281c98c22cab9641b317b8d065ef` |
| wlroots patch | `tools/s10plus/a67/wlroots-kbase-linear-dmabuf.patch` |
| glvnd | Fedora `libglvnd-1.7.0-8.fc43.aarch64` |
| target ABI | `aarch64-glibc-2.42`, Fedora 43 |

`build-mesa-kbase-wayland.sh` and `build-wlroots-kbase-linear.sh` now fetch,
detach to the full commit, reset/clean the worktree and `git apply --check` the
recorded patch.  No branch name or moving head is accepted.

## Files in the release set

The manifest records install path, mode, SHA-256, ELF build ID/SONAME where
applicable, and required status for:

- `libEGL_mesa.so.0.0.0`
- `libgallium_dri.so`
- `libwlroots-0.19.so`
- `nuxel-graphics-profile`
- `graphics-profile.json`
- `egl-kbase.json`
- `50_mesa.json`
- `nuxel-gpu-status`
- `nuxel-wayland-gpu-wrapper.sh`
- `nuxel-session.sh`
- symlinks:
  - `/usr/lib64/libEGL_mesa.so.0 -> libEGL_mesa.so.0.0.0`
  - `/usr/lib64/dri/panfrost_dri.so -> ../libgallium_dri.so`
  - `/usr/lib64/dri/exynos_dri.so -> ../libgallium_dri.so`

The kbase EGL probe source hash is recorded under `probe` and the image builder
requires `/usr/lib/nuxel/nuxel-kbase-egl-probe` in a release image.

## Verify

```sh
tools/s10plus/a67/sync-gpu-release-assets.sh   # copy helpers + regenerate
tools/s10plus/a67/nuxel-gpu-image-verify.sh <rootfs-stage> \
  --manifest release/s10plus/gpu/gpu-manifest.json
```

Verification fails closed on:

- missing/wrong file hash or executable mode;
- stock `.nuxel-bak` EGL link;
- missing probe in a release stage;
- profile default other than `gpu-rendered-shm-presented`;
- missing `software-safe` fallback;
- `gpu-rendered-dmabuf-presented` or `fully-accelerated` marked available;
- unguarded PWN36000 boot bootstrap or staged/deployed session mismatch;
- release checksum file mismatch.

A runtime copy of the manifest and `gpu-SHA256SUMS` is installed at
`/usr/share/nuxel/`; the verifier then enforces the per-file manifest hashes
even though the release asset files themselves are not stored there.
