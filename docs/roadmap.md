# Nuxel Development Roadmap

This document outlines the planned development milestones for Nuxel, from the current MVP phase through to a v1.0 release suitable for daily driving on the Google Pixel 10 Pro XL.

---

### Note on code-size claims (accuracy correction)

Early drafts of `README.md` and `docs/milestones.md` cited an inflated
**"~25K lines"** figure for the native core. The measured, reproducible core is
far lower but reflects **real, present code**. The single source of truth for
all code-size figures is **[docs/repo-audit.md](repo-audit.md)**; the headline
numbers, re-measured on this cycle:

```
corrected cycle: claimed 25K, actual core ~7.2K
```

```bash
# pure Python across the two core trees (~7.2K "true core"):
find services/ shell/ -name '*.py' | xargs wc -l
#    => 7,234 lines (services/ 2,863 + shell/ 4,371)

# Python + C (the exact command older prose quoted):
find services/ shell/ -name '*.py' -o -name '*.c' | xargs wc -l
#    => 12,246 lines total

# Full .py/.c/.js cross-tree total (services + shell + pwa):
find services/ shell/ pwa/ \( -name '*.py' -o -name '*.c' -o -name '*.js' \) | xargs wc -l
#    => 18,036 lines total
```

The pure-Python core (services + shell tooling) is **~7.2K lines**, and adding
the C sources brings Python + C to **12,246** lines. The sandbox subsystem is
**2,005** lines, not the ~20K previously listed. Separate from this core, the
boot/initramfs, kernel config, PWA pipeline, and build/CI tooling add further
real code. What the docs once called "gaps" (systemd units, D-Bus policy files,
OpenRC init scripts) already exist as committed files under
`services/*/systemd`, `services/*/dbus`, and `shell/config/openrc/` — see
`README.md` and the verified-exists checklist in `docs/repo-audit.md`.

---

## Milestone Overview

| Milestone     | Target    | Key Deliverables                                                           |
|---------------|-----------|----------------------------------------------------------------------------|
| **MVP**       | 3 months  | Bootable system, Phosh shell, PWA launcher, SMS/calling, basic WiFi        |
| **Beta**      | 6 months  | Full PWA suite, bridge v1, notifications, camera, stable connectivity, OTA |
| **v1.0**      | 12 months | Mainline kernel, GPU acceleration, full hardware support, FDE, app store   |

---

## MVP (Minimum Viable Product) — This Phase

**Target: 3 months from project start**

The MVP proves that Nuxel can boot, run Phosh, launch PWAs, and handle fundamental phone operations (SMS and voice calls) on real hardware.

### Core System

| Task                                          | Status      | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Vendor kernel boots on mustang                | ✅ Complete  | Google's `android-gs-mustang-6.12` kernel boots via Halium bridge        |
| Alpine Linux rootfs                          | ✅ Complete  | pmbootstrap-generated rootfs with musl/BusyBox/OpenRC                    |
| Phosh compositor running                      | ✅ Complete  | Phosh on wlroots displays lockscreen and shell                           |
| Basic touch support                           | ✅ Complete  | libinput + Samsung S6SY791 driver producing correct touch events          |
| OpenRC service initialization                  | ✅ Complete  | System boots to multi-user target, all core services start               |
| ModemManager detects modem                    | ✅ Complete  | Samsung Exynos plugin recognizes Exynos 5500, AT commands functional     |
| SMS send/receive via ModemManager             | ✅ Complete  | SMS sending and receiving verified using mmcli and chatty                |

### Telephony

| Task                                          | Status      | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Voice call initiation                         | 🚧 In progress | ModemManager Voice API creates calls; audio routing being integrated   |
| Call audio routing (uplink/downlink)           | 🚧 In progress | PipeWire ALSA UCM routing for voice call paths via Cirrus Logic CS35L45 + CS42L43 |
| DTMF tone generation                          | ⬜ Pending   | In-band and out-of-band DTMF via ModemManager                            |
| Call hold, swap, conference                   | ⬜ Pending   | Multi-party call management (deferred to Beta)                           |

### Networking

| Task                                          | Status      | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| WiFi connectivity (NetworkManager)             | ✅ Complete  | wpa_supplicant connects to WPA2/WPA3 networks via brcmfmac               |
| WiFi scanning and selection                   | ✅ Complete  | Phosh quick settings shows available networks                            |
| DNS resolution                                | ✅ Complete  | systemd-resolved alternative via openresolv + dnsmasq                    |
| Cellular data (LTE/5G)                        | ⬜ Pending   | ModemManager Bearer API; deferred — WiFi is MVP connectivity              |
| Bluetooth basic (stack init)                   | ⬜ Pending   | BlueZ stack running; no profiles yet; Broadcom BCM4390 detected          |

### PWA Infrastructure

| Task                                          | Status      | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| nuxel-home launcher shell                     | 🚧 In progress | Phosh app drawer replacement with PWA install flow                     |
| Flatpak runtime for PWAs                      | 🚧 In progress | `org.nuxel.Platform` with WPE WebKit + bridge IPC library               |
| PWA manifest parsing and install flow         | 🚧 In progress | Manifest → Flatpak manifest generation + capability consent dialog      |
| PWA launch and sandboxing                     | 🚧 In progress | PWA runs in Flatpak bubblewrap with bridge socket mounted               |

### Bridge

| Task                                          | Status      | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| nuxel-bridge D-Bus service skeleton            | 🚧 In progress | D-Bus service registered; handshake protocol implemented               |
| JSON messaging protocol                        | 🚧 In progress | Request/response marshalling; event subscription framework             |
| SMS capability (pass-through to ModemManager)  | 🚧 In progress | Bridge forwards `sms.send`/`sms.list` to ModemManager Messaging        |
| Call capability (pass-through to ModemManager) | ⬜ Pending   | Bridge forwards `call.dial`/`call.hangup` to ModemManager Voice         |

### Deliverables

1. **Flashable image** — Complete boot.img + init_boot.img + rootfs.img + vendor.img that flashes via fastboot and boots to Phosh
2. **SMS PWA reference implementation** — A minimal PWA that sends and receives SMS via nuxel-bridge
3. **nuxel-home launcher** — PWA shell with install flow and app switching
4. **Documentation** — Complete build guide, device setup guide, and architecture overview

---

## Beta

**Target: 6 months from project start** (3 months after MVP)

Beta brings a complete PWA application suite, a fully functional bridge with all capabilities, camera support, stable connectivity, and over-the-air update infrastructure.

### PWA Suite

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Mail PWA                                      | Beta        | IMAP/SMTP email client with offline support (via bridge `storage`)       |
| Calendar PWA                                  | Beta        | CalDAV calendar with notifications                                       |
| Notes PWA                                     | Beta        | Markdown notes with flat-file storage                                    |
| Files PWA                                     | Beta        | File manager using storage bridge capability                             |
| Camera/Gallery PWA                            | Beta        | Photo capture, viewing, and basic editing                                |
| Maps/Navigation PWA                           | Beta        | GPS navigation using `location` capability + OpenStreetMap               |
| Weather PWA                                   | Beta        | Location-aware weather using `location` capability                       |
| Tasks PWA                                     | Beta        | Todo list with background sync                                           |

### nuxel-bridge v1

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Full capability model implementation           | Beta        | All capabilities (sms, call, contacts, location, camera, notifications, storage, network, background-sync) |
| Capability consent UI (install-time)           | Beta        | Per-capability toggle during PWA install with plain-language descriptions |
| Capability revocation UI (runtime)             | Beta        | Settings → Apps → Permissions with live toggles                          |
| Audit logging and privacy dashboard            | Beta        | Per-PWA capability access log viewable in Settings                       |
| Event subscription system                      | Beta        | Push events for incoming SMS, call state changes, location updates       |
| Bridge protocol v1 (stable)                    | Beta        | Versioned protocol with backward compatibility guarantees                |

### Notification System

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| System notification daemon                    | Beta        | Phosh notification panel populated via org.freedesktop.Notifications     |
| PWA notification capability                   | Beta        | PWAs can send notifications via bridge; click events returned to PWA     |
| Do Not Disturb mode                           | Beta        | Scheduled and manual DND with per-PWA override                           |
| Notification channels / categories            | Beta        | Granular notification control per PWA (alerts, silent, blocked)          |

### Camera Support

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Camera HAL via libcamera                      | Beta        | Basic camera capture pipeline using vendor camera blobs via Halium       |
| PipeWire camera portal                        | Beta        | xdg-desktop-portal camera integration for PWA camera access              |
| Camera preview in PWA                         | Beta        | Viewfinder stream to PWA via bridge                                      |
| Photo capture                                 | Beta        | Single-shot photo capture with EXIF metadata                             |
| Gallery integration                           | Beta        | Captured photos available through Files PWA and gallery view             |

### Connectivity

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Cellular data (LTE)                           | Beta        | ModemManager Bearer API with NetworkManager integration                  |
| WiFi stability improvements                   | Beta        | Power saving tuning, roaming, hidden SSID handling                       |
| Bluetooth audio (A2DP/HFP)                    | Beta        | Media playback and hands-free calling via Broadcom BCM4390 Bluetooth     |
| Bluetooth input (HID)                         | Beta        | Bluetooth keyboard/mouse support                                         |
| GPS navigation stability                      | Beta        | Continuous GPS tracking with adequate power management                   |
| Hotspot / tethering                           | Beta        | WiFi and USB tethering via NetworkManager                                |

### OTA Updates

> **Full update policy:** see [`docs/update-strategy.md`](update-strategy.md)
> for the complete strategy. Two mechanisms are used:
> - **RAUC** for the `mustang` phone (pmOS) — A/B rootfs slots, dm-verity
>   rootfs, signed `.raucb` bundles, boot-status rollback.
> - **OSTree / rpm-ostree** for the Fedora ARM64 VM — image-based deployments,
>   GRUB atomic activation, plain-LVM userdata.
>
> See also `images/rauc/`, `images/ostree/`, and the build entrypoint
> `images/build-ota.sh` (targets `--target pmos` and `--target fedora`).

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| OTA package generation                        | Beta        | Incremental update packages for kernel, rootfs, and PWA runtimes         |
| A/B slot update mechanism                     | Beta        | RAUC slots on mustang; OSTree deployments on the VM                      |
| Update notification and scheduling            | Beta        | System notification when update available; scheduled install             |
| Rollback on boot failure                      | Beta        | RAUC boot-status marker on mustang; `rpm-ostree rollback` / GRUB on VM   |
| Signed updates                                | Beta        | ED25519/GPG-signed RAUC bundles; GPG-signed OSTree commits               |

**Update tooling status:**

- [x] `docs/update-strategy.md` — policy, slots, rollback, signing, delivery
- [x] `images/rauc/mustang-system-bundle.conf` — on-device RAUC `system.conf`
- [x] `images/rauc/rauc-config.in` — RAUC bundle manifest template
- [x] `images/ostree/README.md` — OSTree compose → deploy → rollback flow
- [x] `images/build-ota.sh` — single entrypoint producing pmos/fedora artifacts
- [ ] Client `nuxel-update` polling + auto-install scheduling (bridge/PWA)

### Deliverables

1. **Beta image** — Full Beta feature set in a flashable image
2. **PWA app catalog (initial)** — Curated list of Nuxel-compatible PWAs
3. **OTA infrastructure** — Update server and client-side tooling
4. **Expanded documentation** — PWA development guide, bridge API reference

---

## v1.0

**Target: 12 months from project start** (6 months after Beta)

v1.0 is the "daily driver" release. It completes the transition to a mainline Linux kernel, enables full hardware acceleration, implements comprehensive power management, and provides full-disk encryption and an app distribution model.

### Mainline Kernel

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Mainline 6.12 LTS kernel booting               | v1.0        | Unmodified mainline kernel with Tensor G5 (gs501) Device Tree            |
| DRM/KMS display driver (MSM DPU)               | v1.0        | Native DRM display driver replacing vendor fbdev path                    |
| GPU initialization (Imagination PowerVR DXT-72-2304) | v1.0    | PowerVR Mesa loading GPU firmware from linux-firmware                   |
| QRTR + IPA modem data path                     | v1.0        | Mainline IPC Router and IPA driver for cellular data via Exynos 5500    |
| UFS 4.0 storage driver                         | v1.0        | Native UFS driver (already upstream, needs DT enablement)                |
| USB-C PD and DisplayPort Alt Mode              | v1.0        | USB Power Delivery negotiation and DP output                             |
| All CPU cores operational                      | v1.0        | CPUfreq and scheduler tuned for Tensor G5 (gs501) cluster                |
| Remove Halium/libhybris dependency             | v1.0        | All userspace binaries link against musl; no bionic shims                |

### Hardware Acceleration

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| GPU acceleration (Vulkan)                     | v1.0        | Mesa PowerVR Vulkan driver for Imagination PowerVR DXT-72-2304           |
| GPU acceleration (OpenGL ES)                  | v1.0        | Mesa PowerVR Gallium3D driver                                            |
| VPU (Video Processing Unit)                   | v1.0        | Hardware video encode/decode via VA-API (Tensor G5 codec)                |
| ISP (Image Signal Processor)                  | v1.0        | Tensor G5 ISP pipeline for photo/video processing                        |
| Display compositing (atomic modesetting)      | v1.0        | Atomic KMS for tear-free rendering at 120 Hz on AMB655X LTPO panel       |
| HDR display support                           | v1.0        | HDR10 output on the AMB655X LTPO OLED display                            |

### Camera

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Camera HAL replacement (libcamera)            | v1.0        | Open-source camera stack replacing Google proprietary HAL                |
| ISP pipeline configuration                    | v1.0        | 3A algorithms (auto-exposure, auto-white-balance, auto-focus)            |
| Multi-camera support                          | v1.0        | Rear wide + ultrawide + telephoto; front selfie camera                   |
| Video recording (4K)                          | v1.0        | Hardware-encoded video with audio                                        |
| Night mode / computational photography        | v1.0        | Basic multi-frame noise reduction (optional, may slip to v1.1)           |

### Sensor Support

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Accelerometer / Gyroscope                     | v1.0        | IIO sensor driver → iio-sensor-proxy → Phosh auto-rotate                 |
| Proximity sensor                              | v1.0        | Proximity → screen-off during calls                                      |
| Ambient light sensor                          | v1.0        | ALS → automatic brightness adjustment in Phosh                           |
| Magnetometer (compass)                        | v1.0        | Compass heading for navigation PWAs                                      |
| Barometer                                     | v1.0        | Pressure sensor for altitude/elevation                                   |
| Hall effect sensor                            | v1.0        | Flip cover detection                                                      |
| Fingerprint sensor (Goodix gf3636)            | v1.0        | libfprint integration for Phosh lockscreen                               |

### Power Management

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Suspend-to-idle (s2idle)                      | v1.0        | System enters low-power state when idle; wakes on modem/input            |
| Deep sleep / suspend-to-RAM (s2ram)           | v1.0        | Deeper sleep state if Tensor G5 firmware supports it                      |
| CPU frequency scaling (cpufreq/schedutil)    | v1.0        | EAS (Energy-Aware Scheduling) with Tensor G5 energy model                |
| GPU frequency scaling                         | v1.0        | Dynamic GPU clocking based on rendering load                             |
| Modem power management                        | v1.0        | Samsung Exynos 5500 enters low-power mode when idle; woken for calls/SMS |
| WiFi power saving                             | v1.0        | 802.11 power save mode; wake-on-WLAN via Broadcom BCM4390                |
| Battery percentage and charging status        | v1.0        | MAX1720x charge counter → upower → Phosh battery indicator               |
| Thermal throttling                            | v1.0        | Thermal zone monitoring and CPU/GPU throttling via MAX77729 + MAX77826   |

### Audio

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Audio routing stability                       | v1.0        | Reliable switching between earpiece, speaker, headphone, BT via Cirrus Logic CS35L45 + CS42L43 |
| Call audio quality (echo cancellation)        | v1.0        | AEC via DSP or software fallback                                          |
| Bluetooth calling (HFP 1.8)                   | v1.0        | Wideband speech over Bluetooth                                            |
| USB-C audio accessory support                 | v1.0        | USB Audio Class 3.0 for USB-C headphones/DACs                            |
| FM Radio (if supported by modem)              | v1.0        | Low priority; deferred to v1.1                                            |

### Security

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Full-Disk Encryption (FDE)                    | v1.0        | dm-crypt with LUKS2; key derived from user PIN/password                  |
| Verified Boot with user-controlled keys       | v1.0        | AVB signing (boot header v4) with user-generated keys; lockscreen verifies boot chain |
| Secure Boot (optional)                        | v1.0        | Titan M3 Secure Boot if Pixel 10 Pro XL supports it                       |
| MAC / SELinux policy (optional)               | v1.0        | Mandatory access control for system services; deferred if too complex    |
| AppArmor profiles for system services         | v1.0        | Per-service confinement profiles                                         |

### App Distribution

| Task                                          | Target       | Description                                                              |
|-----------------------------------------------|:-----------:|--------------------------------------------------------------------------|
| Nuxel App Catalog                             | v1.0        | Curated, verified PWA catalog with capability auditing                   |
| One-tap PWA install from catalog              | v1.0        | Catalog → nuxel-home integration for seamless install                    |
| PWA equivalent recommendations                | v1.0        | For popular Android/iOS apps, suggest PWA equivalents                    |
| Community submission and review               | v1.0        | Developer-submitted PWAs with community review process                   |

### Deliverables

1. **v1.0 release image** — Complete daily-driver capable image
2. **Mainline kernel defconfig and DT** — Contributed upstream; Tensor G5 (gs501)/mustang DT in mainline
3. **App catalog (public)** — Web-based catalog at catalog.nuxel.org
4. **Full documentation suite** — Architecture, build guide, PWA dev guide, bridge API spec, contribution guide
5. **CI/CD pipeline** — Automated nightly builds, kernel testing, regression suite

---

## Risk Analysis

### Critical Risks

| Risk                                         | Impact | Likelihood | Mitigation                                                              |
|----------------------------------------------|:------:|:----------:|-------------------------------------------------------------------------|
| **Modem firmware blobs unavailable**         | High   | Low        | Exynos 5500 modem firmware is in factory images. Risk is closed-source and cannot be modified, not that it's unavailable. Accept binary blob for modem; focus open-source effort above the firmware interface. |
| **Display driver complexity (MSM DPU)**      | High   | Medium     | Tensor G5 DPU driver is partially upstream. Missing features: DSC, HDR, AMB655X LTPO panel-specific init sequence. Mitigation: contribute driver patches upstream; fall back to vendor kernel path if delayed. |
| **Camera ISP documentation gaps**            | High   | High       | Tensor G5 ISP registers are poorly documented. libcamera support for gs501 is nascent. Mitigation: collaborate with libcamera community; prioritize basic capture over advanced ISP features. |
| **Power management (suspend/resume)**        | High   | Medium     | Tensor G5 suspend/resume is complex (DSP firmware save/restore). Mainline support is immature. Mitigation: implement s2idle first; deep sleep as stretch goal. |
| **GPU mainline status (PowerVR DXT-72-2304)** | Medium | Medium     | Mesa PowerVR support for DXT-72-2304 is functional but may lag behind vendor performance. Mitigation: invest in PowerVR Mesa testing and benchmarks; acceptable performance gap for v1.0. |

### Moderate Risks

| Risk                                         | Impact | Likelihood | Mitigation                                                              |
|----------------------------------------------|:------:|:----------:|-------------------------------------------------------------------------|
| **Audio DSP firmware loading**               | Medium | Medium     | Cirrus Logic CS35L45 + CS42L43 firmware is signed; may require specific loading sequence. Mitigation: use vendor firmware; invest in mainline remoteproc support. |
| **WiFi/BT firmware compatibility**           | Medium | Low        | brcmfmac supports Broadcom BCM4390 with board files from vendor. Mitigation: extract NVRAM and board files from vendor partition. |
| **UFS storage performance**                  | Medium | Low        | UFS 4.0 driver is upstream and stable. Minimal risk.                    |
| **Battery charging (PMIC)**                  | Medium | Medium     | MAX77729 + MAX77826 PMIC driver is partially upstream. MAX1720x charger fuel gauge may need work. Mitigation: use vendor kernel PMIC driver initially. |
| **PWA ecosystem maturity**                   | Low    | Medium     | Some categories (banking, advanced camera editing) lack mature PWAs. Mitigation: encourage PWA development; ship reference implementations. |
| **Community and contributor bandwidth**      | Medium | High       | Small initial team. Mitigation: thorough documentation to lower contribution barrier; clear "good first issue" tags. |
| **Fingerprint sensor (Goodix gf3636)**       | Medium | Medium     | Goodix gf3636 driver for mainline is nascent. libfprint may need new backend. Mitigation: initial fallback to vendor kernel driver path. |
| **NFC (NXP SN220)**                          | Low    | Medium     | NXP SN220 NFC controller requires firmware and driver. Mitigation: target Beta; use vendor driver initially if needed. |

### Mitigation Strategies Summary

1. **Vendor kernel as permanent fallback** — If mainline kernel support for a hardware subsystem is delayed, that subsystem remains on the vendor kernel path. The architecture is designed for progressive migration, not flag-day cutover.
2. **Collaborate with upstream communities** — postmarketOS, Phosh, ModemManager, PipeWire, libcamera, and Mesa PowerVR all benefit from Nuxel's work. Contribute patches upstream to share maintenance burden.
3. **Prioritize core phone functionality** — A smartphone that can't make calls or send SMS is not a phone. Telephony and messaging always receive top priority.
4. **Accept binary firmware blobs** — Google Tensor G5 DSP firmware, Exynos 5500 modem firmware, and Broadcom BCM4390 WiFi/BT firmware are distributed as signed binary blobs. Nuxel uses these from factory images. The goal is to have everything *above* the firmware interface be open source.
5. **Phased rollouts** — Each milestone's features can be shipped incrementally. Nightly builds allow early adopters to test and report issues before stable releases.

---

## Post-v1.0 Vision

Beyond v1.0, long-term goals include:

- **Additional device support** — Port to other Google Tensor G5 (gs501) devices and potentially gs601/gs701
- **Convergence** — Desktop mode via USB-C DisplayPort with adaptive Phosh layout
- **Multi-user** — Full multi-user support with per-user PWA installs and data isolation
- **Flatpak app distribution** — Native Flatpak apps (not just PWAs) via Nuxel catalog, for when PWA isn't the right fit
- **Mobile Linux app ecosystem** — Encourage development of adaptive GTK4/libadwaita apps that work on both Nuxel and desktop Linux
- **Cellular privacy** — Modem isolation, call/SMS metadata minimization, VPN-by-default
- **Open hardware exploration** — Investigate feasibility of RISC-V mobile SoC for future reference device

---

<!-- Reconciliation & code-size accuracy owned by the Repo state audit & doc reconciliation build group (briq-01-audit). Single source of truth for all measured counts: docs/repo-audit.md. -->
