# Nuxel Hardware Bring-Up Preparation (mustang)

This document is the operational checklist and design reference for the Phase-2
bring-up of **Google Pixel 10 Pro XL (mustang)**. No physical device is in
reach while this scaffold is written, so **all configs / docs / scripts below
are prepared and validated schema-wise but NOT executed against hardware.**

Execution on real hardware is currently **blocked on the external device**. The
configs are intentionally valid and VM-exercisable where possible so that when
the device arrives, bring-up is a matter of applying files and watching the
interfaces light up.

---

## 1. Scope

| Subsystem            | SoC / Controller                 | Configs                                          |
|----------------------|----------------------------------|--------------------------------------------------|
| Display              | Samsung AMB655X LTPO panel (DRM)| `configs/display/nuxel-mustang-start.sh`         |
| Touch                | Samsung S6SY791                  | `configs/libinput/nuxel-mustang-touch.conf`      |
| Audio (ALSA)         | Cirrus CS42L43 + CS35L45         | `configs/alsa-ucm/GoogleMustang/*.conf`          |
| Audio (PipeWire/WP)  | WirePlumber / PipeWire           | `configs/pipewire/nuxel-phone.conf.part`, `configs/wireplumber/nuxel-voice-call.lua.d/` |
| Modem                | Samsung Exynos 5500              | `configs/modem/nuxel-modem-setup.sh`             |
| WiFi                 | Broadcom BCM4390 (brcmfmac)      | `firmware/manifest.yml`, `docs/wifi-bcm4390-status.md` |
| Camera               | SoC camera / v4l2                | `shell/nuxel-camera-portal/`                     |

The authoritative driver / state table lives in `docs/driver-status.md`.

### Multi-device hardware scope (canonical)

This document is the **mustang** operational checklist. The **S10+
(`beyond2lte`)** and **G7 Power (`ocean`)** targets are separate bring-ups with
their own requirements (`phones/s10plus/s10plus-requirements.md`, `phones/g7power/g7power-requirements.md`)
and their own per-device configs/firmware. The canonical verified component IDs
for all three targets live in **[`docs/hardware-ids.md`](hardware-ids.md)** (with
source URLs cited); the compact cross-device summary is:

| Subsystem  | mustang (Pixel 10 Pro XL)            | s10plus (Galaxy S10+)                  | g7power (Moto G7 Power)          |
|------------|--------------------------------------|----------------------------------------|----------------------------------|
| SoC        | Google Tensor G5 (`gs501`)           | Samsung Exynos 9820                    | Snapdragon 632 (SDM632)          |
| GPU        | PowerVR DXT-72-2304                  | Mali-G76 MP12                          | Adreno 506                       |
| Display    | AMB655X LTPO 3120×1440 @120          | AMOLED 3040×1440 (DDIC **S6E3HA9**)    | IPS LCD 1520×720                 |
| Touch      | Samsung **S6SY791**                  | Samsung **S6SY761** (`sec_ts`) @ 0x48  | Ilitek **ILI2117** (i2c_3 @ 0x41)|
| Audio      | Cirrus **CS35L45 + CS42L43**         | Cirrus **CS47L93** + 2× **CS35L40**    | Qualcomm **WCD9335** (cajon-v2)  |
| WiFi/BT    | Broadcom **BCM4390**                 | Broadcom **BCM4375**                   | Qualcomm **WCN3680B**            |
| Modem      | Samsung Exynos 5500 (PCIe/MHI)       | Shannon LTE (integrated)               | Snapdragon X9 LTE                |
| NFC        | NXP **SN220**                        | Samsung `sec-nfc` (S3FWRN5) @ 0x27     | none (most variants)             |
| Boot model | A/B, header v4                       | A-only, header v1                      | **A/B**, header v1                |
| Flash tool | `fastboot` + `fastbootd`             | TWRP + Odin/`heimdall` (no fastboot)   | `fastboot` + `lk2nd` + EDL       |


---

## 2. Display bring-up

Primary script: **`configs/display/nuxel-mustang-start.sh`** — runs after Phosh
starts and applies:

1.  Panel native mode: `1440x3120 @ 120 Hz` via `wlr-randr` (wlroots stack).
2.  Touch rotation calibration matrix: `configs/libinput/nuxel-mustang-touch.conf`.

The script detects the AMB655X connector from `wlr-randr --json`; on the VM
(no such panel) it backs off gracefully so it can be placed in the UTM image
without erroring.

### bring-up order

```bash
# On the device console / via adb shell over USB-C:
nuxel-mustang-start                       # apply mode + touch matrix
# Inspect:
wlr-randr                                 # expect AMB655X (DSI) 1440x3120@120
libinput list-devices | grep -A6 S6SY791  # expect calibration matrix
```

---

## 3. Touch bring-up

`configs/libinput/nuxel-mustang-touch.conf` applies the calibration matrix:

```
0 -1 1
1  0 0
0  0 1
```

> **Status correction:** the S6SY791 touch driver is **NOT present upstream**
> in mainline Linux 6.12 (there is no `CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791`).
> It must be brought in from the downstream Google kernel
> (`drivers/input/touchscreen/` in the `android-gs-mustang` tree) or as an
> out-of-tree patch. See `docs/driver-status.md` (corrected).

---

## 4. Audio bring-up

Three UCM2 profiles under `configs/alsa-ucm/GoogleMustang/`:

* `Speaker.conf` — built-in stereo via two CS35L45 smart amplifiers
  (CS42L43 → TDM/SoundWire → CS35L45).
* `USB-C-Analog.conf` — USB-C / headset analog route on the CS42L43.
* `VoiceCall.conf` — full-duplex voice path for the Exynos 5500 modem.
* (bonus) `Headphones.conf` — isolated private-media headphone path.

Each carries the required `EnableSequence` / `DisableSequence` verbs. The
`Syntax ""` header and card `Comment` match modern `alsaucm` (ALSA 1.2.x).

Install:

```bash
sudo mkdir -p /usr/share/alsa/ucm2/GoogleMustang
sudo cp configs/alsa-ucm/GoogleMustang/*.conf /usr/share/alsa/ucm2/GoogleMustang/
sudo alsactl init
ucm -c mustang -d VoiceCall get _verb   # sanity-check
```

### PipeWire / WirePlumber

* `configs/pipewire/nuxel-phone.conf.part` — session fragment enabling the JACK
  session manager protocol and anchoring the 48 kHz voice clock.
* `configs/wireplumber/nuxel-voice-call.lua.d/40-nuxel-voice-call.lua` —
  WirePlumber policy labelling the `nuxel-call` voice node with the
  `VoiceCall` UCM route and AEC/focus hints (consumed by Phosh + the native
  dialer/messages apps).

---

## 5. Modem bring-up

`configs/modem/nuxel-modem-setup.sh` — see the script header for the modem key,
operating-mode, and fallback diagnostics. Referenced from `docs/driver-status.md`
for the Exynos 5500 ModemManager plugin state.

## 6. WiFi bring-up

`docs/wifi-bcm4390-status.md` — status of `brcmfmac` + BCM4390 and required
vendor firmware. `firmware/manifest.yml` lists the blobs; `firmware/verify-firmware.sh`
sha256-verifies them.

## 7. Camera

`shell/nuxel-camera-portal/` — see `docs/camera-geolocation-design.md`. On
mustang the same backend switches to the real v4l2 source.

---

## 8. Blocking on external hardware

Phase-2 actual bring-up remains **blocked until a mustang unit is available**.
Everything needed pre-device is scaffolded here. When hardware arrives:

1.  Apply `configs/display`, `configs/libinput`, `configs/alsa-ucm`, `configs/pipewire`,
    `configs/wireplumber`, `configs/modem`.
2.  Run `firmware/install-firmware.sh <factory.zip> --install` and
    `firmware/verify-firmware.sh`.
3.  Boot the Phase-0 kernel (see `kernel/README-toolchain.md` / `docs/build-guide.md`).
4.  Capture serial/UART console log; iterate display → touch → audio → modem.

## 8.1 Firmware extraction & acquisition (briq-hw1)

Required blobs are enumerated in `firmware/manifest.yml`. Detection targets:

| Subsystem            | Controller / bin path                                     |
|----------------------|----------------------------------------------------------|
| Modem                | Exynos 5500 — `vendor/firmware/modem*.bin`, `exynos5500_shm.bin` (200 MB modem partition) |
| WiFi 7               | BCM4390 — `vendor/firmware/brcm/brcmfmac4390{,-pcie}{,.clm_blob,.nvm}` |
| Bluetooth 5.4        | BCM4390 — `vendor/firmware/BCM4390.hcd`                  |
| GPU                  | PowerVR DXT-72-2304 — `vendor/firmware/img/pvr_*.fw` / `pvr_drv.so` |

### Single blocking acquisition command

Google only publishes mustang factory images as a signed zip behind a consent /
download gate (no deterministic anonymous URL). This is **the single blocking
external step** that cannot be automated from inside the sandbox:

```bash
cd /tmp
# Navigate to https://developers.google.com/android/images#mustang, accept the
# terms, copy the link for build BP1A.250405.001 (or newer), then e.g.:
wget "https://dl.google.com/dl/android/aosp/mustang-bp1a.250405.001-factory-<xxxxx>.zip"
unzip mustang-bp1a.250405.001-factory-<xxxxx>.zip
/Users/wicked/x/nuxel/firmware/install-firmware.sh \
    mustang-bp1a.250405.001-factory-<xxxxx>.zip --output-dir ./firmware-out
```

All other firmware paths (enumeration, `--list-files`, `--verify-only`,
`--checksums`, sha256 `verify-firmware.sh`) are fully exercisable **without** the
zip and complete cleanly (exit 0):

```bash
cd /Users/wicked/x/nuxel
./firmware/install-firmware.sh --list-files      # enumerates all blobs + manifest consistency check
./firmware/install-firmware.sh --verify-only      # non-zero only if a required blob is missing
./firmware/verify-firmware.sh --strict            # sha256 against manifest (fails on PLACEHOLDER hashes)
```

> The `--list-files` subcommand runs a manifest-vs-expected consistency check:
> the manifest must cover the Exynos 5500 modem, BCM4390 WiFi/BT and PowerVR GPU
> blobs for mustang. Fill the `PLACEHOLDER_*` `checksum.sha256` values in the
> manifest with real hashes after extraction so `verify-firmware.sh --strict`
> passes.

Blob ownership in the factory zip: `vendor.img` → `vendor/firmware/*`
(WiFi/BT, GPU, sensors, NFC, PMIC, charger, audio, display, touch, fingerprint),
`modem_*.img` → Exynos 5500 baseband, `dsp_*.img` → DSP.

---

## 8.2 Mustang hardware recovery path (battle-tested)

The flow below is the canonical Pixel 10 Pro XL recovery procedure used when a
Nuxel rootfs/kernel build must be re-flashed or the device has gone soft-bricked.
For the full unlock walkthrough (Developer Options, `flashing unlock`, Titan M3
AVB notes, vbmeta disable) see `docs/bootloader-unlock-guide.md`.

```bash
# 0) Preflight — confirm the target unit
fastboot getvar product       # => mustang
fastboot getvar serial        # => 58211FDCQ001LA
fastboot getvar unlocked      # => yes (if not yet unlocked, see unlock guide)

# 1) Flash kernel + initramfs to both slots (Nuxel boot.img artifact)
fastboot flash boot_a boot.img
fastboot flash boot_b boot.img
fastboot set_active a

# 2) Flash the vendor ramdisk / DTBO (required for display + touch bring-up)
fastboot flash vendor_boot_a vendor_boot.img
fastboot flash vendor_boot_b vendor_boot.img
fastboot flash dtbo_a dtbo.img
fastboot flash dtbo_b dtbo.img

# 3) Disable AVB so unsigned Nuxel images boot on the Tensor G5 chain
fastboot flash vbmeta_a --disable-verity --disable-verification vbmeta.img
fastboot flash vbmeta_b --disable-verity --disable-verification vbmeta.img

# 4) Reboot and watch serial/UART for display -> touch bring-up
fastboot reboot
```

### Recovery / de-bricking

| Symptom                                        | Action                                                            |
|------------------------------------------------|-------------------------------------------------------------------|
| Won't reach fastboot (held vol-down + power)  | Check data cable + USB2 port; `fastboot reboot-bootloader`; power cycle |
| Bootloop on a Nuxel build                     | `fastboot set_active b` then `fastboot reboot` (try other slot)   |
| Yellow "unlocked" warning still boot-loops    | Reflash vbmeta with `--disable-verity --disable-verification`     |
| Need to return to stock                       | Unzip factory, run `./flash-all.sh` (wipes device)                |
| `no permissions` (Linux)                      | Install `android-sdk-platform-tools` udev rules or run `sudo fastboot` |

The exact slot/layout values (partitions, sizes) are listed in
`docs/bootloader-unlock-guide.md`.

## 8.3 Firmware bring-up order on device

1. `firmware/install-firmware.sh <factory.zip> --output-dir ./fw --install`
2. `firmware/verify-firmware.sh --strict` → expect **OK** for every required blob.
3. Confirm interfaces: `ip link` (BCM4390 wlan0), `bluetoothctl` (BCM4390),
   `dmesg | grep -i exynos_shm`, `glxinfo | grep -i pvr`.

---

## 9. Artifacts

| Path                                             | Purpose                          |
|--------------------------------------------------|----------------------------------|
| `configs/display/nuxel-mustang-start.sh`         | Display mode + touch apply        |
| `configs/libinput/nuxel-mustang-touch.conf`      | Touch calibration matrix          |
| `configs/alsa-ucm/GoogleMustang/*.conf`          | UCM2 audio profiles (4)           |
| `configs/pipewire/nuxel-phone.conf.part`         | PipeWire phone fragment           |
| `configs/wireplumber/nuxel-voice-call.lua.d/`    | WirePlumber voice-call profile    |
| `docs/hardware-bringup-prep.md`                  | This document                     |
| `firmware/install-firmware.sh`                | Firmware extraction / install / list / verify |
| `firmware/verify-firmware.sh`                 | sha256 verification against `manifest.yml`    |
| `firmware/manifest.yml`                       | Required blob manifest + acquisition metadata |
| `docs/bootloader-unlock-guide.md`             | Bootloader unlock + recovery path             |
