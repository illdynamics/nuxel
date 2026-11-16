# PWNAGE-107000 — USBNET completion + Quick Settings + Settings menu

**Mission:** make USB networking AND USB tethering fully usable, and add the
Quick Settings tile + a Settings menu entry.
**Date:** 2026-11-12
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
**Live kernel at audit:** `4.14.253` (#2 SMP PREEMPT, 2026-11-09)
**SSH:** `root@192.168.178.167` (`~/.ssh/wicked_wqn_id_rsa`)

---

## 1. What was done (summary)

| Part | Location | Requires reflash? |
|---|---|---|
| NCM `misc_deregister` panic fix (kernel) | `kernel/s10plus/patches/0011-nuxel-usb-ncm-idempotent-misc-deregister.patch` (+ `.required`) | **YES** |
| Enable ECM / ECM-subset / EEM + NAT/masquerade (kernel config) | `kernel/s10plus/configs/nuxel-drm-kbase.fragment` | **YES** |
| macOS host-tool cross-build fix for S10+ kernel | `kernel/s10plus/build-kernel.sh` | build-time only |
| **Flashable boot image** (new kernel + proven ramdisk/DTB) | `build/out/s10plus/debug-candidates/p107000-usbnet/boot-usbnet-ecm-ncm-fix.img` | **YES (this is the flash payload)** |
| USB networking + tethering helper (userspace) | `services/nuxel-s10/bin/nuxel-usb-net-helper.sh` | NO (SSH deploy) |
| Host-disconnect monitor | `services/nuxel-s10/bin/nuxel-usb-net-monitor.sh` | NO |
| Persist/restore systemd units | `services/nuxel-s10/systemd/nuxel-usb-net-{restore,monitor}.service` | NO |
| Bridge provider | `services/nuxel-bridge/src/usb_tethering.py` | NO |
| Bridge API wiring (REST + RPC) | `services/nuxel-bridge/src/api.py` | NO |
| Quick Settings tile | `pwa/nuxel-home/index.html` + `pwa/nuxel-home/js/qs.js` | NO |
| Settings menu section | `pwa/nuxel-apps/settings/index.html` + `pwa/nuxel-apps/settings/usb-network-settings.js` | NO |
| Unit tests | `tests/a80/test_usb_net_provider.py` | NO |

---

## 2. Why a reflash is (still) required

The USB data plane is **kernel-gated**. Two things needed a kernel rebuild:

1. **NCM teardown panic** — `drivers/usb/gadget/function/f_ncm.c` under
   `CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE` called `misc_deregister()` from
   `ncm_function_cleanup()` unconditionally, even when `misc_register()` had
   never succeeded. Tearing down an NCM configfs instance (`rmdir`) then
   dereferenced a non-registered/duplicate misc device and panicked
   (`Panic#2 Part1`, `misc_deregister+0x48`, recorded in the earlier
   `n26000-usb-ncm-panic` evidence). Fixed by making the deregister idempotent
   (a `mirrorlink_registered` flag set only on a successful `misc_register`).

2. **ECM / EEM / ECM-subset missing** — the only clean data-plane modes
   (`f_ecm.c` / `f_eem.c` / `f_subset.c` have no Samsung mirrorlink teardown)
   were `# CONFIG_USB_CONFIGFS_ECM is not set`, etc. in the defconfig. Enabled
   them so USB networking prefers CDC-ECM (safe teardown) while NCM/RNDIS are
   still available.

Until the new kernel is flashed, **the live device still runs the old kernel**
and the data plane remains BLOCKED. Nothing can change that in userspace.

---

## 3. Flash payload location (the thing to put in TWRP)

```
boot image  : build/out/s10plus/debug-candidates/p107000-usbnet/boot-usbnet-ecm-ncm-fix.img
size        : 54,593,536 bytes
sha256      : 4501750f5800538cd85fc6b3d314fef4350ceac62e29ffb5057450e63ee702c8
gate        : PASS (tools/s10plus/verify-boot-image.py)
report      : build/out/s10plus/debug-candidates/p107000-usbnet/boot-usbnet-ecm-ncm-fix.img.report.txt
```

Supporting kernel artifacts:

```
raw Image   : kernel/s10plus/.build/out/arch/arm64/boot/Image        (45,645,832 B)
Image.gz    : kernel/s10plus/.build/out/arch/arm64/boot/Image.gz     (16,323,492 B)
.config     : kernel/s10plus/.build/out/.config
```

The boot image reuses the **proven running ramdisk + DTB** taken from
`build/out/s10plus/debug-candidates/p100000/boot-current-s10plus.img`
(unmodified; `--no-dev-nodes` avoids the duplicate `/dev/console|/dev/null`
members the base already contains) and only replaces the kernel payload.

---

## 4. Userspace parts (deploy over SSH, NO reflash)

These can be shipped now on the existing SSH/deploy path (they are not
dm-verity protected in a way that blocks runtime replacement) and only become
fully functional once the new kernel is flashed:

- `services/nuxel-s10/bin/nuxel-usb-net-helper.sh` → `/usr/lib/nuxel/nuxel-usb-net-helper.sh`
- `services/nuxel-s10/bin/nuxel-usb-net-monitor.sh` → `/usr/lib/nuxel/nuxel-usb-net-monitor.sh`
- `services/nuxel-s10/systemd/nuxel-usb-net-restore.service` → `/usr/lib/systemd/system/`
- `services/nuxel-s10/systemd/nuxel-usb-net-monitor.service` → `/usr/lib/systemd/system/`
- `services/nuxel-bridge/src/usb_tethering.py` → `/usr/lib/nuxel-bridge/usb_tethering.py`
- `services/nuxel-bridge/src/api.py` → `/usr/lib/nuxel-bridge/api.py`
- PWA: `pwa/nuxel-home/*`, `pwa/nuxel-apps/settings/*`
- Test: `tests/a80/test_usb_net_provider.py`

### Helper usage (on the phone, as root)

```sh
# point-to-point USB Ethernet to host (device 10.15.19.82 / host 10.15.19.1)
/usr/lib/nuxel/nuxel-usb-net-helper.sh usbnet ecm

# USB tethering: share upstream via NAT (host 10.42.0.0/24, gw 10.42.0.1)
/usr/lib/nuxel/nuxel-usb-net-helper.sh tether ecm

# turn it all off (restores ACM-only gadget)
/usr/lib/nuxel/nuxel-usb-net-helper.sh off

# read state
/usr/lib/nuxel/nuxel-usb-net-helper.sh status
```

The CDC-ACM serial recovery console (`acm.usb0`, UDC `10c00000.dwc3`) is
preserved in every mode.

### Bridge / UI endpoints

- `GET  /api/v1/usb-net/status` (also `/api/v1/system/usb-net`)
- `POST /api/v1/usb-net/set-mode`  `{ "mode": "usbnet"|"tether"|"off", "function": "ecm" }`
- RPC: `bridge.call('usb-net', 'status'|'set-mode', …)` (owner surfaces only)

Quick Settings tile id `qs-usb-tether` (tap = usbnet on/off, long-press =
cycle off → usbnet → tether). Settings tab "USB network" with refresh +
Enable USB networking / Enable USB tethering / Disable buttons.

---

## 5. Validation already run

- Kernel build: `[kernel] Done.` + `kernel config: PASS — matches the live
  S10+ capability set`.
- Built `.config` contains the new symbols:
  `CONFIG_USB_CONFIGFS_ECM=y`, `ECM_SUBSET=y`, `EEM=y`, `USB_F_ECM/EEM/SUBSET=y`,
  `NF_NAT_MASQUERADE_IPV4=y`, `IP_NF_TARGET_MASQUERADE=y`.
- Boot image gate: **PASS**.
- `tools/beta/live/tests/test_tri_link.py`: **51 passed**.
- `tests/a80/test_usb_net_provider.py`: **5 passed** (new).
- `bash -n` on both shell scripts: pass.
- `node --check` on `qs.js` and `usb-network-settings.js`: pass.

---

## 6. NOT done / honest limits

- The flash itself was **not** performed in this run (the user will put the
  phone in TWRP and a follow-up run will `dd`/heimdall the boot image).
- **Host-side macOS ECM driver** is still unvalidated: macOS has no built-in
  CDC-ECM driver; a Linux host (or a reviewed macOS userspace driver) is needed
  for the host end of USB networking/tethering. The phone side is fixed and
  safe to enable.
- RNDIS remains compiled but is `NEEDS_VALIDATION`; ECM is now the preferred
  safe mode.
- Physical proof (real USB link + tether throughput) is pending the reflash +
  a real host cable.

---

## 7. Rollback

- Reflash: boot the previous A/B slot or re-flash
  `build/out/s10plus/debug-candidates/p100000/boot-current-s10plus.img`
  (sha256 `2cbc5085…`) from TWRP.
- Userspace: back up each replaced file before deploy and use the existing
  mission rollback convention (`*.nuxel-rollback-p107000-<UTC>`).
- CDC-ACM `/dev/ttyGS0` (host `/dev/ttyACM*`) is the recovery console in every
  experiment and is never removed.
