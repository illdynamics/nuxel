# Nuxel on the Astro Slide 5G Transformer — Requirements & Bring-Up Plan

**Status:** planning / bring-up requirements document
**Target device:** Planet Computers Astro Slide 5G Transformer
**SoC:** MediaTek MT6873 (Dimensity 800)
**Nuxel version context:** v0.2.0 (design scaffold + code prototype; **nothing is flashable to hardware yet**, including the primary Pixel 10 Pro XL target)

---

## 1. Purpose

This document is the single source of truth for what must be created, extracted,
downloaded, and wired together before Nuxel can be *test-flashed* to the
**Astro Slide 5G** instead of the daily-driver **Google Pixel 10 Pro XL**.

It is deliberately honest: the current repository is a **mustang-only** scaffold,
and mustang itself is still aspirational (no real boot image set, no verified
flash). Porting to the Astro Slide is **not** a rename — it is a second,
substantially different hardware bring-up because the two devices have a
completely different SoC, kernel base, boot chain, partition model, and
firmware/driver stack.

The companion file **`./nuxel-astro-slide.md`** contains the ready-to-use
implementation prompt for the build agent.

---

## 2. Why the Astro Slide is the right first test device (and not the Galaxy S22 Ultra)

| Factor | Astro Slide 5G | Samsung Galaxy S22 Ultra |
|---|---|---|
| Bootloader unlock | Standard `fastboot flashing unlock` after OEM unlock (community-confirmed on OESF/XDA) | Knox / RMM / KG prenormal; tripping the fuse is irreversible and can permanently disable some features |
| Stock fallback | Virtual A/B slots — keep stock Android+Magisk on **slot A**, test Nuxel on **slot B** | Knox-tainted, A/B available but warranty/fuse state already compromised on the user's unit |
| Community Linux precedent | Gemian (Planet's Debian-based Linux) packaging branch exists for the same 4.14 BSP kernel | Heavily locked, less community Linux precedent |
| Unbrick safety | Fastboot + MediaTek SP Flash Tool / MTK Client recovery paths exist | Knox/EDL recovery is harder and more opaque |
| Risk to main phone | Zero — it is a spare device | Same (it is a spare), but the Knox state is already damaged |

**Recommendation:** use the Astro Slide. Keep **slot A** as stock Android+Magisk
as the permanent fallback and do all Nuxel work on **slot B**.

---

## 3. Current codebase reality check (from the deep-analyze)

The repository is a clean but **not-yet-flashable** Linux phone OS scaffold:

- **Kernel:** `kernel/build-kernel.sh` builds the *public* GKI `android16-6.12`
  common kernel and merges `kernel/defconfig`. The authoritative `gs501_defconfig`
  lives in a **private** Google vendor tree (`android-gs-mustang-6.12`) that is
  not anonymously fetchable.
- **Boot:** `images/build.sh` produces either a generic `NUXELBOOT1` bundle or
  an Android boot header v4 (`ANDROID!`) **only when** `Image.gz` + DTB are
  present. `boot/flash.sh` is mustang-specific (Google ABL, `vendor_boot`,
  `init_boot`, `vbmeta`, `fastbootd` super flashing).
- **Firmware:** `firmware/manifest.yml` + `install-firmware.sh` +
  `verify-firmware.sh` are **mustang-only** (Exynos 5500 modem, BCM4390 WiFi/BT,
  PowerVR DXT GPU, Samsung AMB655X panel, Cirrus audio, etc.).
- **Device:** `device/deviceinfo` + `device/APKBUILD` are mustang-only.
- **Rootfs:** `images/mkrootfs.sh` builds a Flatpak/Phosh userspace and an
  ext4 `system.img`; it is device-agnostic in userspace terms but assumes
  `system_a`/`system_b` + dm-verity + AVB.

**Consequence:** the Astro Slide bring-up is a *new kernel tree + new device
package + new firmware manifest + new boot/flash scripts*, sharing only the
device-agnostic userspace (services, shell, PWA, configs).

---

## 4. Astro Slide 5G hardware profile (verified)

| Component | Astro Slide 5G value | Source |
|---|---|---|
| Device | Planet Computers Astro Slide 5G Transformer | Planet Computers / reviews |
| SoC | MediaTek **MT6873** (Dimensity 800) — 4× Cortex-A76 + 4× Cortex-A55 | TechRadar / community kernel |
| GPU | Mali-G57 MC4 (Valhall) | MediaTek MT6873 spec |
| RAM | 8 GB LPDDR4X | Planet / reviews |
| Storage | 128 GB eMMC/UFS + microSD | Planet / reviews |
| Display | 6.39" AMOLED FHD+ (2340×1080) | Planet / ZDNet |
| Connectivity | MediaTek **MT6635** combo (WiFi 5 / BT / GPS / FM) | `fayep/astro-modules` (`CFG_FM_CHIP=mt6635`) |
| Modem | Integrated MediaTek 5G modem (Dimensity 800) | TechRadar |
| OS (shipped) | Android 11 | Planet / community |
| Kernel (shipped BSP) | **4.14.186 AOSP BSP** | `fayep/astro-modules` |
| Boot model | **Virtual A/B (VAB)** dynamic partitions, `super` 6 GB | `fayep/astro-modules` `docs/flashing.md` |
| Boot image | Android boot image (legacy header, 2048-byte page): kernel + ramdisk + recovery DTBO + DTB | `fayep/astro-modules` `pack-boot.sh` |

Community resources (authoritative for this work):

- `https://github.com/fayep/astro-modules` — clean-room MT6873 kernel modules
  (`wmt_chrdev_wifi`, `bt_drv`, `scalpel`), Docker `astro-kbuild` build env,
  `build.sh`, `pack-boot.sh`, and `docs/flashing.md`.
- `https://github.com/fayep/astro-linux-kernel-4.14` — downstream Astro 4.14
  kernel source. Branches: `android-11.0`, `android-12.0`, `main`,
  `our-wifi-work`, and **`packaging`** (Gemian / Debian userspace).
- `https://github.com/planet-community/planet-devices` — Planet device community
  repository (issues, feature requests, root/flash documentation).
- postmarketOS has **no Astro Slide port** (only `planet-geminipda` and
  `planet-cosmocom`), so there is no drop-in mainline device package.

---

## 5. Core gap analysis: Pixel 10 Pro XL (mustang) vs Astro Slide 5G

| Dimension | Pixel 10 Pro XL (mustang) | Astro Slide 5G |
|---|---|---|
| Kernel base | Linux 6.12 LTS (GKI) | **4.14.186 downstream MediaTek BSP** |
| Mainline support | Partial; vendor gs501 tree is private | **Essentially none for MT6873**; must use downstream BSP |
| Boot chain | Boot ROM → Titan M3 → Google ABL → Linux + AVB/dm-verity | MediaTek preloader → LK bootloader → Linux (no Titan M3, no Google AVB) |
| Boot image format | Boot header v4 + `vendor_boot` + `init_boot` + `vbmeta` | Legacy Android boot image (PAGE 2048) with kernel/ramdisk/recovery-DTBO/DTB |
| Partition model | Full A/B GPT + `super` dynamic partitions | **Virtual A/B (VAB)**: physical `boot_a`/`boot_b`, logical `system`/`vendor`/`product` inside `super`, B slot = COW |
| Verified boot | AVB 2.0 + Titan M3 | LK verified boot (AVB v2 for VAB) — keep slot A stock to avoid brick |
| GPU | PowerVR DXT-72-2304 (vendor only) | Mali-G57 MC4 (Valhall; mainline Panfrost exists in modern kernels, but **not** in 4.14 BSP → vendor mali_kbase + libmali userspace) |
| Display | Samsung AMB655X 3120×1440@120 | 2340×1080 AMOLED, MediaTek DSI/DRM downstream |
| Touch | Samsung S6SY791 | **Unknown controller — must be read from a real device** (downstream MTK touch driver) |
| Modem | Samsung Exynos 5500 (PCIe/MHI) | **Integrated MT6873 modem** via MediaTek CCCI/Rild; **no upstream ModemManager plugin** |
| WiFi/BT | Broadcom BCM4390 (brcmfmac) | **MediaTek MT6635 combo** via proprietary `wmt_drv`/`wlan_drv_gen4m`/`bt_drv` stack |
| Audio | Cirrus CS35L45 + CS42L43 | **Unknown codec — must be read from a real device** (downstream MTK ASoC) |
| NFC / camera / sensors | Various Pixel components | Unknown until real device `getprop`/dmesg |

**Bottom line:** the Astro Slide cannot run the existing Nuxel 6.12 kernel or
its mustang drivers. It needs its **own downstream 4.14 kernel**, **own device
tree**, **own vendor firmware**, and **own boot/flash path**. The device-agnostic
Nuxel userspace (Phosh, GTK4/PWA, services, sandbox) can be reused *on top of*
that kernel.

---

## 6. What is needed to make Nuxel work on the Astro Slide

### 6.1 Firmware / proprietary blobs (per-device, never shared with mustang)

Extract from the Astro Slide's **stock vendor partition** (do **not** reuse any
Pixel blobs):

| Blob area | Expected contents | Linux consumers |
|---|---|---|
| MediaTek connectivity (`MT6635`) | `wmt_drv.ko`, `wlan_drv_gen4m.ko`, `bt_drv.ko`, `fmradio_drv.ko`, NVRAM/calibration files | vendor `wmt`/`wlan` stack (or clean-room replacements) |
| GPU Mali | `mali_kbase.ko` / `libmali` userspace (GLES/EGL/Vulkan), `gpufreq`/`ged` blobs | vendor Mali driver + Wayland EGL |
| Display | panel init / MIPI DSI sequences, `lcm` params | MediaTek DRM/DSI driver + DT |
| Touch | touch firmware/calibration | downstream touch driver |
| Audio | codec/DSP firmware | downstream ASoC |
| Camera | ISP/cam `dummy_pcm`/sensor calibration | downstream v4l2/ISP |
| Sensor hub / IMU / ALS | firmware blobs | downstream drivers |
| NFC (if present) | controller firmware | downstream NFC driver |
| Modem | MT6873 modem/md1image/CCCI firmware | MediaTek modem stack |

Acquisition: pull the stock firmware package from Planet Computers, or dump from
the device (`adb shell` + `dd`/`tar` of `/vendor/firmware`, `/vendor/lib/modules`,
and `by-name` modem partitions). The exact source must be documented per blob
(like the existing mustang `firmware/manifest.yml`).

### 6.2 Kernel (per-device)

- Use the **downstream MediaTek MT6873 4.14.186 BSP** (`fayep/astro-linux-kernel-4.14`
  or Planet's own GPL kernel source).
- Add a Nuxel Astro defconfig fragment (not the mustang `kernel/defconfig`).
- Port the Nuxel features (the `drivers/nuxel/` patch, hardening Kconfigs) onto
  the 4.14 tree **only where they compile** — do not assume 6.12 symbols exist.
- Keep the vendor MTK display/GPU/modem/connectivity/audio drivers enabled.
- Build with clang-11 (the community build uses `CC=clang-11`) or the MTK
  recommended toolchain, not the 6.12 GKI clang baseline.

### 6.3 Device tree (per-device)

- Obtain/keep the MT6873 Astro DTS/DTSI from the downstream kernel.
- Create `nuxel.astro.*` DTBO or boot DTB modifications for: chosen bootargs,
  console (UART), display/touch nodes, and Nuxel boot param.
- Do **not** use mustang DTBs on Astro (different `compatible`, different SoC).

### 6.4 Boot chain & flash tooling (per-device)

- **Boot image format:** legacy Android boot image (2048-byte page) with
  kernel + ramdisk + recovery DTBO + DTB. The existing `images/bootpack/mkbootimg.py`
  (v4) is **not** the right format — add an Astro-specific packer modeled on
  `fayep/astro-modules/pack-boot.sh` (or use `mkbootimg` v0 with `--pagesize 2048`).
- **Flash sequence** (from `fayep/astro-modules/docs/flashing.md`):

  ```sh
  fastboot reboot fastboot
  fastboot resize-logical-partition system_b-cow 1   # free super space
  fastboot flash vendor_b vendor_b.img
  fastboot flash boot_b boot_b_<nuxel>.img
  fastboot reboot-bootloader
  fastboot set_active b
  fastboot reboot
  ```

- **Never** `set_active` from fastbootd — only from the bootloader.
- Slot A remains stock Android+Magisk as the fallback.
- Additional recovery tools: `adb`, `fastboot`, MediaTek **SP Flash Tool** /
  **MTK Client** (for preloader/DA-level recovery), and a USB-C data cable.

### 6.5 Drivers matrix (Astro-specific status)

| Subsystem | Astro driver reality | Nuxel action |
|---|---|---|
| GPU | vendor `mali_kbase` + `libmali` (4.14) | Bundle vendor Mali userspace; fallback to fbdev/software llvmpipe for first boot |
| Display | MTK DRM/DSI downstream | Keep enabled; bring up panel via DT; `wlr-randr` 2340×1080 |
| Touch | downstream MTK touch (controller TBD) | Identify via `getevent`/dmesg; write libinput calibration |
| WiFi | proprietary `wlan_drv_gen4m` + `wmt_chrdev_wifi` (clean-room) | Use vendor module or clean-room `wmt_chrdev_wifi`; firmware from device |
| Bluetooth | proprietary `bt_drv` / MTK stack | Use vendor or clean-room `bt_drv` |
| Modem | MTK CCCI/Rild | **Not ModemManager-ready**; Phase-1 target is data/WiFi, not voice/SMS |
| Audio | downstream MTK ASoC + codec (TBD) | Identify codec; UCM2 profile per device |
| Sensors/NFC/camera | downstream MTK | Map after real-device inspection |

### 6.6 Userspace (device-agnostic, reusable)

- Phosh + phoc (Wayland), GTK4/libadwaita native apps, PWA launcher, nuxel
  services (bridge/portal/notifications), sandbox configs, hardened_malloc.
- For the Astro, first boot can use a minimal **initramfs → debug shell** to
  validate kernel/display, then the full Phosh rootfs.
- Optionally model on **Gemian** (Planet's Debian) for proven Astro userspace
  integration points (keyboard, suspend, charging), without importing Android HAL.

---

## 7. Mandatory per-device directory separation (anti-cross-flash)

The single most important safety rule: **every device-specific artifact lives
under a per-device directory and is selected by a device key.** No shared
top-level device file may contain both device's data.

Proposed canonical layout (the agent implements this):

```
firmware/
  google-pixel-10-pro-xl/          # key: mustang
    manifest.yml
    install-firmware.sh
    verify-firmware.sh
    blobs/                         # extracted at build time (gitignored)
  astro-slide/                     # key: astro
    manifest.yml
    install-firmware.sh
    verify-firmware.sh
    blobs/                         # extracted at build time (gitignored)

kernel/
  google-pixel-10-pro-xl/
    defconfig                      # moved from kernel/defconfig (gs501 fragment)
    patches/                       # moved from kernel/patches/
    README-toolchain.md
  astro-slide/
    defconfig                      # MT6873 4.14 fragment
    patches/
    README-toolchain.md

device/
  google-pixel-10-pro-xl/
    deviceinfo                     # moved from device/deviceinfo
    APKBUILD
    90-nuxel-mustang.rules
    nuxel-mustang.conf
  astro-slide/
    deviceinfo                     # new MT6873 deviceinfo
    APKBUILD
    90-nuxel-astro.rules
    nuxel-astro.conf

boot/
  google-pixel-10-pro-xl/
    flash.sh                       # moved/adapted from boot/flash.sh
    recovery.sh
    boot-config.txt
  astro-slide/
    flash.sh                       # new VAB fastboot flow
    recovery.sh
    boot-config.txt
    pack-boot.sh                   # legacy boot image packer (PAGE 2048)

configs/
  google-pixel-10-pro-xl/          # display, libinput, alsa-ucm, modem, ...
  astro-slide/                     # display, libinput, alsa-ucm, modem, ...

images/
  google-pixel-10-pro-xl/          # build.sh, mkrootfs.sh, avb, rauc, ...
  astro-slide/                     # build.sh (Astro boot/vendor build), ...

tools/                             # SHARED, device-agnostic only
  sign-image.sh gen-keys.sh dedupe-assets.sh ...

device-selection (shared): a single NUXEL_DEVICE / --device switch resolves the
per-device dir above. Default must be explicit; never silently guess.
```

Device keys:

- `mustang` / `google-pixel-10-pro-xl` → Google Pixel 10 Pro XL
- `astro` / `astro-slide` → Planet Computers Astro Slide 5G

`nuxel.device=` on the kernel cmdline must match the selected key, and each
flash script must verify the connected device (`fastboot getvar product`) before
flashing and refuse on mismatch.

---

## 8. Safety / anti-brick rules

1. **Slot A stays stock Android+Magisk on the Astro.** All Nuxel work targets
   slot B. Fallback = `fastboot set_active a && fastboot reboot`.
2. **Verify device identity before every flash.** For Astro, check
   `fastboot getvar product` / `getvar serial` and `getvar current-slot`.
3. **Never flash the wrong device's firmware/driver.** Enforce via the
   per-device directory + device-key gate in all scripts.
4. **Never touch `persist`/`nvdata`/`nvram`/`proinfo`/`seccfg`/`tee`** — these
   hold per-unit calibration (IMEI, MAC, calibration data). Astro: protect
   `nvdata`, `nvram`, `proinfo`, `persist`, `tee`, `md1img`-adjacent calibration.
5. **Back up the full stock firmware before the first flash.**
6. **`fastboot resize-logical-partition system_b-cow 1` only while running on
   slot A** (it is safe to destroy slot B COW from slot A; never destroy A from B).
7. Do **not** relock the Astro bootloader while testing. Leave `unlocked: yes`.

---

## 9. Prerequisites the operator must provide (not automatable)

1. A working Astro Slide 5G with **OEM unlock enabled** and **USB debugging** on.
2. A USB-C data cable + a Linux/macOS host with `adb` and `fastboot`
   (platform-tools ≥ 34).
3. The **stock Astro firmware/OTP package** (from Planet or a dumped copy) for
   firmware extraction and recovery.
4. A serial/UART access point is *optional but recommended* (MTK UART) for early
   boot logs.
5. Enough battery (> 60%).

Bootloader unlock (community-confirmed):

```sh
adb reboot bootloader
fastboot flashing unlock      # wipes device; confirm on screen
```

---

## 10. Phased Astro bring-up plan

| Phase | Goal | Exit criteria |
|---|---|---|
| 0 | Inventory the real device | `fastboot getvar all`, `getprop`, `dmesg`, `getevent`, `lsmod`, `/vendor/firmware` dumped; touch/audio/NFC/sensor/camera controllers identified |
| 1 | Boot the **stock 4.14 kernel** on slot B with Nuxel initramfs (debug shell) | Serial/display console alive; `nuxel.device=astro` present |
| 2 | Bring up display + touch | Phosh launches at 2340×1080; touch calibrated |
| 3 | Bring up WiFi/BT | `wlan0` up, `bluetoothctl` sees controller |
| 4 | Bring up GPU | Hardware GLES via vendor libmali, or explicit llvmpipe fallback |
| 5 | Bring up audio | Speaker + mic paths work via PipeWire/UCM |
| 6 | Userspace hardening | AppArmor, nftables, hardened_malloc, sandbox verified |
| 7 | Modem/camera (stretch) | Data path first; voice/SMS only if MTK modem stack becomes viable |

**Phase 0 is the immediate blocker** — several Astro component IDs are unknown
and must be collected from the physical device before the device package and
firmware manifest can be completed accurately.

---

## 11. Open questions to resolve on a real device

- Exact touchscreen controller and I2C/SPI address.
- Exact audio codec and routing.
- Exact display panel LCM name/DDIC.
- Camera sensor list and ISP path.
- Whether NFC is present and its controller.
- Sensor hub (accelerometer/gyro/ALS/proximity) component list.
- Modem interface exposed to userspace (and whether a usable AT/QMI/MBIM path exists).
- Whether the `packaging` (Gemian) branch already carries a bootable Debian rootfs
  we can adapt instead of building from scratch.

---

## 12. References

- Repo deep-analyze files: `README.md`, `QUICKSTART.md`, `kernel/build-kernel.sh`,
  `kernel/defconfig`, `images/build.sh`, `boot/flash.sh`, `device/deviceinfo`,
  `firmware/manifest.yml`, `docs/driver-status.md`, `docs/hardware-bringup-prep.md`.
- Astro community kernel/modules: https://github.com/fayep/astro-modules
- Astro downstream 4.14 kernel: https://github.com/fayep/astro-linux-kernel-4.14
- Planet device community: https://github.com/planet-community/planet-devices
- postmarketOS device list (no Astro Slide port): https://wiki.postmarketos.org/wiki/Devices
