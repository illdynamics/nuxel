You are fixing and completing the Nuxel phone OS for the CORRECT target device. The previous build was done for the wrong phone (Pixel 7 "panther"). You must now fix ALL files to target the actual device:

## TARGET DEVICE - EXACT SPECS
- **Device**: Google Pixel 10 Pro XL
- **Codename**: mustang
- **Serial Number**: 58211FDCQ001LA
- **Hardware Version**: MP1.0
- **Hardware SKU**: G45RY
- **SoC**: Google Tensor G5 (not G2!)
- **CPU**: ARM Cortex-X5 + Cortex-A730 + Cortex-A530 (Armv9.2)
- **GPU**: Imagination Technologies DXT-72-2304 (not Mali!)
- **Modem**: Samsung Exynos 5500 (not 5300!)
- **Display**: 3120x1440 LTPO OLED, 120Hz
- **RAM**: 16GB LPDDR5X
- **Storage**: 256GB UFS 4.0
- **WiFi**: Broadcom BCM4390 (WiFi 7)
- **Bluetooth**: 5.4
- **Kernel target**: Linux 6.12 LTS (not 5.10!)
- **Defconfig**: gs501_defconfig (not gs201_defconfig!)
- **Battery**: 5300mAh

## TWO REFERENCE DOCUMENTS
Read these files in the workspace to understand architecture:
1. `/workspace/Fonux, NuDroid, and the Best Path to a Linux-Only PWA-First Smartphone.md`
2. `/workspace/Building a Post-Android Phone OS on Existing Android Hardware.pdf`

## BOOTLOADER SPECIFICS FOR THIS EXACT DEVICE
The Google Pixel 10 Pro XL (mustang) bootloader chain:
- Boot ROM → Google Secure Boot (Titan M3 chip)
- Verified Boot: AVB 2.0 with chain of trust through Titan M3
- Bootloader: Google ABL (Android Bootloader) - mustang variant
- Fastboot protocol: standard + Google extensions
- Fastbootd: supported in userspace
- A/B slots: _a / _b with seamless updates
- Dynamic partitions: super partition containing system, system_ext, product, vendor
- boot.img header: version 4
- vendor_boot.img: required (contains vendor ramdisk + DTBO)
- init_boot.img: required on Android 14+ (generic ramdisk)
- dtbo.img: required (device tree overlay)
- Boot image signing: AVB uses vbmeta to chain-verify boot and dtbo
- Unlock method: `fastboot flashing unlock` (requires OEM unlocking enabled in Developer Options)
- Unlock critical: `fastboot flashing unlock_critical` for bootloader partitions
- Re-lock: `fastboot flashing lock` (WILL WIPE DEVICE)
- Custom AVB: We must create our own vbmeta.img with disabled verification for custom boot
- Custom key enrollment: Use `fastboot flash avb_custom_key` if needed
- Partition layout for mustang (from factory image):
  - boot_a/boot_b: 96MB each
  - vendor_boot_a/vendor_boot_b: 96MB each  
  - init_boot_a/init_boot_b: 8MB each
  - dtbo_a/dtbo_b: 16MB each
  - vbmeta_a/vbmeta_b: 64KB each
  - super: 8GB (dynamic - contains system, system_ext, product, vendor)
  - userdata: remaining space
  - modem_a/modem_b: 200MB each (Exynos 5500 firmware)
  - dsp_a/dsp_b: 64MB each
  - persist: 32MB
  - metadata: 64MB

## DRIVER REQUIREMENTS FOR TENSOR G5
The mustang uses different drivers than previous Pixels:
- GPU: Imagination DXT (PowerVR Rogue) - uses pvr_drv.so + powervr kernel module, NOT panfrost
- Display: Samsung AMB655X LTPO panel driver (not S6E3FC3)
- Touch: Samsung S6SY791 touch controller (not synaptics)
- Audio: Cirrus Logic CS35L45 speaker amp + CS42L43 audio codec
- Modem: Samsung Exynos 5500 via MHI v2 (PCIe Gen3)
- WiFi: Broadcom BCM4390 (brcmfmac with updated firmware)
- NFC: NXP SN220 (pn544 replacement)
- Sensors: Bosch BMI270 IMU, ST LSM6DSV, AMS TCS3710 ALS/prox
- USB: USB 3.2 Gen2 Type-C with DP Alt Mode
- Fingerprint: Goodix optical under-display (gf3636)
- Battery charging: TI BQ2597x fast charge + max1720x fuel gauge
- PMIC: Maxim MAX77729 + MAX77826

## WHAT TO FIX AND COMPLETE

### 1. Fix ALL device references from panther → mustang
Every file that mentions "panther", "gs201", "Tensor G2", "Exynos 5300", "S6E3FC3", "synaptics", "5.10" must be updated to mustang specs.

### 2. Rewrite device-info.yml for mustang
Complete hardware specs as listed above.

### 3. Rewrite kernel/defconfig for gs501
The gs501 uses different:
- GPU: CONFIG_DRM_POWERVR instead of CONFIG_DRM_PANFROST
- Display: CONFIG_DRM_PANEL_SAMSUNG_AMB655X
- Audio: CONFIG_SND_SOC_CS35L45, CONFIG_SND_SOC_CS42L43
- Modem: CONFIG_MHI_BUS_PCI_GENERIC (Exynos 5500 uses PCIe MHI)
- Touch: CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791
- Sensors: CONFIG_BMI270, CONFIG_LSM6DSV
- WiFi: CONFIG_BRCMFMAC (BCM4390)
- Charger: CONFIG_CHARGER_BQ2597X, CONFIG_BATTERY_MAX1720X
- UFS: CONFIG_SCSI_UFSHCD_PLATFORM (UFS 4.0)
- Kernel base: 6.12 LTS, not 5.10

### 4. Update boot/flash.sh for mustang bootloader specifics
Include:
- AVB disable instructions (flash custom vbmeta)
- Exact partition sizes for mustang
- init_boot flashing step (required on mustang)
- dtbo flashing
- Modem firmware flashing instructions
- Titan M3 considerations
- `fastboot flashing unlock_critical` warning
- Exact command sequences for this serial number device

### 5. Update images/build.sh
- Change kernel source: android-gs-mustang-6.12 (not android-gs-raviole-5.10)
- Change defconfig: gs501_defconfig
- Add init_boot.img and dtbo.img generation
- Add vbmeta.img generation with disabled verification
- Update partition sizes for mustang

### 6. Create boot/boot.img/mustang-boot-config.txt
Boot image configuration specific to mustang:
- cmdline: console=ttyGSI0,115200 earlycon=gsihvc0 loglevel=4 init=/init nuxel.boot=1 nuxel.device=mustang nuxel.serial=58211FDCQ001LA root=/dev/disk/by-partlabel/system_a rootwait ro rootfstype=ext4
- Base address: 0x10000000 (mustang uses different base than panther)
- Kernel offset: 0x00008000
- Ramdisk offset: 0x01000000 (mustang increased)
- DTB offset: 0x00000100 (mustang uses DTBO overlay, not embedded DTB)
- Header version: 4
- OS version: 15.0.0
- OS patch level: 2025-06-05

### 7. Update firmware/manifest.yml for Exynos 5500
Different firmware files and paths for mustang's modem.

### 8. Update images/hooks/01-customize-rootfs.sh
Fix driver references for mustang (touch, display, audio, modem).

### 9. Update images/config/packages.yml
Add packages for Imagination GPU (powervr), mustang-specific kernel modules.

### 10. Update ci/Dockerfile and ci/build-pipeline.yml
Change kernel source references.

### 11. Update all docs (architecture.md, device-setup.md, build-guide.md, roadmap.md)
Fix hardware references throughout.

### 12. Create a bootloader-unlock-guide.md file
Complete step-by-step bootloader unlock guide for this exact Pixel 10 Pro XL (serial 58211FDCQ001LA, HW MP1.0, SKU G45RY).

### 13. Create a driver-status.md file
Track which drivers work and which are in progress for mustang.

## RULES
1. Fix EVERY reference to panther/gs201/Tensor G2 across all files
2. All kernel configs must reference gs501_defconfig and 6.12 LTS
3. The flash script must handle the full mustang boot chain including AVB
4. Do NOT delete working PWA code - only fix device references
5. Do NOT delete working service code - only update if modem interface changed
6. Complete the bootloader unlock guide with exact serial-specific instructions
7. Continue until every file is corrected
8. The result must be flashable to device 58211FDCQ001LA

---

<!-- Task reconciliation owned by the Repo state audit & doc reconciliation build group (briq-01-audit). See docs/repo-audit.md for the measured single source of truth. -->
