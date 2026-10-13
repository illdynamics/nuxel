# Nuxel → Motorola Moto G7 Power — Implementation Prompt for the Build Agent

> **How to use this file:** copy the entire block below the `PROMPT-START`
> marker and paste it into your agent. The rest of this file is the prompt
> itself plus acceptance criteria, so the agent has everything it needs without
> guessing.

<!-- PROMPT-START -->

## Role

You are a senior embedded-Linux / phone-OS bring-up engineer working on the
**Nuxel** repository at `/Users/wicked/x/nuxel` (the repo root). Your job is to
implement the **Motorola Moto G7 Power (Snapdragon 632, codename `ocean`)** as a
second, fully-separated hardware target alongside the existing **Google Pixel
10 Pro XL (mustang)** target — without breaking the mustang scaffold and
without ever cross-flashing device-specific firmware, drivers, kernels, or
images.

## Non-negotiable safety rules

1. **Every device-specific artifact is stored under a per-device directory**
   (see layout below) and selected by an explicit device key:
   `google-pixel-10-pro-xl` (key `mustang`), `g7power` (key `g7power`,
   codename `ocean`), and `s10plus` (key `s10plus`, codename `beyond2lte`).
2. **No device file may contain multiple devices' data.** Shared code must be
   device-agnostic (userspace services, PWA, sandbox configs, generic tools).
3. **The G7 Power is a Qualcomm/moto device and DOES use `fastboot`.** But the
   unlock step and the `lk2nd` chainload are distinct from the mustang Google ABL
   flow — do not reuse mustang's `vendor_boot`/`init_boot`/`vbmeta`/`fastbootd`
   logic for it.
4. **Verify device identity before every flash.** `fastboot getvar product` must
   be `ocean` (or the exact reported value); refuse on mismatch.
5. **Never touch** `modemst1`, `modemst2`, `fsg`, `fsc`, `ddr`, `persist`,
   `misc` — these hold per-unit calibration (IMEI, MAC, radio calibration).
6. **`fastboot flash dtbo dtbo.img` must precede `lk2nd`** on msm8953 — a
   missing/corrupt dtbo is the classic soft-brick.
7. **Do not relock the bootloader** (`fastboot oem lock`) while testing.
8. Do not invent or fabricate firmware blobs, checksums, device IDs, or driver
   status. Mark unknown values explicitly as `UNKNOWN` / `TBD` and require the
   operator to fill them from a real device.

## Verified context you must rely on (do not hallucinate)

### Current repo state (deep-analyzed)

- Nuxel v0.2.0 is a **mustang-only scaffold**, not a flashable OS. `README.md`
  and `QUICKSTART.md` say so explicitly.
- `kernel/build-kernel.sh` builds public GKI `android16-6.12` and merges
  `kernel/defconfig` (gs501/mustang fragment). The real `gs501_defconfig` is in
  a private Google vendor tree.
- `images/build.sh` emits a generic `NUXELBOOT1` bundle or an Android boot
  header v4 (`ANDROID!`) only when `kernel/.build/out/Image.gz` + DTB exist.
- `images/bootpack/mkbootimg.py` implements **only boot header v3/v4** — the
  G7 Power requires **v1** (legacy header, kernel + ramdisk, page 2048).
- `boot/flash.sh` is mustang-only (Google ABL, `vendor_boot`, `init_boot`,
  `vbmeta`, A/B `fastbootd` super flashing).
- `firmware/manifest.yml`, `firmware/install-firmware.sh`,
  `firmware/verify-firmware.sh` are mustang-only.
- `device/deviceinfo` and `device/APKBUILD` are mustang-only.
- `configs/` holds mustang display/libinput/alsa-ucm/modem/pipewire/wireplumber.
- `images/mkrootfs.sh` is device-agnostic userspace (Phosh/Flatpak/PWA).
- `boot/initramfs/init.sh` parses `nuxel.device=`, `nuxel.slot=`, `root=`,
  `rootfstype=` and probes root via `/dev/disk/by-partlabel/system_${SLOT}`
  then generic devices; it must be extended for the G7 Power eMMC A-only layout.

### Motorola Moto G7 Power (ocean) verified facts

- Device: Motorola Moto G7 Power (XT1955), codename **`ocean`**.
- SoC: **Qualcomm Snapdragon 632 (SDM632)** — 4× Kryo 250 Gold (Cortex-A73) @1.8 GHz
  + 4× Kryo 250 Silver (Cortex-A53) @1.8 GHz, 14 nm.
- GPU: Adreno 506 → mainline **freedreno** (MSM DRM).
- RAM 3/4 GB LPDDR3; storage 32/64 GB **eMMC** + microSD.
- Display: 6.2" IPS LCD **1520×720**, 19:9; backlight TI LM3697 (i2c_5 @ 0x36).
- Touch: Ilitek **ILI2117** (i2c_3 @ 0x41, IRQ tlmm 65, inverted-x) — mainline `ili210x`.
- WiFi/BT: Qualcomm **WCN3680B** (802.11 b/g/n, BT 4.2) — integrated; WiFi = `wcn36xx` + QCOM_WCNSS_PIL, BT = hci_qca.
- Modem: Qualcomm Snapdragon X9 LTE (integrated).
- Audio: Qualcomm **WCD9335 (cajon-v2)** ASoC.
- Sensors: Bosch BMI160 (accel+gyro), MEMSIC MMC3630KJ (magnetometer), AMS TMD2725 (prox+ALS).
- NFC: none (most ocean variants) — *verify on device*.
- Battery 5000 mAh, 15 W TurboPower.
- Shipped kernel: Qualcomm **4.9 downstream**.
- Boot model: **A-only** (no A/B slots); `boot`/`system`/`vendor`/`dtbo` separate.
- Boot image: **legacy header v1** (page 2048).
- Flash tooling: **`fastboot`** + **`lk2nd`** + **EDL (9008)** for unbrick.
- Unlock: `fastboot oem unlock <MOTOROLA_CODE>` (one-time code from the portal).
- Community resources:
  - postmarketOS generic msm8953 port: device `device-qcom-msm8953`, kernel
    `linux-postmarketos-qcom-msm8953` (mainline). Covers SDM450/625/626/632.
    Wiki: `https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_450/625/626/632_(MSM8953)`
  - postmarketOS Moto G7 Power page:
    `https://wiki.postmarketos.org/wiki/Motorola_Moto_G7_Power_(motorola-ocean)`
  - lk2nd mainline bootloader: `https://github.com/msm8916-mainline/lk2nd`
  - msm8953 mainline kernel: `https://github.com/msm8953-mainline/linux`
  - msm8953 ALSA UCM configs: `https://github.com/msm8953-mainline/alsa-ucm-conf`
  - Motorola unlock portal:
    `https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device`

### G7 Power boot chain (verified from postmarketOS)

Stock **ABOOT** cannot boot a mainline kernel. The msm8953 port uses **`lk2nd`**
(mainline Qualcomm bootloader) chainloaded from the stock `boot` partition, which
then loads the mainline kernel + mainline device tree.

pmOS-proven flash sequence (the Nuxel script must mirror this):
```sh
fastboot flash dtbo dtbo.img            # stock dtbo (must be re-flashed)
fastboot flash boot lk2nd.img           # install lk2nd
# reboot into lk2nd's fastboot, then:
fastboot flash boot boot.img            # mainline kernel + Nuxel initramfs
fastboot flash userdata nuxel-rootfs.img  # or flash to system
fastboot reboot
```

> **Touch is now identified** (Ilitek ILI2117 @ i2c_3 0x41) and the upstream
> ocean DTS carries the touch node, but community reports still show the generic
> image booting with **no touchscreen** on some units, so display/touch remains a
> Phase-1 verification task. EDL (Qualcomm 9008) is the unbrick path and must be
> verified **before** the first flash.

## Target directory layout to implement

Do **not** delete the current mustang files; move/copy them into per-device
directories while keeping symlinks or thin wrappers at the old paths for
backward compatibility, and clearly document the new canonical paths. Add the
`s10plus/` slots as stubs too so the tree is uniformly three-device.

```
firmware/
  google-pixel-10-pro-xl/   manifest.yml install-firmware.sh verify-firmware.sh blobs/
  g7power/                  manifest.yml install-firmware.sh verify-firmware.sh blobs/
  s10plus/                  manifest.yml install-firmware.sh verify-firmware.sh blobs/
kernel/
  google-pixel-10-pro-xl/   defconfig patches/ README-toolchain.md
  g7power/                  defconfig patches/ README-toolchain.md build-kernel.sh
  s10plus/                  defconfig patches/ README-toolchain.md build-kernel.sh
device/
  google-pixel-10-pro-xl/   deviceinfo APKBUILD 90-nuxel-mustang.rules nuxel-mustang.conf
  g7power/                  deviceinfo APKBUILD 90-nuxel-ocean.rules nuxel-ocean.conf
  s10plus/                  deviceinfo APKBUILD 90-nuxel-beyond2lte.rules nuxel-beyond2lte.conf
boot/
  google-pixel-10-pro-xl/   flash.sh recovery.sh boot-config.txt
  g7power/                  flash.sh recovery.sh boot-config.txt pack-boot-v1.sh lk2nd/
  s10plus/                  flash.sh recovery.sh boot-config.txt pack-boot-v1.sh uboot-chainload.sh
configs/
  google-pixel-10-pro-xl/   display libinput alsa-ucm modem pipewire wireplumber
  g7power/                  display libinput alsa-ucm modem pipewire wireplumber
  s10plus/                  display libinput alsa-ucm modem pipewire wireplumber
images/
  google-pixel-10-pro-xl/   build.sh mkrootfs.sh avb rauc
  g7power/                  build.sh (G7 Power boot/rootfs build)
  s10plus/                  build.sh (S10+ boot/vendor build)
tools/                      # SHARED device-agnostic (sign-image, gen-keys, dedupe-assets, ...)
```

## Device selection mechanism (must be easy and explicit)

Implement a single shared selector used by every per-device script:

- Environment variable: `NUXEL_DEVICE` (values: `mustang`, `g7power`, `s10plus`).
- Equivalent CLI flag on build/flash scripts: `--device <mustang|g7power|s10plus>`.
- Resolution order: CLI flag > `NUXEL_DEVICE` > explicit error if unset.
- Map keys to dirs:
  - `mustang` → `google-pixel-10-pro-xl`
  - `g7power` → `g7power` (codename `ocean`)
  - `s10plus` → `s10plus` (codename `beyond2lte`)
- Every script must print the resolved device key + directory at startup and
  abort (exit non-zero) if required per-device files are missing.

---

## Tasks (implement in this order)

### Task 1 — Refactor mustang into its per-device directory (preserve behavior)

Move/copy the current mustang-specific files into `google-pixel-10-pro-xl/`
subdirs, then make the top-level scripts dispatch by `--device mustang`:

- `firmware/manifest.yml`, `firmware/install-firmware.sh`,
  `firmware/verify-firmware.sh` → `firmware/google-pixel-10-pro-xl/`.
- `kernel/defconfig`, `kernel/patches/`, `kernel/README-toolchain.md` →
  `kernel/google-pixel-10-pro-xl/`.
- `device/deviceinfo`, `device/APKBUILD`, the mustang udev/modprobe snippets →
  `device/google-pixel-10-pro-xl/`.
- `boot/flash.sh`, `boot/recovery.sh`, mustang boot config →
  `boot/google-pixel-10-pro-xl/`.
- `configs/` mustang display/libinput/alsa-ucm/modem/pipewire/wireplumber →
  `configs/google-pixel-10-pro-xl/`.
- `images/build.sh`, `images/mkrootfs.sh`, `images/avb/`, `images/rauc/`,
  `images/ostree/`, `images/build-ota.sh` → keep as the **mustang/VM default**
  but add `--device mustang` handling and read inputs from the per-device dirs.

**Acceptance:** `NUXEL_DEVICE=mustang bash images/build.sh --quick` and
`bash boot/google-pixel-10-pro-xl/flash.sh --help` still run (as far as the
current scaffold allows) and report device key `mustang`. No behavior regressed
for the existing VM/PWA paths.

### Task 2 — Scaffold the G7 Power device package

Create `device/g7power/deviceinfo` and `device/g7power/APKBUILD` using the
verified SDM632 facts above. Touch and audio are already identified
(ILI2117 touch, WCD9335 codec) — set those explicitly. Mark only the
camera/sensor component names as `UNKNOWN — collect from real device`. Set:

- `deviceinfo_arch=aarch64`
- `deviceinfo_name="Motorola Moto G7 Power"`, `deviceinfo_codename=ocean`
- `deviceinfo_soc="Qualcomm Snapdragon 632 (SDM632)"`, `deviceinfo_soc_family=msm8953`
- `deviceinfo_gpu="Adreno 506"`
- `deviceinfo_display="6.2\" IPS LCD 1520x720"`
- `deviceinfo_boot_header_version=1` (legacy, page 2048)
- `deviceinfo_boot_slots="none"` (A-only) + note ABOOT→lk2nd chainload
- `deviceinfo_flash_method=fastboot` (with lk2nd + EDL recovery notes)
- `deviceinfo_kernel="linux-postmarketos-qcom-msm8953"`
- `deviceinfo_kernel_cmdline` with `nuxel.device=g7power`, console, and
  root placeholders appropriate to the A-only eMMC `userdata`/`system` layout.

Also create `device/g7power/90-nuxel-ocean.rules` and
`device/g7power/nuxel-ocean.conf` as **stubs** the operator fills from
real-device inventory (Task 8).

**Acceptance:** files exist, parse cleanly, and no mustang value is copied into
the G7 Power device package.

### Task 3 — G7 Power firmware manifest + extractor

Create `firmware/g7power/manifest.yml` with categories for the Qualcomm msm8953
stack and mark every source path/checksum as `UNKNOWN`/`PLACEHOLDER` until a
device dump is available:

- `gpu` (Adreno 506): `a506_zap.mbn` + `qcom/` firmware.
- `wifi_bt` (WCN3680B): WCNSS firmware + `wlan_mac.bin`/NVRAM.
- `audio` (WCD9335/cajon-v2): codec/DSP firmware.
- `display`, `touch`, `camera`, `sensors`, `modem` (X9 LTE DSP — protect modemst).

Implement `firmware/g7power/install-firmware.sh` and
`firmware/g7power/verify-firmware.sh` modeled on the mustang versions but
**completely independent** (different manifest, different `--device`, different
blob paths). Include `--list-files`, `--verify-only`, `--checksums`, and the
same consistency gate. Add a **fastboot/`adb` pull mode** that extracts
`/vendor/firmware`, `/vendor/firmware_mnt`, and `/vendor/lib/modules` from the
device.

**Acceptance:** `NUXEL_DEVICE=g7power firmware/g7power/install-firmware.sh --list-files`
runs without touching mustang files and reports the G7 Power manifest; the
script refuses to install anything until real blob hashes are filled (or runs
in "pending" mode).

### Task 4 — G7 Power kernel build wrapper + defconfig

Create:

- `kernel/g7power/defconfig` — an msm8953 fragment. It must **not** copy
  mustang's `gs501`/BCM4390/PowerVR assumptions. Instead enable/keep:
  `CONFIG_DRM`, MSM DRM/DSI, freedreno (`CONFIG_DRM_MSM`), `CONFIG_WCN36XX`
  + `CONFIG_QCOM_WCNSS_PIL` (WCN3680B — **not** ath10k), `CONFIG_TOUCHSCREEN_ILI210X`,
  WCD9335 ASoC, `CONFIG_EXT4_FS`/`CONFIG_F2FS_FS`,
  `CONFIG_DEVTMPFS`, namespaces/seccomp/AppArmor where the msm8953 tree
  supports them, and the Nuxel `drivers/nuxel/` features **only if the patch
  applies**. Annotate any 6.12-only symbol that cannot exist in the msm8953 tree.
- `kernel/g7power/build-kernel.sh` — a wrapper that clones/builds
  `linux-postmarketos-qcom-msm8953` (from `msm8953-mainline/linux`), applies
  `kernel/g7power/patches/`, builds `Image.gz` + DTB with `aarch64-linux-gnu-`
  (or clang), and writes artifacts under `kernel/g7power/.build/out/`.
- `kernel/g7power/patches/` — port the Nuxel boot-param/phone feature patch to
  the msm8953 tree, or a stub patch with a documented TODO if it does not
  apply cleanly.

**Acceptance:** `NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --help`
prints SDM632/msm8953 context; running it (when network + toolchain are
available) produces `kernel/g7power/.build/out/Image.gz` and an msm8953 DTB, and
never touches `kernel/google-pixel-10-pro-xl/`.

### Task 5 — G7 Power boot image packer + lk2nd chainload + flash/recovery scripts

Create `boot/g7power/pack-boot-v1.sh` that builds a **legacy Android boot image
header v1 (page 2048)** (kernel + ramdisk). Do **not** reuse the mustang v4
`vendor_boot`/`init_boot`/`vbmeta` flow.

Create `boot/g7power/lk2nd/` scaffolding that documents/ships the `lk2nd` build
(from `msm8916-mainline/lk2nd`) and its `lk2nd.img` output.

Create `boot/g7power/flash.sh` implementing the pmOS-proven fastboot sequence, with:

- `--device g7power` required/verified (`fastboot getvar product` == `ocean`).
- `fastboot flash dtbo dtbo.img` → `fastboot flash boot lk2nd.img` → reboot into
  lk2nd fastboot → `fastboot flash boot boot.img` → `fastboot flash userdata <rootfs.img>`.
- `--rootfs-partition` override (userdata vs system).
- `--unlock` helper that documents the Motorola `fastboot oem unlock <code>` step
  (the code itself is operator-supplied).
- `--revert` mode that re-flashes the backed-up stock `boot` + `dtbo`.
- `--edl` helper/notes for the Qualcomm 9008 unbrick path.
- Explicit warnings that `dtbo` must be flashed before `lk2nd`.

Create `boot/g7power/recovery.sh` adapted for fastboot/`adb`/EDL recovery and
`boot/g7power/boot-config.txt`.

**Acceptance:** `bash boot/g7power/flash.sh --help` prints the fastboot + lk2nd
sequence and safety warnings; the script exits early without a connected G7
Power and never references mustang partitions.

### Task 6 — G7 Power rootfs/boot build orchestration

Create `images/g7power/build.sh` (or `images/build.sh --device g7power`) that
consumes `kernel/g7power/.build/out/` + `boot/g7power/pack-boot-v1.sh` and
produces the G7 Power `boot.img` and a `userdata`-targeted Nuxel rootfs (with
the msm8953 modules installed). Reuse the **device-agnostic** `mkrootfs.sh`
userspace assembly, but do not require dm-verity/AVB for the first G7 Power boot.

**Acceptance:** build orchestration is fully separated from mustang and emits
artifacts under a clearly named `g7power` output dir, with a build manifest
recording the device key.

### Task 7 — Configs for G7 Power

Create `configs/g7power/` with:

- `display/` script applying 1520×720 mode via `wlr-randr`.
- `libinput/` touch calibration (values marked `UNKNOWN` until real device).
- `alsa-ucm/` + `pipewire/` + `wireplumber/` stubs for the WCD9335/cajon-v2
  codec (reference the `msm8953-mainline/alsa-ucm-conf` examples).
- `modem/` stub documenting that the X9 LTE modem is **not** ModemManager-ready.

**Acceptance:** configs exist, are device-keyed, and no mustang display/touch
values leak into G7 Power.

### Task 8 — Operator device-inventory template + gate

Add a template (e.g. `docs/g7power-device-inventory.md` or a `getprop`/`dmesg`
collection script) that captures the **remaining unknowns** (camera sensors,
sensor-hub confirmation, exact WiFi/BT firmware filenames under `/vendor/firmware`,
modem interface, bootloader revision). Touch/panel/audio/WiFi are already known
(ILI2117, LM3697, WCD9335, WCN3680B). Wire the G7 Power build/flash scripts to **fail
with a clear message** if required inventory fields are still `UNKNOWN`, so
nobody flashes a half-specified image.

### Task 9 — Documentation

Update `README.md`, `QUICKSTART.md`, and add `docs/g7power-bringup.md`
explaining:

- The multi-device model and `NUXEL_DEVICE` / `--device` selection
  (`mustang` / `g7power` / `s10plus`).
- The G7 Power boot chain (ABOOT → lk2nd → Linux) and fastboot/EDL model.
- Exact build + flash commands for the G7 Power.
- The anti-cross-flash rules and the known touchscreen gap.

---

## Acceptance criteria (definition of done)

1. `make`/VM/PWA mustang paths still pass their existing (scaffold-level)
   checks with `NUXEL_DEVICE=mustang`.
2. `NUXEL_DEVICE=g7power` selects only `g7power` directories everywhere.
3. Every device-specific file lives under a per-device dir; a grep for
   `mustang` inside `g7power/` and `g7power`/`ocean` inside
   `google-pixel-10-pro-xl/` returns no device-coupling (except documented
   cross-references).
4. G7 Power flash script refuses on device mismatch, flashes `dtbo` before
   `lk2nd`, and provides a one-command revert to stock `boot`/`dtbo`.
5. No fabricated checksums/IDs: all unknowns are `UNKNOWN`/`PLACEHOLDER` with a
   real-device collection step.
6. All new shell scripts pass `bash -n` and `shellcheck` (where available).
7. Build/flash scripts print the resolved device key and abort on missing
   per-device inputs.
8. New docs are present and consistent with `g7power-requirements.md`.

---

## Deliverables to produce in the repo

- The per-device directory tree above, fully populated with code + stubs
  (including the `s10plus/` stub slots for consistency).
- `docs/g7power-bringup.md`.
- Updated `README.md` / `QUICKSTART.md`.
- `docs/g7power-device-inventory.md` (operator template).
- No changes to the committed userspace services/PWA/sandbox unless needed to
  make them device-agnostic (and if changed, keep them working for mustang/VM).

## Explicit things you must NOT do

- Do not claim the G7 Power or mustang path is "flashable/verified" until the
  required device inventory + real firmware + real kernel build are complete.
- Do not reuse Pixel/Broadcom/PowerVR firmware for the G7 Power.
- Do not relock the bootloader.
- Do not touch `modemst1`/`modemst2`/`fsg`/`fsc`/`ddr`/`persist`/`misc`.
- Do not skip the `dtbo`-before-`lk2nd` step.
- Do not delete or overwrite mustang files without preserving a working path.

<!-- PROMPT-END -->

---

## Operator quick reference (not part of the agent prompt)

This section is for you (the human), so you know the *immediate* next physical
step before handing work back to the agent.

### Reality check

Neither target is flashable today. The mustang path is an aspirational scaffold,
and the G7 Power path is a **new** mainline msm8953 bring-up (built on the
postmarketOS `qcom-msm8953` port). The agent's job is to build the
correctly-separated scaffolding + real G7 Power tooling, **not** to pretend a
bootable image already exists.

### First physical action (Phase 0 — device inventory + unlock + EDL check)

Before trusting any firmware/driver list:

```sh
# Unlock (one-time, via Motorola portal code)
adb reboot bootloader
fastboot getvar all                # capture product (ocean), serial, slot info
fastboot oem get_unlock_data       # paste into Motorola portal -> get code
fastboot oem unlock <UNLOCK_CODE>  # wipes device

# Verify EDL (Qualcomm 9008) unbrick path BEFORE flashing anything
#   power off, hold Vol Down + Vol Up, plug USB -> host should show Qualcomm 9008

# After rebooting back into stock Android:
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|qcom|msm'
adb shell dmesg > g7power-dmesg.txt
adb shell getevent -pl             # identify touchscreen/input controllers
adb shell ls -R /vendor/firmware /vendor/firmware_mnt /vendor/lib/modules
```

Feed the captured `g7power-dmesg.txt`, `getevent`, and vendor listings back into
`docs/g7power-device-inventory.md` and `firmware/g7power/manifest.yml` before
the first lk2nd/flash.

### Back up the stock boot/recovery/modem images before any modification

```sh
adb shell "dd if=/dev/block/bootdevice/by-name/boot of=/sdcard/boot.img; dd if=/dev/block/bootdevice/by-name/recovery of=/sdcard/recovery.img; dd if=/dev/block/bootdevice/by-name/dtbo of=/sdcard/dtbo.img"
adb pull /sdcard/boot.img /sdcard/recovery.img /sdcard/dtbo.img
```

### Minimal flash + revert commands (G7 Power, once images exist)

```sh
# Install lk2nd + flash Nuxel rootfs
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh --device g7power

# Revert to stock at any time
fastboot flash dtbo dtbo.img
fastboot flash boot boot.img      # backed-up stock boot
fastboot reboot
```

### How the devices stay separated

- Firmware: `firmware/google-pixel-10-pro-xl/` vs `firmware/g7power/` vs `firmware/s10plus/`
- Kernel: `kernel/google-pixel-10-pro-xl/` vs `kernel/g7power/` vs `kernel/s10plus/`
- Device: `device/google-pixel-10-pro-xl/` vs `device/g7power/` vs `device/s10plus/`
- Boot/flash: `boot/google-pixel-10-pro-xl/` vs `boot/g7power/` vs `boot/s10plus/`
- Configs: `configs/google-pixel-10-pro-xl/` vs `configs/g7power/` vs `configs/s10plus/`
- Images: `images/google-pixel-10-pro-xl/` vs `images/g7power/` vs `images/s10plus/`
- Shared (device-agnostic): `services/`, `shell/`, `pwa/`, `tools/`, `vm/`
