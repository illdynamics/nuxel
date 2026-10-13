# Nuxel Linux Phone OS Design Notes

****Status:** v0.2.0 production  
****Last updated:** 2026-05-10  
**Primary direction:** Graphene-style security principles, but **not Android-based**  
**Hard rule:** no Android runtime, no APK dependency, no Play Store, no Play Services, no AOSP app layer, no Waydroid as a required compatibility layer.

---

## 1. Core thesis

Nuxel should be a hardened, mobile-first Linux operating system that borrows the *security mindset* of GrapheneOS without borrowing Android as the base platform.

The operating system should be:

- Linux-native
- mobile-first
- security-first
- privacy-respecting
- app-sandboxed by default
- PWA-first for most user-facing applications
- native Linux app capable for system apps and high-trust apps
- independent of Android, Google Play, APKs, AOSP userspace, and Android compatibility layers

The goal is not to build “de-Googled Android.” The goal is to build a real Linux phone OS with a strict app model and a hardened trust chain.

---

## 2. Chosen UI direction

### Recommendation: Phosh + GTK/libadwaita first

Nuxel should initially use the **Phosh / GTK / libadwaita** route rather than KDE Plasma Mobile as the primary system shell.

Reasoning:

- Phosh is explicitly designed for mobile devices running mainline Linux.
- Phosh has a smaller, more appliance-like feel than KDE Plasma Mobile.
- A security-first phone OS benefits from a tighter, more boring, less tweak-heavy shell.
- GTK/libadwaita is a good fit for simple, adaptive, GNOME-style system applications.
- Phosh already includes mobile-relevant components such as a shell, compositor, on-screen keyboard, mobile settings, calls, SMS/MMS components, and portal integrations.

### KDE Plasma Mobile position

KDE Plasma Mobile is not rejected permanently. It can be supported later as an alternative user environment or as a sandboxed app/tooling ecosystem, but it should not define the initial Nuxel security model.

For the first serious prototype:

```text
Shell:             Phosh-derived or stock Phosh initially
Compositor:        phoc / wlroots path initially
Core toolkit:      GTK4 + libadwaita
App UX policy:     minimal, locked down, mobile-first
Display server:    Wayland only
```

Short version: **Phosh is the bunker. KDE is the rave cave. Build the bunker first.**

---

## 3. App model

### 3.1 PWA-first

Nuxel should be **PWA-first** for mainstream applications.

PWAs should be treated as first-class apps, not just browser bookmarks. The OS should provide a dedicated hardened web-app runtime.

The Nuxel PWA runtime should provide:

- per-app browser profiles
- per-app storage isolation
- installable icons and launcher entries
- service worker support
- offline-first behavior
- background sync queues where possible
- Web Push / UnifiedPush bridge where possible
- permission prompts for camera, microphone, location, files, notifications, clipboard, sensors, and background behavior
- no global browser extension leakage into app contexts
- strict content isolation
- easy uninstall with full data wipe option

PWAs are the default answer for:

- dashboards
- admin tools
- social clients
- notes
- forums
- marketplaces
- simple communication apps
- cloud services with good web frontends
- internal tools
- music/community tools that do not require deep realtime audio or special hardware access

### 3.2 Native Linux apps

Native apps remain necessary for system-grade, low-level, high-trust, or high-performance tasks.

Native apps should be used for:

- settings
- dialer
- SMS/MMS
- modem tools
- camera
- file manager
- terminal
- password manager / secrets UI
- VPN / firewall UI
- package/store UI
- secure key management
- accessibility tools
- realtime audio / music production tools
- debugging and recovery tools

Initial native app stack:

```text
Toolkit:      GTK4/libadwaita
Language:     Rust, C, Go, or Python depending on component criticality
Packaging:    Flatpak-like model or stricter Nuxel package format
Sandboxing:   mandatory unless explicitly system-trusted
```

---

## 4. No Android dependency

Nuxel must not depend on Android to function.

Explicitly out of scope for the base system:

- Play Store
- Google Play Services
- APK installation
- Android Runtime / ART
- Android app compatibility as a required feature
- Waydroid as a required subsystem
- AOSP userspace as an app foundation
- Firebase-only push assumptions
- Play Integrity / SafetyNet dependency
- Google-only maps, auth, billing, or notification paths

Waydroid may be studied as a compatibility example, but it should not ship as a core Nuxel component. Including it would pull Android back into the trust model through the side door wearing a fake moustache.

Stock Android factory images for the target Pixel may be kept only as an **external device recovery reference**, not as part of Nuxel and not as a runtime dependency.

---

## 5. Sandboxing and permissions

Classic desktop Linux trust assumptions are not acceptable for a hardened phone OS.

Nuxel should use a strict capability model:

- no ambient home directory access
- no raw filesystem access by default
- no network access by default for native apps unless declared and approved
- no background execution by default
- no broad D-Bus access
- no raw device access
- no microphone/camera/location without runtime user consent
- no clipboard spying
- no screenshots or screen recording without explicit permission
- no contact/calendar access without portals
- no “start on boot” without user approval

Recommended primitives:

```text
Linux namespaces
cgroups
seccomp
Landlock
AppArmor or SELinux
bubblewrap-style sandbox construction
xdg-desktop-portals
Wayland-only display isolation
PipeWire permission mediation
nftables/cgroup-based per-app network controls
```

### Portal-first model

Apps should request actions, not broad access.

Bad model:

```text
App receives /home/user/Documents forever.
```

Good model:

```text
User picks one file through a portal. App receives only that handle.
```

Important portals:

- file picker portal
- camera portal
- microphone portal
- location portal
- notifications portal
- contacts portal
- calendar portal
- clipboard portal
- Bluetooth portal
- USB portal
- secrets/keyring portal
- screen share / screen recording portal

---

## 6. OS security architecture

Nuxel should be designed as an immutable, verified, atomic-update mobile OS.

Required properties:

- read-only base OS
- signed system images
- atomic updates
- rollback on failed boot
- rollback protection where hardware allows it
- encrypted user data
- separate user data from system image
- reproducible builds where possible
- minimal privileged services
- locked-down default network surface
- visible security state for the user
- ability to recover safely after a failed flash or update

Possible implementation directions to evaluate:

```text
OSTree-style image deployment
systemd-sysupdate
RAUC
Mender
A/B partitioning concepts
LUKS2 / fscrypt for data encryption
TPM/TEE/hardware-bound keys where possible
```

---

## 7. App distribution

Nuxel needs an app store/repository model that avoids the Linux anti-pattern of users curling random install scripts.

Repository/store requirements:

- signed packages
- signed metadata
- permission manifests
- source links
- reproducible build metadata where possible
- update history
- maintainer identity
- vulnerability status
- no account required for free apps
- privacy-respecting paid app path later
- visible permission changes on update
- easy uninstall and data wipe

The model should feel like:

```text
F-Droid principles
+ Flathub-style distribution mechanics
+ stricter mobile permissions
+ Graphene-like paranoia
+ Linux-native guts
```

---

## 8. Initial development and testing path

### Phase 1: UTM VM on Apple Silicon

Development should begin in a **UTM ARM64 Linux VM** on the MacBook M1.

Reasoning:

- The MacBook M1 is ARM64, matching the architecture family of most Linux phone targets.
- ARM64 Linux VMs run much closer to native speed than x86 emulation on Apple Silicon.
- This is enough to test the OS shape, shell, app model, sandboxing, packaging, and update concepts before dealing with cursed phone hardware.

Initial VM recommendation:

```text
Host:             MacBook M1
VM manager:       UTM
Guest arch:       ARM64 / aarch64
Guest distro:     Fedora ARM64 or Debian ARM64 first
Shell:            Phosh
Display:          Wayland
Resolution:       phone-shaped, e.g. 390x844, 414x896, or 720x1280 portrait
RAM:              4–8 GB
CPU cores:        4
Disk:             40–80 GB
Networking:       shared NAT initially
Shared folders:   disabled for security-mode testing
Clipboard sync:   disabled for security-mode testing
```

### Phase 2: Hardened VM profile

Once the shell and app model work, create a separate VM profile for security architecture testing:

```text
UEFI boot
Secure Boot experiments
signed kernel/initramfs experiments
read-only root filesystem
atomic updates
rollback tests
encrypted user data
software TPM experiments if useful
```

### Phase 3: postmarketOS / aarch64 validation

After the generic ARM64 Linux VM works, test postmarketOS/QEMU paths for mobile-Linux-specific assumptions.

Goal:

- compare Phosh behavior
- compare mobile packages
- inspect device packaging structure
- learn from postmarketOS without becoming dependent on it

### Phase 4: real hardware only after gates pass

Do not start by flashing the phone. First build the OS model in the VM, then validate the target device.

---

## 9. Target physical device

### Intended target device

```text
Device:            Google Pixel 10 Pro XL
Serial number:     58211FDCQ001LA
Hardware version:  MP1.0
Hardware SKU:      G45RY
Codename:          mustang / Google Mustang
CPU family:        ARM64 / aarch64
```

This exact device must be treated as a hardware bring-up target, not as an assumed-ready daily-driver platform.

### Current public feasibility snapshot

Public reporting indicates that Google posted early device-tree patches for booting Pixel 10 family hardware, including:

```text
Pixel 10:          frankel
Pixel 10 Pro:      blazer
Pixel 10 Pro XL:   mustang
```

However, the public state described in November 2025 was very preliminary: barebones device trees, dependent on a yet-unreleased bootloader, booting only to a UART command prompt from an initramfs. That is not a usable phone OS yet.

Therefore, the Pixel 10 Pro XL mustang path is promising but not safe to assume production-ready.

---

## 10. Pixel 10 Pro XL hardware validation checklist

Before attempting a real Nuxel install on the Pixel 10 Pro XL, verify every item below.

### Bootloader and recovery

- Confirm whether this exact unit allows OEM unlocking.
- Confirm whether `fastboot flashing unlock` works.
- Confirm whether the bootloader can be safely relocked with a custom OS signing key.
- Confirm what warning state appears after relock/custom key enrollment.
- Confirm rollback protection behavior.
- Confirm full recovery path to stock firmware.
- Confirm factory image availability for this exact model/SKU.
- Confirm whether flashing wipes data, and document it clearly.

### Kernel and boot chain

- Confirm mainline Linux kernel boot status for `mustang`.
- Confirm whether device-tree patches are upstream, pending, or experimental.
- Confirm whether the required bootloader has been released.
- Confirm whether boot reaches only UART/initramfs or reaches graphical userspace.
- Confirm storage, USB, display, touch, buttons, and thermal basics before any daily-driver attempt.

### Display and input

- Display panel initializes.
- Backlight control works.
- Touchscreen works.
- Orientation works.
- Hardware buttons work.
- Cutout/notch/safe-area handling is mapped.
- On-screen keyboard works.

### Wireless and modem

- Wi-Fi works.
- Bluetooth works.
- Cellular modem initializes.
- SIM/eSIM behavior is understood.
- Calls work.
- SMS works.
- MMS works or is explicitly out of scope.
- Emergency calling behavior is tested according to local law and safe lab procedure.
- GPS/GNSS works.

### Audio, camera, and sensors

- Speaker output works.
- Microphone input works.
- Earpiece works.
- Headset / USB-C audio path works.
- Camera stack status is known.
- Camera ISP status is known.
- Haptics work.
- Accelerometer/gyroscope/proximity/ambient light sensors work.
- Fingerprint reader status is known.
- NFC / secure element status is known.
- UWB status is known or explicitly out of scope.

### Power management

- Charging works.
- Battery reporting works.
- Suspend/resume works.
- Wake from power button works.
- Wake from call/message path works if modem is enabled.
- Idle drain is measured.
- Thermal behavior is measured.
- No runaway modem/GPU/CPU drain.

### Security properties

- Verified boot story is documented.
- User data encryption works.
- Secure wipe works.
- Update rollback behavior works.
- Lock screen protects secrets.
- No debug shells are exposed in production mode.
- Developer mode is visibly different from locked mode.
- Boot state is visible to the user.

Hard gate:

```text
No daily-driver claim until bootloader, display, touch, storage, Wi-Fi, modem, audio, suspend/resume, charging, encrypted data, recovery, and update rollback are proven.
```

---

## 11. VM vs real device scope

### VM can test well

```text
Phosh UX
GTK/libadwaita core app design
PWA runtime behavior
per-app browser profiles
permission prompts
sandboxing
portals
native package model
repository signing
atomic updates
rollback logic
filesystem isolation
network permission model
clipboard policy
screen recording policy
small-screen adaptive layouts
```

### VM cannot prove

```text
Pixel bootloader behavior
real verified boot chain
bootloader relocking
modem/calls/SMS
emergency calling
camera ISP
fingerprint reader
secure element
real battery life
suspend/resume reliability
thermal behavior
touchscreen quirks
haptics
GPS/GNSS
Bluetooth edge cases
real GPU driver behavior
```

Conclusion: **UTM first for architecture; Pixel later for hardware truth.**

---

## 12. Immediate next milestones

### Milestone A: VM bootstrap

- Install UTM on MacBook M1.
- Create ARM64 Linux VM.
- Install Fedora ARM64 or Debian ARM64.
- Install Phosh session.
- Force phone-shaped portrait resolution.
- Disable shared clipboard/folders when testing isolation.

### Milestone B: shell and system app prototype

- Boot into Phosh.
- Verify Wayland-only session.
- Build a minimal settings mockup in GTK/libadwaita.
- Build a minimal launcher entry for a PWA.
- Build a minimal Nuxel “app permissions” UI mockup.

### Milestone C: PWA runtime prototype

- Create per-app isolated browser profile launcher.
- Install one test PWA as a pseudo-native app.
- Test offline cache.
- Test local storage wipe.
- Test camera/mic/location prompt flow.
- Test app uninstall cleanup.

### Milestone D: native sandbox prototype

- Package one tiny GTK app.
- Run it in a sandbox.
- Deny home directory by default.
- Add file-open portal only.
- Test network denied by default.
- Add explicit network permission toggle.

### Milestone E: update prototype

- Create immutable base image concept.
- Add signed update metadata.
- Test atomic update in VM.
- Test rollback after broken update.

### Milestone F: Pixel hardware research

- Confirm exact Pixel 10 Pro XL SKU and unlockability.
- Confirm mainline Linux status for `mustang`.
- Track device-tree patches.
- Track bootloader requirements.
- Track postmarketOS or other mobile Linux porting status.
- Do not flash until recovery path is tested and documented.

---

## 13. Non-goals for the first prototype

- No Android app compatibility.
- No Play Store replacement for APKs.
- No Waydroid integration.
- No attempt to support every Linux desktop app.
- No KDE-first shell.
- No full app store on day one.
- No daily-driver claim.
- No banking-app compatibility promise.
- No government-ID-app compatibility promise.
- No “works on all Pixels” claim.

---

## 14. Design mantra

```text
PWA-first.
Native Linux where needed.
Phosh/GTK for the shell.
Wayland only.
No Android.
No ambient trust.
VM first.
Pixel 10 Pro XL mustang only after hardware gates pass.
```

Build the bunker first. Add the rave lights later.

---

## 15. References checked while drafting

- UTM: ARM64 operating systems on Apple Silicon can run through Apple Hypervisor at near-native speeds; x86/x64 on Apple Silicon uses lower-performance emulation.  
  https://mac.getutm.app/

- Phosh: aims to provide a daily-usable, robust, easy-to-use graphical environment for mobile devices running mainline Linux; includes phosh, phoc, keyboard, calls, chatty, mobile settings, and portal components.  
  https://phosh.mobi/about/

- MDN Progressive Web Apps: PWAs are built using web platform technologies but can provide platform-app-like UX, run across platforms from one codebase, be installable, work offline/background, and integrate with the device.  
  https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps

- Flatpak concepts: apps run in isolated sandboxes; access to files, network, graphics sockets, bus subsystems, and devices must be explicitly granted; portals provide controlled host interaction.  
  https://docs.flatpak.org/en/latest/basic-concepts.html

- Google Store Pixel 10 Pro/Pro XL page: confirms Pixel 10 Pro XL product family, Pixel 10 Pro XL size, Tensor G5, Pixel security/update marketing, dual-SIM/5G information.  
  https://store.google.com/nl/product/pixel_10_pro

- NieuweMobiel Pixel 10 Pro XL specs: lists article code `G45RY` and codename `Google Mustang`; also lists Android 16, 7 years of security updates/upgrades, Tensor G5, 16 GB RAM, USB-C, Wi-Fi 7, Bluetooth 5.3, NFC, UWB, sensors, and battery specs.  
  https://www.nieuwemobiel.nl/Google-Pixel-10-Pro-XL/Specificaties

- Google factory images page: factory images restore Nexus/Pixel devices to original firmware; Google notes that flashing factory images erases data and recommends relocking the bootloader after use.  
  https://developers.google.com/android/images

- Phoronix report, 2025-11-11: Google posted preliminary device-tree patches for Pixel 10, Pixel 10 Pro, and Pixel 10 Pro XL `mustang`; described as barebones, dependent on a yet-unreleased bootloader, and only reaching UART/initramfs rather than a useful end-user system.  
  https://www.phoronix.com/news/Google-Pixel-10-Google-DTs
