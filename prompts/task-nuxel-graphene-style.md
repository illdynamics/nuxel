You are building Nuxel — a hardened, Graphene-style Linux phone OS with ZERO Android dependencies. No Waydroid, no Halium, no libhybris, no APK, no AOSP. Pure Linux.

## REFERENCE DOCUMENTS
Read these two files in the workspace first:
1. `/workspace/Fonux, NuDroid, and the Best Path to a Linux-Only PWA-First Smartphone.md`
2. `/workspace/Building a Post-Android Phone OS on Existing Android Hardware.pdf`

## TARGET DEVICE
- Google Pixel 10 Pro XL
- Codename: mustang
- Serial: 58211FDCQ001LA
- HW: MP1.0, SKU: G45RY
- SoC: Google Tensor G5
- GPU: Imagination PowerVR DXT-72-2304
- Modem: Samsung Exynos 5500
- Kernel target: Linux 6.12 LTS, gs501_defconfig
- Display: Samsung AMB655X LTPO 3120x1440@120Hz
- Touch: Samsung S6SY791

## ARCHITECTURE PHILOSOPHY

This is NOT postmarketOS. This is NOT Alpine. This is NOT a desktop Linux remake.

This is: **Qubes-lite + Fedora Silverblue + hardened Flatpak + PWA runtime, on a phone.**

Key principles:
1. **Immutable OS** — read-only system partition, signed images, atomic A/B updates, automatic rollback on failed boot. No package manager mutating the live system.
2. **Portals everywhere** — apps ask for ACTIONS not permanent access. File picker, camera, mic, location, contacts, calendar, notifications, Bluetooth, USB, secrets portals.
3. **No ambient trust** — no app sees other apps' data, no ambient filesystem access, no ambient IPC, no background execution unless approved.
4. **Per-app sandboxing** — namespaces, cgroups, seccomp, Landlock, AppArmor, Bubblewrap, per-app nftables network policy.
5. **Hardened everything** — hardened_malloc, CFI, stack protector, PAC/BTI, RELRO, PIE, FORTIFY_SOURCE, zero writable+executable pages.
6. **Verified boot** — secure boot chain, signed kernel/initramfs/rootfs, user-controlled keys for bootloader relock, dm-verity for system partition.
7. **Wayland only** — no X11, no XWayland, no legacy display protocols.
8. **GTK4/libadwaita only** — one UI toolkit for native apps. Phosh shell. No KDE, no Qt, no multi-stack chaos.
9. **PWA-first app model** — but each PWA gets its own isolated browser profile, separate storage, per-app permissions, no shared browser state.
10. **No Android at all** — no Waydroid, no Halium, no libhybris, no APK support, no Play Services, no Android runtime. If an app doesn't have a PWA version, it doesn't run.

## CURRENT STATE

The workspace has 144 existing files including:
- 6 PWA apps (nuxel-home, mail, calendar, notes, files, camera-gallery)
- 4 native GTK4/libadwaita C apps (dialer, messages, contacts, settings)
- nuxel-bridge D-Bus service with capability model
- nuxel-notifications daemon
- boot/flash.sh — flash script for mustang
- boot/recovery.sh — recovery mode
- boot/initramfs/init.sh — initramfs bootstrap
- boot/boot.img/mustang-boot-config.txt — boot config
- kernel/defconfig — kernel config for gs501
- kernel/patches/0001-nuxel-phone-features.patch
- firmware/manifest.yml + firmware/install-firmware.sh
- docs/ (architecture.md, device-setup.md, build-guide.md, pwa-model.md, roadmap.md, bootloader-unlock-guide.md, driver-status.md, service-graph.md)
- services/nuxel-bridge/ + services/nuxel-notifications/
- shell/nuxel-shell/ (4 native apps + firstboot wizard)
- shell/config/ (meson.build, desktop files, icons, schemas, phosh override)
- pwa/ (all PWAs, Flatpak manifests, launcher)
- ci/validate-build.sh
- README.md, LICENSE

## WHAT TO BUILD / FIX / REPLACE

### 1. Rewrite docs/architecture.md
Complete rewrite. Structure:
- Immutable OS architecture (dm-verity system + writable data partition)
- A/B slot boot flow with verified boot chain
- App sandbox model (namespaces + seccomp + Landlock + AppArmor + nftables)
- Portals architecture (ALL hardware access through portals)
- PWA runtime isolation (per-app browser profiles, no shared state)
- Capability-based security for native apps
- No Android anywhere — no Halium, no libhybris, no Waydroid
- Explicitly state: "This is not an AOSP fork. This is not postmarketOS. This is a hardened Linux phone OS."
- Reference mustang hardware throughout

### 2. Create docs/security-model.md
Comprehensive security document:
- Sandbox architecture: bubblewrap + namespaces + seccomp BPF + Landlock + AppArmor
- Portals: xdg-desktop-portal + Nuxel-specific portals for telephony/contacts
- Exploit mitigations: hardened_malloc, CFI, stack protector, PAC/BTI, CET, RELRO, PIE
- Network isolation: per-app nftables rules via cgroupv2 + BPF
- Storage isolation: per-app `/var/app/<app-id>/data`, no cross-app access
- IPC isolation: only explicit D-Bus permissions, no ambient Unix sockets
- Display isolation: Wayland per-app surface isolation, no screen capture without portal
- Audio isolation: PipeWire per-app streams with portal grants
- Verified boot: user-controlled signing keys, dm-verity hash tree on system partition
- Boot chain: Boot ROM → Titan M3 → Nuxel-signed bootloader → dm-verity system → user data
- Relock support: User can enroll their own AVB key and relock bootloader

### 3. Rewrite docs/pwa-model.md
Complete rewrite for hardened PWA runtime:
- Architecture: Each PWA runs in its own WebKitGTK instance with separate WebContext
- Storage: Per-app IndexedDB/CacheAPI stored at `/var/app/<pwa-id>/data/`
- Permissions: Camera/mic/geolocation/notifications all gated through nuxel-bridge portals
- Background: Service workers register with nuxel-notifications for push
- Isolation: No shared cookies, no shared localStorage, no shared ServiceWorker registrations
- App lifecycle: PWAs launched by nuxel-home launcher, each in separate Flatpak with `--no-network` by default
- Network: Per-PWA network toggle via nftables cgroupv2 rules
- File access: Only through file picker portal, no `file://` access
- WebUSB/WebBluetooth/WebNFC: Explicitly disabled until portal infrastructure exists

### 4. Rewrite docs/build-guide.md
Complete rewrite for immutable image building:
- No pmbootstrap. No Alpine packages. No `apk add`.
- Build process: Compile kernel → build initramfs → assemble rootfs from Flatpak runtimes → create dm-verity hash tree → sign boot image → package for flashing
- Toolchain: aarch64-linux-gnu cross-compiler, openssl for signing, veritysetup for dm-verity
- Root filesystem: Based on GNOME Flatpak runtime (org.gnome.Platform//46) as the base, plus Nuxel-specific overlay
- Output: boot.img, vendor_boot.img, init_boot.img, system.img (with dm-verity), vbmeta.img
- Signing: User generates keys with `./tools/gen-keys.sh`, signs with `./tools/sign-image.sh`
- Flashing: Standard fastboot with VBmeta verification disabled (development) or user-signed (production)

### 5. Rewrite docs/device-setup.md
Complete rewrite for pure mainline approach:
- No Halium. No libhybris. No Android HAL reuse.
- Kernel: Linux 6.12 LTS from `android-gs-mustang-6.12` branch
- Device tree: mustang DTS from AOSP kernel tree, kept up to date
- Firmware: Extracted from factory image once, never modified
- Bootloader unlock: Standard `fastboot flashing unlock`
- AVB: Custom vbmeta with user keys for relocking
- Testing: Serial console via SuzyQ cable on ttyGSI0
- Known issues: Camera ISP (in progress), modem calls (MHI driver WIP), GPU (PowerVR mainline driver nascent)

### 6. Create services/nuxel-portal/ — Capability Portal Daemon
A D-Bus service that mediates ALL hardware access:
- `src/portal.py` — Main portal daemon implementing the xdg-desktop-portal interfaces
- Implements: Camera, Microphone, Location, Contacts, Notifications, FileChooser, Screenshot, ScreenCast
- Each portal request shows a GTK4 dialog for user consent
- Per-app permission tracking with revocable grants
- Integration with nuxel-bridge for phone-specific portals (SMS, Call, PhoneStatus)
- `dbus/org.nuxel.Portal.conf` — D-Bus security policy
- `systemd/nuxel-portal.service` or init script

### 7. Create shell/nuxel-shell/nuxel-sandbox/ — App Sandbox Policy
Sandbox configuration and enforcement:
- `sandbox.h` / `sandbox.c` — C library implementing sandbox creation
- Uses: `bwrap` (bubblewrap) for namespace isolation, `seccomp` for syscall filtering, `landlock` for filesystem restrictions
- Default policy: no network, no filesystem (except app data), no device access, no other process visibility
- `profiles/` directory — per-app sandbox profile JSON files defining allowed capabilities
- `nftables.sh` — sets up per-app nftables rules using cgroupv2 matching
- `seccomp/` — BPF filter definitions for common app categories

### 8. Create configs/hardened-malloc.conf
Configuration for GrapheneOS's hardened_malloc:
- Enable on system-wide basis via LD_PRELOAD
- Configuration: zero-on-free, canary protection, guard slabs, quarantine
- Integration with glibc via `/etc/ld.so.preload`

### 9. Create configs/apparmor.d/ — Per-App AppArmor Profiles
AppArmor profiles for:
- `usr.bin.nuxel-bridge` — D-Bus service with controlled bus access
- `usr.bin.nuxel-notifications` — Notification daemon
- `usr.bin.nuxel-dialer` — Only ModemManager D-Bus + audio
- `usr.bin.nuxel-messages` — Only ModemManager SMS D-Bus
- `usr.bin.nuxel-contacts` — Only contacts portal
- `usr.bin.nuxel-settings` — Only GSettings + selected system configs
- `usr.bin.nuxel-portal` — Portal daemon with broad D-Bus access
- `usr.lib.flatpak-*` — Template for Flatpak app confinement

### 10. Create configs/nftables/nuxel-app-firewall.nft
nftables ruleset for per-app network control:
- Default: drop all from app cgroups
- Allow: only if app has `network` capability granted
- DNS: Allow DNS (port 53) for all for name resolution
- VPN: Route through VPN interface if enabled
- Per-app rules: `socket cgroupv2 level 2 "app-*" accept`

### 11. Create tools/gen-keys.sh
Key generation script for verified boot:
- Generate RSA 4096 or ECDSA P-256 key for AVB signing
- Generate dm-verity root hash signing key
- Store keys in `keys/` directory (gitignored)
- Output public key for bootloader enrollment

### 12. Create tools/sign-image.sh
Image signing script:
- Sign boot.img with AVB key
- Generate dm-verity hash tree for system.img
- Create vbmeta.img chaining boot and system verification
- Sign vbmeta with device key

### 13. Rewrite images/mkrootfs.sh
Build script for the immutable root filesystem:
- Based on Flatpak runtime as base OS layer
- Mount system.img as ext4 with dm-verity
- Populate with Nuxel core services + native apps + Flatpak runtimes
- No package manager in the image
- All apps installed as Flatpak bundles in `/var/lib/flatpak`
- PWA runtime as Flatpak applications using WebKitGTK

### 14. Rewrite boot/flash.sh
Update for the immutable model:
- Flash dm-verity enabled system despite being in development
- Add --relock option for production relocking
- Add key enrollment support
- Keep all mustang-specific parameters

### 15. Update services/nuxel-bridge/src/bridge.py
Add portal integration:
- Register with nuxel-portal for permission checks
- Add `CheckPermission(app_id, capability)` D-Bus method
- Emit signals when permissions change
- Integrate with the portal dialog system

### 16. Update services/nuxel-bridge/src/capabilities.py
Add new capabilities:
- `network:outbound` — Outbound network access
- `network:inbound` — Inbound connections (servers)
- `storage:persistent` — Persistent storage
- `background:execution` — Run in background
- `display:screenshot` — Screen capture
- `display:screencast` — Screen recording
- `usb:access` — USB device access
- `bluetooth:scan` — BT scanning
- `bluetooth:connect` — BT connections

### 17. Update pwa/nuxel-home/js/bridge.js  
Add portal-driven permission requests:
- Request permission via bridge → portal dialog → user consent → grant
- Show permission status in app info
- Revoke permissions from app settings

### 18. Create pwa/flatpak/org.nuxel.PWARuntime.json
Flatpak manifest for the hardened PWA runtime:
- Based on org.gnome.Platform//46
- Includes WebKitGTK with sandboxed WebContext
- Default sandbox: --no-network, --no-device-access
- Network only granted via portal

## RULES
1. No Android. No Waydroid. No Halium. No libhybris. No APK. No Play Store. None.
2. GTK4/libadwaita/Phosh only. No KDE. No Qt. No X11.
3. Immutable OS. Read-only system. Atomic updates. Rollback.
4. Real code, not stubs. Every portal, sandbox, profile must be functional.
5. Mustang-specific throughout. No generic "works on any phone."
6. Graphene-level security thinking applied to Linux-native substrate.
7. Do NOT delete working PWA code — only update the bridge integration.
8. Do NOT delete working native C apps — only add AppArmor profiles.
9. Continue until all files are created with real content.
10. The result must be BUILDABLE and FLASHABLE to device 58211FDCQ001LA.

---

<!-- Task reconciliation owned by the Repo state audit & doc reconciliation build group (briq-01-audit). See docs/repo-audit.md for the measured single source of truth. -->
