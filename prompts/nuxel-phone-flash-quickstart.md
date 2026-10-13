# Nuxel Phone Flash Quickstart — Google Pixel 10 Pro XL (`mustang`)

> **Canonical copy.** This file at the repository root is the single canonical
> phone-flash quickstart. `finish/nuxel-phone-flash-quickstart.md` is
> maintained **byte-identical** to this file so there is never a contradictory
> second version.
>
> **Status (2026-08-29): VM validation succeeded; physical `mustang` flashing
> remains BLOCKED — zero hardware interaction in this task.**
>
> Everything below is grounded in the current repository reality
> (`docs/mustang-recovery-bringup.md`, `docs/bootloader-unlock-guide.md`,
> `docs/firmware-verification.md`, `boot/flash.sh`, `boot/recovery.sh`,
> `boot/README.md`, `firmware/manifest.yml`, `firmware/install-firmware.sh`,
> `firmware/verify-firmware.sh`, `images/avb/`, `task-nuxel-mustang.md`).
> Any detail that cannot be verified from the repo or from live evidence is
> explicitly marked **`requires verification`** — nothing is invented.
>
> **Hard rule: do NOT flash the physical Pixel 10 Pro XL ("mustang") as part
> of this task. Zero hardware interaction.** The phone remains on its stock
> Google build; no bootloader unlock, no fastboot flash, no recovery boot has
> been performed on serial `58211FDCQ001LA` in this cycle.

---

## Flashable ready state

**❌ NOT READY TO FLASH** (`mustang`, Nuxel v0.2.0 — deep-analyze 2026-08-29).
VM validation is green, but the physical flashable image set is still absent
(no kernel build, 0/30 firmware blobs, no `boot.img`/`vbmeta.img` set) and no
hardware has been touched. See §1 for the full gate table.

---

## 1. Current flash-readiness status

| Gate | Status | Evidence / note |
|---|---|---|
| UTM ARM64 VM boots a live Nuxel environment | ✅ **PASSED** | Live UTM validation completed in this cycle: VM `nuxel-aarch64-phosh` (UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`), ARM64 Fedora guest with Phosh + Nuxel bridge/portal/notifications + HTTP API + Nuxel Home/PWA verified running. See `vm/utm-state-report.md` and the cycle's E2E classification. |
| Physical `mustang` flashing | ⛔ **BLOCKED** | Zero hardware interaction in this task. No device has been put in fastboot, no bootloader unlock, no flash. This unit is presumed on its stock Google build until §9–§15 are executed on real hardware. |
| Flashable Android-format image set (`boot.img` v4, `vendor_boot.img`, `init_boot.img`, `dtbo.img`, `vbmeta.img`, `system.img`) | ⛔ **NOT PRESENT** | `build/out/flashable/` currently contains only `cmdline.txt`. The repo ships a genuine ARM64 boot chain (`boot/boot.img/Image.gz`, `initramfs.cpio.gz`, dtbs — see §12), but not an AOSP-`mkbootimg` Android boot-image set for `mustang`. |
| Firmware blobs | ⛔ **NOT INSTALLED** | `firmware/verify-firmware.sh --strict` reports 30 required blobs MISSING / 0 verified (expected: none installed). Extraction is hardware-gated. |
| Factory image on disk | ⛔ **NOT AVAILABLE** | The `mustang-bp1a.250405.001` factory zip must be downloaded by the operator (§6). |
| Bootloader unlock | ⛔ **NOT PERFORMED** | Hardware-gated; current unlock state of this unit `requires verification`. |
| Recovery path | ⚠️ **SCRIPTED, NOT EXERCISED** | `boot/recovery.sh` + stock `flash-all.sh` path documented; never run on a real unit → `UNKNOWN` until hardware. |

**Bottom line:** the UTM VM validates the generic ARM64 / Fedora / Phosh /
service / PWA integration path. That is **not** proof that the physical
Pixel 10 Pro XL is flashable. Physical `mustang` flashing remains **BLOCKED**
until the §6–§17 gates are passed on real hardware.

---

## 2. Required prerequisites

- A real **Google Pixel 10 Pro XL (`mustang`)** with the exact identity in §5.
- A Mac (or Linux/Windows) host with a **USB data cable** (not charge-only).
- **Android platform-tools** (`adb` + `fastboot`, fastboot ≥ 34.0.0) — §3.
- The **Nuxel repository** (this repo, root `/Users/wicked/x/nuxel`).
- The **matching Google factory image** for the exact build currently on the
  phone, plus its published SHA-256 checksum — §6–§7.
- A **full backup** of the phone — every unlock/flash step wipes data (§4).
- Network access for downloads, and enough free disk for the factory zip
  (~several GB) plus extracted images.
- Acceptance that this is **experimental bring-up**: there is no "safe" first
  flash on a brand-new boot chain; the recovery path (§15) is the safety net.

---

## 3. Android platform-tools

Per `docs/bootloader-unlock-guide.md`:

```bash
# macOS
brew install android-platform-tools

# Linux (Debian/Ubuntu)
sudo apt update
sudo apt install android-sdk-platform-tools

# Windows: download from https://developer.android.com/studio/releases/platform-tools
# (URL/version on that page: requires verification)
```

Verify before touching the device:

```bash
adb version
fastboot --version        # must be >= 34.0.0 (docs/bootloader-unlock-guide.md)
```

`boot/flash.sh` refuses to run without `fastboot` on `PATH`
(`check_fastboot()` → "fastboot not found. Install android-tools-fastboot.").
Linux hosts may additionally need `android-sdk-platform-tools` udev rules /
`sudo fastboot` (see §10).

---

## 4. Backup requirements

Every one of these operations **wipes the device**:

- `fastboot flashing unlock` — factory-resets immediately after on-screen
  confirmation (`docs/bootloader-unlock-guide.md`).
- `fastboot flashing unlock_critical` — also wipes (only needed when flashing
  bootloader/radio partitions).
- `fastboot flashing lock` (re-lock) — "WILL WIPE DEVICE COMPLETELY" and is
  only for returning to stock.
- `fastboot -w` (wipe userdata, invoked by `boot/flash.sh --wipe`).
- Stock restore via the factory image's `./flash-all.sh` — wipes the device.

Before ANY unlock or flash:

1. Back up photos/media, chats, 2FA seeds, passwords, and anything
   irreplaceable.
2. Note the current Android build / bootloader version on the phone
   (exact bootloader string for this unit: `requires verification`).
3. Download and SHA-256-verify the matching stock factory image (§6–§7) and
   keep the untouched archive on the Mac as the recovery asset.
4. Record the Nuxel commit/build ID and image hashes being flashed (§16).

Do not proceed until the phone's data is safe and a known-good stock restore
path exists.

---

## 5. Exact `mustang` target identification

The target is the **Google Pixel 10 Pro XL**, codename **`mustang`**
(source: `task-nuxel-mustang.md`, `docs/bootloader-unlock-guide.md`,
`firmware/manifest.yml`, `boot/flash.sh` header):

| Field | Value |
|---|---|
| Device | Google Pixel 10 Pro XL |
| Codename | `mustang` |
| Serial | `58211FDCQ001LA` |
| Hardware version | `MP1.0` |
| Hardware SKU | `G45RY` |
| SoC | Google Tensor G5 (`gs501`) |
| Security chip | Titan M3 |
| Bootloader | Google ABL (mustang variant) |
| Verified boot | AVB 2.0, chain of trust through Titan M3 |
| Kernel target | Linux 6.12 LTS (`android-gs-mustang-6.12`, `gs501_defconfig`) |
| Display | 3120×1440 LTPO OLED, 120 Hz |
| Modem | Samsung Exynos 5500 |
| WiFi / BT | Broadcom BCM4390 (WiFi 7) / BT 5.4 |
| GPU | Imagination Technologies DXT-72-2304 (PowerVR) |

Confirm the device identity on the bench (never trust the name on the box):

```bash
fastboot devices          # => 58211FDCQ001LA    fastboot
fastboot getvar product   # => mustang
fastboot getvar serial    # => 58211FDCQ001LA
fastboot getvar unlocked  # => yes / no
fastboot getvar secure    # => yes (Titan M3 active)
fastboot getvar current-slot   # => a or b
```

The repo tooling **actively checks** this identity rather than assuming it
(`docs/mustang-recovery-bringup.md` §8): `boot/flash.sh` refuses to proceed
(without `--force`) unless `fastboot getvar product` returns `mustang`, and
`firmware/install-firmware.sh --list-files` fails unless `firmware/manifest.yml`
declares the correct `device: mustang`, `soc: tensor_g5`, `modem: exynos_5500`.

---

## 6. Factory-image acquisition

Per `firmware/manifest.yml`, `docs/hardware-bringup-prep.md`, and
`docs/bootloader-unlock-guide.md`:

- Google publishes Pixel 10 factory images only as a **signed zip behind a
  consent / dual-tab flow** at
  `https://developers.google.com/android/images#mustang`. The zip cannot be
  fetched deterministically inside an automated sandbox — this is an
  **operator step**.
- The build referenced by the repo is **`mustang-bp1a.250405.001`**; the
  download filename pattern is
  `mustang-bp1a.250405.001-factory-<xxxxx>.zip` — the exact `<xxxxx>` suffix
  **`requires verification`** from the factory-images page at download time.

```bash
# Documented operator command (suffix requires verification):
cd /tmp
wget "https://dl.google.com/dl/android/aosp/mustang-bp1a.250405.001-factory-<xxxxx>.zip"
unzip mustang-bp1a.250405.001-factory-<xxxxx>.zip
```

Keep the untouched zip as your stock-recovery asset (§15). Never modify it.
Record the exact build string and the published checksum before extracting.

---

## 7. SHA-256 verification

1. Google publishes checksums on the factory-images page for each build
   (exact page layout: **`requires verification`** at download time).
2. Verify the downloaded zip:

```bash
shasum -a 256 mustang-bp1a.250405.001-factory-<xxxxx>.zip
# compare output against the published SHA-256; abort on any mismatch
```

3. After extracting firmware with the repo tooling (§8), the repo's own
   verifier re-checks every blob:

```bash
./firmware/verify-firmware.sh --strict
```

`firmware/verify-firmware.sh` compares each blob's sha256 against the
`checksum` recorded in `firmware/manifest.yml`. Until a real extraction
records real hashes, the manifest entries are placeholders
(`sha256:verify_against_stock`) and are reported as not-yet-verified —
placeholders must **never** be promoted to "verified" (`docs/firmware-verification.md`).

---

## 8. Firmware extraction using the repo firmware tooling

The repo owns the extraction pipeline: `firmware/install-firmware.sh` +
`firmware/verify-firmware.sh` + `firmware/manifest.yml`.

Current status (`docs/firmware-verification.md`): verify-only modes are DONE
(manifest self-consistency PASSED; 30 required blobs MISSING / 0 verified —
the correct result while nothing is installed). Extract-and-flash is
**hardware-gated** — no factory zip has been processed on a real unit.

Operator flow (from `docs/mustang-recovery-bringup.md` §7 / `docs/firmware-verification.md` §4.2):

```bash
# 1) Manifest self-consistency + full blob list (no device needed)
./firmware/install-firmware.sh --list-files

# 2) Extract the firmware blobs from the matching factory zip
./firmware/install-firmware.sh mustang-bp1a.250405.001-factory-<xxxxx>.zip \
    --output-dir ./firmware-out --install

# 3) Re-verify on-device — every sha256 must match the manifest
./firmware/install-firmware.sh --verify-only
./firmware/verify-firmware.sh --strict
```

Blob categories covered by the manifest (30 required + 2 optional):
Exynos 5500 modem, BCM4390 WiFi 7, BCM4390 BT 5.4 (`BCM4390.hcd`), PowerVR
GPU (`pvr_*`), display/touch (AMB655X panel, S6SY791 touch), audio
(CS42L43 / CS35L45), sensors, NFC, fingerprint, PMIC, charger. Destinations
land under `/lib/firmware/...` (e.g. `modem*.bin`, `brcm/brcmfmac4390*.bin`,
`img/pvr_*` — full table in `docs/mustang-recovery-bringup.md` §6).

The blobs are **redistributable code from the stock Google factory image and
are not shipped in this repo**; the manifest lists them and the scripts
extract them on the operator host.

---

## 9. Bootloader unlock requirements

> **[HARDWARE-GATED]** — not executed on serial `58211FDCQ001LA` in this task.
> Full walkthrough: `docs/bootloader-unlock-guide.md`.

1. **Carrier-lock check first.** Settings → About phone → SIM status. If the
   device is carrier-locked (Verizon/AT&T-class restrictions), OEM unlocking
   is unavailable — current state for this unit: **`requires verification`**.
2. **Enable Developer options**: Settings → About phone → tap Build number
   7 times → enter PIN.
3. **Enable OEM unlocking**: Settings → System → Developer options → toggle
   **OEM unlocking** ON and confirm the security warning. If grayed out, the
   device cannot be unlocked.
4. **Enable USB debugging** and authorize the host RSA key.
5. Reboot to bootloader: `adb reboot bootloader` (or Power off → hold
   Volume Down + Power).
6. Preflight: `fastboot devices` → `58211FDCQ001LA fastboot`; `fastboot getvar
   product` → `mustang`; `fastboot getvar unlocked` → `no`.
7. **Unlock (wipes the device):**

```bash
fastboot flashing unlock
# confirm on the on-screen warning; the device factory-resets and reboots
fastboot getvar unlocked   # => yes
```

8. **Unlock critical — only if flashing bootloader/radio partitions** (also
   wipes): `fastboot flashing unlock_critical`.
9. **Titan M3 notes**: unlocking disables AVB verification of boot images and
   the "locked bootloader" guarantee; it does NOT disable Titan M3
   attestation, Keymaster, StrongBox, or hardware root of trust.
10. **Re-lock (wipes completely, stock-only)**: `fastboot flashing lock`.
    Re-locking with mismatched AVB keys bricks boot. The production relock
    path is `./boot/flash.sh --relock-custom-key keys/nuxel-avb-private.pem
    --production` (signs via `images/avb/sign.sh`, enrolls
    `fastboot oem avb_set_key`, sets `state=locksigned`) — see §13.

---

## 10. `fastboot` detection

```bash
adb devices               # Android booted: 58211FDCQ001LA    device
adb reboot bootloader
fastboot devices          # fastboot mode:  58211FDCQ001LA    fastboot
```

Always run the full preflight before anything destructive
(`docs/bootloader-unlock-guide.md` §Recovery Procedures):

```bash
fastboot devices
fastboot getvar product       # mustang
fastboot getvar serial        # 58211FDCQ001LA
fastboot getvar current-slot  # a or b
fastboot getvar unlocked      # yes (see §9 otherwise)
```

If `fastboot devices` is empty (`docs/bootloader-unlock-guide.md`):

1. Use a **data** cable, not charge-only.
2. Try another USB port; prefer USB 2.0 if USB 3.x is flaky.
3. USB debugging must be enabled **before** entering bootloader, and the host
   RSA key authorized over ADB.
4. Ensure the device is not in "charging only" USB mode.
5. Linux: `sudo fastboot` or install `android-sdk-platform-tools` udev rules.
6. Windows: install the Google USB driver.
7. Force it: `fastboot reboot-bootloader`, or power-cycle into fastboot.
8. Last resort: replace the USB-C cable and retry on another host OS.

---

## 11. Test-boot strategy where supported

The roadmap's intended test-boot step is
(`task-nuxel-mustang.md` / prior task text):

```bash
fastboot boot boot.img
```

This boots the image **without permanently writing it** — but only when the
image and the current `mustang` boot chain genuinely support it.

**Current-repo caveat (important):** the packaged artifact currently shipped
in this repo (`boot/boot.img/` + `boot/README.md`) is a **custom `NUXELBOOT1`
self-describing bundle** designed for genuine ARM64 / QEMU-UTM boot
(`Image.gz` + `initramfs.cpio.gz` + dtbs + modules). It is **not** an Android
Boot Image header-v4 image produced by AOSP `mkbootimg`, and
`boot/README.md` explicitly states the repo does **not** fabricate an Android
Boot Image header. Whether the `mustang` ABL can `fastboot boot` such a
bundle: **`requires verification`** — treat as unsupported until proven
otherwise on hardware.

Success criteria: the device must boot far enough to produce **observable
Nuxel behavior** (serial/UART, USB/ADB, display). "fastboot accepted the
command" is not success.

---

## 12. Persistent flashing via `boot/flash.sh`

`boot/flash.sh` is the repository's fastboot flashing front-end for mustang
(`docs/mustang-recovery-bringup.md` §5). Before running it:

```bash
bash -n boot/flash.sh
sed -n '1,240p' boot/flash.sh      # inspect assumptions + flags
```

Flags the script currently accepts: `--boot`, `--boot-artifact-dir`,
`--kernel-out`, `--build-boot`, `--publish-boot`, `--vendor-boot`,
`--init-boot`, `--dtbo`, `--vbmeta`, `--modem`, `--system`, `--slot`,
`--unlock`, `--relock`, `--relock-custom-key`, `--production`, `--wipe`,
`--force`, `--no-reboot`, `--skip-avb`, `--allow-unverity-dev`.

The script's **enforced** flash order (canonical for mustang):

```text
1. vbmeta          (AVB verification — MUST be first)
2. dtbo            (device-tree overlay)
3. boot.img        (kernel + recovery ramdisk)
4. init_boot.img   (init / GKI boot — required on mustang)
5. vendor_boot.img (vendor ramdisk + dtbs)
6. system.img      (fastbootd, dm-verity)
+ set_active <slot> (+ optional -w wipe)
```

Documented dev-mode invocation (`docs/mustang-recovery-bringup.md` §5):

```bash
./boot/flash.sh --boot boot/boot.img/boot.img --wipe --skip-avb
```

Built-in safety gates (do not bypass with `--force` casually):

- `check_fastboot` — refuses without `fastboot`.
- `check_device` — refuses with no device; refuses (without `--force`) if
  `fastboot getvar product` is not `mustang`.
- `verify_image` — requires each image present and above a minimum size, and
  **exits 5 on a zero-filled "DEV STUB, NOT FLASHABLE" image**; exits 2 when
  required images are missing ("Nuxel v0.2.0 does NOT produce real flashable
  images yet").

**Current blocker (as of 2026-08-19):** the required image set
(`build/out/flashable/{boot.img, init_boot.img, vendor_boot.img, dtbo.img,
vbmeta.img, system.img}`) **does not exist** in the workspace —
`build/out/flashable/` contains only `cmdline.txt`. `images/build.sh` must be
run first; the Android-honest path (`images/build.sh --android`) additionally
requires AOSP `mkbootimg`/`mkdtboimg` and the real `mustang.dtb` from the
private `android-gs-mustang-6.12` vendor kernel, which are **not available in
this environment** (`boot/README.md`). **Do not attempt a persistent flash
until that gate is genuinely passed.**

---

## 13. AVB / A-B / dynamic-partition considerations

**AVB 2.0 (verified boot):** `boot ROM → Titan M3 → Google ABL → vbmeta →
boot/dtbo/system/vendor` (`task-nuxel-mustang.md`,
`images/avb/mustang-avb.conf`).

- Development: flash a custom `vbmeta.img` with flags 2
  (`disable_verity | disable_verification`) to **both slots**:
  `fastboot flash vbmeta_a --disable-verity --disable-verification vbmeta.img`
  (and same for `vbmeta_b`) — `boot/flash.sh` does this in dev mode.
- Production: sign the chain with the Nuxel owner key via
  `images/avb/sign.sh` (avbtool, `images/avb/mustang-avb.conf`,
  `keys/nuxel-avb-private.pem`), enroll the public key
  (`fastboot oem avb_set_key`), flash signed vbmeta with enforcement flags
  intact, set `state=locksigned`, then relock. Relocking with mismatched keys
  bricks boot (`docs/mustang-recovery-bringup.md` §4.2).
- **Order matters**: vbmeta first, or the bootloader cannot verify the rest.

**A/B (seamless) slots:** every boot partition exists as `_a` and `_b`
(boot, vendor_boot, init_boot, dtbo, vbmeta, modem, dsp). Flash **both
slots**, then `fastboot set_active <slot>`. If one slot fails to boot, the
bootloader retries the other (`fastboot set_active b && fastboot reboot`);
read the active slot via `adb shell getprop ro.boot.slot`.

**Dynamic partitions:** `super` (8 GB) contains `system`, `system_ext`,
`product`, `vendor`. The `system.img` flash happens in **fastbootd**
(`fastboot reboot fastboot`), which `boot/flash.sh`'s `flash_system_dmverity`
handles, before returning to bootloader.

**`mustang` partition layout** (from `task-nuxel-mustang.md`,
`docs/bootloader-unlock-guide.md`, `boot/boot.img/mustang-boot-config.txt`):

| Partition | Size | Purpose |
|---|---|---|
| `boot_a` / `boot_b` | 96 MB | Kernel + initramfs |
| `vendor_boot_a` / `vendor_boot_b` | 96 MB | Vendor ramdisk + DTBO |
| `init_boot_a` / `init_boot_b` | 8 MB | Generic ramdisk (required, Android 14+) |
| `dtbo_a` / `dtbo_b` | 16 MB | Device tree overlay |
| `vbmeta_a` / `vbmeta_b` | 64 KB | AVB verification metadata |
| `super` | 8 GB | Dynamic: system, system_ext, product, vendor |
| `modem_a` / `modem_b` | 200 MB | Exynos 5500 firmware |
| `dsp_a` / `dsp_b` | 64 MB | DSP firmware |
| `persist` | 32 MB | Calibration data |
| `metadata` | 64 MB | OTA metadata |
| `userdata` | Remainder | User data |

**Image format notes:** boot image header **v4**; `vendor_boot.img` is
required (vendor ramdisk + DTBO); `init_boot.img` is required on Android 14+
(generic ramdisk); `dtbo.img` carries device-tree overlays; AVB uses `vbmeta`
to chain-verify boot and dtbo.

---

## 14. First-boot validation

After a persistent flash (`boot/flash.sh` reports "Flash complete!", first
boot takes ~35 s):

1. Allow the device to boot without interrupting it.
2. Verify observable behavior, in order: Nuxel kernel starts → root
   filesystem mounts → services start → Phosh/display → touch → network →
   modem → audio (each "if supported" by the current bring-up).
3. Slot check + driver/interfaces evidence
   (`docs/bootloader-unlock-guide.md` §Recovery Procedures):

```bash
adb wait-for-device shell getprop ro.boot.slot    # a (or b)
adb shell dmesg | grep -iE "brcmfmac|exynos|pvr"  # interfaces vs firmware
```

4. Use the repo's recovery diagnostic shell for deeper checks
   (`boot/recovery.sh`, `docs/mustang-recovery-bringup.md` §3):
   `partitions`, `mounts`, `dmesg`, `logs`, `mount-root [a|b]`, `hardware`,
   `boot-slot`.
5. **Bootloop:** hold Volume Down + Power ~15 s to force bootloader, re-run
   the preflight (§10), try the other slot, re-flash the boot artifacts, and
   only then consider stock recovery (§15).

---

## 15. Recovery to stock factory image

**The stock factory image is the safety net. Download + SHA-256 verify it
(§6–§7) BEFORE any experiment, and keep the untouched zip on the Mac.**

- **Restore stock (wipes device):**

```bash
unzip mustang-bp1a.250405.001-factory-<xxxxx>.zip
cd mustang-bp1a.250405.001-factory-<xxxxx>/
./flash-all.sh
```

  (Documented in `docs/bootloader-unlock-guide.md` §Recovery Procedures and
  `docs/hardware-bringup-prep.md` §8.2. The `<xxxxx>` suffix requires
  verification.)

- **If the device won't boot after a Nuxel experiment:**
  1. Force bootloader mode: hold Volume Down + Power for 15 s.
  2. Re-run the fastboot preflight (§10). If `product` still returns
     `mustang` and the device enumerates, re-flash the boot artifacts — a
     dropped/truncated transfer is the most common cause.
  3. Bootloop: try the other slot first (`fastboot set_active b && fastboot
     reboot`), then re-seal AVB off, then restore stock as the last resort.

- **Nuxel recovery shell** (`boot/recovery.sh`): enter via
  Volume Up + Power (or `fastboot reboot recovery`, or `sudo reboot
  recovery`). Commands: `partitions`, `mounts`, `dmesg`, `logs`, `mount-root
  [a|b]`, `umount-root`, `hardware`, `boot-slot`, `reflash`,
  `factory-reset`, `shell`, `bootloader`, `reboot`
  (`docs/mustang-recovery-bringup.md` §3).

- **Re-lock** only when returning to stock: `fastboot flashing lock` (wipes
  completely). Never relock with mismatched AVB keys.

- **Status:** the recovery path is fully scripted and documented, but has
  **not been exercised on real hardware** → on-device recovery status is
  **UNKNOWN / `requires verification`**.

---

## 16. What constitutes a safe/valid Nuxel hardware build

A build is safe to flash only when **every** item below is verified with
evidence — never assumed (`boot/README.md`, `docs/firmware-verification.md`,
`docs/mustang-recovery-bringup.md`):

1. **Real kernel**: Linux 6.12 LTS built from the vendor
   `android-gs-mustang-6.12` tree, `gs501_defconfig`, producing a real
   `Image.gz` (the repo's generic-ARM64 kernel path is a UTM/validation
   artifact, not a mustang flash artifact).
2. **Real `boot.img`** in Android Boot Image **header v4**, built with AOSP
   `mkbootimg` from that kernel + a real initramfs — not a `NUXELBOOT1`
   custom bundle and not a zero-filled stub.
3. **Real `vendor_boot.img`** (vendor ramdisk + DTBO) and **real
   `init_boot.img`** (required on mustang).
4. **Real `dtbo.img`** built with `mkdtboimg` from the real `mustang.dtb`
   (the vendor `mustang.dtb` lives in the private `android-gs-mustang-6.12`
   tree; not available in this environment).
5. **Correct `vbmeta.img`**: development (flags 2, verification disabled) or
   production (signed with the enrolled Nuxel key, `state=locksigned`).
6. **`system.img`** with dm-verity for the dynamic partitions (flashed via
   fastbootd).
7. **Firmware blobs** extracted from the **exact matching stock factory
   image**, with **real sha256 hashes recorded** in `firmware/manifest.yml` —
   no `PLACEHOLDER` entries promoted (§7–§8).
8. **Boot chain verified** (AVB order, both A/B slots, `set_active`).
9. **Recovery path tested** (§15) before the flash is called "safe".
10. **Provenance recorded**: Nuxel commit/build ID, image SHA-256 hashes,
    bootloader version, stock factory image version.

**Architecture constraint:** mustang remains a **vendor-kernel bootstrap**
(`android-gs-mustang-6.12`) with a later mainline migration. This quickstart
does not change that architecture.

---

## 17. Explicit warnings against flashing placeholder/stub images

- The repo's own `QUICKSTART.md` warns: the v0.2.0 build produces
  **zero-filled dev stubs** for `init_boot.img`, `vendor_boot.img`, and
  `dtbo.img` — "⛔ DO NOT FLASH TO HARDWARE."
- `boot/flash.sh` refuses zero-filled images itself: `verify_image` detects a
  fully-zero 4 KiB head and exits with **"DEV STUB, NOT FLASHABLE"**; it also
  exits 2 when required images are missing.
- `boot/README.md`: when no real kernel is available, **no `boot.img` is
  produced at all** — the repo never ships a kernel-less artifact masquerading
  as a boot image. The shipped `NUXELBOOT1` bundle is for genuine ARM64/UTM
  boot, **not** an Android boot image — do not `fastboot flash` it as one.
- `firmware/manifest.yml` placeholders (`sha256:verify_against_stock`) must
  never be silently promoted to "verified" (`docs/firmware-verification.md`).
- **Never flash an image just because it exists.** Flash only an image whose
  provenance, format, target device, boot-chain compatibility, and recovery
  path have all been verified. **VM success is not phone success** (§18).

---

## 18. VM success ≠ physical Pixel success

The UTM VM (`nuxel-aarch64-phosh`) validates the **generic ARM64 / Fedora /
Phosh / Nuxel services / HTTP API / PWA** integration path. The physical
Pixel 10 Pro XL additionally requires:

- a real `mustang`-compatible kernel (vendor `android-gs-mustang-6.12`);
- real `mustang` device-tree support and boot-chain-compatible images;
- correct firmware (modem/WiFi/BT/GPU/display/touch/audio/sensors);
- display/touch/modem/GPU/audio drivers on silicon;
- correct AVB / A-B / dynamic-partition handling;
- a tested recovery path.

Until those hardware gates pass, the only valid verdict is the one this
document records:

> **VM validation succeeded; physical `mustang` flashing remains BLOCKED —
> zero hardware interaction in this task.**

---

## 19. Reference documents (repo reality)

- `docs/mustang-recovery-bringup.md` — canonical recovery / bring-up path.
- `docs/bootloader-unlock-guide.md` — end-to-end unlock walkthrough + recovery procedures.
- `docs/firmware-verification.md` — firmware verify-only status + flash path.
- `docs/hardware-bringup-prep.md` — §8 mustang hardware recovery path.
- `boot/flash.sh` — fastboot flashing front-end (canonical order, stub guard).
- `boot/recovery.sh` — recovery / failsafe-boot diagnostic shell.
- `boot/README.md` — boot artifact chain (`NUXELBOOT1` vs Android header v4).
- `boot/boot.img/mustang-boot-config.txt` — boot image configuration + partition sizes.
- `firmware/manifest.yml` — firmware blob manifest (30 required + 2 optional).
- `firmware/install-firmware.sh`, `firmware/verify-firmware.sh` — extraction/verification tooling.
- `images/avb/sign.sh`, `images/avb/mustang-avb.conf` — AVB signing chain.
- `task-nuxel-mustang.md` — mustang target specs and device identity.
- `vm/utm-state-report.md` — current UTM VM state report (this cycle).

---

## 20. Change log / reconciliation

- **2026-08-19** — Canonical quickstart authored at the repository root
  (`nuxel-phone-flash-quickstart.md`) covering all 17 items; the copy at
  `finish/nuxel-phone-flash-quickstart.md` is maintained **byte-identical**.
  Flash-readiness status finalized after this cycle's live UTM validation:
  **VM validation succeeded; physical `mustang` flashing remains BLOCKED —
  zero hardware interaction in this task.** `finish/nuxel-boot-and-test.md`
  reconciled (non-contradictory note appended).
