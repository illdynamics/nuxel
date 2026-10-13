# Nuxel on the Motorola Moto G7 Power — Requirements & Bring-Up Plan

**Status:** planning / bring-up requirements document
**Target device:** Motorola Moto G7 Power (XT1955, Snapdragon 632)
**Codename:** `ocean`
**Nuxel version context:** v0.2.0 (design scaffold + code prototype; **nothing is flashable to hardware yet**, including the primary Pixel 10 Pro XL target)

---

## 1. Purpose

This document is the single source of truth for what must be created, extracted,
downloaded, and wired together before Nuxel can be *test-flashed* to the
**Motorola Moto G7 Power** instead of the daily-driver **Google Pixel 10 Pro XL**.

It is deliberately honest: the current repository is a **mustang-only** scaffold,
and mustang itself is still aspirational. Porting to the G7 Power is **not** a
rename — it is a second, substantially different hardware bring-up (Qualcomm vs
Google Tensor, mainline msm8953 vs GKI 6.12, lk2nd/fastboot vs Google ABL).

The companion file **`./nuxel-g7power.md`** contains the ready-to-use
implementation prompt for the build agent.

---

## 2. Why the G7 Power is a strong first test device (and not the S22 Ultra / Astro Slide)

| Factor | Moto G7 Power (ocean) | Samsung Galaxy S22 Ultra | Astro Slide 5G |
|---|---|---|---|
| Bootloader unlock | Official Motorola portal → `fastboot oem unlock <code>` | Knox / RMM / KG prenormal | `fastboot flashing unlock` |
| Flash tooling | Standard **`fastboot`** (Qualcomm/Motorola) | Odin / heimdall | `fastboot` (VAB) |
| Community Linux precedent | **postmarketOS `qcom-msm8953` generic port** (mainline) | Weak | `fayep/astro-modules` |
| Mainline kernel | **Yes — `linux-postmarketos-qcom-msm8953`** | No | No (downstream 4.14) |
| Mainline bootloader | **`lk2nd`** (msm8916-mainline) | No | No |
| Unbrick safety | **Qualcomm EDL** (9008) + fastboot | Knox/EDL opaque | MTK SP Flash Tool |
| Risk to main phone | Zero — spare device | Same, but Knox liability | Zero |

**Recommendation:** the G7 Power is, on paper, the **easiest** of the spare
devices because it is a **mainline-supported Qualcomm msm8953 device** with a
working `lk2nd` bootloader and standard `fastboot`. postmarketOS already treats
`motorola-ocean` as a first-class device under the `qcom-msm8953` generic port.

> **Honest caveats to keep in mind:**
> - Touch is now **identified** (Ilitek ILI2117) and the upstream ocean DTS
>   carries the touch node, but several community reports still note *"no
>   touchscreen"* on the generic image, so display/touch is still a Phase-1
>   verification task, not a freebie.
> - The community wiki records a bricked unit requiring **EDL recovery**, so we
>   must keep the EDL (9008) unbrick path verified **before** the first flash.
> - Bootloader unlock requires a **one-time unlock code from Motorola** (device
>   IMEI + serial), which only the operator can obtain.

---

## 3. Current codebase reality check (from the deep-analyze)

The repository is a clean but **not-yet-flashable** Linux phone OS scaffold:

- **Kernel:** `kernel/build-kernel.sh` builds the public GKI `android16-6.12`
  common kernel and merges `kernel/defconfig`. The authoritative `gs501_defconfig`
  lives in a private Google vendor tree.
- **Boot:** `images/build.sh` produces a generic `NUXELBOOT1` bundle or an
  Android boot header v4 (`ANDROID!`) only when `Image.gz` + DTB are present.
  `boot/flash.sh` is mustang-specific (Google ABL, `vendor_boot`, `init_boot`,
  `vbmeta`, `fastbootd` super flashing).
- **Firmware:** `firmware/manifest.yml` + `install-firmware.sh` +
  `verify-firmware.sh` are mustang-only.
- **Device:** `device/deviceinfo` + `device/APKBUILD` are mustang-only.
- **Rootfs:** `images/mkrootfs.sh` builds a Flatpak/Phosh userspace + ext4
  `system.img`; device-agnostic in userspace terms but assumes
  `system_a`/`system_b` + dm-verity + AVB.
- **Boot packers:** `images/bootpack/mkbootimg.py` implements only Android boot
  header **v3/v4**. The G7 Power needs **v1** (legacy header, kernel + ramdisk,
  page 2048).

**Consequence:** the G7 Power bring-up is a *new kernel tree + new device
package + new firmware manifest + new boot/flash scripts*, sharing only the
device-agnostic userspace (services, shell, PWA, configs).

---

## 4. Motorola Moto G7 Power hardware profile (verified)

| Component | G7 Power (XT1955) value | Source |
|---|---|---|
| Device | Motorola Moto G7 Power | postmarketOS `motorola-ocean` |
| Codename | `ocean` | postmarketOS |
| SoC | Qualcomm **Snapdragon 632 (SDM632)** — 4× Kryo 250 Gold (Cortex-A73) @1.8 GHz + 4× Kryo 250 Silver (Cortex-A53) @1.8 GHz, 14 nm | postmarketOS `qcom-msm8953` |
| GPU | Adreno 506 | postmarketOS `qcom-msm8953` |
| RAM | 3/4 GB LPDDR3 | Motorola / reviews |
| Storage | 32/64 GB **eMMC** + microSD | Motorola / reviews |
| Display | 6.2" IPS LCD, **1520×720** (HD+), 19:9 | Motorola / reviews |
| Backlight | TI **LM3697** LED driver (I2C `i2c_5` @ 0x36) | mainline `sdm632-motorola-ocean.dts` |
| Touch | Ilitek **ILI2117** (I2C `i2c_3` @ 0x41, IRQ tlmm 65, inverted-x) | mainline `sdm632-motorola-ocean.dts` |
| WiFi/BT | Qualcomm **WCN3680B** (802.11 b/g/n, BT 4.2) — integrated; WiFi = `wcn36xx` | SDM632 spec / defconfig |
| Modem | Qualcomm **Snapdragon X9 LTE** (integrated) | SDM632 spec |
| NFC | None (most ocean variants) — verify | device inventory |
| Audio | Qualcomm **WCD9335/cajon-v2** codec + speaker amp | postmarketOS `qcom-msm8953` |
| Sensors | Bosch **BMI160** (accel + gyro), MEMSIC **MMC3630KJ** (magnetometer), AMS **TMD2725** (proximity + ALS) | pmOS wiki (sensors sandbox, xt1955-5) |
| Battery | 5000 mAh, 15 W TurboPower (QC 3.0) | Motorola |
| Shipped OS | Android 9 (upgradable) | Motorola |
| Shipped kernel | Qualcomm **4.9 downstream** BSP | Motorola OSS |
| Boot model | **A-only** (no A/B slots); `boot`, `system`, `vendor`, `dtbo`, `userdata` etc. | Motorola partition table |
| Boot image | Legacy Android boot image (header **v1**, page 2048) | AOSP |
| Flash tooling | **`fastboot`** (Qualcomm/Motorola) + **lk2nd** + **EDL** (9008) | postmarketOS `qcom-msm8953` |

### Community resources (authoritative for this work)

- **postmarketOS generic msm8953 port** — device package `device-qcom-msm8953`,
  kernel `linux-postmarketos-qcom-msm8953` (mainline). Covers SDM450/625/626/632
  (ocean = SDM632). Wiki:
  `https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_450/625/626/632_(MSM8953)`
- **postmarketOS Moto G7 Power device page:**
  `https://wiki.postmarketos.org/wiki/Motorola_Moto_G7_Power_(motorola-ocean)`
- **lk2nd** mainline bootloader (msm8916/msm8953):
  `https://github.com/msm8916-mainline/lk2nd`
- **msm8953 mainline kernel:** `https://github.com/msm8953-mainline/linux`
- **msm8953 ALSA UCM configs:** `https://github.com/msm8953-mainline/alsa-ucm-conf`
- **Motorola bootloader unlock portal:** `https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device`

### Key boot-chain fact (G7 Power / msm8953)

The G7 Power's stock **ABOOT** cannot boot a mainline kernel directly. The
postmarketOS msm8953 port uses **`lk2nd`** — a small Qualcomm bootloader
chainloaded from the stock `boot` partition (or `aboot`) — which then loads the
mainline kernel and a mainline device tree. The standard sequence is:

```sh
fastboot flash dtbo dtbo.img          # stock dtbo (must be re-flashed)
fastboot flash boot lk2nd.img         # lk2nd replaces the stock boot chain
# then via lk2nd's fastboot:
fastboot flash boot boot.img          # mainline kernel + initramfs
fastboot flash userdata rootfs.img    # Nuxel rootfs (or use system partition)
```

`fastboot getvar all` / `fastboot oem device-info` report the unlock state, and
EDL mode (Qualcomm 9008) is the last-resort unbrick path (via `edl`/QFIL).

---

## 5. Core gap analysis: Pixel 10 Pro XL (mustang) vs Moto G7 Power (ocean)

| Dimension | Pixel 10 Pro XL (mustang) | Moto G7 Power (ocean) |
|---|---|---|
| Kernel base | Linux 6.12 LTS (GKI) | Qualcomm **4.9 downstream** → **mainline `linux-postmarketos-qcom-msm8953`** |
| Mainline support | Partial; vendor gs501 tree is private | **Yes** — mainline msm8953 |
| Boot chain | Boot ROM → Titan M3 → Google ABL → Linux + AVB | PBL → SBL → ABOOT → **lk2nd** → mainline Linux |
| Boot image format | Header **v4** + `vendor_boot` + `init_boot` + `vbmeta` | Header **v1** (legacy), kernel + ramdisk, page 2048 |
| Partition model | Full A/B GPT + `super` dynamic partitions | **A-only**; `boot`/`system`/`vendor`/`dtbo` separate |
| Verified boot | AVB 2.0 + Titan M3 | None to fight (unlock disables enforcement) |
| Flash tooling | `fastboot` + `fastbootd` | **`fastboot` + `lk2nd`**; **EDL** for unbrick |
| GPU | PowerVR DXT (vendor only) | Adreno 506 → mainline **freedreno** (msm drm) |
| Display | Samsung AMB655X 3120×1440@120 | 1520×720 IPS (MSM DRM/DSI) |
| Touch | Samsung S6SY791 | Ilitek ILI2117 (mainline `ili210x`) |
| Modem | Samsung Exynos 5500 (PCIe/MHI) | Snapdragon X9 LTE — no upstream MM plugin |
| WiFi/BT | Broadcom BCM4390 (brcmfmac) | Qualcomm WCN3680B (wcn36xx + QCOM_WCNSS_PIL) |
| Audio | Cirrus CS35L45 + CS42L43 | Qualcomm WCD9335 (cajon-v2 ASoC) |
| NFC / sensors / camera | Various Pixel components | None/minimal + Qualcomm sensors; unknown until inventory |

**Bottom line:** the G7 Power cannot run the existing Nuxel 6.12 kernel or
mustang drivers, but it is the **most mainline-friendly** of the targets: the
`qcom-msm8953` port gives us a mainline kernel + lk2nd + freedreno + wcn36xx.
The Nuxel userspace (Phosh, GTK4/PWA, services, sandbox) is reused *on top of*
that kernel.

---

## 6. What is needed to make Nuxel work on the G7 Power

### 6.1 Firmware / proprietary blobs (per-device, never shared with mustang)

Extract from the G7 Power's **stock `vendor`/`system` partition** (via `adb
pull`/`dd` from fastboot/TWRP, or from the Motorola stock firmware). Do **not**
reuse any Pixel blobs.

| Blob area | Expected contents | Linux consumers |
|---|---|---|
| GPU Adreno 506 | `a506_zap.mbn` (firmware), `qcom/` firmware | freedreno (msm drm) |
| WiFi/BT WCN3680B | WCNSS firmware + `wlan_mac.bin`, NVRAM | wcn36xx + QCOM_WCNSS_PIL |
| Audio WCD9335 | codec/DSP firmware (`wcd9335`/`cajon-v2`) | mainline ASoC |
| Display | panel init / MIPI DSI sequences | MSM DRM/DSI + DT |
| Touch | ILI2117 config (no FW blob needed on mainline) | mainline `ili210x` driver |
| Modem | X9 LTE modem/DSP firmware (protect modemst!) | qcom modem stack (Phase-late) |
| Sensors / camera | sensor/ISP firmware | downstream drivers |

Acquisition: `adb pull`/`dd` from a booted stock ROM or `fastboot`/TWRP of
`/vendor/firmware`, `/vendor/firmware_mnt`, `/vendor/lib/modules`, and the
`/firmware` image files — or extract from the Motorola stock firmware package.
Document every blob source in the new `firmware/g7power/manifest.yml`.

### 6.2 Kernel (per-device)

- Use **`linux-postmarketos-qcom-msm8953`** (mainline, from `msm8953-mainline`)
  as the Nuxel G7 Power kernel base — **not** the 6.12 GKI mustang kernel.
- Add a Nuxel G7 Power defconfig fragment (`kernel/g7power/defconfig`), not the
  mustang `kernel/defconfig`.
- Port the Nuxel `drivers/nuxel/` patch + hardening Kconfigs onto the msm8953
  tree **only where they compile**.
- Enable MSM DRM/freedreno, DSI panel, wcn36xx (+ QCOM_WCNSS_PIL), ILI2117 touch, WCD9335 ASoC, ext4/f2fs,
  namespaces/seccomp/AppArmor where the tree supports them.
- Build with `aarch64-linux-gnu-` or clang.

### 6.3 Device tree (per-device)

- Obtain the msm8953/ocean DTS from the pmOS kernel tree.
- Create `nuxel.ocean.*` modifications for: chosen bootargs, console (UART),
  display/touch nodes, `nuxel.device=g7power` boot param, and eMMC root.
- Do **not** use mustang DTBs on the G7 Power.

### 6.4 Boot chain & flash tooling (per-device)

- **Boot image format:** legacy Android boot image header **v1** (page 2048).
  Add a v1 packer (or AOSP `mkbootimg` v1); the existing `mkbootimg.py` is v3/v4 only.
- **lk2nd chainload:** build/flash `lk2nd` (msm8916-mainline) to the `boot`
  partition so mainline can boot.
- **Flash sequence** (pmOS-proven, `fastboot`):
  ```sh
  fastboot flash dtbo dtbo.img            # stock dtbo (required)
  fastboot flash boot lk2nd.img           # install lk2nd
  # reboot into lk2nd's fastboot, then:
  fastboot flash boot boot.img            # mainline kernel + Nuxel initramfs
  fastboot flash userdata nuxel-rootfs.img  # or flash to system
  fastboot reboot
  ```
- **Unlock (one-time, operator):** `fastboot oem unlock <MOTOROLA_CODE>`.
- **Unbrick:** Qualcomm **EDL (9008)** via `edl`/QFIL to re-flash stock
  bootloader images.
- Recovery to stock: re-flash stock Motorola firmware via fastboot (or Lenovo
  Moto Smart Assistant).

### 6.5 Drivers matrix (G7 Power-specific status)

| Subsystem | G7 Power driver reality | Nuxel action |
|---|---|---|
| GPU | Adreno 506 → freedreno (msm drm) | freedreno; llvmpipe fallback for first boot |
| Display | MSM DRM/DSI + LM3697 backlight | Bring up ocean panel via DT; `wlr-randr` 1520×720 |
| Touch | Ilitek ILI2117 (mainline `ili210x`) | Enable `CONFIG_TOUCHSCREEN_ILI210X`; libinput calibration |
| WiFi | WCN3680B → wcn36xx + QCOM_WCNSS_PIL | Firmware from device; mainline wcn36xx |
| Bluetooth | WCN3680B (BT 4.2) | hci_qca + firmware |
| Modem | Snapdragon X9 LTE | Not ModemManager-ready; Phase-1 target is data/WiFi |
| Audio | WCD9335 (cajon-v2 ASoC) | Per-device UCM2 profile (msm8953-mainline examples) |
| NFC / sensors / camera | None (NFC) + BMI160/MMC3630KJ/TMD2725 sensors; camera TBD | Map after real-device inventory |

### 6.6 Userspace (device-agnostic, reusable)

- Phosh + phoc (Wayland), GTK4/libadwaita native apps, PWA launcher, nuxel
  services (bridge/portal/notifications), sandbox configs, hardened_malloc.
- First boot can use a minimal **initramfs → debug shell** (via lk2nd fastboot)
  to validate kernel/display, then the full Phosh rootfs.

---

## 7. Mandatory per-device directory separation (anti-cross-flash)

Identical layout to the S10+ plan (single shared rule across all targets) — see
`./s10plus-requirements.md` §7. The G7 Power occupies the `g7power/` slots:

```
firmware/g7power/        manifest.yml install-firmware.sh verify-firmware.sh blobs/
kernel/g7power/          defconfig patches/ README-toolchain.md build-kernel.sh
device/g7power/          deviceinfo APKBUILD 90-nuxel-ocean.rules nuxel-ocean.conf
boot/g7power/            flash.sh recovery.sh boot-config.txt pack-boot-v1.sh lk2nd/
configs/g7power/         display libinput alsa-ucm modem pipewire wireplumber
images/g7power/          build.sh (G7 Power boot/rootfs build)
```

Device keys:

- `mustang`  / `google-pixel-10-pro-xl` → Google Pixel 10 Pro XL
- `s10plus`  / `beyond2lte`             → Samsung Galaxy S10+ (Exynos)
- `g7power`  / `ocean`                  → Motorola Moto G7 Power

`nuxel.device=` on the kernel cmdline must match the selected key, and each
flash script must verify the connected device identity (`fastboot getvar product`
== `ocean`) before flashing and refuse on mismatch.

---

## 8. Safety / anti-brick rules

1. **EDL (9008) is the safety net.** Verify the EDL unbrick path **before** the
   first flash (boot to EDL, confirm the host enumerates Qualcomm 9008).
2. **Verify device identity before every flash.** `fastboot getvar product` must
   be `ocean`; refuse on mismatch.
3. **Never flash the wrong device's firmware/driver.** Enforce via the per-device
   directory + device-key gate in all scripts.
4. **Never touch `modemst1`, `modemst2`, `fsg`, `fsc`, `ddr`, `persist`,
   `misc`** — these hold per-unit calibration (IMEI, MAC, radio calibration).
5. **Back up the full stock firmware (or at least the boot/recovery/modem
   images) before the first flash.**
6. **`fastboot flash dtbo dtbo.img` must precede lk2nd** — a missing/corrupt
   dtbo is the classic cause of a soft-brick on msm8953.
7. **Do not relock the bootloader** while testing (`fastboot oem lock`).
8. Keep the stock `boot` image backed up so the original boot chain is restorable.

---

## 9. Prerequisites the operator must provide (not automatable)

1. The **Moto G7 Power (XT1955)** with a USB-C data cable and `adb` + `fastboot`
   on a Linux/macOS host (platform-tools ≥ 34).
2. The **Motorola unlock code** (from the official portal using IMEI + serial)
   and the `fastboot oem unlock <code>` step performed.
3. The **stock Motorola firmware** (for firmware extraction + EDL/fastboot recovery).
4. **EDL access verified** (Qualcomm 9008) before any flashing.
5. Enough battery (> 60 %).

Bootloader unlock (operator, one-time):
```sh
# Developer options -> OEM unlocking + USB debugging ON
adb reboot bootloader
fastboot oem get_unlock_data          # paste into Motorola portal -> get code
fastboot oem unlock <UNLOCK_CODE>     # wipes device
```

---

## 10. Phased G7 Power bring-up plan

| Phase | Goal | Exit criteria |
|---|---|---|
| 0 | Inventory the real device | `fastboot getvar all`, `getprop`, `dmesg`, `getevent`, `/vendor/firmware` + `/vendor/lib/modules` dumped; touch/panel/WiFi/audio IDs verified against upstream DTS; camera + modem inventory collected |
| 1 | Install lk2nd + boot mainline msm8953 kernel with Nuxel initramfs (debug shell) | lk2nd fastboot responds; kernel boots; `nuxel.device=g7power` on console |
| 2 | Bring up display + touch | Phosh launches at 1520×720; ILI2117 touch calibrated |
| 3 | Bring up WiFi/BT | `wlan0` up (wcn36xx), `bluetoothctl` sees WCN3680B |
| 4 | Bring up GPU | freedreno GLES (or explicit llvmpipe fallback) |
| 5 | Bring up audio | Speaker + mic via PipeWire/UCM (cajon-v2) |
| 6 | Userspace hardening | AppArmor, nftables, hardened_malloc, sandbox verified |
| 7 | Modem/camera (stretch) | Data path first; voice/SMS only if qcom stack becomes viable |

**Phase 0 is the immediate blocker** — the touch/panel/WiFi/audio IDs are
now known from the upstream msm8953 device tree (ILI2117 touch, WCN3680B,
WCD9335), so Phase 0 shrinks to collecting the real firmware blobs and the
remaining camera/modem inventory before the device package and firmware
manifest are complete.

---

## 11. Open questions to resolve on the real device

- ~~Touch controller~~ → **resolved: Ilitek ILI2117 @ I2C 0x41 (i2c_3)** (confirm on the unit).
- Panel resolution/timing known (720×1520, LM3697 backlight); exact LCM/DDIC is only in the stock vendor tree.
- Audio codec confirmed: WCD9335 (cajon-v2); exact speaker routing still needs the UCM profile.
- Camera sensor list (if present) and ISP path.
- Whether NFC is present on this ocean variant.
- Sensor hub confirmed: BMI160 (accel+gyro), MMC3630KJ (magnetometer), TMD2725 (prox+ALS).
- Exact WiFi/BT firmware filenames under `/vendor/firmware`.
- Current bootloader revision (for stock recovery images).
- Whether `userdata` or `system` is the better target for the Nuxel rootfs on
  this 32/64 GB eMMC unit.

---

## 12. References

- Repo deep-analyze files: `README.md`, `QUICKSTART.md`, `kernel/build-kernel.sh`,
  `kernel/defconfig`, `images/build.sh`, `images/bootpack/mkbootimg.py`,
  `boot/flash.sh`, `device/deviceinfo`, `firmware/manifest.yml`,
  `docs/driver-status.md`, `docs/device-setup.md`, `boot/initramfs/init.sh`.
- postmarketOS msm8953 port:
  https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_450/625/626/632_(MSM8953)
- postmarketOS Moto G7 Power page:
  https://wiki.postmarketos.org/wiki/Motorola_Moto_G7_Power_(motorola-ocean)
- lk2nd: https://github.com/msm8916-mainline/lk2nd
- msm8953 mainline kernel: https://github.com/msm8953-mainline/linux
- msm8953 ALSA UCM configs: https://github.com/msm8953-mainline/alsa-ucm-conf
- Motorola bootloader unlock portal:
  https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device
