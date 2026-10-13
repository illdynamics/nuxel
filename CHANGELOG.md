# Changelog

All notable changes to the Nuxel Phone OS repository are documented here.

The canonical version lives in [`VERSION`](VERSION) and is bumped in lockstep
across the shell apps, the PWA manifest, the device `APKBUILD`s, the VM tooling
and the OTA builder (see *Versioning* below).

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
