# Nuxel — Motorola Moto G7 Power manual flash guide

**Device:** Motorola Moto G7 Power **XT1955** (Qualcomm Snapdragon 632 / SDM632,
msm8953 family, codename **`ocean`**)
**Nuxel:** `v0.3.1-alpha` · **Guide written:** 2026-10-13
**Authoritative repo docs:** this file is the "do it now" checklist. Background:
`phones/g7power/g7power-go-guide.md`, `phones/g7power/moto-g7-power-quickstart.md`,
`docs/g7power-bringup.md`, `docs/g7power-device-inventory.md`.

> ⚠️ **Read §2 (safety) and §5 (backups) before you flash anything.**
> The G7 Power boot chain is **PBL → stock ABOOT → lk2nd → mainline Linux →
> Nuxel initramfs → rootfs**. `lk2nd` is a *second-stage bootloader* you must
> flash to the `boot` partition; the stock ABOOT cannot boot a mainline kernel
> by itself. Flashing in the wrong order (lk2nd before a valid `dtbo`) is the
> classic msm8953 **soft-brick**.
>
> **There is no "just `fastboot flash boot` once" path on this device — it is a
> two-phase flash.** Follow §6 exactly, in order.

---

## 0. TL;DR — the shortest safe path

1. **Unlock the bootloader** (Motorola code from the portal). Wipes the device. → §4
2. **Back up your stock `boot` and `dtbo`** — this is your undo button. → §5
3. **Verify EDL (Qualcomm 9008) enumerates** — your unbrick safety net. → §9.1
4. **Verify the Nuxel artifacts** (hashes) from the release tarball. → §4.4
5. **Phase 1 (stock ABOOT fastboot):** flash `dtbo` (your stock backup) **first**,
   then `lk2nd`. → §6.1
6. **Phase 2 (lk2nd fastboot):** flash the Nuxel `boot.img`, then the rootfs. → §6.2
7. Reboot and watch the Nuxel boot splash + initramfs. → §7

The whole thing, using the repo's own script (which enforces the order):

```bash
cd /x/nuxel
bash boot/g7power/flash.sh --device g7power \
    --dtbo   /path/to/stock-dtbo.img \
    --lk2nd  build/out/g7power/lk2nd.img \
    --boot   build/out/g7power/nuxel-ocean-boot.img \
    --rootfs build/out/g7power/nuxel-ocean-rootfs.img
```

---

## 1. What you are flashing (artifact inventory)

`v0.3.1-alpha` is built **by the GitHub release workflow** (Actions → “Release”,
tag `v0.3.1-alpha`). The G7 Power release archive is:

```
nuxel-v0.3.1-alpha-g7power.tar.gz
```

Extract it and you get `g7power/`:

| File | What it is | Flashes to |
|---|---|---|
| `g7power/lk2nd.img` | lk2nd msm8953 second-stage bootloader (built from `msm8916-mainline/lk2nd`) — **required** | `boot` (phase 1, stock ABOOT) |
| `g7power/nuxel-ocean-boot.img` | mainline kernel `Image.gz` + Nuxel initramfs + `sdm632-motorola-ocean.dtb`, packed as an Android **boot header v1** (page 2048) | `boot` (phase 2, lk2nd fastboot) |
| `g7power/nuxel-ocean-rootfs.img` | Nuxel userspace, plain **ext4**, writable (Phase-1, no dm-verity/AVB) | `userdata` |
| `g7power/build-manifest.json` | device key, kernel commit, load addresses used, timestamps | — |
| `g7power/sha256sums.txt` | per-file checksums you verify before flashing | — |

> **Not in the archive:** `dtbo.img`. You flash **your own backed-up stock
> `dtbo`** in phase 1 (see §5, §6.1). There is no Nuxel DTBO for this device.

> **No `userdata.img`.** In Phase 1 the rootfs image *is* the userdata payload:
> `nuxel-ocean-rootfs.img` is flashed to the **shared `userdata`** partition
> (see §6.2). No separate `userdata.img` is produced or needed.
>
> **`lk2nd` is specific to this phone.** It is required here because the stock
> Motorola ABOOT cannot load a mainline DTB/cmdline; that is **not** a
> general Nuxel bootloader. The Galaxy S10+ (`s10plus`) does **not** use `lk2nd`
> at all — do not mix the two devices' bootloaders.

Boot image facts (Android boot header v1, page size 2048):

```
kernel  load addr : 0x80008000
ramdisk load addr : 0x81000000
tags    load addr : 0x80000100
```

The device is **A/B** (`boot_a`/`boot_b`, `dtbo_a`/`dtbo_b`, current slot is
whatever `fastboot getvar current-slot` reports — the stock unit here booted
`_b`). `fastboot flash boot` / `fastboot flash dtbo` write the **current slot**;
that is what you want. The rootfs goes to the shared `userdata` partition.

---

## 2. Safety — read this twice

**Protected partitions — NEVER pull, NEVER flash, NEVER `dd` these.** They hold
per-unit data (IMEI, radio calibration, DDR training) that cannot be regenerated:

```
modemst1  modemst2  fsg  fsc  ddr  persist  misc
```

1. **dtbo BEFORE lk2nd — always.** A missing/empty/corrupt `dtbo` combined with a
   custom `boot` is the classic msm8953 soft-brick. The repo script enforces this
   order in code; if you flash manually, do it in the exact order in §6.
2. **Never re-lock the bootloader** (`fastboot oem lock`) while Nuxel is
   installed. Relock is out of scope for this bring-up; it can hard-brick a
   device with a non-stock image.
3. **Keep the bootloader unlocked** for the whole bring-up and testing period.
4. **EDL (Qualcomm 9008) is the safety net.** Confirm it enumerates *before* your
   first flash (§9.1). If `fastboot` ever becomes unreachable, EDL recovers it.
5. **Have backups.** Stock `boot` + `dtbo` (§5) and ideally the full stock
   firmware package for your exact variant.
6. **A real USB *data* cable.** Charge-only cables behave exactly like a dead
   port: the phone never enumerates for `fastboot`. Use a known-good data cable
   and a direct port (no hub).
7. **Battery > 60%.**
8. Device identity is checked before every flash: `fastboot getvar product` must
   print **`ocean`**, otherwise every script refuses.

> This build has **not been proven to boot on your specific unit yet**. "Built,
> signed-off by CI, hash-verified" is **not** "boots". §7 is the actual test.

---

## 3. Modes — which button combo, and when

The G7 Power has three modes you use. The **same `fastboot` tool** is used for
phase 1 and phase 2, but it is talking to **two different bootloaders**.

| Mode | How to enter | What provides `fastboot` | Used for |
|---|---|---|---|
| **Stock ABOOT fastboot** | Power off. Hold **Vol Down + Power** until the bootloader/fastboot screen appears. | The phone's stock Motorola bootloader (ABOOT) | Phase 1: `flash dtbo`, `flash boot lk2nd.img` |
| **lk2nd fastboot** | After flashing `lk2nd.img` to `boot`, run `fastboot reboot bootloader` (or reboot and hold Vol Down). | lk2nd (the msm8953 bootloader you just flashed) | Phase 2: `flash boot nuxel-ocean-boot.img`, `flash userdata rootfs` |
| **EDL / Qualcomm 9008** | Power off. Hold **Vol Down + Vol Up**, then plug USB. | Qualcomm PBL over USB (`VID:05C6 PID:9008`) | Unbrick only |

Confirm from the host:

```bash
adb devices                 # shows the phone only in a booted OS / TWRP
fastboot devices            # shows the phone in EITHER fastboot (ABOOT or lk2nd)
fastboot getvar product     # must print: ocean
fastboot getvar current-slot
fastboot getvar unlocked    # must print: yes (otherwise unlock first, §4)
```

> Tip: run `bash boot/g7power/flash.sh --device g7power --unlock-help` for the
> Motorola unlock walkthrough, and `... --edl` for the EDL walkthrough.

---

## 4. Prerequisites

### 4.1 Hardware
- Motorola Moto G7 Power **XT1955** (`ocean`) — a **spare** unit; flashing wipes it.
- A **USB data cable** (not charge-only) + a direct USB port.
- Battery **> 60%**.
- Optional but strongly recommended: a **microSD card** to hold the stock backup.

### 4.2 Host tools
- `fastboot` (Android platform-tools ≥ 34): `fastboot --version`
- `adb`: `adb version`
- `python3` (for `tools/read-boot-header-v1.py`)
- For unbrick: **`edl`** (bkerler/edl v3) or Windows **QFIL** (see §9.1).

### 4.3 Only you can provide (do these first — longest lead item is the unlock code)
- **Motorola bootloader unlock code** — request it from the Motorola portal using
  your device's IMEI + serial. There is no way to automate this and it is
  **manual** (minutes → hours). The phone's "OEM unlocking" toggle should be
  enabled (**Settings → System → Developer options → OEM unlocking**).
- **Your unit's stock `boot` + `dtbo`** — pulled in §5.

> **Carrier-lock check:** Settings → About phone → SIM status. If the phone is
> network/carrier-locked, the bootloader **cannot** be unlocked — stop.

### 4.4 Unlock the bootloader (WIPES THE DEVICE — back up first!)

```bash
# On the phone: enable Developer options + USB debugging + OEM unlocking.
adb reboot bootloader
fastboot oem get_unlock_data        # copy the whole string
#   Submit it at the Motorola bootloader-unlock portal; wait for the code.
fastboot oem unlock <YOUR_UNLOCK_CODE>
# Reboot, re-enable USB debugging, verify:
fastboot getvar unlocked            # -> unlocked: yes
```

### 4.5 Verify the Nuxel artifacts before flashing

```bash
cd /x/nuxel
# 1) Verify the downloaded archive against the release's SHA256SUMS.txt asset:
sha256sum -c SHA256SUMS.txt          # macOS: shasum -a 256 -c SHA256SUMS.txt
# 2) Unpack and verify each image against the archive's own per-file checksums:
tar -xzf nuxel-v0.3.1-alpha-g7power.tar.gz
cd g7power
sha256sum -c sha256sums.txt          # macOS: shasum -a 256 -c sha256sums.txt
python3 ../tools/read-boot-header-v1.py nuxel-ocean-boot.img
# expect: magic=ANDROID!, page_size=2048,
#         kernel=0x80008000, ramdisk=0x81000000, tags=0x80000100
```

Optionally sanity-check `lk2nd.img` is an Android boot image:

```bash
head -c 8 lk2nd.img          # -> ANDROID!
```

---

## 5. Backups — your undo button (do this before §6)

You need the **stock `boot` and `dtbo`** images for your unit. Without root, `dd`
from stock Android is blocked; get them from a booted **TWRP** (boot it
*transiently* — do **not** flash it) or from a stock firmware package.

### 5.1 Boot TWRP transiently (after unlock) and pull the stock images

```bash
# 1) Download a TWRP for ocean (slot-aware) to the host, e.g. twrp-ocean.img
# 2) Boot it WITHOUT flashing (writes nothing to /recovery):
fastboot boot twrp-ocean.img
# 3) In TWRP, adb is root:
adb devices

SLOT=$(adb shell getprop ro.boot.slot_suffix)      # e.g. _b
adb shell "dd if=/dev/block/bootdevice/by-name/boot${SLOT} of=/sdcard/stock-boot.img"
adb shell "dd if=/dev/block/bootdevice/by-name/dtbo${SLOT} of=/sdcard/stock-dtbo.img"

adb pull /sdcard/stock-boot.img .
adb pull /sdcard/stock-dtbo.img .
```

> **NEVER `dd`** `modemst*`, `fsg`, `fsc`, `ddr`, `persist`, `misc`. Only
> `boot_<slot>`, `dtbo_<slot>`, `recovery` are safe.

Keep `stock-boot.img` and `stock-dtbo.img` **forever** — they revert lk2nd and
Nuxel back to stock, and `stock-boot.img` also confirms the real load addresses.

### 5.2 Confirm the real load addresses (sanity, not fabrication)

```bash
python3 tools/read-boot-header-v1.py stock-boot.img
```

The values should match `docs/g7power-device-inventory.md`
(`0x80008000` / `0x81000000` / `0x80000100`). If they differ, **stop** and update
the inventory first — the build's load addresses come from that file.

---

## 6. The flash — two phases, exact order

Do §6.1 fully (including the reboot into lk2nd), **then** §6.2.

### 6.1 Phase 1 — stock ABOOT fastboot: `dtbo` first, then `lk2nd`

```bash
cd /x/nuxel

# Enter stock ABOOT fastboot: power off, then hold Vol Down + Power.
fastboot devices
fastboot getvar product            # MUST print: ocean  (else STOP)
fastboot getvar unlocked           # MUST print: yes    (else unlock first)

# STEP 1 — dtbo FIRST (mandatory; prevents the msm8953 soft-brick).
#          Use YOUR backed-up stock dtbo.
fastboot flash dtbo /path/to/stock-dtbo.img

# STEP 2 — lk2nd to the boot partition (still stock ABOOT).
fastboot flash boot build/out/g7power/lk2nd.img

# STEP 3 — reboot into lk2nd's fastboot.
fastboot reboot bootloader
# Wait ~10 s. `fastboot devices` should now list the phone again — this time
# it is lk2nd answering, not ABOOT.
```

Equivalent using the repo script (enforces the order, prompts before each write):

```bash
bash boot/g7power/flash.sh --device g7power \
    --dtbo  /path/to/stock-dtbo.img \
    --lk2nd build/out/g7power/lk2nd.img
# the script also reboots into lk2nd fastboot for you
```

### 6.2 Phase 2 — lk2nd fastboot: Nuxel kernel boot image + rootfs

You are now in **lk2nd fastboot** (`fastboot getvar product` may print `lk2nd`
or `ocean` depending on version — that is expected).

```bash
cd /x/nuxel

# STEP 4 — the Nuxel mainline boot image (kernel + initramfs + DTB).
fastboot flash boot build/out/g7power/nuxel-ocean-boot.img

# STEP 5 — the Nuxel rootfs to userdata (OVERWRITES your data).
fastboot flash userdata build/out/g7power/nuxel-ocean-rootfs.img

# STEP 6 — boot Nuxel.
fastboot reboot
```

Equivalent one-shot (after phase 1) using the script:

```bash
bash boot/g7power/flash.sh --device g7power \
    --boot   build/out/g7power/nuxel-ocean-boot.img \
    --rootfs build/out/g7power/nuxel-ocean-rootfs.img
```

> If `fastboot flash userdata` complains about the partition name, check
> `fastboot getvar all | grep -i userdata`; the shared partition is `userdata`
> (`/dev/block/bootdevice/by-name/userdata`, mmcblk0p64).

---

## 7. First boot — what to expect

1. The device resets; you should see the **lk2nd** splash briefly, then the
   Nuxel boot splash (RGB565 framebuffer) from the initramfs.
2. Watch the **serial console** (`console=ttyMSM0,115200`,
   `earlycon=msm_geni_serial,0xa88000`) if you have a UART/`picocom`,
   or run `fastboot oem console`/`adb` once userspace is up.
3. Root is `/dev/block/bootdevice/by-name/userdata` (ext4, `rw`).
4. **This is bring-up.** Display/touch/audio/modem/camera may not be fully
   working; the milestone was: mainline kernel boots, Nuxel initramfs runs,
   userspace mounts. If it drops to a shell, that is still a success.

If it **does not** boot, go straight to §9 (recovery/revert). Do not experiment
while the device is in an unknown state.

---

## 8. Quick reference — the exact command sequence

```bash
# After unlock + backups + artifact verification:

# --- Phase 1 (stock ABOOT fastboot: Vol Down + Power) ---
fastboot flash dtbo  /path/to/stock-dtbo.img
fastboot flash boot  build/out/g7power/lk2nd.img
fastboot reboot bootloader

# --- Phase 2 (lk2nd fastboot) ---
fastboot flash boot     build/out/g7power/nuxel-ocean-boot.img
fastboot flash userdata build/out/g7power/nuxel-ocean-rootfs.img
fastboot reboot
```

---

## 9. Recovery, revert & unbrick

### 9.1 Confirm the EDL safety net *before* flashing

```bash
# Power off. Hold Vol Down + Vol Up, plug USB.
# macOS:   system_profiler SPUSBDataType | grep -i -E 'qualcomm|9008'
# Linux:   lsusb | grep -i 05c6:9008
~/.venvs/edl/bin/edl --help        # bkerler/edl v3
```
If EDL does not enumerate, fix *that* before flashing anything.

### 9.2 Revert to stock (undo lk2nd + Nuxel)

```bash
# Enter stock ABOOT fastboot (Vol Down + Power), then:
fastboot flash dtbo /path/to/stock-dtbo.img
fastboot flash boot /path/to/stock-boot.img
fastboot reboot
```

Or via the script:

```bash
bash boot/g7power/flash.sh --device g7power --revert \
    --stock-dtbo /path/to/stock-dtbo.img \
    --stock-boot /path/to/stock-boot.img
```

### 9.3 Hard-brick / fastboot unreachable → EDL 9008

Power off, hold **Vol Down + Vol Up**, plug USB (host must see `05C6:9008`).
Use `edl` (Linux/macOS) or **QFIL** (Windows) to restore the stock partitions
from your stock firmware package. This restores `aboot`, `boot`, `dtbo`, etc.

> **Do not** write to `modemst*`, `fsg`, `fsc`, `ddr`, `persist`, `misc` from EDL
> either.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `fastboot devices` empty, phone off-screen | charge-only cable / hub / port | use a **data** cable + direct port (§4.1) |
| `fastboot getvar product` ≠ `ocean` | wrong device connected | connect the G7 Power, or `NUXEL_EXPECTED_SERIAL` to pin a unit |
| `fastboot flash boot lk2nd.img` refused | bootloader **locked** | unlock (§4.4) |
| Phone bootloops / black after lk2nd flash | **dtbo not valid / flashed after boot** | enter ABOOT fastboot, `fastboot flash dtbo stock-dtbo.img`, reflash `boot` (§9.2) |
| `fastboot` works in ABOOT but not after `reboot bootloader` | lk2nd did not come up | revert stock boot (§9.2); check you flashed the right `lk2nd.img` |
| Rootfs flash fails / partition not found | wrong partition name | `fastboot getvar all | grep -i userdata` → use `userdata` |
| No display after Nuxel boot but device responds | Phase-1 bring-up, display not up | keep serial console; it is expected to be incomplete |
| Nothing works, no fastboot at all | soft/hard brick | **EDL 9008** (§9.3) |

---

## 11. Appendix

### 11.1 Artifact → partition map

| Artifact | Partition | Phase | Tool |
|---|---|---|---|
| `stock-dtbo.img` (your backup) | `dtbo` | 1 (stock ABOOT) | `fastboot` |
| `lk2nd.img` | `boot` | 1 (stock ABOOT) | `fastboot` |
| `nuxel-ocean-boot.img` | `boot` | 2 (lk2nd) | `fastboot` |
| `nuxel-ocean-rootfs.img` | `userdata` | 2 (lk2nd) | `fastboot` |

### 11.2 Load addresses (from `docs/g7power-device-inventory.md`)

```
KERNEL_ADDR  = 0x80008000
RAMDISK_ADDR = 0x81000000
TAGS_ADDR    = 0x80000100
page_size    = 2048
```

### 11.3 Where the artifacts come from

The GitHub **Release** workflow (`.github/workflows/release.yml`) builds, on a
clean Ubuntu runner, for `g7power`:

1. the shared initramfs (`images/build.sh --initramfs-only`),
2. the mainline kernel `Image.gz` + `sdm632-motorola-ocean.dtb` + modules
   (`kernel/g7power/build-kernel.sh --clone`),
3. `lk2nd.img` (`boot/g7power/lk2nd/build-lk2nd.sh`),
4. the boot + rootfs images (`images/g7power/build.sh`),

then **verifies** them (`tools/verify-artifacts.sh`) and only then packages
`nuxel-v0.3.1-alpha-g7power.tar.gz`. A missing or invalid artifact makes the run **red**
and no release is published.

---

*Build the bunker first. Add the rave lights later. — Nuxel v0.3.1-alpha*
