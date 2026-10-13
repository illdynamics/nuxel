# Nuxel on the Motorola Moto G7 Power — Bring-Up Guide

**Device:** Motorola Moto G7 Power (XT1955), codename `ocean`
**SoC:** Qualcomm Snapdragon 632 (SDM632, msm8953 DT family)
**Status:** bring-up in progress — **NOT flashable/verified yet**
**Last updated:** 2026-08-28 (multi-device refactor cycle)

> ⛔ **Honesty gate:** the G7 Power path is **not** flashable or verified
> today. It is a new SDM632/msm8953 bring-up built on the postmarketOS
> `motorola-ocean` port, mainline `msm8953-mainline/linux` and the
> `msm8916-mainline/lk2nd` chainloader. Every checksum, load address,
> firmware filename and driver-status claim in this tree is
> `UNKNOWN` / `PLACEHOLDER` until the physical device is inventoried via
> **Phase 0** (`docs/g7power-device-inventory.md`). Nothing in this document
> is a promise that an image will boot on your unit before that inventory
> exists and before a real kernel + lk2nd build has been produced and tested.
>
> Two absolute rules drive every G7 Power decision in this repo:
>
> 1. **dtbo is flashed BEFORE lk2nd, always** (enforced in code) — this
>    prevents the classic msm8953 soft-brick.
> 2. **Protected partitions are never touched** — `modemst1 modemst2 fsg
>    fsc ddr persist misc` hold per-unit IMEI/MAC/radio calibration data and
>    are irreplaceable.

---

## Table of contents

1. [Multi-device model (`NUXEL_DEVICE` / `--device`)](#1-multi-device-model)
2. [G7 Power boot chain (PBL → ABOOT → lk2nd → Linux)](#2-g7-power-boot-chain)
3. [Two-phase fastboot (stock ABOOT vs lk2nd)](#3-two-phase-fastboot)
4. [Motorola unlock portal](#4-motorola-unlock-portal)
5. [Protected partitions](#5-protected-partitions)
6. [Phase 0 device inventory + build gate](#6-phase-0-device-inventory-and-build-gate)
7. [Exact build commands](#7-exact-build-commands)
8. [ILI2117 touch caveat](#8-ili210x-touch-caveat)
9. [WiFi: wcn36xx vs ath10k](#9-wifi-wcn36xx-vs-ath10k)
10. [Driver status matrix (honest)](#10-driver-status-matrix-honest)
11. [EDL unbrick path (Qualcomm 9008)](#11-edl-unbrick-path-qualcomm-9008)
12. [Safety rules recap](#12-safety-rules-recap)
13. [References](#13-references)

---

## 1. Multi-device model

Nuxel is a **multi-hardware-target** repository. Every device-specific
artifact lives under a **per-device directory** keyed by a canonical device
key. No shared top-level device file contains more than one device's data,
and **no script ever guesses** which device you mean — selection is always
explicit (`tools/nuxel-device-select.sh` resolves it, and every per-device
script prints the resolved key before doing any work).

### 1.1 Device keys, codenames and directories

| Key | Device | Codename | Per-device dir | Status |
|---|---|---|---|---|
| `mustang` | Google Pixel 10 Pro XL | mustang | `google-pixel-10-pro-xl/` | Scaffold (0% flashable) |
| `s10plus` | Samsung Galaxy S10+ (Exynos) | beyond2lte | `s10plus/` | Bring-up in progress |
| `g7power` | Motorola Moto G7 Power (ocean) | ocean | `g7power/` | Bring-up in progress |

`NUXEL_DEVICE=g7power` (or the alias `NUXEL_DEVICE=ocean`, or
`--device g7power`) resolves to the `g7power/` directories in all six
device-specific areas. The selector exports `NUXEL_DEVICE_KEY=g7power` and
`NUXEL_DEVICE_DIR=g7power`; every G7 Power script then hard-guards
`[ "${NUXEL_DEVICE_KEY}" = "g7power" ]` and refuses to run on any other key.

### 1.2 Per-device directory layout

| Artifact area | g7power directory |
|---|---|
| Firmware (manifest, install/verify, blobs) | `firmware/g7power/` |
| Kernel (defconfig, patches, toolchain docs, build) | `kernel/g7power/` |
| Device package (deviceinfo, APKBUILD, udev, conf) | `device/g7power/` |
| Boot (flash, recovery, boot-config, packer, lk2nd docs) | `boot/g7power/` |
| Configs (display, libinput, alsa-ucm, modem, …) | `configs/g7power/` |
| Images (build orchestration) | `images/g7power/` |

**Shared / device-agnostic** (never device-keyed, never merged with
device-specific content): `services/`, `shell/`, `pwa/`, `vm/`, `ci/`,
`assets/`, `tools/` (including the selector and
`tools/read-boot-header-v1.py`), `images/mkrootfs.sh`,
`boot/initramfs/init.sh` (shared POSIX-sh init that dispatches on
`nuxel.device=`), and the shared `configs/` security trees.

### 1.3 The device selector: `tools/nuxel-device-select.sh`

Resolution order is strict:

1. **CLI `--device <key>`** (highest priority)
2. **`NUXEL_DEVICE` environment variable**
3. **Explicit error** — never silently guess (no default device)

Aliases: `s10plus|beyond2lte` and `g7power|ocean`; `mustang` has no alias.
A missing key produces `ERROR: NUXEL_DEVICE is not set and --device was not
passed.` and exit 1. The kernel cmdline carries `nuxel.device=g7power` so
the shared initramfs dispatches to the G7 Power root probe (see §2.4).

```bash
# Examples — equivalent forms
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh --device g7power --help
bash boot/g7power/flash.sh --device g7power --help          # CLI flag wins
NUXEL_DEVICE=ocean bash images/g7power/build.sh --help      # alias
bash images/g7power/build.sh        # missing key -> ERROR, exit 1
bash boot/g7power/flash.sh --device mustang   # -> ERROR: --device g7power required; exit 1
```

---

## 2. G7 Power boot chain

### 2.1 Diagram

```
┌──────────┐   ┌───────────────┐   ┌───────────────────────┐
│   PBL    │──▶│  stock ABOOT  │──▶│  lk2nd (msm8953)      │
│ (XBL)    │   │ (unlocked,    │   │ msm8916-mainline/lk2nd│
│          │   │  fastboot #1) │   │ = "second-stage boot" │
└──────────┘   └───────────────┘   └───────────┬───────────┘
                                               │
                                               ▼
                       ┌───────────────────────────────────────┐
                       │  mainline Linux                       │
                       │  linux-postmarketos-qcom-msm8953      │
                       │  DTB: qcom/sdm632-motorola-ocean.dtb  │
                       └───────────────────┬───────────────────┘
                                           │ nuxel.device=g7power
                                           ▼
                       ┌───────────────────────────────────────┐
                       │  Nuxel initramfs (boot/initramfs)     │
                       │  eMMC A/B root probe (userdata)        │
                       └───────────────────┬───────────────────┘
                                           ▼
                       ┌───────────────────────────────────────┐
                       │  rootfs on userdata (ext4) → Phosh    │
                       └───────────────────────────────────────┘
```

`PBL -> stock ABOOT -> lk2nd -> mainline Linux -> Nuxel initramfs ->
rootfs`. lk2nd replaces the Android boot-image parsing step: it loads a
mainline `Image.gz` + DTB + ramdisk (legacy header v1, page 2048) and hands
control to Linux. Once Linux is up, the initramfs dispatches on
`nuxel.device=g7power` and probes the eMMC root (see §2.4).

### 2.2 Why lk2nd is **mandatory**

The stock Motorola ABOOT **cannot boot mainline Linux directly**:

- It only understands the **stock Android boot image** layout and requires
  a **stock-compatible DTB** (vendor DTBO) and a stock cmdline. A mainline
  `Image.gz` with `qcom/sdm632-motorola-ocean.dtb` is not something stock
  ABOOT can parse — it will refuse to boot or mis-load the kernel.
- It enforces the stock boot verification policy on the boot partition.
- It cannot pass the cmdline parameters mainline needs
  (`nuxel.device=g7power`, `root=...`).

`lk2nd` (from `https://github.com/msm8916-mainline/lk2nd`, target
`msm8953`) is a tiny second-stage bootloader that runs **from the `boot`
partition** in place of a stock kernel. It re-initializes the display
(framebuffer handoff for mainline), provides its own **fastboot mode**, and
can load mainline kernels + DTBs + ramdisks. This is the same mechanism
postmarketOS uses across the msm8916/msm8953 family — it is the only sane
path from stock ABOOT to mainline Linux on this device.

### 2.3 The dtbo-first rule (why it exists)

**On msm8953, `dtbo` must be flashed before lk2nd. Always. No exceptions.**

- The stock ABOOT reads the **dtbo partition** (device-tree overlays) as
  part of its boot sequence. If the dtbo partition is corrupt, mismatched or
  empty, stock ABOOT (and in some firmware revisions even the PBL path) can
  fail to boot at all — the classic **msm8953 soft-brick**: device stuck on
  the boot logo or in a fastboot/boot loop with no recovery from the normal
  button combo.
- lk2nd itself does **not** need the dtbo partition, but the transition
  happens *through* stock ABOOT: you flash lk2nd to `boot` and then reboot
  **via stock ABOOT**, which validates/reads the dtbo before chain-loading.
  A bad dtbo at that moment bricks the transition.
- Therefore the enforced order is: **flash `dtbo` first (stock ABOOT
  fastboot), then flash `boot` with `lk2nd.img` (stock ABOOT fastboot)**,
  then `fastboot reboot bootloader` to enter lk2nd's own fastboot.

`boot/g7power/flash.sh` enforces this in code (the `--dtbo` step is
processed before the `--lk2nd` step; the script refuses to run with a
warning if lk2nd is flashed without a fresh dtbo in the same invocation,
and `--revert` also restores dtbo before boot).

### 2.4 Initramfs: eMMC root probe (A/B device, shared `userdata`)

**Correction 2026-10-12:** the G7 Power is **A/B**, not A-only (verified on the
unit: `boot_a`/`boot_b`, `dtbo_a`/`dtbo_b`, `system_a`/`system_b`,
`vendor_a`/`vendor_b`, `vbmeta_a`/`vbmeta_b`, plus a **shared** `userdata`;
the reference unit runs slot `_b`). The initramfs root probe is unaffected
because the packed cmdline pins `root=/dev/block/bootdevice/by-name/userdata`
and `userdata` is shared across slots. The old text below said A-only.

The G7 Power has eMMC storage with partitions
under `/dev/block/bootdevice/by-name/`. The shared initramfs
(`boot/initramfs/init.sh`) resolves the root device in this order for
`nuxel.device=g7power`:

1. `ROOT_SPEC` if set (explicit `root=` from the lk2nd/mainline cmdline),
2. else `/dev/block/bootdevice/by-name/userdata`,
3. else `/dev/block/bootdevice/by-name/system`,
4. else an error listing the available partitions under
   `/dev/block/bootdevice/by-name/` and an `emergency_shell`.

The root filesystem is formatted **ext4** (Phase 1 has no dm-verity/AVB —
the rootfs on `userdata` is intentionally writable during bring-up; see
§7). The s10plus and mustang initramfs paths are untouched and still
dispatch on their own `nuxel.device=` keys.

---

## 3. Two-phase fastboot

The G7 Power has **two different fastboot modes**, and knowing which one
you are in is critical. The stock ABOOT fastboot is the *bootstrap* mode;
lk2nd fastboot is the *Nuxel* mode.

| | Stock ABOOT fastboot | lk2nd fastboot |
|---|---|---|
| Entered via | Power off → **Vol Down + Power** | After lk2nd is flashed: `fastboot reboot bootloader` from stock ABOOT fastboot, or Vol Down + Power when lk2nd is installed on `boot` |
| What it can flash | `dtbo`, `boot`, `recovery`, `system`, `vendor`, `userdata`, … — anything the stock partition table exposes; enforces stock image policy on some partitions | Anything lk2nd exposes (typically `boot`, `dtbo`, `userdata`, …); loads mainline kernel + DTB + ramdisk |
| Purpose here | **Phase 1**: flash `dtbo` (first!) + flash `lk2nd.img` to `boot` | **Phase 2**: flash Nuxel `boot.img` + rootfs to `userdata` |
| cmdline / boot policy | Stock ABOOT boot verification applies | None — lk2nd just loads what you give it |
| Identity info | `fastboot getvar product` → `ocean` | Same getvar interface (lk2nd emulates fastboot getvar) |

**How to identify which mode you are in:**

- `fastboot getvar product` — both modes return `ocean`; if it returns
  garbage or fails, you are not talking to this device.
- `fastboot getvar version-baseband` / `fastboot getvar secure` — stock
  ABOOT answers; lk2nd answers a smaller set of getvars and may report
  `secure: no`.
- The on-screen text differs: stock ABOOT shows the Motorola logo +
  "FLASH MODE"/unlock state; lk2nd shows a small white/blue text
  bootloader banner with the lk2nd version string.
- `fastboot devices` works for both — the mode is not distinguishable from
  `fastboot devices` output alone; check `getvar` or the screen.

**Golden rule:** dtbo is flashed in **stock ABOOT fastboot**, lk2nd is
flashed in **stock ABOOT fastboot**, and the Nuxel boot.img + rootfs are
flashed in **lk2nd fastboot**. `boot/g7power/flash.sh` implements exactly
this two-phase flow (Phase 1 then Phase 2 in one invocation, or
`--dry-run` to preview every command).

---

## 4. Motorola unlock portal

A locked bootloader cannot flash lk2nd (stock ABOOT verifies the boot
partition). Unlock is required once, per device, via Motorola's official
portal. **Unlocking wipes the device** — back everything up first.

### 4.1 Full sequence

```bash
# 1. On the device: enable Developer Options (tap Build Number 7x),
#    enable USB debugging AND "OEM Unlocking".
# 2. Boot to stock ABOOT fastboot:
adb reboot bootloader

# 3. Read the unlock data (a long base64-ish string — SAVE IT):
fastboot oem get_unlock_data

# 4. Submit it at the Motorola unlock portal:
#    https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device
#    Paste the unlock data, submit, wait for the email with your unlock code.

# 5. Unlock (WIPES DEVICE — BACKUP FIRST):
fastboot oem unlock <YOUR_UNLOCK_CODE>

# 6. Reboot, re-enable USB debugging, continue with Phase 0 inventory.
fastboot reboot
```

`bash boot/g7power/flash.sh --unlock-help` prints this sequence.

### 4.2 What gets wiped / what to back up

- Unlocking wipes **userdata** (and in Motorola's flow, resets the device
  to factory state). Take the Phase 0 inventory **before** unlocking if you
  want stock Android data, or accept the wipe.
- The **protected partitions** (§5) are *not* wiped by unlocking, but you
  must never flash them from Nuxel either.
- Back up the **stock `boot.img` and `dtbo.img`** before flashing anything
  — they are your revert path and your source for the boot-image load
  addresses (§6, §7).
- **Never relock during development.** `fastboot oem lock` is only allowed
  behind an explicit `--production-relock` flag with a triple confirmation,
  and only once Nuxel is proven bootable — a relocked bootloader with a
  mainline boot image may not boot at all.

---

## 5. Protected partitions

The following partitions are **never touched by any Nuxel script, ever**
(denylist in `boot/g7power/flash.sh`, `boot/g7power/recovery.sh`,
`firmware/g7power/install-firmware.sh` and every partition-iterating
script; also encoded as `NUXEL_PROTECTED_PARTITIONS` in
`device/g7power/nuxel-ocean.conf` and `boot/g7power/boot-config.txt`):

| Partition | What lives there | Why it is irreplaceable |
|---|---|---|
| `modemst1` | Modem EFS (radio calibration, IMEI-related data) | Per-unit baseband calibration + identity; wiping = null IMEI / no signal, unrecoverable without Qualcomm service tools |
| `modemst2` | Modem EFS backup mirror | Second copy of the same per-unit radio identity |
| `fsg` | RF calibration / secure filesystem data | Per-unit RF tuning for the X9 LTE radio; wrong data = broken bands / no signal |
| `fsc` | Modem filesystem config | Modem state/config tied to the unit's calibration |
| `ddr` | DDR (memory) training data | Per-unit DRAM training parameters; corrupting it can prevent the device from booting at all |
| `persist` | Per-unit sensor/touch/display calibration + misc NVRAM | Wrong data = broken sensors/touch/backlight; only the unit's own data is valid |
| `misc` | Bootloader misc flags (recovery reason, etc.) | Standard Android "never touch" partition; corruption can wedge the boot path |

**Enforcement:** any loop over `/dev/block/bootdevice/by-name/` (or any
`fastboot flash` target) must be denylist-checked **before** the `dd` /
`fastboot flash` runs; the rootfs target partition (default `userdata`) is
validated against the list and refused on collision. Phase 1 never flashes
the modem at all (the X9 LTE modem is **not** ModemManager-ready; see §10).

**Back them up** (read-only, via the stock Android ADB session — this does
not modify anything):

```bash
adb shell "mkdir -p /sdcard/backup && for p in modemst1 modemst2 fsg fsc ddr persist misc; do dd if=/dev/block/bootdevice/by-name/\$p of=/sdcard/backup/\$p.img; done"
adb pull /sdcard/backup
```

---

## 6. Phase 0 device inventory and build gate

**Phase 0 is the immediate blocker.** `docs/g7power-device-inventory.md` is
the operator template: it lists every collection command (identity
getprops, `/proc/cmdline`, `cpuinfo`, full `dmesg` dump, `getevent -pl`
input dump, eMMC by-name listing + `/proc/partitions`, vendor
firmware/module listings, asound cards, WCNSS/qca firmware listings, stock
`boot.img` pull + header extraction) and the fill-in fields:
`DEVICE_VARIANT`, `BOOTLOADER_VERSION`, `KERNEL_ADDR`, `RAMDISK_ADDR`,
`TAGS_ADDR`, `WIFI_FW_FILENAMES`, `BT_FW_FILENAMES`, `AUDIO_UCM_CARD`,
`CAMERA_SENSORS`, `FINGERPRINT_SENSOR`, `NFC_PRESENT`.

The stock boot image header is parsed with the repo tool:

```bash
adb shell "dd if=/dev/block/bootdevice/by-name/boot of=/sdcard/stock-boot.img bs=4096"
adb pull /sdcard/stock-boot.img /tmp/stock-boot.img
python3 tools/read-boot-header-v1.py /tmp/stock-boot.img
# -> kernel_addr / ramdisk_addr / tags_addr / page_size / kernel_size /
#    ramdisk_size / dt_size / os_version / name / cmdline
```

**Why it is required:** every G7 Power artifact depends on data that only
the physical device can provide — the real kernel/ramdisk/tags load
addresses (stock ABOOT will not boot a mainline image at wrong addresses),
the real WCNSS/qca firmware filenames for the WiFi/BT manifest, the real
ALSA card name for the WCD9335 UCM, and the real camera/fingerprint
identity. Fabricating these is a brick risk, so the repo refuses to guess.

### 6.1 The `_check_g7power_inventory()` gate

Every G7 Power build/flash script (`kernel/g7power/build-kernel.sh`,
`boot/g7power/flash.sh`, `images/g7power/build.sh`,
`firmware/g7power/install-firmware.sh`) embeds the same gate: while
`KERNEL_ADDR`, `RAMDISK_ADDR`, `TAGS_ADDR` still contain `PLACEHOLDER` or
`WIFI_FW_FILENAMES` still contains `UNKNOWN` in
`docs/g7power-device-inventory.md`, the script prints the Phase 0 reminder
and exits 1. `--help` and `--dry-run` are exempt so the operator can
preview commands before inventory exists.

```bash
_check_g7power_inventory() {
    local inv="${NUXEL_ROOT}/docs/g7power-device-inventory.md"
    if grep -q "KERNEL_ADDR:.*PLACEHOLDER" "${inv}" 2>/dev/null; then
        echo "ERROR: G7 Power device inventory incomplete."
        echo "       Run Phase 0 commands in docs/g7power-device-inventory.md"
        echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, WIFI_FW_FILENAMES"
        exit 1
    fi
}
```

**Never fabricate a value to pass the gate.** Wrong addresses or firmware
filenames are worse than no build.

---

## 7. Exact build commands

> ⚠️ These commands require the Phase 0 inventory to be complete (§6), a
> working `aarch64-linux-gnu-` toolchain (see
> `kernel/g7power/README-toolchain.md`), and — for the flash steps — an
> unlocked G7 Power in the correct fastboot mode (§3, §4).

```bash
# Phase 0: inventory (adb, device in stock Android)
# Follow docs/g7power-device-inventory.md and fill at minimum:
#   KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR, WIFI_FW_FILENAMES
# (scripts refuse to run while any of them is PLACEHOLDER/UNKNOWN)

# Phase 1: lk2nd + kernel
bash boot/g7power/lk2nd/README.md   # read lk2nd build instructions (msm8953)
NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --clone

# Phase 2: flash lk2nd (stock ABOOT fastboot mode)
#   dtbo is flashed FIRST (mandatory), then lk2nd to the boot partition.
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
    --device g7power --dtbo stock-dtbo.img --lk2nd lk2nd.img

# Phase 3: flash Nuxel (lk2nd fastboot mode)
NUXEL_DEVICE=g7power bash images/g7power/build.sh
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
    --device g7power --boot build/out/g7power/nuxel-ocean-boot.img \
    --rootfs build/out/g7power/nuxel-ocean-rootfs.img
```

### 7.1 What each command produces

| Command | Produces | Notes |
|---|---|---|
| `build-kernel.sh --clone` | `kernel/g7power/.build/out/arch/arm64/boot/Image.gz`, `kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb`, `kernel/g7power/.build/modules-staging/lib/modules/` | Clones `msm8953-mainline/linux` (branch `master`), applies `kernel/g7power/patches/*.patch`, merges `kernel/g7power/defconfig` via `merge_config.sh`, runs `olddefconfig`, builds `Image.gz dtbs modules` |
| `images/g7power/build.sh` | `build/out/g7power/nuxel-ocean-boot.img`, `build/out/g7power/nuxel-ocean-rootfs.img`, `build/out/g7power/lk2nd.img` (copy if built, else `lk2nd.img: NOT YET BUILT`), `build/out/g7power/build-manifest.json` | Packs boot via `boot/g7power/pack-boot-v1.sh`, assembles rootfs via `images/mkrootfs.sh`, installs firmware + device configs + kernel modules into the rootfs |
| `flash.sh --dtbo … --lk2nd …` | — | Phase 1 (stock ABOOT fastboot): dtbo first, lk2nd to `boot`, reboot into lk2nd fastboot |
| `flash.sh --boot … --rootfs …` | — | Phase 2 (lk2nd fastboot): Nuxel boot.img to `boot`, rootfs to `userdata`, reboot |

### 7.2 Boot image (header v1, page 2048)

The packer defaults (`boot/g7power/pack-boot-v1.sh`) are the *typical*
msm8953 values, **all marked PLACEHOLDER and VERIFY**:

```
page_size=2048
kernel_addr=PLACEHOLDER_0x80008000   # typical for msm8953; VERIFY
ramdisk_addr=PLACEHOLDER_0x81000000  # typical for msm8953; VERIFY
tags_addr=PLACEHOLDER_0x80000100     # typical for msm8953; VERIFY
name="nuxel-g7power"
```

Use `--addresses-from-device` to extract the real addresses from the stock
`boot.img` (Phase 0 dump) instead of the placeholders:

```bash
bash boot/g7power/pack-boot-v1.sh \
    --kernel kernel/g7power/.build/out/arch/arm64/boot/Image.gz \
    --ramdisk boot/initramfs/initramfs.cpio.gz \
    --dtb kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb \
    --cmdline "console=ttyMSM0,115200 earlycon=msm_geni_serial,0xa88000 nuxel.device=g7power root=/dev/block/bootdevice/by-name/userdata rootfstype=ext4 rootwait rw" \
    --addresses-from-device /tmp/stock-boot.img \
    --output /tmp/nuxel-ocean-boot.img
```

### 7.3 Phase 1 has no dm-verity / AVB

The G7 Power has no dynamic partitions (`system_a`/`system_b` are plain, so the mustang
`vbmeta` / `vendor_boot` / `init_boot` / fastbootd flow does **not** apply
and is never used. Phase 1 emits an **unsigned, writable ext4 rootfs on
`userdata`** with no dm-verity/AVB — deliberately: bring-up needs an
editable rootfs and adb/fastboot debugging until the boot chain is proven.
dm-verity/AVB for the G7 Power is a later phase, documented but not
implemented. Never copy Pixel/Samsung signing material or firmware into the
G7 Power tree.

---

## 8. ILI2117 touch: solved (config bug), not a missing driver

The mainline `sdm632-motorola-ocean.dts` (in `msm8953-mainline/linux`)
declares the touch controller as:

```dts
&i2c_3 {
        status = "okay";
        touchscreen@41 {
                compatible = "ilitek,ili2117";
                reg = <0x41>;
                interrupt-parent = <&tlmm>;
                interrupts = <65 IRQ_TYPE_EDGE_FALLING>;
                touchscreen-inverted-x;
        };
};
```

**The "no touchscreen" blocker was a Nuxel config bug, not missing support.**
Nuxel requested `CONFIG_TOUCHSCREEN_ILI2117=y` (hardware name mistaken for a
Kconfig symbol), which **does not exist** in
the tree; `olddefconfig` silently dropped it, so `CONFIG_TOUCHSCREEN_ILI210X`
stayed unset and no ILI2117 driver was ever built. ILI2117 support lives in
the multi-chip mainline driver:

```
drivers/input/touchscreen/ili210x.c  ->  CONFIG_TOUCHSCREEN_ILI210X
    of_device_id "ilitek,ili2117" -> ili211x_chip
```

Verified against the real tree (`msm8953-mainline/linux`, Linux 6.19):

* `drivers/input/touchscreen/ili210x.c` contains
  `{ .compatible = "ilitek,ili2117", .data = &ili211x_chip }` plus the
  43-byte ILI211x frame decoder (`ILI211X_DATA_SIZE 43`, checksum-checked,
  up to 10 contacts, no firmware request).
* `drivers/input/touchscreen/Kconfig` defines `TOUCHSCREEN_ILI210X`
  (its help text only mentions ILI2102/2103/2105 — that stale text is the
  origin of the "no ILI2117 driver" myth).
* The built kernel image from the previous pass really did contain
  `# CONFIG_TOUCHSCREEN_ILI210X is not set` and the rootfs contained no
  ilitek module at all — i.e. the flashable artifacts had **zero** touch
  driver.

So: the driver is upstream and exact-matches this binding. There is nothing
to port, and **do not** write an `ili210x.c` or port the vendor stack.

**Verified on the real unit (stock Android 10, XT1955-4, slot `_b`) — see
`g7power/stock-evidence/`:**

| Fact | Observed | Matches mainline DT? |
|---|---|---|
| Touch I²C client | `3-0041` on `78b7000.i2c` (i2c-3) | ✅ i2c_3 @ 0x41 |
| IRQ | `/proc/interrupts`: IRQ 286 `msm8953-gpio`/`msmgpio` **65 Edge** owner `ilitek` | ✅ tlmm 65, edge |
| Input device | `/dev/input/event1`, name `tchip`, `INPUT_PROP_DIRECT`, ABS_MT X max 719 / Y max 1519, slots 0..9 | ✅ 720x1520 panel, 10 contacts |
| Bound driver | `/sys/bus/i2c/drivers/**ILITEK_TDDI**` | ⚠️ vendor TDDI driver (see caveat) |

**Honest caveat:** stock Motorola binds this touch node with the out-of-tree
vendor driver `ILITEK_TDDI`, not `ili210x`. The mainline DTS was nevertheless
authored for this exact phone with `ilitek,ili2117`, so the expectation is
that `ili210x` binds and works; but **that has not been proven on hardware
yet**. If `ili210x` binds and the IRQ fires but no valid 43-byte frames
arrive, re-read §15 of `nuxel-g7power-touchscreen.md` (compare live DT vs
built DT, then re-check the physical controller) before attempting any port.

**How to verify on the device after Nuxel boots:**

```bash
uname -a
modinfo ili210x 2>/dev/null            # only if built as a module (=m)
dmesg | grep -iE 'ili210|ili211|ilitek|i2c-3|78b7000'
grep -A12 -i 'ILI210x' /proc/bus/input/devices   # expect "ILI210x Touchscreen"
find /sys/bus/i2c/devices -maxdepth 1 -name '*-0041'
readlink -f /sys/bus/i2c/devices/*-0041/driver    # expect .../ili210x_i2c
grep -iE 'ili210|ilitek|touch' /proc/interrupts  # counter must rise on touch
evtest /dev/input/eventX                          # ABS_MT_* events
```

| Observation | Layer to fix |
|---|---|
| No `*-0041` I²C device | DT/controller not instantiated, wrong runtime DT |
| `*-0041` present, no `ili210x` driver link | Kconfig/module/modalias (this was the bug) |
| Bound, IRQ counter never rises | IRQ/pinctrl/trigger/power/reset, or wrong controller |
| IRQ rises, no evdev events | packet/checksum path (ILI211x protocol mismatch) |
| Events but mirrored | orientation config — do **not** double-invert (see below) |

**Inverted-X:** the DT already carries `touchscreen-inverted-x`, and
`ili210x` reports through the generic touchscreen-property helpers, so the
kernel inverts X once. The Xorg InputClass that also carried
`TransformationMatrix "-1 0 1 0 1 0 0 0 1"` is therefore **disabled**
(`configs/g7power/libinput/99-nuxel-ocean-touch.conf.disabled`); enabling it
as-is would mirror touch. Keeping it disabled removes one whole layer of
orientation uncertainty for the first boot. (It also matched the
non-existent product name `ILI2117*`, so it never actually applied.)

**Firmware:** nothing to install. Only the unrelated ILI251x path in
`ili210x.c` requests `ilitek/ili251x.bin`. Do not install it for ILI2117.

## 9. WiFi: wcn36xx vs ath10k

The G7 Power's WiFi/BT combo is the Qualcomm **WCN3680B**
(802.11 b/g/n, 2.4 GHz). The correct mainline driver stack is:

- **`wcn36xx`** (`CONFIG_WCN36XX`) — the mainline mac80211 driver for
  WCNSS 3680-class chips,
- **`CONFIG_QCOM_WCNSS_PIL`** (peripheral image loader) — loads the WCNSS
  firmware images (`WCNSS_qcom_cfg.ini`, `WCNSS_qcom_wlan_nv.bin`,
  `WCNSS_*.img`),
- **`CONFIG_WCNSS_CORE`** — WCNSS core/remoteproc plumbing.

**Never use `ath10k` for this chip.** ath10k targets QCA6174/QCA9377 and
other 10k-series devices; the WCN3680B is not an ath10k device. If
`CONFIG_ATH10K` is enabled and something tries to bind it, the result is
either a probe failure or a driver claiming the device with **no matching
firmware** — no `wlan0` interface, no WiFi, plus confusing dmesg noise.
Likewise **never use `brcmfmac`** — that is Broadcom-only silicon
(mustang's BCM4390 path) and cannot drive the WCN3680B at all.

The kernel defconfig (`kernel/g7power/defconfig`) therefore sets
`CONFIG_WCN36XX=y`, `CONFIG_QCOM_WCNSS_PIL=y`, `CONFIG_WCNSS_CORE=y` and
explicitly leaves `# CONFIG_ATH10K is not set` and
`# CONFIG_BRCMFMAC is not set`. The firmware manifest
(`firmware/g7power/manifest.yml`) expects the WCNSS files under
`/vendor/firmware/` and `/vendor/firmware/wlan/prima/` (collected via
`adb shell ls /vendor/firmware/WCNSS*` and
`adb shell ls /vendor/firmware/wlan/prima/` in Phase 0). Bluetooth on the
same chip uses **`hci_qca`** (`CONFIG_BT_HCIUART_QCA`) with firmware under
`/vendor/firmware/qca/` — never `CONFIG_BT_HCIUART_BCM`.

---

## 10. Driver status matrix (honest)

| Subsystem | Hardware | Kernel driver | Status | Notes |
|---|---|---|---|---|
| GPU | Adreno 506 | `CONFIG_DRM_MSM` (freedreno) | ✅ ok (mainline) | Needs `a506_zap.mbn` (firmware, checksum UNKNOWN until Phase 0) |
| Display | 6.2" IPS LCD 1520x720 (19:9) | MSM DSI + panel-simple; framebuffer handed off from lk2nd | 🚧 boot-time framebuffer | DDIC/LCM name UNKNOWN (Phase 0); backlight TI LM3697 i2c_5 @ 0x36 (`CONFIG_BACKLIGHT_TI_LM3697`); wlr-randr 1520x720 on DSI-1 |
| Touch | Ilitek ILI2117, i2c_3 @ 0x41, IRQ tlmm 65, inverted-x | `CONFIG_TOUCHSCREEN_ILI210X` | ⚠️ verify-on-device | Some units boot without touch — check `evtest /dev/input/eventX` (§8) |
| WiFi | WCN3680B (b/g/n 2.4 GHz) | `wcn36xx` + `CONFIG_QCOM_WCNSS_PIL` | ⬜ needs firmware | WCNSS filenames/checksums UNKNOWN until Phase 0 (`WIFI_FW_FILENAMES` gate); NOT ath10k/brcmfmac |
| Bluetooth | WCN3680B (BT 4.2) | `hci_qca` (`CONFIG_BT_HCIUART_QCA`) | ⬜ needs firmware | qca/ firmware filename UNKNOWN until Phase 0 |
| Audio | WCD9335 (cajon-v2) ASoC | `CONFIG_SND_SOC_WCD9335` | 🚧 UCM card TBD | ALSA card name from `aplay -l`/`/proc/asound/cards` (Phase 0); UCM2 reference: `msm8953-mainline/alsa-ucm-conf`; 48000 Hz stereo |
| Modem | Snapdragon X9 LTE (SDM632, no 5G) | — | ❌ not MM-ready | No upstream ModemManager plugin; **Phase 7 stretch**; never flash `modemst1 modemst2 fsg fsc ddr` |
| Sensors | BMI160 (accel+gyro), MMC3630KJ (mag), TMD2725 (prox/ALS) | mainline IIO (`CONFIG_BMI160_I2C`, mag/ALS driver TBD from tree) | ⬜ verify-on-device | IIO drivers in mainline; verify each node on the unit |
| Camera | rear/front sensors UNKNOWN | — | ⬜ UNKNOWN | Identify from dmesg in Phase 0; **Phase 6+** |
| Fingerprint | rear-mounted, UNKNOWN | — | ⬜ UNKNOWN | Identify in Phase 0; **Phase 6+** |
| NFC | none on most ocean variants | — | ⬜ verify only | Check dmesg for NFC + `ls /dev/nfc*` during Phase 0 |

Legend: ✅ ok (mainline) / 🚧 works in the vendor/pmOS tree or needs
bring-up glue / ⬜ needs firmware or inventory / ❌ deferred. Nothing here
is "verified" until the Phase 0 inventory and a real kernel build confirm
it on this unit.

---

## 11. EDL unbrick path (Qualcomm 9008)

If the device is hard-bricked (no fastboot, no boot logo, not recognized
by `fastboot devices`), the Qualcomm **EDL (Emergency Download Mode)** is
the last-resort rescue path. It runs in the PBL and can rewrite the
partition table from scratch.

### 11.1 Entering EDL

1. Power the device fully off.
2. Hold **Vol Down + Vol Up** (both volume keys), then plug the USB cable
   into the host.
3. The device should enumerate as a Qualcomm device:
   - `lsusb | grep "05C6:9008"` → `Qualcomm, Inc. Gobi Wireless Modem
     (QDL loader)` (VID `05C6`, PID `9008`) — or `900E` on some units.
   - Linux may also show `/dev/ttyUSB*` (e.g. `/dev/ttyUSB0`) — that is
     the EDL serial port the `edl` tool talks to.
4. If it enumerates as `900E` instead of `9008`, you are in **EDL with
   Sahara handshake required** — the `edl` tool handles both.

### 11.2 Tools

- **`bkerler/edl`** (recommended, cross-platform):
  ```bash
  git clone https://github.com/bkerler/edl
  cd edl
  pip install -r requirements.txt
  # or: pip install edl
  python3 edl.py --help
  ```
- **QFIL** (Windows, from Qualcomm's QPST tool suite) — GUI alternative
  for flashing full stock `prog_emmc_firehose` XML packages.

### 11.3 What to flash to recover

With stock firmware files (from the correct XT1955 variant — match the
region/model of your unit), restore at minimum:

```bash
# List partitions first (read-only) to confirm the connection:
python3 edl.py rl          # print the partition table
# Then restore the boot chain + dtbo (stock files from your variant):
python3 edl.py w boot  stock-boot.img
python3 edl.py w dtbo  stock-dtbo.img
python3 edl.py w recovery stock-recovery.img   # if available
# If the unit still will not boot, restore the full stock package:
python3 edl.py f stock/  # firehose: flash everything in the stock dir
```

`bash boot/g7power/flash.sh --edl` prints these instructions. After EDL
recovery the device boots stock Android again; you can then re-run Phase 0
and the two-phase Nuxel flash (§7). Note: EDL is the *unbrick* path, not a
normal flash path — prefer fastboot whenever the device will enter it.

---

## 12. Safety rules recap

1. **Explicit selection only** — `--device` > `NUXEL_DEVICE` > error; never
   guess. `nuxel.device=g7power` on the cmdline matches the selected key.
2. **Identity check before every flash** — `fastboot getvar product` must
   be `ocean`, `serialno` must match `NUXEL_EXPECTED_SERIAL` if set, and
   `unlocked` must be `yes`; refuse on any mismatch.
3. **dtbo before lk2nd, always** — enforced in code; the classic msm8953
   soft-brick is prevented by this order, never by luck.
4. **Two-phase fastboot, never reordered** — dtbo + lk2nd in stock ABOOT
   fastboot; Nuxel boot.img + rootfs in lk2nd fastboot.
5. **Protected partitions never touched** — `modemst1 modemst2 fsg fsc ddr
   persist misc` (denylist-checked before every `dd` / `fastboot flash`).
6. **Never relock the bootloader during development** — `fastboot oem lock`
   only behind an explicit `--production-relock` flag with triple
   confirmation, and only after Nuxel is proven bootable.
7. **Never fabricate data** — checksums, load addresses, firmware
   filenames, and driver status stay `UNKNOWN` / `PLACEHOLDER` until the
   physical device provides them (Phase 0). `KERNEL_ADDR`, `RAMDISK_ADDR`,
   `TAGS_ADDR`, `WIFI_FW_FILENAMES` gate every build/flash script.
8. **No mustang/s10plus contamination** — no Pixel/Broadcom/PowerVR/
   Samsung/Exynos firmware, no vendor_boot/init_boot/vbmeta/fastbootd, no
   A/B logic anywhere in the G7 Power path.
9. **Per-device isolation** — every G7 Power artifact lives under
   `g7power/`; shared files only branch on the device key.
10. **Honest status** — the G7 Power path is **not** flashable/verified
    until Phase 0 inventory + real firmware + real kernel build complete.

---

## 13. References

- `phones/g7power/g7power-prompt.md` — the G7 Power implementation prompt (source of
  truth for this bring-up).
- `docs/g7power-device-inventory.md` — Phase 0 operator template + build
  gate input (fields `KERNEL_ADDR`, `RAMDISK_ADDR`, `TAGS_ADDR`,
  `WIFI_FW_FILENAMES`, …).
- `boot/g7power/boot-config.txt` — machine-readable boot facts (header v1,
  page 2048, PLACEHOLDER addresses, protected partitions).
- `boot/g7power/lk2nd/README.md` — lk2nd source, msm8953 build and flash
  sequence.
- `boot/g7power/flash.sh`, `boot/g7power/recovery.sh` — the two-phase
  flash/recovery tooling.
- `kernel/g7power/build-kernel.sh`, `kernel/g7power/defconfig`,
  `kernel/g7power/README-toolchain.md` — kernel build wrapper, msm8953
  fragment, toolchain notes.
- `firmware/g7power/manifest.yml` — firmware tree (all checksums UNKNOWN).
- `device/g7power/deviceinfo`, `device/g7power/nuxel-ocean.conf` — pmOS
  deviceinfo + Nuxel device config.
- `configs/g7power/` — display, libinput, alsa-ucm, modem, pipewire,
  wireplumber device configs.
- postmarketOS motorola-ocean device page:
  `https://wiki.postmarketos.org/wiki/Motorola_Moto_G7_Power_(motorola-ocean)`
- lk2nd: `https://github.com/msm8916-mainline/lk2nd` (branch `master`,
  target `msm8953`).
- Mainline kernel: `https://github.com/msm8953-mainline/linux`
  (`linux-postmarketos-qcom-msm8953`), DTB
  `qcom/sdm632-motorola-ocean.dtb`.
- msm8953-mainline UCM configs:
  `https://github.com/msm8953-mainline/alsa-ucm-conf` (WCD9335).
- Motorola bootloader unlock portal:
  `https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device`
- EDL tool: `https://github.com/bkerler/edl`; QFIL (QPST) for Windows.
- `docs/s10plus-bringup.md`, `docs/mustang-recovery-bringup.md` — sibling
  per-device bring-up docs (cross-reference only; no shared device data).

---

_Build the bunker first. Add the rave lights later._ —
G7 Power bring-up status: **not flashable/verified until Phase 0 inventory +
real firmware + real kernel build.** Phase 0 starts with ADB + dmesg + a
stock boot.img backup. That is your foundation.
