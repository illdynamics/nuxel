# Nuxel on the Samsung Galaxy S10+ (Exynos) — Bring-Up Guide

**Device:** Samsung Galaxy S10+ (SM-G975F, Exynos 9820), codename `beyond2lte`
**Status:** bring-up in progress — **NOT flashable/verified yet**
**Last updated:** 2026-08-28 (multi-device refactor cycle)

> ⛔ **Honesty gate:** neither the mustang (Pixel 10 Pro XL) path nor the S10+
> path is flashable or verified today. The S10+ path is a **new Exynos 9820
> bring-up** built on the postmarketOS `samsung-exynos9820` port. Every
> checksum, load address, firmware filename and driver-status claim in this
> tree is `UNKNOWN` / `PLACEHOLDER` until the physical device (already in
> TWRP) is inventoried via **Phase 0**
> (`docs/s10plus-device-inventory.md`). Nothing in this document should be
> read as a promise that an image will boot on your unit before that
> inventory exists.

---

## Table of contents

1. [Multi-device model (`NUXEL_DEVICE` / `--device`)](#1-multi-device-model)
2. [Hardware snapshot (verified facts)](#2-hardware-snapshot)
3. [S10+ boot chain (S-Boot → U-Boot → Linux)](#3-s10plus-boot-chain)
4. [Flash model: TWRP + Download Mode, **no fastboot**](#4-flash-model)
5. [Knox-tripped reality](#5-knox-tripped-reality)
6. [Protected partitions](#6-protected-partitions)
7. [Phase 0 device inventory + build gate](#7-phase-0-device-inventory)
8. [Build pipeline (exact commands)](#8-build-pipeline)
9. [Anti-cross-flash rules](#9-anti-cross-flash-rules)
10. [Driver status matrix (honest)](#10-driver-status-matrix)
11. [Recovery path (full stock restore)](#11-recovery-path)
12. [S10+ artifact tree](#12-s10plus-artifact-tree)
13. [Safety rules recap](#13-safety-rules-recap)
14. [References](#14-references)

---

## 1. Multi-device model

Nuxel is a **multi-hardware-target** repository. Every device-specific
artifact lives under a **per-device directory** keyed by a canonical device
key. No shared top-level device file contains more than one device's data,
and **no script ever guesses** which device you mean — selection is always
explicit.

### 1.1 Device keys, codenames and directories

| Key | Device | Codename | Per-device dir | Status |
|---|---|---|---|---|
| `mustang` | Google Pixel 10 Pro XL | mustang | `google-pixel-10-pro-xl/` | Scaffold (0% flashable) |
| `s10plus` | Samsung Galaxy S10+ (Exynos) | beyond2lte | `s10plus/` | Bring-up in progress |
| `g7power` | Motorola Moto G7 Power | ocean | `g7power/` | Stub only |

### 1.2 Per-device directory layout

Each of the six device-specific areas mirrors the same three keys:

| Artifact area | mustang | s10plus | g7power |
|---|---|---|---|
| Firmware (manifest, install/verify, blobs) | `firmware/google-pixel-10-pro-xl/` | `firmware/s10plus/` | `firmware/g7power/` |
| Kernel (defconfig, patches, toolchain docs, build) | `kernel/google-pixel-10-pro-xl/` | `kernel/s10plus/` | `kernel/g7power/` |
| Device package (deviceinfo, APKBUILD, udev, conf) | `device/google-pixel-10-pro-xl/` | `device/s10plus/` | `device/g7power/` |
| Boot (flash, recovery, boot-config, packers) | `boot/google-pixel-10-pro-xl/` | `boot/s10plus/` | `boot/g7power/` |
| Configs (display, libinput, alsa-ucm, modem, …) | `configs/google-pixel-10-pro-xl/` | `configs/s10plus/` | `configs/g7power/` |
| Images (build orchestration, avb/rauc/ostree) | `images/google-pixel-10-pro-xl/` | `images/s10plus/` | `images/g7power/` |

**Shared / device-agnostic** (never device-keyed, never merged with
device-specific content): `services/`, `shell/`, `pwa/`, `vm/`, `ci/`,
`assets/`, `tools/` (except the new selector), `images/mkrootfs.sh`,
`images/config/`, `images/hooks/`, `images/bootpack/`, `boot/initramfs/`
(shared POSIX-sh init), and `configs/{apparmor,apparmor.d,dbus,init,
networkmanager,nftables,nuxel,hardened-malloc*}`.

The mustang files that historically lived at top level (`firmware/*`,
`kernel/defconfig`, `kernel/patches/`, `device/*`, `boot/flash.sh`,
`boot/recovery.sh`, `configs/{display,libinput,alsa-ucm,modem,pipewire,
wireplumber}/`, `images/{avb,rauc,ostree}/`) were **moved into
`google-pixel-10-pro-xl/`** and thin symlinks/wrappers at the old paths keep
existing references working. `kernel/build-kernel.sh` and `images/build.sh`
stay at top level as **`--device` dispatchers**.

### 1.3 The device selector: `tools/nuxel-device-select.sh`

Every per-device script sources `tools/nuxel-device-select.sh` (a shared,
device-agnostic library) and uses `${NUXEL_DEVICE_DIR}` for per-device
paths. Resolution order is strict:

1. **CLI `--device <key>`** (highest priority)
2. **`NUXEL_DEVICE` environment variable**
3. **Explicit error** — never silently guess (no default device)

Aliases are accepted: `s10plus|beyond2lte` and `g7power|ocean`.
`mustang` has no alias. After resolution the selector **exports and prints**
`NUXEL_DEVICE_KEY` and `NUXEL_DEVICE_DIR` before any work happens, and every
S10+ script then hard-guards `[ "${NUXEL_DEVICE_KEY}" = "s10plus" ]`,
refusing to continue on any other key.

```bash
# Examples — equivalent forms
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh --device s10plus --help
bash boot/s10plus/flash.sh --device s10plus --help          # CLI flag wins
NUXEL_DEVICE=beyond2lte bash images/s10plus/build.sh --help # alias
bash images/s10plus/build.sh --help   # usage, exit 0 (--help exempt from selection/gate)
# Missing key -> explicit error, exit 1:
bash images/s10plus/build.sh   # (no --device, no NUXEL_DEVICE) -> ERROR: NUXEL_DEVICE is not set ...; exit 1
```

The kernel cmdline `nuxel.device=` must match the selected key; the
initramfs dispatches on it (see §3.3).

---

## 2. Hardware snapshot

Verified facts (authoritative for this bring-up; do not extend without a
cited source — `docs/hardware-ids.md`, `phones/s10plus/s10plus-requirements.md`):

| Component | S10+ (SM-G975F) value |
|---|---|
| Device / codename | Samsung Galaxy S10+ / `beyond2lte` (Exynos variant) |
| SoC | Samsung Exynos 9820 — 2× Mongoose M4 + 2× Cortex-A75 + 4× Cortex-A55, 8 nm |
| GPU | Mali-G76 MP12 (Bifrost) → mainline **Panfrost** |
| RAM | 8 GB LPDDR4X |
| Storage | UFS 2.1 at `/dev/block/platform/13d60000.ufs` (by-name symlinks) |
| Display | 6.4" Dynamic AMOLED 3040×1440, 19:9, HDR10+; DDIC **S6E3HA9** (`s6e3ha9_beyond2`) |
| Touch | Samsung **S6SY761**-series (`sec_ts`), I2C `hsi2c_10` @ 0x48, firmware `y771`/`y771_d` |
| WiFi / BT | Broadcom **BCM4375** (Wi-Fi 6 / 802.11ax, BT 5.0) — firmware filenames UNKNOWN until Phase 0 |
| Modem | Integrated Samsung **Shannon LTE** (Cat 20, no 5G) — **NOT ModemManager-ready** |
| NFC | Samsung `sec-nfc` (S3FWRN5-family), I2C @ 0x27 |
| Audio | Cirrus **CS47L93** (MADERA ASoC) + 2× **CS35L40** smart amps |
| Battery | 4100 mAh (15 W wired, 12–15 W wireless Qi) |
| Partition model | **A-only** (no A/B); separate `boot` / `recovery` / `system` / `vendor` / `product` / `userdata` |
| Boot image | Legacy Android boot image **header v1** (magic `ANDROID!`, page 2048, kernel + ramdisk, no vendor_boot/init_boot) |
| Flash tooling | **NO fastboot.** TWRP (`adb` + `dd`) and Download Mode (Odin/`heimdall`) only |
| Boot chain | S-Boot → custom U-Boot (`chiffathefox/u-boot`, branch `exynos9820`, `exynos9820_defconfig`) → `linux-postmarketos-exynos9820` via EFI → Nuxel initramfs (`nuxel.device=s10plus`) → rootfs → Phosh |

---

## 3. S10+ boot chain

### 3.1 Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│ Boot ROM (Samsung, eFused — Knox already tripped, never relock)      │
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ S-Boot (Samsung primary bootloader)                                  │
│  • initializes CPU / DRAM / UFS / display                            │
│  • reads a legacy Android boot image (header v1, page 2048)          │
│    from the UFS by-name `boot` partition                             │
│  • IGNORES kernel cmdline and boot offset; REJECTS mainline DTBs     │
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼  (boot.img "kernel" slot = u-boot.bin)
┌──────────────────────────────────────────────────────────────────────┐
│ custom U-Boot  (github.com/chiffathefox/u-boot, branch exynos9820,   │
│                 exynos9820_defconfig, CC=aarch64-linux-gnu-gcc-10)   │
│  • full bootloader: UFS/MMC, EFI stub support, DTB handling          │
│  • boots the mainline kernel via EFI (S-Boot cannot)                 │
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼  (EFI / Image.gz + exynos9820-beyond2lte.dtb)
┌──────────────────────────────────────────────────────────────────────┐
│ linux-postmarketos-exynos9820 (close-to-mainline Exynos 9820 tree)   │
│  cmdline: earlycon=exynos4210,0x10020000 console=ttySAC0,115200      │
│           nuxel.device=s10plus root=/dev/block/platform/             │
│           13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw  │
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Nuxel initramfs (boot/initramfs/init.sh — shared, POSIX sh)          │
│  s10plus branch: explicit root= > userdata > system under            │
│  /dev/block/platform/13d60000.ufs/by-name ; failure -> emergency_shell│
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ rootfs — ext4 on the `userdata` partition (Phase 1: writable,        │
│ NO dm-verity/AVB on purpose)                                         │
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Phosh / GTK4 / Wayland shell + Nuxel services (device-agnostic)      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Why U-Boot chainload is **mandatory**

Samsung's S-Boot:

- **ignores the kernel cmdline** and the boot offset recorded in `boot.img`
  (it boots the payload it decides to boot, not the one the header asks for),
- **rejects mainline-compatible device trees** (it only accepts Samsung
  downstream DTB structures), and
- cannot boot an EFI stub kernel or pass a DTB to mainline Linux.

The proven postmarketOS path — and the one Nuxel adopts — is to let S-Boot
boot a **custom U-Boot** (`chiffathefox/u-boot`, branch `exynos9820`,
`exynos9820_defconfig`) wrapped as the "kernel" of a legacy v1 boot image on
the `boot` partition. That U-Boot then boots `linux-postmarketos-exynos9820`
**via EFI**, exactly like a PC bootloader. A mainline kernel **cannot** be
booted directly by S-Boot; there is no shortcut around the chainload.

Both the Nuxel kernel image and the U-Boot chainload image are produced by
`boot/s10plus/pack-boot-v1.sh` (legacy v1 packer, page 2048, `ANDROID!`
magic) — completely separate from `images/bootpack/mkbootimg.py` (v3/v4).

### 3.3 Initramfs dispatch (`nuxel.device=`)

`boot/initramfs/init.sh` (shared, POSIX sh, no bashisms) parses
`nuxel.device=` and dispatches:

- `mustang` / `vm` / (empty) → existing A/B dynamic-partition probe
  (unchanged; mustang + UTM VM baseline preserved),
- `s10plus` → A-only UFS probe with order **explicit `root=` cmdline >
  `userdata` > `system`** under `UFS_BASE=/dev/block/platform/13d60000.ufs/by-name`,
  logging the chosen root (`s10plus: root → …`),
- `g7power` → stub (eMMC path TBD) → `emergency_shell`,
- unknown → error → `emergency_shell`.

`emergency_shell` always prints `/proc/cmdline` and the available block
devices (`/dev/disk/by-partlabel/`, `/dev/sd* /dev/vd* /dev/mmcblk*`,
`/dev/block/platform/*/by-name/`) before dropping to an interactive
`sh -i` **only when `nuxel.debug=1`** is on the cmdline.

### 3.4 Boot configuration file

`boot/s10plus/boot-config.txt` records the machine-readable boot facts:
`device=s10plus`, `codename=beyond2lte`,
`ufs_path=/dev/block/platform/13d60000.ufs/by-name`, U-Boot source/defconfig,
`page_size=2048`, `cmdline_base` / `cmdline_root`, the protected-partition
list, and the recovery combos. The three load addresses
(`kernel_addr`, `ramdisk_addr`, `tags_addr`) are **PLACEHOLDER values** until
the operator extracts them from the stock boot.img during Phase 0.

---

## 4. Flash model

### 4.1 Why there is **no fastboot** on the S10+

Samsung Exynos devices never implemented the Android `fastboot` protocol.
S-Boot speaks Samsung's **Download Mode** protocol (Odin / `heimdall`), and
that is the only host-driven flashing interface at the bootloader level. The
S10+ therefore has **no `fastboot` path for anything**: no `fastboot
flashing unlock`, no `fastboot flash boot`, no `fastboot reboot recovery`.
Any tutorial that says "put the Galaxy in fastboot mode" is describing a
Qualcomm device, not this one. **Every S10+ script, doc and comment in this
tree is written accordingly** — the flash tooling is:

1. **TWRP** (`adb` + `dd`) for the Nuxel boot/rootfs payloads, and
2. **Download Mode + Odin/heimdall** for full-stock restore and revert.

### 4.2 Entering TWRP

The S10+ is already running TWRP. To re-enter it:

```text
Power off the device, then hold   Vol Up + Bixby + Power
until TWRP starts (release when the logo/recovery appears).
```

Verify the connection:

```bash
adb devices          # must list the device in "device" state
adb shell getprop ro.product.device   # must print: beyond2lte
adb shell getprop ro.product.name     # must print: beyond2ltexx (or regional variant)
```

### 4.3 Entering Download Mode

```text
Power off the device, then hold   Vol Down + Bixby + Power
until the warning screen appears (release; press Vol Up to continue).
```

Download Mode accepts Odin/`heimdall` flashes only. This is the recovery net
for this device (§11).

### 4.4 The full flash sequence (once images exist)

1. Boot TWRP (`Vol Up + Bixby + Power`).
2. `adb devices` — confirm the S10+ is visible.
3. Run the flash script with an explicit device key:
   ```bash
   NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh \
       --device s10plus \
       --uboot build/out/s10plus/u-boot-beyond2lte.img \
       --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img
   ```
4. Reboot: `adb shell twrp reboot`.

`boot/s10plus/flash.sh` enforces, in order: `--device s10plus` required;
device-key guard via the selector; **Phase 0 inventory gate** (unless
`--dry-run`); `adb` present; device identity verified
(`ro.product.device == beyond2lte` **and** `ro.product.name` starts with
`beyond2lte`); rootfs partition denylist-checked against the protected list
(default rootfs target: `userdata`); confirmation prompts (unless
`--force`); and `dd` to UFS by-name targets with `bs=4096`. It never
touches `efs efsg persist param up_param steady keystorage carrier
cp_debug misc`. Full option set: `--device`, `--uboot`, `--rootfs`,
`--rootfs-partition`, `--sideload`, `--revert`, `--stock-boot`, `--dry-run`,
`--force`, `--help`.

### 4.5 TWRP ADB sideload

`--sideload` prints the TWRP sideload instructions
(TWRP → Advanced → ADB Sideload → Swipe to start → `adb sideload
nuxel-s10plus.zip`). The sideload ZIP builder is **not implemented yet** —
use the `adb push` + `dd` path for now.

---

## 5. Knox-tripped reality

The S10+ bootloader's Knox fuse is **already tripped** (this is why TWRP and
custom boot chains are possible on this unit).

**What it means**

- The bootloader is permanently unlocked at the hardware/eFuse level.
- Samsung Knox attestation, Secure Boot (Knox flavor), and everything built
  on top of Knox is permanently disabled on this unit.
- Samsung Knox-backed features will never work again on this unit:
  Samsung Pay, Secure Folder, Knox containers/workspace, Samsung Health
  (Knox-backed portions), Knox attestation APIs, and possibly Widevine L1
  DRM. Warranty services via Samsung are void for software claims.

**What it does NOT mean**

- The device is bricked or degraded for our purposes — quite the opposite.
- Normal hardware (display, touch, radio, WiFi, storage, battery) is
  unaffected; TWRP works; custom kernels, U-Boot chainloading, and Nuxel are
  all possible.
- There is no "Knox restoration" to perform: the fuse is one-way. Any
  tool that claims to restore Knox is a scam or a brick risk.

**Non-negotiables**

- **Never relock the bootloader.** With a custom boot chain installed,
  relocking trips `ODIN LOCK` and can **hard-brick** the device.
- **Never attempt Knox restoration.** It is physically impossible.
- **Never flash a stock CSC/AP from a different regional variant** — a
  mismatched carrier/region package can trip additional eFuses.

---

## 6. Protected partitions

The following partitions are **never touched by any Nuxel script, ever**
(denylist in `boot/s10plus/flash.sh`, `boot/s10plus/uboot-chainload.sh`, and
enforced by the inventory/pull tooling):

| Partition | What lives there | Why never touch it |
|---|---|---|
| `efs` | IMEI, radio/baseband calibration, DRK | Wipe = null IMEI, no signal, unrecoverable without Samsung service tools |
| `efsg` | EFS group/backup mirror | Same class as `efs`; second copy of per-unit identity |
| `persist` | Per-unit calibration, sensor/touch calibration | Wrong data = broken sensors/touch; only the unit's own data is valid |
| `param` | Samsung boot parameters | Boot state flags; corruption can prevent boot |
| `up_param` | Upload-mode (crash dump) parameters | Corruption affects crash handling/debug paths |
| `steady` | Samsung steady-state/security metadata | Linked to boot state + Knox-adjacent metadata |
| `keystorage` | Key storage (DRK/keystore material) | Wiping breaks device encryption identity |
| `carrier` | Carrier-specific configuration | Wrong content can lock/break carrier features |
| `cp_debug` | Modem debug/log partition | Contains baseband logs; not user data |
| `misc` | Bootloader misc flags (recovery reason etc.) | Standard Android "don't touch" partition |

Any partition-listing/iteration script **denylist-checks before `dd`** — the
rootfs target partition (default `userdata`) is validated against this list
and refused if it collides.

Back up the whole `by-name` table (especially `efs`/`persist`) via TWRP
before the first modification:

```bash
adb shell "mkdir -p /sdcard/backup && for p in efs efsg persist param up_param steady; do dd if=/dev/block/platform/13d60000.ufs/by-name/\$p of=/sdcard/backup/\$p.img; done"
adb pull /sdcard/backup
```

---

## 7. Phase 0 device inventory

**Phase 0 is the immediate blocker.** `docs/s10plus-device-inventory.md` is
the operator template: it lists every collection command (identity
getprops, `/proc/cmdline`, `cpuinfo`, full `dmesg` dump, `getevent -pl`
input dump, UFS by-name listing + `/proc/partitions`, vendor
firmware/module listings, asound cards, BCM4375 firmware listings, stock
`boot.img` pull + header extraction) and the fill-in fields:
`DEVICE_VARIANT`, `BOOTLOADER_VERSION`, `ANDROID_BUILD`, `KERNEL_ADDR`,
`RAMDISK_ADDR`, `TAGS_ADDR`, `SENSOR_HUB`, `CAMERA_FRONT`, `CAMERA_REAR`,
`WIFI_FW_FILENAME`, `BT_HCD_FILENAME`, `TOUCH_FW_PATH`, `AUDIO_UCM_CARD`.

The stock boot.img header is parsed with the repo tool:

```bash
adb pull /dev/block/platform/13d60000.ufs/by-name/boot /tmp/stock-boot.img
python3 tools/read-boot-header-v1.py /tmp/stock-boot.img
# -> kernel_addr / ramdisk_addr / tags_addr / page_size / kernel_size /
#    ramdisk_size / dt_size / os_version / name / cmdline
```

### 7.1 The `_check_s10plus_inventory()` gate

Every S10+ build/flash script (`kernel/s10plus/build-kernel.sh`,
`boot/s10plus/uboot-chainload.sh`, `images/s10plus/build.sh`,
`boot/s10plus/flash.sh`) embeds the same gate: while
`KERNEL_ADDR`, `RAMDISK_ADDR`, `TAGS_ADDR` still contain `PLACEHOLDER` or
`WIFI_FW_FILENAME` still contains `UNKNOWN` in
`docs/s10plus-device-inventory.md`, the script prints the Phase 0 reminder
and exits 1. `--help` and `--dry-run` are exempt so the operator can preview
commands before inventory exists. The gate exists because flashing with the
wrong load addresses or the wrong WiFi firmware filename is a brick risk on
this device — S-Boot is picky and there is no fastboot rescue path.

**Never fabricate a value to pass the gate.** Wrong addresses/filenames are
worse than no build.

---

## 8. Build pipeline

### 8.1 Prerequisites (operator-provided, not automatable)

- The S10+ (SM-G975F) in TWRP with a USB-C data cable; `adb` + `heimdall`
  on the host (platform-tools ≥ 34).
- The **stock Samsung firmware** (BL/AP/CP/CSC tarballs for SM-G975F,
  matching the current bootloader revision) — needed for firmware
  extraction and Download-Mode recovery.
- A **full TWRP backup** (or `dd` of every by-name partition) before any
  modification — especially `efs`/`persist`.
- AArch64 cross toolchain: `gcc-10-aarch64-linux-gnu` (Debian/Ubuntu:
  `apt install gcc-10-aarch64-linux-gnu`; macOS: `messense/macos-cross-toolchains`
  homebrew tap). See `kernel/s10plus/README-toolchain.md`.

### 8.2 Exact commands

```bash
# ── Phase 0: inventory (REQUIRED FIRST) ──────────────────────────────────
# Follow docs/s10plus-device-inventory.md on the device in TWRP.
# Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR, WIFI_FW_FILENAME.
# Every build/flash script below refuses to run until the gate passes.

# ── Phase 1: kernel + U-Boot ─────────────────────────────────────────────
# Clone + build linux-postmarketos-exynos9820 (branch exynos9820) and merge
# the Nuxel defconfig fragment (kernel/s10plus/defconfig):
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone
#   extra: --jobs N | --cross <prefix> | --clean | --help
#   outputs: kernel/s10plus/.build/out/arch/arm64/boot/Image.gz
#            kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dtb

# Build chiffathefox/u-boot (exynos9820) and flash it to the boot partition
# via TWRP adb+dd (device in TWRP, identity verified automatically):
NUXEL_DEVICE=s10plus bash boot/s10plus/uboot-chainload.sh --device s10plus

# ── Phase 2: rootfs + boot images ────────────────────────────────────────
# Assemble S10+ artifacts into build/out/s10plus/ (requires the kernel
# outputs above + shared boot/initramfs/initramfs.cpio.gz):
NUXEL_DEVICE=s10plus bash images/s10plus/build.sh --device s10plus
#   emits: build/out/s10plus/u-boot-beyond2lte.img
#          build/out/s10plus/nuxel-beyond2lte-boot.img
#          build/out/s10plus/nuxel-beyond2lte-rootfs.img
#          build/out/s10plus/build-manifest.json
#   Phase 1: NO dm-verity/AVB (rootfs writable on purpose — bring-up).

# ── Flash (device in TWRP) ───────────────────────────────────────────────
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh \
    --device s10plus \
    --uboot build/out/s10plus/u-boot-beyond2lte.img \
    --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img
```

### 8.3 What each piece does

- **`kernel/s10plus/build-kernel.sh`** — clones
  `postmarketOS/linux-postmarketos` branch `exynos9820` into
  `kernel/s10plus/.build/src`; applies `kernel/s10plus/patches/*.patch`
  **non-fatally** (per-patch README hint if a mustang-era patch is
  6.12-only and does not apply); merges `kernel/s10plus/defconfig` with
  `scripts/kconfig/merge_config.sh -m` + `olddefconfig`; builds
  `Image.gz dtbs` with `O=kernel/s10plus/.build/out`; prints output paths.
- **`kernel/s10plus/defconfig`** — Exynos 9820 fragment (NOT gs501): enables
  Panfrost, exynos DRM/DSI + S6E3HA9 panel, `sec_ts`, brcmfmac SDIO (BCM4375),
  btbcm, MADERA/CS47L93 + CS35L40, UFS, ext4/f2fs, AppArmor, seccomp, and
  namespace support; symbols that cannot exist in the exynos9820 tree are
  commented with the reason.
- **`boot/s10plus/uboot-chainload.sh`** — clones
  `chiffathefox/u-boot` branch `exynos9820` into
  `kernel/s10plus/.build/u-boot`; verifies device identity; builds
  `exynos9820_defconfig` with `CC=aarch64-linux-gnu-gcc-10`; wraps
  `u-boot.bin` as a v1 boot image via `pack-boot-v1.sh`; `adb push` + `dd`
  to the UFS by-name `boot` partition (`bs=4096`); prints the heimdall
  revert hint. No fastboot anywhere.
- **`boot/s10plus/pack-boot-v1.sh`** — Python 3 legacy v1 packer
  (page 2048, `ANDROID!`, kernel/ramdisk/DTS padded to page size,
  `name=nuxel-s10plus`, `id=0`); defaults for the load addresses are
  `kernel_addr 0x80008000`, `ramdisk_addr 0x84000000`,
  `tags_addr 0x80000100` **marked PLACEHOLDER-verify-from-real-device**;
  `--addresses-from-device <stock-boot.img>` mode reads the real addresses
  via `tools/read-boot-header-v1.py`.
- **`images/s10plus/build.sh`** — sources the selector (must resolve to
  `s10plus`), runs the inventory gate, requires
  `kernel/s10plus/.build/out/arch/arm64/boot/Image.gz` + a
  `*beyond2lte*.dtb` under `.../dts/exynos/` + shared
  `boot/initramfs/initramfs.cpio.gz`; calls `pack-boot-v1.sh` for both boot
  images; calls the device-agnostic `images/mkrootfs.sh`; overlays
  `firmware/s10plus/blobs`, `configs/s10plus/`, udev rules, and kernel
  modules into the rootfs staging; emits the rootfs image + `build-manifest.json`
  (device key, kernel commit, build timestamp). Never touches
  `build/out/mustang/`.
- **`firmware/s10plus/install-firmware.sh`** — modes: `--list-files`
  (S10+ manifest only), `--verify-only` (UNKNOWN checksums → reported
  pending, exit 0), `--checksums` (sha256 of `blobs/`), `--twrp-pull`
  (identity check then `adb pull` of `/vendor/firmware`,
  `/vendor/lib/modules`, `/vendor/etc/firmware`, `/system/lib64` into
  `blobs/`, cross-referencing found vs missing), `--install` (refuses until
  real checksums exist or `--force-pending`). Guards
  `NUXEL_DEVICE==s10plus`; never reads mustang paths or the mustang
  manifest.

---

## 9. Anti-cross-flash rules

| From → To | Rule | Why |
|---|---|---|
| S10+ images → mustang | ⛔ NEVER | Different SoC, boot image format (v1 vs v4), partitions, cmdline; will not boot and may corrupt the Pixel |
| S10+ images → g7power | ⛔ NEVER | g7power is a stub (SDM632/MSM8953); Exynos 9820 images are meaningless there |
| mustang images → S10+ | ⛔ NEVER | gs501/Tensor G5 kernel + v4 boot image cannot be read by S-Boot |
| g7power images → anything | ⛔ NEVER | Stub only; nothing flashable exists |
| Pixel/BCM4390/PowerVR/gs501/AMB655X/S6SY791 firmware → S10+ | ⛔ NEVER | Wrong radio/GPU/panel/touch silicon; flashing vendor blobs from another device is a brick risk |
| Stock Samsung firmware for a different variant → S10+ | ⛔ NEVER | Mismatched BL/AP/CP/CSC can trip additional eFuses |
| Any image to `efs efsg persist param up_param steady keystorage carrier cp_debug misc` | ⛔ NEVER | See §6 |

Enforcement: per-device directories + the device-key selector + identity
verification (`beyond2lte` / `beyond2ltexx`) before every flash + the
protected-partition denylist. There is no shared "flash anything" script.

---

## 10. Driver status matrix (honest)

| Subsystem | Hardware | Kernel driver | Status | Notes |
|---|---|---|---|---|
| GPU | Mali-G76 MP12 (Bifrost) | `CONFIG_DRM_PANFROST` | ✅ ok (mainline) | Panfrost in `linux-postmarketos-exynos9820`; vendor GLES blob optional fallback |
| Display | S6E3HA9 AMOLED 3040×1440 | exynos DRM/DSI + `s6e3ha9_beyond2` | 🚧 downstream | Samsung DRM/DSI in pmOS exynos9820 tree; panel init firmware `s6e3ha9_beyond2_*.bin` UNKNOWN until Phase 0 |
| Touch | S6SY761 (`sec_ts`) | `CONFIG_TOUCHSCREEN_SAMSUNG_SEC_TS` | 🚧 downstream | I2C hsi2c_10 @ 0x48; firmware `y771`/`y771_d` UNKNOWN until Phase 0 |
| Audio | CS47L93 + 2× CS35L40 | MADERA ASoC (`CONFIG_MFD_CS47L93`, `CONFIG_SND_SOC_CS35L40`) | 🚧 downstream | Needs `cs47l93-dsp1-*.wmfw` + `cs35l40-dsp*.wmfw`; UCM routing from real tinymix (Phase 0) |
| NFC | sec-nfc (S3FWRN5-family) @ 0x27 | `CONFIG_NFC_SEC` (verify symbol in tree) | 🚧 downstream | Commented in defconfig pending tree check |
| WiFi | BCM4375 (Wi-Fi 6) | `CONFIG_BRCMFMAC` + `_SDIO` | ⬜ needs firmware | `brcmfmac4375-sdio.bin` + CLM blob; filename UNKNOWN until Phase 0 (`WIFI_FW_FILENAME` gate) |
| BT | BCM4375 (BT 5.0) | `CONFIG_BT_HCIUART_BCM` | ⬜ needs firmware | `BCM4375.hcd` UNKNOWN until Phase 0 |
| Modem | Shannon LTE (Cat 20, no 5G) | — | ❌ not in Phase 1 | No upstream ModemManager plugin; `modem` partition DO NOT flash; `efs`/`efsg` NEVER (IMEI/baseband) |
| Sensors | accelerometer/gyro/ALS/proximity hub | — | ⬜ UNKNOWN | Identify from dmesg/getevent during Phase 0 |
| Camera | front/rear sensors + ISP | — | ⬜ UNKNOWN | Identify from dmesg during Phase 0 |

Legend: ✅ ok / 🚧 downstream (works in the vendor/pmOS tree, not mainline)
/ ⬜ needs firmware or inventory / ❌ deferred. Nothing here is "verified"
until the Phase 0 inventory + a real kernel build confirm it on this unit.

---

## 11. Recovery path

### 11.1 Revert to stock Android (full restore)

```text
1. Power off. Hold  Vol Down + Bixby + Power  → Download Mode
   (release on the warning screen, press Vol Up to continue).
2. From the stock SM-G975F Odin package, extract the four .tar.md5 files.
3. heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5
```

- Use a stock package matching the current bootloader revision and the
  correct regional CSC — never a different variant's package.
- This is also the one-command revert hinted by every S10+ script.

### 11.2 Revert just the boot partition

```bash
# Download Mode
heimdall flash --BOOT <stock-boot.img>
# or via boot/s10plus/flash.sh --revert (device must already be in
# Download Mode, Vol Down + Bixby + Power; the script runs heimdall
# directly and performs no adb identity check in revert mode):
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh --device s10plus \
    --revert --stock-boot <stock-boot.img>
```

### 11.3 Re-flash TWRP

```text
TWRP (Vol Up + Bixby + Power) → Advanced → ADB Sideload → Swipe to start
adb sideload twrp-beyond2lte.zip    # or nuxel-s10plus.zip
```

There is **no fastboot recovery path** on this Exynos device — TWRP +
Download Mode (Odin/heimdall) are the only recovery mechanisms.

---

## 12. S10+ artifact tree

```
docs/s10plus-bringup.md            (this file)
docs/s10plus-device-inventory.md   (Phase 0 template + gate input)
tools/nuxel-device-select.sh       (shared selector — all devices)
tools/read-boot-header-v1.py       (v1 boot.img header parser)

firmware/s10plus/
  manifest.yml                     (device s10plus; firmware_files: gpu_mali,
                                    display_panel, touch, wifi_bt, audio, nfc,
                                    modem (DO NOT INSTALL), sensors, camera;
                                    all checksums UNKNOWN)
  install-firmware.sh              (--list-files/--verify-only/--checksums/
                                    --twrp-pull/--install)
  verify-firmware.sh               (required:true verified vs pending)
  blobs/                           (populated by --twrp-pull; .gitkeep now)

kernel/s10plus/
  defconfig                        (Exynos 9820 fragment, NOT gs501)
  build-kernel.sh                  (linux-postmarketos-exynos9820 wrapper)
  patches/README.md                (which mustang patches port / why)
  README-toolchain.md              (gcc-10-aarch64-linux-gnu, macOS tap,
                                    pmOS repo, Samsung OSRC fallback)

device/s10plus/
  deviceinfo                       (pmOS format v2, beyond2lte, exact hw table)
  APKBUILD                         (pkgname device-samsung-beyond2lte)
  90-nuxel-beyond2lte.rules        (sec_ts, nfc, wlan0, camera/sensor stubs)
  nuxel-beyond2lte.conf            (NUXEL_* vars incl. UFS/display/fw paths)

boot/s10plus/
  flash.sh                         (TWRP adb+dd; heimdall revert; identity +
                                    denylist + inventory gate; NO fastboot)
  recovery.sh                      (TWRP + Download Mode reference)
  pack-boot-v1.sh                  (legacy v1 packer, page 2048)
  uboot-chainload.sh               (chiffathefox/u-boot exynos9820 build+flash)
  boot-config.txt                  (machine-readable boot facts)

images/s10plus/
  build.sh                         (boot images + rootfs → build/out/s10plus/)

configs/s10plus/
  display/nuxel-s10plus-display.sh (wlr-randr 3040x1440 on DSI-1)
  libinput/99-nuxel-beyond2lte-touch.conf
  alsa-ucm/README.md + SamsungBeyond2/{SamsungBeyond2.conf,HiFi.conf}
  modem/README.md                  (Shannon LTE: WiFi-only Phase 1)
  pipewire/ + wireplumber/         (48000 Hz 2ch stereo placeholders)
```

---

## 13. Safety rules recap

1. **Explicit selection only** — `--device` > `NUXEL_DEVICE` > error; never
   guess. `nuxel.device=` on the cmdline matches the selected key.
2. **Identity check before every flash** — `ro.product.device == beyond2lte`
   and `ro.product.name == beyond2ltexx` (or regional variant); refuse on
   mismatch.
3. **No fastboot, ever** — TWRP (adb+dd) and Download Mode (Odin/heimdall)
   only.
4. **Protected partitions never touched** — `efs efsg persist param
   up_param steady keystorage carrier cp_debug misc` (denylist-checked).
5. **Never relock the bootloader / never attempt Knox restoration** —
   ODIN LOCK may brick; Knox is one-way.
6. **Never fabricate data** — checksums, load addresses, firmware
   filenames, and driver status stay `UNKNOWN`/`PLACEHOLDER` until the
   physical device provides them (Phase 0).
7. **Per-device isolation** — no S10+ file references mustang hardware
   (except this doc's cross-references), and no shared file merges device
   content.
8. **Honest status** — neither target is flashable/verified yet.

---

## 14. References

- `phones/s10plus/s10plus-requirements.md` — requirements & bring-up plan (this document's
  source of truth).
- `docs/s10plus-device-inventory.md` — Phase 0 operator template + gate.
- `phones/s10plus/nuxel-s10plus.md` — implementation prompt for the S10+ scaffold.
- `docs/hardware-ids.md` — canonical hardware component IDs (all targets).
- postmarketOS Exynos 9820 port:
  `https://wiki.postmarketos.org/wiki/Samsung_Exynos_9820_(samsung-exynos9820)`
- Custom U-Boot: `https://github.com/chiffathefox/u-boot` (branch
  `exynos9820`, `exynos9820_defconfig`).
- TWRP for beyond2lte: `https://twrp.me/samsung/samsunggalaxys10plus.html`
- Samsung OSRC (Exynos 9820 kernel): `https://opensource.samsung.com`
  (search SM-G975F).
- `docs/driver-status.md`, `docs/bootloader-unlock-guide.md`,
  `docs/firmware-verification.md` — mustang-era references (cross-target).

---

_Build the bunker first. Add the rave lights later._ —
S10+ bring-up status: **not flashable/verified until Phase 0 inventory +
real firmware + real kernel build.**
