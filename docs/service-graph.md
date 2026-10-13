# Service Dependency Graph

```
┌────────────────────────────────────────────────────────────┐
│                      NUXEL SYSTEM                            │
├────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ nuxel-   │  │ nuxel-   │  │ nuxel-   │  │ nuxel-   │   │
│  │ Dialer   │  │ Messages │  │ Contacts │  │ Settings │   │
│  │ (Native) │  │ (Native) │  │ (Native) │  │ (Native) │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘   │
│       │              │             │                        │
│  ┌────▼──────────────▼─────────────▼──────────────────┐    │
│  │                 nuxel-bridge                          │    │
│  │         D-Bus service (org.nuxel.Bridge)              │    │
│  │         Capability model, PWA<->native mediation      │    │
│  └────┬──────────────┬─────────────┬──────────────────┘    │
│       │              │             │                        │
│  ┌────▼────┐  ┌──────▼──────┐ ┌───▼────────┐              │
│  │Modem-   │  │Network-     │ │  GeoClue   │              │
│  │Manager  │  │Manager      │ │  Location  │              │
│  │Telephony│  │WiFi/Ethernet│ │  Services  │              │
│  │SMS/MMS  │  │Connectivity │ │            │              │
│  └────┬────┘  └──────┬──────┘ └────────────┘              │
│       │              │                                     │
│  ┌────▼────┐  ┌──────▼──────┐                              │
│  │Exynos   │  │  Broadcom   │                              │
│  │5500     │  │  BCM4390    │                              │
│  │Modem    │  │  WiFi/BT    │                              │
│  └─────────┘  └─────────────┘                              │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   PWA LAYER                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │   │
│  │  │ nuxel-   │ │ nuxel-   │ │ nuxel-   │ │ nuxel- │ │   │
│  │  │ Home     │ │ Mail     │ │ Calendar │ │ Files  │ │   │
│  │  │(Launcher)│ │(IMAP)    │ │(CalDAV)  │ │(Files) │ │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┘ │   │
│  │       │             │            │                   │   │
│  │  ┌────▼─────────────▼────────────▼────────────────┐ │   │
│  │  │           Flatpak Sandbox                        │ │   │
│  │  │    WebKitGTK WebView + Service Worker            │ │   │
│  │  │    xdg-desktop-portal → nuxel-bridge              │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                SYSTEM SERVICES                       │   │
│  │  PipeWire (Audio)  |  BlueZ (Bluetooth)              │   │
│  │  Upower (Power)    |  elogind (Session)              │   │
│  │  polkit (Auth)     |  iwd (WiFi daemon)              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              KERNEL + HARDWARE                       │   │
│  │  Mainline 6.12 LTS (android-gs-mustang-6.12)        │   │
│  │  → Mainline 6.12 LTS (end state)                    │   │
│  │  DRM/KMS (GS501) | MHI (Modem) | ALSA (Audio)         │   │
│  │  PowerVR DXT-72-2304 (PowerVR Rogue) | IIO (Sensors)               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

## Service Startup Order

```
1. dbus                   (message bus)
2. udev                   (device management)
3. elogind                (session management)
4. modemmanager           (modem hardware init)
5. networkmanager + iwd   (network connectivity)
6. pipewire + wireplumber (audio services)
7. bluetooth              (BT hardware init)
8. geoclue                (location services)
9. upower                 (power management)
10. nuxel-bridge          (PWA-to-native bridge, waits for modem)
11. nuxel-notifications   (notification daemon)
12. phoc + phosh          (display server + shell)
13. flatpak PWAs          (launched on demand)
14. nuxel-{apps}          (native apps, launched on demand)
```

## Dependency Matrix

| Service | Requires | Provides |
|---------|----------|----------|
| dbus | kernel | IPC bus |
| udev | kernel | Device detection |
| modemmanager | dbus, udev, kernel(MHI) | Telephony, SMS |
| networkmanager | dbus, kernel | WiFi, Ethernet |
| nuxel-bridge | dbus, modemmanager, networkmanager, geoclue | PWA API |
| nuxel-notifications | dbus, nuxel-bridge | Notifications |
| phoc | dbus, kernel(DRM) | Wayland compositor |
| phosh | phoc, nuxel-bridge | Mobile shell |
