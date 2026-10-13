# Nuxel Firmware Verification & mustang Recovery Path

> **Status: verify-only is DONE. Extract-and-flash is `pending real mustang device`.**
> This document records exactly what was verified without a physical device, and
> the canonical recovery/flash path that **requires hardware** to complete. It
> does **not** claim a successful on-device flash — none has occurred yet.

## 1. What this doc covers

The firmware bring-up objective for **Google Pixel 10 Pro XL (mustang)** —
Tensor G5 (gs501), Samsung **Exynos 5500** 5G modem, Broadcom **BCM4390**
WiFi 7 / BT 5.4, Imagination **PowerVR DXT-72-2304** GPU — is split into two
halves:

| Half | Deliverable | Status |
|------|-------------|--------|
| **Verify** | Scripts run in verify-only/checksum mode; manifest coherent; sha256 list produced | ✅ **DONE (this doc)** |
| **Flash** | Extract stock factory image + flash blobs/partitions on-device | ⛔ **HARDWARE-GATED** — pending real mustang device + downloaded factory zip |

The firmware blobs themselves are **re-distributable code/firmware from the
stock Google factory image** and are *not* part of this repo. `manifest.yml`
lists the blobs and their destinations; the actual bytes are extracted on an
operator host, never shipped here.

---

## 2. Verified scripts (this run)

All three scripts are owned by this group and were executed in verify/checksum
mode **without a physical device or the factory image on disk**:

| Command | Result |
|---------|--------|
| `./firmware/verify-firmware.sh --root / --strict` | Runs the sha256 gate; reports all 30 required blobs MISSING (expected — none installed) + 0 hash mismatches, exit 2. Confirms the manifest parse path + placeholder logic work. |
| `./firmware/install-firmware.sh --list-files` | **CONSISTENCY CHECK: PASSED** — prints all 32 manifest entries (30 required + 2 optional) with `PENDING` hashes and confirms the manifest covers Exynos 5500 modem, BCM4390 WiFi/BT, PowerVR GPU. Exit 0. |
| `./firmware/install-firmware.sh --checksums` | sha256 of installed blobs (none yet) + a `PENDING` report for all 30 required dests, then runs the manifest consistency gate again. Exit 0. |
| `./firmware/install-firmware.sh --verify-only --no-modem --no-wifi --no-bt --no-gpu` | Confirms the `--no-*` skips genuinely exclude the matching blob categories. Skipping modem(5)+wifi(5)+bt(1)+gpu(4)=15 blobs leaves 30 → **15 required MISSING** (exit 15). |
| `./firmware/install-firmware.sh --verify-only --no-wifi --no-bt --no-gpu` | Three-flag variant: skips wifi(5)+bt(1)+gpu(4)=10 blobs, leaving 30 → **20 required MISSING** (exit 20). |

### 2.1 Representative checksum-mode output

```
[verify-fw] Verify summary: 0 ok, 30 missing, 0 mismatch, 0 placeholder.
[verify-fw][warn] Firmware verification did NOT fully pass (rc=2).
```

and `--list-files` reports:

```
required count: 30   optional count: 2
CONSISTENCY CHECK: PASSED
Result: firmware/manifest.yml covers all expected mustang blobs
        (Exynos 5500 modem, BCM4390 WiFi/BT, PowerVR GPU).
```

The **30 missing** warnings are the *correct and honest* result while no
firmware is installed. They become hard failures — by design — once real blobs
land but a sha256 does not match.

---

## 3. Manifest coverage

`firmware/manifest.yml` enumerates all required blob categories:

| Category | Blobs | Hardware |
|----------|-------|----------|
| `modem` | 7 (5 required) | Exynos 5500 baseband + calibration + SHM |
| `wifi` | 5 | BCM4390 WiFi 7 (SDIO + PCIe + CLM + NVM) |
| `bluetooth` | 1 | BCM4390 BT 5.4 (`BCM4390.hcd`) |
| `gpu` | 4 | PowerVR DXT-72-2304 (`pvr_*`) |
| `display` / `touch` | 3 | AMB655X panel + S6SY791 touch |
| `audio` | 3 | Cirrus Logic CS42L43 + CS35L45 |
| `sensors`, `nfc`, `fingerprint`, `pmic`, `charger` | 11 | IMU/ALS, SN220, gf3636, MAX77729/77826, BQ2597x/MAX1720x |

`list_files` runs a self-consistency gate over these and **passed** — i.e. the
manifest's expectations and the scripts' expected blob list are in sync. No
manifest edits were needed (only script-level fixes, see §5).

---

## 4. The mustang recovery + flash path

The two scripts that drive device bring-up exist and are self-consistent with
the packaged boot chain:

- `boot/flash.sh` — fastboot flashing of `boot/boot.img/boot.img` +
  `boot/boot.img/initramfs.cpio.gz`, DTBO, vbmeta (`images/avb/`), modem and
  system; supports `--unlock`, `--relock`, `--relock-custom-key`, `--wipe`,
  `--production`, `--skip-avb`, `--allow-unverity-dev`.
- `boot/recovery.sh` — a recovery shell baked into the initramfs/rootfs
  (diagnostics, reflash via sideload, factory reset, A/B slot fallback). It is
  `boot/recovery.sh`, not a separate `recovery.img`.

### 4.1 Verify-only (no device) — always run first

```bash
# 1) Manifest self-consistency + full blob list
./firmware/install-firmware.sh --list-files

# 2) sha256 gate against a root tree (or the live host)
./firmware/verify-firmware.sh --root / --strict

# 3) checksum mode (installed blobs + PENDING report)
./firmware/install-firmware.sh --checksums
```

### 4.2 On-device flash — REQUIRES real mustang hardware

> **Gate:** this path has not been executed yet. Do not treat it as done.

```bash
# A. Bootloader preflight (device must be in fastboot)
fastboot devices                                # => 58211FDCQ001LA  fastboot
fastboot getvar product                         # => mustang
fastboot getvar unlocked                        # => yes (else see bootloader-unlock-guide.md)

# B. Unlock + disable AVB (wipes device), then flash the OS
./boot/flash.sh --boot boot/boot.img/boot.img --wipe --skip-avb

# C. Extract + install firmware from the stock factory image
./firmware/install-firmware.sh <factory.zip> --output-dir ./firmware-out --install

# D. Re-verify on-device — every sha256 must match the manifest
./firmware/install-firmware.sh --verify-only && ./firmware/verify-firmware.sh --strict
```

Recovery/de-bricking follow the "battle-tested mustang path" in
`docs/bootloader-unlock-guide.md` §*Recovery Procedures*.

---

## 5. Script fixes made this cycle

Only real defects in the verified scripts were changed:

1. **`--no-modem/--no-wifi/--no-bt/--no-gpu` now actually filter blob
   categories** across verify, checksums, and install (previously parsed but
   unused except `--no-modem`). Verified: `--no-wifi --no-bt --no-gpu` drops
   the 10 WiFi/BT/GPU blobs from the required list (30 → 20).
2. **Banner color** — `echo` → `echo -e` so `${BOLD}`/`${NC}` render instead of
   leaking `\033[...` literal text.
3. **`--checksums` now emits a manifest-consistent PENDING list + runs the
   sha256 gate**, so the verify-only mode is fully self-checking without a
   device.

No changes to `firmware/manifest.yml` were required — it is consistent with
both scripts.

---

## 6. Hardware-gated checklist (owned by this path)

- [x] `firmware/install-firmware.sh`, `firmware/verify-firmware.sh`,
      `firmware/manifest.yml` exist and are coherent.
- [x] Verify-only / checksum / list-files modes run and produce consistent
      sha256 + blob output.
- [ ] Download `mustang-bp1a.250405.001` factory zip **on the operator host**.
- [ ] `./firmware/install-firmware.sh <factory.zip> --output-dir ... --install`
      on a **real mustang device** (root).
- [ ] `./firmware/verify-firmware.sh --strict` passes on-device (all 30 blobs
      present, no PENDING hashes).

Until the last three are completed on real hardware, the flash state is
explicitly **`pending real mustang device`**.
