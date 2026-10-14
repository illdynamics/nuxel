<!-- Nuxel v0.3.3-alpha -->
# Nuxel Architecture

> **Scope note:** This document describes the **target architecture and design
> intent** for Nuxel. It is a forward-looking spec, not a claim that every
> subsystem is implemented today. For the *measured* state of the codebase —
> real line counts, file inventory, and a verified-exists checklist of systemd
> units, D-Bus policies, and OpenRC scripts — see
> **[docs/repo-audit.md](repo-audit.md)** (single source of truth). Any table
> below that lists a status such as **"Enabled"** refers to the intended
> configuration of the target design unless the referenced file exists in the
> repo and is measured/verified in the audit.

<!-- Phase 3 Architecture Update v0.3.3-alpha -->
## Phase 3: Native GTK4 Home + System Portal Split

### Overview

As of Phase 3, Nuxel uses a **native GTK4/libadwaita Home screen** as the default
launcher in VM and development environments. The original Chromium kiosk PWA Home
(`nuxel-home-kiosk`) is preserved as a fallback only, activated via:

```bash
tools/nuxel-rollback-home.sh
```

### System Portal (Non-GUI)

The system portal (`nuxel-portal`) now runs **without GTK**. It delegates all
user-consent dialogs to the **Phosh Agent** (`nuxel-phosh-agent`), which runs
in the user session and provides GTK4/libadwaita permission dialogs via D-Bus:

```
Application → nuxel-portal (system bus, no GUI)
                → org.nuxel.PhoshAgent.RequestPermission (session bus)
                    → GTK4/libadwaita mobile dialog
```

This split ensures that system services (running as root) never import GTK,
while user-facing dialogs remain visually consistent with the Phosh/Adwaita theme.

### Notification Architecture

Notifications are now handled by a **system hub** (`org.nuxel.Notifications` on system bus)
with a **user relay** (`nuxel-phosh-agent` on session bus):

```
App → org.nuxel.Notifications.Notify (system bus)
         → stores notification in memory
         → emits NotificationAdded signal

nuxel-phosh-agent (session bus):
    → polls org.nuxel.Notifications.GetNotifications every 2s
    → relays new notifications to org.freedesktop.Notifications (FDO spec)
    → Phosh/phoc displays native desktop notifications
```

### Optional / Future

- **WebKitGTK PWA runtime**: Optional in the build system. PWA apps default to
  Chromium `--app=` mode for development. A dedicated WebKitGTK launcher with
  per-app isolation is planned as a future optimization.
- **Hardware flashing**: Gated behind explicit `--device` flags in `flash.sh`.
  VM bootstrapping via `vm/nuxel-vm-bootstrap.sh` is the recommended development path.

### Rollback

```bash
# Roll back to PWA Kiosk Home
tools/nuxel-rollback-home.sh

# Full rollback of Phase 3 changes
sudo systemctl disable nuxel-bridge nuxel-portal nuxel-notifications
systemctl --user disable --now nuxel-home-native.service
systemctl --user enable --now nuxel-home-kiosk.service
```

---

> **Target device:** Google Pixel 10 Pro XL (mustang) — Tensor G5, Exynos 5500 modem, PowerVR DXT-72-2304 GPU
> **Serial:** 58211FDCQ001LA
> **This is NOT an AOSP fork. This is NOT postmarketOS. This is NOT Alpine. This is a hardened Linux phone OS.**

---

## 1. Immutable OS Architecture

Nuxel is built on an **immutable root filesystem** — the system partition is read-only, signed, and verified at boot via dm-verity. No package manager mutates the running system. All application and user state lives on a separate writable data partition.

### 1.1 Partition Layout

```
Physical storage (UFS 4.0, 128/256/512 GB)
├── boot_a / boot_b          (96 MB each) — Kernel + initramfs, signed
├── init_boot_a / init_boot_b (8 MB each) — Generic ramdisk (boot header v4)
├── vendor_boot_a/b          (96 MB each) — Vendor ramdisk + DTBO
├── dtbo_a / dtbo_b          (16 MB each) — Device Tree Blob Overlay
├── vbmeta_a / vbmeta_b      (64 KB each) — AVB verification metadata
├── super (dynamic partitions, ~8 GB)
│   ├── system_a / system_b  — Nuxel immutable rootfs (ext4, dm-verity)
│   ├── system_ext_a/b       — Reserved
│   ├── product_a/b          — Product overlays, Flatpak runtimes
│   └── vendor_a/b           — Tensor G5 firmware blobs
├── metadata                 (64 MB) — OTA metadata, boot reason
├── modem_a / modem_b        (300 MB each) — Exynos 5500 firmware
├── bluetooth_a/b            (4 MB each) — BCM4390 firmware
├── dsp_a / dsp_b            (128 MB each) — Tensor G5 DSP firmware
├── persist                  (32 MB) — Factory calibration — NEVER TOUCH
├── misc                     (1 MB) — A/B slot selection
├── frp                      (512 KB) — Factory Reset Protection
└── userdata                 (remaining) — Writable user data (ext4/f2fs)
```

### 1.2 A/B Slot Update Model

Nuxel uses Google's A/B seamless update scheme:

- **Active slot** (e.g., `system_a`) — currently booted, read-only
- **Inactive slot** (e.g., `system_b`) — update target
- An OTA writes the new system image to the inactive slot
- On next boot, the bootloader switches to the updated slot
- If boot fails, the bootloader falls back to the previous slot automatically
- **Always two complete system copies** — no single-point-of-failure on update

Slot selection is stored in the `misc` partition. The bootloader reads it, loads the appropriate `boot_{a|b}` image, and verifies AVB chain through Titan M3.

### 1.3 Read-Only Guarantees

- `/usr` — read-only, dm-verity verified
- `/etc` — read-only at boot with an overlay (tmpfs) for runtime config
- `/var` — writable, lives on `userdata` partition
- `/home` — symlink to `/var/home`
- No writable files exist on the system image — full image replacement is the only update path

---

## 2. Display Stack: Wayland Only

**No X11. No XWayland. No legacy display protocols.**

```
App (GTK4/libadwaita or PWA WebKit)
    │
    ▼
Wayland Protocol (wl_surface)
    │
    ▼
Phosh / phoc (wlroots-based compositor)
    │
    ├── DRM/KMS (mainline) — Samsung AMB655X LTPO OLED @ 3120x1440 120Hz
    ├── libinput — Samsung S6SY791 touch controller
    ├── squeekboard — On-screen keyboard
    └── feedbackd — Haptic/LED/audio feedback
```

**Shell components:**
- **phoc** — wlroots compositor, window management
- **phosh** — Shell UI: lockscreen, panel, overview, notifications, quick settings
- **squeekboard** — Virtual keyboard with mobile layouts
- **feedbackd** — Haptic and audio feedback events

**Display pipeline (mainline kernel path):**
```
App → Wayland → wlroots Vulkan renderer → PowerVR DXT open-source driver → DRM/KMS → Panel
```

No Android framebuffer, no libhybris, no legacy compatibility layers.

---

## 3. Application Model

### 3.1 PWA-First, With Native Core

| Layer | Implementation | Security Model |
|-------|---------------|----------------|
| **Core phone apps** | GTK4/libadwaita native (C) | AppArmor, bubblewrap |
| **D-Bus services** | Python (nuxel-bridge, nuxel-portal, nuxel-notifications) | D-Bus policy, AppArmor |
| **User-installed apps** | PWAs in hardened WebKitGTK runtime | Flatpak + portal isolation |
| **System runtime** | Fedora Silverblue-style immutable | dm-verity, read-only |

### 3.2 Native Core Apps

Native GTK4/libadwaita C applications for hardware-critical functions:

| App | Purpose | D-Bus access |
|-----|---------|-------------|
| **nuxel-dialer** | Voice calls | ModemManager.Call, ModemManager.Voice |
| **nuxel-messages** | SMS/MMS | ModemManager.Messaging |
| **nuxel-contacts** | vCard contacts | org.nuxel.Contacts (nuxel-bridge) |
| **nuxel-settings** | System config | GSettings, NetworkManager, ModemManager |

These run **outside** the Flatpak sandbox with carefully audited privileges, confined by AppArmor profiles.

### 3.3 PWA Runtime Isolation

Every PWA runs in its **own isolated WebKitGTK instance** with:

- **Separate WebContext** — No shared cookies, localStorage, or ServiceWorker registrations
- **Per-app storage** — `/var/app/<pwa-id>/data/` for IndexedDB/CacheAPI
- **Per-app permissions** — Every hardware access gated through portals
- **No `file://` access** — File picker portal only
- **No WebUSB, WebBluetooth, WebNFC** — Disabled until portal infrastructure exists

---

## 4. Boot Chain

### 4.1 Verified Boot Flow (Production)

```
Power On
  │
  ▼
Boot ROM (mask ROM, immutable)
  │
  ▼
Titan M3 Security Chip
  ├── Verifies XBL signature (OEM key)
  ├── Verifies ABL signature (OEM key)
  │
  ▼
ABL (Android Bootloader — mustang variant)
  ├── Reads AVB descriptor from vbmeta_a/b
  ├── Verifies boot.img hash chain (dm-verity root hash)
  ├── Verifies system.img hash tree
  │
  ▼
Linux Kernel 6.12 LTS (from boot.img, signed)
  │
  ▼
Initramfs (from boot.img)
  ├── Loads dm-verity target for system partition
  ├── Verifies root hash against AVB chain
  ├── Mounts system (dm-verity, read-only)
  ├── Mounts userdata (writable, no verification needed)
  └── switch_root to system
       │
       ▼
systemd (or OpenRC) → nuxel services → Phosh → Lockscreen
```

### 4.2 Development Boot Flow

For development (unlocked bootloader, unsigned images):

```
fastboot flash vbmeta_a --disable-verity --disable-verification
fastboot flash vbmeta_b --disable-verity --disable-verification
```

This disables AVB verification, allowing unsigned boot images. **Never do this on a production device.**

### 4.3 User-Controlled Keys for Production

For production relocking:
1. User generates their own AVB signing keys via `tools/gen-keys.sh`
2. Signs boot.img, system.img, and vbmeta.img with their key
3. Enrolls the public key in the bootloader
4. Relocks the bootloader: `fastboot flashing lock`
5. The Titan M3 now verifies Nuxel-signed images with the user's key

---

## 5. App Sandbox Model

### 5.1 Sandbox Layers

Every application (both native and PWA) is confined by multiple layers:

```
┌─────────────────────────────────────────────────────┐
│                   APPLICATION                        │
├─────────────────────────────────────────────────────┤
│  Layer 1: Bubblewrap (namespace isolation)           │
│  ├── Mount namespace — only app data dir visible    │
│  ├── PID namespace — no other process visibility    │
│  ├── Network namespace — isolated or restricted     │
│  └── UID/GID namespace — sandbox user               │
├─────────────────────────────────────────────────────┤
│  Layer 2: seccomp BPF (syscall filtering)            │
│  ├── Default deny-all, allow-list by category        │
│  ├── Block: ioctl on /dev, ptrace, perf_event_open   │
│  └── Block: __arm64_smccc_smc (EL3 calls)           │
├─────────────────────────────────────────────────────┤
│  Layer 3: Landlock (filesystem restrictions)         │
│  ├── Read-only: /usr, /etc (system paths)           │
│  ├── Deny: /dev, /sys, /proc/<other-pids>           │
│  └── Allow: /var/app/<app-id>/data (rw)              │
├─────────────────────────────────────────────────────┤
│  Layer 4: AppArmor (MAC)                             │
│  ├── Per-app profile in configs/apparmor.d/          │
│  ├── Controls D-Bus access, capabilities             │
│  └── Controls binary execution, file read/write      │
├─────────────────────────────────────────────────────┤
│  Layer 5: nftables (network isolation)               │
│  ├── cgroupv2-based per-app rules                    │
│  ├── Default: drop all traffic from app cgroup       │
│  └── Allow: only if app has `network` capability     │
└─────────────────────────────────────────────────────┘
```

### 5.2 Portals Architecture

ALL hardware access is mediated through portals. No app talks directly to hardware.

```
Application
    │
    ▼
xdg-desktop-portal (standard portals)
    │
    ├── Camera portal → PipeWire → ISP
    ├── Microphone portal → PipeWire → Audio DSP
    ├── Location portal → GeoClue → GPS/GNSS
    ├── Notifications portal → nuxel-notifications
    ├── FileChooser portal → userdata filesystem
    ├── Screenshot portal → Wayland compositor
    └── ScreenCast portal → Wayland compositor
    
nuxel-portal (Nuxel-specific portals — new in this build)
    │
    ├── Telephony portal → ModemManager → Exynos 5500
    │   ├── SMS send/receive
    │   ├── Voice call initiate/end
    │   └── Phone status (signal, operator, battery)
    ├── Contacts portal → EDS / nuxel-contacts
    └── Settings portal → GSettings / system config
```

**Key principle:** The portal asks for an **action**, not permanent access. "This app wants to take a photo" — user approves for that one capture. No ambient camera permission.

---

## 6. Capability-Based Security (nuxel-bridge)

`nuxel-bridge` (`org.nuxel.Bridge`) is the central D-Bus service that mediates all PWA ↔ system communication.

### 6.1 Capability Registry

| Capability | System Access | Default |
|-----------|---------------|---------|
| `call:initiate` | ModemManager.Call.Create | Deny |
| `call:end` | ModemManager.Call.Hangup | Deny |
| `call:status` | ModemManager.Modem state | Prompt |
| `sms:send` | ModemManager.Messaging.Send | Deny |
| `sms:receive` | ModemManager.Messaging.List | Prompt |
| `contacts:read` | EDS / nuxel-contacts D-Bus | Prompt |
| `contacts:write` | EDS contact modification | Deny |
| `location:read` | GeoClue2.Client.GetLocation | Prompt |
| `camera:capture` | PipeWire camera portal | Prompt |
| `camera:preview` | PipeWire camera preview | Prompt |
| `notifications:send` | org.freedesktop.Notifications | Allow |
| `notifications:receive` | org.freedesktop.Notifications | Allow |
| `phone:status` | ModemManager.Modem props | Allow |
| `network:outbound` | Outbound network sockets | Prompt |
| `network:inbound` | Inbound connections (servers) | Deny |
| `storage:persistent` | /var/app/<id>/data writable | Allow |
| `background:execution` | Stay running after suspend | Deny |
| `display:screenshot` | Wayland screenshot protocol | Prompt |
| `display:screencast` | Wayland screencast protocol | Deny |
| `usb:access` | USB device nodes | Deny |
| `bluetooth:scan` | BlueZ scanning | Prompt |
| `bluetooth:connect` | BlueZ connections | Deny |

### 6.2 Permission Flow

```
PWA requests capability
    → bridge.py validates request
    → nuxel-portal shows GTK4 dialog
    → user grants/denies
    → capability stored in /var/lib/nuxel/permissions/<app-id>.json
    → bridge checks on every method call
    → user can revoke at any time via Settings
```

---

## 7. No Android. No Exceptions.

| Technology | Status | Reason |
|-----------|--------|--------|
| Waydroid | **Not present** | Would reintroduce Android runtime |
| Halium | **Not present** | Would require libhybris + Android kernels |
| libhybris | **Not present** | Would require Android HAL shims |
| APK support | **Not present** | Would require Android framework |
| Play Services | **Not present** | Proprietary Google dependency |
| AOSP | **Not present** | This is not an Android derivative |

**If an app doesn't have a PWA version or a native GTK4 port, it doesn't run on Nuxel.** This is by design — the security model depends on not having an Android compatibility layer.

---

## 8. System Services Graph

```
User (PWA/GTK4 App)
    │
    ├── Wayland (phoc/phosh) — Display, input, compositing
    ├── PipeWire — Audio routing, camera streams
    ├── xdg-desktop-portal — Standard portals (file, screen, camera)
    ├── nuxel-portal — Nuxel-specific portals (telephony, contacts)
    ├── nuxel-bridge — Capability-gated D-Bus mediator
    ├── nuxel-notifications — Notification relay to PWAs
    ├── ModemManager — Exynos 5500 modem control
    ├── NetworkManager — WiFi (BCM4390), cellular data, BT PAN
    ├── GeoClue — GPS/GNSS location (Exynos 5500 GPS engine)
    ├── BlueZ — Bluetooth 5.4 (BCM4390)
    ├── upowerd — Power management
    ├── iio-sensor-proxy — IMU, ALS, barometer (BMI270, TCS3710)
    ├── fprintd — Goodix gf3636 fingerprint sensor
    └── feedbackd — Haptic, LED, sound feedback
```

---

## 9. Exploit Mitigations

| Mitigation | Status | Mechanism |
|-----------|--------|-----------|
| hardened_malloc | **Enabled** | GrapheneOS malloc via LD_PRELOAD |
| CFI (Control Flow Integrity) | **Kernel + Userspace** | LLVM CFI, -fsanitize=cfi |
| Shadow Call Stack | **Enabled** | -fsanitize=shadow-call-stack (aarch64) |
| PAC (Pointer Auth) | **Enabled** | ARMv8.3-A PAC instructions |
| BTI (Branch Target) | **Enabled** | ARMv8.5-A BTI |
| RELRO (Full) | **Enabled** | -Wl,-z,relro,-z,now |
| PIE (Position Independent) | **Enabled** | -fPIE -pie |
| FORTIFY_SOURCE | **Level 3** | -D_FORTIFY_SOURCE=3 |
| Stack Protector | **Strong** | -fstack-protector-strong |
| Zero W+X pages | **Enforced** | Kernel CONFIG_STRICT_MODULE_RWX |
| Kernel page-table isolation | **Enabled** | CONFIG_UNMAP_KERNEL_AT_EL0 |
| Kernel address sanitizer | **Enabled** | CONFIG_KASAN (debug builds) |

---

## 10. Hardware Map (mustang — Pixel 10 Pro XL)

| Component | Device | Linux Driver |
|-----------|--------|-------------|
| **SoC** | Google Tensor G5 (gs501) | ARM64 architecture |
| **CPU** | 1×Cortex-X5 + 3×A730 + 4×A530 | cpufreq, cgroup, cpuidle |
| **GPU** | Imagination PowerVR DXT-72-2304 | PowerVR DRM/KMS (open-source) |
| **Display** | Samsung AMB655X LTPO 3120×1440@120Hz | Samsung panel driver + DSC |
| **Touch** | Samsung S6SY791 (I²C/SPI) | samsung_s6sy791 |
| **Modem** | Samsung Exynos 5500 | Exynos IPC, QRTR, MHI |
| **WiFi/BT** | Broadcom BCM4390 (SDIO) | brcmfmac, btbcm |
| **NFC** | NXP SN220 (I²C) | nxp-nci |
| **Audio** | Cirrus Logic CS42L43 + CS35L45 (×2) | cs42l43, cs35l45 |
| **PMIC** | Maxim MAX77729 + MAX77826 | max77729, max77826 |
| **Charger** | TI BQ2597x + MAX1720x | bq2597x, max1720x |
| **Fingerprint** | Goodix gf3636 (SPI) | goodix-fingerprint |
| **IMU** | Bosch BMI270 + ST LSM6DSV | bmi270, st_lsm6dsv |
| **ALS/Prox** | AMS TCS3710 | tcs3710 |
| **Barometer** | Bosch BMP581 | bmp581 |
| **Magnetometer** | AKM AK09970 | ak09970 |
| **Security** | Titan M3 | SPI TPM-like interface |
| **Battery** | 5300 mAh Li-Po | power_supply subsystem |
| **Storage** | UFS 4.0 | ufs-qcom |
| **USB-C** | USB 3.2 Gen2 + DP Alt Mode | dwc3, phy-qcom-qmp |
| **Wireless charging** | Qi 2.0 MPP | qcom-pm8941-wled |

---

## 11. Build System Architecture

**This is NOT pmbootstrap. This is NOT Alpine apk.**

Build flow:
```
Host (x86_64 Linux)
    │
    ├── Cross-compile kernel (aarch64-linux-gnu-)
    │   └── linux-6.12.y + gs501_defconfig + Nuxel patches → boot.img
    │
    ├── Build initramfs
    │   ├── kernel modules (UFS, display, touch, modem)
    │   └── busybox-based /init script
    │
    ├── Assemble rootfs
    │   ├── org.gnome.Platform//46 Flatpak runtime as base
    │   ├── Nuxel overlay: services, native apps, configs
    │   └── No package manager in image
    │
    ├── Create dm-verity hash tree
    │   └── veritysetup → system.img + root hash
    │
    ├── Sign boot image (AVB)
    │   └── avbtool + user key → signed boot.img
    │
    ├── Package for flashing
    │   ├── boot.img (signed)
    │   ├── init_boot.img (signed, v4 header)
    │   ├── vendor_boot.img (from factory)
    │   ├── system.img (dm-verity)
    │   └── vbmeta.img (chaining boot + system)
    │
    └── Flash via fastboot
        └── flash.sh script
```

**Output artifacts:** `build/out/` — flashable images ready for `fastboot flash`

**CI:** Each merge produces signed flashable images. Automated rollback testing on-device (mustang serial 58211FDCQ001LA).

---

## 12. Filesystem Layout (Runtime)

```
/ (dm-verity rootfs, read-only)
├── usr/
│   ├── bin/
│   │   ├── nuxel-bridge          — D-Bus capability mediator
│   │   ├── nuxel-portal           — Portal daemon
│   │   ├── nuxel-notifications    — Notification daemon
│   │   ├── nuxel-dialer           — GTK4 call app
│   │   ├── nuxel-messages         — GTK4 SMS app
│   │   ├── nuxel-contacts         — GTK4 contacts app
│   │   └── nuxel-settings         — GTK4 settings app
│   ├── lib/systemd/system/        — Service units
│   ├── share/
│   │   ├── applications/          — .desktop files
│   │   ├── icons/                 — App icons
│   │   ├── glib-2.0/schemas/      — GSettings schemas
│   │   └── nuxel/                 — Shared assets
│   └── libexec/                   — Helper binaries
├── etc/
│   ├── nuxel/                     — Nuxel config
│   │   ├── bridge.conf
│   │   ├── permissions/           — Per-app permission grants
│   │   └── pwa-registry/          — Installed PWA manifests
│   ├── apparmor.d/                — AppArmor profiles
│   ├── nftables/                  — nftables rulesets
│   └── dbus-1/system.d/           — D-Bus policies
├── var/ (writable, userdata partition)
│   ├── app/                       — Per-app data directories
│   │   └── <app-id>/
│   │       ├── data/              — App writable data
│   │       └── config/            — App configuration
│   ├── lib/flatpak/               — Flatpak runtimes + apps
│   ├── home/                      — User home directory
│   ├── log/                       — System logs
│   └── tmp/                       — Temporary files
└── mnt/
    └── sdcard/                    — External storage (when available)
```

---

## 13. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Init system | systemd | Industry standard, cgroup management, socket activation |
| Display server | Phosh (wlroots) | Purpose-built for mobile, GTK4-native |
| UI toolkit | GTK4/libadwaita | Only one toolkit, Phosh-native, maintained |
| App format | PWA + Flatpak | No SDK needed, automatic sandboxing, portal model |
| Base runtime | GNOME Flatpak runtime | Immutable, verified, no package manager |
| Sandbox | Bubblewrap + seccomp + Landlock + AppArmor | Defense in depth |
| Network control | nftables + cgroupv2 | Per-app rules without netfilter overhead |
| Boot verification | AVB + dm-verity | Standard Android verified boot chain |
| Security chip | Titan M3 | Hardware-backed key storage, attestation |
| Kernel | Linux 6.12 LTS | Long-term support, mainline mustang support |

---

## 14. Comparison: Nuxel vs. Alternatives

| Aspect | Nuxel | postmarketOS | Ubuntu Touch | Droidian |
|--------|-------|-------------|-------------|----------|
| **Base** | Fedora/Flatpak runtime | Alpine Linux | Ubuntu | Debian |
| **Android deps** | **None** | None (pure paths) | Halium+libhybris | Halium+libhybris |
| **Kernel** | Mainline 6.12 LTS | Mainline + vendor | Mostly vendor | Vendor |
| **App model** | PWA-first + native GTK4 | Native + anbox | Ubuntu Touch apps | Debian + Flatpak |
| **Sandbox** | Namespaces+seccomp+AppArmor | Flatpak | AppArmor | Flatpak |
| **Immutable** | **Yes — dm-verity system** | Partial | Yes | No |
| **Portals** | Every hardware access | Standard xdg portals | Custom | Standard |
| **OTA updates** | A/B slots, rollback | pmbootstrap | System image | APT |


---

<!-- Reconciliation & code-size accuracy owned by the Repo state audit & doc reconciliation build group (briq-01-audit). Single source of truth for all measured counts: docs/repo-audit.md. -->
