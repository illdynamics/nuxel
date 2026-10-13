# Nuxel → Samsung Galaxy S10+ (Exynos) — Implementation Prompt for the Build Agent

> **How to use this file:** copy the entire block below the `PROMPT-START`
> marker and paste it into your agent. The rest of this file is the prompt
> itself plus acceptance criteria, so the agent has everything it needs without
> guessing.

<!-- PROMPT-START -->

## Role

You are a senior embedded-Linux / phone-OS bring-up engineer working on the
**Nuxel** repository at `/Users/wicked/x/nuxel` (the repo root). Your job is to
implement the **Samsung Galaxy S10+ (Exynos 9820, codename `beyond2lte`)** as a
second, fully-separated hardware target alongside the existing **Google Pixel
10 Pro XL (mustang)** target — without breaking the mustang scaffold and
without ever cross-flashing device-specific firmware, drivers, kernels, or
images.

## Non-negotiable safety rules

1. **Every device-specific artifact is stored under a per-device directory**
   (see layout below) and selected by an explicit device key:
   `google-pixel-10-pro-xl` (key `mustang`), `s10plus` (key `s10plus`,
   codename `beyond2lte`), and `g7power` (key `g7power`, codename `ocean`).
2. **No device file may contain multiple devices' data.** Shared code must be
   device-agnostic (userspace services, PWA, sandbox configs, generic tools).
3. **The S10+ is a Samsung Exynos device: there is NO `fastboot`.** All flash
   tooling must use **TWRP (ADB + `dd`)** and **Download Mode (Odin/`heimdall`)**
   only. Never emit `fastboot` commands for the S10+.
4. **Verify device identity before every flash.** Check `getprop ro.product.device`
   == `beyond2lte` and `ro.product.name` == `beyond2ltexx` (or the actual
   variant) from TWRP, and refuse on mismatch.
5. **Never touch** `efs`, `efsg`, `persist`, `param`, `up_param`, `steady`,
   `keystorage`, `carrier`, `cp_debug`, `misc` — these hold per-unit
   calibration (IMEI, MAC, DRK, Knox state, baseband calibration).
6. **Never relock the bootloader or attempt Knox restoration** — the fuse is
   already tripped and irreversible; leave it alone.
7. Do not invent or fabricate firmware blobs, checksums, device IDs, or driver
   status. Mark unknown values explicitly as `UNKNOWN` / `TBD` and require the
   operator to fill them from a real device (the unit is already in TWRP).

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
  S10+ requires **v1** (legacy header, kernel + ramdisk, page 2048).
- `boot/flash.sh` is mustang-only (Google ABL, `vendor_boot`, `init_boot`,
  `vbmeta`, A/B `fastbootd` super flashing).
- `firmware/manifest.yml`, `firmware/install-firmware.sh`,
  `firmware/verify-firmware.sh` are mustang-only.
- `device/deviceinfo` and `device/APKBUILD` are mustang-only.
- `configs/` holds mustang display/libinput/alsa-ucm/modem/pipewire/wireplumber.
- `images/mkrootfs.sh` is device-agnostic userspace (Phosh/Flatpak/PWA).
- `boot/initramfs/init.sh` parses `nuxel.device=`, `nuxel.slot=`, `root=`,
  `rootfstype=` and probes root via `/dev/disk/by-partlabel/system_${SLOT}`
  then generic devices; it must be extended for the S10+ UFS A-only layout.

### Samsung Galaxy S10+ (Exynos) verified facts

- Device: Samsung Galaxy S10+ (SM-G975F, Exynos), codename **`beyond2lte`**.
- SoC: **Exynos 9820** (2× Mongoose M4 + 2× Cortex-A75 + 4× Cortex-A55, 8 nm).
- GPU: Mali-G76 MP12 (Bifrost → mainline **Panfrost**).
- RAM 8 GB LPDDR4X; storage **UFS 2.1** at `/dev/block/platform/13d60000.ufs`.
- Display: 6.4" Dynamic AMOLED **3040×1440**, 19:9, HDR10+; DDIC **S6E3HA9** (`s6e3ha9_beyond2`).
- Touch: Samsung **S6SY761**-series (`sec_ts`), I2C hsi2c_10 @ 0x48, firmware `y771`/`y771_d`, FOD.
- WiFi/BT: Broadcom **BCM4375** (Wi-Fi 6, BT 5.0) — confirmed (`samsung,brcm-wlan` node + teardown).
- Modem: integrated Samsung Shannon LTE (Exynos 9820, no 5G).
- Audio: Cirrus Logic **CS47L93** codec + **2× CS35L40** amps (madera ASoC).
- NFC: Samsung `sec-nfc` (S3FWRN5-family) @ I2C 0x27, with embedded SE (P3).
- Battery 4100 mAh, 15 W wired.
- Shipped kernel: Samsung **4.14.x downstream**.
- Boot model: **A-only** (no A/B slots); `boot`/`recovery`/`system`/`vendor`/`product` separate.
- Boot image: **legacy header v1** (page 2048).
- **No `fastboot`** — flash via **TWRP (ADB sideload + `dd`)** and **Download Mode (Odin/`heimdall`)**.
- The device is **already in TWRP** → bootloader already unlocked, Knox already tripped.
- Community resources:
  - postmarketOS generic Exynos 9820 port: device `device-samsung-exynos9820`,
    kernel `linux-postmarketos-exynos9820` (close-to-mainline). Covers
    `beyond0lte`/`beyond1lte`/`beyond2lte`.
    Wiki: `https://wiki.postmarketos.org/wiki/Samsung_Exynos_9820_(samsung-exynos9820)`
  - Custom U-Boot fork (secondary bootloader, boots mainline via EFI):
    `https://github.com/chiffathefox/u-boot` branch `exynos9820`
    (`exynos9820_defconfig`).
  - TWRP beyond2lte: `https://twrp.me/samsung/samsunggalaxys10plus.html`
  - Samsung OSRC kernel: `https://opensource.samsung.com` (SM-G975F).

### S10+ boot chain (verified from postmarketOS)

Samsung **S-Boot** initializes CPU/DRAM/UFS/display but **ignores the kernel
cmdline and boot offset from `boot.img`** and **does not accept mainline DTBs**.
The proven path is: S-Boot → **custom U-Boot** (`chiffathefox/u-boot`,
`exynos9820`) → mainline Linux via EFI.

U-Boot build:
```sh
git clone https://github.com/chiffathefox/u-boot -b exynos9820
cd u-boot
make CC=aarch64-linux-gnu-gcc-10 CROSS_COMPILE=aarch64-linux-gnu- exynos9820_defconfig
mkbootimg --kernel u-boot.bin -o boot.img
```

pmOS-proven TWRP flash sequence (the Nuxel script must mirror this):
```sh
adb reboot recovery                 # or Vol Up + Bixby + Power
adb push u-boot-boot.img /tmp
adb shell dd if=/tmp/u-boot-boot.img of=/dev/block/platform/13d60000.ufs/by-name/boot
adb push <rootfs>.img /tmp
adb shell dd if=/tmp/<rootfs>.img of=/dev/block/platform/13d60000.ufs/by-name/userdata
adb shell twrp reboot
```
Alternative: `pmbootstrap install --android-recovery-zip --recovery-install-partition data`
+ TWRP **ADB Sideload**.

## Target directory layout to implement

Do **not** delete the current mustang files; move/copy them into per-device
directories while keeping symlinks or thin wrappers at the old paths for
backward compatibility, and clearly document the new canonical paths. Add the
`g7power/` slots as stubs too so the tree is uniformly three-device.

```
firmware/
  google-pixel-10-pro-xl/   manifest.yml install-firmware.sh verify-firmware.sh blobs/
  s10plus/                  manifest.yml install-firmware.sh verify-firmware.sh blobs/
  g7power/                  manifest.yml install-firmware.sh verify-firmware.sh blobs/
kernel/
  google-pixel-10-pro-xl/   defconfig patches/ README-toolchain.md
  s10plus/                  defconfig patches/ README-toolchain.md build-kernel.sh
  g7power/                  defconfig patches/ README-toolchain.md build-kernel.sh
device/
  google-pixel-10-pro-xl/   deviceinfo APKBUILD 90-nuxel-mustang.rules nuxel-mustang.conf
  s10plus/                  deviceinfo APKBUILD 90-nuxel-beyond2lte.rules nuxel-beyond2lte.conf
  g7power/                  deviceinfo APKBUILD 90-nuxel-ocean.rules nuxel-ocean.conf
boot/
  google-pixel-10-pro-xl/   flash.sh recovery.sh boot-config.txt
  s10plus/                  flash.sh recovery.sh boot-config.txt pack-boot-v1.sh uboot-chainload.sh
  g7power/                  flash.sh recovery.sh boot-config.txt pack-boot-v1.sh lk2nd/
configs/
  google-pixel-10-pro-xl/   display libinput alsa-ucm modem pipewire wireplumber
  s10plus/                  display libinput alsa-ucm modem pipewire wireplumber
  g7power/                  display libinput alsa-ucm modem pipewire wireplumber
images/
  google-pixel-10-pro-xl/   build.sh mkrootfs.sh avb rauc
  s10plus/                  build.sh (S10+ boot/vendor build)
  g7power/                  build.sh (G7 Power boot/rootfs build)
tools/                      # SHARED device-agnostic (sign-image, gen-keys, dedupe-assets, ...)
```

## Device selection mechanism (must be easy and explicit)

Implement a single shared selector used by every per-device script:

- Environment variable: `NUXEL_DEVICE` (values: `mustang`, `s10plus`, `g7power`).
- Equivalent CLI flag on build/flash scripts: `--device <mustang|s10plus|g7power>`.
- Resolution order: CLI flag > `NUXEL_DEVICE` > explicit error if unset.
- Map keys to dirs:
  - `mustang` → `google-pixel-10-pro-xl`
  - `s10plus` → `s10plus` (codename `beyond2lte`)
  - `g7power` → `g7power` (codename `ocean`)
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

### Task 2 — Scaffold the S10+ device package

Create `device/s10plus/deviceinfo` and `device/s10plus/APKBUILD` using the
verified Exynos 9820 facts above. Touch, audio, and NFC are already identified
(S6SY761 touch, CS47L93 + 2× CS35L40 audio, Samsung sec-nfc) — set those
explicitly. Mark only `deviceinfo_camera_*` and sensor component names as
`UNKNOWN — collect from real device`. Set:

- `deviceinfo_arch=aarch64`
- `deviceinfo_name="Samsung Galaxy S10+"`, `deviceinfo_codename=beyond2lte`
- `deviceinfo_soc="Samsung Exynos 9820"`, `deviceinfo_soc_family=exynos9820`
- `deviceinfo_gpu="Mali-G76 MP12"`
- `deviceinfo_display="6.4\" Dynamic AMOLED 3040x1440"`
- `deviceinfo_boot_header_version=1` (legacy, page 2048)
- `deviceinfo_boot_slots="none"` (A-only) + note S-Boot→U-Boot chainload
- `deviceinfo_flash_method="twrp-adb"` (NOT fastboot) with heimdall/Odin recovery note
- `deviceinfo_kernel="linux-postmarketos-exynos9820"`
- `deviceinfo_kernel_cmdline` with `nuxel.device=s10plus`, console, and
  root placeholders appropriate to the A-only UFS `userdata`/`system` layout.

Also create `device/s10plus/90-nuxel-beyond2lte.rules` and
`device/s10plus/nuxel-beyond2lte.conf` as **stubs** the operator fills from
real-device inventory (Task 8).

**Acceptance:** files exist, parse cleanly, and no mustang value is copied into
the S10+ device package.

### Task 3 — S10+ firmware manifest + extractor

Create `firmware/s10plus/manifest.yml` with categories for the Exynos stack and
mark every source path/checksum as `UNKNOWN`/`PLACEHOLDER` until a device dump
is available:

- `gpu` (Mali-G76): `libmali`/`mali_kbase` userspace + firmware.
- `display` (S6E3HA9), `touch` (S6SY761), `audio` (CS47L93 + 2× CS35L40), `wifi_bt` (BCM4375 `.bin`/`.hcd`/`.clm_blob`), `nfc` (sec-nfc), `sensors`, `camera`, `modem` (Shannon CP, protect EFS).

Implement `firmware/s10plus/install-firmware.sh` and
`firmware/s10plus/verify-firmware.sh` modeled on the mustang versions but
**completely independent** (different manifest, different `--device`, different
blob paths). Include `--list-files`, `--verify-only`, `--checksums`, and the
same consistency gate. For the S10+, add a **TWRP-pull mode** that uses `adb`
to extract `/vendor/firmware`, `/vendor/lib/modules`, `/vendor/etc/firmware`,
and `/system/lib64` GPU blobs from the already-TWRP'd unit.

**Acceptance:** `NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --list-files`
runs without touching mustang files and reports the S10+ manifest; the script
refuses to install anything until real blob hashes are filled (or runs in
"pending" mode).

### Task 4 — S10+ kernel build wrapper + defconfig

Create:

- `kernel/s10plus/defconfig` — an Exynos 9820 fragment. It must **not** copy
  mustang's `gs501`/BCM4390/PowerVR assumptions. Instead enable/keep:
  `CONFIG_DRM`, Exynos DRM/DSI, Panfrost (`CONFIG_DRM_PANFROST`), brcmfmac/cywd
  for BCM4375, madera ASoC (CS47L93 + CS35L40), `CONFIG_EXT4_FS`/`CONFIG_F2FS_FS`,
  `CONFIG_DEVTMPFS`, namespaces/seccomp/AppArmor where the exynos9820 tree
  supports them, and the Nuxel `drivers/nuxel/` features **only if the patch
  applies**. Annotate any 6.12-only symbol that cannot exist in the exynos9820 tree.
- `kernel/s10plus/build-kernel.sh` — a wrapper that clones/builds
  `linux-postmarketos-exynos9820`, applies `kernel/s10plus/patches/`, builds
  `Image.gz` + DTB with `aarch64-linux-gnu-` (or clang), and writes artifacts
  under `kernel/s10plus/.build/out/`.
- `kernel/s10plus/patches/` — port the Nuxel boot-param/phone feature patch to
  the exynos9820 tree, or a stub patch with a documented TODO if it does not
  apply cleanly.

**Acceptance:** `NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --help`
prints Exynos 9820 context; running it (when network + toolchain are available)
produces `kernel/s10plus/.build/out/Image.gz` and an exynos9820 DTB, and never
touches `kernel/google-pixel-10-pro-xl/`.

### Task 5 — S10+ boot image packer + U-Boot chainload + flash/recovery scripts

Create `boot/s10plus/pack-boot-v1.sh` that builds a **legacy Android boot image
header v1 (page 2048)** (kernel + ramdisk, no vendor_boot). Do **not** reuse the
mustang v4 `vendor_boot`/`init_boot`/`vbmeta` flow.

Create `boot/s10plus/uboot-chainload.sh` that:
- clones/builds `chiffathefox/u-boot` (`exynos9820_defconfig`),
- wraps `u-boot.bin` with `mkbootimg --kernel u-boot.bin` into `u-boot-boot.img`,
- pushes it to TWRP and `dd`s it to `/dev/block/platform/13d60000.ufs/by-name/boot`.

Create `boot/s10plus/flash.sh` implementing the pmOS-proven TWRP sequence, with:

- `--device s10plus` required/verified (checks `getprop ro.product.device` == `beyond2lte`).
- `adb push` + `adb shell dd` of the U-Boot boot.img and the Nuxel rootfs to
  `userdata` (or `system`), with a `--rootfs-partition` override.
- `--sideload` mode (TWRP ADB Sideload) as an alternative.
- `--revert` mode that re-flashes the stock `boot` partition from a backed-up
  image via TWRP/`heimdall`.
- Explicit warnings that there is **no fastboot** on this device and that
  Download Mode (Odin/`heimdall`) is the fallback.

Create `boot/s10plus/recovery.sh` adapted for TWRP/`adb`/`heimdall` recovery and
`boot/s10plus/boot-config.txt`.

**Acceptance:** `bash boot/s10plus/flash.sh --help` prints the TWRP sequence and
safety warnings; the script exits early without a connected S10+ and never
references mustang partitions or `fastboot`.

### Task 6 — S10+ rootfs/boot build orchestration

Create `images/s10plus/build.sh` (or `images/build.sh --device s10plus`) that
consumes `kernel/s10plus/.build/out/` + `boot/s10plus/pack-boot-v1.sh` and
produces the S10+ U-Boot `boot.img` and a `userdata`-targeted Nuxel rootfs
(with the Exynos/vendor modules installed). Reuse the **device-agnostic**
`mkrootfs.sh` userspace assembly, but do not require dm-verity/AVB for the first
S10+ boot.

**Acceptance:** build orchestration is fully separated from mustang and emits
artifacts under a clearly named `s10plus` output dir, with a build manifest
recording the device key.

### Task 7 — Configs for S10+

Create `configs/s10plus/` with:

- `display/` script applying 3040×1440 mode via `wlr-randr`.
- `libinput/` touch calibration for the S6SY761 (`sec_ts`) controller.
- `alsa-ucm/` + `pipewire/` + `wireplumber/` stubs for the CS47L93 + CS35L40 codec.
- `modem/` stub documenting that the Shannon LTE modem is **not** ModemManager-ready.

**Acceptance:** configs exist, are device-keyed, and no mustang display/touch
values leak into S10+.

### Task 8 — Operator device-inventory template + gate

Add a template (e.g. `docs/s10plus-device-inventory.md` or a TWRP `getprop`/`dmesg`
collection script) that captures the **remaining unknowns** (camera sensors,
sensor hub, exact WiFi/BT firmware filenames, modem interface). Touch/audio/
panel/NFC/WiFi are already known (S6SY761, CS47L93 + 2× CS35L40, S6E3HA9,
Samsung sec-nfc, BCM4375). Wire the S10+ build/flash scripts to **fail with a
clear message** if required inventory fields are still `UNKNOWN`, so nobody
flashes a half-specified image.

### Task 9 — Documentation

Update `README.md`, `QUICKSTART.md`, and add `docs/s10plus-bringup.md`
explaining:

- The multi-device model and `NUXEL_DEVICE` / `--device` selection
  (`mustang` / `s10plus` / `g7power`).
- The S10+ boot chain (S-Boot → U-Boot → Linux) and TWRP/`heimdall` flash model.
- Exact build + flash commands for the S10+.
- The anti-cross-flash rules and the already-tripped-Knox reality.

---

## Acceptance criteria (definition of done)

1. `make`/VM/PWA mustang paths still pass their existing (scaffold-level)
   checks with `NUXEL_DEVICE=mustang`.
2. `NUXEL_DEVICE=s10plus` selects only `s10plus` directories everywhere.
3. Every device-specific file lives under a per-device dir; a grep for
   `mustang` inside `s10plus/` and `s10plus`/`beyond2lte` inside
   `google-pixel-10-pro-xl/` returns no device-coupling (except documented
   cross-references).
4. S10+ flash script refuses on device mismatch, uses **no `fastboot`**, and
   provides a one-command revert (re-flash stock `boot` via TWRP/`heimdall`).
5. No fabricated checksums/IDs: all unknowns are `UNKNOWN`/`PLACEHOLDER` with a
   real-device collection step.
6. All new shell scripts pass `bash -n` and `shellcheck` (where available).
7. Build/flash scripts print the resolved device key and abort on missing
   per-device inputs.
8. New docs are present and consistent with `s10plus-requirements.md`.

---

## Deliverables to produce in the repo

- The per-device directory tree above, fully populated with code + stubs
  (including the `g7power/` stub slots for consistency).
- `docs/s10plus-bringup.md`.
- Updated `README.md` / `QUICKSTART.md`.
- `docs/s10plus-device-inventory.md` (operator template).
- No changes to the committed userspace services/PWA/sandbox unless needed to
  make them device-agnostic (and if changed, keep them working for mustang/VM).

## Explicit things you must NOT do

- Do not claim the S10+ or mustang path is "flashable/verified" until the
  required device inventory + real firmware + real kernel build are complete.
- Do not emit `fastboot` commands for the S10+ (Samsung Exynos has no fastboot).
- Do not reuse Pixel/Broadcom/PowerVR firmware for the S10+.
- Do not relock the bootloader or attempt to restore Knox.
- Do not touch `efs`/`efsg`/`persist`/`param`/`up_param`/`steady`/`keystorage`.
- Do not delete or overwrite mustang files without preserving a working path.

<!-- PROMPT-END -->

---

## Operator quick reference (not part of the agent prompt)

This section is for you (the human), so you know the *immediate* next physical
step before handing work back to the agent.

### Reality check

Neither target is flashable today. The mustang path is an aspirational scaffold,
and the S10+ path is a **new** Exynos 9820 bring-up (built on the postmarketOS
exynos9820 port). The agent's job is to build the correctly-separated scaffolding
+ real S10+ tooling, **not** to pretend a bootable image already exists.

### First physical action (Phase 0 — device inventory via TWRP)

The S10+ is already in TWRP. Before trusting any firmware/driver list:

```sh
adb reboot recovery        # or Vol Up + Bixby + Power
adb devices

# Capture identity + inventory
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|exynos'
adb shell cat /proc/cmdline
adb shell dmesg > s10plus-dmesg.txt
adb shell getevent -pl                       # identify touchscreen/input controllers
adb shell ls -R /vendor/firmware /vendor/lib/modules /vendor/etc/firmware
adb shell ls -R /dev/block/platform/13d60000.ufs/by-name
adb shell cat /proc/partitions
```

Feed the captured `s10plus-dmesg.txt`, `getevent`, and vendor listings back into
`docs/s10plus-device-inventory.md` and `firmware/s10plus/manifest.yml` before
the first U-Boot/flash.

### Back up EFS + full stock before any modification (critical)

```sh
adb shell "mkdir -p /sdcard/backup && for p in efs efsg persist param up_param steady; do dd if=/dev/block/platform/13d60000.ufs/by-name/$p of=/sdcard/backup/$p.img; done"
adb pull /sdcard/backup
```

### Minimal flash + revert commands (S10+, once images exist)

```sh
# Chainload U-Boot + flash Nuxel rootfs (stock Android stays recoverable via Download Mode)
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh --device s10plus

# Revert to stock at any time (Download Mode + Odin/heimdall):
#   Hold Vol Down + Bixby + Power -> Download Mode
#   heimdall flash --BL BL_*.tar.md5 --AP AP_*.tar.md5 --CP CP_*.tar.md5 --CSC CSC_*.tar.md5
```

### How the devices stay separated

- Firmware: `firmware/google-pixel-10-pro-xl/` vs `firmware/s10plus/` vs `firmware/g7power/`
- Kernel: `kernel/google-pixel-10-pro-xl/` vs `kernel/s10plus/` vs `kernel/g7power/`
- Device: `device/google-pixel-10-pro-xl/` vs `device/s10plus/` vs `device/g7power/`
- Boot/flash: `boot/google-pixel-10-pro-xl/` vs `boot/s10plus/` vs `boot/g7power/`
- Configs: `configs/google-pixel-10-pro-xl/` vs `configs/s10plus/` vs `configs/g7power/`
- Images: `images/google-pixel-10-pro-xl/` vs `images/s10plus/` vs `images/g7power/`
- Shared (device-agnostic): `services/`, `shell/`, `pwa/`, `tools/`, `vm/`
