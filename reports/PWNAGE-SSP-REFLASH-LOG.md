# PWNAGE-SSP — Reflash Log

All times are local (Europe/Amsterdam), 2026-11-13. Device serial
`R58M75KDB2X`. Only the **boot** partition (`/dev/block/sda14`, GPT label
`boot`) was ever written. EFS, modem/radio, recovery, bootloader, PIT,
userdata, vendor and every other partition were never opened for write.

---

## 0. Pre-flight (device + recovery)

| Check | Result |
|---|---|
| `adb devices -l` | `R58M75KDB2X  recovery  product:omni_beyond2lte  model:Galaxy_S10_  device:beyond2lte` |
| `ro.product.device` | `beyond2lte` |
| `ro.product.model` | `Galaxy S10+` |
| `/sys/devices/soc0/machine` | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` |
| `/dev/block/by-name/boot` | symlink → `/dev/block/sda14` (UFS `13d60000.ufs`) |
| `blockdev --getsize64 boot` | 57 671 680 bytes |
| Boot partition magic | `ANDROID!` v1 header, `nuxel-s10plus` board, Nuxel cmdline (`nuxel.device=s10plus`) |
| Kernel in the live boot image | `Linux version 4.14.253-gf7194c1d15ed-dirty … #30 … Nov 12 22:45:17 2026`, i.e. the tree's own build (`Image` sha 593949ce…) |

## 1. Original-boot backup (BEFORE any change)

```
adb shell dd if=/dev/block/by-name/boot of=/tmp/boot-orig.img bs=1M
adb pull /tmp/boot-orig.img backups/boot/boot-orig-20261113.img
```

| File | Size | SHA256 |
|---|---|---|
| `backups/boot/boot-orig-20261113.img` | 57 671 680 | `7ca7cc70c1ab78ebd1882455ec6aaa9da9d5b766cbee01835ca7b8a20359abf8` |

The pulled copy's SHA256 was recomputed on the workstation and matched the
on-device checksum exactly. This file is never overwritten and is the rollback
target for every attempt in this log.

## 2. Pre-existing known-good images (were already on the workstation)

`build/backup/sda14-known-good-20261101.img` and the p111000 NFC candidates
remain untouched.

---

## 3. Attempt 1 — combined kernel `#31` (SSP + userns + nftables)

### 3.1 What changed in the image

| Change | Detail |
|---|---|
| `CONFIG_NF_TABLES` family | added to `kernel/s10plus/configs/nuxel-drm-kbase.fragment` (nf_tables, inet/ipv4/ipv6/netdev, NFT_{CT,NAT,MASQ,REJECT,REDIR,QUEUE,QUOTA,LOG,LIMIT,COMPAT,SET_*,FIB*}, CGROUP_NET_CLASSID, XT match cgroup/socket/pktttype) |
| `CONFIG_USER_NS` behaviour | the retired `0008-nuxel-userns-flatpak.patch` (which replaced the upstream `current_chrooted()` check with an unconditional `ret = -EPERM;`) is replaced by a patch that keeps the upstream chroot + LOD_SEC checks and adds the standard `kernel.unprivileged_userns_clone` sysctl (default 0) |
| New kernel gate | `tools/s10plus/verify-kernel-userns.py`, called from `kernel/s10plus/build-kernel.sh` before `Image.gz` is built |
| Sensors | nothing in the kernel was changed for SSP — the driver was already complete; the blocker is hardware/state (see `PWNAGE-SSP-HARDWARE-MAP.md` §4) |

All previously required patches were still applied (`0003`, `0004`, `0005`,
`0006-sec-ts-lpm-bind`, `0007 NFC` ×2, `0008-mfc-firmware`, `0009`, `0010`,
`0011`). `verify-kernel-config.py` (live capability parity) and
`verify-kernel-nfc.py` / `verify-kernel-usbnet.py` all passed in the same build.

### 3.2 Build

```
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh
→ build/out/s10plus/ssp/build/kernel-build-1.log   (RC=0)
```

| Output | Size | SHA256 |
|---|---|---|
| `kernel/s10plus/.build/out/arch/arm64/boot/Image` | 45 781 000 | `cd4827cb9d92bc2a49f0d544109fe78b817afd344f7cfd7f0e2514fefcfd136d` |
| `…/Image.gz` | 16 400 570 | (not used for flashing: S-Boot executes the raw Image) |

Gate lines from the log:

```
userns gate: PASS — USER_NS + namespace set + nftables are built in,
  create_user_ns() keeps the upstream chroot check, and the
  unprivileged_userns_clone / max_user_namespaces knobs exist
kernel config: PASS — matches the live S10+ capability set
```

### 3.3 Image assembly

`tools/s10plus/pack-ssp-boot.py` measures the donor layout instead of
assuming it (after an earlier attempt mis-derived the page rule):

```
header_bytes       2048
kernel_offset      2048
kernel_size        45781000
ramdisk_offset     45785088
ramdisk_size       2424832      (LZMA-alone, copied byte-for-byte from the donor)
dtb_offset         48209920
dtb_region_size    6584320      (DTB + hash block tail, copied byte-for-byte)
kernel_addr        0x10008000
ramdisk_addr       0x11000000
```

Image padded back to the partition size so the `dd` writes a fixed length.

| File | Size | SHA256 |
|---|---|---|
| `build/out/s10plus/ssp/images/boot-ssp-v1.img` | 57 671 680 | `2c53313fc84c54b3cc4c20c973a22e1d28a2580dfaacb9c4ac871122aadd71b3` |

Gate: `verify-boot-image.py` → **PASS** (header_field40=1, raw arm64 Image,
LZMA ramdisk decodes to 8 791 372 bytes / 84 cpio records / `/init` present,
appended DTB has `sec-nfc@27` intact, partition slack 0).

### 3.4 Flash

| Step | Result |
|---|---|
| Device identity re-checked (model/boot partition/size) | PASS |
| `adb push boot-ssp-v1.img /tmp/` → on-device `sha256sum` | `2c53313f…aadd71b3` (matches) |
| Read current boot → `/tmp/boot-before-v1.img` | `7ca7cc70…20359abf8` (matches the backup) |
| `dd if=/tmp/boot-ssp-v1.img of=/dev/block/by-name/boot bs=1M conv=fsync` | 57 671 680 bytes copied, 0 errors |
| Readback `dd if=/dev/block/by-name/boot of=/tmp/boot-readback-v1.img` → sha256 | `2c53313f…aadd71b3` — identical |
| `adb reboot` | issued |

### 3.5 Result — **PASS (booted Nuxel)**

~45 s after reboot:

```
adb devices -l          → empty (not TWRP)
ping 192.168.178.167    → 2/2 packets
ssh root@192.168.178.167:
  Linux 4.14.253-gf7194c1d15ed-dirty #31 SMP PREEMPT Fri Nov 13 09:27:28 CET 2026 aarch64
  systemctl is-system-running → starting (later: services listed running)
  zcat /proc/config.gz | grep CONFIG_NF_TABLES= → CONFIG_NF_TABLES=y
  cat /proc/sys/kernel/unprivileged_userns_clone → 0
```

The phone did **not** return to TWRP. It booted the Nuxel Fedora userspace,
reached `nuxel-wayland`, `nuxel-orientationd`, `nuxel-bridge` etc.

### 3.6 Follow-ups during this boot (no reflash)

- `dnf -y install nftables` (userspace binary only; kernel support was already
  in image v1). `nft --version` → `nftables v1.1.3`.
- `nft add table/chain` succeeded. The `mark` expression was not built
  (`CONFIG_NF_TABLES` set but `nft mark`/`meta mark` needs `NFT_META`), so a
  follow-up image should add `CONFIG_NFT_META`, `CONFIG_CGROUP_NET_CLASSID`
  userspace path and validate the console guard; see
  `PWNAGE-SSP-REPORT.md` §5.
- `sysctl -w kernel.unprivileged_userns_clone=1` then `unshare -Ur true` as
  `nuxel` still fails with `No space left on device` (ENOSPC). The compile-time
  and source-level cause of the *previous* total failure is fixed, but the
  runtime path still refuses. `user.max_user_namespaces = 27227`,
  `/proc/self/uid_map` maps 0→0, and the cgroup-v2 hierarchy is writable, so
  this needs a deeper kernel runtime investigation and is reported
  **PARTIAL**, not PASS. It is NOT claimed as working.

---

## 4. Sensor work after boot (no reflash — diagnostics only)

| Action | Result |
|---|---|
| `cat /sys/class/sensors/ssp_sensor/{mcu_name,mcu_rev}` | `BCM47752KUB1G`, `BR0121080900,BR010` (MCU answers SPI) |
| `cat .../accelerometer_sensor/raw_data` | `0,0,0` |
| `printf "ESW:READY" > /dev/bbd_control` | kernel runs `bbd_mcu_ready_work_func`; `Sensors of MCU are not ready!`; `get_chipid` timeout; `initialize_mcu - MCU is not working : 0xffffffff` |
| `tools/s10plus/ssp-probe.c` built static aarch64 and run as BBD peer | sees every kernel→MCU `whoami` (`09 00 0f 01 00 00 00 00 00 00 00`), kernel still times out waiting for a reply |
| `open("/dev/ttyBCM")` register probe | all MISO reads `0xFF`; HSI registers readable (see hardware map §4) |
| `echo 0/1 > mcu_power` power-cycle (rail) | rail toggles; `mcu_name` still read at probe time, but post-boot register reads stay `0xFF` and the `whoami` handshake times out |
| `GPS_PWR_EN` (gpio145) forced high | no change |

No partition was written during any of these diagnostics.

---

## 5. Rollback

To return to the exact pre-mission state:

```
adb push backups/boot/boot-orig-20261113.img /tmp/boot-orig.img   # from TWRP
adb shell 'dd if=/tmp/boot-orig.img of=/dev/block/by-name/boot bs=1M conv=fsync'
```

Expected readback: `7ca7cc70…20359abf8`. Or use the existing
`boot/s10plus/flash.sh --revert` path (heimdall, BOOT only) with
`backups/boot/boot-orig-20261113.img`.

## 6. Attempt ledger

| # | Image SHA256 | Result | Failure cause | Evidence |
|---|---|---|---|---|
| 1 | `2c53313f…aadd71b3` (kernel `#31`) | **PASS** — Nuxel boots, SSH up, nftables + userns sysctl present | (sensors PARTIAL — hub firmware/reply path not usable; see hardware map §4) | `build/out/s10plus/ssp/evidence/` |

---

## 7. Attempt 2 — kernel `#33` with native sensor-hub bring-up (PWNAGE-SSP patch 0013)

### 7.1 Why
After attempt 1 the hub answered its probe-time chip-ID but `bSspShutdown` stayed true and
only the Android `lhd` daemon could clear it. The new patch (see `PWNAGE-SSP-REPORT.md` §2)
adds a kernel-owned bring-up, explicit IRQ ownership, gyro raw sysfs and diagnostics.

### 7.2 Build + image (2026-11-13 ~10:43)
```
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh
→ build/out/s10plus/ssp/build/kernel-build-5.log  (RC=0)
→ kernel config: PASS — matches the live S10+ capability set
→ userns gate: PASS
```

| Output | Size | SHA256 |
|---|---:|---|
| `kernel/s10plus/.build/out/arch/arm64/boot/Image` | 45 783 048 | `63e39e0cd762bbcf437e5d199b82f7fe880ddbc22eefbd46db68834641e830ee` |
| `build/out/s10plus/ssp/images/boot-ssp-v3.img` | 57 671 680 | `cbcc4335743a1307c0da20e1cd701ce4956398e6ac64d817c94e5eb08045b72e` |

`verify-boot-image.py` → **PASS** (header v1, raw arm64 Image, LZMA ramdisk, 84 cpio records,
`/init`, `sec-nfc@27`, partition slack 0).

### 7.3 Flash — **NOT PERFORMED**

| Pre-flight check | Result |
|---|---|
| `adb devices -l` | **empty** — no TWRP/ADB device attached |
| USB enumeration | only "Samsung USB C Earphones"; no adb interface |
| SSH to `192.168.178.167` | reachable (Nuxel `#32`, boot_id `1d7ca91d…`) |
| Device identity/boot partition/backup | NOT re-verified for this attempt (requires TWRP) |

The mission policy requires device identity, TWRP access, boot-partition verification and
pre-flash backup/readback before every write. With no ADB device none of these could be
performed, so **no partition was written** and no reflash count was consumed.

### 7.4 Exact flash procedure to run when TWRP is attached

```
adb devices -l                                  # must show R58M75KDB2X recovery
adb shell 'getprop ro.product.device'           # beyond2lte
adb shell 'readlink -f /dev/block/by-name/boot' # /dev/block/sda14
adb shell 'dd if=/dev/block/by-name/boot of=/tmp/boot-pre-v3.img bs=1M'
adb pull /tmp/boot-pre-v3.img backups/boot/boot-pre-v3-<ts>.img
sha256sum backups/boot/boot-pre-v3-<ts>.img     # must equal current/known-good
adb push build/out/s10plus/ssp/images/boot-ssp-v3.img /tmp/
adb shell 'sha256sum /tmp/boot-ssp-v3.img'      # cbcc4335…45b72e
adb shell 'dd if=/tmp/boot-ssp-v3.img of=/dev/block/by-name/boot bs=1M conv=fsync'
adb shell 'dd if=/dev/block/by-name/boot of=/tmp/boot-readback-v3.img bs=1M'
adb shell 'sha256sum /tmp/boot-readback-v3.img' # must equal cbcc4335…45b72e
adb reboot
```
Then: TWRP window = boot failure; SSH/Nuxel = success. Capture `dmesg | grep SSPBBD` first.

### 7.5 Attempt ledger (updated)

| # | Image SHA256 | Flash | Result |
|---|---|---|---|
| 1 | `2c53313f…aadd71b3` (kernel #31) | PASS (boot only) | Nuxel booted; sensors PARTIAL |
| 2 | `cbcc4335…45b72e` (kernel #33, SSP bring-up) | **NOT FLASHED — no TWRP** | Pending operator reconnection |

---

## 8. Attempt ledger — continuation run (2026-11-13, 10:57 → 13:00 CET)

All writes: TWRP, identity `beyond2lte`, boot = `/dev/block/sda14` (57 671 680 B),
pre-flash backup pulled to `backups/boot/`, image hash checked on-device, write,
readback hash compared.  Boot partition only.

| # | Image | SHA256 | Kernel | Boot result | Notes |
|---|---|---|---|---|---|
| 3 | boot-ssp-v4 | `d2b2308504f28bdb9d2e311320948b1c6d60c28fb16d98619a29f5f16b38f33c` | #35 | **PASS** | first image with `nuxel_ssp_data` registration |
| 4 | boot-ssp-v5 | `1f6f8ef9efa7ca2bb7b406d23fa2ee01a6dfdb0b53e0d6a125e3f14ab8ff14bc` | #36 | **PASS** | power-cycle retry |
| 5 | boot-ssp-v6 | `5e67d6bcbf32340abb700fcc91eb35aebb1a5da95397e89f76352d7eb28d815e` | #40 | **PASS** | BBD peer transport, `bbd_sensor` writable |
| 6 | boot-ssp-v7 | `2c304ecaadb7f0e519356607951dd3725ff5c6d1d57490abd5858a417c5f9da2` | #41 | **PASS** | recoverable shutdown/reset state |
| 7 | boot-ssp-v8 | `14c5c4228ef531e53c8bbf7f5c79386de23c81dc85c9a584ed937ec4ae43427f` | #42 | **PASS** | peer tx/rx tracing |
| 8 | boot-ssp-v9 | `f8c4ae5286d420bc881e02c778fd0dcf88faa0bbab0cce0003a4302dae1d2b66` | #43 | **PASS** | balanced shub-int |
| 9 | boot-ssp-v10 | `a9d08bad6ce6f794ad19bc84f98df561164d08fe276affacf6153e936fd4fa92` | #44 | **PASS** | userns trace |
| 10 | boot-ssp-v11 | `40acab27dd7a54b0e410dd4b6f94d823add950f105bc549c47d1ba2fc8a30661` | #45 | **PASS** | create_user_ns stage trace |
| 11 | boot-ssp-v12 | `64731fb852430460f2a5f46d34b9d4f8f4c68b0dfa3f299f03b0d442ec663167` | #46 | **PASS** | chroot refine v1 |
| 12 | boot-ssp-v13 | `36bcd8be9cca3f2ed664a5b821e0fc115940bc88601bdcf4fc6030fa708e35a0` | #47 | **PASS** | chroot refine v2 |
| 13 | boot-ssp-v14 | `7ad5183acbfeb88c0f2232c5ebbcaaa3c087039a04be51f94bb5417b27505e2a` | #48 | **PASS — live** | userns reachable-chroot fix → `unshare -U` rc=0 |

No image boot-looped into TWRP.  Every recovery reboot was an explicit
`reboot recovery` issued from Nuxel over SSH to reach TWRP for the next write.

### 8.1 Rollback

```
# from TWRP
adb push backups/boot/boot-orig-20261113.img /tmp/boot-orig.img
adb shell 'dd if=/tmp/boot-orig.img of=/dev/block/by-name/boot bs=1M conv=fsync'
# expected readback:
# 7ca7cc70c1ab78ebd1882455ec6aaa9da9d5b766cbee01835ca7b8a20359abf8
```
