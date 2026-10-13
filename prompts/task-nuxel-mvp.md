You are building Nuxel - a Linux-only, PWA-first phone operating system targeting the Google Pixel XL 10. No Android userspace, no Play Store dependencies. This is a staged build toward an MVP that can actually be flashed and tested.

## CONTEXT FROM TWO DOCUMENTS

The repository contains two documents that define the project:
1. `Fonux, NuDroid, and the Best Path to a Linux-Only PWA-First Smartphone.md` - Full analysis of distro strategy, hardware, app model, roadmap, risks
2. `Building a Post-Android Phone OS on Existing Android Hardware.pdf` - Technical build strategy: hybrid approach with staged migration from vendor kernel reuse toward mainline Linux

Key architectural decisions from these documents:
- Base distro: postmarketOS-style (Alpine-based) with Phosh shell
- Kernel strategy: Start with vendor kernel via Halium/libhybris bridge, then mainline LTS (6.12 preferred, 6.6 fallback) as end state
- App model: PWA-first for general apps, native for telephony/SMS/contacts/camera/settings
- Packaging: Native distro packages for core system, Flatpak for first-party web shells, installed PWAs for third-party
- Core services: ModemManager (telephony), NetworkManager, PipeWire (audio/video), GeoClue (location), xdg-desktop-portal
- No Android app compatibility layer needed (no Waydroid, no Android AppSupport)
- Boot chain: fastboot/fastbootd, handle AVB, A/B slots, dynamic partitions on Pixel hardware

## PROJECT NAME: Nuxel

## TARGET HARDWARE: Google Pixel XL 10 (gen10 / panther-family)

## WHAT TO BUILD - STAGED MVP

### Phase 1: Project Foundation & Structure
Create the complete Nuxel project repository structure under /Users/wicked/x/nuxel/:
```
nuxel/
├── README.md
├── LICENSE
├── docs/
│   ├── architecture.md
│   ├── device-setup.md
│   ├── pwa-model.md
│   ├── build-guide.md
│   └── roadmap.md
├── images/
│   ├── build.sh
│   ├── config/
│   │   ├── device-info.yml
│   │   └── packages.yml
│   └── hooks/
├── shell/
│   ├── nuxel-shell/
│   │   ├── nuxel-settings/
│   │   ├── nuxel-dialer/
│   │   ├── nuxel-messages/
│   │   └── nuxel-contacts/
│   └── config/
├── services/
│   ├── nuxel-bridge/
│   │   ├── src/
│   │   │   ├── bridge.py
│   │   │   ├── capabilities.py
│   │   │   └── api.py
│   │   ├── dbus/
│   │   │   └── org.nuxel.Bridge.conf
│   │   └── systemd/
│   │       └── nuxel-bridge.service
│   └── nuxel-notifications/
├── pwa/
│   ├── nuxel-home/
│   │   ├── index.html
│   │   ├── manifest.json
│   │   ├── sw.js
│   │   ├── css/
│   │   ├── js/
│   │   └── icons/
│   ├── nuxel-apps/
│   │   ├── mail/
│   │   ├── calendar/
│   │   ├── notes/
│   │   ├── files/
│   │   └── camera-gallery/
│   └── flatpak/
│       ├── org.nuxel.Home.json
│       ├── org.nuxel.Mail.json
│       └── org.nuxel.Calendar.json
├── boot/
│   ├── boot.img/
│   ├── initramfs/
│   └── flash.sh
├── kernel/
│   ├── patches/
│   └── defconfig
├── firmware/
│   └── manifest.yml
└── ci/
    ├── Dockerfile
    └── build-pipeline.yml
```

### Phase 2: Core System Services Specification
Design and spec out the core services:
- **nuxel-bridge**: D-Bus service that mediates between PWAs and native phone functions. Clean capability model: call initiate/end, SMS send/receive, contact lookup, geolocation handoff, notification bridge, camera capture request. No raw modem access, no AT commands, no unrestricted system-bus exposure.
- **nuxel-notifications**: Notification daemon that bridges system notifications to PWA notification API
- **Service dependency graph** showing ModemManager → nuxel-bridge → PWAs

### Phase 3: PWA Runtime & First-Party Apps
Build actual working PWA code:
- **nuxel-home**: Mobile-first PWA launcher with app grid, search, recent apps. Installable. Offline-capable via service worker. Communicates with nuxel-bridge for phone status.
- **nuxel-mail**: Email PWA (IMAP/SMTP client)
- **nuxel-calendar**: Calendar PWA with CalDAV support
- **nuxel-notes**: Notes PWA with markdown support, local storage + sync
- **nuxel-files**: File browser PWA
- Each PWA must have: manifest.json with proper icons, service worker for offline support, responsive mobile UI

### Phase 4: Build & Flash Infrastructure
- Build scripts that produce flashable images
- Flash script for Pixel XL 10 using fastboot
- Bootloader unlock guide
- Recovery/fallback documentation
- CI pipeline definition

### Phase 5: Native Shell Apps (Skeleton)
Create skeleton/stub native apps for:
- Dialer (GTK/libadwaita, ModemManager D-Bus integration)
- Messages (SMS/MMS, ModemManager D-Bus)
- Contacts (evolution-data-server or custom)
- Settings (GSettings/dconf based)

## RULES
1. Build EVERY file with real, functional code - not placeholders or TODOs
2. The PWA apps must be fully functional HTML/CSS/JS with working service workers
3. The bridge service must have real D-Bus integration code
4. All configs must reference actual Pixel XL 10 hardware
5. Write proper documentation that someone could actually follow to flash a Pixel XL 10
6. Continue building until all 5 phases are complete
7. Do not stop early - keep going until every file exists with real content
8. The goal is an MVP that can be tested: someone should be able to read the docs, run the build scripts, and flash their phone

Start building now. Go through all 5 phases systematically. Create every file with real content. Do not stop until complete.

---

<!-- Task reconciliation owned by the Repo state audit & doc reconciliation build group (briq-01-audit). See docs/repo-audit.md for the measured single source of truth. -->
