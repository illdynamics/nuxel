# Nuxel v0.8.5-beta — live fix report

Date: 2026-11-15 · Device: S10+ `beyond2lte` · Kernel 4.14.253 (vendor) ·
Deployed over the Wi-Fi SSH console and the USB-ECM console (`10.15.19.1`).

This release is a **repair release**: every item below was reproduced on the
running phone, fixed in the repository, deployed live and re-checked. Where the
live check could not complete, the limitation is stated instead of claimed.

## Fixed

### 1. Flatpak apps did not start (Stremio, Signal, …)
`/run/user/1000/.flatpak` was owned by `root:root`, so Flatpak (uid 1000) failed
with `Unable to lock …/.flatpak/<app>/.ref: Permission denied` before the app's
first instruction. `nuxel-session.sh` and
`flatpak_provider.ensure_flatpak_runtime_dirs()` now create/repair that tree for
the session user (no symlink following). Live: sandbox launches; Stremio and
Signal get single-instance guards so a double tap cannot hit `EADDRINUSE :11470`.

### 2. Messenger microphones ("sped-up robot", Signal dead)
`--filesystem=/run/user/0/pulse:/run/flatpak/pulse` is invalid for Flatpak 1.16
(silently ignored), while `--socket=pulseaudio` creates an empty private
`/run/flatpak/pulse` that was exported as `PULSE_SERVER`. The provider now maps
the live session socket onto that path with three explicit mounts. Live proof:
`parec` inside the sandbox recorded 393 KB from the S10+ mic with the launcher's
exact argv; `pactl info` answered.

### 3. Tethering and hotspot forwarding
`nuxel_app_firewall` forward chain (priority −100, policy drop) ran before the
tether/hotspot tables (−50/−49) and contained no allows; its drop-log was the
first rule and shadowed accepts. It now accepts the tether/hotspot interfaces
and subnets and logs last. `ip_forward` is durable
(`/etc/sysctl.d/90-nuxel-tether.conf`), the tether provider sets loose
`rp_filter` and no longer writes back a stale value on stop.

### 4. Hotspot from the app
`network_manager.hotspot_*` used `nmcli device wifi hotspot`, which cannot work
on this image (no udev → no managed phy). It now drives the hostapd+dnsmasq owner
`/usr/libexec/nuxel/nuxel-hotspot`, persists the owner's SSID/password and
reports the real state. The test AP **NuxNet** (`Setyup34#`) is running on
`wlan1` with NAT on `wlan0` and `ip_forward=1`.

### 5. Idle CPU / jank
- Broadcom DeX PCIe link (`14E4:4475`) was re-linking ~4×/s; remove+rescan ended
  it. Softirq 2000 → 27 ticks/10 s, kernel log ~3200 lines/s → ~0.
- Removed stale debug nftables tables from an earlier session.
- Launcher/drawer: delegated icon load/error handling (no per-tile inline
  handlers), CSS custom-property tint, deferred sweeps.
- Settings: no drop-shadow filter on the live pattern stroke; visible-only
  polling.

### 6. Double GTK/Flatpak icons
The fallback glyph behind partially transparent app icons is now unpaintable for
external icons (origin-tagged wells, CSS + node removal) and the coloured tile
backdrop is dropped. Verified in a headless render against the real CSS/assets.

### 7. Blue rectangle after power-menu lock
Transient OSD/power-menu cards are hidden on every lock transition and while the
lock glass is up.

## Component state

`final-summary.md` is rewritten from the live device: mobile networking, NFC,
auto-rotate sensors, fingerprint and camera are documented with exact current
evidence and the remaining work.

## Regression contracts

`tests/pwnage_v085/test_v085_live_fixes.py` — 8 static contracts covering every
fix above (all pass). `tests/pwnage_usbnet/test_usb_tether_provider.py` updated
for the new shared-forwarding stop semantics (10/10 pass).
