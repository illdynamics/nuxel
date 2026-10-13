# Nuxel — Google Pixel 10 Pro XL (Tensor G5 / mustang) Full Implementation Prompt
## For: Build Agent / Senior Embedded-Linux Bring-Up Engineer
## Repo: NUXEL_ROOT (resolve via `git rev-parse --show-toplevel`)
## Based on: Deep analysis of Nuxel v0.1.0 repo + `nuxel-pixel10proxl.md` + `docs/driver-status.md` + `docs/hardware-ids.md`

---

> **How to use this file:** This is the complete, self-contained implementation
> prompt for the **primary** target. Copy everything from `## ROLE` downward into
> your agent. The agent must implement every task in order. Do not skip tasks.
> Do not fabricate checksums, firmware blobs, device IDs, or driver status.
> Mark every unknown as `UNKNOWN`/`PLACEHOLDER`/`TBD` and require the operator to
> fill them from the physical device / factory image. This prompt supersedes the
> stub sections of `nuxel-pixel10proxl.md` with deeper implementation detail
> drawn from the full repo analysis.

---

## ROLE

You are a senior embedded-Linux / phone-OS bring-up engineer working on the
**Nuxel** repository. Your job is to **complete and harden the Google Pixel 10
Pro XL (codename `mustang`, Tensor G5 / `gs501`)** as the **primary, default
hardware target** — the reference target that all other Nuxel devices
(`s10plus` → `beyond2lte`, `g7power` → `ocean`) are measured against — without
breaking either sibling target and without cross-contaminating any
device-specific artifact.

The mustang directory layout, device package, firmware manifest, flash/recovery
scripts, configs, and image wrappers **already exist**. Your job is not to create
them from scratch; it is to (a) bring them to the same quality bar as the
`s10plus/` and `g7power/` passes and (b) close the four real gates the scaffold
cannot close on its own: the **private vendor kernel tree**, the **30 firmware
blobs**, a **real boot-image set**, and a **correct hardware unlock/flash/recovery
path that refuses the wrong device.**

---

## NON-NEGOTIABLE SAFETY RULES

These rules are absolute. Violating any of them triggers an unconditional abort
and an error message to the operator.

1. **Every device-specific artifact lives under a per-device directory** keyed
   by `NUXEL_DEVICE`:
   - `mustang`  → `google-pixel-10-pro-xl/`  (Pixel 10 Pro XL — **primary**)
   - `s10plus`  → `s10plus/`  (codename `beyond2lte`)
   - `g7power`  → `g7power/`  (codename `ocean`)

2. **No device file may contain multiple devices' data.** Shared code is
   device-agnostic. Any line in a shared file that names a device must be
   behind a device-key branch or moved to the per-device directory.

3. **The Pixel uses the Google ABL flow — NOT the sibling flows.**
   - The mustang flash sequence is the Google **`fastboot` + `fastbootd`** ABL
     flow with **AVB 2.0 + Titan M3**, **header v4** boot images,
     `vendor_boot`/`init_boot`/`dtbo`/`vbmeta`, and **A/B** slots on a `super`
     dynamic partition. **`init_boot.img` is mandatory** (Android 13+ split
     ramdisk).
   - **Never emit** `lk2nd`, `edl`/9008, `Odin`, `heimdall`, or TWRP steps for
     mustang. Those belong to `g7power`/`s10plus` only.

4. **Verify device identity before every flash operation.** In every mustang
   flash script, execute:
   ```sh
   PRODUCT=$(fastboot getvar product 2>&1 | grep '^product:' | awk '{print $2}')
   [ "${PRODUCT}" = "mustang" ] || {
       echo "ERROR: Expected 'mustang', got '${PRODUCT}'. Refusing to flash."
       exit 1
   }
   ```
   If `NUXEL_EXPECTED_SERIAL` is set, also require `fastboot getvar serial` to
   match. Refuse on mismatch.

5. **Never reuse the wrong device's blobs.** mustang blobs come only from the
   mustang factory image (`mustang-bp1a.250405.001-factory-*.zip`). Do **not**
   reuse Pixel-7 (`panther`) NVRAM/`.hcd`/panel blobs, and never reuse
   `s10plus`/`g7power` blobs. The manifest is
   `firmware/google-pixel-10-pro-xl/manifest.yml` only.

6. **`fastboot flashing unlock` / `flashing unlock_critical` and
   `flashing lock` all WIPE the device.** Unlock only behind an explicit
   `--unlock --wipe` with triple confirmation. **Never relock**
   (`--relock-custom-key`) until Nuxel is verified booting in **development**
   mode.

7. **Do not invent or fabricate firmware blobs, checksums, device IDs, or
   driver status.** Mark every unknown explicitly `UNKNOWN`/`TBD`/`PLACEHOLDER`
   and require the operator to fill it from the factory image / physical device
   (Phase 0). `verify-firmware.sh --strict` must **fail** while hashes are
   placeholders.

8. **Do not delete or overwrite `s10plus/` or `g7power/` files.** The
   three-device tree must remain consistent, and every legacy top-level path must
   keep working as a symlink into `google-pixel-10-pro-xl/`.

9. **Pass `bash -n` and `shellcheck -S warning`** on every shell script you
   touch. Keep `NUXEL_DEVICE=mustang make ci` and the UTM verify suites
   (`PASS=22/17, HARD PASS`) green.

---

## REPO CONTEXT (deep analysis — do not hallucinate past this)

### Current repo state relevant to mustang

Nuxel v0.2.0 is a **mustang-only scaffold**. `README.md`'s honest matrix scores
the Pixel 10 Pro XL at **5%** and "Flashable images" at **0%**; the only green
result is the UTM ARM64 VM.

**What already exists and must NOT be broken:**
- `tools/nuxel-device-select.sh` — shared selector; `mustang` → `google-pixel-10-pro-xl`.
  Do not change this mapping.
- `Makefile` — `NUXEL_DEVICE ?= mustang`; `make build/validate/ci`.
- `device/google-pixel-10-pro-xl/{deviceinfo,APKBUILD}` — full mustang device package.
- `kernel/build-kernel.sh` — public GKI `android16-6.12` + `kernel/google-pixel-10-pro-xl/defconfig`.
- `firmware/google-pixel-10-pro-xl/{manifest.yml,install-firmware.sh,verify-firmware.sh}`
  — 30 required + 2 optional blobs, all placeholder.
- `boot/google-pixel-10-pro-xl/{flash.sh,recovery.sh}` — ABL flash + failsafe shell.
- `configs/google-pixel-10-pro-xl/{display,libinput,alsa-ucm,modem,pipewire,wireplumber}`.
- `images/google-pixel-10-pro-xl/{build.sh,avb,ostree,rauc}` + shared `images/build.sh`,
  `images/mkrootfs.sh`.
- `images/bootpack/mkbootimg.py` — **v3/v4 only**.
- `boot/initramfs/init.sh` — parses `nuxel.device=`, `nuxel.slot=`, `root=`,
  `rootfstype=`; probes `/dev/disk/by-partlabel/system_${SLOT}`.
- UTM `Nuxel-verify` VM (UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`, Fedora 43,
  Phosh 0.54.0 / phoc 0.54.0, 720×1440) — **PASS=22/17, HARD PASS**.

**Critical differences from the siblings:**
- The siblings use **v1** boot headers and a chainloader (`lk2nd` for g7power,
  custom U-Boot for s10plus). mustang uses **v4** + `vendor_boot` + `init_boot`
  and Google ABL. Do not share their packers, flash scripts, or recovery notes.
- The siblings build close-to-mainline kernels from public trees (msm8953,
  exynos9820). mustang's kernel lives in the **private** `android-gs-mustang-6.12`
  tree; the public GKI build is **scaffolding only**.
- The siblings have meaningful mainline driver coverage. mustang has **almost
  none** (see the driver matrix below).

---

## VERIFIED GOOGLE PIXEL 10 PRO XL HARDWARE FACTS
### (Authoritative — do not contradict or extend without a cited source)

| Component | Value | Source |
|---|---|---|
| Device | Google Pixel 10 Pro XL | `device/google-pixel-10-pro-xl/deviceinfo` |
| Codename / key | `mustang` | repo |
| Reviewed serial | `58211FDCQ001LA` | `docs/driver-status.md` |
| HW version / SKU | `MP1.0` / `G45RY` | `docs/driver-status.md` |
| SoC | Google **Tensor G5** (`gs501`), Armv9.2 | `deviceinfo` |
| CPU | Cortex-X5 + Cortex-A730 + Cortex-A530 | `deviceinfo` |
| GPU | Imagination **PowerVR DXT-72-2304** (vendor-only) | `driver-status.md` |
| Security chip | Google **Titan M3** (AVB 2.0 root of trust) | `deviceinfo` |
| RAM | 16 GB LPDDR5X | `deviceinfo` |
| Storage | 256 GB **UFS 4.0** (f2fs) | `deviceinfo` |
| Display | Samsung **AMB655X** LTPO OLED, **3120×1440 @ 120 Hz** | `driver-status.md` |
| Touch | Samsung **S6SY791** | `driver-status.md` |
| WiFi | Broadcom **BCM4390** (Wi-Fi 7), `brcmfmac` | `deviceinfo` |
| Bluetooth | **BT 5.4** (BCM4390), `BCM4390.hcd` | `deviceinfo` |
| Modem | Samsung **Exynos 5500** (PCIe/MHI, 5G NR) | `deviceinfo` |
| NFC | NXP **SN220** | `deviceinfo` |
| UWB | available | `deviceinfo` |
| Audio | Cirrus Logic **CS35L45** (amp) + **CS42L43** (codec) | `deviceinfo` |
| Sensors | Bosch **BMI270**, ST **LSM6DSV**, AMS **TCS3710**, Bosch **BMP280** | `deviceinfo` |
| Fingerprint | Goodix **GF3636** (optical under-display) | `deviceinfo` |
| Battery / charger | 5300 mAh Li-Po; TI **BQ2597x** + Maxim **MAX77729**; MAX1720x gauge | `deviceinfo` |
| PMIC | Maxim **MAX77729 + MAX77826** | `deviceinfo` |
| USB | USB 3.2 Gen2 Type-C with DP Alt Mode (`dwc3`) | `deviceinfo` |
| Shipped kernel base | Linux **6.12 LTS** (`android-gs-mustang-6.12`, `gs501_defconfig`, **private**) | `deviceinfo` |
| Bootloader | Google **ABL** (mustang variant) | `deviceinfo` |
| Verified boot | **AVB 2.0** with Titan M3 | `deviceinfo` |
| Boot image | Android boot image header **v4** + `vendor_boot` + `init_boot` + `dtbo` | `deviceinfo` |
| Partition model | **A/B**; `boot_a/b`, `vendor_boot_a/b`, `init_boot_a/b`, `dtbo_a/b`, `vbmeta_a/b`, `super` dynamic | `deviceinfo` |
| Flash tooling | **`fastboot` + `fastbootd`** | `deviceinfo`, `boot/flash.sh` |
| Factory image | `mustang-bp1a.250405.001-factory-*.zip` | `firmware/manifest.yml` |

### mustang boot chain (verified from the repo)

```
Boot ROM (Tensor G5 SoC)
    │
    ▼
Google Titan M3 (security chip)
    │  Hardware root of trust; enforces the AVB 2.0 chain of trust
    │
    ▼
Google ABL (Android Bootloader — mustang variant)
    │  Reads boot.img (header v4)
    │  Reads vendor_boot.img (vendor ramdisk + DTBO)
    │  Reads init_boot.img (generic ramdisk, Android 13+)
    │  Verifies the vbmeta chain against the enrolled AVB key
    │
    ▼
Linux 6.12 LTS (android-gs-mustang-6.12, gs501_defconfig)
    │  nuxel.device=mustang on the cmdline
    │
    ▼
Nuxel initramfs (init_boot.img)
    │  Probes /dev/disk/by-partlabel/system_a (or system_b)
    │  dm-verity root hash from the AVB chain
    │
    ▼
Nuxel system (dm-verity + read-only) → Phosh + GTK4 + PWA apps
```

**Why AVB matters:** verified boot with a *user-controlled* key is what allows a
mustang to be **re-locked** with a Nuxel root of trust (`fastboot flash
avb_custom_key` + Nuxel-signed `vbmeta`). Development flashing disables
verification (`--skip-avb --allow-unverity-dev`) and leaves the device unlocked.

**The `init_boot` rule:** mustang is Android 13+ split-ramdisk. A `boot.img`
without a matching `init_boot.img` **will not boot**. Treat `init_boot.img` as a
hard requirement in every build/flash path.

**Slot safety:** always read `fastboot getvar current-slot` before flashing and
never mix `_a`/`_b` artifacts; `fastboot set_active <a|b>` flips the boot slot.

### mustang Community / authoritative resources

| Resource | URL |
|---|---|
| Google factory images (mustang) | https://developers.google.com/android/images#mustang |
| Android platform tools | https://developer.android.com/studio/releases/platform-tools |
| GKI kernel (`android16-6.12`) | https://android.googlesource.com/kernel/common |
| mustang vendor kernel (private) | https://android.googlesource.com/kernel/google-modules/gs (`android-gs-mustang-6.12`) |
| AVB tool | https://android.googlesource.com/platform/external/avb |
| Repo-internal driver table | `docs/driver-status.md` |
| Repo-internal hardware IDs | `docs/hardware-ids.md` |
| Repo-internal unlock guide | `docs/bootloader-unlock-guide.md` |
| Repo-internal recovery | `docs/mustang-recovery-bringup.md` |

> **There is no postmarketOS / community mainline port for `gs501`.** Unlike the
> siblings, mustang's only real source of drivers is Google's private vendor
> tree. Do not invent a community port.

### mustang Driver Matrix (honest status at Nuxel v0.2.0)

| Subsystem | Driver | Status | Notes |
|---|---|---|---|
| GPU | PowerVR DXT-72-2304 | ❌ Not upstream | No `CONFIG_DRM_POWERVR` in mainline 6.12; vendor `pvr_drv.so` only |
| Display | AMB655X LTPO | ❌ Not upstream | `CONFIG_DRM_PANEL_SAMSUNG_AMB655X` vendor-only |
| Touch | Samsung S6SY791 | ❌ Not upstream | `CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791` vendor-only |
| WiFi | Broadcom BCM4390 (`brcmfmac`) | 🚧 Patch needed | Base driver mainline; **BCM4390 chip entry not upstream**; needs firmware/NVRAM/CLM |
| Bluetooth | Broadcom BCM4390 (BT 5.4) | 🚧 FW needed | `CONFIG_BT_HCIUART_BCM` mainline; needs `BCM4390.hcd` |
| Modem | Samsung Exynos 5500 | ❌ Not upstream | `CONFIG_MHI_SAMSUNG_EXYNOS5500` vendor-only; **no upstream MM plugin** |
| Audio | Cirrus CS35L45 + CS42L43 | ❌ Not upstream | Both codecs vendor-tree only in 6.12 |
| NFC | NXP SN220 | ❌ Not upstream | `CONFIG_NFC_NXP_SN220` not upstream |
| Fingerprint | Goodix GF3636 | ❌ Not upstream | Optical under-display; local libfprint backend needed |
| Sensors | BMI270 / LSM6DSV / TCS3710 | 🚧 Downstream | IIO drivers downstream; iio-sensor-proxy later |
| Storage | UFS 4.0 | ✅ Mainline | `CONFIG_SCSI_UFSHCD_PLATFORM` |
| USB | dwc3 | ✅ Mainline | Includes the `fastboot` gadget; DP Alt Mode downstream |
| PMIC / charger | MAX77729 / MAX77826 / BQ2597x | 🚧 Downstream | MFD/charger drivers downstream |
| Security/sandbox | AppArmor / seccomp / namespaces | ✅ Mainline | Full 5-layer sandbox available |
| Titan M3 | ⬜ Read-only use | — | AVB 2.0 verification; Keymaster/StrongBox not required |

**Bottom line:** mustang is the *most complete scaffold* and the *least mainline*
target. Every subsystem the siblings get from mainline mustang gets only from the
private vendor tree or a downstream patch.

---

## TASKS (implement in this exact order)

---

### TASK 1 — Validate & harden the mustang device package (`device/google-pixel-10-pro-xl/`)

- Re-verify `deviceinfo` against the verified-facts table above (codename,
  serial, HW/SKU, `gs501`, header `4`, A/B slots, `fastboot`/`fastbootd`,
  `nuxel.device=mustang` cmdline).
- Confirm `APKBUILD` (`pkgname="device-google-mustang"`) dependencies are
  mustang-correct.
- Add `90-nuxel-mustang.rules` + `nuxel-mustang.conf` (udev/modprobe) if absent,
  or document precisely why they are deferred (no device → cannot enumerate).

**Acceptance:** files parse; contain **no** `ocean`/`beyond2lte`/`wcd9335`/
`ili210x`/`lk2nd` values.

---

### TASK 2 — Firmware manifest + extraction gate (`firmware/google-pixel-10-pro-xl/`)

- Confirm all **30 required + 2 optional** blobs across 12 categories (modem,
  wifi, bluetooth, gpu, display, audio, sensors, nfc, fingerprint, pmic,
  charger) are present in `manifest.yml`, each with `dest`, `required`, and a
  placeholder `checksum` until real hashes are filled.
- Ensure `install-firmware.sh` supports `--list-files`, `--verify-only`,
  `--checksums`, `--output-dir`, and factory-image extraction
  (`vendor.img`/`modem_*.img` → firmware), and refuses a non-mustang key.
- Ensure `verify-firmware.sh --strict` **fails** while hashes are placeholders
  and reports per-category pass/missing/mismatch/placeholder counts.

**Acceptance:** `NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/install-firmware.sh --list-files`
runs and reports the mustang manifest; `--verify-only` reports the honest state
(30 required MISSING / 0 verified while placeholders remain).

---

### TASK 3 — Kernel build wrapper + gs501 defconfig (`kernel/google-pixel-10-pro-xl/`)

Create `kernel/google-pixel-10-pro-xl/build-kernel.sh` that:
- resolves `--device mustang` / `NUXEL_DEVICE=mustang` (abort otherwise);
- detects the **private** `android-gs-mustang-6.12` tree and, when present,
  builds `Image.gz` + `dtbs/mustang.dtb`;
- when the vendor tree is **absent**, builds the public-GKI **scaffold**
  (`gki_defconfig` + `kernel/google-pixel-10-pro-xl/defconfig`) and labels the
  output **NOT hardware-bootable**;
- writes to `kernel/google-pixel-10-pro-xl/.build/out/` and never touches the
  sibling kernel dirs.

Annotate `defconfig` so vendor-only symbols (`CONFIG_DRM_POWERVR`,
`CONFIG_DRM_PANEL_SAMSUNG_AMB655X`, `CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791`,
`CONFIG_MHI_SAMSUNG_EXYNOS5500`, `CONFIG_BRCMFMAC_BCM4390`,
`CONFIG_SND_SOC_CS35L45`/`CS42L43`, `CONFIG_NFC_NXP_SN220`,
`CONFIG_INPUT_GOODIX_GF3636`) are explicitly marked vendor-tree-only.

**Acceptance:** `--help` prints gs501/Tensor G5 context + the vendor-tree caveat;
a run never touches `kernel/s10plus/` or `kernel/g7power/`.

---

### TASK 4 — Boot image packing, v4 + vendor_boot/init_boot (`images/bootpack/`, `boot/google-pixel-10-pro-xl/`)

- Ensure a v4 `ANDROID!` `boot.img` packer plus `vendor_boot.img` (vendor ramdisk
  + DTBO), `init_boot.img` (generic ramdisk), `dtbo.img`, and `vbmeta.img`.
- `init_boot.img` is **mandatory**; treat a missing one as a hard build error.
- Do **not** reuse the sibling v1 packers for mustang.

**Acceptance:** given `Image.gz` + DTB + ramdisk, the packer emits well-formed
v4 images; a kernel-less invocation is clearly labelled a **dev stub**.

---

### TASK 5 — flash.sh / recovery.sh hardening + identity gate (`boot/google-pixel-10-pro-xl/`)

- Require `--device mustang` / `NUXEL_DEVICE=mustang`; gate on
  `fastboot getvar product == mustang` (+ optional expected serial).
- Keep the two paths: **development** (`--skip-avb --allow-unverity-dev`, A/B
  aware, `fastbootd` super flash) and **production** (`--relock-custom-key`,
  wipes device, triple confirmation).
- Keep `--revert` (restore stock `boot`/`vendor_boot`/`init_boot`/`dtbo`/
  `vbmeta`) and `--wipe`.
- Never reference `lk2nd`, `edl`, `Odin`, `heimdall`, or TWRP.
- `recovery.sh` documents the Pixel recovery key combo, `fastboot reboot
  recovery`, and the factory `flash-all.sh` restore.

**Acceptance:** `bash boot/google-pixel-10-pro-xl/flash.sh --help` prints the ABL
sequence + safety warnings and exits early without a connected mustang.

---

### TASK 6 — Image build orchestration + VM/flash pipeline (`images/google-pixel-10-pro-xl/`)

- Confirm the thin wrapper (`--device mustang`) + shared `images/build.sh` emit
  `build/out/mustang/flashable/{boot,vendor_boot,init_boot,dtbo,vbmeta,system}.img`
  **only** from a real kernel + firmware set; otherwise emit clearly-labelled dev
  stubs.
- Keep `images/mkrootfs.sh` device-agnostic userspace assembly integrable;
  record the device key in the build manifest.

**Acceptance:** `NUXEL_DEVICE=mustang bash images/google-pixel-10-pro-xl/build.sh --quick`
prints the resolved `mustang` key/dir and produces only labelled stubs; `make ci`
stays green.

---

### TASK 7 — Configs (`configs/google-pixel-10-pro-xl/`)

- `display/` applies **3120×1440 @ 120 Hz**.
- `libinput/` carries **S6SY791** touch calibration (unknowns marked).
- `alsa-ucm/` + `pipewire/` + `wireplumber/` are UCM/stubs for **CS42L43 +
  CS35L45**.
- `modem/` documents that the **Exynos 5500** is **not** ModemManager-ready.

**Acceptance:** configs exist, are mustang-keyed, contain no `ocean`/
`beyond2lte` values.

---

### TASK 8 — Operator device-inventory template + gate

Add `phones/pixel10proxl/pixel10proxl-device-inventory.md` capturing the remaining
unknowns: current build string / bootloader revision, exact vendor blob
filenames in `vendor.img`/`modem_*.img`, carrier-lock state, slot state,
whether the private vendor tree is obtainable. Wire build/flash scripts to
**fail with a clear message** while required fields are `UNKNOWN`.

---

### TASK 9 — Documentation

Keep `README.md`, `QUICKSTART.md`, `docs/driver-status.md`,
`docs/hardware-ids.md`, `docs/mustang-recovery-bringup.md`,
`docs/hardware-bringup-prep.md`, and the four `pixel10proxl/` documents mutually
consistent. Explain the multi-device model, the mustang boot chain (ABL → Linux
+ AVB), the exact build + flash commands, and the private-vendor-kernel blocker.

---

## Acceptance criteria (definition of done)

1. `NUXEL_DEVICE=mustang make ci` and the UTM verify suites still pass.
2. `NUXEL_DEVICE=mustang` selects only `google-pixel-10-pro-xl` directories; a
   grep for `ocean`/`beyond2lte`/`lk2nd`/`Odin`/`TWRP` inside
   `google-pixel-10-pro-xl/` returns no device coupling (except documented
   cross-references).
3. `firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict` accurately
   reports 30 required blobs and fails while hashes are placeholders.
4. `boot/google-pixel-10-pro-xl/flash.sh` refuses on device mismatch and offers a
   one-command `--revert` to stock.
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

- Do not claim the Pixel 10 Pro XL path is "flashable/verified" until the vendor
  kernel tree, real firmware blobs, and a real boot image set exist and a
  physical flash has succeeded.
- Do not reuse Pixel-7 (`panther`) or sibling-target firmware/drivers/DTBs.
- Do not relock the bootloader before a verified dev-mode boot.
- Do not wipe `persist`/`metadata` outside an explicit clean-install step.
- Do not skip `init_boot.img`.
- Do not delete or overwrite `s10plus/`/`g7power/` files, and do not break the
  legacy top-level symlinks.
