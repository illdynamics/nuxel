# Nuxel Driver Status for Google Pixel 10 Pro XL (mustang)

## Target Device Specifications

| Component            | Specification                            |
|----------------------|------------------------------------------|
| **Device**           | Google Pixel 10 Pro XL (mustang)         |
| **SoC**              | Google Tensor G5 (gs501)                 |
| **Serial**           | 58211FDCQ001LA                           |
| **HW Version**       | MP1.0                                    |
| **SKU**              | G45RY                                    |
| **Kernel**           | Linux 6.12 LTS                           |
| **Defconfig**        | gs501_defconfig                          |

> **Honesty notice.** The original roadmap marked many drivers as "Complete"
> and others as "In Progress". Almost none of them are present in **upstream
> mainline Linux 6.12**; they exist only in Google's downstream
> `android-gs-mustang-6.12` tree. This file now reflects the **true** state:
> ✅ = works upstream/available, 🚧 = downstream-only or patch required,
> ⬜ = pending device/bring-up, ❌ = not implemented / not yet reached.
> Phase-0 uses the downstream vendor kernel as the bring-up kernel (see
> `docs/build-guide.md`), so "downstream-only" items **will** be reachable
> there — but they are not mainline.

---

## Multi-device hardware component table (canonical)

The driver matrices below are **mustang-only**. The canonical component table
for all three targets lives in **[`docs/hardware-ids.md`](hardware-ids.md)**
(with the source URLs cited); the compact cross-device summary is:

| Component    | mustang (Pixel 10 Pro XL)             | s10plus (Galaxy S10+)                    | g7power (Moto G7 Power)            |
|--------------|---------------------------------------|------------------------------------------|------------------------------------|
| SoC          | Google Tensor G5 (`gs501`)            | Samsung Exynos 9820                      | Snapdragon 632 (SDM632)            |
| GPU          | PowerVR DXT-72-2304                   | Mali-G76 MP12                            | Adreno 506                         |
| Display      | AMB655X LTPO 3120×1440 @120           | AMOLED 3040×1440 (DDIC **S6E3HA9**)      | IPS LCD 1520×720                   |
| Touch        | Samsung **S6SY791**                   | Samsung **S6SY761** (`sec_ts`) @ 0x48    | Ilitek **ILI2117** (i2c_3 @ 0x41)  |
| Audio        | Cirrus **CS35L45 + CS42L43**          | Cirrus **CS47L93** + 2× **CS35L40**      | Qualcomm **WCD9335** (cajon-v2)    |
| WiFi / BT    | Broadcom **BCM4390**                  | Broadcom **BCM4375**                     | Qualcomm **WCN3680B**              |
| Modem        | Samsung Exynos 5500 (PCIe/MHI)        | Shannon LTE (integrated)                 | Snapdragon X9 LTE                  |
| NFC          | NXP **SN220**                         | Samsung `sec-nfc` (S3FWRN5) @ 0x27       | none (most variants)               |
| Boot model   | A/B, header v4                        | A-only, header v1                        | **A/B**, header v1                  |
| Flash tool   | `fastboot` + `fastbootd`              | TWRP + Odin/`heimdall` (no fastboot)     | `fastboot` + `lk2nd` + EDL         |

---

## Driver Support Matrix

### GPU: Imagination PowerVR DXT-72-2304

| Driver Component        | Status       | Notes                                        |
|-------------------------|:------------:|----------------------------------------------|
| PowerVR DRM driver      | 🚧 Downstream | **No CONFIG_DRM_POWERVR in mainline 6.12.**  |
| PowerVR Rogue/kernel mod| 🚧 Downstream | pvr_rogue_km.ko only in vendor kernel        |
| Mesa PowerVR Gallium3D  | ❌ TODO       | Requires Imagination Mesa branch (not merged)|
| Mesa Vulkan (PowerVR)   | ❌ TODO       | mesa-powervr not in distro yet               |
| Hardware acceleration   | ❌ TODO       | Not reachable until Phase 5 GPU bring-up     |
| Software fallback       | ⬜ Pending    | Phosh on llvmpipe until DRI lands            |

**Notes:** PowerVR DXT-72-2304 is Imagination's current GPU core. There is **no
mainline PowerVR DRM driver**; it only ships in the vendor kernel with the
proprietary `pvr_drv.so` userspace. Firmware must come from the vendor
partition.

---

### Display: Samsung AMB655X LTPO OLED

| Driver Component        | Status       | Notes                                        |
|-------------------------|:------------:|----------------------------------------------|
| Panel driver            | 🚧 Downstream | `CONFIG_DRM_PANEL_SAMSUNG_AMB655X` **not in mainline** |
| 120Hz refresh           | 🚧 Downstream | Panel timing in vendor devicetree            |
| LTPO backlight          | 🚧 Downstream | AMB655X backlight in vendor panel driver     |
| HDR / DSC / adaptive sync | ❌ TODO     | Post-bring-up                              |

**Notes:** AMB655X is Samsung LTPO, downstream-only. Bring-up prepared by
`configs/display/nuxel-mustang-start.sh` + `configs/libinput/nuxel-mustang-touch.conf`.

---

### Touchscreen: Samsung S6SY791

| Driver Component        | Status       | Notes                                        |
|-------------------------|:------------:|----------------------------------------------|
| I2C touch driver        | 🚧 Downstream | **No CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791 in mainline 6.12.** Driver lives in Google vendor kernel (`drivers/input/touchscreen/`). |
| Multi-touch (10pt)      | 🚧 Downstream | Driver provides MT-slot protocol             |
| libinput calibration    | ✅ Prepared   | `configs/libinput/nuxel-mustang-touch.conf`  |
| Firmware update         | ⬜ Pending    | s6sy791_touch_fw.bin (vendor)                |

**Correction:** the original roadmap listed this as "Complete". The S6SY791
driver is **NOT upstream** and must come from the vendor tree or an out-of-tree
patch.

---

### Modem: Samsung Exynos 5500

| Driver Component        | Status       | Notes                                        |
|-------------------------|:------------:|----------------------------------------------|
| MHI PCIe generic bus    | 🚧 Downstream | `CONFIG_MHI_BUS_PCI_GENERIC`; MHI netlink present, must compile against vendor tree |
| Exynos 5500 MHI plugin  | ❌            | **No CONFIG_MHI_SAMSUNG_EXYNOS5500 in mainline.** |
| ModemManager plugin     | ❌ TODO       | **Exynos 5500 has no plugin in mainline ModemManager.** Detection depends on MHI + firmware. |
| Voice calls / SMS / LTE | ⬜ Pending    | Requires a working MM plugin + CP            |
| 5G NR / VoLTE           | ❌ TODO       | Carrier-dependent, IMS not reached           |
| Modem firmware loading  | ⬜ Pending    | modem.bin (~200 MB) from modem partition     |

**Correction:** the roadmap claimed ModemManager detects the modem. That is
**false** — see `configs/modem/exynos5500-people.md`. The Exynos 5500 is a
PCIe/MHI Samsung modem handled only generically; Nuxel must add a plugin.
Until a device is present this is unreachable.

---

### WiFi: Broadcom BCM4390

| Driver Component        | Status       | Notes                                        |
|-------------------------|:------------:|----------------------------------------------|
| brcmfmac (SDIO/PCIe)    | ✅ Available | Base driver in mainline                      |
| BCM4390/4391 chip entry | ❌            | **Not in upstream quirks** — patch required  |
| PCIe firmware (802.11be)| ⬜ Pending    | `brcmfmac4390-pcie.bin` from vendor          |
| 6GHz / MLO / WPA3       | ⬜ Pending    | Requires CLM blob + firmware                 |

**Correction:** the roadmap listed WiFi firmware "✅ Extracted". No firmware has
actually been extracted (no device/factory image on hand). See
`docs/wifi-bcm4390-status.md`, `firmware/manifest.yml`.

---

### Bluetooth: Broadcom BCM4390 (BT 5.4)

| Driver Component        | Status       | Notes                                        |
|-------------------------|:------------:|----------------------------------------------|
| HCI UART (BCM)          | ✅ Available | CONFIG_BT_HCIUART_BCM in mainline            |
| BCM4390 .hcd firmware   | ⬜ Pending    | BCM4390.hcd from vendor                      |
| LE Audio / A2DP / HFP   | ❌ TODO       | Post-bring-up                               |

---

### Audio: Cirrus CS35L45 + CS42L43

| Driver Component        | Status       | Notes                                        |
|-------------------------|:------------:|----------------------------------------------|
| CS35L45 codec driver    | 🚧 Downstream | `CONFIG_SND_SOC_CS35L45` not in mainline 6.12 |
| CS42L43 codec driver    | 🚧 Downstream | Not upstream                                |
| ALSA UCM configs        | ✅ Prepared   | `configs/alsa-ucm/GoogleMustang/*.conf`      |
| PipeWire / WirePlumber  | ✅ Prepared   | `configs/pipewire`, `configs/wireplumber`    |
| Actual audio output     | ⬜ Pending    | Requires codec drivers + DSP firmware        |

**Correction:** codec drivers exist only downstream. All configs are scaffolded
and VM-exercisable, but no real audio has sounded on mustang.

---

### Sensors

| Component              | Status       | Notes                                        |
|------------------------|:------------:|----------------------------------------------|
| BMI270 IMU             | 🚧 Downstream | CONFIG_BMI270 not confirmed upstream         |
| LSM6DSV IMU            | 🚧 Downstream | ST_LSM6DSV downstream-only                   |
| TCS3710 ALS            | 🚧 Downstream | TCS3701 family                               |
| iio-sensor-proxy       | ⬜ Pending    | Autoload after kernel sensor nodes           |

---

### USB

| Component              | Status       | Notes                                        |
|------------------------|:------------:|----------------------------------------------|
| USB 3.2 / dwc3         | ✅ Available | Mainline dwc3                                |
| Type-C CC / PD         | 🚧 Downstream | TCPM/TCPCI, SBU footprint in vendor tree     |
| USB gadget (fastbootd) | ✅ Available | Required for flashing                        |
| DP Alt Mode            | 🚧 Downstream | DisplayPort over USB-C needs SoC DP driver   |

---

### Fingerprint: Goodix gf3636

| Component              | Status       | Notes                                        |
|------------------------|:------------:|----------------------------------------------|
| Goodix GF3636 driver   | ❌            | **No CONFIG_INPUT_GOODIX_GF3636 upstream**   |
| libfprint / fprintd    | ❌ TODO       | Not integrated                               |

---

### Power Management

| Component              | Status       | Notes                                        |
|------------------------|:------------:|----------------------------------------------|
| MAX77729 / MAX77826 PMIC| 🚧 Downstream| MFD drivers downstream                        |
| BQ2597x charger        | 🚧 Downstream | CONFIG_CHARGER_BQ2597X not mainline          |
| MAX1720x fuel gauge    | 🚧 Downstream | Not mainline                                 |

---

### NFC: NXP SN220

| Component              | Status       | Notes                                        |
|------------------------|:------------:|----------------------------------------------|
| NXP SN220 NCI driver   | ❌            | **No CONFIG_NFC_NXP_SN220 in mainline.** Pending device+NFC stack |

---

### Storage: UFS 4.0

| Component              | Status       | Notes                                        |
|------------------------|:------------:|----------------------------------------------|
| ufshcd platform        | ✅ Available | CONFIG_SCSI_UFSHCD_PLATFORM mainline         |
| UFS 4 / HPB / inline cr| ✅ Available | Mainline                                     |

---

## Kernel Configuration Summary (honest)

| Feature                  | Config Option                        | Status |
|--------------------------|--------------------------------------|:------:|
| PowerVR GPU              | CONFIG_DRM_POWERVR                   | ❌ not upstream |
| AMB655X panel            | CONFIG_DRM_PANEL_SAMSUNG_AMB655X      | ❌ not upstream |
| S6SY791 touch            | CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791    | ❌ not upstream |
| Exynos 5500 MHI          | CONFIG_MHI_SAMSUNG_EXYNOS5500        | ❌ not upstream |
| MHI PCIe generic         | CONFIG_MHI_BUS_PCI_GENERIC           | 🚧 downstream tree |
| BCM4390 WiFi             | CONFIG_BRCMFMAC_BCM4390              | ❌ not upstream |
| CS35L45 audio            | CONFIG_SND_SOC_CS35L45               | ❌ not upstream |
| CS42L43 audio            | CONFIG_SND_SOC_CS42L43               | ❌ not upstream |
| NXP SN220 NFC            | CONFIG_NFC_NXP_SN220                 | ❌ not upstream |
| Goodix GF3636 FP         | CONFIG_INPUT_GOODIX_GF3636           | ❌ not upstream |
| UFS 4.0                  | CONFIG_SCSI_UFSHCD_PLATFORM          | ✅ available |

> All ❌-not-upstream options that are aspirational have been **removed from
> `kernel/defconfig`** or annotated by the Kernel Build Foundation group
> (bg-01). The Phase-0 build uses the downstream `gs501_defconfig` which
> carries the actual Google/SoC drivers.

## Firmware Blobs Required

The authoritative list + verification is in `firmware/manifest.yml` and
`firmware/verify-firmware.sh`. **None are extracted yet** (no factory image /
device in reach).

## Key Differences from panther (Pixel 7)

| Feature              | panther (OLD)              | mustang (CORRECT target) |
|----------------------|----------------------------|---------------------------|
| SoC                  | Tensor G2                  | Tensor G5 (gs501)         |
| GPU                  | Mali-G710 MP7              | PowerVR DXT-72-2304       |
| Modem                | Exynos 5300                | Exynos 5500               |
| Display panel        | S6E3FC3                    | Samsung AMB655X LTPO      |
| Touch                | Synaptics s3908            | Samsung S6SY791           |
| Audio                | MAX98373 + WSA881X         | Cirrus CS35L45 + CS42L43  |
| WiFi                 | BCM4389 (WiFi 6E)          | BCM4390 (WiFi 7)          |
| Sensors              | BMI160 + LSM6DSO           | BMI270 + LSM6DSV          |
| Defconfig            | gs201_defconfig            | gs501_defconfig           |
| Kernel base          | 5.10                       | 6.12 LTS                  |

## Legend

| Icon | Meaning                                  |
|:----:|------------------------------------------|
| ✅   | Works / available (mainline-upstream)     |
| 🚧   | Downstream-only or patch / bring-up needed|
| ⬜   | Pending device / firmware / bring-up      |
| ❌   | Not implemented / not upstream            |
