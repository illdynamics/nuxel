# A51 — Preflight & Root Cause (Wi-Fi)

Executed read-only-first on the physical Samsung Galaxy S10+ (SM-G975F,
beyond2lte, Exynos 9820) over the USB live console on 2026-10-22 (CEST).
Every command was a capability-selected, framed, SHA-256-verified console
round-trip. No flashing, no partition writes, no kernel/bootloader changes.

## Device identity (live)
| Field | Value |
|---|---|
| Kernel | `Linux fedora 4.14.253 #15 SMP PREEMPT … aarch64` |
| OS | Fedora Linux 43 (Forty Three) |
| RAM | 7.2 GiB, 8 CPUs |
| Rootfs | `/dev/sda31` 3.9G, 56% used, 1.7G free |
| Session | Wayland compositor **phoc** (root), `XDG_RUNTIME_DIR=/run/nuxel-wayland`, `wayland-0` |

## Root cause — confirmed against the LIVE checkout
The running bridge is `/usr/lib/nuxel/nuxel-bridge/bridge.py` (launched by the
`/usr/bin/nuxel-bridge` shim). Its sha256 was `e61f844c…`, byte-identical to
`services/nuxel-bridge/src/bridge.py` at HEAD. That live file contained:

```python
def connect_wifi(self, ssid, password, security):
    ...
    mgr.AddAndActivateConnection(dbus.Dictionary(profile,signature='sa{sv}'), path, '/new')
```

`scan_wifi()` already returned a real `ap_path` per AP, but `connect_wifi()`
accepted only `(ssid, password, security)` and **discarded** it, then passed the
literal `/new` as `specific_object`. `/new` is not an access point object path,
so NetworkManager rejected every activation with:

```
org.freedesktop.NetworkManager.Device.SpecificObjectNotFound:
The access point /new was not in the scan list.
```

## Device / AP mapping (live D-Bus trace)
- Wi-Fi devices: `wlan0` = `/org/freedesktop/NetworkManager/Devices/2`, `wlan1` = `/org/freedesktop/NetworkManager/Devices/3` (both type 2).
- `_wifi_device()` picks the first type-2 device → wlan0 (`/Devices/2`).
- wlan0 `GetAccessPoints()` returns real object paths, e.g. `/org/freedesktop/NetworkManager/AccessPoint/{1,2,3,4,5,6,9,…}`; wlan1 returns `/…/{27,28,29,…}`.
- Strongest observed AP: SSID `Undetektable` (bytes `556e646574656b7461626c65`), BSSID `32:01:24:17:CF:1F`, 2437 MHz, WPA3(SAE), AP `/org/freedesktop/NetworkManager/AccessPoint/3`.

## PolicyKit (already correct — not the fault)
`/etc/polkit-1/rules.d/50-nuxel-bridge-network.rules` on the device already
allows the `nuxel-bridge` service account: `enable-disable-wifi`, `wifi.scan`,
`network-control`, `settings.modify.system`. The bridge therefore *was*
authorised to create and activate connections; the request reached NM and was
rejected only because `/new` was not a valid AP path. (Note: the repo's
`services/nuxel-bridge/polkit/…rules` is an older copy; the live rule is the
A47-corrected one and was intentionally left untouched.)

## Frontend is already ahead of the backend
The deployed `pwa/nuxel-apps/settings/wifi-settings.js` (sha256 `83bb596e…`)
already sends `{ssid, password, security, ap_path, bssid, device, ssid_hex}`
and renders a `wifi_stage`, but the backend never returned `bssid/frequency/
ssid_hex` and never consumed `ap_path`. A51 completed the backend contract to
match the frontend, and synced the repo copy of `wifi-settings.js` to the
deployed version.
