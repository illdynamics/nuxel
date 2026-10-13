# Nuxel — Samsung Galaxy S10+ manual flash guide

**Device:** Samsung Galaxy S10+ **SM-G975F** (Exynos 9820, codename `beyond2lte`)
**Nuxel:** `v0.3.0-alpha` · **Guide written:** 2026-10-13
**Authoritative repo docs:** this file is the "do it now" checklist. Background:
`phones/s10plus/s10plus-go-guide.md`, `docs/s10plus-bringup.md`,
`docs/s10plus-device-inventory.md`.

> ⚠️ **Read §2 (safety) and §5 (backups) before you flash anything.**
> On this device there is **no fastboot, ever** — it is Exynos. You flash with
> **heimdall in Download Mode** (primary, proven path) or **TWRP `dd`**
> (alternative). Download Mode is always reachable, so a bad `boot` image
> cannot hard-brick you **as long as you never touch the protected partitions
> and never re-lock the bootloader**.

---

## 0. TL;DR — the shortest safe path

1. **Back up stock `boot` + `dtbo`** from TWRP (your undo button). → §5
2. **Verify the Nuxel artifacts** (hashes + header). → §4.4
3. **Download Mode** (Vol Down + Bixby + Power) → flash `BOOT` (and the rootfs to
   `userdata`) with heimdall. → §6
4. Reboot and watch. → §7
5. Anything wrong? Download Mode is always reachable → **re-flash your stock
   `boot.img`**. → §9

The one command that actually flashes Nuxel (Phase 1):

```bash
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img
```

---

## 1. What you are flashing (artifact inventory)

`v0.3.0-alpha` is built **by the GitHub release workflow** (Actions → “Release”,
tag `v0.3.0-alpha`). The S10+ archive is:

```
nuxel-v0.3.0-alpha-s10plus.tar.gz
```

Extract it to get `s10plus/`:

| File | What it is | Flashes to |
|---|---|---|
| `s10plus/nuxel-beyond2lte-boot.img` | downstream Samsung **Linux 4.14.253** kernel `Image.gz` + Nuxel initramfs + **merged board DTB** (`exynos9820.dtb` + `exynos9820-beyond2lte_eur_open_<rev>.dtbo`), packed as an Android **boot header v1** (page 2048, `ANDROID!`) | `BOOT` |
| `s10plus/nuxel-beyond2lte-rootfs.img` | Nuxel userspace, plain **ext4**, writable (Phase 1, no dm-verity/AVB) | `SYSTEM` (proven) or `userdata` |
| `s10plus/build-manifest.json` | device key, kernel commit, DTB used, load addresses, timestamps | — |
| `s10plus/sha256sums.txt` | per-file checksums you verify before flashing | — |

Boot image facts (Android boot header v1, page 2048):

```
kernel  load addr : 0x10008000
ramdisk load addr : 0x11000000
tags    load addr : 0x10000100
```

**The DTB is embedded in the boot image.** CI now merges the SoC base DTB with
the highest board-revision overlay into a single `exynos9820-beyond2lte.dtb`
before packing, because the downstream Samsung tree only ships the base
`exynos9820.dtb` + separate `.dtbo` overlays. You therefore only ever flash the
one `nuxel-beyond2lte-boot.img` — there is no separate `-merged.img` in the
release.

> **What this gets you:** the real downstream Samsung kernel boots on the real
> S10+ hardware, the Nuxel initramfs runs, and rootfs mounts from the flashed
> partition. "Built and hash-verified by CI" is **not** "boots on your unit" —
> §7 is the actual test.

The S10+ is **A-only** (no A/B slots). The UFS partition path is
`/dev/block/platform/13d60000.ufs/by-name`.

---

## 2. Safety — read this twice

**Protected partitions — NEVER flash / `dd` / wipe these.** They hold IMEI, MAC,
calibration and Knox data — **irreplaceable**:

```
efs  efsg  persist  param  up_param  steady  keystorage  carrier  cp_debug  misc
```

1. **No fastboot.** `heimdall` (Download Mode) or TWRP `dd` only. Ignore every
   "fastboot flash …" instruction you find online for this phone.
2. **Never wipe or overwrite `dtbo`** — S-Boot needs it to bring up the board.
3. **Never re-lock the bootloader and never attempt a Knox restore.** The Knox
   fuse is already tripped; relock ("ODIN LOCK") can hard-brick the phone.
4. **Download Mode is your safety net.** It is independent of whatever is on
   `boot`, so a bad boot image is recoverable — confirm it works *before* your
   first flash.
5. **Have backups:** stock `boot` + `dtbo` (§5), plus the full **SM-G975F
   BL/AP/CP/CSC** firmware package for your region + bootloader revision (§5.4).
6. **A real USB *data* cable** + a direct port (no hub). Charge-only cables look
   exactly like "Download Mode not detected".
7. **Battery > 60%.**
8. Device identity is verified before every flash: `ro.product.device` must be
   **`beyond2lte`** and the model must be **SM-G975F (Exynos)** — the scripts
   refuse a Snapdragon `SM-G975U`/`g975u`.

---

## 3. Modes — which button combo, and when

| Mode | How to enter | Host sees it as | Used for |
|---|---|---|---|
| **Download Mode** (Odin mode) | Power off (hold Power ~10 s). Hold **Vol Down + Bixby + Power** until the warning screen, release, press **Vol Up**. | `heimdall detect` → “Device detected”; `lsusb` shows `04e8:…` | **heimdall flashing** (flash Nuxel, and revert) |
| **TWRP recovery** | Power off. Hold **Vol Up + Bixby + Power** until the TWRP logo. | `adb devices` lists it | Backups (pull stock `boot`/`dtbo`), `adb push` + `dd` flashing, sideload |
| **Normal / Android** | Power. | `adb devices` (if USB debugging is on) | not used here |

Confirm from the host:

```bash
adb devices            # lists the phone in TWRP; nothing in Download Mode
heimdall detect        # lists the phone in Download Mode; nothing in TWRP
heimdall version       # MUST print vX.Y.Z — NOT the heimdall-rs crypto tool
```

> ⚠️ **heimdall gotcha:** a *different* program also called `heimdall` exists
> (`heimdall-rs`, an Ethereum tool, often installed via cargo). If
> `heimdall version` doesn't print a version like `v2.2.2`, you have the wrong
> tool. Install the real one: `apt install heimdall-flash` (Linux) or
> `brew install heimdall` (macOS).

---

## 4. Prerequisites

### 4.1 Hardware
- Samsung Galaxy S10+ **SM-G975F** (Exynos) — a **spare** unit; flashing wipes data.
  (A Snapdragon US `SM-G975U` is a *different* device; the scripts refuse it.)
- Bootloader **already unlocked** and **TWRP already installed** (Knox fuse
  already tripped — leave it that way).
- A **USB-C data cable** + a direct USB port.
- Battery **> 60%**.

### 4.2 Host tools
- `heimdall` (the real Samsung tool; `heimdall version` → `vX.Y.Z`)
- `adb` (`adb version`)
- `python3` (for `tools/read-boot-header-v1.py`)
- Optional (Windows): **Odin** for a full stock restore.

### 4.3 Only you can provide
- **Your unit's stock `boot.img` and `dtbo.img`** — pulled in §5 (your revert).
- **The SM-G975F BL/AP/CP/CSC firmware package** matching your region and
  bootloader revision (recovery insurance; §5.4).
- Your unit's **`hw_rev`** (`getprop ro.revision`) — selects which board DTBO
  S-Boot applies at boot.

### 4.4 Verify the Nuxel artifacts before flashing

```bash
cd /x/nuxel
# 1) Verify the downloaded archive against the release's SHA256SUMS.txt asset:
sha256sum -c SHA256SUMS.txt          # macOS: shasum -a 256 -c SHA256SUMS.txt
# 2) Unpack and verify each image against the archive's own per-file checksums:
tar -xzf nuxel-v0.3.0-alpha-s10plus.tar.gz
cd s10plus
sha256sum -c sha256sums.txt          # macOS: shasum -a 256 -c sha256sums.txt
python3 ../tools/read-boot-header-v1.py nuxel-beyond2lte-boot.img
# expect: magic=ANDROID!, page_size=2048,
#         kernel=0x10008000, ramdisk=0x11000000, tags=0x10000100, name=nuxel-s10plus
```

---

## 5. Step 1 — TWRP: back up stock and confirm the device

### 5.1 Enter TWRP
Power off (hold Power ~10 s), then hold **Vol Up + Bixby + Power** until TWRP
appears. Confirm the host sees it and it is *your* device:

```bash
adb devices
adb shell getprop ro.product.device    # MUST print: beyond2lte
adb shell getprop ro.product.name      # e.g. beyond2ltexx  (save this)
adb shell getprop ro.product.model     # MUST be SM-G975F (Exynos), NOT SM-G975U
adb shell getprop ro.bootloader        # save the bootloader revision
adb shell getprop ro.revision          # this is your hw_rev (DTBO selection)
```

### 5.2 Back up stock partitions (YOUR REVERT — do this first)

```bash
mkdir -p ~/s10plus-backup
adb shell "mkdir -p /sdcard/nuxel-backup"
for p in boot dtbo recovery; do
  adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/$p of=/sdcard/nuxel-backup/$p.img bs=4096" && echo "$p ok"
done
# Read-only copies of calibration (keep, but NEVER restore onto another unit):
for p in efs efsg persist param up_param steady keystorage; do
  adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/$p of=/sdcard/nuxel-backup/$p.img bs=4096 2>/dev/null" || true
done
adb pull /sdcard/nuxel-backup ~/s10plus-backup/
ls -la ~/s10plus-backup/nuxel-backup
```

**Keep `boot.img` and `dtbo.img`. They are how you go back to stock.**

### 5.3 Confirm the boot load addresses from YOUR stock `boot.img`

```bash
python3 tools/read-boot-header-v1.py ~/s10plus-backup/nuxel-backup/boot.img
```

Expect `page_size=2048`, `kernel≈0x10008000`, `ramdisk≈0x11000000`,
`tags≈0x10000100`. If your unit differs, the prebuilt image's header won't match
your bootloader — update `docs/s10plus-device-inventory.md`, then **re-run the
build** (the script refuses to pack with unverified override addresses). The
repo values come from the pmOS S10 deviceinfo and should be correct for the
SM-G975F, but confirm on your unit.

### 5.4 Get stock firmware (recovery insurance)

Download the SM-G975F **BL / AP / CP / CSC** package for your exact region +
bootloader revision (e.g. samfw.com / sammobile.com). Keep it forever — you only
need it if something goes badly wrong (§9).

---

## 6. Step 2 — Download Mode: flash Nuxel with heimdall

### 6.1 Enter Download Mode
Power off (hold Power ~10 s until black), then hold **Vol Down + Bixby + Power**
until the warning screen → release → press **Vol Up** to continue.

### 6.2 Confirm heimdall sees it
```bash
heimdall detect
# expect: "Device detected"
```
Nothing? Re-enter Download Mode, try a different **data** cable/port.

### 6.3 Flash — the proven path (BOOT only, Phase 1)
```bash
cd /x/nuxel

# Dry-run preview (repo wrapper: prints the exact command, flashes nothing):
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
    --boot build/out/s10plus/nuxel-beyond2lte-boot.img --dry-run

# REAL FLASH (minimal, proven command):
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img
```

heimdall reboots the device automatically at the end. **Watch the screen.**

### 6.4 Flash BOOT + rootfs together (Phase 2)

The rootfs now ships in the release archive. **Critical:** the rootfs must land
on the same partition the kernel roots from. The shipped boot image's cmdline is:

```
buildvariant=userdebug nuxel.device=s10plus \
root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw
```

so the rootfs must be flashed to **`userdata`** (heimdall name `USERDATA`).
`heimdall flash` takes BOOT and the rootfs in a single Download-Mode session:

```bash
heimdall detect     # still in Download Mode

NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
    --boot   build/out/s10plus/nuxel-beyond2lte-boot.img \
    --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img \
    --partition-rootfs USERDATA
```

Or the raw equivalent:

```bash
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img \
               --USERDATA build/out/s10plus/nuxel-beyond2lte-rootfs.img
```

> ⚠️ **Do not mismatch.** `boot/s10plus/flash-heimdall.sh` defaults
> `--partition-rootfs` to `SYSTEM`; that only works if the boot image's cmdline
> roots from `system` as well. The shipped image roots from **`userdata`**, so
> either pass `--partition-rootfs USERDATA` (as above) **or** flash to `userdata`
> with the TWRP `dd` path in §6.5. If you deliberately want the rootfs on
> `SYSTEM`, re-pack the boot image with
> `root=/dev/block/platform/13d60000.ufs/by-name/system`.

### 6.5 Alternative — rootfs via TWRP `dd` (no heimdall)
```bash
# In TWRP (Vol Up + Bixby + Power):
adb push build/out/s10plus/nuxel-beyond2lte-rootfs.img /tmp/nuxel-rootfs.img
adb shell "dd if=/tmp/nuxel-rootfs.img of=/dev/block/platform/13d60000.ufs/by-name/userdata bs=4096"
adb shell sync
```
Full repo helper (identity check + protected-partition denylist):
`NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh --device s10plus --rootfs <rootfs.img>`.

> If heimdall rejects a **sparse** image, use the TWRP `dd` path above (the CI
> rootfs is a plain ext4 image, not sparse, so this normally does not apply).

---

## 7. Step 3 — Test the boot

Expected sequence on the S10+:
1. Samsung splash (S-Boot) runs and applies the board DTBO from the `dtbo`
   partition over the embedded base DTB.
2. The Nuxel downstream 4.14 kernel starts; the **Nuxel initramfs** runs `init`,
   sets up `/proc /sys /dev`, resolves the S10+ UFS root, and mounts the Nuxel
   rootfs from the flashed partition.

Read the result honestly:

| What you see | Meaning |
|---|---|
| Nuxel splash / kernel boot + userspace comes up | ✅ **bring-up success** — real Nuxel kernel on real S10+ hardware |
| Kernel boots, black screen, device alive on USB/serial | ✅ kernel boot success; the panel/DSI path (DTBO `hw_rev`) is the remaining display bring-up |
| Samsung splash → nothing / reboot loop | ✗ boot header/addresses or DTB mismatch → revert (§9) and recheck §5.3 |
| Nothing at all, but the phone enumerates in Download Mode | keep going — **Download Mode is always reachable**, revert or reflash |

If you have a serial console (`console=ttySAC0,115200`) or a shell:
```sh
cat /proc/device-tree/compatible
ls /sys/class/drm ; ls /sys/class/net
dmesg | tail -50
```

> **WiFi/modem/camera** need the vendor firmware blobs at `/lib/firmware` +
> `/etc/wifi`. CI **does not** ship those blobs (they are device-dumped, not
> redistributable — `firmware/s10plus/blobs/` is a placeholder in the repo), so a
> CI-built rootfs boots but has no WiFi/modem until you add your own blobs
> (see §9.4).

---

## 8. Quick reference — the exact command sequence

```bash
# --- Backups (TWRP: Vol Up + Bixby + Power) ---
adb shell getprop ro.product.device        # beyond2lte
adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/boot of=/sdcard/nuxel-backup/boot.img bs=4096"
adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/dtbo of=/sdcard/nuxel-backup/dtbo.img bs=4096"
adb pull /sdcard/nuxel-backup ~/s10plus-backup/

# --- Flash (Download Mode: Vol Down + Bixby + Power) ---
heimdall detect
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img

# --- Revert (Download Mode) ---
heimdall flash --BOOT ~/s10plus-backup/nuxel-backup/boot.img
```

---

## 9. Revert & unbrick

Download Mode is always reachable, regardless of what is on `boot`.

### 9.1 Revert just the boot partition (fast)
```bash
# Enter Download Mode, then:
heimdall flash --BOOT ~/s10plus-backup/nuxel-backup/boot.img
# or via the wrapper:
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh --device s10plus \
    --revert --stock-boot ~/s10plus-backup/nuxel-backup/boot.img
```

### 9.2 Full stock restore (guaranteed)
Download Mode + your SM-G975F Odin package:
```bash
heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5
```
Use only **your** region/revision package. On Windows the equivalent is Odin.

### 9.3 Re-flash TWRP (if you lose it)
TWRP → Advanced → ADB Sideload → swipe → `adb sideload twrp-beyond2lte.zip`.

### 9.4 Add your vendor firmware blobs to the rootfs (WiFi/modem/camera)
```bash
# On the host, with the device in TWRP (blobs are pulled from your unit):
bash firmware/s10plus/fetch-vendor-blobs.sh
python3 firmware/s10plus/gen-manifest.py
# Re-run the S10+ image build so the blobs land in the rootfs:
NUXEL_DEVICE=s10plus bash images/s10plus/build.sh --device s10plus
# Then re-flash the rootfs (§6.4/§6.5).
```

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `heimdall detect` finds nothing (in Download Mode) | charge-only cable / wrong port / not fully in Download Mode | re-enter Download Mode; data cable; different port |
| `heimdall` does EVM/blockchain things | you ran `heimdall-rs`, not the Samsung tool | use the real tool (`heimdall version` → `vX.Y.Z`) |
| `adb getprop ro.product.device` ≠ `beyond2lte` | wrong device (e.g. Snapdragon S10+) | stop; this guide is SM-G975F (Exynos) only |
| Flash "succeeds", then Samsung splash + restart | wrong load addresses or DTB not applied | recheck §5.3 from your stock boot.img; confirm `hw_rev`; the embedded merged DTB matches the highest board rev |
| No display, but device alive/enumerates | panel/DSI or DTBO `hw_rev` mismatch | confirm `hw_rev` (`ro.revision`); note S-Boot still applies the `dtbo` partition at boot |
| No WiFi/modem after boot | vendor firmware blobs absent from the rootfs (expected for a CI build) | add your blobs and rebuild the rootfs (§9.4) |
| `heimdall` "Protocol initialisation failed" | flaky cable/port, device not settled | re-enter Download Mode, re-plug, retry; try another cable/port |
| Device won't boot at all | — | Download Mode is always reachable → §9 |

---

## 11. Appendix

### 11.1 Artifact → partition map

| Artifact | Partition | Tool |
|---|---|---|
| `nuxel-beyond2lte-boot.img` | `BOOT` | `heimdall` (Download Mode) |
| `nuxel-beyond2lte-rootfs.img` | `USERDATA`/`userdata` (matches the boot cmdline) | `heimdall` or TWRP `dd` |
| your backed-up `boot.img` (stock) | `BOOT` | `heimdall` (revert) |

Never touch: `efs efsg persist param up_param steady keystorage carrier cp_debug misc`,
and never overwrite `dtbo`.

### 11.2 Addresses & identity

```
KERNEL_ADDR  = 0x10008000
RAMDISK_ADDR = 0x11000000
TAGS_ADDR    = 0x10000100
page_size    = 2048
soc          = Exynos 9820 (kernel: downstream Linux 4.14.253)
UFS by-name  = /dev/block/platform/13d60000.ufs/by-name
```

### 11.3 Where the artifacts come from

The GitHub **Release** workflow (`.github/workflows/release.yml`) builds, on a
clean Ubuntu runner, for `s10plus`:

1. the shared initramfs (`images/build.sh --initramfs-only`),
2. the downstream Samsung 4.14 kernel `Image.gz` + DTBs
   (`kernel/s10plus/build-kernel.sh --clone`),
3. the boot + rootfs images (`images/s10plus/build.sh`; the script merges the
   base DTB + highest-rev board DTBO into `exynos9820-beyond2lte.dtb` first),

then **verifies** them (`tools/verify-artifacts.sh`) and only then packages
`nuxel-v0.3.0-alpha-s10plus.tar.gz`. A missing or invalid artifact makes the run **red**
and no release is published.

### 11.4 Command cheat-sheet

```bash
# Modes (power off first)
#   Download Mode : Vol Down + Bixby + Power (hold to warning, then Vol Up)
#   TWRP          : Vol Up   + Bixby + Power (hold to TWRP logo)

# Identity (TWRP)
adb shell getprop ro.product.device     # beyond2lte
adb shell getprop ro.product.model      # SM-G975F
adb shell getprop ro.revision           # hw_rev

# Verify (host)
sha256sum build/out/s10plus/nuxel-beyond2lte-boot.img
python3 tools/read-boot-header-v1.py build/out/s10plus/nuxel-beyond2lte-boot.img

# Flash / revert (Download Mode)
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img
heimdall flash --BOOT ~/s10plus-backup/nuxel-backup/boot.img
```

---

*Build the bunker first. Add the rave lights later. — Nuxel v0.3.0-alpha*
