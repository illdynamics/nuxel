# PWNAGE-SSP — Report (S10+ sensors & auto-rotation)

**Device:** Samsung Galaxy S10+ `SM-G975F`, `beyond2lte`, Exynos 9820
**Serial:** `R58M75KDB2X`
**Date:** 2026-11-13 (Europe/Amsterdam)
**Live image at report time:** `boot-ssp-v14.img`, kernel `4.14.253-gf7194c1d15ed-dirty #48`
SHA256 `7ad5183acbfeb88c0f2232c5ebbcaaa3c087039a04be51f94bb5417b27505e2a`
**Rollback (known-good pre-SSP boot):** `backups/boot/boot-orig-20261113.img`
(`7ca7cc70c1ab78ebd1882455ec6aaa9da9d5b766cbee01835ca7b8a20359abf8`)

> This document replaces the earlier draft.  Every status below was measured on the
> handset in this run; nothing is inferred from a device node existing.

---

## 0. Status summary

| Requirement | Status | Evidence |
|---|---|---|
| Nuxel boots on the delivered kernel | **PASS** | §1, RE reflash log |
| Accelerometer supplies real live data | **FAIL** | §4 — `raw_data` `0,0,0`; hub returns no SPI data |
| Gyroscope supplies real live data | **FAIL** | §4 |
| Nuxel sensor service works reliably | **PARTIAL** | bridge runs, opens the ABI, relays frames; hub silent (§4) |
| Orientation detection | **PARTIAL** | policy/daemon live; auto mode correctly refuses without a real sample |
| Actual Nuxel display rotates on request | **PASS** (manual) | §5 — `wlr-randr --transform 270` applied and read back |
| Display rotates from physical movement | **FAIL** | needs live accelerometer |
| Three physical rotation cycles | **NOT TESTED — OPERATOR REQUIRED** | no live sensor |
| **Per-app firewall kernel flag** | **PASS** | §6 — `unshare -U/-Ur` as `nuxel` rc=0; `meta cgroup <classid>` loads |
| Force checkbox (per-app default rotation) | **PASS** (source + live API) | §7 |

**Bottom line (honest):** the kernel, device tree and userspace are now correct and
verified end-to-end **up to the sensor hub's MCU**, and two blocked capabilities were
fixed for real (unprivileged user namespaces → per-app firewalling; the BBD peer
transport).  The remaining blocker is not in Nuxel's code path: the BCM47752 MCU
does not answer the SPI stream until its application firmware ("patch") is
downloaded, and the only implementation of that download protocol is the vendor
Android `lhd`, which requires seven Bionic libraries plus the Android sensor HAL
that do not exist under glibc.  §4 documents exactly what is measured and what
would be needed next.  No synthetic sample has been produced or claimed.

---

## 1. Flash history (all verified, boot partition only)

Every write below: device identity checked (`beyond2lte`), boot partition resolved
to `/dev/block/sda14` (57 671 680 B), pre-flash backup pulled, image SHA256 checked
on-device, write, on-device readback compared.  **No other partition was touched.**

| # | Image | SHA256 (short) | Result |
|---|---|---|---|
| 1 | boot-ssp-v3 (pre-existing build) | `cbcc4335` | not flashed (superseded) |
| 2 | boot-ssp-v4 | `d2b23085` | PASS — Nuxel booted (`#35`) |
| 3 | boot-ssp-v5 | `1f6f8ef9` | PASS — booted (`#36`) |
| 4 | boot-ssp-v6 | `5e67d6bc` | PASS — booted (`#40`) |
| 5 | boot-ssp-v7 | `2c304eca` | PASS — booted (`#41`) |
| 6 | boot-ssp-v8 | `14c5c422` | PASS — booted (`#42`) |
| 7 | boot-ssp-v9 | `f8c4ae52` | PASS — booted (`#43`) |
| 8 | boot-ssp-v10 | `a9d08bad` | PASS — booted (`#44`) |
| 9 | boot-ssp-v11 | `40acab27` | PASS — booted (`#45`) |
| 10 | boot-ssp-v12 | `64731fb8` | PASS — booted (`#46`) |
| 11 | boot-ssp-v13 | `36bcd8be` | PASS — booted (`#47`) |
| 12 | boot-ssp-v14 | `7ad5183a` | **PASS — live now (`#48`)** |

The phone returned to TWRP only when Nuxel was deliberately asked to reboot into
recovery (`reboot recovery`) between attempts; it never boot-looped back to TWRP.

Per-attempt pre-flash backups live in `backups/boot/boot-pre-v*-*.img`.

---

## 2. Kernel work that was verified on hardware

Each item below was a real defect found by measurement and fixed in the tree, then
confirmed from the live kernel (`/sys`, dmesg) after flashing.

| Fix | Why it was needed | Live proof |
|---|---|---|
| `nuxel_ssp_data` registered at probe | the pointer was only set by BBD callbacks that require `lhd`; every bring-up said "SSP device not registered" | dmesg `Nuxel bring-up target registered` |
| `nuxel_ssp_bringup_hw()` runs even after a previous failure | a failed attempt set `resetting=1` and `bSspShutdown=1`, permanently blocking retries | `nuxel_hub_diag` shows `shutdown`/`resetting` cleared |
| BBD peer transport (open/write `bbd_sensor`, direct `tx` frames) | the userspace peer read the wrong side; `.write` was NULL so replies returned `-EAGAIN` | dmesg `Nuxel peer tx hdr=0f … -> 11` |
| MCU power-cycle retry on failed handshake | a halted MCU needs the 1.8 V rail cycled | dmesg `vdd_mcu_1p8 re-enabled -> 0 (enabled=1)` |
| balanced shub-int enable | double `enable_irq()` caused `Unbalanced enable for IRQ 443` | warning gone in #48 dmesg |
| rate-limited reset requests | each hello timeout raised an MCU reset; under the native bridge that was a reset loop | `Nuxel hello reset requested/refused` counters |
| `inc_ucount()` uninitialised `tns` | loop step dereferenced `tns` before assignment | source fix + gate |
| `current_chrooted()` reachable-chroot refinement | Nuxel PID1 chroots into the Fedora root, so upstream check reported every process as chrooted and `create_user_ns()` failed with **ENOSPC** | `unshare -U` rc=0 (§6) |

Build gates on the delivered kernel: `kernel config: PASS`, `userns gate: PASS`,
NFC + USBNET objects compiled and symbol-checked, `verify-boot-image.py` PASS
(raw arm64 Image, LZMA ramdisk, `sec-nfc@27` intact, slack 0).

---

## 3. Device tree / hardware identification

Unchanged from the measured map (`PWNAGE-SSP-HARDWARE-MAP.md`): SPI7 `BCM4773@0`,
`ssp-host-req`/`ssp-mcu-req`/`ssp-mcu-resp`, `ssp-shub-int` IRQ 443, MCU rail
`vdd_mcu_1p8`, hub `BCM47752KUB1G`, firmware string `BR0121080900,BR010`,
LSM6DSO accel+gyro behind it.  **No DT property, GPIO, IRQ, rail or address was
guessed or changed.**

---

## 4. The remaining blocker, measured

What works now, in order:

1. `nuxel-ssp-bridge` opens `/dev/bbd_sensor` (read+write) and `/dev/ttyBCM`.
2. The kernel delivers every AP→MCU message to the peer as a full
   `[u16 len][ssp_msg][payload]` frame (dmesg `Nuxel peer tx hdr=0f len=1 … -> 11`).
3. The bridge writes those bytes to `/dev/ttyBCM` and the SSI work queue performs a
   real SPI transfer (dmesg `DBG SPI @ TX: <255B = 1 … RX: <255B = 1`).
4. The hub **never answers**.  Raw MISO reads are `0xFF` with the SSI
   `PE` (protocol error) flag:

   ```
   [SSPBBD]: DBG SPI @ PZC: rx stat 0xff(PE) avail 114688, (rx_strm_fifo_ovfl)
   ```

   and `get_chipid()` times out on every attempt:
   `completion is timeout!` → `MCU device ID = 85, reading ID = -1`.

5. Therefore `sensor_state` reads back empty, `enable=0`, and both
   `accelerometer_sensor/raw_data` and `gyro_sensor/raw_data` stay `0,0,0`.

**Why:** the BCM47752 only speaks that stream after its application firmware is
downloaded.  Samsung ships that image inside the kernel
(`drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h`,
`AsicVersion=0x004775B0` = BCM4775x, `BlobLength=438895`, CRC-32 `0x93D3F2B4`) and
the running kernel serves it via `/dev/bbd_patch` (verified: 897 113 bytes,
header matches).  The download protocol itself is implemented only by vendor
`lhd`:

* `sensors/acquired/vendor-bin-hw-lhd` is Bionic: interpreter
  `/system/bin/linker64`, `DT_NEEDED` `liblog, libutils, libz,
  libhardware_legacy, libc++, libc, libm, libdl`.
* It is a *daemon* that also needs the Android sensor HAL
  (`sensors.sensorhub.so`, `sensors.exynos9820.so`) for the data path.

The alternative tried and measured: the kernel's own `bbd_rpc_lh.c` implements only
the **receive** side of the reliable transport layer; there is no native
patch-download (RPC request construction) code anywhere in this kernel tree or in
Nuxel.  Guessing that proprietary RPC framing would be a fabricated fix, which the
specification forbids, so it was not done.

**What is needed to finish:** either
(a) a lawful implementation of lhd's patch-download RPC (request id + chunking +
transport-layer TX), verified against the hub's own replies, or
(b) running the owner's extracted `lhd` inside an isolated Android-compat prefix
with the matching linker/libraries and a stub sensor HAL.

Neither is present.  Until then the sensor stream cannot exist and auto-rotation
cannot be honest.

---

## 5. Display rotation (compositor path) — PASS

The compositor accepts and reports the transform even though the sensor is silent:

```
$ XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
    wlr-randr --output HEADLESS-1 --transform 270
HEADLESS-1 … Transform: 270     # read back
$ … --transform normal
HEADLESS-1 … Transform: normal  # read back
```

`nuxel-orientationd` is live (`_daemon_live: true`, `display_verified: true`) and
correctly reports `auto_state: fixed` / `auto: false` because no real gravity
sample exists.  Returning it to `normal` restored portrait.

---

## 6. Per-app firewall kernel flag — PASS

Measured on the live kernel `#48`:

```
$ su - nuxel -c "unshare -U true";        rc=0
$ su - nuxel -c "unshare -Ur true";       rc=0
$ su - nuxel -c "unshare -U -r id -u";    0  rc=0
```

Kernel capabilities present and verified live: `CONFIG_USER_NS=y`,
`CONFIG_NF_TABLES=y`, `CONFIG_NFT_META=y`, `CONFIG_CGROUP_NET_CLASSID=y`.
nftables `1.1.3` loads the per-app rule form this kernel supports and counts it:

```
meta cgroup 16973825 accept
meta cgroup 0 counter packets 7 bytes 923 accept
# re-checked on the live device at 13:15: nft rc=0
```

`nuxel-firewall.sh classid nuxel-dialer` → `17023629` (deterministic).
The boot opt-in is shipped as `/etc/sysctl.d/90-nuxel-userns.conf`
(`kernel.unprivileged_userns_clone=1`).

Honest limitation: this Samsung 4.14 tree has **no `nft_socket` expression at all**
(`socket cgroup…` is rejected by the kernel), so the cgroup-classid match above is
the correct mechanism, not the cgroupv2 path variant.

---

## 7. Other operator requests (source-verified; were already implemented)

Confirmed present in the repository (and unchanged by this run):

* NFC, location and Wi-Fi status-bar icons hide while their radio is off
  (`pwa/nuxel-home/js/status-bar.js`).
* Notification cue `nuxel-pow.mp3` plus edge FX on notification.
* Edge FX toggles for notification / screen-on / screen-off / lock / unlock.
* Settings → Apps per-app default rotation with a **Force** checkbox.

A fresh live end-to-end check of these UI items was **NOT TESTED** in this run
(they need an operator at the glass).  They are `PASS (source)` only.

---

## 8. What would change the FAILs to PASS

1. Sensor firmware download (see §4).  Only then do `raw_data` nodes carry real
   samples and `nuxel-orientationd` leaves `auto_state: fixed`.
2. The physical three-cycle rotation test (operator present).
3. The UI checks in §7 (operator present).

---

## 9. Final live state (13:16 CET)

```
$ uname -r                 4.14.253-gf7194c1d15ed-dirty   (#48)
$ systemctl is-system-running   running
$ systemctl is-active nuxel-wayland nuxel-orientationd nuxel-ssp-bridge nuxel-bridge
active active active active
$ cat /sys/class/sensors/ssp_sensor/nuxel_hub_diag
mcu_probe=1 shutdown=1 resetting=0 sensor_state=0x3feff enable=0x0 shub_irq=443
$ cat accelerometer_sensor/raw_data   -> 0,0,0
$ cat gyro_sensor/raw_data            -> 0,0,0
$ su - nuxel -c "unshare -U true"     -> rc=0
$ nft (meta cgroup classid rule)      -> rc=0
```

The phone is live on the delivered image with no recovery fallback, and the
persisted bridge keeps the transport open for the sensor-hub bring-up attempt.

## 10. Honest completion statement

Two capabilities were actually **fixed and hardware-verified** in this run:

* **per-app firewalling kernel flag** — unprivileged user namespaces now work
  (`unshare -U` rc=0 as the user) and nftables classid matching loads;
* **native BBD/SSP bring-up path** — the kernel registers the SSP device,
  performs recovery, and carries AP↔MCU frames through a glibc peer without
  Bionic.

Automated rotation is **not** achieved because the BCM47752 MCU does not stream
until vendor firmware is downloaded, and that proprietary RPC has no
implementation available to Nuxel.  Per the mission's definition of done this is
reported as **FAIL** for live accelerometer/gyro and **NOT TESTED — OPERATOR
REQUIRED** for the physical rotation cycles.  No synthetic data was used.
