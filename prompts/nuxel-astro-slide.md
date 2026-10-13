# Nuxel → Astro Slide 5G — Implementation Prompt for the Build Agent

> **How to use this file:** copy the entire block below the `PROMPT-START`
> marker and paste it into your agent. The rest of this file is the prompt
> itself plus acceptance criteria, so the agent has everything it needs without
> guessing.

<!-- PROMPT-START -->

## Role

You are a senior embedded-Linux / phone-OS bring-up engineer working on the
**Nuxel** repository at `/Users/wicked/x/nuxel` (the repo root). Your job is to
implement the **Astro Slide 5G Transformer** as a second, fully-separated
hardware target alongside the existing **Google Pixel 10 Pro XL (mustang)**
target — without breaking the mustang scaffold and without ever cross-flashing
device-specific firmware, drivers, kernels, or images.

## Non-negotiable safety rules

1. **Every device-specific artifact is stored under a per-device directory**
   (see layout below) and selected by an explicit device key:
   `google-pixel-10-pro-xl` (key `mustang`) and `astro-slide` (key `astro`).
2. **No device file may contain both devices' data.** Shared code must be
   device-agnostic (userspace services, PWA, sandbox configs, generic tools).
3. **The Astro Slide must keep slot A as stock Android+Magisk.** All Nuxel
   work targets **slot B only**. The fallback is always
   `fastboot set_active a && fastboot reboot`.
4. **Verify device identity before every flash.** The Astro flash script must
   check `fastboot getvar product` (and refuse unless it is the Astro product
   string), and the mustang script must continue checking `mustang`.
5. **Never touch** `persist`, `nvdata`, `nvram`, `proinfo`, `seccfg`, `tee`,
   `md1img`/modem calibration, or any per-unit calibration partition.
6. **Do not relock the Astro bootloader** while testing.
7. Do not invent or fabricate firmware blobs, checksums, device IDs, or driver
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
- `boot/flash.sh` is mustang-only (Google ABL, `vendor_boot`, `init_boot`,
  `vbmeta`, A/B `fastbootd` super flashing).
- `firmware/manifest.yml`, `firmware/install-firmware.sh`,
  `firmware/verify-firmware.sh` are mustang-only (Exynos 5500, BCM4390,
  PowerVR DXT, Samsung AMB655X, Cirrus audio, etc.).
- `device/deviceinfo` and `device/APKBUILD` are mustang-only.
- `configs/` holds mustang display/libinput/alsa-ucm/modem/pipewire/wireplumber.
- `images/mkrootfs.sh` is device-agnostic userspace (Phosh/Flatpak/PWA).

### Astro Slide 5G verified facts

- SoC: MediaTek **MT6873** (Dimensity 800), 4× Cortex-A76 + 4× Cortex-A55.
- GPU: Mali-G57 MC4 (Valhall).
- RAM 8 GB, storage 128 GB, display 6.39" AMOLED FHD+ (2340×1080), Android 11.
- Connectivity: MediaTek **MT6635** combo (WiFi 5 / BT / GPS / FM).
- Modem: integrated MT6873 5G modem.
- Shipped kernel: **4.14.186 AOSP BSP**.
- Boot model: **Virtual A/B (VAB)** dynamic partitions; `super` is 6 GB;
  `boot_a`/`boot_b` are physical; `system`/`vendor`/`product` are logical inside
  `super` with COW backing the B slot.
- Boot image: **legacy Android boot image, 2048-byte page** with
  kernel + ramdisk + recovery DTBO + DTB.
- Bootloader unlock: standard `fastboot flashing unlock` after OEM unlock.
- Community resources:
  - `https://github.com/fayep/astro-modules` (clean-room `wmt_chrdev_wifi`,
    `bt_drv`, `scalpel`, Docker `astro-kbuild`, `build.sh`, `pack-boot.sh`,
    `docs/flashing.md`).
  - `https://github.com/fayep/astro-linux-kernel-4.14` (downstream kernel;
    branches `android-11.0`, `android-12.0`, `main`, `our-wifi-work`,
    `packaging` = Gemian/Debian).
  - `https://github.com/planet-community/planet-devices`.
- postmarketOS has **no** Astro Slide port (only `planet-geminipda` and
  `planet-cosmocom`).

### Astro flash sequence (verified from `fayep/astro-modules/docs/flashing.md`)

```sh
fastboot reboot fastboot
fastboot resize-logical-partition system_b-cow 1   # only while on slot A
fastboot flash vendor_b vendor_b.img
fastboot flash boot_b boot_b_<nuxel>.img
fastboot reboot-bootloader                         # set_active fails in fastbootd
fastboot set_active b
fastboot reboot
```

## Target directory layout to implement

Do **not** delete the current mustang files; move/copy them into per-device
directories while keeping symlinks or thin wrappers at the old paths for
backward compatibility, and clearly document the new canonical paths.

```
firmware/
  google-pixel-10-pro-xl/
    manifest.yml
    install-firmware.sh
    verify-firmware.sh
    blobs/                      # gitignored
  astro-slide/
    manifest.yml
    install-firmware.sh
    verify-firmware.sh
    blobs/                      # gitignored
kernel/
  google-pixel-10-pro-xl/
    defconfig
    patches/
    README-toolchain.md
  astro-slide/
    defconfig
    patches/
    README-toolchain.md
    build-kernel.sh             # MT6873 4.14 build wrapper
device/
  google-pixel-10-pro-xl/
    deviceinfo
    APKBUILD
    90-nuxel-mustang.rules
    nuxel-mustang.conf
  astro-slide/
    deviceinfo
    APKBUILD
    90-nuxel-astro.rules
    nuxel-astro.conf
boot/
  google-pixel-10-pro-xl/
    flash.sh
    recovery.sh
    boot-config.txt
  astro-slide/
    flash.sh
    recovery.sh
    boot-config.txt
    pack-boot.sh                # legacy PAGE-2048 boot image packer
configs/
  google-pixel-10-pro-xl/       # display, libinput, alsa-ucm, modem, ...
  astro-slide/                  # display, libinput, alsa-ucm, modem, ...
images/
  google-pixel-10-pro-xl/       # build.sh, mkrootfs.sh, avb, rauc, ...
  astro-slide/                  # build.sh (Astro boot/vendor build), ...
tools/                          # SHARED device-agnostic (sign-image, gen-keys, dedupe-assets, ...)
```

## Device selection mechanism (must be easy and explicit)

Implement a single shared selector used by every per-device script:

- Environment variable: `NUXEL_DEVICE` (values: `mustang` or `astro`).
- Equivalent CLI flag on build/flash scripts: `--device <mustang|astro>`.
- Resolution order: CLI flag > `NUXEL_DEVICE` > explicit error if unset.
- Map keys to dirs:
  - `mustang` → `google-pixel-10-pro-xl`
  - `astro`  → `astro-slide`
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

### Task 2 — Scaffold the Astro device package

Create `device/astro-slide/deviceinfo` and `device/astro-slide/APKBUILD` using
the verified MT6873 facts above. Mark unknown values (`deviceinfo_touchscreen`,
`deviceinfo_audio`, `deviceinfo_camera_*`, sensor/NFC component names) as
`UNKNOWN — collect from real device`. Set:

- `deviceinfo_arch=aarch64`
- `deviceinfo_soc="MediaTek MT6873 (Dimensity 800)"`
- `deviceinfo_soc_family=mt6873`
- `deviceinfo_gpu="Mali-G57 MC4"`
- `deviceinfo_display="6.39\" AMOLED 2340x1080"`
- `deviceinfo_boot_header_version=0` (legacy, page 2048)
- `deviceinfo_boot_slots="virtual_ab"` + super/VAB notes
- `deviceinfo_flash_method=fastboot`
- `deviceinfo_kernel="Linux 4.14.186 MediaTek BSP (downstream)"`
- `deviceinfo_kernel_cmdline` with `nuxel.device=astro`, console, and root
  placeholders appropriate to slot B.

Also create `device/astro-slide/90-nuxel-astro.rules` and
`device/astro-slide/nuxel-astro.conf` as **stubs** that the operator fills from
real-device inventory (Task 8).

**Acceptance:** files exist, parse cleanly, and no mustang value is copied into
the Astro device package.

### Task 3 — Astro firmware manifest + extractor

Create `firmware/astro-slide/manifest.yml` with categories for the MTK stack
and mark every source path/checksum as `UNKNOWN`/`PLACEHOLDER` until a device
dump is available:

- `connectivity` (MT6635): `wmt_drv.ko`, `wlan_drv_gen4m.ko`, `bt_drv.ko`,
  `fmradio_drv.ko`, NVRAM/calibration files.
- `gpu`: Mali `mali_kbase.ko`, `libmali` userspace, GPU frequency/GED blobs.
- `display`, `touch`, `audio`, `camera`, `sensors`, `nfc`, `modem`.

Implement `firmware/astro-slide/install-firmware.sh` and
`firmware/astro-slide/verify-firmware.sh` modeled on the mustang versions but
**completely independent** (different manifest, different `--device`, different
blob paths). Include `--list-files`, `--verify-only`, `--checksums`, and the
same consistency gate.

**Acceptance:** `NUXEL_DEVICE=astro firmware/astro-slide/install-firmware.sh --list-files`
runs without touching mustang files and reports the Astro manifest; the script
refuses to install anything until real blob hashes are filled (or runs in
"pending" mode).

### Task 4 — Astro kernel build wrapper + defconfig

Create:

- `kernel/astro-slide/defconfig` — an MT6873 4.14 fragment. It must **not**
  copy mustang's `gs501`/BCM4390/PowerVR assumptions. Instead enable/keep:
  `CONFIG_DRM`, MediaTek DRM/DSI (`CONFIG_DRM_MEDIATEK`/DSI as present in the
  BSP), `CONFIG_MALI`/vendor Mali where the BSP provides it, MTK connectivity
  (`wmt`/`wlan`/`bt`), MTK modem/CCCI, `CONFIG_EXT4_FS`, `CONFIG_F2FS_FS`,
  `CONFIG_DEVTMPFS`, namespaces/seccomp/AppArmor where the 4.14 tree supports
  them, and the Nuxel `drivers/nuxel/` features **only if the patch applies**.
  Annotate any 6.12-only symbol that cannot exist in 4.14.
- `kernel/astro-slide/build-kernel.sh` — a wrapper that clones/builds the
  downstream MT6873 4.14 tree (`fayep/astro-linux-kernel-4.14` or Planet's GPL
  source), applies `kernel/astro-slide/patches/`, builds `Image.gz` + DTB with
  `CC=clang-11` (or the MTK toolchain), and writes artifacts under
  `kernel/astro-slide/.build/out/`.
- `kernel/astro-slide/patches/` — port the Nuxel boot-param/phone feature patch
  to 4.14, or a stub patch with a documented TODO if it does not apply cleanly.

**Acceptance:** `NUXEL_DEVICE=astro bash kernel/astro-slide/build-kernel.sh --help`
prints MT6873/4.14 context; running it (when network + toolchain are available)
produces `kernel/astro-slide/.build/out/Image.gz` and a MT6873 DTB, and never
touches `kernel/google-pixel-10-pro-xl/`.

### Task 5 — Astro boot image packer + flash/recovery scripts

Create `boot/astro-slide/pack-boot.sh` that builds a **legacy Android boot
image (2048-byte page)** by swapping the kernel/DTB into a Magisk-patched
factory boot image exactly as the community `pack-boot.sh` does (recompute
header SHA1, preserve ramdisk/DTB offsets). Do **not** reuse the mustang v4
`vendor_boot`/`init_boot`/`vbmeta` flow.

Create `boot/astro-slide/flash.sh` implementing the verified VAB sequence, with:

- `--device astro` required/verified.
- Pre-flight `fastboot getvar product` check.
- `fastboot reboot fastboot`, `resize-logical-partition system_b-cow 1`,
  `flash vendor_b`, `flash boot_b`, `reboot-bootloader`, `set_active b`,
  `reboot`.
- `--revert` mode to `set_active a` and reboot to stock.
- Explicit warnings about slot A fallback and about `set_active` only working
  from the bootloader.

Create `boot/astro-slide/recovery.sh` adapted for MTK fastboot/`adb` recovery
and `boot/astro-slide/boot-config.txt`.

**Acceptance:** `bash boot/astro-slide/flash.sh --help` prints the VAB sequence
and safety warnings; the script exits early without a connected Astro device
and never references mustang partitions.

### Task 6 — Astro rootfs/boot build orchestration

Create `images/astro-slide/build.sh` (or `images/build.sh --device astro`) that
consumes `kernel/astro-slide/.build/out/` + `boot/astro-slide/pack-boot.sh` and
produces Astro `boot_b_<nuxel>.img` and `vendor_b.img` (with the clean-room/
vendor MTK modules installed). Reuse the **device-agnostic** `mkrootfs.sh`
userspace assembly, but do not require dm-verity/AVB for the first Astro boot.

**Acceptance:** build orchestration is fully separated from mustang and emits
artifacts under a clearly named `astro-slide` output dir, with a build manifest
recording the device key.

### Task 7 — Configs for Astro

Create `configs/astro-slide/` with:

- `display/` script applying 2340×1080 mode via `wlr-randr`.
- `libinput/` touch calibration (values marked `UNKNOWN` until real device).
- `alsa-ucm/` + `pipewire/` + `wireplumber/` stubs for the Astro audio codec.
- `modem/` stub documenting that the MT6873 modem is **not** ModemManager-ready.

**Acceptance:** configs exist, are device-keyed, and no mustang display/touch
values leak into Astro.

### Task 8 — Operator device-inventory template + gate

Add a template (e.g. `docs/astro-device-inventory.md` or a `getprop`/dmesg
collection script) that captures the **unknowns** (touch controller, audio
codec, panel LCM, camera sensors, NFC, sensors, modem interface) from the real
device. Wire the Astro build/flash scripts to **fail with a clear message** if
required inventory fields are still `UNKNOWN`, so nobody flashes a half-specified
image.

### Task 9 — Documentation

Update `README.md`, `QUICKSTART.md`, and add `docs/astro-slide-bringup.md`
explaining:

- The two-device model and `NUXEL_DEVICE` / `--device` selection.
- The Astro slot A/slot B safety model.
- Exact build + flash commands for Astro.
- The anti-cross-flash rules.

---

## Acceptance criteria (definition of done)

1. `make`/VM/PWA mustang paths still pass their existing (scaffold-level)
   checks with `NUXEL_DEVICE=mustang`.
2. `NUXEL_DEVICE=astro` selects only `astro-slide` directories everywhere.
3. Every device-specific file lives under a per-device dir; a grep for
   `mustang` inside `astro-slide/` and `astro` inside
   `google-pixel-10-pro-xl/` returns no device-coupling (except documented
   cross-references).
4. Astro flash script refuses on device mismatch and provides a one-command
   revert to slot A.
5. No fabricated checksums/IDs: all unknowns are `UNKNOWN`/`PLACEHOLDER` with a
   real-device collection step.
6. All new shell scripts pass `bash -n` and `shellcheck` (where available).
7. Build/flash scripts print the resolved device key and abort on missing
   per-device inputs.
8. New docs are present and consistent with `astro-requirements.md`.

---

## Deliverables to produce in the repo

- The per-device directory tree above, fully populated with code + stubs.
- `docs/astro-slide-bringup.md`.
- Updated `README.md` / `QUICKSTART.md`.
- `docs/astro-device-inventory.md` (operator template).
- No changes to the committed userspace services/PWA/sandbox unless needed to
  make them device-agnostic (and if changed, keep them working for mustang/VM).

## Explicit things you must NOT do

- Do not claim the Astro or mustang path is "flashable/verified" until the
  required device inventory + real firmware + real kernel build are complete.
- Do not fabricate a MT6873 mainline DTS or pretend mainline 6.12 supports the
  Astro.
- Do not reuse Pixel/Broadcom/PowerVR firmware for the Astro.
- Do not relock any bootloader.
- Do not delete or overwrite mustang files without preserving a working path.

<!-- PROMPT-END -->

---

## Operator quick reference (not part of the agent prompt)

This section is for you (the human), so you know the *immediate* next physical
step before handing work back to the agent.

### Reality check

Neither target is flashable today. The mustang path is an aspirational scaffold,
and the Astro path is a **new** downstream-MediaTek bring-up. The agent's job is
to build the correctly-separated scaffolding + real Astro tooling, **not** to
pretend a bootable image already exists.

### First physical action (Phase 0 — device inventory)

On the spare Astro Slide, before trusting any firmware/driver list:

```sh
# Unlock Developer Options, OEM unlock, USB debugging
adb reboot bootloader
fastboot getvar all          # capture product/serial/slot/partition info
fastboot getvar product
fastboot getvar current-slot

# After booting back into Android (stock, slot A):
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|mediatek'
adb shell dmesg > astro-dmesg.txt
adb shell getevent -pl        # identify touchscreen/input controllers
adb shell ls -R /vendor/firmware /vendor/lib/modules /vendor/etc/firmware
adb shell ls -R /sys/bus/i2c/devices /sys/bus/platform/devices | head
```

Feed the captured `astro-dmesg.txt`, `getevent`, and vendor listings back into
`docs/astro-device-inventory.md` and the Astro `firmware/astro-slide/manifest.yml`
before the first slot-B flash.

### Minimal flash + revert commands (Astro, once images exist)

```sh
# Flash Nuxel to slot B (stock Android+Magisk stays on slot A)
NUXEL_DEVICE=astro bash boot/astro-slide/flash.sh --device astro

# Revert to stock at any time
fastboot reboot-bootloader
fastboot set_active a
fastboot reboot
```

### How the two devices stay separated

- Firmware: `firmware/google-pixel-10-pro-xl/` vs `firmware/astro-slide/`
- Kernel: `kernel/google-pixel-10-pro-xl/` vs `kernel/astro-slide/`
- Device: `device/google-pixel-10-pro-xl/` vs `device/astro-slide/`
- Boot/flash: `boot/google-pixel-10-pro-xl/` vs `boot/astro-slide/`
- Configs: `configs/google-pixel-10-pro-xl/` vs `configs/astro-slide/`
- Images: `images/google-pixel-10-pro-xl/` vs `images/astro-slide/`
- Shared (device-agnostic): `services/`, `shell/`, `pwa/`, `tools/`, `vm/`
