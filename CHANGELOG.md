# Changelog

All notable changes to the Nuxel Phone OS repository are documented here.

The canonical version lives in [`VERSION`](VERSION) and is bumped in lockstep
across the shell apps, the PWA manifest, the device `APKBUILD`s, the VM tooling
and the OTA builder (see *Versioning* below).

---

## [v0.3.2-alpha] — 2026-10-13

**Theme:** make the release CI build the **same complete rootfs** a local build
does — the boot splash is no longer silently dropped.

Reported symptom: the S10+ rootfs published by CI still held only ~20 MB of
content while a local build's staging tree was ~60 MB. Root cause:
`images/mkrootfs.sh` builds the Plymouth boot theme through
`tools/build-nuxel-boot-theme.sh`, which needs **`ffmpeg`** to extract the
animation frames. `.github/workflows/release.yml` never installed `ffmpeg`, and
that step is deliberately non-fatal, so it logged a warning and continued — the
rootfs shipped without the ~50 MB frame sequence (96 PNGs) and the
`nuxel.plymouth` / `nuxel.script` descriptors. `tools/verify-artifacts.sh`
passed because it never checked for the theme.

Verified against the artifacts: a local rootfs image carries 96 `frame-*.png`
files (99 PNG signatures incl. wallpapers) and a `plymouth/` payload; the
v0.3.1-alpha CI image carried 2 PNGs (wallpapers only) and no `plymouth` payload
at all — i.e. 19.9 MB of non-zero inode data vs ~88 MB locally.

### Fixed

- **CI installs `ffmpeg`.** The Release workflow build dependencies now include
  `ffmpeg`, so `images/mkrootfs.sh` -> `tools/build-nuxel-boot-theme.sh`
  produces the Plymouth theme (96 PNG frames + `nuxel.plymouth` / `nuxel.script`)
  in CI exactly as it does on a dev box. This closes the local-vs-CI rootfs gap.
- **`tools/verify-artifacts.sh` is fail-closed on the boot splash.** For both
  `g7power` and `s10plus` it now requires, inside the ext4 rootfs:
  - `/usr/share/nuxel/boot/nuxel-boot-animation.mp4` (size-checked via `debugfs`,
    must be >= 1 MB), and
  - the generated Plymouth theme
    (`/usr/share/plymouth/themes/nuxel/nuxel.plymouth` + `frame-0001.png`).

  A rootfs that silently lost its theme — the exact v0.3.1-alpha CI failure — is
  now a hard failure instead of a green build.
- **Version bump to `v0.3.2-alpha`** across `VERSION`, README/design/docs, the
  flash guides, the device `APKBUILD`s, the shell/PWA manifests, the VM tooling
  and the OTA builder. The device `APKBUILD`s and shell/PWA `meson.build`s, which
  the previous bump left at `0.3.0-alpha`, are now in lockstep.

### Notes

- No hardware/boot status changed: still **0 of 3 phones verified booting**.
- The G7 Power rootfs gains the boot splash in CI too (same shared builder), so
  both bring-up phones now ship the full userspace + theme.

---

## [v0.3.1-alpha] — 2026-10-13

**Theme:** make the bring-up rootfs **actually contain a userspace**, and make
the artifact gate stop a near-empty image from ever being published as
"complete".

Reported symptom: the S10+ release archive was only ~21 MB (a 22 MB boot image
plus a 26 MB rootfs holding a **44 KB / 10-file** overlay), while a local build's
rootfs was ~60 MB+. Root cause: `images/mkrootfs.sh` declared every userspace
step but **never called them** — the script was a no-op that exited 0, so every
"rootfs" was only the per-device config overlay.

### Fixed

- **`images/mkrootfs.sh` now actually builds the userspace.** Added the missing
  driver (`main`): clean -> Flatpak/fallback base -> core services -> native apps
  -> security configs -> assets -> Plymouth theme -> directory/permission setup
  -> optional dm-verity image -> summary. Previously none of these ran, so
  `/usr/bin/nuxel-bridge`, `/etc/nuxel/paths.conf`, the AppArmor/nftables/sysctl
  configs and the boot theme were absent from every rootfs image.
- **`tools/verify-artifacts.sh` is now genuinely fail-closed.** It no longer
  accepts an image on a magic number alone:
  - boot images must carry a real kernel + ramdisk + device tree (Android v1
    header sizes must be non-zero) — an empty/placeholder header fails;
  - rootfs images must contain the expected payload (per-device config plus the
    Nuxel userspace core `/usr/bin/nuxel-bridge`), verified by reading the ext4
    contents with `debugfs` — the 44 KB S10+ image that shipped in
    v0.3.0-alpha is now a hard failure;
  - `NUXEL_S10PLUS_UBOOT=1` makes `u-boot-beyond2lte.img` a required artifact.
- **Rootfs images are sized from real content.** The 512 MB minimum floor in
  both device builders, combined with a `resize2fs -M` that cannot always shrink
  a many-small-file filesystem, produced a **512 MB** G7 Power rootfs in CI. The
  floor is now 64 MB and the image is sized from the staging tree (content + 25%
  + slack).
- **The S10+ build no longer reports a phantom `INCOMPLETE`.** U-Boot is a
  mainline-stretch artifact; the supported Phase-1 downstream/heimdall set is
  `boot.img` + `rootfs.img`, exactly as the flash guide documents. U-Boot is
  built when present and only fails the build when explicitly required
  (`NUXEL_S10PLUS_UBOOT=1`).
- **Version bump to `v0.3.1-alpha`** across `VERSION`, README/design/docs, the
  flash guides, PWA/shell manifests, VM tooling and the OTA builder.

### Notes

- **There is no `userdata.img`** by design in Phase 1: the rootfs image *is* the
  userdata payload (G7 Power: shared `userdata`; S10+: `SYSTEM`/`userdata`), so
  the archive ships `nuxel-*-rootfs.img`, not a separate `userdata.img`.
- **`lk2nd` is G7 Power-only** (`msm8953`). The S10+ is Exynos and never uses
  `lk2nd`; its chain is stock `S-Boot` -> (optional `u-boot-beyond2lte.img`) ->
  `nuxel-beyond2lte-boot.img`.
- Device-proprietary vendor blobs (`firmware/*/blobs/vendor-*`) remain
  **unshippable** (gitignored): CI builds the rootfs from repo sources only, so a
  CI image is smaller than a local one that has pulled those blobs. The gate
  verifies the repo-provided payload, not the non-redistributable firmware.

---

## [v0.3.0-alpha] — 2026-10-13

**Theme:** make the release pipeline **fail-closed and genuinely green** for the
two bring-up phones (**G7 Power** `g7power`/ocean and **Galaxy S10+**
`s10plus`/beyond2lte). Every build/release step for both phones now actually
produces its artifact, and the workflow can no longer report success when a
kernel / initramfs / boot image / rootfs is missing or invalid.

### Changed

- **`mustang` (Google Pixel 10 Pro XL) removed from the release workflow** for
  now. The build matrix is `g7power` + `s10plus` only; the `prepare` job filters
  any other device key out (with a warning) and fails if nothing supported is
  requested. `images/build.sh` still refuses non-mustang devices except in the
  new initramfs-only mode.
- **Per-device `sha256sums.txt` in every release archive.**
  `images/g7power/build.sh` and `images/s10plus/build.sh` now emit
  `sha256sums.txt` alongside the images, so the flash guides can verify each
  flashed artifact (`nuxel-ocean-boot.img`, `nuxel-ocean-rootfs.img`, `lk2nd.img`
  / `nuxel-beyond2lte-boot.img`, `nuxel-beyond2lte-rootfs.img`) before writing
  it to the device.
- **Version bump to `v0.3.0-alpha`** across `VERSION`, README/design/docs,
  APKBUILDs, PWA/shell manifests, services and the OTA builder.

### Fixed

- **Release workflow no longer goes green on a failed build.** All
  `continue-on-error: true` flags were removed from the build matrix, the
  "Package device artifact" step is no longer `if: always()` + best-effort, the
  upload step uses `if-no-files-found: error`, and the `publish release` job now
  runs only when the whole build matrix succeeded (`if: needs.build.result ==
  'success'`). A device whose kernel/images fail leaves the run **red** and no
  GitHub Release is created.
- **New strict artifact gate `tools/verify-artifacts.sh`.** After the image
  build, CI verifies (per device) that the kernel `Image.gz` is a real
  gzip-compressed **ARM64 Linux Image** (`0x644d5241`), that the board DTB is a
  valid FDT (`0xd00dfeed`), that the boot image carries the `ANDROID!` header,
  that the rootfs is `ext4` (`0x53EF` superblock magic), and — on G7 Power —
  that `lk2nd.img` is present. Any miss fails the job with `::error::`.
- **S10+ boot image now builds in CI.** The downstream Exynos 9820 tree ships
  only the SoC base DTB (`dts/exynos/exynos9820.dtb`) plus per-revision overlays
  (`dts/samsung/exynos9820-beyond2lte_eur_open_<rev>.dtbo`); the previous build
  looked for a board `.dtb` that is never produced, so `images/s10plus/build.sh`
  aborted with "No beyond2lte DTB found". It now merges base + highest-revision
  overlay into `exynos9820-beyond2lte.dtb` with `fdtoverlay`
  (`device-tree-compiler`) before packing, matching the previously-built local
  artifact byte-for-byte (376101 bytes, rev 26).
- **Shared initramfs is now a first-class step.** `images/build.sh` gained
  `--initramfs-only`, which assembles the device-agnostic initramfs, mirrors it
  to `build/boot-artifact/` and exits 0 — instead of the old "mustang dispatcher"
  invocation that exited 3 whenever the (now-removed) mustang kernel was absent.
- **G7 Power `lk2nd.img` is now built in CI.** New
  `boot/g7power/lk2nd/build-lk2nd.sh` clones `msm8916-mainline/lk2nd` and builds
  `lk2nd-msm8953` with the `arm-none-eabi` toolchain, producing the
  `lk2nd.img` that `images/g7power/build.sh` copies into the release. Without it
  the G7 Power artifact set was silently incomplete.

### Notes

- `g7power` kernel build time varies with runner speed (~25–47 min for the full
  mainline `msm8953` tree: `Image.gz` + `dtbs` + `modules`); both bounds are
  normal. The `s10plus` downstream 4.14 kernel builds in ~15 min.

## [v0.2.2-alpha] — 2026-10-13

**Theme:** pre-release fix on top of v0.2.1-alpha — make the **S10+** and the
**Pixel 10 Pro XL (`mustang`)** kernel builds actually produce an `Image.gz` in
CI. No other behaviour changes; the readiness picture is unchanged.

### Fixed

- **S10+ kernel build (CI).** v0.2.1-alpha forced `CROSS_COMPILE` and dropped
  compiler-unsupported KCFLAGS, but the build still failed on the runner's GCC 13
  because the downstream 4.14 Exynos 9820 tree hard-codes `-Werror` in two places
  a `KCFLAGS` relaxation cannot reach:
  - **per-category promotions** in the top `Makefile`
    (`KBUILD_CFLAGS += $(call cc-option,-Werror=strict-prototypes)` and friends,
    `Makefile:935-947`). GCC's "the more specific option wins, independently of
    order" rule means the generic `-Wno-error` appended via KCFLAGS does **not**
    downgrade them, so the build died on
    `block/blk-crypt.c:213: error: function declaration isn't a prototype
    [-Werror=strict-prototypes]`;
  - **per-directory flags appended after `KBUILD_CFLAGS`** on the cc command
    line — the bcmdhd Wi-Fi driver's
    `DHDCFLAGS += -Wall -Werror -Wstrict-prototypes` → `EXTRA_CFLAGS` →
    `ccflags-y`. That re-enables a general `-Werror`, so the build died on
    `drivers/net/wireless/broadcom/bcmdhd_101_16/wl_android.c:12016: error: the
    comparison will always evaluate as ‘true’ … [-Werror=address]`
    (`cc1: all warnings being treated as errors`).

  `kernel/s10plus/build-kernel.sh` now runs the new
  `tools/kernel-relax-werror.sh`, which strips the `-Werror` /
  `-Werror=<diag>` / `-Werror-<diag>` tokens (and whole
  `$(call cc-option,-Werror=...)` expressions) from the scratch tree's **source**
  Makefiles — leaving `-Wno-error…` untouched and avoiding the kbuild-internal
  `scripts/Makefile.*` feature-probe helpers. `DEFAULT_KCFLAGS` also gains
  `-Wno-error=strict-prototypes`, `-Wno-error=date-time` and
  `-Wno-error=designated-init` (each still probed against the selected compiler
  and dropped if unsupported). Idempotent; the tree is a throwaway clone.
- **Pixel 10 Pro XL (`mustang`) kernel build — patch.** The committed
  `kernel/google-pixel-10-pro-xl/patches/0001-nuxel-phone-features.patch`
  declared `@@ -0,0 +1,108 @@` for a hunk that adds only 107 lines
  (`drivers/nuxel/nuxel-core.c`), so `git apply --check` failed
  (`error: corrupt patch`) and `kernel/build-kernel.sh` aborted with
  `error: patch not applied and does not apply` before it ever configured or
  built. The hunk header is corrected to `@@ -0,0 +1,107 @@`; the patch now applies
  cleanly to the `android16-6.12` GKI common tree.
- **Pixel 10 Pro XL (`mustang`) compiler-diagnostics relaxation.**
  `kernel/build-kernel.sh` now neutralises the GKI tree's global
  `CONFIG_WERROR=y` (which lands in `KBUILD_CPPFLAGS` via
  `scripts/Makefile.extrawarn`) with a probe-checked
  `DEFAULT_KCFLAGS="-Wno-error=parentheses -Wno-error"` — KCFLAGS is appended to
  `KBUILD_CFLAGS`, i.e. *after* the `-Werror`, so it wins — fixing e.g.
  `fs/fuse/dev.c:458: … [-Werror=parentheses]`. It also runs
  `tools/kernel-relax-werror.sh` to strip the per-directory `-Werror`
  (`arch/arm64/kernel/vdso32`, aic7xxx, lpfc). The generated asm/uapi headers are
  now produced before `archprepare` (`make asm-generic archprepare`) so the
  host-tool gate builds on a pristine tree.

### Added

- `tools/kernel-relax-werror.sh` — idempotent helper that strips hard-coded
  `-Werror` from a kernel source tree's Makefiles (used by the `mustang` and
  S10+ kernel dispatchers).

### Changed

- **Repository-wide version bump v0.2.1-alpha → v0.2.2-alpha** in: `VERSION`,
  `README.md`, `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with a
  new 0.2.2-alpha release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`) and the OTA builder (`images/build-ota.sh`).
- `README.md` gains a short *What's new in v0.2.2-alpha* section.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.2-alpha`.
- Historical run logs (under `vm/logs/`) and the point-in-time VM recon report
  (`vm/utm-state-report.md`) are left untouched as record.

---

## [v0.2.1-alpha] — 2026-10-13

**Theme:** pre-release fix on top of v0.2.0 — make the **S10+ kernel build**
succeed in CI. No other behaviour changes; the readiness picture is unchanged.

### Fixed

- **S10+ kernel build (CI / any non-Samsung host).**
  `kernel/s10plus/build-kernel.sh` never overrode the downstream Samsung tree's
  hardcoded toolchain. The Exynos 9820 `Makefile` line 316 sets

  ```
  CROSS_COMPILE ?= $(srctree)/toolchain/gcc-cfp/gcc-cfp-jopp-only/aarch64-linux-android-4.9/bin/aarch64-linux-android-
  ```

  a tree-internal Android GCC that is **not** shipped with the source. A bare
  `make` therefore failed before compiling anything:

  ```
  make[1]: .../aarch64-linux-android-gcc: No such file or directory
  Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: -fstack-protector-strong not supported by compiler
  make[1]: *** [Makefile:1267: prepare-compiler-check] Error 1
  ```

  which cascaded into `[nuxel-s10plus-build][error] Kernel image not found:
  .../arch/arm64/boot/Image.gz` and an empty `build/out/s10plus/` (the GitHub
  Actions job logged the kernel step as exit 2 and packaged nothing). The
  wrapper now sets `CROSS_COMPILE` (default `aarch64-linux-gnu-`, matching the
  `gcc-aarch64-linux-gnu` package CI installs) and passes it on **every** `make`
  invocation, so the command-line assignment overrides the tree's `?=` default.
  `--cross <prefix>` is now honoured (previously accepted and silently ignored),
  and `--cross ''`/`CROSS_COMPILE=` yields a native aarch64 host build.
- **S10+ kernel build, second toolchain bug: version-specific `KCFLAGS`.**
  With the toolchain path fixed, the build still died at the same
  `prepare-compiler-check` — but no longer because of a missing compiler.
  `DEFAULT_KCFLAGS` contained `-Wno-error=return-mismatch`, and `-Wno-error=<x>`
  is a **hard error** when the compiler has no `-W<x>` (GCC 13 does not know
  `-Wreturn-mismatch`; it is GCC >= 14). The downstream tree appends `$(KCFLAGS)`
  to `KBUILD_CFLAGS` (`Makefile:963`), so the unknown flag made **every**
  `cc-option` probe fail — producing the misleading
  `Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: -fstack-protector-strong not
  supported by compiler`. The wrapper now probes each relaxation flag against the
  selected compiler (`echo | $(CC) <flag> -c -x c - -o /dev/null`) and keeps only
  the supported ones: GCC 13 drops `-Wno-error=return-mismatch`; GCC 15 keeps it.
  Verified against GCC 13.4 (probe fails before, passes after) and GCC 15.2.

- **S10+ kernel build, third issue: the tree's global `-Werror`.** With the
  probe flag fixed the kernel finally compiled (`CC arch/arm64/...`), then died
  on a real warning promoted to an error:
  `arch/arm64/mm/fault.c: ... error: format '%lx' expects argument of type
  'long unsigned int', but argument 5 has type 'phys_addr_t' ... [-Werror=format=]`.
  The downstream Makefile compiles with a global `-Werror` (`Makefile:428`), so
  any `-Wall` warning is fatal. `DEFAULT_KCFLAGS` now ends with a bare
  `-Wno-error`; because `$(KCFLAGS)` is appended **last** to `KBUILD_CFLAGS`
  (`Makefile:963`), it downgrades the tree's `-Werror` (and its earlier
  `-Werror=<...>` set) back to warnings - while the specific
  `-Wno-error=<diag>` relaxations still cover GCC 14+ default-errors.

### Changed

- **Repository-wide version bump v0.2.0 → v0.2.1-alpha** in: `VERSION`,
  `README.md`, `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with a
  new 0.2.1-alpha release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`), and the OTA builder (`images/build-ota.sh`).
- `README.md` gains a short *What's new in v0.2.1-alpha* section.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.1-alpha`.
- Historical run logs (under `vm/logs/`) and the point-in-time VM recon report
  (`vm/utm-state-report.md`) are left untouched as record.

---

## [v0.2.0] — 2026-10-13

**Theme:** from a single mustang-only scaffold to a **three-target bring-up
repository**, with per-device orchestration, safety gates, consolidated device
docs, and a repository-wide version bump.

> ⛔ **Readiness headline (unchanged in spirit from v0.1.0):** Nuxel is still a
> **design scaffold + code prototype**. It is **not** a flashable phone OS. No
> target has booted Nuxel from a Nuxel-built image, and there is **no verified
> flashable artifact set** for any device.

### Added

- **Multi-device support with explicit selection.** `tools/nuxel-device-select.sh`
  resolves a device key (`--device` > `NUXEL_DEVICE` env > explicit error;
  aliases `s10plus|beyond2lte`, `g7power|ocean`) and every per-device script
  sources it and prints the resolved key before doing any work.
- **Per-device subtrees** for `firmware/`, `kernel/`, `device/`, `boot/`,
  `configs/` and `images/` for all three targets (`google-pixel-10-pro-xl`
  / mustang, `s10plus`, `g7power`).
- **Phase 0 device-inventory templates + build gates:**
  - `docs/g7power-device-inventory.md`
  - `docs/s10plus-device-inventory.md`
  - `docs/pixel10proxl-device-inventory.md`

  Every build/flash/firmware script refuses to run while load addresses or
  firmware filenames are still `PLACEHOLDER`/`UNKNOWN`.
- **G7 Power (Motorola Moto G7 Power, SDM632/msm8953, `ocean`) bring-up:**
  - On-device **stock-evidence** capture bundle —
    `phones/g7power/stock-evidence/` (partitions, props, dmesg, input devices,
    i2c, USB, firmware sysfs, vendor modules, etc.).
  - lk2nd chainloader docs and artifact — `boot/g7power/lk2nd/`.
  - QCDT boot-image packer `tools/build-qcdt-boot.py` (lk2nd-format DT table).
  - Boot-image cmdline patcher `tools/patch-boot-cmdline.py`.
  - Two-phase fastboot flash flow (`boot/g7power/flash.sh`), recovery
    (`boot/g7power/recovery.sh`), boot packer (`boot/g7power/pack-boot-v1.sh`),
    boot config (`boot/g7power/boot-config.txt`).
  - EDL (Qualcomm 9008) unbrick path documented.
  - Bring-up guide: `docs/g7power-bringup.md`; "do it now" checklist:
    `phones/g7power/g7power-go-guide.md`.
- **S10+ (Samsung Galaxy S10+, Exynos 9820, `beyond2lte`) bring-up:**
  - Exynos boot chain docs (S-Boot → U-Boot → Linux), the **no-fastboot**
    reality (TWRP + Download Mode / heimdall), Knox-tripped constraints,
    protected-partition list and anti-cross-flash rules.
  - Flash tooling: `boot/s10plus/flash.sh`, `flash-heimdall.sh`,
    `uboot-chainload.sh`, `pack-boot-v1.sh`, `recovery.sh`,
    `boot/s10plus/boot-config.txt`.
  - Firmware staging: `firmware/s10plus/` (`fetch-vendor-blobs.sh`,
    `gen-manifest.py`, `install-firmware.sh`, `verify-firmware.sh`, vendor
    firmware blob trees).
  - Bring-up guide: `docs/s10plus-bringup.md`; "do it now" checklist:
    `phones/s10plus/s10plus-go-guide.md`.
- **Pixel 10 Pro XL (mustang) prep:** Phase 0 inventory template + gate
  (`docs/pixel10proxl-device-inventory.md`) and reconciliation against the
  multi-device layout.
- **[`CHANGELOG.md`](CHANGELOG.md)** (this file).

### Changed

- **Repository-wide version bump v0.1.0 → v0.2.0** in: `VERSION`, `README.md`,
  `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with
  a new 0.2.0 release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver=0.2.0`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`, `vm/utm-state-report.md`), and the OTA builder
  (`images/build-ota.sh`).
- **README** rewritten around the multi-device reality: a new
  *What's new in v0.2.0* section, a restructured *Project Structure* table
  (`phones/`, `prompts/`), an updated *Honest Status* table (per-target rows,
  per-area scores), corrected documentation links, and per-device "go-guide"
  links.
- Documentation cross-references updated to the new `phones/` layout.

### Fixed

- **G7 Power touchscreen.** Root-caused the "no touch driver" dead end: the
  controller (ILI2117) is handled by mainline **`ili210x`**
  (`CONFIG_TOUCHSCREEN_ILI210X`, OF match `ilitek,ili2117`); the config had
  requested the **nonexistent** `CONFIG_TOUCHSCREEN_ILI2117`, so no driver was
  ever built. Config fixed and kernel rebuilt
  (`kernel/g7power/defconfig`, `configs/g7power/libinput/`).
- **G7 Power lk2nd black-screen packaging bug.** The payload boot image's DT
  region must be an lk2nd-format QCDT v3 table (12-byte header, 40-byte
  entries) — a raw FDT or a 20-byte Qualcomm header fails validation. Fixed via
  `tools/build-qcdt-boot.py` (DTB bytes unchanged; only packaging corrected).

### Moved / reorganised

- Device **documentation bundles** consolidated under [`phones/`](phones/):
  - `g7power/` → `phones/g7power/`
  - `s10plus/` → `phones/s10plus/`
  - `pixel10proxl/` → `phones/pixel10proxl/`
- Loose planning / analysis prompts consolidated under `prompts/`.
- All in-repo references (docs, scripts, APKBUILDs, config READMEs) updated to
  the new paths.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.0`.
- The historical provenance lines that describe an analysis *of the v0.1.0
  tree* (e.g. "Based on: Deep analysis of Nuxel v0.1.0 repo") are intentionally
  left at v0.1.0; run logs under `vm/logs/` are left untouched as historical
  record.

### Readiness assessment — v0.2.0

| Area | Score | Notes |
|---|---|---|
| Design/docs | 78% | Architecture, security model, PWA spec, three device doc bundles |
| Repo structure | 85% | Clean layout; device doc bundles consolidated under `phones/` |
| PWA apps | 45% | Manifests, SWs, JS exist — need integration testing |
| Native GTK apps | 25–35% | C source exists, not proven buildable on aarch64 |
| D-Bus bridge/portal | 30% | Python parses, dev-grade auth, not integration-tested |
| Sandbox/security | 20% | Configs exist, enforcement not wired end-to-end |
| Build system | 20% | Per-device dispatchers + inventory gates; still unproven on hardware |
| Flashable images | 0% | No verified boot artifact set produced |
| Pixel 10 Pro XL (mustang) | 5% | Public mustang Linux is UART/initramfs-level only |
| Galaxy S10+ (beyond2lte) | 10% | Bring-up: device package, gates, docs — no boot yet |
| Moto G7 Power (ocean) | 15% | Bring-up: touchscreen-driver fix, stock evidence, lk2nd/QCDT tooling |
| UTM VM | 25% | Scripts/docs exist, no VM image artifact produced |

**Overall: ~30–35% MVP scaffold. 0% verified flashable OS. ~40–45% patchable VM demo.**

### Still not done (honest gaps)

- **No target has booted a Nuxel-built image.** 0% verified flashable.
- **Phase 0 inventories are empty templates** — load addresses, firmware
  filenames and checksums remain `PLACEHOLDER`/`UNKNOWN` until filled from the
  physical devices. Every build/flash gate therefore stays closed.
- **Sandbox enforcement is not wired end-to-end** (namespaces + seccomp +
  Landlock + AppArmor + nftables configs exist; enforcement is not proven).
- **Native GTK4 apps are unproven on aarch64.**
- **No VM image artifact** is produced by the bootstrap (scripts/docs only).
- **Modem, camera and sensors are deferred** on both bring-up targets.

### Next (v0.3.0 candidates)

1. Fill the G7 Power and S10+ Phase 0 inventories from the real devices.
2. Produce real kernel + lk2nd + boot/rootfs images and attempt first boot.
3. Build a bootable UTM VM image artifact and run Phosh + bridge/portal.
4. Prove the sandbox enforces (namespaces/seccomp/Landlock/AppArmor/nftables)
   in an integration test.

---

## [v0.1.0] — 2026-05-10

**Baseline release: mustang-only design scaffold + code prototype.**

- Architecture blueprint, security model and PWA runtime specification.
- PWA shells (home, mail, calendar, notes, files, camera) with manifests and
  service workers.
- Python D-Bus services (bridge, portal, notifications) and native GTK4 C app
  source.
- Security configuration files (AppArmor, nftables, hardened_malloc).
- Build / flash / sign / recovery scripts as architectural planning material.
- UTM VM testing scripts for early validation.

Status at v0.1.0: ~25–30% MVP scaffold, **0% verified flashable**, ~35–45%
patchable VM demo. See [`docs/repo-audit.md`](docs/repo-audit.md) for the
measured code footprint and [`docs/milestones.md`](docs/milestones.md) for the
programme view.
