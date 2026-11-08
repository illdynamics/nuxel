# Interface (radio) state persistence

Nuxel stores the owner's ON/OFF intent for interfaces it switches in:

```
/var/lib/nuxel/interfaces.json
```

A missing document means the safe first-boot defaults:

| Interface | Default | Applied by |
|---|---|---|
| Bluetooth | OFF | `hw_providers.bluetooth_set_power` |
| NFC | OFF | `nfc_provider.NfcProvider` |
| GNSS power rail | OFF | `api.location.gnss-power` |

Wi-Fi is deliberately *not* stored here. NetworkManager already persists
`WirelessEnabled` in `/var/lib/NetworkManager/NetworkManager.state`, and
`nuxel-wifi.service` now preserves a persisted OFF instead of forcing the radio
back ON. The location/GPS privacy policy is likewise already durable in
`/var/lib/nuxel/permissions/location-policy.json`.

## Boot restore

`nuxel-interface-state.service` runs once per boot (before the Wayland
session) and executes:

```
/usr/lib/nuxel/nuxel-interface-state restore
```

It never invents a state. A failed radio action is logged and boot continues;
the next status read shows the real provider result.

## Bluetooth default-off details

`bluetooth.service` and the BCM4375 H4 attach (`nuxel-bluetooth.service`) are
not enabled into the boot graph. When the persisted value is ON, the restore or
the UI toggle starts both in order:

1. `nuxel-bluetooth.service` (patchram + `btattach`)
2. `bluetooth.service` (BlueZ)

When the value is OFF, both are stopped and the Bluetooth rfkill node is
soft-blocked. This avoids the old boot sequence that unblocked the radio and
left it powered even when the owner had turned Bluetooth off.

## CLI

```sh
nuxel-interface-state status --json
nuxel-interface-state set bluetooth on
nuxel-interface-state set nfc off
nuxel-interface-state restore
```
