# Nuxel — Google Pixel 10 Pro XL Flash Quickstart
## Device: Google Pixel 10 Pro XL (`mustang`) | Nuxel v0.2.0

---

## Flashable ready state

**❌ NOT READY TO FLASH** (`mustang`, Nuxel v0.2.0 — deep-analyze 2026-08-29).
Kernel not built (`kernel/google-pixel-10-pro-xl/.build/out/Image.gz` absent),
0/30 firmware blobs verified, no `boot.img`/`init_boot.img`/`vbmeta.img` set,
and no physical flash has ever been performed. The gate table below documents
every remaining step.

> ⚠️ **HONEST STATUS — READ THIS FIRST**
>
> As of Nuxel v0.2.0, the Pixel 10 Pro XL (mustang) is a **design scaffold
> and code prototype — not a flashable OS**. The UTM ARM64 VM (Fedora 43,
> Phosh 0.54.0) boots and passes all verification suites (PASS=22/17, HARD
> PASS). Physical hardware flashing is **BLOCKED** — no verified boot image
> set, no firmware extracted, no kernel cross-built for mustang yet.
>
> The Pixel 10 Pro XL is Nuxel's **primary/default target**, but it is also the
> **hardest** one to bring up: its Tensor G5 (`gs501`) vendor kernel tree is
> private and almost every peripheral driver (GPU, panel, touch, modem, audio)
> is downstream-only. This is the reference device for the whole project — the
> VM geometry, the build dispatcher, `boot/flash.sh`, `firmware/manifest.yml`
> and `device/deviceinfo` all default to `mustang`.
>
> This guide documents the complete, correct procedure for when the build is
> ready. Every step is grounded in the actual repo (`boot/google-pixel-10-pro-xl/flash.sh`,
> `firmware/google-pixel-10-pro-xl/manifest.yml`, `docs/bootloader-unlock-guide.md`,
> `docs/driver-status.md`, `docs/mustang-recovery-bringup.md`). Placeholder
> values are explicitly marked.
>
> **Hard rule: Do NOT flash the physical Pixel 10 Pro XL (serial
> `58211FDCQ001LA`) until every gate in this document passes on real
> hardware.**

---

## Flash Readiness Gate

| Gate | Status | Evidence |
|---|---|---|
| UTM VM boots + all verify suites pass | ✅ **PASSED** | VM UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`; Phosh 0.54.0; PASS=22/17, HARD PASS |
| Physical mustang flashing | ⛔ **BLOCKED** | Zero hardware interaction in v0.2.0 cycle |
| Flashable image set (boot.img v4, vendor_boot, init_boot, dtbo, vbmeta, system.img) | ⛔ **NOT PRESENT** | `build/out/flashable/` contains only `cmdline.txt` |
| Firmware blobs | ⛔ **NOT INSTALLED** | `firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict` → 30 required MISSING / 0 verified |
| Factory image on disk | ⛔ **NOT AVAILABLE** | Operator must download `mustang-bp1a.250405.001` factory zip |
| Bootloader unlock | ⛔ **NOT PERFORMED** | Hardware-gated; current unlock state `requires verification` |
| Kernel cross-build (gs501/mustang) | ⛔ **NOT BUILT** | `gs501_defconfig` lives in private Google vendor tree; public GKI used for scaffolding |
| Recovery path | ⚠️ **SCRIPTED, NOT EXERCISED** | `boot/google-pixel-10-pro-xl/recovery.sh` + factory `flash-all.sh` documented; never run on real hardware |

**Bottom line:** read this guide in full before touching the device. Nothing here
is invented — every step is grounded in the verified hardware facts and the Nuxel
repository structure, and every unresolved value is explicitly marked.

---

## Why the Pixel 10 Pro XL is Different from the Other Two Targets

| | **Pixel 10 Pro XL (mustang)** | Galaxy S10+ (s10plus) | G7 Power (g7power) |
|---|---|---|---|
| Flash tool | **`fastboot` + `fastbootd`** (Google ABL) | TWRP + heimdall (**no fastboot**) | `fastboot` + `lk2nd` |
| Boot image | Header **v4** + `vendor_boot` + `init_boot` | Header **v1** (page 2048) | Header **v1** (page 2048) |
| Partition model | **A/B** dynamic `super` | A-only UFS | A-only eMMC |
| Verified boot | **AVB 2.0 + Titan M3** | none to fight | none to fight |
| Chainloader | None (ABL works) | U-Boot (chiffathefox) | lk2nd (msm8916-mainline) |
| GPU driver | **PowerVR DXT (vendor only)** | Mali Panfrost (mainline) | freedreno (mainline ✅) |
| Kernel path | GKI 6.12 (**private vendor tree**) | linux-postmarketos-exynos9820 | msm8953-mainline/linux |
| Mainline readiness | ❌ **Very low** | 🚧 Medium | ✅ High |
| Unbrick path | Google factory image (`flash-all.sh`) | Download Mode + heimdall | EDL (Qualcomm 9008) |

**Key takeaway:** the Pixel is the only Nuxel target with a real
verified-boot chain, and the only one whose recovery path is Google's own signed
factory image rather than a community tool. Respect it: an unlocked Pixel is
easy to recover, a *re-locked* Pixel with the wrong AVB key is not.

---

## Device Identity Reference

| Field | Value |
|---|---|
| Device | Google Pixel 10 Pro XL |
| Codename | `mustang` |
| Serial (reviewed) | `58211FDCQ001LA` |
| Hardware version | `MP1.0` |
| Hardware SKU | `G45RY` |
| SoC | Google Tensor G5 (`gs501`) |
| CPU | ARM Cortex-X5 + Cortex-A730 + Cortex-A530 (Armv9.2) |
| GPU | Imagination Technologies PowerVR DXT-72-2304 |
| Security chip | Google Titan M3 |
| RAM | 16 GB LPDDR5X |
| Storage | 256 GB UFS 4.0 |
| Display | Samsung AMB655X LTPO OLED, 3120×1440, 120 Hz |
| Touch | Samsung S6SY791 |
| WiFi/BT | Broadcom BCM4390 (Wi-Fi 7, BT 5.4) |
| Modem | Samsung Exynos 5500 (PCIe/MHI, 5G NR) |
| NFC | NXP SN220 |
| Audio | Cirrus Logic CS35L45 + CS42L43 |
| Sensors | Bosch BMI270, ST LSM6DSV, AMS TCS3710, Bosch BMP280 |
| Fingerprint | Goodix GF3636 (optical under-display) |
| Battery | 5300 mAh Li-Po; TI BQ2597x + Maxim MAX77729 |
| Bootloader | Google ABL (mustang variant) |
| Verified boot | AVB 2.0 with Titan M3 chain of trust |
| Boot image format | Android boot image **header v4** + `vendor_boot` + `init_boot` + `dtbo` |
| Partition model | **A/B** (seamless updates); `super` dynamic partition |
| Flash method | **`fastboot` + `fastbootd`** |
| Kernel target | Linux 6.12 LTS (`android-gs-mustang-6.12`, `gs501_defconfig`) |
| Factory image | `mustang-bp1a.250405.001-factory-*.zip` |

---

## The Pixel 10 Pro XL Boot Chain

```
Boot ROM (Tensor G5 SoC)
    │
    ▼
Google Titan M3 (security chip)
    │  Hardware root of trust
    │  Enforces AVB 2.0 chain of trust
    │
    ▼
Google ABL (Android Bootloader — mustang variant)
    │  Reads boot.img header v4
    │  Reads vendor_boot.img (vendor ramdisk + DTBO)
    │  Reads init_boot.img (generic ramdisk, Android 13+)
    │  Verifies the vbmeta chain against AVB keys
    │
    ▼
Linux 6.12 LTS kernel (android-gs-mustang-6.12, gs501_defconfig)
    │  nuxel.device=mustang on cmdline
    │
    ▼
Nuxel initramfs (init_boot.img)
    │  Probes /dev/disk/by-partlabel/system_a (or system_b)
    │  dm-verity root hash from the AVB chain
    │
    ▼
Nuxel system partition (dm-verity + read-only)
    │
    ▼
Phosh + GTK4 + PWA apps
```

**Key differences from the siblings:** the Pixel uses `fastboot` throughout. No
Odin, no TWRP, no U-Boot chainload. The AVB 2.0 chain is what provides verified
boot — if you flash a custom key, you can relock the bootloader with your own
signing key.

**`init_boot` is required:** mustang is Android 13+ split-ramdisk. A `boot.img`
without a matching `init_boot.img` will not boot. Do not skip it.

---

## Prerequisites

### Hardware

- Google Pixel 10 Pro XL (`mustang`), serial `58211FDCQ001LA`
- USB-C data cable (not charge-only; USB 3.2 Gen2 preferred)
- The device must NOT be carrier-locked (check: Settings → About phone → SIM
  status; if it shows "Network locked", you cannot unlock the bootloader)
- Enough battery (> 50%)

### Host Software

```bash
# Linux (Debian/Ubuntu)
sudo apt update
sudo apt install android-sdk-platform-tools \
    git make python3 \
    libssl-dev

# Verify platform tools
adb version          # must be present
fastboot --version   # must be >= 34.0.0

# macOS
brew install android-platform-tools
adb version
fastboot --version
```

### Critical: Carrier-Lock Check

```bash
# On the device: Settings → About phone → SIM status
# If "Network locked" appears, OEM unlock cannot be enabled — STOP HERE.

# Alternatively, check in ADB (if USB debugging is already on):
adb shell settings get global oem_unlock_allowed
# 1 = can unlock, 0 = cannot unlock (carrier-locked or restricted)
```

---

## Required Backup Before ANY Operation

Every unlock or flash operation **wipes the device** (factory reset).
Back up everything irreplaceable before proceeding.

```bash
# 1. Sync photos / media to Google Photos or local storage
# 2. Note the exact Android build string:
#    Settings → About phone → Build number
#    (saves the exact bootloader version needed for stock recovery)
# 3. Export 2FA seeds, password manager backups, app data
# 4. Note: fastboot flashing unlock IMMEDIATELY factory resets the device

# Record device state before any changes:
adb devices                    # => 58211FDCQ001LA    device
adb shell getprop ro.product.name     # => mustang
adb shell getprop ro.bootloader       # save this string
adb shell getprop ro.build.id         # save this string (for matching factory image)
```

---

## Step 1 — Enable OEM Unlocking (One-Time Setup)

> Skip to Step 2 if the bootloader is already unlocked.

```bash
# On the device:
# 1. Settings → About phone → tap "Build number" 7 times rapidly
#    "You are now a developer!" should appear.
#
# 2. Settings → System → Developer options
#    Toggle "OEM unlocking" ON
#    If this option is greyed out: device is carrier-locked. Cannot proceed.
#
# 3. Toggle "USB debugging" ON
#    Confirm the RSA key fingerprint on the device when prompted.

# Verify on host:
adb devices
# Expected: 58211FDCQ001LA    device
# If it shows "unauthorized": revoke and re-authorize USB debugging on device.
```

---

## Step 2 — Reboot to Fastboot (Bootloader)

```bash
# Method 1 (ADB):
adb reboot bootloader

# Method 2 (hardware):
# Power off → hold Volume Down + Power simultaneously

# Verify fastboot mode:
fastboot devices
# Expected: 58211FDCQ001LA    fastboot

fastboot getvar product
# Expected: product: mustang

fastboot getvar serial
# Expected: serial: 58211FDCQ001LA

fastboot getvar unlocked
# Expected: unlocked: no (if still locked)

fastboot getvar secure
# Expected: secure: yes (Titan M3 active — expected and correct)

fastboot getvar current-slot
# Expected: current-slot: a (or b)
```

---

## Step 3 — Unlock the Bootloader

> ⚠️ **WARNING: `fastboot flashing unlock` IMMEDIATELY FACTORY RESETS the device.**
> All data is wiped. There is no undo. Do NOT proceed without completing the
> backup step above.

```bash
# Unlock the bootloader:
fastboot flashing unlock
# The device will display a warning screen.
# Use Volume buttons to select "Unlock the bootloader".
# Press Power to confirm.
# The device factory resets and reboots.

# After reboot + setup, re-enable USB debugging:
# Settings → System → Developer options → USB debugging ON

# Reboot to fastboot again:
adb reboot bootloader

# Verify unlock:
fastboot getvar unlocked
# Expected: unlocked: yes

# For flashing bootloader/radio partitions (only needed if flashing BL/modem):
fastboot flashing unlock_critical
# This also wipes the device. Only run if you need to flash the bootloader partition.
```

---

## Step 4 — Download the Factory Image

The factory image is required to extract firmware blobs and as a stock
recovery asset.

```bash
# 1. Open in a browser (cannot be automated — Google consent flow):
#    https://developers.google.com/android/images#mustang
#
# 2. Find build: mustang-bp1a.250405.001
#    Download: mustang-bp1a.250405.001-factory-<xxxxx>.zip
#    (the <xxxxx> suffix requires verification from the page at download time)
#
# 3. Verify SHA-256 against the published checksum on that page:
shasum -a 256 mustang-bp1a.250405.001-factory-<xxxxx>.zip
# Compare output exactly against the published hash. Abort on any mismatch.

# 4. Keep the untouched zip as your stock recovery asset. Never modify it.

# 5. Extract:
cd /tmp
unzip mustang-bp1a.250405.001-factory-<xxxxx>.zip
```

---

## Step 5 — Extract Firmware Blobs

```bash
# Using the Nuxel firmware tooling:
cd <NUXEL_ROOT>

# List what will be extracted (dry run — no device needed):
NUXEL_DEVICE=mustang ./firmware/google-pixel-10-pro-xl/install-firmware.sh --list-files
# Expected: lists 30 required + 2 optional blobs; all reported MISSING (correct)

# Extract from factory image:
NUXEL_DEVICE=mustang ./firmware/google-pixel-10-pro-xl/install-firmware.sh \
    /tmp/mustang-bp1a.250405.001-factory-<xxxxx>.zip \
    --output-dir ./firmware-out \
    --install

# Verify extraction:
NUXEL_DEVICE=mustang ./firmware/google-pixel-10-pro-xl/verify-firmware.sh --root ./firmware-out -v
NUXEL_DEVICE=mustang ./firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict
# Expected after successful extraction + hashing: all 30 required blobs VERIFIED
```

### What the firmware manifest covers (mustang)

| Category | Files (manifest entries) | Destination |
|---|---|---|
| Exynos 5500 modem | `modem.bin`, `modem_pr.bin`, `modem_cal.bin`, `modem_cfg.txt`, `exynos5500_shm.bin` (+ramdump/debug optional) | `/lib/firmware/` |
| BCM4390 WiFi 7 | `brcmfmac4390*.bin`, `brcmfmac4390-pcie.clm_blob`, `brcmfmac4390.nvm` | `/lib/firmware/brcm/` |
| BCM4390 BT 5.4 | `BCM4390.hcd` | `/lib/firmware/brcm/` |
| PowerVR GPU | `pvr_*.fw`, `pvr_drv.so` (vendor) | `/lib/firmware/img/`, `/usr/lib/` |
| Display (AMB655X) | `amb655x_fw.bin`, `amb655x_gamma.bin` | `/lib/firmware/` |
| Touch (S6SY791) | `s6sy791_touch_fw.bin` | `/lib/firmware/` |
| Audio (CS42L43 + CS35L45) | `cs35l45_fw.bin`, `cs35l45_dsp.bin`, `cs42l43_fw.bin` | `/lib/firmware/` |
| Sensors | `bmi270_fw.bin`, `lsm6dsv_fw.bin`, `tcs3710_fw.bin` | `/lib/firmware/` |
| NFC (NXP SN220) | `sn220_fw.bin` | `/lib/firmware/` |
| Fingerprint (Goodix GF3636) | `gf3636_fw.bin` | `/lib/firmware/` |
| PMIC (MAX77729 + MAX77826) | `max77729_fw.bin`, `max77826_fw.bin` | `/lib/firmware/` |
| Charger (BQ2597x + MAX1720x) | `bq2597x_fw.bin`, `max1720x_fw.bin` | `/lib/firmware/` |

---

## Step 6 — Build the Nuxel Kernel

> ⛔ **Currently blocked by private Google vendor tree.** The authoritative
> `gs501_defconfig` lives in `android-gs-mustang-6.12` (private). The public
> GKI `android16-6.12` can be used for scaffolding but is not bootable on
> mustang hardware without the vendor tree. This step will be unblocked when
> the vendor kernel source is available.

```bash
# Install cross-compiler:
sudo apt install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
    bc bison flex libssl-dev libelf-dev

export CROSS_COMPILE=aarch64-linux-gnu-
export ARCH=arm64

# When vendor tree is available:
git clone https://android.googlesource.com/kernel/google-modules/gs \
    -b android-gs-mustang-6.12 kernel/.build/vendor
# (This repo is currently private and returns 404 for anonymous access)

# With vendor tree available:
NUXEL_DEVICE=mustang bash kernel/google-pixel-10-pro-xl/build-kernel.sh --vendor

# Without vendor tree (public GKI only — NOT bootable on hardware):
NUXEL_DEVICE=mustang bash kernel/google-pixel-10-pro-xl/build-kernel.sh
# Produces a scaffold build only. Merge: gki_defconfig + kernel/google-pixel-10-pro-xl/defconfig

# Expected output (when build succeeds):
# kernel/google-pixel-10-pro-xl/.build/out/Image.gz
# kernel/google-pixel-10-pro-xl/.build/out/dtbs/mustang.dtb
```

### Kernel configuration highlights (mustang/gs501)

The `kernel/google-pixel-10-pro-xl/defconfig` fragment enables:

| Feature | Config | Status |
|---|---|---|
| PowerVR DXT GPU | `CONFIG_DRM_POWERVR` | ❌ Not in mainline GKI; vendor tree only |
| AMB655X LTPO panel | `CONFIG_DRM_PANEL_SAMSUNG_AMB655X` | ❌ Not in mainline; vendor tree only |
| S6SY791 touch | `CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791` | ❌ Not in mainline; vendor tree only |
| Exynos 5500 modem | `CONFIG_MHI_SAMSUNG_EXYNOS5500` | ❌ Not in mainline; vendor tree only |
| BCM4390 WiFi 7 | `CONFIG_BRCMFMAC` + BCM4390 chip entry | 🚧 Base driver mainline; chip entry needs patch |
| UFS 4.0 | `CONFIG_SCSI_UFSHCD_PLATFORM` | ✅ Mainline |
| AppArmor / seccomp | `CONFIG_SECURITY_APPARMOR`, `CONFIG_SECCOMP` | ✅ Mainline |
| Linux namespaces | All namespace configs | ✅ Mainline |
| Nuxel features | `CONFIG_NUXEL`, `CONFIG_NUXEL_PHONE`, `CONFIG_NUXEL_BOOT_PARAM` | ✅ Nuxel patch |

---

## Step 7 — Build Nuxel Boot Images

> ⛔ **Currently blocked by Step 6.** No verified boot artifact set produced yet.

```bash
# Build the full image set (requires kernel + firmware from Steps 5-6):
NUXEL_DEVICE=mustang bash images/google-pixel-10-pro-xl/build.sh --android

# This produces:
#   build/out/mustang/flashable/boot.img         ← Android boot header v4
#   build/out/mustang/flashable/vendor_boot.img  ← Vendor ramdisk + DTBO
#   build/out/mustang/flashable/init_boot.img    ← Generic ramdisk (Android 13+)
#   build/out/mustang/flashable/dtbo.img         ← Device tree overlay
#   build/out/mustang/flashable/vbmeta.img       ← AVB verification metadata
#   build/out/mustang/flashable/system.img       ← dm-verity ext4 system

# Dev build (no real kernel — produces stubs, NOT FLASHABLE):
NUXEL_DEVICE=mustang bash images/google-pixel-10-pro-xl/build.sh --quick
# Produces zero-filled stubs in build/out/mustang/flashable/ for CI validation only.
```

### mustang Boot Image Format Details

| Image | Format | Size | Notes |
|---|---|---|---|
| `boot.img` | Android header **v4** | ~96 MB slot | Kernel + generic ramdisk ref (Android 13+) |
| `vendor_boot.img` | Android header v3 + vendor ramdisk | ~96 MB slot | Vendor ramdisk + DTBO overlay; **required on mustang** |
| `init_boot.img` | Android header v4 | ~8 MB slot | Generic ramdisk; **required on Android 13+ (mustang)** |
| `dtbo.img` | DTBO format | ~16 MB slot | Device tree overlay; verified by AVB via vbmeta |
| `vbmeta.img` | AVB 2.0 | ~64 KB | Chains verification of boot, vendor_boot, dtbo, system; signed with AVB key |
| `system.img` | ext4 + dm-verity | ~8 GB (super) | Read-only system partition; mounted via dm-verity |

**Critical mustang specifics:**
- `init_boot.img` is **required** — mustang uses Android 13+ split-ramdisk.
  Missing `init_boot` causes a boot failure. Do not skip it.
- `vendor_boot.img` contains the mustang DTBO. Without it, the display and
  touch do not initialize.
- `vbmeta.img` with `--disable_verity --disable_hashtree` is needed for dev
  flashing without a relocked bootloader.

---

## Step 8 — Generate AVB Keys (for Production Relock)

> For development flashing (no relock), skip this step. The dev flash path
> uses `--skip-avb` / `--allow-unverity-dev` which disables AVB verification
> and does not require custom keys.

```bash
# Generate Nuxel-specific AVB RSA key (one-time; protect this key):
cd <NUXEL_ROOT>
bash tools/gen-keys.sh --avb --out keys/
# Produces: keys/nuxel-avb-private.pem, keys/nuxel-avb-public.pem

# Enroll the custom public key in the bootloader (BEFORE relocking):
fastboot flash avb_custom_key keys/nuxel-avb-public.pem

# Sign vbmeta with your custom key:
bash images/google-pixel-10-pro-xl/avb/sign.sh \
    --key keys/nuxel-avb-private.pem \
    --images build/out/mustang/flashable/

# Relock with custom key (WIPES DEVICE — production only):
bash boot/google-pixel-10-pro-xl/flash.sh \
    --device mustang \
    --relock-custom-key keys/nuxel-avb-private.pem \
    --production
```

---

## Step 9 — Flash to the Google Pixel 10 Pro XL

### Pre-flash safety checklist

- [ ] Device is in **fastboot mode** (`fastboot devices` shows `58211FDCQ001LA fastboot`)
- [ ] `fastboot getvar product` returns `mustang`
- [ ] `fastboot getvar unlocked` returns `yes`
- [ ] Full backup complete (Backup section above)
- [ ] Factory image downloaded + SHA-256 verified
- [ ] Firmware blobs extracted + verified (Step 5)
- [ ] Boot images built (Step 7) — NOT zero-filled stubs
- [ ] Battery > 50%

### Development flash (AVB disabled — easiest path)

```bash
# !! Verify device identity first !!
fastboot getvar product     # must be: mustang
fastboot getvar serial      # must be: 58211FDCQ001LA
fastboot getvar unlocked    # must be: yes

# Flash all images (development mode: AVB disabled)
NUXEL_DEVICE=mustang bash boot/google-pixel-10-pro-xl/flash.sh \
    --device mustang \
    --skip-avb \
    --allow-unverity-dev \
    --slot a

# What flash.sh does in development mode:
# 1. fastboot flash boot_a         build/out/mustang/flashable/boot.img
# 2. fastboot flash vendor_boot_a  build/out/mustang/flashable/vendor_boot.img
# 3. fastboot flash init_boot_a    build/out/mustang/flashable/init_boot.img
# 4. fastboot flash dtbo_a         build/out/mustang/flashable/dtbo.img
# 5. fastboot flash vbmeta_a       build/out/mustang/flashable/vbmeta.img  (AVB disabled)
# 6. fastboot flash system_a       build/out/mustang/flashable/system.img  (via fastbootd super)
# 7. fastboot set_active a
# 8. fastboot reboot

# Or manually, step by step:
fastboot flash boot_a          build/out/mustang/flashable/boot.img
fastboot flash vendor_boot_a   build/out/mustang/flashable/vendor_boot.img
fastboot flash init_boot_a     build/out/mustang/flashable/init_boot.img
fastboot flash dtbo_a          build/out/mustang/flashable/dtbo.img

# For vbmeta — disable verification (dev mode):
python3 external/avbtool/avbtool make_vbmeta_image \
    --flag 2 \
    --output build/out/mustang/flashable/vbmeta-disabled.img
fastboot flash vbmeta_a        build/out/mustang/flashable/vbmeta-disabled.img

# Flash system (dynamic partition via fastbootd):
fastboot reboot fastboot        # enter fastbootd (userspace fastboot)
fastboot flash system_a         build/out/mustang/flashable/system.img
fastboot flash modem_a          build/out/mustang/flashable/modem.img  # if rebuilding modem

# Set active slot and reboot:
fastboot set_active a
fastboot reboot
```

### Wipe userdata (first flash or clean install)

```bash
# Only needed on first flash or if you want a clean Nuxel install:
fastboot -w
# OR:
fastboot erase userdata
fastboot erase metadata
```

### Production flash (custom AVB key + relock)

```bash
# Only after successfully booting in dev mode and generating AVB keys:
NUXEL_DEVICE=mustang bash boot/google-pixel-10-pro-xl/flash.sh \
    --device mustang \
    --relock-custom-key keys/nuxel-avb-private.pem \
    --production
# WARNING: --relock-custom-key triggers fastboot flashing lock which WIPES the device.
# Only use this after verifying Nuxel boots correctly in dev mode.
```

---

## A/B Slot Management

The Pixel 10 Pro XL uses A/B seamless updates. Both slots (`_a` and `_b`) must
be managed correctly.

```bash
# Check current active slot:
fastboot getvar current-slot
# => current-slot: a

# Flash to current active slot:
SLOT=$(fastboot getvar current-slot 2>&1 | grep 'current-slot:' | awk '{print $2}')
fastboot flash boot_${SLOT}         build/out/mustang/flashable/boot.img
fastboot flash vendor_boot_${SLOT}  build/out/mustang/flashable/vendor_boot.img
fastboot flash init_boot_${SLOT}    build/out/mustang/flashable/init_boot.img
fastboot flash dtbo_${SLOT}         build/out/mustang/flashable/dtbo.img

# Switch active slot (for A/B update testing):
fastboot set_active b
fastboot set_active a

# Flash modem partition (only if updating modem firmware):
fastboot flash modem_a  build/out/mustang/flashable/modem.img
# Note: modem_*.img contains the Exynos 5500 baseband — ~200 MB
```

---

## Partition Layout Reference (mustang)

```
Partition       Size        Notes
─────────────── ─────────── ──────────────────────────────────────────
boot_a/boot_b   96 MB each  Android boot image v4 (kernel + generic ramdisk ref)
vendor_boot_a/b 96 MB each  Vendor ramdisk + DTBO
init_boot_a/b   8 MB each   Generic ramdisk (Android 13+; REQUIRED)
dtbo_a/dtbo_b   16 MB each  Device tree overlay
vbmeta_a/b      64 KB each  AVB 2.0 top-level descriptor
super           ~8 GB       Dynamic partition: system, system_ext, product, vendor
userdata        remaining   User data (ext4 / f2fs; wiped on unlock)
modem_a/b       200 MB each Exynos 5500 baseband firmware
dsp_a/b         64 MB each  DSP firmware
persist         32 MB       Persistent calibration (do NOT wipe)
metadata        64 MB       Dynamic partition metadata
```

---

## fastboot Reference for mustang

```bash
# Identity checks (run these before every flash session):
fastboot getvar product          # => mustang
fastboot getvar serial           # => 58211FDCQ001LA
fastboot getvar unlocked         # => yes (must be unlocked to flash)
fastboot getvar secure           # => yes (Titan M3 — expected)
fastboot getvar current-slot     # => a or b
fastboot getvar max-download-size  # => 536870912 (512 MB)

# Flash commands:
fastboot flash <partition>  <image.img>
fastboot erase <partition>
fastboot set_active <a|b>
fastboot -w                         # wipe userdata + metadata
fastboot reboot                     # reboot to Android
fastboot reboot bootloader          # reboot back to fastboot
fastboot reboot fastboot            # reboot to fastbootd (userspace; dynamic partitions)
fastboot reboot recovery            # reboot to recovery

# Dynamic partition flashing (system.img requires fastbootd):
fastboot reboot fastboot
fastboot flash system_a  system.img

# AVB key management:
fastboot flash avb_custom_key  keys/nuxel-avb-public.pem
fastboot erase avb_custom_key   # remove custom key

# Dangerous (wipes + locks):
fastboot flashing lock            # re-lock bootloader (WIPES DEVICE)
fastboot flashing unlock          # unlock (WIPES DEVICE)
fastboot flashing unlock_critical # unlock critical (WIPES DEVICE; only for BL/radio)
```

---

## Firmware Details (Exynos 5500 Modem)

The Exynos 5500 modem is a PCIe/MHI device. It is **not upstream** in
mainline ModemManager. Nuxel v0.2.0 does not have a working MM plugin for it.

```bash
# Modem firmware is in the modem partition (separate from vendor partition):
# modem_a / modem_b — ~200 MB per slot

# ModemManager status (honest):
# CONFIG_MHI_BUS_PCI_GENERIC — downstream vendor tree only
# CONFIG_MHI_SAMSUNG_EXYNOS5500 — not in mainline at all
# A custom MM plugin is required before voice/SMS/data works.

# Phase 1 target: WiFi (BCM4390 brcmfmac) only.
# Phase 8+ target: Exynos 5500 modem bring-up via custom MM plugin.
```

---

## Step 10 — Verify the Flash

```bash
# After the device reboots into Nuxel:

# Verify services (from adb shell once Nuxel boots):
adb shell systemctl status nuxel-web nuxel-http-bridge nuxel-bridge \
    nuxel-portal nuxel-notifications --no-pager

# Verify D-Bus services:
adb shell ss -ltnp | grep -E ':(8000|8080)'

# Test the bridge API:
adb shell curl -s 'http://127.0.0.1:8080/api/v1/ping?message=hello'

# Verify Phosh is running:
adb shell systemctl --user status phosh

# Check for failed units:
adb shell systemctl --failed

# Nuxel init verified (from dmesg):
adb shell dmesg | grep -i 'nuxel'
# Expected: "nuxel-init: nuxel.device=mustang" + dm-verity mount success
```

---

## Recovery — How to Restore Stock Android

If anything goes wrong, restore from the factory image. The stock `flash-all.sh`
script included in the factory zip handles everything.

```bash
# Enter fastboot mode:
# Power off → hold Volume Down + Power

# Verify connected:
fastboot devices
# => 58211FDCQ001LA    fastboot

# Option 1: Use the factory image's own flash script (safest):
cd /tmp/mustang-bp1a.250405.001-factory-<xxxxx>/
./flash-all.sh
# This wipes userdata and reflashes all partitions to stock.

# Option 2: Manual restore (only if flash-all.sh is unavailable):
fastboot flash bootloader  bootloader-mustang-*.img
fastboot reboot bootloader
fastboot flash radio       radio-mustang-*.img
fastboot reboot bootloader
fastboot flash boot_a      boot.img
fastboot flash vendor_boot_a vendor_boot.img
fastboot flash init_boot_a   init_boot.img
fastboot flash dtbo_a        dtbo.img
fastboot flash vbmeta_a      vbmeta.img
fastboot reboot fastboot
fastboot flash system_a    system.img
fastboot flash product_a   product.img
fastboot flash vendor_a    vendor.img
fastboot -w
fastboot set_active a
fastboot reboot

# Option 3: Revert Nuxel boot → stock boot only (fastest; keeps stock data):
NUXEL_DEVICE=mustang bash boot/google-pixel-10-pro-xl/flash.sh --revert
# This re-flashes stock boot.img + vendor_boot.img from the saved factory backup.
```

---

## Phased Bring-Up Plan (mustang)

| Phase | Goal | Entry Criteria | Exit Criteria |
|---|---|---|---|
| 0 | Unlock + factory image | Device in hand, carrier-unlocked | Bootloader unlocked, factory image downloaded + SHA-256 verified |
| 1 | Firmware extraction | Factory image available | `verify-firmware.sh --strict` → 30/30 verified |
| 2 | Vendor kernel build | Vendor tree accessible (`android-gs-mustang-6.12`) | `Image.gz` + mustang DTB produced |
| 3 | Boot image packing | Kernel + firmware ready | `boot.img` v4 + `vendor_boot.img` + `init_boot.img` produced |
| 4 | First boot (display + touch) | Images flashed | Phosh launches at 3120×1440; S6SY791 touch responds |
| 5 | WiFi/BT | Phase 4 done + BCM4390 firmware | `wlan0` up; `bluetoothctl` sees BCM4390 |
| 6 | GPU | Phase 5 done | PowerVR DXT (vendor) or llvmpipe fallback in Phosh |
| 7 | Audio | Phase 6 done + CS42L43/CS35L45 firmware | Speaker via PipeWire UCM |
| 8 | Modem | Phase 7 done | Custom MM plugin for Exynos 5500; data via LTE/5G |
| 9 | dm-verity + production AVB | Phase 8 done | Custom AVB key enrolled; bootloader relocked; dm-verity enforced |

---

## Driver Status (mustang — honest)

| Subsystem | Status | Notes |
|---|---|---|
| GPU (PowerVR DXT-72-2304) | ❌ Not mainline | No `CONFIG_DRM_POWERVR` upstream; vendor `pvr_drv.so` only |
| Display (AMB655X LTPO) | ❌ Not mainline | `CONFIG_DRM_PANEL_SAMSUNG_AMB655X` vendor tree only |
| Touch (S6SY791) | ❌ Not mainline | `CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791` vendor tree only |
| WiFi (BCM4390 brcmfmac) | 🚧 Base mainline | BCM4390 chip entry + firmware from device needed |
| Bluetooth (BCM4390 BT 5.4) | 🚧 Needs `.hcd` | `CONFIG_BT_HCIUART_BCM` mainline; `BCM4390.hcd` from vendor |
| Modem (Exynos 5500 PCIe/MHI) | ❌ Not mainline | No `CONFIG_MHI_SAMSUNG_EXYNOS5500` upstream; custom MM plugin needed |
| Audio (CS42L43 + CS35L45) | ❌ Not mainline | Both codecs vendor-tree only in 6.12 |
| NFC (NXP SN220) | ❌ Not mainline | `CONFIG_NFC_NXP_SN220` not upstream |
| Fingerprint (Goodix GF3636) | ❌ Not mainline | Optical under-display; no upstream driver |
| UFS 4.0 | ✅ Mainline | `CONFIG_SCSI_UFSHCD_PLATFORM` |
| AppArmor / seccomp | ✅ Mainline | Full sandbox available |
| USB 3.2 / dwc3 | ✅ Mainline | Standard dwc3; includes `fastboot` gadget |
| Titan M3 | ⬜ Read-only | AVB 2.0 verification uses it; Keymaster/StrongBox not needed |

---

## FAQ

**Q: Why is the mustang kernel locked behind a private Google repo?**
The `gs501_defconfig` and all SoC/modem/radio driver modules live in
`android-gs-mustang-6.12`, which Google has not made publicly accessible for
anonymous cloning. The public GKI (`android16-6.12`) can be used for building
and scaffolding but will not boot on mustang hardware without the vendor tree.
This is the single biggest hardware-bring-up blocker.

**Q: Do I need to unlock the bootloader before I can use Nuxel?**
Yes. Without an unlocked bootloader, fastboot will refuse to flash custom images.
Unlocking factory resets the device — back up everything first.

**Q: Can I re-lock the bootloader with Nuxel installed?**
Yes, using a custom AVB key. Generate your own AVB key pair, enroll the public
key via `fastboot flash avb_custom_key`, sign all images with your private key,
then `fastboot flashing lock`. The device will only boot images signed with
your key — this is the production Nuxel security model.

**Q: Why is the Pixel harder to bring up than the S10+ or G7 Power?**
Because almost none of its silicon is mainline. The S10+ has Panfrost and the
G7 Power has freedreno/MSM DRM/ILI2117/LM3697 all upstream; the Pixel's GPU,
panel, touch, modem, and audio codecs exist only in Google's private vendor tree.
The Pixel is the primary target *and* the least mainline-friendly one.

**Q: What happens to Titan M3 after bootloader unlock?**
Titan M3 remains active for hardware key storage and attestation. Unlocking
disables AVB verification of boot images (which is what we want during
development). It does NOT disable Titan M3 itself. Re-locking with a custom
key re-enables verified boot with your own root of trust.

**Q: Will Google Banking / Google Pay still work?**
No. Unlocking the bootloader trips the software integrity flag. Google Pay,
banking apps using SafetyNet/Play Integrity, and DRM content (Widevine L1) may
refuse to work. Nuxel is not an Android-based OS anyway — none of these are
relevant.

**Q: Can I use Nuxel on a carrier-locked mustang?**
No. Carrier-locked devices have OEM unlock disabled and the bootloader cannot
be unlocked without carrier intervention or an account unlock. Check before
purchasing a device for Nuxel use.

**Q: The factory image URL has `<xxxxx>` in it. What goes there?**
The exact suffix is shown on the Google factory images page at download time
and changes between builds. Always verify the SHA-256 checksum published on
that page against your downloaded file before using it.

---

## Key URLs

| Resource | URL |
|---|---|
| Google Pixel factory images | https://developers.google.com/android/images#mustang |
| Android platform tools | https://developer.android.com/studio/releases/platform-tools |
| GKI kernel (android16-6.12) | https://android.googlesource.com/kernel/common (branch android16-6.12) |
| mustang vendor kernel (private) | https://android.googlesource.com/kernel/google-modules/gs (branch android-gs-mustang-6.12) |
| AVB tool | https://android.googlesource.com/platform/external/avb |
| Nuxel repo | `/Users/wicked/x/nuxel` (local) |

---

*Build the bunker first. Add the rave lights later.*
*— Nuxel v0.2.0*
