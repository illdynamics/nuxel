# Nuxel on the Google Pixel 10 Pro XL — Requirements & Bring-Up Plan

**Status:** primary-target reference / bring-up requirements document
**Target device:** Google Pixel 10 Pro XL (`mustang`)
**Codename:** `mustang`
**Device key:** `mustang` → directory `google-pixel-10-pro-xl`
**Reviewed serial:** `58211FDCQ001LA` | HW `MP1.0` | SKU `G45RY`
**Nuxel version context:** v0.2.0 (design scaffold + code prototype; **nothing is
flashable to hardware yet** — including this primary target)

---

## 1. Purpose

This document is the single source of truth for what must be created, extracted,
downloaded, and wired together before Nuxel can be *test-flashed* to the
**Google Pixel 10 Pro XL (`mustang`)**.

The Pixel 10 Pro XL is Nuxel's **primary and default hardware target** — the
device every other port (`s10plus`, `g7power`) is measured against, and the
device the UTM VM, the build dispatcher, `boot/flash.sh`, `firmware/manifest.yml`
and `device/deviceinfo` all default to. It is therefore *not* framed as a "port"
the way the sibling documents are; it is the **reference target**, and the job of
this file is to state, honestly, exactly how far the reference target is from
being bootable.

It is deliberately honest: Nuxel v0.2.0 is a **mustang-only scaffold**, and
mustang itself is still aspirational. The repository contains a real multi-device
directory layout, real per-device scripts, and a passing UTM VM, but **no kernel
has been cross-built for mustang, no firmware blob has been extracted, and no
boot-image set exists.**

The companion files are:

- **`./nuxel-pixel10proxl.md`** — the ready-to-use implementation prompt for the
  build agent (acceptance criteria included).
- **`./pixel10proxl-prompt.md`** — the full, deep-analysis implementation prompt.
- **`./google-pixel-10-pro-xl-quickstart.md`** — the operator flash quickstart.

---

## 2. Why the Pixel 10 Pro XL is the primary target (and the hardest)

The Pixel 10 Pro XL is the **practical** choice of primary target: it is the
flagship the design is written for, it carries a Google Titan M3 hardware root of
trust (which maps cleanly onto Nuxel's AVB/GrapheneOS-style security model), and
its bootloader uses the standard, well-understood Google ABL + `fastboot` flow.

It is *simultaneously* the **hardest** of the three Nuxel targets to actually
bring up, because its silicon is the least mainline-friendly:

| Factor | Google Pixel 10 Pro XL (`mustang`) | Samsung Galaxy S10+ (`s10plus`) | Moto G7 Power (`g7power`) |
|---|---|---|---|
| SoC / kernel base | **Tensor G5 `gs501`**, GKI 6.12; vendor tree **private** | Exynos 9820; `linux-postmarketos-exynos9820` (close-to-mainline) | SDM632; `msm8953-mainline/linux` (mainline) |
| Mainline driver coverage | **Very low** — GPU, panel, touch, modem, audio mostly downstream-only | Medium (Panfrost GPU, several upstream) | **High** (freedreno, MSM DRM, ILI2117, LM3697 upstream) |
| Bootloader | Google ABL + AVB 2.0 + Titan M3 | Samsung S-Boot + TWRP (already unlocked) | Stock ABOOT + `lk2nd` + EDL |
| Flash tooling | `fastboot` + `fastbootd` (A/B super) | TWRP + Odin/`heimdall` (**no fastboot**) | `fastboot` + `lk2nd` + EDL (9008) |
| Unbrick safety | `fastboot` always available | Download Mode + Odin | EDL (Qualcomm 9008) |
| Community Linux precedent | **Weak** — no postmarketOS port; gs501 downstream-only | Good (`samsung-exynos9820`) | Good (`qcom-msm8953`, `motorola-ocean`) |
| Risk to a daily driver | Highest (bootloader unlock wipes; AVB fights custom images) | Zero (spare, already tainted) | Zero (spare) |

**Recommendation / reality:** the Pixel 10 Pro XL stays the **primary target**
(and the reference for all documentation, VM geometry, and the flash pipeline),
but its bring-up is **gated hardest** by a private vendor kernel tree and a
downstream-only driver stack. The sibling mainline-friendly targets
(`s10plus`, `g7power`) exist precisely so the *userspace, sandbox, PWA, and
flash-pipeline* work can be proven on hardware that mainline can actually boot
while the Pixel vendor-kernel dependency is resolved.

> **Honest caveats to keep in mind:**
> - `gs501_defconfig` and the Tensor G5 SoC/modem/GPU drivers live in
>   `android-gs-mustang-6.12`, which Google does not publish for anonymous
>   cloning. **This is the single biggest blocker.**
> - Every mustang peripheral driver in `docs/driver-status.md` is
>   downstream-only or not upstream: PowerVR DXT GPU, AMB655X LTPO panel,
>   S6SY791 touch, Exynos 5500 modem, CS35L45/CS42L43 audio, SN220 NFC, GF3636
>   fingerprint.
> - Bootloader unlock is hardware-gated, `fastboot flashing unlock` **wipes the
>   device**, and re-locking requires Nuxel-signed AVB images with a custom key.
> - No physical flash has ever been attempted. The recovery path
>   (`boot/google-pixel-10-pro-xl/recovery.sh`, factory `flash-all.sh`) is
>   scripted but **never exercised on real hardware**.

---

## 3. Current codebase reality check (from the deep-analyze)

Nuxel v0.2.0 is a clean but **not-yet-flashable** Linux phone OS scaffold. The
mustang path is the most complete in the tree, but "most complete" here means
"best-documented scaffold", not "bootable".

What actually exists and defaults to `mustang`:

- **Device selector:** `tools/nuxel-device-select.sh` maps `mustang` →
  `google-pixel-10-pro-xl`; the `Makefile` sets `NUXEL_DEVICE ?= mustang`, and
  `images/build.sh`, `boot/flash.sh`, `firmware/*` all default to mustang when no
  `--device` is passed.
- **Device package:** `device/google-pixel-10-pro-xl/deviceinfo` (full
  postmarketOS-format identity + boot/flash metadata) and
  `device/google-pixel-10-pro-xl/APKBUILD` (`pkgname="device-google-mustang"`).
- **Kernel:** `kernel/build-kernel.sh` builds the *public* GKI `android16-6.12`
  and merges `kernel/google-pixel-10-pro-xl/defconfig`. The authoritative
  `gs501_defconfig` is **not** in the repo (private vendor tree). A per-device
  wrapper/README-toolchain lives under `kernel/google-pixel-10-pro-xl/`.
- **Firmware:** `firmware/google-pixel-10-pro-xl/manifest.yml` lists **30
  required + 2 optional** blobs across 12 categories (modem, wifi, bluetooth,
  gpu, display, audio, sensors, nfc, fingerprint, pmic, charger). Every entry is
  `source_path`/`checksum` = placeholder — **0 of 30 verified**. Only symlinked
  compatibility entry points exist at `firmware/manifest.yml`,
  `firmware/install-firmware.sh`, `firmware/verify-firmware.sh`.
- **Boot/flash:** `boot/google-pixel-10-pro-xl/flash.sh` is mustang-only (Google
  ABL, `boot`/`vendor_boot`/`init_boot`/`dtbo`/`vbmeta`, A/B slots, `fastbootd`
  super flashing, dev = AVB-disabled, prod = custom-key relock). `boot/recovery.sh`
  is the failsafe shell. Legacy symlinks `boot/flash.sh` / `boot/recovery.sh`
  point at the mustang files.
- **Images:** `images/google-pixel-10-pro-xl/build.sh` is a thin wrapper that
  pins `--device mustang` and forwards to the shared dispatcher `images/build.sh`;
  `images/google-pixel-10-pro-xl/{avb,ostree,rauc}` hold the mustang AVB, OSTree
  (VM) and RAUC (pmOS) update scaffolding. Shared, device-agnostic userspace
  assembly lives in `images/mkrootfs.sh` (Phosh/Flatpak/PWA).
- **Configs:** `configs/google-pixel-10-pro-xl/{display,libinput,alsa-ucm,modem,pipewire,wireplumber}`
  are prepared (mustang-suffixed files), and legacy symlinks
  (`configs/display`, `configs/libinput`, …) point at the Pixel directory.
- **Boot packer:** `images/bootpack/mkbootimg.py` implements **boot header
  v3/v4** (correct for mustang) but **no v1** (needed by the A-only siblings).
- **VM:** the UTM ARM64 `Nuxel-verify` VM (UUID
  `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`, Fedora 43, **Phosh 0.54.0 / phoc
  0.54.0**, frozen 720×1440 portrait) boots and passes the verification suites
  (**PASS=22/17, HARD PASS**) — this is the only "green" hardware-adjacent result
  in the whole tree, and it validates *userspace*, not the Pixel.

**Consequence:** the mustang bring-up is not a rename and not a one-liner — it
is **(1) obtaining the private vendor kernel tree, (2) extracting and hashing the
30 vendor blobs, (3) producing a real boot-image set, and (4) physically unlocking
and flashing a device whose only recovery path is Google's own factory image.**

---

## 4. Google Pixel 10 Pro XL hardware profile (verified from the repo)

| Component | mustang value | Source |
|---|---|---|
| Device | Google Pixel 10 Pro XL | `device/google-pixel-10-pro-xl/deviceinfo` |
| Codename / key | `mustang` | repo |
| Serial | `58211FDCQ001LA` | `docs/driver-status.md` |
| HW version / SKU | `MP1.0` / `G45RY` | `docs/driver-status.md` |
| SoC | Google **Tensor G5** (`gs501`), Armv9.2 | `deviceinfo`, `driver-status.md` |
| CPU | Cortex-X5 + Cortex-A730 + Cortex-A530 | `deviceinfo` |
| GPU | Imagination **PowerVR DXT-72-2304** | `driver-status.md` |
| Security chip | Google **Titan M3** (AVB root of trust) | `deviceinfo` |
| RAM | 16 GB LPDDR5X | `deviceinfo` |
| Storage | 256 GB **UFS 4.0** (`ufshcd`, f2fs) | `deviceinfo` |
| Display | Samsung **AMB655X** LTPO OLED, 3120×1440 @ 120 Hz | `driver-status.md` |
| Touch | Samsung **S6SY791** (I2C) | `driver-status.md` |
| WiFi / BT | Broadcom **BCM4390** (Wi-Fi 7 / BT 5.4), `brcmfmac` + `BCM4390.hcd` | `deviceinfo` |
| Modem | Samsung **Exynos 5500** (PCIe/MHI, 5G NR) | `deviceinfo` |
| NFC | NXP **SN220** | `deviceinfo` |
| UWB | available | `deviceinfo` |
| Audio | Cirrus Logic **CS35L45** (amp) + **CS42L43** (codec) | `deviceinfo` |
| Sensors | Bosch BMI270, ST LSM6DSV, AMS TCS3710, Bosch BMP280 | `deviceinfo` |
| Fingerprint | Goodix **GF3636** (optical under-display) | `deviceinfo` |
| Battery / charging | 5300 mAh Li-Po; TI BQ2597x + Maxim MAX77729 | `deviceinfo` |
| PMIC | Maxim MAX77729 + MAX77826 | `deviceinfo` |
| Shipped kernel base | Linux **6.12 LTS** (`android-gs-mustang-6.12`, `gs501_defconfig`) | `deviceinfo` |
| Bootloader | Google **ABL** (mustang variant) + AVB 2.0 + Titan M3 | `deviceinfo` |
| Verified boot | AVB 2.0 with Titan M3 chain of trust | `deviceinfo` |
| Boot image | Android boot header **v4** + `vendor_boot` + `init_boot` + `dtbo` + `vbmeta` | `deviceinfo` |
| Partition model | **A/B** (`boot_a/b`, `vendor_boot_a/b`, `init_boot_a/b`, `dtbo_a/b`, `vbmeta_a/b`) + `super` dynamic | `deviceinfo` |
| Flash tooling | **`fastboot`** + `fastbootd` | `deviceinfo`, `boot/flash.sh` |

### Authoritative resources

- **Google factory images (mustang):** `https://developers.google.com/android/images#mustang`
  — reviewed build string `BP1A.250405.001` (`mustang-bp1a.250405.001-factory-*.zip`).
- **Google GKI kernel (public):** `https://android.googlesource.com/kernel/common`
  (branch `android16-6.12`).
- **Google vendor kernel (private):**
  `https://android.googlesource.com/kernel/google-modules/gs`
  (branch `android-gs-mustang-6.12`) — anonymous clone currently returns 404.
- **AVB tool:** `https://android.googlesource.com/platform/external/avb`.
- **Repo-internal:** `docs/driver-status.md`, `docs/hardware-ids.md`,
  `docs/bootloader-unlock-guide.md`, `docs/mustang-recovery-bringup.md`,
  `docs/hardware-bringup-prep.md`, `docs/verification-report.md`,
  `docs/build-guide.md`, `docs/device-setup.md`.

### mustang boot chain

```
Boot ROM (Tensor G5 SoC)
    │
    ▼
Google Titan M3 (security chip)
    │  Hardware root of trust; enforces the AVB 2.0 chain of trust
    │
    ▼
Google ABL (Android Bootloader — mustang variant)
    │  Reads boot.img (header v4), vendor_boot.img (vendor ramdisk + DTB/DTBO),
    │  init_boot.img (generic ramdisk, Android 13+ split-ramdisk)
    │  Verifies the vbmeta chain against the enrolled AVB key
    │
    ▼
Linux 6.12 LTS (android-gs-mustang-6.12, gs501_defconfig)
    │  nuxel.device=mustang on the kernel cmdline
    │
    ▼
Nuxel initramfs (init_boot.img)
    │  Probes /dev/disk/by-partlabel/system_a (or system_b)
    │  dm-verity root hash from the AVB chain
    │
    ▼
Nuxel system partition (dm-verity + read-only) ──► Phosh + GTK4 + PWA apps
```

**Key point:** the Pixel uses `fastboot` throughout — no TWRP, no Odin, no
`lk2nd`, no U-Boot chainload. AVB 2.0 is the whole verified-boot story; enrolling
a custom AVB key is what makes a *relocked* Nuxel Pixel possible.

---

## 5. What makes mustang different from the sibling targets (gap analysis)

| Dimension | mustang (Pixel 10 Pro XL) | s10plus (Galaxy S10+) | g7power (Moto G7 Power) |
|---|---|---|---|
| Kernel base | GKI 6.12 (`android-gs-mustang-6.12`, private) | Exynos 9820 downstream → `linux-postmarketos-exynos9820` | Qualcomm 4.9 → `linux-postmarketos-qcom-msm8953` |
| Mainline support | **Very low** | Medium | **High** |
| Boot chain | Boot ROM → Titan M3 → ABL → Linux (+AVB) | S-Boot → U-Boot → Linux (EFI) | PBL → ABOOT → `lk2nd` → Linux |
| Boot image format | Header **v4** + `vendor_boot` + `init_boot` + `vbmeta` | Header **v1** (page 2048) | Header **v1** (page 2048) |
| Partition model | A/B + `super` dynamic | A-only UFS | A-only eMMC |
| Verified boot | AVB 2.0 + Titan M3 | none to fight (unlock disables) | none to fight |
| Flash tooling | `fastboot` + `fastbootd` | TWRP (adb/`dd`) + Odin/`heimdall` | `fastboot` + `lk2nd` + EDL |
| GPU | PowerVR DXT (vendor only) | Mali-G76 → Panfrost | Adreno 506 → freedreno |
| Modem | Samsung Exynos 5500 (PCIe/MHI, no upstream MM plugin) | Shannon LTE (integrated) | Snapdragon X9 LTE |
| WiFi/BT | Broadcom BCM4390 (brcmfmac, chip-entry patch) | Broadcom BCM4375 | Qualcomm WCN3680B (wcn36xx) |
| Audio | Cirrus CS35L45 + CS42L43 (downstream) | Cirrus CS47L93 + CS35L45 | Qualcomm WCD9335 |

**Bottom line:** mustang is the *most feature-complete scaffold* and the
*hardest actual bring-up*. Every subsystem that the siblings get from mainline
(freedreno, MSM DRM, ILI2117, Panfrost) mustang gets only from Google's private
vendor tree.

---

## 6. What is needed to make Nuxel work on the Pixel 10 Pro XL

### 6.1 Firmware / proprietary blobs (mustang only, never shared)

Extract from the **stock factory image** (`mustang-bp1a.250405.001-factory-*.zip`)
— never reuse `s10plus`/`g7power` blobs, and never reuse a stale `panther`
(Pixel 7) blob. The manifest
(`firmware/google-pixel-10-pro-xl/manifest.yml`) enumerates **30 required + 2
optional** entries:

| Category | Example blobs | Linux consumers |
|---|---|---|
| Exynos 5500 modem | `modem.bin`, `modem_pr.bin`, `modem_cal.bin`, `modem_cfg.txt`, `exynos5500_shm.bin` | MHI/PCIe modem stack (Phase 8) |
| BCM4390 WiFi 7 | `brcmfmac4390-pcie.bin`, `brcmfmac4390-pcie.clm_blob`, `brcmfmac4390.nvm` | `brcmfmac` (chip-entry patch) |
| BCM4390 BT 5.4 | `BCM4390.hcd` | `hci_qca`/`hci_bcm` userspace `.hcd` load |
| PowerVR DXT GPU | `pvr_rogue_km.fw`, `pvr_dxt_fw.fw`, `pvr_rogue_csf.fw`, `pvr_drv.so` | vendor PowerVR DRM + userspace |
| Display (AMB655X) | `amb655x_fw.bin`, `amb655x_gamma.bin` | panel init (vendor DRM) |
| Touch (S6SY791) | `s6sy791_touch_fw.bin` | touch driver FW update |
| Audio (CS35L45/CS42L43) | `cs35l45_fw.bin`, `cs35l45_dsp.bin`, `cs42l43_fw.bin` | ASoC/DSP |
| Sensors | `bmi270_fw.bin`, `lsm6dsv_fw.bin`, `tcs3710_fw.bin` | IIO sensor drivers |
| NFC (SN220) | `sn220_fw.bin` | NCI stack |
| Fingerprint (GF3636) | `gf3636_fw.bin` | libfprint/fprintd |
| PMIC / charger | `max77729_fw.bin`, `max77826_fw.bin`, `bq2597x_fw.bin`, `max1720x_fw.bin` | MFD/charger/fuel-gauge |

Acquisition (operator, cannot be automated — Google's consent flow):
`firmware/google-pixel-10-pro-xl/install-firmware.sh <factory.zip> --output-dir
./firmware-out --install`, then `verify-firmware.sh --strict` must report
**30/30 verified**.

### 6.2 Kernel (mustang / gs501)

- **Blocking dependency:** the authoritative `gs501_defconfig` and the Tensor G5
  SoC/modem/GPU/panel/touch drivers live in the **private**
  `android-gs-mustang-6.12` tree. Until that tree is accessible, only the public
  GKI `android16-6.12` can be built — and it is **not bootable on mustang
  hardware**.
- The public build merges `gki_defconfig` + `kernel/google-pixel-10-pro-xl/defconfig`.
- Required config symbols are documented in `docs/driver-status.md`; almost all
  mustang peripherals are **not upstream** (`CONFIG_DRM_POWERVR`,
  `CONFIG_DRM_PANEL_SAMSUNG_AMB655X`, `CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791`,
  `CONFIG_MHI_SAMSUNG_EXYNOS5500`, `CONFIG_BRCMFMAC_BCM4390`,
  `CONFIG_SND_SOC_CS35L45`/`CS42L43`, `CONFIG_NFC_NXP_SN220`,
  `CONFIG_INPUT_GOODIX_GF3636`).
- Only `CONFIG_SCSI_UFSHCD_PLATFORM` (UFS 4.0), `dwc3` (USB), and
  AppArmor/seccomp/namespaces are genuinely mainline today.

### 6.3 Device tree

- mustang needs its `gs501` DTB/DTBO from the vendor tree (public GKI ships no
  mustang DT). The DTBO is packed into `vendor_boot.img`.
- `chosen`/bootargs must carry `nuxel.device=mustang`,
  `nuxel.serial=58211FDCQ001LA`, `nuxel.boot=1`, and the
  `root=/dev/disk/by-partlabel/system_${SLOT}` selection.

### 6.4 Boot images & flash tooling

- Header **v4** boot image packing is supported by
  `images/bootpack/mkbootimg.py` (+ AOSP `mkbootimg`); the `vendor_boot`,
  `init_boot`, `dtbo`, `vbmeta` and `super`/`system.img` set is the mustang
  format. `init_boot.img` is **mandatory** on Android 13+ (mustang).
- Two flash paths: **development** (`--skip-avb --allow-unverity-dev`, no
  relock) and **production** (`--relock-custom-key`, requires Nuxel-signed AVB
  images and **wipes the device**).
- Recovery: factory `flash-all.sh` (safest), manual `fastboot` restore, or
  `boot/google-pixel-10-pro-xl/flash.sh --revert`.

### 6.5 Driver matrix (honest, mustang-specific)

| Subsystem | Driver reality | Nuxel action |
|---|---|---|
| GPU | PowerVR DXT-72-2304, **vendor-only** | Vendor kernel + `pvr_drv.so`; llvmpipe fallback first |
| Display | AMB655X LTPO, **not upstream** | Vendor panel driver; 3120×1440@120 |
| Touch | S6SY791, **not upstream** | Vendor touch driver + libinput conf |
| WiFi | `brcmfmac` base mainline, **BCM4390 chip-entry patch needed** | Extract BCM4390 firmware/NVRAM/CLM |
| Bluetooth | `hci_bcm` mainline, needs `BCM4390.hcd` | Extract `.hcd` |
| Modem | Exynos 5500 PCIe/MHI, **no upstream MM plugin** | Phase 8; WiFi-only in Phase 1 |
| Audio | CS35L45 + CS42L43, **not upstream** | Vendor ASoC + UCM |
| NFC / fingerprint | SN220 / GF3636, **not upstream** | Phase late |
| UFS 4.0 / USB / sandbox | **Mainline** | Use directly |

### 6.6 Userspace (device-agnostic, reusable, already proven in the VM)

Phosh + phoc (Wayland), GTK4/libadwaita native apps, the PWA launcher, the
`nuxel-*` D-Bus services (bridge/portal/notifications), the 5-layer sandbox
configs, and hardened_malloc. This is exactly what the UTM `Nuxel-verify` VM
exercises (PASS=22/17, HARD PASS).

---

## 7. Mandatory per-device directory separation (anti-cross-flash)

Every device-specific artifact lives under a per-device directory keyed by
`NUXEL_DEVICE`, identical to the sibling targets. mustang occupies the
`google-pixel-10-pro-xl/` slots:

```
firmware/google-pixel-10-pro-xl/   manifest.yml install-firmware.sh verify-firmware.sh blobs/
kernel/google-pixel-10-pro-xl/     defconfig patches/ README-toolchain.md build-kernel.sh
device/google-pixel-10-pro-xl/     deviceinfo APKBUILD 90-nuxel-mustang.rules nuxel-mustang.conf
boot/google-pixel-10-pro-xl/       flash.sh recovery.sh boot-config.txt
configs/google-pixel-10-pro-xl/    display libinput alsa-ucm modem pipewire wireplumber
images/google-pixel-10-pro-xl/     build.sh avb/ ostree/ rauc/
```

Device keys (`tools/nuxel-device-select.sh`):

- `mustang`  → `google-pixel-10-pro-xl` → Google Pixel 10 Pro XL
- `s10plus`  / `beyond2lte` → `s10plus` → Samsung Galaxy S10+ (Exynos)
- `g7power`  / `ocean`      → `g7power` → Motorola Moto G7 Power

`nuxel.device=` on the kernel cmdline **must** match the selected key, and
`boot/google-pixel-10-pro-xl/flash.sh` **must** verify the connected device
identity (`fastboot getvar product` == `mustang`) and refuse on mismatch. The
legacy top-level paths (`boot/flash.sh`, `firmware/manifest.yml`, `device/deviceinfo`,
`configs/display`, …) are **symlinks** into the Pixel directory for backward
compatibility — they are not a second copy.

---

## 8. Safety / anti-brick rules

1. **Google's factory image is the safety net.** Download and SHA-256-verify
   `mustang-bp1a.250405.001-factory-*.zip` (and keep it untouched) **before**
   the first flash. `flash-all.sh` from that zip is the canonical restore.
2. **`fastboot flashing unlock` (and `flashing unlock_critical`) WIPE the
   device.** Back up everything irreplaceable first.
3. **Verify device identity before every flash.** `fastboot getvar product`
   must be `mustang` and `fastboot getvar serial` must be the expected unit;
   refuse on mismatch.
4. **Never cross-flash.** Enforce the per-device directory + device-key gate in
   every script. Never flash a Pixel with another device's firmware/kernel/DTS.
5. **Never `--relock-custom-key` / `flashing lock` until Nuxel is verified
   booting in dev mode** — relocking with wrong/missing AVB images bricks the
   boot path.
6. **Never flash official Google images back onto a relocked-with-custom-key
   device** without first re-enrolling the Google key path.
7. **Do not wipe `persist` / `metadata`** except as an explicit, deliberate
   clean-install step (`fastboot -w` wipes `userdata` + `metadata` only).
8. **Keep the A/B active slot known** (`fastboot getvar current-slot`) and never
   mix slot artifacts.

---

## 9. Prerequisites the operator must provide (not automatable)

1. The **Google Pixel 10 Pro XL (`mustang`)** — carrier-unlocked, with a USB-C
   **data** cable (USB 3.2 Gen2 preferred) and `adb`/`fastboot`
   (platform-tools ≥ 34) on a Linux/macOS host.
2. **OEM unlocking enabled** and the bootloader **unlocked**
   (`fastboot flashing unlock`; wipes the device).
3. The **factory image** `mustang-bp1a.250405.001-factory-*.zip`, downloaded and
   SHA-256-verified from Google's images page (consent flow cannot be automated).
4. **Access to the private vendor kernel tree** `android-gs-mustang-6.12`
   (`gs501_defconfig` + Tensor G5 drivers), or an equivalent signed vendor kernel.
5. Enough battery (> 50%).

Unlock (operator, one-time):
```sh
# Device: Settings → About phone → tap Build number ×7 → Developer options
#   → enable "OEM unlocking" (+ "USB debugging")
adb reboot bootloader
fastboot getvar product          # must be: mustang
fastboot flashing unlock         # WIPES the device; confirm on-device
fastboot flashing unlock_critical  # only if flashing bootloader/radio
```

---

## 10. Phased mustang bring-up plan

| Phase | Goal | Exit criteria |
|---|---|---|
| 0 | Unlock + factory image | Bootloader unlocked; factory image downloaded + SHA-256 verified; `getvar all` captured |
| 1 | Firmware extraction | `verify-firmware.sh --strict` → **30/30 verified** (real hashes filled) |
| 2 | Vendor kernel build | `android-gs-mustang-6.12` accessible; `Image.gz` + mustang DTB produced |
| 3 | Boot image packing | `boot.img` v4 + `vendor_boot.img` + `init_boot.img` + `dtbo.img` + `vbmeta.img` produced (not stubs) |
| 4 | First boot (display + touch) | Phosh launches at 3120×1440; S6SY791 touch responds |
| 5 | WiFi/BT | `wlan0` up (BCM4390 brcmfmac); `bluetoothctl` sees BCM4390 |
| 6 | GPU | PowerVR DXT (vendor) or explicit llvmpipe fallback in Phosh |
| 7 | Audio | Speaker + mic via PipeWire/UCM (CS42L43 + CS35L45) |
| 8 | Modem | Custom MHI/MM plugin for Exynos 5500; LTE/5G data path |
| 9 | dm-verity + production AVB | Custom AVB key enrolled; bootloader relocked; dm-verity enforced |

**Phase 0/2 are the immediate blockers.** Phase 0 is operator-gated (hardware +
factory image); Phase 2 is upstream-gated (private vendor kernel tree).

---

## 11. Open questions to resolve on the real device

- Does the reviewed serial `58211FDCQ001LA` still match the unit in hand, and is
  it carrier-unlocked?
- Exact build string / bootloader revision currently on the device (must match
  the factory image used for recovery).
- Are the private vendor kernel sources obtainable under any Google program, or
  must a signed prebuilt vendor kernel be used as-is?
- Exact vendor blob filenames inside `vendor.img`/`modem_*.img` (the manifest
  paths are placeholders until the factory image is unpacked).
- Whether the PowerVR DXT userspace (`pvr_drv.so`) needs a specific Mesa/PowerVR
  branch for GLES/Vulkan, or runs llvmpipe-only initially.
- Whether `super` dynamic-partition resizing is needed for a full Nuxel
  `system.img`, or whether the rootfs should target `userdata` first.
- Titan M3 Keymaster/StrongBox: required at all for Nuxel, or strictly AVB-only?

---

## 12. References

- Repo files: `README.md`, `QUICKSTART.md`, `Makefile`, `tools/nuxel-device-select.sh`,
  `device/google-pixel-10-pro-xl/{deviceinfo,APKBUILD}`,
  `kernel/build-kernel.sh`, `kernel/google-pixel-10-pro-xl/{defconfig,README-toolchain.md,patches/}`,
  `firmware/google-pixel-10-pro-xl/{manifest.yml,install-firmware.sh,verify-firmware.sh}`,
  `boot/google-pixel-10-pro-xl/{flash.sh,recovery.sh}`,
  `images/build.sh`, `images/mkrootfs.sh`, `images/bootpack/mkbootimg.py`,
  `docs/driver-status.md`, `docs/hardware-ids.md`, `docs/bootloader-unlock-guide.md`,
  `docs/mustang-recovery-bringup.md`, `docs/hardware-bringup-prep.md`,
  `docs/verification-report.md`, `docs/build-guide.md`, `docs/device-setup.md`.
- Google factory images (mustang): https://developers.google.com/android/images#mustang
- Android platform tools: https://developer.android.com/studio/releases/platform-tools
- GKI kernel (`android16-6.12`): https://android.googlesource.com/kernel/common
- mustang vendor kernel (private): https://android.googlesource.com/kernel/google-modules/gs
- AVB tool: https://android.googlesource.com/platform/external/avb
- Nuxel repo root: `/Users/wicked/x/nuxel` (local)
