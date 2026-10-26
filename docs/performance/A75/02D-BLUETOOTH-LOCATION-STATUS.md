# A75 — Bluetooth and Location Status (truthful backend verdicts)

## Bluetooth — BLOCKED_HARDWARE (evidenced)
The provider contract now works and returns a precise, structured result instead
of a generic missing-provider error.

Live readback (`BluetoothGetStatus` / `BluetoothSetPowered`):
```
state: "service_unavailable"
adapter_present: false
hci_devices: []
kernel_bt_driver: "bcm43xx"
rfkill_present: true
rfkill_soft_blocked: true
rfkill_hard_blocked: false
rfkill_names: ["bcm43xx Bluetooth"]
detail: "no hci0 registered (no BlueZ adapter); kernel BT controller driver:
         bcm43xx (controller never registers hci0: firmware/transport);
         rfkill soft-blocked"
error (on set-powered): "NO_ADAPTER"
```

Evidence:
- `bluez 5.87` is installed and `bluetooth.service` is active/running.
- `/sys/class/bluetooth/` is **empty** (no `hci0`).
- `/proc/config.gz` reports the kernel has a `bcm43xx` BT controller driver,
  but the controller never registers `hci0` (firmware/transport). This is a
  genuine downstream-kernel/vendor-firmware limitation, not a bridge defect.
- Enabling is **not faked**: `BluetoothSetPowered(true)` returns
  `success: false, error: "NO_ADAPTER"` and readback stays `powered: null`.

No fix was attempted at kernel/firmware level (out of scope for this
userspace-only mission; flashing/DTB changes are forbidden).

## Location / GPS — policy toggle VERIFIED, GNSS BLOCKED_HARDWARE
The Location tile controls a persistent **privacy/provider policy**, which is
deliberately separate from a GNSS fix.

Live readback:
```
LocationSetEnabled(true)  -> {success:true, enabled:true, permission_enabled:true}
LocationSetEnabled(false) -> {success:true, enabled:false, permission_enabled:false}
gnss: {present: false, nodes: [], fix_supported: false}
location_fix_available: false
provider: "geoclue2", provider_ready: false
```

Evidence and honest limits:
- The policy file `/var/lib/nuxel/permissions/location-policy.json` round-trips
  correctly (`{"enabled": true/false, "updated": …}`).
- **No satellite fix is ever fabricated** and “Location enabled” is never
  equated with a fix. The test restored the policy to `false`.
- GeoClue2 is installed but the bridge cannot reach it:
  `org.freedesktop.DBus.Error.AccessDenied` when calling
  `org.freedesktop.GeoClue2.Manager.GetClient`. The installed
  `/usr/share/dbus-1/system.d/org.freedesktop.GeoClue2.conf` only grants the
  `geoclue` user special receive rules; the `nuxel-bridge` uid is denied the
  GeoClue client round-trip. Fixing this is a D-Bus policy change that should
  be made deliberately (an extra system-bus rule), not bundled silently here.
- GNSS hardware nodes (`/dev/ssp_sensorhub`, `/dev/ssp_data_injection`,
  `/dev/bbd_sensor`) are absent in the bridge's view and `fix_supported=false`:
  the Exynos BCM47752 GNSS path has no wired userspace provider.

## Verdicts
- `BLUETOOTH_BLOCKED_HARDWARE` — bcm43xx controller never registers hci0.
- `LOCATION_SERVICE_VERIFIED` — policy enable/disable/readback is real.
- `GNSS_BLOCKED_HARDWARE` — no GNSS receiver/provider wired; no fix fabricated.
