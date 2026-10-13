# Nuxel — Motorola Moto G7 Power (SDM632) Full Implementation Prompt

> **⚠️ Corrections applied 2026-10-12 (unit evidence, see `g7power/stock-evidence/`).**
> 1. **Touch is NOT a missing driver.** `CONFIG_TOUCHSCREEN_ILI2117` does not exist; ILI2117 is handled by mainline `ili210x` (`CONFIG_TOUCHSCREEN_ILI210X`, OF match `ilitek,ili2117`). This repo's defconfig asked for the wrong symbol, so no touch driver was ever built. Fixed + kernel rebuilt. Full analysis: `nuxel-g7power-touchscreen.md`; summary: `g7power-go-guide.md` §1.7 and `docs/g7power-bringup.md` §8.
> 2. **The G7 Power is A/B, not A-only** (`boot_a/boot_b`, `dtbo_a/dtbo_b`, `system_a/b`, `vendor_a/b`, `vbmeta_a/b`, shared `userdata`; reference unit runs slot `_b`). Any "A-only" statement below for g7power is superseded.
> 3. **Stock touch driver on Android is the vendor `ILITEK_TDDI`**, not `ili210x` — mainline bind is expected but still unproven.
> 4. `/vendor/firmware*`, `dmesg`, `/proc/cmdline` and `/dev/block/*` are **root-only** on this stock ROM; adb (unrooted) cannot back up stock images or pull blobs.


## For: Build Agent / Senior Embedded-Linux Bring-Up Engineer
## Repo: NUXEL_ROOT (resolve via `git rev-parse --show-toplevel`)
## Based on: Deep analysis of Nuxel v0.1.0 repo + `nuxel-g7power.md` + `docs/hardware-ids.md` + `docs/driver-status.md`

---

> **How to use this file:** This is the complete, self-contained implementation
> prompt for the G7 Power target. Copy everything from `## ROLE` downward into
> your agent. The agent must implement every task in order. Do not skip tasks.
> Do not fabricate checksums, firmware blobs, device IDs, or driver status.
> Mark every unknown as `UNKNOWN`/`PLACEHOLDER`/`TBD` and require the operator
> to fill them from the physical device. This prompt supersedes the stub sections
> of `nuxel-g7power.md` with deeper implementation detail drawn from the full
> repo analysis.

---

## ROLE

You are a senior embedded-Linux / phone-OS bring-up engineer working on the
**Nuxel** repository. Your job is to implement the **Motorola Moto G7 Power
(XT1955, Snapdragon 632 / SDM632, codename `ocean`)** as a fully-separated
third hardware target alongside the existing mustang (Pixel 10 Pro XL) and
s10plus (Galaxy S10+) scaffolds — without breaking either existing target and
without cross-contaminating any device-specific artifact.

This work extends the stub `g7power/` directories already created by the S10+
implementation pass. Replace every stub with a real, working implementation
that exactly mirrors the quality and safety standards of the S10+ pass.

---

## NON-NEGOTIABLE SAFETY RULES

These rules are absolute. Violating any of them triggers an unconditional abort
and an error message to the operator.

1. **Every device-specific artifact lives under a per-device directory** keyed
   by `NUXEL_DEVICE`:
   - `mustang`  → `google-pixel-10-pro-xl/`
   - `s10plus`  → `s10plus/`
   - `g7power`  → `g7power/`  (codename `ocean`)

2. **No device file may contain multiple devices' data.** Shared code is
   device-agnostic. Any line in a shared file that names a device must be
   behind a device-key branch or moved to the per-device directory.

3. **The G7 Power uses `fastboot` — but NOT the mustang Google ABL flow.**
   - No `vendor_boot`, `init_boot`, `vbmeta`, `fastbootd` super partition, or
     A/B slot logic. These are mustang-only concepts.
   - The G7 Power flash sequence is: `dtbo` → `lk2nd` → reboot into lk2nd
     fastboot → `boot` → `userdata`. This exact order is mandatory.
   - **`dtbo` MUST be flashed before `lk2nd`.** A missing/corrupt dtbo is the
     classic soft-brick on msm8953. This rule is enforced in code, not just docs.

4. **Verify device identity before every flash operation.** In every G7 Power
   flash script, execute:
   ```sh
   PRODUCT=$(fastboot getvar product 2>&1 | grep '^product:' | awk '{print $2}')
   [ "${PRODUCT}" = "ocean" ] || {
       echo "ERROR: Expected 'ocean', got '${PRODUCT}'. Refusing to flash."
       exit 1
   }
   ```
   Also check `fastboot getvar serialno` matches the operator's expected serial
   if `NUXEL_EXPECTED_SERIAL` is set. Refuse on mismatch.

5. **Never touch the following partitions** (per-unit calibration, IMEI, MAC,
   radio calibration — irreplaceable if wiped):
   `modemst1`, `modemst2`, `fsg`, `fsc`, `ddr`, `persist`, `misc`.
   Any script that iterates over `/dev/block/bootdevice/by-name/` must
   explicitly skip these with a denylist check before any `dd` or
   `fastboot flash`.

6. **Do not relock the bootloader** (`fastboot oem lock`) during development or
   testing. Relocking is a production-only operation and must be explicitly
   gated by a `--production-relock` flag with a triple confirmation prompt.

7. **Do not invent or fabricate firmware blobs, checksums, device IDs, or
   driver status.** Mark every unknown value explicitly as `UNKNOWN` / `TBD` /
   `PLACEHOLDER`. Require the operator to fill them from the physical device
   (Phase 0 inventory).

8. **Do not delete or overwrite mustang or s10plus files.** The three-device tree
   must remain consistent. Any file you move or refactor must leave a working
   wrapper or symlink at the old path if anything references it.

9. **Pass `bash -n` and `shellcheck -S warning`** on every new shell script.
   Use `#!/usr/bin/env bash` and `set -euo pipefail` for all new scripts.
   No bashisms inside `#!/bin/sh` scripts.

---

## REPO CONTEXT (deep analysis — do not hallucinate past this)

### Current repo state relevant to G7 Power

Following the S10+ implementation pass, stub `g7power/` directories exist in:
`firmware/g7power/`, `kernel/g7power/`, `device/g7power/`, `boot/g7power/`,
`configs/g7power/`, `images/g7power/`. Each stub contains only placeholder
`README.md` files and empty or comment-only config stubs.

**What already exists and must NOT be broken:**
- `tools/nuxel-device-select.sh` — shared device selector; `g7power`/`ocean`
  already resolves to `g7power` directory. Do not modify this mapping, only
  extend it if needed.
- `boot/initramfs/init.sh` — extended for mustang A/B and s10plus A-only UFS.
  The G7 Power A-only eMMC path is stubbed as `TODO` — implement it fully.
- `images/mkrootfs.sh` — device-agnostic; reuse without modification.
- All three UTM VM verify suites (PASS=22/17, HARD PASS) — must still pass
  after this implementation.

**Critical build chain differences from s10plus:**
- The s10plus uses a custom U-Boot chainload (chiffathefox/u-boot,
  exynos9820). The G7 Power uses **lk2nd** (msm8916-mainline/lk2nd) —
  completely different project, different build system, different flash sequence.
- The s10plus has NO fastboot. The G7 Power DOES have fastboot (via lk2nd and
  stock ABOOT), so the flash script structure is different.
- The s10plus uses UFS; the G7 Power uses **eMMC**. Partition paths differ:
  `/dev/block/bootdevice/by-name/` for G7 Power.
- The s10plus mkbootimg was v1 (same format). The G7 Power also needs v1, but
  the load addresses are different and must be extracted from the stock `boot.img`.
- `images/bootpack/mkbootimg.py` is v3/v4 only — the G7 Power also needs the
  v1 packer from `boot/s10plus/pack-boot-v1.sh`. Reuse that script if it is
  general enough, or create `boot/g7power/pack-boot-v1.sh` as a copy with
  G7-specific defaults.

---

## VERIFIED MOTOROLA MOTO G7 POWER HARDWARE FACTS
### (Authoritative — do not contradict or extend without a cited source)

| Component | Value | Source |
|---|---|---|
| Device | Motorola Moto G7 Power (XT1955) | postmarketOS `motorola-ocean` |
| Codename | `ocean` | postmarketOS / lk2nd |
| SoC | Qualcomm **Snapdragon 632 (SDM632)** — 4× Kryo 250 Gold (Cortex-A73) + 4× Kryo 250 Silver (Cortex-A53) @ 1.8 GHz, 14 nm | pmOS `qcom-msm8953` / SDM632 spec |
| SoC family | `msm8953` (SDM632 is SDM450/SDM625/SDM632 family, same msm8953 DT tree) | postmarketOS |
| GPU | Qualcomm **Adreno 506** → mainline **freedreno** (`CONFIG_DRM_MSM`) | pmOS / msm8953 kernel |
| RAM | 3 GB or 4 GB LPDDR3 (variant-dependent) | Motorola / reviews |
| Storage | 32 GB or 64 GB **eMMC** + microSD slot | Motorola |
| eMMC path | `/dev/block/bootdevice/by-name/` | pmOS msm8953 |
| Display | 6.2″ IPS LCD, **1520×720**, 19:9 ratio | Motorola / reviews |
| Backlight | TI **LM3697** @ I2C `i2c_5` address `0x36` | `sdm632-motorola-ocean.dts` (mainline) |
| Touch | Ilitek **ILI2117** @ I2C `i2c_3` address `0x41`, IRQ `tlmm 65`, `inverted-x` | `sdm632-motorola-ocean.dts` (mainline) |
| Touch driver | `ili210x` (mainline `CONFIG_TOUCHSCREEN_ILI210X`) | mainline kernel |
| WiFi | Qualcomm **WCN3680B** (802.11 b/g/n, 2.4 GHz only) | SDM632 spec / pmOS |
| WiFi driver | `wcn36xx` + `CONFIG_QCOM_WCNSS_PIL` (NOT `ath10k`) | pmOS msm8953 |
| Bluetooth | BT 4.2 (integrated in WCN3680B) | SDM632 spec |
| BT driver | `hci_qca` | pmOS msm8953 |
| Modem | Qualcomm Snapdragon **X9 LTE** (integrated, Category 7, no 5G) | SDM632 spec |
| Audio codec | Qualcomm **WCD9335** (cajon-v2) ASoC | pmOS `qcom-msm8953` |
| Sensors | Bosch **BMI160** (accel+gyro), MEMSIC **MMC3630KJ** (magnetometer), AMS **TMD2725** (prox+ALS) | pmOS wiki (XT1955-5 confirmed) |
| NFC | **None** (most ocean variants) — verify on physical device | `docs/hardware-ids.md` |
| Fingerprint | Rear-mounted — exact sensor TBD from physical device | `docs/hardware-ids.md` |
| Battery | 5000 mAh, **15W TurboPower** (Qualcomm Quick Charge 3.0) | Motorola |
| Shipped kernel | Qualcomm **4.9** downstream | Motorola OSS |
| Boot model | **A/B** (`boot_a/boot_b`, `dtbo_a/dtbo_b`, shared `userdata`; unit on slot `_b`) — corrected 2026-10-12 from the previous wrong "A-only" claim | Motorola partition table (unit evidence) |
| Partition table | `boot`, `system`, `vendor`, `dtbo`, `userdata`, `recovery` (separate) | Motorola / pmOS |
| Boot image format | **Legacy Android boot image header v1** (page 2048) | Motorola / pmOS |
| Flash tooling | **`fastboot`** (stock ABOOT + lk2nd) + **EDL 9008** (unbrick) | pmOS msm8953 |
| Unlock method | `fastboot oem get_unlock_data` → Motorola portal → `fastboot oem unlock <CODE>` | Motorola unlock portal |
| Touch caveat | ILI2117 DTS node present in mainline, but some units boot with no touchscreen — verify on device | pmOS wiki user notes |

### G7 Power Boot Chain (verified from postmarketOS)

```
Qualcomm Boot ROM (PBL)
    │
    ▼
Stock ABOOT (Motorola primary bootloader)
    │  Initializes: DDR, eMMC, display (framebuffer handoff to lk2nd)
    │  CANNOT: accept mainline DTBs or cmdline correctly
    │  CAN: boot a v1 boot.img from the boot partition
    │
    ▼ (we write lk2nd.img to the boot partition via fastboot)
lk2nd (msm8916-mainline/lk2nd)
    │  Qualcomm mainline LK2ND secondary bootloader
    │  Builds for msm8953 target
    │  Presents its own fastboot interface (on reboot into lk2nd)
    │  Accepts mainline kernel DTBs correctly
    │  Passes correct cmdline to kernel
    │
    ▼ (flash boot.img via lk2nd's fastboot)
linux-postmarketos-qcom-msm8953
    │  Close-to-mainline kernel for msm8953/SDM632
    │  nuxel.device=g7power on cmdline
    │
    ▼
Nuxel initramfs
    │  Probes /dev/block/bootdevice/by-name/userdata (eMMC A-only)
    │
    ▼
Nuxel rootfs → Phosh + GTK4 + PWA apps
```

**Why lk2nd is required:** Stock ABOOT does not correctly pass the kernel
cmdline and cannot accept mainline-compatible device trees. lk2nd is the
standard solution for all msm8953/SDM632 mainline Linux devices (pmOS, etc.).

**The dtbo-first rule:** On msm8953, the stock ABOOT reads the `dtbo` partition
to set up the display and some hardware before handing off to lk2nd. If dtbo
is corrupted or missing, ABOOT may hang before lk2nd even loads. Always flash
a known-good `dtbo` before writing lk2nd to the `boot` partition.

**The two-phase fastboot:** There are TWO fastboot modes on the G7 Power:
1. **Stock ABOOT fastboot** (reached via `adb reboot bootloader` or
   Vol Down + Power) — use this to flash `dtbo` and the initial `lk2nd.img`.
2. **lk2nd fastboot** (reached via `adb reboot bootloader` after lk2nd is
   installed) — use this to flash the mainline kernel `boot.img` and rootfs.
   lk2nd exposes a different device string and may behave slightly differently.
Every script must document which fastboot phase it targets.

### G7 Power Community Resources (authoritative)

| Resource | URL |
|---|---|
| pmOS msm8953 generic | https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_450/625/626/632_(MSM8953) |
| pmOS Moto G7 Power | https://wiki.postmarketos.org/wiki/Motorola_Moto_G7_Power_(motorola-ocean) |
| lk2nd bootloader | https://github.com/msm8916-mainline/lk2nd |
| msm8953 mainline kernel | https://github.com/msm8953-mainline/linux |
| msm8953 ALSA UCM configs | https://github.com/msm8953-mainline/alsa-ucm-conf |
| Motorola unlock portal | https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device |
| SDM632 DTS (mainline) | `arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dts` in mainline kernel |

### G7 Power Driver Matrix (honest status at Nuxel v0.2.0)

| Subsystem | Driver | Status | Notes |
|---|---|---|---|
| GPU | Adreno 506 → freedreno (MSM DRM) | ✅ Mainline | `CONFIG_DRM_MSM`; Mesa freedreno; full mainline support |
| Display | DSI + IPS LCD panel (MSM DRM) | ✅ Mainline | Framebuffer from lk2nd; panel timing TBD from device |
| Backlight | TI LM3697 | ✅ Mainline | `CONFIG_BACKLIGHT_TI_LM3697`; I2C i2c_5 @ 0x36 |
| Touch | Ilitek ILI2117 (`ili210x`) | ✅ Mainline | `CONFIG_TOUCHSCREEN_ILI210X`; i2c_3 @ 0x41; inverted-x; verify on device |
| WiFi | WCN3680B (`wcn36xx` + `CONFIG_QCOM_WCNSS_PIL`) | 🚧 Needs firmware | Base driver mainline; WCNSS firmware from device |
| Bluetooth | WCN3680B BT 4.2 (`hci_qca`) | 🚧 Needs firmware | `CONFIG_BT_HCIUART_QCA`; BT firmware from device |
| Modem | Snapdragon X9 LTE | ❌ Not MM-ready | No upstream MM plugin for X9 LTE on msm8953; Phase-7 stretch |
| Audio | WCD9335 cajon-v2 (ASoC) | 🚧 Downstream | `CONFIG_SND_SOC_WCD9335`; UCM from msm8953-mainline/alsa-ucm-conf |
| Sensors | BMI160, MMC3630KJ, TMD2725 | 🚧 Partially mainline | BMI160 mainline; MMC3630KJ + TMD2725 need check |
| NFC | None (most variants) | ✅ N/A | Verify `ls /sys/class/nfc/` on physical device |
| USB | dwc3 | ✅ Mainline | Standard dwc3; fastboot gadget works |
| eMMC | `mmc_core` | ✅ Mainline | Standard eMMC; `/dev/block/bootdevice/by-name/` |
| Power | Qualcomm PM8953 PMIC | 🚧 Partial mainline | RPM regulator + spmi; some power domains mainline |
| Battery/charging | QC 3.0 TurboPower | 🚧 Partial | qcom-smbb / smbchg driver |

**The G7 Power has the best mainline support of all three Nuxel targets.** The
GPU (freedreno), display (MSM DRM), touch (ILI2117), and backlight (LM3697) are
all upstream. WiFi/BT need firmware but the drivers are mainline. This is a
genuinely achievable Phase-1 target.

---

## TASKS (implement in this exact order)

---

### TASK 1 — Extend `boot/initramfs/init.sh` for G7 Power A-only eMMC layout

The shared `boot/initramfs/init.sh` currently has a stub for G7 Power that
calls `emergency_shell`. Replace it with a real implementation.

**G7 Power root probe (eMMC A-only):**

```sh
g7power)
    # G7 Power A-only eMMC layout
    # eMMC path: /dev/block/bootdevice/by-name/
    # lk2nd passes the correct cmdline; root= may be explicit or we probe.
    EMMC_BASE="/dev/block/bootdevice/by-name"
    if [ -n "${ROOT_SPEC}" ]; then
        ROOT_DEV="${ROOT_SPEC}"
    elif [ -b "${EMMC_BASE}/userdata" ]; then
        ROOT_DEV="${EMMC_BASE}/userdata"
    elif [ -b "${EMMC_BASE}/system" ]; then
        ROOT_DEV="${EMMC_BASE}/system"
    else
        err "g7power: cannot find root partition under ${EMMC_BASE}"
        err "Available: $(ls ${EMMC_BASE} 2>/dev/null | tr '\n' ' ')"
        emergency_shell
    fi
    log "g7power: root → ${ROOT_DEV} (fstype: ${ROOT_FSTYPE:-ext4})"
    ;;
```

Also confirm that the `s10plus` and `mustang` paths still compile and the
`bash -n` / `shellcheck` pass still holds on the whole `init.sh`.

**Acceptance:** `bash -n boot/initramfs/init.sh` passes; `g7power` case
compiles and correctly resolves eMMC root.

---

### TASK 2 — G7 Power device package (`device/g7power/`)

Replace every stub file with full implementations.

#### `device/g7power/deviceinfo`

```sh
# Nuxel Device Info — postmarketOS format
# Motorola Moto G7 Power (XT1955)
# Codename: ocean

deviceinfo_format_version="2"
deviceinfo_name="Motorola Moto G7 Power"
deviceinfo_manufacturer="Motorola"
deviceinfo_codename="ocean"
deviceinfo_year="2019"
deviceinfo_arch="aarch64"
deviceinfo_chassis="handset"

# SoC
deviceinfo_soc="Qualcomm Snapdragon 632 (SDM632)"
deviceinfo_soc_family="msm8953"
deviceinfo_cpu="4x Kryo 250 Gold (Cortex-A73) + 4x Kryo 250 Silver (Cortex-A53) @ 1.8 GHz (14nm)"

# GPU — Adreno 506 mainline freedreno
deviceinfo_gpu="Qualcomm Adreno 506"
deviceinfo_gpu_driver="freedreno"
deviceinfo_gpu_driver_config="CONFIG_DRM_MSM=y"

# Display — IPS LCD 1520x720
deviceinfo_display="6.2\" IPS LCD 1520x720 19:9"
deviceinfo_screen_width="720"
deviceinfo_screen_height="1520"
deviceinfo_screen_refresh_rate="60"
deviceinfo_display_ddic="UNKNOWN — collect LCM name from real device (stock vendor tree)"
deviceinfo_backlight="TI LM3697"
deviceinfo_backlight_i2c_bus="i2c_5"
deviceinfo_backlight_i2c_addr="0x36"

# Touch — Ilitek ILI2117 (mainline)
deviceinfo_touchscreen="Ilitek ILI2117"
deviceinfo_touchscreen_driver="ili210x"
deviceinfo_touchscreen_i2c_bus="i2c_3"
deviceinfo_touchscreen_i2c_addr="0x41"
deviceinfo_touchscreen_irq="tlmm 65"
deviceinfo_touchscreen_inverted_x="true"
deviceinfo_touchscreen_note="ILI2117 in mainline sdm632-motorola-ocean.dts. Some units may boot with no touch — verify on device."

# WiFi / BT — WCN3680B (wcn36xx, NOT ath10k)
deviceinfo_wifi="Qualcomm WCN3680B (802.11 b/g/n, 2.4 GHz)"
deviceinfo_wifi_driver="wcn36xx"
deviceinfo_wifi_note="CONFIG_QCOM_WCNSS_PIL required. NOT ath10k. b/g/n 2.4 GHz only."

deviceinfo_bluetooth="4.2 (WCN3680B)"
deviceinfo_bluetooth_driver="hci_qca"

# Modem — X9 LTE, NOT MM-ready in Phase 1
deviceinfo_modem="Qualcomm Snapdragon X9 LTE (integrated, SDM632, no 5G)"
deviceinfo_modem_driver="NOT_MM_READY"
deviceinfo_modem_note="No upstream ModemManager plugin for X9 LTE on msm8953. Phase 1: WiFi only."

# NFC
deviceinfo_nfc="none (most ocean variants — verify on physical device)"

# Storage — eMMC
deviceinfo_storage="eMMC (32 or 64 GB) + microSD"
deviceinfo_storage_driver="mmc_core"
deviceinfo_storage_path="/dev/block/bootdevice/by-name"
deviceinfo_storage_filesystem="ext4"

# Memory
deviceinfo_ram="3 or 4 GB LPDDR3 (variant-dependent)"

# Battery
deviceinfo_battery="5000 mAh"
deviceinfo_battery_charging="15W TurboPower (Qualcomm QC 3.0)"

# Audio
deviceinfo_audio_codec="Qualcomm WCD9335 (cajon-v2)"
deviceinfo_audio_driver="wcd9335"

# Sensors (verified from pmOS wiki XT1955-5)
deviceinfo_sensor_accel_gyro="Bosch BMI160"
deviceinfo_sensor_mag="MEMSIC MMC3630KJ"
deviceinfo_sensor_prox_als="AMS TMD2725"
deviceinfo_sensor_fingerprint="UNKNOWN — rear-mounted, collect from real device"

# Camera — UNKNOWN; collect from real device
deviceinfo_camera_front="UNKNOWN — collect from real device"
deviceinfo_camera_rear="UNKNOWN — collect from real device"

# Boot configuration
deviceinfo_boot_header_version="1"
deviceinfo_boot_page_size="2048"
deviceinfo_boot_slots="none"
deviceinfo_boot_note="A-only. Stock ABOOT -> lk2nd (msm8916-mainline/lk2nd, msm8953 target) -> mainline Linux via EFI. dtbo MUST be flashed before lk2nd."

# Flash
deviceinfo_flash_method="fastboot"
deviceinfo_flash_note="fastboot (stock ABOOT + lk2nd). EDL (Qualcomm 9008) for unbrick. Unlock via fastboot oem get_unlock_data -> Motorola portal."

# Kernel
deviceinfo_kernel="linux-postmarketos-qcom-msm8953"
deviceinfo_kernel_source="https://github.com/msm8953-mainline/linux"
deviceinfo_kernel_cmdline="console=ttyMSM0,115200 earlycon=msm_geni_serial,0xa88000 nuxel.device=g7power root=PLACEHOLDER_fill_from_device rootfstype=ext4 rootwait rw"
```

#### `device/g7power/APKBUILD`

Create a postmarketOS-format APKBUILD stub for `device-motorola-ocean`.
Exact values from the hardware table above. Include:
- `pkgname=device-motorola-ocean`
- `_pmb_kernel="linux-postmarketos-qcom-msm8953"`
- `_pmb_dtb="qcom/sdm632-motorola-ocean.dtb"` (verify DTB path in kernel tree)
- `depends` covering `linux-postmarketos-qcom-msm8953`, `firmware-motorola-ocean` (stub),
  `lk2nd-msm8953` (stub)
- `install_kernel()` function that documents the two-phase lk2nd flash sequence
- Mark camera/fingerprint/exact DDIC as `UNKNOWN`

#### `device/g7power/90-nuxel-ocean.rules`

Udev rules for the G7 Power:
```
# Ilitek ILI2117 touch (mainline ili210x driver)
SUBSYSTEM=="input", ATTRS{name}=="ILI210x Touchscreen", TAG+="nuxel-touch"

# TI LM3697 backlight
SUBSYSTEM=="backlight", KERNEL=="lm3697*", TAG+="nuxel-backlight"

# Adreno 506 / freedreno DRM
SUBSYSTEM=="drm", KERNEL=="card*", ATTRS{driver}=="msm", TAG+="nuxel-gpu"

# WCN3680B WiFi (wcn36xx)
SUBSYSTEM=="net", KERNEL=="wlan*", DRIVERS=="wcn36xx", TAG+="nuxel-wifi"

# WCN3680B BT (hci_qca)
SUBSYSTEM=="bluetooth", KERNEL=="hci*", TAG+="nuxel-bluetooth"

# eMMC block device
SUBSYSTEM=="block", KERNEL=="mmcblk0*", TAG+="nuxel-storage"

# Camera and fingerprint — UNKNOWN, add after Phase 0 inventory
# SUBSYSTEM=="video4linux", ...  # TBD
```

#### `device/g7power/nuxel-ocean.conf`

```sh
# Nuxel device configuration for Motorola Moto G7 Power (ocean)
# Fill all UNKNOWN values from real device via Phase 0 inventory (docs/g7power-device-inventory.md)

NUXEL_DEVICE=g7power
NUXEL_CODENAME=ocean
NUXEL_EMMC_PATH=/dev/block/bootdevice/by-name
NUXEL_DISPLAY_RESOLUTION=1520x720
NUXEL_DISPLAY_ORIENTATION=normal

# Touch — ILI2117 i2c_3 @ 0x41, inverted-x
NUXEL_TOUCH_DRIVER=ili210x
NUXEL_TOUCH_INVERTED_X=true

# WiFi firmware path (wcn36xx / WCNSS PIL)
NUXEL_WIFI_FW_DIR=/lib/firmware/wlan/prima
NUXEL_WIFI_FW_FILE=UNKNOWN  # collect: adb shell ls /vendor/firmware/wlan/prima/
NUXEL_BT_FW_DIR=/lib/firmware/qca
NUXEL_BT_FW_FILE=UNKNOWN    # collect: adb shell ls /vendor/firmware/qca/

# Audio
NUXEL_AUDIO_CODEC=wcd9335
NUXEL_ALSA_UCM_CARD=UNKNOWN  # collect: adb shell cat /proc/asound/cards

# Boot addresses — fill from stock boot.img header
NUXEL_KERNEL_ADDR=PLACEHOLDER
NUXEL_RAMDISK_ADDR=PLACEHOLDER
NUXEL_TAGS_ADDR=PLACEHOLDER

# Protected partitions — NEVER flash
NUXEL_PROTECTED_PARTITIONS="modemst1 modemst2 fsg fsc ddr persist misc"
```

**Acceptance:** All four files exist, parse cleanly with `bash -n` where
applicable, contain only G7 Power / SDM632 / ocean values, and contain zero
mustang or s10plus values.

---

### TASK 3 — G7 Power firmware manifest and extractor (`firmware/g7power/`)

#### `firmware/g7power/manifest.yml`

```yaml
device: g7power
codename: ocean
soc: sdm632
soc_family: msm8953
flash_method: fastboot+lk2nd

# Acquisition: adb pull from device (Android) or TWRP/recovery
# adb pull /vendor/firmware           firmware/g7power/blobs/vendor-firmware/
# adb pull /vendor/firmware_mnt       firmware/g7power/blobs/vendor-firmware-mnt/
# adb pull /vendor/lib/modules        firmware/g7power/blobs/vendor-modules/

firmware_files:
  gpu_adreno:
    - source_path: "vendor/firmware/a506_zap.mbn"
      dest: "/lib/firmware/qcom/a506_zap.mbn"
      description: "Adreno 506 GPU security firmware (zap shader; freedreno requires it)"
      required: true
      checksum: "UNKNOWN — collect from device"
    - source_path: "vendor/firmware/a506*.elf"
      dest: "/lib/firmware/qcom/"
      description: "Adreno 506 microcode ELF (if present)"
      required: false
      checksum: "UNKNOWN"

  wifi_bt:
    # WCN3680B WiFi via wcn36xx + WCNSS_PIL
    # Firmware path varies: /vendor/firmware/wlan/prima/ or /vendor/firmware/
    - source_path: "vendor/firmware/wlan/prima/WCNSS_qcom_cfg.ini"
      dest: "/lib/firmware/wlan/prima/WCNSS_qcom_cfg.ini"
      description: "WCNSS WiFi configuration (wcn36xx)"
      required: true
      checksum: "UNKNOWN — collect from device"
    - source_path: "vendor/firmware/wlan/prima/WCNSS_qcom_wlan_nv.bin"
      dest: "/lib/firmware/wlan/prima/WCNSS_qcom_wlan_nv.bin"
      description: "WCNSS NVRAM calibration blob"
      required: true
      checksum: "UNKNOWN"
    - source_path: "vendor/firmware/WCNSS_*.img"
      dest: "/lib/firmware/"
      description: "WCNSS firmware images (PIL segments — filenames vary)"
      required: true
      checksum: "UNKNOWN — verify filenames via: adb shell ls /vendor/firmware/WCNSS*"
    - source_path: "vendor/firmware/wlan_mac.bin"
      dest: "/lib/firmware/wlan_mac.bin"
      description: "WiFi MAC address file"
      required: false
      checksum: "UNKNOWN"
    # Bluetooth HCI firmware via hci_qca
    - source_path: "vendor/firmware/qca/UNKNOWN_BT_FW.bin"
      dest: "/lib/firmware/qca/"
      description: "WCN3680B Bluetooth firmware (hci_qca) — filename TBD from device"
      required: true
      checksum: "UNKNOWN — collect: adb shell ls /vendor/firmware/qca/"

  audio:
    # WCD9335 cajon-v2 codec
    - source_path: "vendor/firmware/wcd9335*"
      dest: "/lib/firmware/"
      description: "WCD9335 codec firmware blobs"
      required: false
      checksum: "UNKNOWN"
    - source_path: "vendor/etc/firmware/wcd9335*"
      dest: "/lib/firmware/"
      description: "WCD9335 codec firmware (etc/firmware path)"
      required: false
      checksum: "UNKNOWN"

  display:
    - source_path: "UNKNOWN — collect LCM firmware from vendor tree"
      dest: "UNKNOWN"
      description: "LCD panel init firmware (LCM; DDIC name unknown; framebuffer passed from lk2nd)"
      required: false
      checksum: "UNKNOWN"

  touch:
    - source_path: "UNKNOWN — ILI2117 uses mainline driver; firmware may not be needed"
      dest: "UNKNOWN"
      description: "ILI2117 touch firmware (if required by driver; likely not needed)"
      required: false
      checksum: "UNKNOWN"

  sensors:
    - source_path: "UNKNOWN — BMI160, MMC3630KJ, TMD2725 are mainline IIO drivers"
      dest: "UNKNOWN"
      description: "Sensor firmware (likely not needed for mainline drivers)"
      required: false
      checksum: "UNKNOWN"

  camera:
    - source_path: "UNKNOWN — collect ISP/sensor firmware from real device"
      dest: "UNKNOWN"
      description: "Camera ISP firmware (Phase 7 stretch)"
      required: false
      checksum: "UNKNOWN"

  modem:
    # CRITICAL: Do NOT flash modemst1/modemst2/fsg/fsc from here.
    # X9 LTE modem on SDM632 is not MM-ready. Phase 1: WiFi only.
    - source_path: "PLACEHOLDER — X9 LTE modem firmware path TBD"
      dest: "DO NOT INSTALL — modem bring-up is Phase 7"
      description: "Snapdragon X9 LTE modem firmware — NOT for Phase 1"
      required: false
      checksum: "UNKNOWN"

  fingerprint:
    - source_path: "UNKNOWN — collect from real device; rear-mounted sensor TBD"
      dest: "UNKNOWN"
      description: "Fingerprint sensor firmware (Phase 6+)"
      required: false
      checksum: "UNKNOWN"
```

#### `firmware/g7power/install-firmware.sh`

Implement with all modes mirroring the S10+ pattern:
- `--list-files` — Print manifest; do not install anything.
- `--verify-only` — Check each installed blob against sha256. Report `pending`
  for blobs still with `UNKNOWN` checksums.
- `--checksums` — Print sha256 of every blob under `blobs/`.
- `--adb-pull` — Pull vendor firmware from connected device via ADB:
  ```sh
  ADB_DEVICE=$(adb get-serialno 2>/dev/null | tr -d '\r')
  DEVICE_PROP=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')
  [ "${DEVICE_PROP}" = "ocean" ] || {
      echo "ERROR: Expected 'ocean', got '${DEVICE_PROP}'"; exit 1
  }
  adb pull /vendor/firmware       firmware/g7power/blobs/vendor-firmware/
  adb pull /vendor/firmware_mnt   firmware/g7power/blobs/vendor-firmware-mnt/
  adb pull /vendor/lib/modules    firmware/g7power/blobs/vendor-modules/
  adb pull /vendor/etc/firmware   firmware/g7power/blobs/vendor-etc-firmware/
  ```
  After pulling, cross-reference against manifest and report found vs. missing.
- `--install` — Copy blobs from `blobs/` to rootfs staging. Refuse until real
  checksums are filled (or `--force-pending` passed).
- Guard: if `NUXEL_DEVICE != g7power`, abort immediately.
- Protected partition guard: print and enforce that `modemst1`, `modemst2`,
  `fsg`, `fsc`, `ddr`, `persist`, `misc` are never listed as firmware targets.

#### `firmware/g7power/verify-firmware.sh`

Mirror the s10plus verify script. Enforce:
- Every `required: true` blob: real sha256 + installed, OR reported pending.
- Advisory for `required: false`.
- Never touch mustang or s10plus manifests.

**Acceptance:** `NUXEL_DEVICE=g7power firmware/g7power/install-firmware.sh --list-files`
runs correctly, reports G7 Power manifest only, never touches mustang or s10plus files.

---

### TASK 4 — G7 Power kernel build wrapper and defconfig (`kernel/g7power/`)

#### `kernel/g7power/defconfig`

An **msm8953 / SDM632 / linux-postmarketos-qcom-msm8953 Kconfig fragment**.
Must NOT include any mustang (gs501), s10plus (exynos9820), Pixel, Samsung,
PowerVR, BCM4390, BCM4375, or GKI 6.12-specific symbols.

```kconfig
# =============================================================================
# Nuxel msm8953/SDM632 defconfig fragment for Motorola Moto G7 Power (ocean)
# Applied on top of linux-postmarketos-qcom-msm8953 base config
# Kernel source: https://github.com/msm8953-mainline/linux
# =============================================================================

# GPU — Adreno 506, mainline freedreno
CONFIG_DRM=y
CONFIG_DRM_MSM=y
CONFIG_DRM_MSM_GPU_STATE=y
# CONFIG_DRM_PANFROST is not set   # Mali only; not on SDM632
# CONFIG_DRM_POWERVR is not set    # Imagination only; not on SDM632

# Display — MSM DSI (mainline)
CONFIG_DRM_PANEL_SIMPLE=y          # may be needed for IPS LCD panel
# Backlight — TI LM3697
CONFIG_BACKLIGHT_TI_LM3697=y       # mainline; I2C i2c_5 @ 0x36

# Touch — Ilitek ILI2117 (mainline)
CONFIG_TOUCHSCREEN_ILI210X=y       # mainline; I2C i2c_3 @ 0x41; inverted-x
# Not needed (wrong chips for this device):
# CONFIG_TOUCHSCREEN_SAMSUNG_SEC_TS is not set   # S10+ touch only
# CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791 is not set  # mustang touch only

# WiFi — WCN3680B via wcn36xx (NOT ath10k; NOT brcmfmac)
CONFIG_WCN36XX=y
CONFIG_QCOM_WCNSS_PIL=y
CONFIG_WCNSS_CORE=y
# CONFIG_ATH10K is not set         # NOT the right driver for WCN3680B
# CONFIG_BRCMFMAC is not set       # Broadcom only; not on SDM632

# Bluetooth — WCN3680B via hci_qca
CONFIG_BT=y
CONFIG_BT_HCIUART=y
CONFIG_BT_HCIUART_QCA=y
# CONFIG_BT_HCIUART_BCM is not set # Broadcom only; not on SDM632

# Audio — WCD9335 cajon-v2 ASoC
CONFIG_SND=y
CONFIG_SND_SOC=y
CONFIG_SND_SOC_WCD9335=y          # WCD9335 cajon-v2
CONFIG_SND_SOC_MSM8916_WCD_IRCODEC=y  # verify availability in msm8953 tree
CONFIG_SND_SOC_QCOM=y
# CONFIG_SND_SOC_CS47L93 is not set   # S10+ audio only
# CONFIG_SND_SOC_CS42L43 is not set   # mustang audio only

# Sensors (mainline IIO)
CONFIG_IIO=y
CONFIG_BMI160_I2C=y                # Bosch BMI160 accel+gyro (mainline)
CONFIG_BMI160_SPI=n
# MMC3630KJ magnetometer — verify driver name in msm8953 tree
# CONFIG_MMC35240 or CONFIG_IIO_MMC3630KJ — TBD from kernel tree
# TMD2725 prox+ALS — verify driver name in msm8953 tree
# CONFIG_APDS9960 or CONFIG_TMD2725 — TBD from kernel tree

# Storage — eMMC
CONFIG_MMC=y
CONFIG_MMC_BLOCK=y
CONFIG_MMC_SDHCI=y
CONFIG_MMC_SDHCI_MSM=y

# Filesystems
CONFIG_EXT4_FS=y
CONFIG_F2FS_FS=y
CONFIG_VFAT_FS=y                   # microSD

# USB — dwc3 (fastboot gadget)
CONFIG_USB_DWC3=y
CONFIG_USB_DWC3_QCOM=y
CONFIG_USB_GADGET=y
CONFIG_USB_CONFIGFS=y

# Device nodes
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y

# Qualcomm IPC / RPM
CONFIG_QCOM_SMD=y
CONFIG_QCOM_SMEM=y
CONFIG_RPMSG=y
CONFIG_RPMSG_QCOM_SMD=y
CONFIG_QCOM_COMMAND_DB=y
CONFIG_QCOM_RPM=y

# Security — where supported by msm8953 tree
CONFIG_SECURITY=y
CONFIG_SECURITY_APPARMOR=y
CONFIG_SECCOMP=y
CONFIG_USER_NS=y
CONFIG_NET_NS=y
CONFIG_PID_NS=y
CONFIG_IPC_NS=y
CONFIG_UTS_NS=y
CONFIG_NAMESPACES=y

# Nuxel phone features (conditional; only if patch applies to msm8953 tree)
# CONFIG_NUXEL=y       # apply only if 0001-nuxel-phone-features.patch compiles clean
# CONFIG_NUXEL_PHONE=y
# CONFIG_NUXEL_BOOT_PARAM=y

# --- Symbols explicitly NOT present in linux-postmarketos-qcom-msm8953 ---
# CONFIG_DRM_POWERVR      — mustang PowerVR GPU; not in msm8953 tree
# CONFIG_DRM_PANFROST     — S10+ Mali GPU; not on SDM632
# CONFIG_DRM_PANEL_SAMSUNG_AMB655X  — mustang display
# CONFIG_DRM_PANEL_SAMSUNG_S6E3HA9  — S10+ display
# CONFIG_BRCMFMAC         — Broadcom WiFi; not on SDM632
# CONFIG_MFD_MADERA       — S10+ audio; not on SDM632
# CONFIG_SND_SOC_CS47L93  — S10+ codec
# CONFIG_SND_SOC_CS35L40  — S10+ amp
# CONFIG_SCSI_UFSHCD      — UFS; G7 Power uses eMMC, not UFS
# CONFIG_MHI_BUS_PCI_GENERIC — mustang modem; not on msm8953
```

#### `kernel/g7power/build-kernel.sh`

```bash
#!/usr/bin/env bash
# =============================================================================
# Nuxel G7 Power Kernel Build Wrapper — linux-postmarketos-qcom-msm8953
# Device: Motorola Moto G7 Power (XT1955), codename ocean
# Kernel: msm8953-mainline/linux (close-to-mainline Snapdragon 632 / SDM632)
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEVICE_KEY="g7power"
KOUT="${NUXEL_ROOT}/kernel/g7power/.build/out"
KSRC="${NUXEL_ROOT}/kernel/g7power/.build/src"
PATCHES="${NUXEL_ROOT}/kernel/g7power/patches"
DEFCONFIG="${NUXEL_ROOT}/kernel/g7power/defconfig"

CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"
JOBS="${JOBS:-$(nproc)}"

MSM8953_KERNEL_REPO="https://github.com/msm8953-mainline/linux"
MSM8953_KERNEL_BRANCH="master"

echo "[nuxel-g7power-kernel] Device:    ${DEVICE_KEY} (ocean, SDM632/msm8953)"
echo "[nuxel-g7power-kernel] Kernel:    linux-postmarketos-qcom-msm8953 (msm8953-mainline/linux)"
echo "[nuxel-g7power-kernel] Cross:     ${CROSS_COMPILE}"
echo "[nuxel-g7power-kernel] Output:    ${KOUT}"

DO_CLONE=0; DO_BUILD=1; DO_CLEAN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)  grep '^#' "$0" | head -12; exit 0 ;;
        --clone)    DO_CLONE=1; shift ;;
        --clean)    DO_CLEAN=1; shift ;;
        --jobs)     JOBS="$2"; shift 2 ;;
        --cross)    CROSS_COMPILE="$2"; shift 2 ;;
        *)          echo "Unknown: $1"; exit 1 ;;
    esac
done

mkdir -p "${KOUT}" "${KSRC}"

if [[ $DO_CLONE -eq 1 ]] || [[ ! -d "${KSRC}/.git" ]]; then
    echo "[kernel] Cloning msm8953-mainline/linux..."
    git clone --depth=1 -b "${MSM8953_KERNEL_BRANCH}" \
        "${MSM8953_KERNEL_REPO}" "${KSRC}" || {
        echo "[kernel] ERROR: Clone failed. Check network access."
        echo "[kernel] Repo: ${MSM8953_KERNEL_REPO}"
        exit 1
    }
fi

if [[ $DO_CLEAN -eq 1 ]]; then
    make -C "${KSRC}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" mrproper
fi

echo "[kernel] Applying Nuxel patches..."
for patch in "${PATCHES}"/*.patch; do
    [[ -f "$patch" ]] || continue
    echo "[kernel] Applying: $(basename "$patch")"
    git -C "${KSRC}" apply "$patch" 2>/dev/null || {
        echo "[kernel] WARN: Patch $(basename "$patch") did not apply cleanly."
        echo "[kernel] See ${PATCHES}/$(basename "$patch" .patch).README"
    }
done

echo "[kernel] Configuring (msm8953_defconfig + Nuxel fragment)..."
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" msm8953_defconfig 2>/dev/null || \
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" defconfig
"${KSRC}/scripts/kconfig/merge_config.sh" -m \
    "${KOUT}/.config" "${DEFCONFIG}"
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" olddefconfig

echo "[kernel] Building Image.gz + DTBs (jobs=${JOBS})..."
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" -j"${JOBS}" Image.gz dtbs modules

# Install modules into a staging dir
MODULES_STAGING="${NUXEL_ROOT}/kernel/g7power/.build/modules-staging"
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" INSTALL_MOD_PATH="${MODULES_STAGING}" modules_install

echo ""
echo "[kernel] Done."
echo "[kernel] Image.gz:  ${KOUT}/arch/arm64/boot/Image.gz"
echo "[kernel] DTBs:      ${KOUT}/arch/arm64/boot/dts/qcom/"
echo "[kernel] DTB:       ${KOUT}/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb"
echo "[kernel] Modules:   ${MODULES_STAGING}/lib/modules/"
ls -lh "${KOUT}/arch/arm64/boot/Image.gz" 2>/dev/null || \
    echo "[kernel] WARN: Image.gz not found — build may have failed."
ls "${KOUT}/arch/arm64/boot/dts/qcom/" 2>/dev/null | grep ocean || \
    echo "[kernel] WARN: ocean DTB not found — check DTS availability in tree."
```

#### `kernel/g7power/patches/README.md`

Document:
- Port status of Nuxel `0001-nuxel-phone-features.patch` to the msm8953 tree.
  Apply `git apply --check` and note which hunks pass/fail.
- The msm8953-mainline kernel already has mainline ILI2117, freedreno, wcn36xx,
  BMI160 — Nuxel patches are primarily the `drivers/nuxel/` boot param and
  phone feature additions.
- If any hunk fails: create `0001-nuxel-phone-features.patch.TODO` with the
  unported sections and a comment explaining what upstream symbol is missing.

#### `kernel/g7power/README-toolchain.md`

Document:
- Toolchain: `aarch64-linux-gnu-` (GCC 10+) or LLVM clang with aarch64 target
- Install (Debian/Ubuntu): `sudo apt install gcc-aarch64-linux-gnu bc bison flex libssl-dev libelf-dev`
- macOS: `brew tap messense/macos-cross-toolchains && brew install aarch64-unknown-linux-gnu`
- Kernel source: `https://github.com/msm8953-mainline/linux`
- DTB name to expect: `arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb`
- Note that SDM632 = msm8953 family; the defconfig may be named `msm8953_defconfig` or variant

**Acceptance:** `NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --help`
prints G7 Power / SDM632 context. A full `--clone` + build with network + toolchain
produces `Image.gz` + `sdm632-motorola-ocean.dtb`, never touching
`kernel/google-pixel-10-pro-xl/` or `kernel/s10plus/`.

---

### TASK 5 — Boot image packer, lk2nd chainload, flash/recovery scripts (`boot/g7power/`)

#### `boot/g7power/pack-boot-v1.sh`

Implement (or symlink/adapt from `boot/s10plus/pack-boot-v1.sh` if the
implementation is sufficiently general) a legacy Android boot image header v1
packer. G7 Power specific defaults:

```
# G7 Power boot image v1 load addresses
# (VERIFY ALL from real device stock boot.img — use tools/read-boot-header-v1.py)
page_size=2048
kernel_addr=PLACEHOLDER_0x80008000   # typical for msm8953; VERIFY
ramdisk_addr=PLACEHOLDER_0x81000000  # typical for msm8953; VERIFY
tags_addr=PLACEHOLDER_0x80000100     # typical; VERIFY
name="nuxel-g7power"
```

Include an `--addresses-from-device` mode that reads a stock `boot.img` and
extracts the addresses automatically. Usage:

```
boot/g7power/pack-boot-v1.sh \
    --kernel kernel/g7power/.build/out/arch/arm64/boot/Image.gz \
    --ramdisk boot/initramfs/initramfs.cpio.gz \
    --dtb kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb \
    --cmdline "console=ttyMSM0,115200 earlycon=msm_geni_serial,0xa88000 nuxel.device=g7power root=/dev/block/bootdevice/by-name/userdata rootfstype=ext4 rootwait rw" \
    --output /tmp/nuxel-ocean-boot.img
```

#### `boot/g7power/lk2nd/README.md`

Document the lk2nd build process for msm8953:

```markdown
# lk2nd — Mainline Qualcomm Bootloader for Moto G7 Power (msm8953)

## Source
https://github.com/msm8916-mainline/lk2nd (branch: master)
Target: msm8953 (used by ocean/SDM632)

## Build
git clone https://github.com/msm8916-mainline/lk2nd
cd lk2nd
make TOOLCHAIN_PREFIX=arm-none-eabi- msm8953 -j$(nproc)
# Output: build-msm8953/lk2nd.img

## Flash (Phase 1: Stock ABOOT fastboot mode)
# 1. Flash dtbo FIRST (MANDATORY — see dtbo-first rule)
fastboot flash dtbo /path/to/stock-dtbo.img    # use backed-up stock dtbo
# 2. Flash lk2nd to the boot partition
fastboot flash boot build-msm8953/lk2nd.img
# 3. Reboot into lk2nd fastboot
fastboot reboot bootloader
# (Now you are in lk2nd's fastboot, not stock ABOOT)
# 4. Flash mainline kernel boot.img
fastboot flash boot /tmp/nuxel-ocean-boot.img
# 5. Flash rootfs
fastboot flash userdata /path/to/nuxel-ocean-rootfs.img
# 6. Reboot
fastboot reboot

## Recovery / Revert
# If the device does not boot after flashing lk2nd:
# Enter stock ABOOT fastboot (Vol Down + Power from off)
fastboot flash dtbo  /path/to/stock-dtbo-backup.img
fastboot flash boot  /path/to/stock-boot-backup.img
fastboot reboot

## EDL (Qualcomm 9008) Unbrick Path
# If fastboot is inaccessible (hard brick):
# Power off, hold Vol Down + Vol Up, plug USB
# Host should detect: Qualcomm HS-USB QDLoader 9008 (VID:05C6, PID:9008)
# Use edl tool (bkerler/edl) or QFIL (Windows) to flash stock partitions
```

#### `boot/g7power/flash.sh`

Full implementation:

```bash
#!/usr/bin/env bash
# =============================================================================
# Nuxel Flash Script — Motorola Moto G7 Power (ocean, SDM632 / msm8953)
# Flash method: fastboot (stock ABOOT) + lk2nd + EDL 9008 (unbrick)
#
# !!! CRITICAL FLASH ORDER — NEVER CHANGE THIS !!!
# 1. flash dtbo (MANDATORY FIRST — prevents soft-brick)
# 2. flash boot with lk2nd.img (via stock ABOOT fastboot)
# 3. reboot into lk2nd fastboot
# 4. flash boot with mainline Nuxel boot.img (via lk2nd fastboot)
# 5. flash userdata with rootfs
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

PROTECTED_PARTITIONS="modemst1 modemst2 fsg fsc ddr persist misc"
DEVICE_EXPECTED="ocean"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Args
DEVICE_KEY=""
LK2ND_IMG=""
BOOT_IMG=""
DTBO_IMG=""
ROOTFS_IMG=""
ROOTFS_PARTITION="userdata"
DO_UNLOCK_HELP=0
DO_REVERT=0
STOCK_BOOT_IMG=""
STOCK_DTBO_IMG=""
DRY_RUN=0
FORCE=0
SKIP_DTBO=0

usage() {
    cat <<EOF
Usage: $0 --device g7power [options]

CRITICAL FLASH ORDER (enforced in code):
  1. --dtbo  must be flashed BEFORE --lk2nd (prevents soft-brick on msm8953)
  2. --lk2nd flash is via STOCK ABOOT fastboot
  3. --boot  flash is via LK2ND fastboot (after reboot)
  4. --rootfs flash is via LK2ND fastboot

Options:
  --device g7power         REQUIRED. Refuses on any other value.
  --dtbo  <path>           Path to dtbo.img (flashed FIRST, via stock ABOOT fastboot)
  --lk2nd <path>           Path to lk2nd.img (flashed to boot partition, stock ABOOT)
  --boot  <path>           Path to Nuxel boot.img (flashed via lk2nd fastboot)
  --rootfs <path>          Path to Nuxel rootfs image
  --rootfs-partition <n>   Target partition (default: userdata)
  --unlock-help            Print Motorola unlock portal instructions
  --revert                 Re-flash stock boot + dtbo (reverts lk2nd + Nuxel)
  --stock-boot <path>      Stock boot.img for --revert
  --stock-dtbo <path>      Stock dtbo.img for --revert (REQUIRED with --revert)
  --edl                    Print EDL (Qualcomm 9008) unbrick instructions
  --dry-run                Print commands but do not execute
  --force                  Skip confirmation prompts

NEVER touch: ${PROTECTED_PARTITIONS}
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --device)           DEVICE_KEY="$2"; shift 2 ;;
        --dtbo)             DTBO_IMG="$2"; shift 2 ;;
        --lk2nd)            LK2ND_IMG="$2"; shift 2 ;;
        --boot)             BOOT_IMG="$2"; shift 2 ;;
        --rootfs)           ROOTFS_IMG="$2"; shift 2 ;;
        --rootfs-partition) ROOTFS_PARTITION="$2"; shift 2 ;;
        --unlock-help)      DO_UNLOCK_HELP=1; shift ;;
        --revert)           DO_REVERT=1; shift ;;
        --stock-boot)       STOCK_BOOT_IMG="$2"; shift 2 ;;
        --stock-dtbo)       STOCK_DTBO_IMG="$2"; shift 2 ;;
        --edl)              cat "${NUXEL_ROOT}/boot/g7power/lk2nd/README.md" | grep -A20 "EDL"; exit 0 ;;
        --dry-run)          DRY_RUN=1; shift ;;
        --force)            FORCE=1; shift ;;
        --help|-h)          usage; exit 0 ;;
        *)                  log_error "Unknown: $1"; usage; exit 1 ;;
    esac
done

# Validate device key
[ "${DEVICE_KEY}" = "g7power" ] || {
    log_error "--device g7power required. Got: '${DEVICE_KEY}'"
    log_error "This script is ONLY for the Motorola Moto G7 Power (ocean)."
    exit 1
}

log_info "Nuxel Flash — Motorola Moto G7 Power (ocean, SDM632)"
log_info "Flash method: fastboot (stock ABOOT) + lk2nd + EDL 9008 (unbrick)"

# Unlock help
if [[ $DO_UNLOCK_HELP -eq 1 ]]; then
    cat <<'EOF'
=== Motorola Bootloader Unlock Instructions ===

1. Enable USB debugging and OEM Unlock in Developer Options.
2. Reboot to fastboot: adb reboot bootloader
3. Get unlock data:
   fastboot oem get_unlock_data
   (copies a string to the terminal — save it)
4. Submit unlock request:
   https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device
   Paste the unlock data, submit, wait for the email with your unlock code.
5. Unlock (WIPES DEVICE — BACKUP FIRST):
   fastboot oem unlock <YOUR_UNLOCK_CODE>
6. Reboot and re-enable USB debugging.
EOF
    exit 0
fi

# Verify device identity
log_info "Checking connected device..."
if ! fastboot devices | grep -q "."; then
    log_error "No fastboot device found. Is the G7 Power in fastboot mode?"
    log_error "Enter fastboot: power off, then hold Vol Down + Power."
    exit 1
fi

PRODUCT=$(fastboot getvar product 2>&1 | grep '^product:' | awk '{print $2}' | tr -d '\r')
SERIAL=$(fastboot getvar serialno 2>&1 | grep '^serialno:' | awk '{print $2}' | tr -d '\r')
UNLOCKED=$(fastboot getvar unlocked 2>&1 | grep '^unlocked:' | awk '{print $2}' | tr -d '\r')

log_info "Product: ${PRODUCT} | Serial: ${SERIAL} | Unlocked: ${UNLOCKED}"

[ "${PRODUCT}" = "${DEVICE_EXPECTED}" ] || {
    log_error "Device mismatch: expected '${DEVICE_EXPECTED}', got '${PRODUCT}'"
    log_error "REFUSING TO FLASH. Connect the correct G7 Power (ocean)."
    exit 1
}
[ "${UNLOCKED}" = "yes" ] || {
    log_error "Bootloader is LOCKED. Run: bash boot/g7power/flash.sh --unlock-help"
    exit 1
}
log_ok "Device verified: ${PRODUCT} (${SERIAL}), unlocked: ${UNLOCKED}"

# Protected partition validation
for p in ${PROTECTED_PARTITIONS}; do
    [ "${ROOTFS_PARTITION}" = "${p}" ] && {
        log_error "ROOTFS_PARTITION='${p}' is protected. Refusing."
        exit 1
    }
done

# Revert mode
if [[ $DO_REVERT -eq 1 ]]; then
    log_warn "REVERT MODE: Re-flashing stock dtbo + boot (removes lk2nd + Nuxel kernel)"
    [ -n "${STOCK_DTBO_IMG}" ] || { log_error "--stock-dtbo required for --revert"; exit 1; }
    [ -n "${STOCK_BOOT_IMG}" ] || { log_error "--stock-boot required for --revert"; exit 1; }
    [ -f "${STOCK_DTBO_IMG}" ] || { log_error "dtbo not found: ${STOCK_DTBO_IMG}"; exit 1; }
    [ -f "${STOCK_BOOT_IMG}" ] || { log_error "boot not found: ${STOCK_BOOT_IMG}"; exit 1; }

    log_info "Flashing stock dtbo first..."
    [[ $DRY_RUN -eq 0 ]] && fastboot flash dtbo "${STOCK_DTBO_IMG}" || \
        log_info "[dry-run] fastboot flash dtbo ${STOCK_DTBO_IMG}"
    log_info "Flashing stock boot..."
    [[ $DRY_RUN -eq 0 ]] && fastboot flash boot "${STOCK_BOOT_IMG}" || \
        log_info "[dry-run] fastboot flash boot ${STOCK_BOOT_IMG}"
    [[ $DRY_RUN -eq 0 ]] && fastboot reboot || log_info "[dry-run] fastboot reboot"
    log_ok "Revert complete."
    exit 0
fi

# === PHASE 1: Stock ABOOT fastboot — flash dtbo + lk2nd ===
if [[ -n "${DTBO_IMG}" ]] || [[ -n "${LK2ND_IMG}" ]]; then
    log_info "=== PHASE 1: Stock ABOOT fastboot (dtbo + lk2nd) ==="

    # STEP 1 — dtbo MUST come before lk2nd (enforced in code)
    if [[ -n "${DTBO_IMG}" ]]; then
        [ -f "${DTBO_IMG}" ] || { log_error "dtbo not found: ${DTBO_IMG}"; exit 1; }
        log_warn "Flashing dtbo FIRST (mandatory on msm8953)..."
        [[ $FORCE -eq 0 ]] && read -rp "Flash dtbo? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
        [[ $DRY_RUN -eq 0 ]] && fastboot flash dtbo "${DTBO_IMG}" || \
            log_info "[dry-run] fastboot flash dtbo ${DTBO_IMG}"
        log_ok "dtbo flashed."
    else
        log_warn "No --dtbo specified. ENSURE dtbo is intact before flashing lk2nd!"
    fi

    # STEP 2 — lk2nd to boot partition (via stock ABOOT fastboot)
    if [[ -n "${LK2ND_IMG}" ]]; then
        [ -f "${LK2ND_IMG}" ] || { log_error "lk2nd not found: ${LK2ND_IMG}"; exit 1; }
        log_info "Flashing lk2nd to boot partition (stock ABOOT fastboot)..."
        [[ $FORCE -eq 0 ]] && read -rp "Flash lk2nd to /boot? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
        [[ $DRY_RUN -eq 0 ]] && fastboot flash boot "${LK2ND_IMG}" || \
            log_info "[dry-run] fastboot flash boot ${LK2ND_IMG}"
        log_ok "lk2nd flashed."

        log_info "Rebooting into lk2nd fastboot..."
        [[ $DRY_RUN -eq 0 ]] && fastboot reboot bootloader || \
            log_info "[dry-run] fastboot reboot bootloader"
        log_info "Waiting for lk2nd fastboot to appear (10s)..."
        sleep 10
        log_info "Now in lk2nd fastboot. Proceeding to Phase 2..."
    fi
fi

# === PHASE 2: lk2nd fastboot — flash mainline kernel boot.img + rootfs ===
if [[ -n "${BOOT_IMG}" ]] || [[ -n "${ROOTFS_IMG}" ]]; then
    log_info "=== PHASE 2: lk2nd fastboot (Nuxel boot.img + rootfs) ==="

    if [[ -n "${BOOT_IMG}" ]]; then
        [ -f "${BOOT_IMG}" ] || { log_error "boot.img not found: ${BOOT_IMG}"; exit 1; }
        log_info "Flashing Nuxel boot.img via lk2nd fastboot..."
        [[ $FORCE -eq 0 ]] && read -rp "Flash Nuxel boot.img? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
        [[ $DRY_RUN -eq 0 ]] && fastboot flash boot "${BOOT_IMG}" || \
            log_info "[dry-run] fastboot flash boot ${BOOT_IMG}"
        log_ok "Nuxel boot.img flashed."
    fi

    if [[ -n "${ROOTFS_IMG}" ]]; then
        [ -f "${ROOTFS_IMG}" ] || { log_error "rootfs not found: ${ROOTFS_IMG}"; exit 1; }
        log_warn "Flashing rootfs to /${ROOTFS_PARTITION} — this OVERWRITES existing data."
        [[ $FORCE -eq 0 ]] && read -rp "Flash rootfs to /${ROOTFS_PARTITION}? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
        [[ $DRY_RUN -eq 0 ]] && fastboot flash "${ROOTFS_PARTITION}" "${ROOTFS_IMG}" || \
            log_info "[dry-run] fastboot flash ${ROOTFS_PARTITION} ${ROOTFS_IMG}"
        log_ok "Rootfs flashed to /${ROOTFS_PARTITION}."
    fi

    [[ $DRY_RUN -eq 0 ]] && fastboot reboot || log_info "[dry-run] fastboot reboot"
fi

log_ok "Flash complete."
log_info "If the device does not boot:"
log_info "  Revert: bash boot/g7power/flash.sh --device g7power --revert \\"
log_info "          --stock-dtbo <stock-dtbo.img> --stock-boot <stock-boot.img>"
log_info "  EDL:    bash boot/g7power/flash.sh --edl"
```

#### `boot/g7power/recovery.sh`

Implement a recovery helper documenting:
- The two fastboot modes (stock ABOOT vs lk2nd fastboot) and how to enter each
- The full stock-restore sequence (dtbo + boot)
- The EDL (Qualcomm 9008) unbrick path with `edl` tool command examples
- How to verify the EDL connection (`lsusb | grep "05C6:9008"`)

#### `boot/g7power/boot-config.txt`

```
# Nuxel G7 Power Boot Configuration
# Stock ABOOT -> lk2nd (msm8916-mainline/lk2nd, msm8953) -> mainline Linux -> Nuxel
# Boot image format: legacy Android boot image header v1 (page 2048)
# Flash: fastboot (2-phase: stock ABOOT then lk2nd fastboot)

device=g7power
codename=ocean
soc=sdm632
soc_family=msm8953
emmc_path=/dev/block/bootdevice/by-name

# lk2nd source: https://github.com/msm8916-mainline/lk2nd
# lk2nd target: msm8953
# lk2nd build output: build-msm8953/lk2nd.img

# Kernel load addresses (VERIFY from real device stock boot.img):
kernel_addr=PLACEHOLDER_verify_from_stock_boot
ramdisk_addr=PLACEHOLDER_verify_from_stock_boot
tags_addr=PLACEHOLDER_verify_from_stock_boot
page_size=2048

# DTB: arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb
# Kernel cmdline:
cmdline="console=ttyMSM0,115200 earlycon=msm_geni_serial,0xa88000 nuxel.device=g7power root=/dev/block/bootdevice/by-name/userdata rootfstype=ext4 rootwait rw"

# CRITICAL FLASH ORDER — dtbo BEFORE lk2nd, ALWAYS:
# 1. fastboot flash dtbo dtbo.img           (stock ABOOT fastboot)
# 2. fastboot flash boot lk2nd.img          (stock ABOOT fastboot)
# 3. fastboot reboot bootloader             (enter lk2nd fastboot)
# 4. fastboot flash boot nuxel-boot.img     (lk2nd fastboot)
# 5. fastboot flash userdata rootfs.img     (lk2nd fastboot)
# 6. fastboot reboot

# Protected partitions — NEVER flash:
# modemst1 modemst2 fsg fsc ddr persist misc

# Recovery: EDL (Qualcomm 9008) — power off, hold Vol Down + Vol Up, plug USB
# Check: lsusb | grep "05C6:9008"
# Tool: pip install edl; edl --port /dev/ttyUSB0 flash boot stock-boot.img
```

**Acceptance:** `bash boot/g7power/flash.sh --help` prints the two-phase
fastboot sequence and all safety warnings. `bash -n boot/g7power/flash.sh`
passes. The script enforces dtbo-before-lk2nd in code, refuses on device
mismatch, and never touches protected partitions.

---

### TASK 6 — G7 Power rootfs/boot build orchestration (`images/g7power/build.sh`)

Create `images/g7power/build.sh` that:

1. Sources `tools/nuxel-device-select.sh` and verifies `NUXEL_DEVICE_KEY=g7power`.
2. Checks for required inputs:
   - `kernel/g7power/.build/out/arch/arm64/boot/Image.gz`
   - `kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb`
   - `boot/initramfs/initramfs.cpio.gz`
3. Calls `boot/g7power/pack-boot-v1.sh` to build the Nuxel boot image (v1).
4. Calls `images/mkrootfs.sh` to assemble the Nuxel userspace.
5. Installs G7 Power-specific firmware from `firmware/g7power/blobs/` into rootfs.
6. Installs G7 Power-specific device configs from `configs/g7power/` into rootfs.
7. Installs kernel modules from `kernel/g7power/.build/modules-staging/` into
   the rootfs `/lib/modules/`.
8. Produces all artifacts in `build/out/g7power/`:
   - `nuxel-ocean-boot.img` — Nuxel kernel + initramfs (v1 format)
   - `nuxel-ocean-rootfs.img` — ext4 rootfs image for `userdata`
   - `lk2nd.img` — copy from `boot/g7power/lk2nd/.build/build-msm8953/lk2nd.img`
     (if built; otherwise: `lk2nd.img: NOT YET BUILT` message)
   - `build-manifest.json` — device key, kernel commit, build timestamp
9. Does NOT emit dm-verity/AVB for Phase 1 (document why in a comment).
10. Does NOT touch `build/out/mustang/` or `build/out/s10plus/`.

**Acceptance:** `NUXEL_DEVICE=g7power bash images/g7power/build.sh --help`
prints G7 Power context; artifacts land under `build/out/g7power/`.

---

### TASK 7 — G7 Power device configs (`configs/g7power/`)

#### `configs/g7power/display/nuxel-g7power-display.sh`

```bash
#!/usr/bin/env bash
# Set 1520x720 display mode for G7 Power IPS LCD via MSM DRM
DISPLAY_W=720
DISPLAY_H=1520
OUTPUT="${NUXEL_DISPLAY_OUTPUT:-DSI-1}"
echo "[display] Setting ${DISPLAY_W}x${DISPLAY_H} on ${OUTPUT} (IPS LCD 1520x720, LM3697 backlight)"
wlr-randr --output "${OUTPUT}" --mode "${DISPLAY_W}x${DISPLAY_H}" || {
    echo "[display] WARN: wlr-randr failed. Verify MSM DRM + panel is initialised."
    echo "[display] Check: ls /sys/class/drm/ | grep card"
}
```

#### `configs/g7power/libinput/99-nuxel-ocean-touch.conf`

```ini
# Ilitek ILI2117 touch calibration for G7 Power (1520x720)
# Driver: ili210x (mainline CONFIG_TOUCHSCREEN_ILI210X)
# Bus: i2c_3 @ 0x41, IRQ: tlmm 65, inverted-x

Section "InputClass"
    Identifier "nuxel-g7power-touch"
    MatchIsTouchscreen "on"
    MatchDevicePath "/dev/input/event*"
    MatchProduct "ILI210x Touchscreen"
    Driver "libinput"
    Option "TransformationMatrix" "-1 0 1 0 1 0 0 0 1"  # inverted-x per DTS
    # Calibration values — refine from: libinput debug-events on real device
    # Option "CalibrationMatrix" "UNKNOWN UNKNOWN UNKNOWN UNKNOWN UNKNOWN UNKNOWN"
EndSection
```

Note: the `inverted-x` flag from the DTS maps to `TransformationMatrix "-1 0 1 0 1 0 0 0 1"`
in libinput. Verify this is correct on the physical device and adjust if touch
appears mirrored.

#### `configs/g7power/alsa-ucm/`

```
configs/g7power/alsa-ucm/
├── README.md        — WCD9335 cajon-v2 UCM2 notes; reference msm8953-mainline/alsa-ucm-conf
└── WCD9335/         — (stub)
    ├── HiFi.conf    — UCM2 stub for WCD9335
    └── WCD9335.conf — Master UCM file
```

`README.md` must note:
- Reference UCM configs from `https://github.com/msm8953-mainline/alsa-ucm-conf`
  which has production-tested WCD9335 UCM for ocean/sdm632
- ALSA card name must be filled from real device: `aplay -l` or
  `cat /proc/asound/cards`
- WCD9335 cajon-v2 requires `CONFIG_SND_SOC_WCD9335=y` in the kernel

#### `configs/g7power/modem/README.md`

```markdown
# G7 Power Snapdragon X9 LTE Modem — Status

The Qualcomm Snapdragon X9 LTE modem (integrated in SDM632 / msm8953) is NOT
ready for ModemManager in Nuxel Phase 1. There is no upstream MM plugin for
the X9 LTE modem interface on msm8953.

Phase 1 target: WiFi (WCN3680B / wcn36xx) only.
Phase 7 (stretch): Explore X9 LTE interface; implement custom MM plugin.

NEVER flash modemst1, modemst2, fsg, fsc, ddr — these hold per-unit IMEI
and radio calibration data.
```

#### `configs/g7power/pipewire/` and `configs/g7power/wireplumber/`

Stub configs referencing WCD9335 card name (TBD from `aplay -l` on device).
Default: 48000 Hz, stereo. Document the reference UCM path.

---

### TASK 8 — Operator device-inventory template and build gate

#### `docs/g7power-device-inventory.md`

```markdown
# G7 Power Device Inventory Template (Phase 0)
# Fill via ADB session on the physical device BEFORE running any build

## Phase 0 Collection Commands

# Verify device identity
adb shell getprop ro.product.device    # must be: ocean
adb shell getprop ro.product.name      # e.g.: ocean
adb shell getprop ro.product.model     # e.g.: XT1955-2
adb shell getprop ro.hardware          # e.g.: qcom
adb shell getprop ro.bootloader        # save bootloader revision

# SoC / hardware identity
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|qcom|msm|sdm'
adb shell cat /proc/cmdline
adb shell cat /proc/cpuinfo | head -30

# Full dmesg (critical — identifies touch, WiFi, BT, audio, camera)
adb shell dmesg > g7power-dmesg.txt

# Input devices (confirms ILI2117, inverted-x)
adb shell getevent -pl 2>/dev/null > g7power-input-devices.txt

# eMMC partition table
adb shell ls -la /dev/block/bootdevice/by-name/ > g7power-partitions.txt
adb shell cat /proc/partitions >> g7power-partitions.txt

# Vendor firmware listing (critical for firmware/g7power/manifest.yml)
adb shell ls -laR /vendor/firmware/        > g7power-vendor-firmware.txt
adb shell ls -laR /vendor/firmware_mnt/    >> g7power-vendor-firmware.txt
adb shell ls -laR /vendor/lib/modules/     > g7power-vendor-modules.txt
adb shell ls -laR /vendor/etc/firmware/    > g7power-vendor-etc-fw.txt

# WiFi firmware filenames (wcn36xx — NOT ath10k or brcm)
adb shell ls /vendor/firmware/WCNSS*      2>/dev/null
adb shell ls /vendor/firmware/wlan/prima/ 2>/dev/null

# BT firmware (hci_qca)
adb shell ls /vendor/firmware/qca/        2>/dev/null

# Audio card discovery
adb shell cat /proc/asound/cards          2>/dev/null
adb shell ls /sys/class/sound/            2>/dev/null

# Camera sensor identification (dmesg is best; also try v4l2-ctl)
grep -iE 'camera|sensor|ov[0-9]|s5k[0-9]|imx[0-9]|cci' g7power-dmesg.txt | head -20

# Fingerprint sensor
adb shell ls /sys/class/fingerprint/      2>/dev/null
grep -i fingerprint g7power-dmesg.txt | head -10

# Boot image load addresses (extract from stock boot.img)
adb shell "dd if=/dev/block/bootdevice/by-name/boot of=/sdcard/stock-boot.img bs=4096"
adb pull /sdcard/stock-boot.img /tmp/stock-boot.img
python3 tools/read-boot-header-v1.py /tmp/stock-boot.img

## Fill these after collection:
DEVICE_VARIANT:       UNKNOWN — fill from ro.product.model (e.g., XT1955-2)
BOOTLOADER_VERSION:   UNKNOWN — fill from ro.bootloader
KERNEL_ADDR:          PLACEHOLDER — extract from stock boot.img header
RAMDISK_ADDR:         PLACEHOLDER — extract from stock boot.img header
TAGS_ADDR:            PLACEHOLDER — extract from stock boot.img header
WIFI_FW_FILENAMES:    UNKNOWN — list from /vendor/firmware/WCNSS* and wlan/prima/
BT_FW_FILENAMES:      UNKNOWN — list from /vendor/firmware/qca/
AUDIO_UCM_CARD:       UNKNOWN — collect from aplay -l / /proc/asound/cards
CAMERA_SENSORS:       UNKNOWN — identify from dmesg
FINGERPRINT_SENSOR:   UNKNOWN — identify from dmesg / /sys/class/fingerprint/
NFC_PRESENT:          VERIFY — check dmesg for NFC; ls /dev/nfc* 2>/dev/null
```

#### Build gate function

Wire into every G7 Power build/flash script:

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

---

### TASK 9 — Documentation

#### `docs/g7power-bringup.md`

Create comprehensive documentation (minimum 300 lines) covering:

1. **Multi-device model** — how `NUXEL_DEVICE=g7power` maps to the `g7power/`
   directories; the three device keys.
2. **G7 Power boot chain** — ABOOT → lk2nd → Linux diagram; why lk2nd is needed;
   the dtbo-first rule and why it exists on msm8953.
3. **Two-phase fastboot** — stock ABOOT fastboot vs lk2nd fastboot; what each
   can flash; how to identify which mode you're in.
4. **Motorola unlock portal** — the full unlock sequence; what gets wiped; the
   `oem get_unlock_data` → portal → `oem unlock` flow.
5. **Protected partitions** — `modemst1`, `modemst2`, `fsg`, `fsc`, `ddr`,
   `persist`, `misc` — list and explain why each is irreplaceable.
6. **Phase 0 inventory** — why it is required; how to run it.
7. **Exact build commands:**
   ```bash
   # Phase 0: inventory (adb, device in Android)
   # Phase 1: lk2nd + kernel
   bash boot/g7power/lk2nd/README.md   # read build instructions
   NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --clone
   # Phase 2: flash lk2nd (stock ABOOT fastboot mode)
   NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
       --device g7power --dtbo stock-dtbo.img --lk2nd lk2nd.img
   # Phase 3: flash Nuxel (lk2nd fastboot mode)
   NUXEL_DEVICE=g7power bash images/g7power/build.sh
   NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
       --device g7power --boot build/out/g7power/nuxel-ocean-boot.img \
       --rootfs build/out/g7power/nuxel-ocean-rootfs.img
   ```
8. **ILI2117 touch caveat** — DTS node exists but some units may boot with no
   touch; what to check (`evtest /dev/input/eventX`) and how to verify.
9. **WiFi: wcn36xx vs ath10k** — why `wcn36xx` + `CONFIG_QCOM_WCNSS_PIL` is
   the correct choice for WCN3680B; what happens if ath10k is loaded instead.
10. **Driver status matrix** — honest table for all subsystems.
11. **EDL unbrick path** — how to enter Qualcomm 9008, what tools to use,
    what to flash to recover.

#### Update `README.md` and `QUICKSTART.md`

Add G7 Power to the multi-device table:
```markdown
| `g7power` | Motorola Moto G7 Power (ocean) | ocean | Bring-up in progress |
```

Add a "G7 Power Quick Start" section to `QUICKSTART.md` referencing
`docs/g7power-bringup.md`.

---

## ACCEPTANCE CRITERIA (definition of done)

1. All three UTM VM verify suites still pass (mustang path unbroken).
2. `NUXEL_DEVICE=g7power` selects only `g7power/` directories everywhere.
3. `grep -r "mustang\|s10plus\|beyond2lte" g7power/ 2>/dev/null` returns only
   legitimate cross-references in comments, never device coupling.
4. `grep -r "fastboot flash dtbo\|lk2nd" boot/g7power/flash.sh` confirms dtbo
   is flashed before lk2nd in the code path.
5. `boot/g7power/flash.sh --device mustang` exits with error immediately.
6. No fabricated checksums or firmware blobs: all unknowns are
   `UNKNOWN`/`PLACEHOLDER`.
7. All new shell scripts pass `bash -n` and `shellcheck -S warning`.
8. `_check_g7power_inventory()` gate is wired into build and flash scripts.
9. Protected partitions (`modemst1`, `modemst2`, `fsg`, `fsc`, `ddr`,
   `persist`, `misc`) are never referenced as flash targets in any script.
10. `docs/g7power-bringup.md` is present and internally consistent.

---

## THINGS YOU MUST NOT DO (absolute)

- Do not claim the G7 Power path is flashable/verified until real inventory +
  firmware + kernel build are complete.
- Do not reuse Pixel/Broadcom/PowerVR/Samsung/Exynos firmware for the G7 Power.
- Do not use `ath10k` or `brcmfmac` for WCN3680B WiFi — the correct driver is `wcn36xx`.
- Do not skip or reorder the dtbo → lk2nd → reboot → boot.img flash sequence.
- Do not relock the bootloader (`fastboot oem lock`) during development.
- Do not touch `modemst1`/`modemst2`/`fsg`/`fsc`/`ddr`/`persist`/`misc`.
- Do not delete or overwrite mustang or s10plus files.
- Do not fabricate kernel load addresses — mark as `PLACEHOLDER` and require
  the operator to extract them from the stock `boot.img` via `tools/read-boot-header-v1.py`.
- Do not use mustang's `vendor_boot`/`init_boot`/`vbmeta`/`fastbootd` logic
  for the G7 Power — it is A-only, header v1, no dynamic partition.

---

*Nuxel v0.2.0 — Build the bunker first. Add the rave lights later.*
*G7 Power bring-up: Phase 0 starts with ADB + dmesg + a stock boot.img backup. That's your foundation.*
