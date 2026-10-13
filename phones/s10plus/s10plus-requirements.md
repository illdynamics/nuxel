# Nuxel on the Samsung Galaxy S10+ (Exynos) — Requirements & Bring-Up Plan

**Status:** planning / bring-up requirements document
**Target device:** Samsung Galaxy S10+ (SM-G975F, Exynos 9820)
**Codename:** `beyond2lte`
**Nuxel version context:** v0.2.0 (design scaffold + code prototype; **nothing is flashable to hardware yet**, including the primary Pixel 10 Pro XL target)

---

## 1. Purpose

This document is the single source of truth for what must be created, extracted,
downloaded, and wired together before Nuxel can be *test-flashed* to the
**Samsung Galaxy S10+** instead of the daily-driver **Google Pixel 10 Pro XL**.

It is deliberately honest: the current repository is a **mustang-only** scaffold,
and mustang itself is still aspirational (no real boot image set, no verified
flash). Porting to the S10+ is **not** a rename — it is a second, substantially
different hardware bring-up because the S10+ has a completely different SoC,
kernel base, boot chain, partition model, flash tooling, and firmware/driver
stack.

The companion file **`./nuxel-s10plus.md`** contains the ready-to-use
implementation prompt for the build agent.

---

## 2. Why the S10+ is the right first test device (and not the S22 Ultra / Astro Slide)

| Factor | Samsung Galaxy S10+ (Exynos) | Samsung Galaxy S22 Ultra | Astro Slide 5G |
|---|---|---|---|
| Bootloader state | **Already unlocked** — TWRP is installed, so OEM unlock is already done | Knox / RMM / KG prenormal; unlock is risky | Standard `fastboot flashing unlock` |
| Recovery already present | **Yes — TWRP (beyond2lte)**; usable today to sideload/push images | No custom recovery on the unit | None (stock only) |
| Flash tooling | TWRP (ADB sideload + `dd`) + **Odin / `heimdall`** (Download Mode) | Odin / heimdall | `fastboot` (VAB) |
| Community Linux precedent | **postmarketOS `samsung-exynos9820` generic port** (beyond0lte/beyond1lte/beyond2lte) | Weak (Exynos 2200, near-zero mainline) | `fayep/astro-modules` (MediaTek) |
| Mainline kernel | **Yes — close-to-mainline `linux-postmarketos-exynos9820`** | No | No (downstream 4.14 only) |
| Unbrick safety | TWRP + Download Mode + Odin flash of stock BL/AP/CP/CSC | Knox/EDL recovery is opaque | MTK SP Flash Tool / MTK Client |
| Risk to main phone | Zero — spare device, already "tainted" | Same, but Knox state is a liability | Zero (spare) |

**Recommendation:** use the S10+. The single biggest asset is that **TWRP is
already installed**, which means the bootloader is already unlocked and we have a
working custom recovery to push test kernels/rootfs images. There is a
production-quality postmarketOS port for this exact SoC to build on.

> **Honest note on "Knox didn't wh00p its ass":** having TWRP installed means
> the Knox e-fuse has **already been tripped** (irreversible) — that is exactly
> what unlocking the bootloader does on a Samsung Exynos device. The good news
> is this is the *ideal* state for our purposes: the device is **not bricked**,
> the bootloop is on the Android side only, and TWRP + Download Mode give us a
> full, known-good recovery path. Samsung Pay / Secure Folder / Knox features
> are permanently gone on this unit — which we do not need anyway.

---

## 3. Current codebase reality check (from the deep-analyze)

The repository is a clean but **not-yet-flashable** Linux phone OS scaffold:

- **Kernel:** `kernel/build-kernel.sh` builds the *public* GKI `android16-6.12`
  common kernel and merges `kernel/defconfig`. The authoritative `gs501_defconfig`
  lives in a **private** Google vendor tree (`android-gs-mustang-6.12`).
- **Boot:** `images/build.sh` produces a generic `NUXELBOOT1` bundle or an
  Android boot header v4 (`ANDROID!`) only when `Image.gz` + DTB are present.
  `boot/flash.sh` is mustang-specific (Google ABL, `vendor_boot`, `init_boot`,
  `vbmeta`, `fastbootd` super flashing).
- **Firmware:** `firmware/manifest.yml` + `install-firmware.sh` +
  `verify-firmware.sh` are mustang-only (Exynos 5500 modem, BCM4390 WiFi/BT,
  PowerVR DXT GPU, Samsung AMB655X panel, Cirrus audio, etc.).
- **Device:** `device/deviceinfo` + `device/APKBUILD` are mustang-only.
- **Rootfs:** `images/mkrootfs.sh` builds a Flatpak/Phosh userspace + ext4
  `system.img`; device-agnostic in userspace terms but assumes
  `system_a`/`system_b` + dm-verity + AVB.
- **Boot packers:** `images/bootpack/mkbootimg.py` implements only Android boot
  header **v3/v4**. The S10+ needs **v1** (legacy header, kernel + ramdisk,
  page 2048).

**Consequence:** the S10+ bring-up is a *new kernel tree + new device package +
new firmware manifest + new boot/flash scripts*, sharing only the
device-agnostic userspace (services, shell, PWA, configs).

---

## 4. Samsung Galaxy S10+ hardware profile (verified)

| Component | S10+ (SM-G975F) value | Source |
|---|---|---|
| Device | Samsung Galaxy S10+ (Exynos) | postmarketOS `samsung-beyond2lte` |
| Codename | `beyond2lte` | postmarketOS / TWRP |
| SoC | Samsung **Exynos 9820** (2× Mongoose M4 + 2× Cortex-A75 + 4× Cortex-A55, 8 nm) | postmarketOS `samsung-exynos9820` |
| GPU | Mali-G76 MP12 (Bifrost) | Exynos 9820 spec |
| RAM | 8 GB LPDDR4X | Samsung / reviews |
| Storage | 128/512 GB/1 TB **UFS 2.1** (`/dev/block/platform/13d60000.ufs`) | postmarketOS page |
| Display | 6.4" Dynamic AMOLED, **3040×1440**, 19:9, HDR10+ (DDIC **S6E3HA9**) | Samsung / reviews + DTS |
| Touch | Samsung **S6SY761**-series (`sec_ts`, firmware `y771`/`y771_d`, I2C @ 0x48, FOD) | beyond2lte DTS (`input_common`) |
| WiFi/BT | Broadcom **BCM4375** (Wi-Fi 6 / 802.11ax, BT 5.0) | beyond2lte DTS (`samsung,brcm-wlan`) + teardown |
| Modem | Integrated Samsung **Shannon LTE modem** (Exynos 9820, Cat 20, no 5G) | Exynos 9820 spec |
| NFC | Samsung `sec-nfc` (S3FWRN5-family, I2C @ 0x27) + embedded SE | beyond2lte DTS |
| Audio | Cirrus Logic **CS47L93** codec + **2× CS35L40** speaker amps | beyond2lte DTS |
| Battery | 4100 mAh, 15 W wired / 12–15 W wireless | Samsung |
| Shipped OS | Android 9 (One UI), upgradable to Android 12 | Samsung |
| Shipped kernel | Samsung **4.14.x downstream** (Exynos 9820 BSP) | Samsung OSRC |
| Boot model | **A-only** (no A/B slots); `boot`, `recovery`, `system`, `vendor`, `product` as separate partitions | Samsung partition table |
| Boot image | Legacy Android boot image (header **v1**, page 2048) | Samsung / pmOS U-Boot notes |
| Flash tooling | **No `fastboot`** — uses **Download Mode** (Odin/`heimdall`) + **TWRP** | postmarketOS `samsung-exynos9820` |

### Community resources (authoritative for this work)

- **postmarketOS generic Exynos 9820 port** — device package
  `device-samsung-exynos9820`, kernel `linux-postmarketos-exynos9820`,
  "close-to-mainline". Covers S10e (`beyond0lte`), S10 (`beyond1lte`),
  S10+ (`beyond2lte`).
  Wiki: `https://wiki.postmarketos.org/wiki/Samsung_Exynos_9820_(samsung-exynos9820)`
- **Custom U-Boot fork** (secondary bootloader that boots a mainline kernel via
  EFI, since S-Boot cannot): `https://github.com/chiffathefox/u-boot` branch
  `exynos9820` (`exynos9820_defconfig`).
- **TWRP for beyond2lte:** `https://twrp.me/samsung/samsunggalaxys10plus.html`
- **Samsung open-source release center (Exynos 9820 kernel):**
  `https://opensource.samsung.com` (search SM-G975F).

### Key boot-chain fact (S10+ / Exynos 9820)

Samsung's **S-Boot** initializes CPU, DRAM, UFS and the display, but it **ignores
the kernel cmdline and boot offset from `boot.img`** and **does not accept
mainline-compatible device trees**. postmarketOS therefore treats S-Boot as the
primary bootloader and **chainloads a custom U-Boot** (`chiffathefox/u-boot`,
`exynos9820` branch) which then boots the mainline kernel via EFI. This is the
proven path and the one Nuxel must adopt — a mainline kernel cannot be booted
directly by S-Boot.

---

## 5. Core gap analysis: Pixel 10 Pro XL (mustang) vs Galaxy S10+ (beyond2lte)

| Dimension | Pixel 10 Pro XL (mustang) | Galaxy S10+ (beyond2lte) |
|---|---|---|
| Kernel base | Linux 6.12 LTS (GKI) | Samsung **4.14 downstream** → `linux-postmarketos-exynos9820` (close-to-mainline) |
| Mainline support | Partial; vendor gs501 tree is private | **Yes** — postmarketOS exynos9820 port exists |
| Boot chain | Boot ROM → Titan M3 → Google ABL → Linux + AVB | Boot ROM → S-Boot → **custom U-Boot (EFI)** → mainline Linux |
| Boot image format | Header **v4** + `vendor_boot` + `init_boot` + `vbmeta` | Header **v1** (legacy), kernel + ramdisk, page 2048 |
| Partition model | Full A/B GPT + `super` dynamic partitions | **A-only**; separate `boot`/`recovery`/`system`/`vendor`/`product` |
| Verified boot | AVB 2.0 + Titan M3 | Samsung Knox (already tripped) — no AVB enforcement to fight |
| Flash tooling | `fastboot` + `fastbootd` | **TWRP (`adb` + `dd`) + Odin/`heimdall` (Download Mode)** — no `fastboot` |
| GPU | PowerVR DXT (vendor only) | Mali-G76 MP12 → mainline **Panfrost** (Bifrost) |
| Display | Samsung AMB655X 3120×1440@120 | 3040×1440 AMOLED, downstream Samsung DRM/DSI (exynos9820) |
| Touch | Samsung S6SY791 | Samsung S6SY761 (`sec_ts`) |
| Modem | Samsung Exynos 5500 (PCIe/MHI) | Integrated Shannon LTE — **no upstream ModemManager plugin** |
| WiFi/BT | Broadcom BCM4390 (brcmfmac) | Broadcom BCM4375 (brcmfmac/cywd) |
| Audio | Cirrus CS35L45 + CS42L43 | Cirrus CS47L93 + 2× CS35L40 |
| NFC / sensors / camera | Various Pixel components | Samsung sec-nfc (S3FWRN5) + ST/Samsung sensors; camera TBD |

**Bottom line:** the S10+ cannot run the existing Nuxel 6.12 kernel or mustang
drivers. It needs its **own exynos9820 kernel**, **own device tree**, **own
vendor firmware**, **own U-Boot + TWRP/Odin flash path**. The device-agnostic
Nuxel userspace (Phosh, GTK4/PWA, services, sandbox) can be reused *on top of*
that kernel — and the postmarketOS exynos9820 port gives us a working,
upstream-adjacent base to start from.

---

## 6. What is needed to make Nuxel work on the S10+

### 6.1 Firmware / proprietary blobs (per-device, never shared with mustang)

Extract from the S10+'s **stock `vendor`/`system` partition** (via TWRP `adb
pull`/`tar` or the Samsung firmware package). Do **not** reuse any Pixel blobs.

| Blob area | Expected contents | Linux consumers |
|---|---|---|
| GPU Mali-G76 | `libmali`/`mali_kbase` userspace (GLES/EGL/Vulkan) | Panfrost (preferred) or vendor Mali + Wayland EGL |
| Display | panel init / MIPI DSI sequences | exynos9820 DRM/DSI driver + DT |
| Touch | S6SY761 firmware `y771`/`y771_d` (`tsp_sec/`) | sec_ts driver |
| Audio | CS47L93 + CS35L40 DSP/firmware | downstream ASoC / madera codec |
| WiFi/BT | BCM4375 `.bin`/`.hcd`/`.clm_blob` + NVRAM | brcmfmac/cywd + bluetooth |
| Modem | Shannon CP/modem + calibration (protect EFS!) | Samsung modem stack (Phase-late) |
| NFC / sensors / camera | controller/sensor firmware | downstream drivers |

Acquisition: `adb pull`/`dd` from TWRP (the device is already in TWRP) of
`/vendor/firmware`, `/vendor/lib/modules`, `/vendor/etc/firmware`, and
`/system/lib64` GPU blobs — or extract from the Samsung **AP** (and **BL/CP/CSC**)
firmware tarballs via Odin/`heimdall`. Document every blob source in the new
`firmware/s10plus/manifest.yml`.

### 6.2 Kernel (per-device)

- Use **`linux-postmarketos-exynos9820`** (close-to-mainline, from pmOS) as the
  Nuxel S10+ kernel base — **not** the 6.12 GKI mustang kernel.
- Add a Nuxel S10+ defconfig fragment (`kernel/s10plus/defconfig`), not the
  mustang `kernel/defconfig`.
- Port the Nuxel `drivers/nuxel/` patch + hardening Kconfigs onto the exynos9820
  tree **only where they compile** (do not assume 6.12 symbols).
- Enable Panfrost for Mali-G76, exynos9820 DRM/DSI, brcmfmac/cywd, madera
  audio, ext4/f2fs, namespaces/seccomp/AppArmor where the tree supports them.
- Build with a `aarch64-linux-gnu-` toolchain (or clang); the pmOS U-Boot uses
  `aarch64-linux-gnu-gcc-10`.

### 6.3 Device tree (per-device)

- Obtain the exynos9820/beyond2lte DTS from the pmOS kernel tree.
- Create `nuxel.beyond2lte.*` modifications for: chosen bootargs, console (UART),
  display/touch nodes, `nuxel.device=s10plus` boot param, and UFS root.
- Do **not** use mustang DTBs on the S10+ (different `compatible`, different SoC).

### 6.4 Boot chain & flash tooling (per-device)

- **Boot image format:** legacy Android boot image header **v1** (page 2048).
  The existing `images/bootpack/mkbootimg.py` (v3/v4) is **not** the right
  format — add an S10+-specific v1 packer (or use AOSP `mkbootimg` v1).
- **Chainload U-Boot** (`chiffathefox/u-boot` `exynos9820`): build with
  `exynos9820_defconfig`, wrap as `boot.img` via `mkbootimg --kernel u-boot.bin`,
  and `dd` it to `/dev/block/platform/13d60000.ufs/by-name/boot` from TWRP.
- **Flash sequence** (pmOS-proven, via TWRP):
  ```sh
  adb reboot recovery                 # or Vol Up + Bixby + Power
  adb push u-boot-boot.img /tmp
  adb shell dd if=/tmp/u-boot-boot.img of=/dev/block/platform/13d60000.ufs/by-name/boot
  adb push samsung-exynos9820-rootfs.img /tmp
  adb shell dd if=/tmp/samsung-exynos9820-rootfs.img of=/dev/block/platform/13d60000.ufs/by-name/userdata
  adb shell twrp reboot
  ```
  Alternative: `pmbootstrap install --android-recovery-zip --recovery-install-partition data` + TWRP **ADB Sideload**.
- **No `fastboot`.** Host tools: `adb`, `heimdall`/Odin (for Download Mode
  recovery and stock re-flash), and `TWRP`.
- Recovery path to stock: Odin/`heimdall` flash of the four Samsung firmware
  components (BL, AP, CP, CSC) in Download Mode.

### 6.5 Drivers matrix (S10+-specific status)

| Subsystem | S10+ driver reality | Nuxel action |
|---|---|---|
| GPU | Mali-G76 MP12; Panfrost (mainline Bifrost) | Prefer Panfrost; vendor libmali fallback; llvmpipe for first boot |
| Display | exynos9820 DRM/DSI (pmOS port) | Bring up panel via DT; `wlr-randr` 3040×1440 |
| Touch | Samsung S6SY761 (`sec_ts`) | Enable sec_ts; libinput calibration |
| WiFi | BCM4375 brcmfmac/cywd | Firmware from device; mainline brcmfmac/cywd |
| Bluetooth | BCM4375 (BT 5.0) | hci_uart/btbcm + `.hcd` from device |
| Modem | Shannon LTE (integrated) | **Not ModemManager-ready**; Phase-1 target is data/WiFi |
| Audio | CS47L93 + 2× CS35L40 (madera ASoC) | UCM2 profile per device |
| NFC / sensors / camera | downstream | Map after real-device inventory |

### 6.6 Userspace (device-agnostic, reusable)

- Phosh + phoc (Wayland), GTK4/libadwaita native apps, PWA launcher, nuxel
  services (bridge/portal/notifications), sandbox configs, hardened_malloc.
- First boot can use a minimal **initramfs → debug shell** (via TWRP/U-Boot) to
  validate kernel/display, then the full Phosh rootfs.

---

## 7. Mandatory per-device directory separation (anti-cross-flash)

The single most important safety rule: **every device-specific artifact lives
under a per-device directory and is selected by a device key.** No shared
top-level device file may contain multiple devices' data.

Proposed canonical layout (the agent implements this):

```
firmware/
  google-pixel-10-pro-xl/          # key: mustang   (moved from firmware/*)
    manifest.yml install-firmware.sh verify-firmware.sh blobs/
  s10plus/                         # key: s10plus   (codename beyond2lte)
    manifest.yml install-firmware.sh verify-firmware.sh blobs/
  g7power/                         # key: g7power   (codename ocean)
    manifest.yml install-firmware.sh verify-firmware.sh blobs/

kernel/
  google-pixel-10-pro-xl/          # defconfig, patches/, README-toolchain.md
  s10plus/                         # defconfig, patches/, README-toolchain.md,
                                   # build-kernel.sh (exynos9820)
  g7power/                         # defconfig, patches/, README-toolchain.md,
                                   # build-kernel.sh (msm8953)

device/
  google-pixel-10-pro-xl/          # deviceinfo, APKBUILD, udev/modprobe
  s10plus/                         # deviceinfo (beyond2lte), APKBUILD, ...
  g7power/                         # deviceinfo (ocean), APKBUILD, ...

boot/
  google-pixel-10-pro-xl/          # flash.sh, recovery.sh, boot-config.txt
  s10plus/                         # flash.sh (TWRP/heimdall), recovery.sh,
                                   # pack-boot-v1.sh, uboot-chainload.sh
  g7power/                         # flash.sh (fastboot/lk2nd), recovery.sh,
                                   # pack-boot-v1.sh

configs/
  google-pixel-10-pro-xl/          # display, libinput, alsa-ucm, modem, ...
  s10plus/                         # display, libinput, alsa-ucm, modem, ...
  g7power/                         # display, libinput, alsa-ucm, modem, ...

images/
  google-pixel-10-pro-xl/          # build.sh, mkrootfs.sh, avb, rauc, ...
  s10plus/                         # build.sh (S10+ boot/vendor build), ...
  g7power/                         # build.sh (G7 Power boot/vendor build), ...

tools/                             # SHARED, device-agnostic only
  sign-image.sh gen-keys.sh dedupe-assets.sh ...

device-selection (shared): a single NUXEL_DEVICE / --device switch resolves the
per-device dir above. Default must be explicit; never silently guess.
```

Device keys:

- `mustang`  / `google-pixel-10-pro-xl` → Google Pixel 10 Pro XL
- `s10plus`  / `beyond2lte`             → Samsung Galaxy S10+ (Exynos)
- `g7power`  / `ocean`                  → Motorola Moto G7 Power

`nuxel.device=` on the kernel cmdline must match the selected key, and each
flash script must verify the connected device identity before flashing and
refuse on mismatch.

---

## 8. Safety / anti-brick rules

1. **TWRP and Download Mode are the safety nets.** The device is already
   unlocked; never relock the bootloader and never attempt to re-lock or
   restore Knox (impossible anyway).
2. **Verify device identity before every flash.** Check TWRP `/proc/cmdline`,
   `getprop ro.product.device` == `beyond2lte`, and `ro.product.name` ==
   `beyond2ltexx` (or the variant) before touching partitions.
3. **Never flash the wrong device's firmware/driver.** Enforce via the
   per-device directory + device-key gate in all scripts.
4. **Never touch `efs`, `efsg`, `persist`, `param`, `up_param`, `steady`,
   `keystorage`, `carrier`, `cp_debug`, `misc`** — these hold per-unit
   calibration (IMEI, MAC, DRK, Knox state, baseband calibration).
5. **Back up the full stock firmware + EFS before the first flash** (via TWRP
   full backup or `dd` of every `by-name` partition to external storage).
6. **The device is in a bootloop** — do **not** wipe partitions blindly; first
   inventory the partitions via TWRP (`adb shell ls /dev/block/platform/13d60000.ufs/by-name`).
7. **Do not relock the bootloader.** Leave `unlocked` / Knox-tripped as-is.

---

## 9. Prerequisites the operator must provide (not automatable)

1. The **S10+ (SM-G975F)** in TWRP, with a USB-C data cable and `adb` + `heimdall`
   on a Linux/macOS host (platform-tools ≥ 34).
2. The **stock Samsung firmware** (BL/AP/CP/CSC tarballs for SM-G975F, matching
   the current bootloader revision) for firmware extraction and Download-Mode
   recovery.
3. A **full TWRP backup** (or `dd` of every `by-name` partition) before any
   modification — especially `efs` and `persist`.
4. Optional but recommended: Samsung **Download Mode** (Vol Down + Bixby +
   Power) access confirmed, and Odin/`heimdall` verified working against the
   stock firmware.
5. Enough battery (> 60 %).

---

## 10. Phased S10+ bring-up plan

| Phase | Goal | Exit criteria |
|---|---|---|
| 0 | Inventory the real device via TWRP | `adb shell getprop`, `dmesg`, `getevent -pl`, `cat /proc/cmdline`, `ls by-name`, `/vendor/firmware` + `/vendor/lib/modules` dumped; touch/audio/NFC/panel/WiFi IDs confirmed against upstream DTS; camera + sensor inventory collected |
| 1 | Chainload U-Boot + boot the exynos9820 kernel with Nuxel initramfs (debug shell) | U-Boot runs; kernel boots; `nuxel.device=s10plus` present on console |
| 2 | Bring up display + touch | Phosh launches at 3040×1440; touch calibrated |
| 3 | Bring up WiFi/BT | `wlan0` up, `bluetoothctl` sees the BCM4375 controller |
| 4 | Bring up GPU | Panfrost GLES (or explicit llvmpipe fallback) |
| 5 | Bring up audio | Speaker + mic paths via PipeWire/UCM |
| 6 | Userspace hardening | AppArmor, nftables, hardened_malloc, sandbox verified |
| 7 | Modem/camera (stretch) | Data path first; voice/SMS only if Shannon stack becomes viable |

**Phase 0 is the immediate blocker** — touch/audio/NFC/panel/WiFi IDs are
now known from the upstream beyond2lte DTS, but the real firmware blobs, camera
sensors, and the sensor hub still must be collected from the physical device
(already in TWRP) before the device package and firmware manifest can be
completed accurately.

---

## 11. Open questions to resolve on the real device (via TWRP)

- ~~Touch controller~~ → **resolved: Samsung S6SY761 (`sec_ts`) @ I2C 0x48** (confirm on the unit).
- Audio codec/amps confirmed: CS47L93 + 2× CS35L40; exact UCM routing still to build.
- ~~Panel DDIC~~ → **resolved: Samsung S6E3HA9** (`s6e3ha9_beyond2`).
- Camera sensor list and ISP path.
- NFC confirmed: Samsung sec-nfc (S3FWRN5-family) @ I2C 0x27.
- Sensor hub (accelerometer/gyro/ALS/proximity) component list.
- WiFi chip confirmed: BCM4375; exact firmware filenames still needed.
- Whether the current bootloop still leaves `system`/`vendor` mountable for
  blob extraction, or whether extraction must come from the stock AP tarball.
- Current bootloader revision (to pick the matching stock firmware for recovery).

---

## 12. References

- Repo deep-analyze files: `README.md`, `QUICKSTART.md`, `kernel/build-kernel.sh`,
  `kernel/defconfig`, `images/build.sh`, `images/bootpack/mkbootimg.py`,
  `boot/flash.sh`, `device/deviceinfo`, `firmware/manifest.yml`,
  `docs/driver-status.md`, `docs/device-setup.md`, `boot/initramfs/init.sh`.
- postmarketOS Exynos 9820 port:
  https://wiki.postmarketos.org/wiki/Samsung_Exynos_9820_(samsung-exynos9820)
- postmarketOS S10+ device page:
  https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_(samsung-beyond2lte)
- Custom U-Boot fork: https://github.com/chiffathefox/u-boot (branch `exynos9820`)
- TWRP beyond2lte: https://twrp.me/samsung/samsunggalaxys10plus.html
- Samsung open-source kernel (Exynos 9820): https://opensource.samsung.com
