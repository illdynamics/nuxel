# Nuxel → Google Pixel 10 Pro XL — Implementation Prompt for the Build Agent

> **How to use this file:** copy the entire block below the `PROMPT-START`
> marker and paste it into your agent. The rest of this file is the prompt
> itself plus acceptance criteria, so the agent has everything it needs without
> guessing.

<!-- PROMPT-START -->

## Role

You are a senior embedded-Linux / phone-OS bring-up engineer working on the
**Nuxel** repository at `/Users/wicked/x/nuxel` (the repo root). Your job is to
**complete and harden the Google Pixel 10 Pro XL (`mustang`) target** — the
primary, default hardware target that the UTM VM, the build dispatcher,
`boot/flash.sh`, `firmware/manifest.yml` and `device/deviceinfo` all already
default to — to the same quality bar as the `s10plus/` and `g7power/` target
passes, **without breaking either sibling target** and **without ever
cross-flashing device-specific firmware, drivers, kernels, or images.**

Unlike the sibling prompts, you are **not** adding a new device. The mustang
directory layout already exists. Your job is to close the real gates:
(1) the private vendor kernel tree, (2) the 30 firmware blobs, (3) a real boot
image set, and (4) a hardware-unlock/flash/recovery path that is correct and
refuses to run on the wrong device.

## Non-negotiable safety rules

1. **Every device-specific artifact is stored under a per-device directory**
   and selected by an explicit device key: `google-pixel-10-pro-xl` (key
   `mustang`), `s10plus` (key `s10plus`, codename `beyond2lte`), and `g7power`
   (key `g7power`, codename `ocean`). The mustang directory is the primary.
2. **No device file may contain multiple devices' data.** Shared code must be
   device-agnostic (userspace services, PWA, sandbox configs, generic tools).
3. **The Pixel 10 Pro XL uses the Google ABL + `fastboot`/`fastbootd` flow**
   with AVB 2.0 + Titan M3, **header v4** boot images, `vendor_boot` +
   `init_boot` + `dtbo` + `vbmeta`, and A/B slots on a `super` dynamic
   partition. Do **not** import `lk2nd`/U-Boot/EDL logic from the siblings.
4. **Verify device identity before every flash.** `fastboot getvar product`
   must be `mustang` (and, if `NUXEL_EXPECTED_SERIAL` is set,
   `fastboot getvar serial` must match); refuse on mismatch.
5. **Never flash the wrong device's artifacts, and never reuse `panther`
   (Pixel 7) or sibling-target blobs.** The manifest for mustang is
   `firmware/google-pixel-10-pro-xl/manifest.yml` only.
6. **`fastboot flashing unlock` and `fastboot flashing unlock_critical` WIPE the
   device.** Never run them without an explicit `--unlock`/`--wipe` and a
   triple confirmation. **Never relock** (`fastboot flashing lock` /
   `--relock-custom-key`) until Nuxel is verified booting in development mode.
7. **Do not fabricate firmware blobs, checksums, device IDs, or driver
   status.** Every unknown is `UNKNOWN`/`TBD`/`PLACEHOLDER` and must be filled
   from the real factory image / device before any flash.
8. **Do not delete or overwrite the `s10plus/` or `g7power/` files.** The
   three-device tree must remain consistent, and every legacy top-level path
   (`boot/flash.sh`, `firmware/manifest.yml`, `device/deviceinfo`,
   `configs/display`, …) must keep working as a symlink into
   `google-pixel-10-pro-xl/`.
9. **Pass `bash -n` and `shellcheck`** on every shell script you touch, and keep
   `NUXEL_DEVICE=mustang make ci` / the UTM verify suites green.

## Verified context you must rely on (do not hallucinate)

### Current repo state (deep-analyzed)

- Nuxel v0.2.0 is a **mustang-only scaffold**, not a flashable OS. `README.md`
  and `QUICKSTART.md` say so explicitly. `README.md`'s honest matrix scores the
  Pixel 10 Pro XL at **5%** and "Flashable images" at **0%**.
- `Makefile` sets `NUXEL_DEVICE ?= mustang`; `tools/nuxel-device-select.sh`
  maps `mustang → google-pixel-10-pro-xl` (aliases `s10plus|beyond2lte`,
  `g7power|ocean`); the selector never guesses a default.
- `kernel/build-kernel.sh` builds public GKI `android16-6.12` and merges
  `kernel/google-pixel-10-pro-xl/defconfig`. The authoritative
  `gs501_defconfig` lives in the **private** `android-gs-mustang-6.12` tree.
- `firmware/google-pixel-10-pro-xl/manifest.yml` lists **30 required + 2
  optional** blobs across 12 categories; all `source_path`/`checksum` are
  placeholders → **0 verified**.
- `firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict` reports the
  missing/placeholder state and refuses a non-mustang device key.
- `boot/google-pixel-10-pro-xl/flash.sh` is mustang-only (Google ABL,
  `boot`/`vendor_boot`/`init_boot`/`dtbo`/`vbmeta`, A/B, `fastbootd` super,
  dev = AVB-disabled, prod = custom-key relock). `boot/recovery.sh` is the
  failsafe shell.
- `images/google-pixel-10-pro-xl/build.sh` is a thin wrapper pinning
  `--device mustang` and forwarding to `images/build.sh`;
  `images/google-pixel-10-pro-xl/{avb,ostree,rauc}` hold AVB/OSTree/RAUC
  scaffolding. `images/mkrootfs.sh` is device-agnostic userspace
  (Phosh/Flatpak/PWA).
- `images/bootpack/mkbootimg.py` implements **boot header v3/v4 only** (correct
  for mustang; a v1 packer exists only in the sibling dirs).
- `device/google-pixel-10-pro-xl/deviceinfo` + `APKBUILD`
  (`pkgname="device-google-mustang"`) are complete mustang device packages.
- `configs/google-pixel-10-pro-xl/{display,libinput,alsa-ucm,modem,pipewire,wireplumber}`
  are prepared (mustang-suffixed files).
- `boot/initramfs/init.sh` parses `nuxel.device=`, `nuxel.slot=`, `root=`,
  `rootfstype=` and probes root via `/dev/disk/by-partlabel/system_${SLOT}`.
- The UTM ARM64 `Nuxel-verify` VM (UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`,
  Fedora 43, **Phosh 0.54.0 / phoc 0.54.0**, 720×1440) boots and passes
  **PASS=22/17, HARD PASS**.

### Google Pixel 10 Pro XL (mustang) verified facts

- Device: Google Pixel 10 Pro XL, codename **`mustang`**; reviewed serial
  `58211FDCQ001LA`, HW `MP1.0`, SKU `G45RY`.
- SoC: **Google Tensor G5 (`gs501`)**, Armv9.2 (Cortex-X5 + Cortex-A730 +
  Cortex-A530).
- GPU: **Imagination PowerVR DXT-72-2304** — vendor-only, no mainline DRM.
- Security: **Google Titan M3** (AVB 2.0 root of trust).
- RAM 16 GB LPDDR5X; storage 256 GB **UFS 4.0** (f2fs).
- Display: Samsung **AMB655X** LTPO OLED **3120×1440 @ 120 Hz** (downstream).
- Touch: Samsung **S6SY791** (downstream).
- WiFi/BT: Broadcom **BCM4390** — Wi-Fi 7 / BT 5.4 (`brcmfmac` + `BCM4390.hcd`).
- Modem: Samsung **Exynos 5500** (PCIe/MHI, 5G NR) — no upstream MM plugin.
- Audio: Cirrus Logic **CS35L45** (amp) + **CS42L43** (codec) — downstream.
- NFC: NXP **SN220**; fingerprint: Goodix **GF3636** (optical under-display).
- Sensors: Bosch BMI270, ST LSM6DSV, AMS TCS3710, Bosch BMP280.
- Battery 5300 mAh Li-Po; PMIC Maxim MAX77729 + MAX77826; charger TI BQ2597x +
  Maxim MAX1720x fuel gauge.
- Shipped kernel base: Linux **6.12 LTS** (`android-gs-mustang-6.12`,
  `gs501_defconfig`, **private**).
- Boot: **A/B**, header **v4** + `vendor_boot` + `init_boot` + `dtbo` +
  `vbmeta`, `super` dynamic partition, **`fastboot` + `fastbootd`**.
- Factory image: `mustang-bp1a.250405.001-factory-*.zip`
  (`https://developers.google.com/android/images#mustang`).
- Community resources: **none meaningful** — there is no postmarketOS port for
  gs501; the vendor tree is the only real source. Public GKI
  (`android16-6.12`) is scaffolding-only and **not bootable on mustang hardware**.

### mustang boot chain (verified from the repo)

```
Boot ROM (Tensor G5) → Titan M3 → Google ABL →
Linux 6.12 (android-gs-mustang-6.12, gs501_defconfig) →
Nuxel initramfs (init_boot.img; probes /dev/disk/by-partlabel/system_${SLOT}) →
Nuxel system (dm-verity, ro) → Phosh + GTK4 + PWA
```

`init_boot.img` is **mandatory** on Android 13+; `vendor_boot.img` carries the
mustang DTBO; `vbmeta.img` (signed with a custom key for production) is what
enables re-locking with a Nuxel root of trust.

## Target directory layout (already present — complete it, don't re-invent it)

```
firmware/google-pixel-10-pro-xl/   manifest.yml install-firmware.sh verify-firmware.sh blobs/
kernel/google-pixel-10-pro-xl/     defconfig patches/ README-toolchain.md  (+ build wrapper)
device/google-pixel-10-pro-xl/     deviceinfo APKBUILD 90-nuxel-mustang.rules nuxel-mustang.conf
boot/google-pixel-10-pro-xl/       flash.sh recovery.sh boot-config.txt
configs/google-pixel-10-pro-xl/    display libinput alsa-ucm modem pipewire wireplumber
images/google-pixel-10-pro-xl/     build.sh avb/ ostree/ rauc/
tools/                             # SHARED device-agnostic (nuxel-device-select.sh, sign-image, gen-keys, …)
```

Keep the legacy top-level symlinks (`boot/flash.sh`, `boot/recovery.sh`,
`firmware/*.sh`, `firmware/manifest.yml`, `device/deviceinfo`, `device/APKBUILD`,
`configs/{display,libinput,alsa-ucm,modem,pipewire,wireplumber}`,
`images/{avb,ostree,rauc}`, `kernel/{defconfig,patches,README-toolchain.md}`)
pointing into `google-pixel-10-pro-xl/`.

## Device selection mechanism (must be explicit)

- Environment variable: `NUXEL_DEVICE` (values: `mustang`, `g7power`, `s10plus`).
- Equivalent CLI flag: `--device <mustang|g7power|s10plus>`.
- Resolution order: CLI flag > `NUXEL_DEVICE` > explicit error if unset.
- Map: `mustang` → `google-pixel-10-pro-xl`; `s10plus` → `s10plus` (codename
  `beyond2lte`); `g7power` → `g7power` (codename `ocean`).
- Every script must print the resolved device key + directory at startup and
  abort (non-zero) if required per-device files are missing.

---

## Tasks (implement in this order)

### Task 1 — Validate & harden the mustang device package

Re-verify `device/google-pixel-10-pro-xl/deviceinfo` and `APKBUILD` against the
verified facts above. Ensure `deviceinfo` carries the full mustang identity
(codename `mustang`, serial `58211FDCQ001LA`, HW `MP1.0`, SKU `G45RY`, `gs501`,
header `4`, A/B slots, `fastboot`/`fastbootd`), and that `APKBUILD`
(`pkgname="device-google-mustang"`) declares the correct dependencies. Add the
missing mustang udev/modprobe snippets (`90-nuxel-mustang.rules`,
`nuxel-mustang.conf`) if absent, or document precisely why they are deferred.

**Acceptance:** files exist, parse cleanly, contain no sibling-target values
(`ocean`, `beyond2lte`, `wcd9335`, `ili210x`, …).

### Task 2 — Firmware manifest + extraction gate

Confirm `firmware/google-pixel-10-pro-xl/manifest.yml` enumerates all **30
required + 2 optional** blobs (categories: modem, wifi, bluetooth, gpu, display,
audio, sensors, nfc, fingerprint, pmic, charger). Keep every unknown
`checksum`/`source_path` as `PLACEHOLDER`/`UNKNOWN`. Ensure
`install-firmware.sh` supports `--list-files`, `--verify-only`, `--checksums`,
an `--output-dir`, and a factory-image (`vendor.img`/`modem_*.img`) extraction
path, and that `verify-firmware.sh --strict` **fails loudly** while hashes are
placeholders and **refuses a non-mustang key**.

**Acceptance:** `NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/install-firmware.sh --list-files`
runs without touching sibling files and reports the mustang manifest;
`--verify-only` reports the real missing/placeholder state.

### Task 3 — Kernel build wrapper + gs501 defconfig handling

Provide a `kernel/google-pixel-10-pro-xl/build-kernel.sh` wrapper that:
- resolves `--device mustang` / `NUXEL_DEVICE=mustang` and aborts otherwise;
- documents and detects the **private** `android-gs-mustang-6.12` vendor tree
  (and fails with a clear, actionable message when it is unavailable);
- builds the public-GKI **scaffold** path (`gki_defconfig` +
  `kernel/google-pixel-10-pro-xl/defconfig`) when the vendor tree is absent,
  clearly labelling the output **NOT hardware-bootable**;
- emits `kernel/google-pixel-10-pro-xl/.build/out/Image.gz` + `dtbs/mustang.dtb`
  only when a real build succeeds.

Annotate the `defconfig` so that non-upstream mustang symbols
(`CONFIG_DRM_POWERVR`, `CONFIG_DRM_PANEL_SAMSUNG_AMB655X`,
`CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791`, `CONFIG_MHI_SAMSUNG_EXYNOS5500`,
`CONFIG_BRCMFMAC_BCM4390`, `CONFIG_SND_SOC_CS35L45`/`CS42L43`,
`CONFIG_NFC_NXP_SN220`, `CONFIG_INPUT_GOODIX_GF3636`) are explicitly marked as
vendor-tree-only so the scaffold build never silently claims them.

**Acceptance:** `NUXEL_DEVICE=mustang bash kernel/google-pixel-10-pro-xl/build-kernel.sh --help`
prints gs501/Tensor G5 context and the vendor-tree caveat; running it never
touches `kernel/s10plus/` or `kernel/g7power/`.

### Task 4 — Boot image packing (header v4 + vendor_boot/init_boot)

Ensure `images/bootpack/mkbootimg.py` (and/or a wrapper under
`boot/google-pixel-10-pro-xl/`) packs a **v4** `boot.img` and the
`vendor_boot.img` (vendor ramdisk + DTBO), `init_boot.img` (generic ramdisk),
`dtbo.img`, and `vbmeta.img`. `init_boot.img` must be treated as **mandatory**.
Do **not** reuse the sibling v1 packers for mustang.

**Acceptance:** the packer produces a well-formed v4 `ANDROID!` image plus the
`vendor_boot`/`init_boot` set when given `Image.gz` + DTB + ramdisk, and labels a
kernel-less invocation as a **dev stub**.

### Task 5 — flash.sh / recovery.sh hardening + device identity gate

Harden `boot/google-pixel-10-pro-xl/flash.sh`:
- require `--device mustang` / `NUXEL_DEVICE=mustang`;
- gate on `fastboot getvar product == mustang` (and optional expected serial);
- keep the two paths — **development** (`--skip-avb --allow-unverity-dev`,
  A/B slot aware, `fastbootd` super flash) and **production**
  (`--relock-custom-key`, wipes device, triple confirmation);
- keep `--revert` (restore stock `boot`/`vendor_boot`/`init_boot`/`dtbo`/
  `vbmeta`) and `--wipe`;
- never reference sibling partitions or the sibling toolchains.
Ensure `boot/google-pixel-10-pro-xl/recovery.sh` documents the Pixel recovery
key combo, `fastboot reboot recovery`, and the factory `flash-all.sh` restore.

**Acceptance:** `bash boot/google-pixel-10-pro-xl/flash.sh --help` prints the ABL
flash sequence and safety warnings; the script exits early without a connected
mustang and never references `lk2nd`, `Odin`, or TWRP.

### Task 6 — Image build orchestration + VM/flash pipeline

Confirm `images/google-pixel-10-pro-xl/build.sh` (thin `--device mustang`
wrapper) and the shared `images/build.sh` emit
`build/out/mustang/flashable/{boot.img,vendor_boot.img,init_boot.img,dtbo.img,vbmeta.img,system.img}`
only from a real kernel + firmware set, and emit clearly-labelled **dev stubs**
otherwise. Keep the device-agnostic `images/mkrootfs.sh` userspace assembly
integrable. Record the device key in the build manifest.

**Acceptance:** `NUXEL_DEVICE=mustang bash images/google-pixel-10-pro-xl/build.sh --quick`
runs, prints the resolved `mustang` key/dir, and produces only labelled stubs;
`make ci` stays green.

### Task 7 — Configs (display / touch / audio / modem / pipewire / wireplumber)

Confirm `configs/google-pixel-10-pro-xl/`:
- `display/` applies **3120×1440 @ 120 Hz**;
- `libinput/` carries the **S6SY791** touch calibration (mark unknowns);
- `alsa-ucm/` + `pipewire/` + `wireplumber/` are stubs/UCM for **CS42L43 +
  CS35L45**;
- `modem/` documents that the **Exynos 5500** is **not** ModemManager-ready.
No sibling display/touch/audio values may leak in.

**Acceptance:** configs exist, are mustang-keyed, and contain no `ocean`/
`beyond2lte` values.

### Task 8 — Operator device-inventory template + gate

Add `phones/pixel10proxl/pixel10proxl-device-inventory.md` (or an equivalent under
`docs/`) that captures the remaining unknowns (current build string / bootloader
revision, exact vendor blob filenames in `vendor.img`/`modem_*.img`, carrier-lock
state, slot state, whether the private vendor tree is obtainable). Wire the
build/flash scripts to **fail with a clear message** while required inventory
fields are `UNKNOWN`, so nobody flashes a half-specified image.

### Task 9 — Documentation

Update `README.md` / `QUICKSTART.md` if needed and keep
`phones/pixel10proxl/pixel10proxl-requirements.md`,
`phones/pixel10proxl/nuxel-pixel10proxl.md`, `phones/pixel10proxl/pixel10proxl-prompt.md`,
`phones/pixel10proxl/google-pixel-10-pro-xl-quickstart.md`, `docs/driver-status.md`,
`docs/hardware-ids.md`, `docs/mustang-recovery-bringup.md` and
`docs/hardware-bringup-prep.md` mutually consistent. Explain the multi-device
model, the mustang boot chain (ABL → Linux + AVB), the exact build + flash
commands, and the private-vendor-kernel blocker.

---

## Acceptance criteria (definition of done)

1. `NUXEL_DEVICE=mustang make ci` and the UTM verify suites still pass.
2. `NUXEL_DEVICE=mustang` selects only `google-pixel-10-pro-xl` directories; a
   grep for `ocean`/`beyond2lte`/`lk2nd`/`Odin`/`TWRP` inside
   `google-pixel-10-pro-xl/` returns no device coupling (except documented
   cross-references).
3. `firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict` accurately
   reports 30 required blobs, and fails while hashes are placeholders.
4. `boot/google-pixel-10-pro-xl/flash.sh` refuses on device mismatch and offers
   a one-command `--revert` to stock.
5. No fabricated checksums/IDs: all unknowns are `UNKNOWN`/`PLACEHOLDER` with a
   real factory-image/device collection step.
6. All touched shell scripts pass `bash -n` and `shellcheck` (where available).
7. Build/flash scripts print the resolved device key and abort on missing
   per-device inputs.
8. The four `pixel10proxl/` documents are present and consistent with
   `phones/pixel10proxl/pixel10proxl-requirements.md`.

---

## Deliverables to produce in the repo

- Completed mustang-specific code + stubs under the existing
  `google-pixel-10-pro-xl/` slots (device, kernel, firmware, boot, configs,
  images).
- `phones/pixel10proxl/pixel10proxl-requirements.md`,
  `phones/pixel10proxl/nuxel-pixel10proxl.md`,
  `phones/pixel10proxl/pixel10proxl-prompt.md`,
  `phones/pixel10proxl/google-pixel-10-pro-xl-quickstart.md`.
- `phones/pixel10proxl/pixel10proxl-device-inventory.md` (operator template + gate).
- No changes to the committed userspace services/PWA/sandbox unless needed to
  keep them device-agnostic (and if changed, keep mustang/VM working).

## Explicit things you must NOT do

- Do not claim the mustang path is "flashable/verified" until the vendor kernel
  tree, real firmware blobs, and a real boot image set exist and a physical flash
  has succeeded.
- Do not reuse Pixel-7 (`panther`) or sibling-target firmware/drivers/DTBs.
- Do not relock the bootloader before a verified dev-mode boot.
- Do not wipe `persist`/`metadata` outside an explicit clean-install step.
- Do not skip `init_boot.img` (mustang boots fail without it).
- Do not delete or overwrite the `s10plus/`/`g7power/` files, and do not break
  the legacy top-level symlinks.

<!-- PROMPT-END -->

---

## Operator quick reference (not part of the agent prompt)

### Reality check

The Pixel 10 Pro XL is the **primary target** but also the **hardest**: its
silicon is downstream-only and its vendor kernel tree is private. Nothing here is
flashable today. The agent's job is to finish the correctly-separated mustang
tooling and make every gate honest.

### First physical action (Phase 0 — unlock + factory image)

```sh
# Device: Developer options → enable "OEM unlocking" + "USB debugging"
adb devices                       # expect the unit's serial
adb shell getprop ro.product.name # => mustang
adb shell getprop ro.build.id     # save the exact build string
adb shell settings get global oem_unlock_allowed   # 1 = can unlock
adb reboot bootloader
fastboot getvar all               # capture product/serial/slot/current-slot
fastboot flashing unlock          # WIPES the device; confirm on-device

# Download + verify the factory image (browser consent flow, then):
shasum -a 256 mustang-bp1a.250405.001-factory-<xxxxx>.zip   # compare to published
```

### Extract firmware + verify before any flash

```sh
NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/install-firmware.sh \
    /tmp/mustang-bp1a.250405.001-factory-<xxxxx>.zip --output-dir ./firmware-out --install
NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict
# Target: 30/30 verified
```

### Minimal flash + revert (mustang, once images exist)

```sh
# Development flash (AVB disabled):
NUXEL_DEVICE=mustang bash boot/google-pixel-10-pro-xl/flash.sh --device mustang \
    --skip-avb --allow-unverity-dev --slot a

# Revert to stock (from the saved factory backup):
NUXEL_DEVICE=mustang bash boot/google-pixel-10-pro-xl/flash.sh --revert
```

### How the devices stay separated

- Firmware: `firmware/google-pixel-10-pro-xl/` vs `firmware/g7power/` vs `firmware/s10plus/`
- Kernel: `kernel/google-pixel-10-pro-xl/` vs `kernel/g7power/` vs `kernel/s10plus/`
- Device: `device/google-pixel-10-pro-xl/` vs `device/g7power/` vs `device/s10plus/`
- Boot/flash: `boot/google-pixel-10-pro-xl/` vs `boot/g7power/` vs `boot/s10plus/`
- Configs: `configs/google-pixel-10-pro-xl/` vs `configs/g7power/` vs `configs/s10plus/`
- Images: `images/google-pixel-10-pro-xl/` vs `images/g7power/` vs `images/s10plus/`
- Shared (device-agnostic): `services/`, `shell/`, `pwa/`, `tools/`, `vm/`
