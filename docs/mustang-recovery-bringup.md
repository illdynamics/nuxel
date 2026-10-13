# mustang — Nuxel Recovery & Bring-up Path

> **Target device:** Google Pixel 10 Pro XL (codename **mustang**)
> **Serial:** `58211FDCQ001LA` · **HW:** MP1.0 · **SKU:** G45RY
> **SoC:** Google Tensor G5 (gs501) · **Modem:** Samsung Exynos 5500

This document is the canonical recovery / de-bricking / bring-up checklist for
a **real mustang unit**. It is **hardware-gated**: the on-device steps below
have **not been executed yet** because no physical mustang device or factory
image is available in the build environment as of this cycle. Every step that
requires hardware is explicitly labelled `[HARDWARE-GATED]` so nobody mistakes
it for a completed action.

Pair this document with:

- `boot/recovery.sh` — the recovery / failsafe-boot shell baked into the rootfs.
- `boot/flash.sh` — the fastboot flashing front-end.
- `firmware/install-firmware.sh` + `firmware/verify-firmware.sh` +
  `firmware/manifest.yml` — the firmware extraction to `/lib/firmware` layout.
- `docs/bootloader-unlock-guide.md` — end-to-end bootloader unlock walkthrough.
- `docs/firmware-verification.md` — verification status against no device.

---

## 1. Current bring-up status (honest)

| Stage | Status |
|-------|--------|
| Scripts written & shell-syntax clean | ✅ DONE |
| `verify-firmware.sh` runs (default + `--strict`) | ✅ DONE — **30 required blobs MISSING / 0 verified** (expected: no firmware installed) |
| `install-firmware.sh --list-files/--checksums` manifest consistency | ✅ DONE — PASSED |
| Factory image downloaded (`mustang-bp1a.250405.001`) | ⛔ **NOT AVAILABLE HERE** — must be fetched by operator |
| Firefox/modem/DSP extraction on-device | ⛔ **HARDWARE-GATED** |
| `boot/flash.sh` flash sequence on-device | ⛔ **HARDWARE-GATED** |
| `boot/recovery.sh` booted on-device | ⛔ **HARDWARE-GATED** |

> The scripts and this doc are ready so that, the moment a factory zip is
> dropped into `install-firmware.sh`, and the moment a mustang device is in
> fastboot, the whole path can be executed without code changes.

---

## 2. Failsafe boot: entering recovery on mustang

### 2.1 Hardware key method — "hold Volume Up + Power"

1. Power the device fully **off** (hold **Power** (~15 s) or let the battery drain).
2. Press and **hold Volume Down + Power** together for ~15 s to force a hard
   reset / bootloader power cycle if the device is hung.
3. To boot the **recovery** shell: press and **hold Volume Up, then tap Power**.
   Keep holding Volume Up until the Google/mustang recovery image appears.
4. Release both. The device now boots the recovery *ramdisk* — on Nuxel this is
   the `boot/recovery.sh` shell (diagnostics, partition list, mount-root,
   logs, re-flash).

### 2.2 From a booted OS

```bash
adb reboot bootloader      # -> fastboot
fastboot reboot recovery   # boot recovery directly
sudo reboot recovery       # Linux / Nuxel if partially booted
```

### 2.3 From bootloader (soft-brick / bootloop)

```bash
# If the OS bootloops, intercept at the bootloader:
adb reboot bootloader          # from ADB
# or hold Power + Volume Down until recovery/fastboott
fastboot reboot recovery
```

> **Failsafe-slot note (A/B):** mustang uses A/B (seamless) slots. If slot `a`
> fails to boot, the bootloader retries slot `b`. In recovery you can read the
> active slot from `/proc/cmdline` (`androidboot.slot_suffix=a|b`) via
> `boot/recovery.sh` → `boot-slot`. See §4.

---

## 3. `boot/recovery.sh` — the recovery diagnostic shell

`boot/recovery.sh` is the recovery/failsafe shell shipped in the initramfs. It
provides the diagnostic commands required for bring-up (all implemented):

| Command | What it does |
|---------|--------------|
| `partitions` (`check_partitions`) | List block devices, UFS, `by-partlabel`, A/B slot partition sizes |
| `mounts` | Show current mounts (excluding pseudo-filesystems) |
| `dmesg` | Tail last 50 kernel messages |
| `logs` (`view_logs`) | Collect a log bundle to `/tmp/nuxel-logs` (dmesg, cmdline, partitions, mounts, modules, cpuinfo, meminfo, network, pstore) |
| `mount-root [a|b]` | Mount the root/ext4 (or f2fs) filesystem from a slot at `/mnt/root` |
| `umount-root` | Unmount `/mnt/root` |
| `hardware` | Probe DRM, input, IIO, ALSA, network, PCIe (MHI modem), USB |
| `boot-slot` | Read current boot slot from the kernel cmdline |
| `reflash` | Re-flash Nuxel OS (fastboot / ADB sideload path) |
| `factory-reset` | Wipe userdata + reset first-boot marker |
| `shell` | Drop to an interactive emergency shell |
| `bootloader` / `reboot` | Reboot to bootloader / reboot the device |

Using it in the field:

```bash
boot/recovery.sh            # interactive menu
# or, non-interactively from an initramfs init:
recovery.sh partitions
recovery.sh logs
recovery.sh mount-root a
```

---

## 4. fastboot flashing unlock (mustang)

> `[HARDWARE-GATED]` — the commands below are correct for mustang and were
> exercised as a dry-run only; the actual unlock resets the device and has not
> been performed on this serial `58211FDCQ001LA`.

Unlocking the bootloader is a prerequisite for flashing development (non
Google-signed) Nuxel images. Full end-to-end steps, including carrier-lock /
OEM-unlock toggles, live in `docs/bootloader-unlock-guide.md`.

Quick summary for the operator:

```bash
# 1. On-device: Settings > Developer options > OEM unlocking = ON

# 2. Reboot to bootloader
adb reboot bootloader
fastboot devices                # => 58211FDCQ001LA     fastboot
fastboot getvar product         # => mustang
fastboot getvar serial          # => 58211FDCQ001LA
fastboot getvar unlocked        # => no  (until unlocked)

# 3. Unlock (WIPES the device — confirm on screen)
fastboot flashing unlock
# ... confirm on the device, it factory-resets and returns to bootloader ...

fastboot getvar unlocked        # => yes
```

### 4.1 Unlock critical (only if flashing bootloader/radio)

```bash
fastboot flashing unlock_critical
```

### 4.2 Relocking

For **production** (user-signed, AVB locked) use:

```bash
./boot/flash.sh --relock-custom-key keys/nuxel-avb-private.pem --production
```

For **development** re-lock only after enrolling/matchable AVB, per
`docs/bootloader-unlock-guide.md`. Relocking with mismatched keys bricks boot;
this is documented as `[HARDWARE-GATED]`.

---

## 5. Partition / flash ordering — `boot/flash.sh`

`boot/flash.sh` implements the correct **mustang flash ordering**. AVB must be
installed first so the bootloader can verify the rest; dtbo and the boot chain
follow; init_boot and vendor_boot carry the kernel/ramdisk/dtbs; system is
flashed last via **fastbootd** with dm-verity. The script enforces this order
and verifies each image is present and non-stub before flashing.

Canonical order performed by `boot/flash.sh`:

```
1. vbmeta         (AVB verification — MUST be first)
2. dtbo           (device-tree overlay)
3. boot.img       (kernel + recovery ramdisk)
4. init_boot.img  (init / GKI boot)
5. vendor_boot.img(vendor_boot ramdisk + dtbs)
6. system.img     (fastbootd, dm-verity)
+  set_active <slot> (+ optional -w wipe)
```

Run it:

```bash
./boot/flash.sh --boot boot/boot.img/boot.img --wipe --skip-avb
# dev build -> AVB verification disabled; use --production for signed images
```

> `boot/flash.sh`, the boot chain under `boot/boot.img/`, and the flashable
> staging under `build/out/flashable` are consumed together so a real mustang
> flash uses the genuine kernel + initramfs produced by the build (not stubs).

### 5.1 Hardware-gating of flasg

- The sequence above is **correct for mustang** and matches the A/B, GKI,
  `vendor_boot`/`init_boot` world in which the device lives.
- **No flash has occurred.** Any device wearing serial `58211FDCQ001LA` is
  still on its stock Google build until §7 is completed on hardware.

---

## 6. Firmware layout on `/lib/firmware`

After extraction (see `docs/firmware-verification.md` for status), blobs land in
the standard Linux firmware tree. Key destinations for mustang:

| Component | Destination |
|-----------|-------------|
| Exynos 5500 modem | `/lib/firmware/modem*.bin`, `exynos5500_shm.bin`, `modem_cfg.txt` |
| BCM4390 WiFi 7 | `/lib/firmware/brcm/brcmfmac4390*.bin`, `*.clm_blob`, `*.nvm` |
| BCM4390 BT 5.4 | `/lib/firmware/brcm/BCM4390.hcd` |
| PowerVR DXT-72-2304 GPU | `/lib/firmware/img/pvr_*` |
| Display/touch/audio/sensors/NFC/fp/pmic/charger | `samsung/`, `cirrus/`, `bosch/`, `st/`, `ams/`, `nxp/`, `goodix/`, `maxim/`, `ti/` |

Full manifest + hashes: `firmware/manifest.yml`. Verified blobs go to
`checksum.sha256` there; anything still `PLACEHOLDER` must **not** be promoted
to verified until a real sha256 is recorded from an actual extraction.

---

## 7. End-to-end bring-up runbook (operator hardware)

> `[HARDWARE-GATED]` — run in order on the real device after the factory zip is
> downloaded. Do **not** run out of order.

**Phase 0 — acquire the factory image (operator)**
```bash
# Google publishes mustang factory images behind a consent flow at:
#   https://developers.google.com/android/images#mustang
# Download `mustang-bp1a.250405.001-factory-<xxxxx>.zip`
```

**Phase 1 — extract firmware (host, root)**
```bash
./firmware/install-firmware.sh mustang-bp1a.250405.001-factory-<xxxxx>.zip \
    --output-dir ./firmware-out --install
./firmware/verify-firmware.sh --strict
```

**Phase 2 — unlock bootloader (mustang)**   (§4)

**Phase 3 — flash Nuxel OS**
```bash
./boot/flash.sh --boot boot/boot.img/boot.img --wipe --skip-avb
```

**Phase 4 — verify**
```bash
./firmware/install-firmware.sh --verify-only
./firmware/verify-firmware.sh --strict
```

**Phase 5 — recovery practice**
```bash
# Boot to recovery without touching the OS:
adb reboot bootloader && fastboot reboot recovery
# Exercise: partitions / logs / mount-root / reflash (dry)
```

---

## 8. Serial & codename confirmation

The entire toolchain is bound to the correct device identity and *actively
checks* it rather than assuming:

| Identity | Value | Enforced by |
|----------|-------|-------------|
| Codename | `mustang` | `flash.sh` `fastboot getvar product` check; `install-firmware.sh` banner; `manifest.yml` `device:` |
| Serial | `58211FDCQ001LA` | printed in `flash.sh`, `recovery.sh`, `install-firmware.sh`, this doc |
| SKU / HW | `G45RY` / `MP1.0` | printed in `flash.sh` header + this doc |
| SoC | Tensor G5 (`gs501`) | `manifest.yml` `soc:` |
| Modem | Samsung Exynos 5500 | `manifest.yml` `modem:` |

`flash.sh` refuses to proceed (`--force` aside) if `fastboot getvar product`
does not return `mustang`, and `install-firmware.sh --list-files` fails the
manifest self-consistency check unless the manifest declares all four identity
fields correctly.

---

## 9. Hardware-gated checklist (owned by this path)

- [x] `firmware/install-firmware.sh`, `firmware/verify-firmware.sh`,
      `firmware/manifest.yml`, `boot/recovery.sh`, `boot/flash.sh`,
      `docs/mustang-recovery-bringup.md` all exist.
- [x] All scripts pass `bash -n` / `sh -n` shell syntax.
- [x] `verify-firmware.sh` runs default + `--strict`; records 30 MISSING /
      0 verified / 0 mismatch / placeholders not silently promoted.
- [x] Factory image **not available in build env** — capture path is
      documented; script hangs cleanly without it.
- [ ] Download `mustang-bp1a.250405.001` factory zip (operator).
- [ ] `install-firmware.sh <zip>` on real mustang → all 30 blobs land with
      real sha256 recorded (placeholders replaced, not faked).
- [ ] `verify-firmware.sh --strict` passes on-device.
- [ ] Bootloader unlocked on serial `58211FDCQ001LA`.
- [ ] `boot/flash.sh` flash sequence completed on-device.
- [ ] `boot/recovery.sh` exercised interactively on-device.

Until the final four rows complete on a physical unit, the mustang bring-up
state remains **`pending real hardware`** — everything this repo owns is
scripted and verified, but not yet executed against silicon.
