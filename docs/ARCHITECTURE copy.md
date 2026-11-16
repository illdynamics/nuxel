# Nuxel Architecture

This document is the canonical high-level architecture reference. The README
keeps the product overview; release-by-release changes live in
[RELEASE-NOTES.md](RELEASE-NOTES.md) and [CHANGELOG.md](CHANGELOG.md).


```text
┌──────────────────────────────────────────────────┐
│  Flatpak-sandboxed apps (Bubblewrap)             │
│  PWA apps        — WebKitGTK, isolated profiles  │
│  Native apps     — GTK4/libadwaita (C/Python)    │
├──────────────────────────────────────────────────┤
│  nuxel-home launcher                             │
│  nuxel-bridge (D-Bus capability mediator)        │
│  nuxel-portal (GTK4 consent dialogs)             │
│  nuxel-notifications (FDO bridge)                │
├──────────────────────────────────────────────────┤
│  Sandbox: namespaces + seccomp + Landlock        │
│          + AppArmor + nftables                   │
├──────────────────────────────────────────────────┤
│  Phosh + phoc compositor (Wayland)               │
├──────────────────────────────────────────────────┤
│  ModemManager | NetworkManager | PipeWire        │
│  GeoClue | xdg-desktop-portal                    │
├──────────────────────────────────────────────────┤
│  Linux 6.12 LTS (per-device defconfig/patches)   │
│  dm-verity system + A/B slots + AVB              │
├──────────────────────────────────────────────────┤
│  Hardware targets (see Multi-Device Targets):    │
│  Google Pixel 10 Pro XL (mustang)                │
│  Samsung Galaxy S10+     (beyond2lte)            │
│  Motorola Moto G7 Power  (ocean)                 │
└──────────────────────────────────────────────────┘
```


## Component ownership

| Layer | Owner | Responsibility |
|---|---|---|
| Launcher / shell | `pwa/nuxel-home`, `shell/nuxel-home-native` | UI, app launch, immersive chrome, lockscreen |
| Capability mediation | `services/nuxel-bridge` | D-Bus + HTTP RPC, allow-listed actions, status providers |
| GUI remote access | `services/nuxel-remote-desktop` + `system.remote-desktop` | XRDP TCP 13389 (separate X11) and wayvnc TCP 15900 (current Phoc session), OFF by default |
| Console Tri-Link | `services/nuxel-bridge/src/tri_link_status.py`, `pwa/nuxel-apps/console*` | Serial / Wi-Fi SSH / USB SSH status; read-only phone-side truth |
| USB gadget networking | `tools/beta/live/nuxel-usb-net.py`, host adapter | Mode-aware capability and transaction helper; never mutates configfs without safe gates |
| Remote-access policy | `configs/nuxel/security/remote-access.json` | Canonical ports, bind mode, authentication and transport policy |
| Firewall / permissions | `services/nuxel-firewall`, `services/nuxel-permd` | Explicit policy surfaces; no silent allow rules |
| Hardware services | `services/nuxel-*`, `kernel/`, `device/` | Audio, rotation, modem, NFC, camera, GNSS and device bring-up |

## Remote access architecture

```text
Owner LAN (trusted WLAN IPv4 only)
   │
   ├── TCP 13389 ──► xrdp (TLS 1.2/1.3) ──► xrdp-sesman ──► xorgxrdp X11
   │                   PAM user nuxel                      separate session
   │
   └── TCP 15900 ──► wayvnc (PAM + VeNCrypt TLS/RSA-AES)
                       │
                       └── wlr-screencopy + virtual pointer/keyboard
                           └── the ACTIVE Phoc/Wayland phone session
```

* Both services are OFF by default and are started only by an explicit owner
  action through the fixed-argv privileged helper.
* Listeners bind to the current trusted WLAN IPv4 address, not `0.0.0.0`.
* XRDP is a *separate* X11 desktop. VNC mirrors the *current* Phoc session.
* No SSH tunnel is required on the owner LAN. Neither service may be exposed to
  the public Internet.

## USB Tri-Link architecture

The phone-side gadget is an ACM serial console plus, when a validated mode
exists, one network function. NACM teardown panicked the recorded 4.14.253
vendor kernel; the runtime is therefore mode-aware and fails closed. See
[REPORT-USBNET.md](REPORT-USBNET.md) for the current evidence and next step.

```text
host ── USB ──► [CDC-ACM serial: recovery console, always preserved]
                  [NCM: BLOCKED_KNOWN_PANIC on 4.14.253]
                  [RNDIS: compiled, NEEDS_VALIDATION]
                  [ECM/ECM-subset/EEM: not compiled]
```

## Notification, icon-origin and Back-to-Home contracts (PWNAGE-93000)

- **One notification store:** `nuxel-notifications.service` owns
  `org.nuxel.Notifications` and `/var/lib/nuxel/notifications.json`. Native GTK
  and Flatpak/portal traffic arrives through one `--session` FDO relay per real
  session bus; relays forward to the system hub and never create a second store.
- **Badge semantics:** unread, non-archived reminders. Read reminders remain in
  expanded Quick Settings; archive hides them from the active list but keeps the
  durable record.
- **Icon origin:** Nuxel-owned apps use Nuxel artwork; GTK/RPM apps use
  `/api/v1/apps/icon/<id>` (resolved from the real desktop entry); Flatpak apps
  use their export icon. The PWA keeps exactly one image node per loaded tile.
- **Back to Home:** short Back first gives overlays/keyboard/in-app history
  precedence. An app with no verified adapter is minimized (not killed) and
  Home is activated. The bridge clears fullscreen/maximized state, settles, and
  verifies that no non-Home toplevel remains active before reporting success.
- **Edge screen:** the curved panel and edge-aware `sec_ts` driver exist, but no
  Nuxel edge panel/lighting/gesture is implemented yet. See `REPORT-EDGE.md`;
  v1 is a userspace PWA/bridge feature and needs no reflash.
