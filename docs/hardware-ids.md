# Nuxel Hardware Component IDs — Canonical Reference

> **Purpose.** This file is the single canonical component table for Nuxel's
> three hardware targets. It records the *verified* component IDs (with sources)
> so the per-device driver matrices and bring-up plans don't each restate the
> same IDs in slightly different ways.
>
> The detailed per-device **driver state** lives in `docs/driver-status.md`
> (mustang) and the per-device `*-requirements.md` / `nuxel-*.md` bring-up plans
> (s10plus, g7power). The per-device **firmware manifests** enumerate the exact
> blobs. When any of those files disagree with this one, this file wins.

## Device keys

| Key        | Directory             | Codename      | Device                        |
|------------|-----------------------|---------------|-------------------------------|
| `mustang`  | `google-pixel-10-pro-xl` | `mustang`   | Google Pixel 10 Pro XL        |
| `s10plus`  | `s10plus`             | `beyond2lte`  | Samsung Galaxy S10+ (Exynos)  |
| `g7power`  | `g7power`             | `ocean`       | Motorola Moto G7 Power        |

`nuxel.device=` on the kernel cmdline must match the selected key. Every flash
script must verify the connected device identity before flashing and refuse on
mismatch.

---

## Canonical component table

| Component            | mustang (Pixel 10 Pro XL)            | s10plus (Galaxy S10+)                 | g7power (Moto G7 Power)              |
|----------------------|--------------------------------------|---------------------------------------|--------------------------------------|
| SoC                  | Google Tensor G5 (`gs501`)           | Samsung Exynos 9820                   | Qualcomm Snapdragon 632 (SDM632)     |
| GPU                  | PowerVR DXT-72-2304                  | Mali-G76 MP12 (Bifrost)               | Adreno 506                           |
| RAM / Storage        | (TBD) / UFS 4.0                      | 8 GB LPDDR4X / UFS 2.1                | 3/4 GB LPDDR3 / eMMC 32/64 GB        |
| Display              | Samsung AMB655X LTPO 3120×1440       | 6.4" AMOLED 3040×1440, DDIC **S6E3HA9** | 6.2" IPS LCD 1520×720               |
| Backlight            | — (OLED)                             | — (OLED)                              | TI **LM3697** (i2c_5 @ 0x36)         |
| Touch                | Samsung **S6SY791**                  | Samsung **S6SY761** (`sec_ts`) @ 0x48 | Ilitek **ILI2117** (i2c_3 @ 0x41)    |
| Audio                | Cirrus **CS35L45 + CS42L43**         | Cirrus **CS47L93** + 2× **CS35L40**   | Qualcomm **WCD9335** (cajon-v2)      |
| WiFi / BT            | Broadcom **BCM4390** (Wi-Fi 7/BT 5.4)| Broadcom **BCM4375** (Wi-Fi 6/BT 5.0) | Qualcomm **WCN3680B** (b/g/n, BT 4.2)|
| Modem                | Samsung Exynos 5500 (PCIe/MHI)       | Shannon LTE (integrated, no 5G)       | Snapdragon X9 LTE (integrated)       |
| NFC                  | NXP **SN220**                        | Samsung `sec-nfc` (S3FWRN5) @ 0x27    | none (most variants)                 |
| Fingerprint          | Goodix **GF3636**                    | — (rear-mounted, sensor TBD)          | — (rear-mounted, sensor TBD)         |
| Sensors              | BMI270 + LSM6DSV + TCS3710           | sensor hub TBD                        | BMI160 + MMC3630KJ + TMD2725         |
| Boot model           | A/B, header v4 (`vendor_boot`/`init_boot`) | A-only, header v1 (page 2048)  | A-only, header v1 (page 2048)        |
| Flash tooling        | `fastboot` + `fastbootd`             | TWRP (adb/`dd`) + Odin/`heimdall`     | `fastboot` + `lk2nd` + EDL (9008)    |
| Shipped kernel       | (GKI 6.12 target)                    | Samsung 4.14 downstream               | Qualcomm 4.9 downstream              |

---

## Verified IDs by device

### Google Pixel 10 Pro XL (`mustang`)

| Component    | Verified ID                             | Source                                  |
|--------------|-----------------------------------------|-----------------------------------------|
| Device       | Google Pixel 10 Pro XL (`mustang`)      | repo (`device/deviceinfo`, `boot/flash.sh`) |
| SoC          | Google Tensor G5 (`gs501`)              | repo `docs/driver-status.md`            |
| Serial       | `58211FDCQ001LA`                        | repo `docs/driver-status.md`            |
| GPU          | Imagination PowerVR DXT-72-2304         | `docs/driver-status.md`                 |
| Display      | Samsung AMB655X LTPO, 3120×1440 @120 Hz | `docs/driver-status.md`                 |
| Touch        | Samsung S6SY791                         | `docs/driver-status.md`                 |
| Modem        | Samsung Exynos 5500 (PCIe/MHI)          | `docs/driver-status.md`                 |
| WiFi/BT      | Broadcom BCM4390 (Wi-Fi 7, BT 5.4)      | `docs/driver-status.md`                 |
| Audio        | Cirrus CS35L45 + CS42L43                | `docs/driver-status.md`                 |
| NFC          | NXP SN220                               | `docs/driver-status.md`                 |
| Fingerprint  | Goodix GF3636                           | `docs/driver-status.md`                 |
| Storage      | UFS 4.0                                 | `docs/driver-status.md`                 |

### Samsung Galaxy S10+ (`s10plus`, codename `beyond2lte`)

| Component    | Verified ID                                                          | Source                              |
|--------------|----------------------------------------------------------------------|-------------------------------------|
| Device       | Samsung Galaxy S10+ (SM-G975F, Exynos)                               | postmarketOS `samsung-beyond2lte`   |
| SoC          | Exynos 9820 (2× Mongoose M4 + 2× A75 + 4× A55, 8 nm)                 | pmOS `samsung-exynos9820`           |
| GPU          | Mali-G76 MP12 (Bifrost → Panfrost)                                   | Exynos 9820 spec                    |
| RAM/Storage  | 8 GB LPDDR4X; UFS 2.1 @ `/dev/block/platform/13d60000.ufs`           | pmOS device page                    |
| Display      | 6.4" Dynamic AMOLED 3040×1440, 19:9, HDR10+; DDIC **S6E3HA9** (`s6e3ha9_beyond2`) | beyond2lte DTS          |
| Touch        | Samsung **S6SY761** (`sec_ts`), I2C hsi2c_10 @ 0x48, fw `y771`/`y771_d`, FOD | beyond2lte DTS (`input_common`) |
| WiFi/BT      | Broadcom **BCM4375** (Wi-Fi 6, BT 5.0)                               | DTS `samsung,brcm-wlan` + teardown  |
| Modem        | Integrated Samsung Shannon LTE (Cat 20, no 5G)                       | Exynos 9820 spec                    |
| NFC          | Samsung `sec-nfc` (S3FWRN5-family) @ I2C 0x27 + embedded SE          | beyond2lte DTS                      |
| Audio        | Cirrus **CS47L93** codec + **2× CS35L40** amps (madera ASoC)         | beyond2lte DTS                      |
| Battery      | 4100 mAh, 15 W wired / 12–15 W wireless                              | Samsung                             |
| Shipped OS   | Android 9 (One UI), up to Android 12                                | Samsung                             |
| Shipped ker. | Samsung 4.14.x downstream                                            | Samsung OSRC                        |
| Boot model   | A-only; `boot`/`recovery`/`system`/`vendor`/`product`                | Samsung partition table             |
| Boot image   | Legacy Android boot image, header **v1** (page 2048)                 | Samsung / pmOS U-Boot notes         |
| Flash tooling| **No `fastboot`** — TWRP (adb sideload + `dd`) + Odin/`heimdall`      | pmOS `samsung-exynos9820`           |

### Motorola Moto G7 Power (`g7power`, codename `ocean`)

| Component    | Verified ID                                                          | Source                              |
|--------------|----------------------------------------------------------------------|-------------------------------------|
| Device       | Motorola Moto G7 Power (XT1955)                                      | postmarketOS `motorola-ocean`       |
| SoC          | Snapdragon 632 (SDM632); 4× Kryo 250 Gold (A73) + 4× Silver (A53) @1.8 GHz, 14 nm | pmOS `qcom-msm8953`   |
| GPU          | Adreno 506 (→ mainline freedreno)                                    | pmOS `qcom-msm8953`                 |
| RAM/Storage  | 3/4 GB LPDDR3; 32/64 GB eMMC + microSD                               | Motorola / reviews                  |
| Display      | 6.2" IPS LCD 1520×720, 19:9                                          | Motorola / reviews                  |
| Backlight    | TI **LM3697** (I2C `i2c_5` @ 0x36)                                   | mainline `sdm632-motorola-ocean.dts`|
| Touch        | Ilitek **ILI2117** (I2C `i2c_3` @ 0x41, IRQ tlmm 65, inverted-x)     | mainline `sdm632-motorola-ocean.dts`|
| WiFi/BT      | Qualcomm **WCN3680B** (b/g/n, BT 4.2); WiFi = `wcn36xx` + QCOM_WCNSS_PIL | SDM632 spec / defconfig        |
| Modem        | Qualcomm Snapdragon X9 LTE (integrated)                              | SDM632 spec                         |
| NFC          | none (most ocean variants) — *verify on device*                      | device inventory                    |
| Audio        | Qualcomm **WCD9335** (cajon-v2) codec + speaker amp                  | pmOS `qcom-msm8953`                 |
| Sensors      | Bosch BMI160 (accel+gyro), MEMSIC MMC3630KJ (mag), AMS TMD2725 (prox+ALS) | pmOS wiki sensors sandbox (xt1955-5) |
| Battery      | 5000 mAh, 15 W TurboPower (QC 3.0)                                   | Motorola                            |
| Shipped OS   | Android 9 (upgradable)                                               | Motorola                            |
| Shipped ker. | Qualcomm 4.9 downstream                                              | Motorola OSS                        |
| Boot model   | **A/B**; `boot_a`/`boot_b`, `dtbo_a`/`dtbo_b`, `system`/`vendor`/`userdata`; current slot `_b` | Motorola partition table |
| Boot image   | Legacy Android boot image, header **v1** (page 2048)                 | AOSP                                |
| Flash tooling| `fastboot` + `lk2nd` + EDL (9008)                                    | pmOS `qcom-msm8953`                 |

> **G7 Power touch (updated 2026-10-12).** The touch controller is Ilitek
> ILI2117 and the upstream `sdm632-motorola-ocean.dts` node is correct. The
> reported *"no touchscreen"* behaviour is explained: Nuxel asked Kconfig for
> the non-existent `CONFIG_TOUCHSCREEN_ILI2117`, so mainline's real driver
> (`CONFIG_TOUCHSCREEN_ILI210X` → `ili210x.ko`, OF match `ilitek,ili2117`) was
> never built. Fixed. On this handset the hardware is verified present (i2c
> `3-0041`, IRQ 286 = msmgpio 65 edge `ilitek`, `event1` "tchip", 10 MT slots),
> but **stock Android binds it with the vendor `ILITEK_TDDI` driver**, so
> `ili210x` binding on mainline is still to be proven on first boot.
> See `nuxel-g7power-touchscreen.md`, `docs/g7power-bringup.md` §8, and
> `g7power/stock-evidence/`.

---

## Still unknown (needs the physical device)

| Device    | Unknown                                                                |
|-----------|------------------------------------------------------------------------|
| s10plus   | Camera sensors (both) and sensor-hub part numbers; exact firmware blob filenames under `/vendor/firmware`; modem interface; bootloader revision (for matching stock-recovery firmware). |
| g7power   | Exact LCM/DDIC name (only in the stock vendor tree; mainline uses an lk2nd-handoff framebuffer); exact WiFi/BT firmware filenames; camera sensors; whether NFC is present; bootloader revision. |
| mustang   | Everything is still `UNKNOWN`/`PLACEHOLDER` in `firmware/manifest.yml` until a factory image/device is available. |

---

## Sources

### Samsung Galaxy S10+ (`beyond2lte`)

- postmarketOS generic Exynos 9820 port —
  https://wiki.postmarketos.org/wiki/Samsung_Exynos_9820_(samsung-exynos9820)
- postmarketOS S10+ device page —
  https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_(samsung-beyond2lte)
- Custom U-Boot fork (`exynos9820` branch) — https://github.com/chiffathefox/u-boot
- TWRP for beyond2lte — https://twrp.me/samsung/samsunggalaxys10plus.html
- Samsung open-source release center (Exynos 9820 kernel) — https://opensource.samsung.com

### Motorola Moto G7 Power (`ocean`)

- postmarketOS generic msm8953 port —
  https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_450/625/626/632_(MSM8953)
- postmarketOS Moto G7 Power device page —
  https://wiki.postmarketos.org/wiki/Motorola_Moto_G7_Power_(motorola-ocean)
- lk2nd mainline bootloader — https://github.com/msm8916-mainline/lk2nd
- msm8953 mainline kernel — https://github.com/msm8953-mainline/linux
- msm8953 ALSA UCM configs — https://github.com/msm8953-mainline/alsa-ucm-conf
- Motorola bootloader unlock portal —
  https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device

### Google Pixel 10 Pro XL (`mustang`)

- Repo-internal: `docs/driver-status.md`, `firmware/manifest.yml`,
  `device/deviceinfo`, `boot/flash.sh`.
