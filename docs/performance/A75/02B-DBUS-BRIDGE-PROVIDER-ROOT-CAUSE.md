# A75 — D-Bus / Nuxel Bridge Provider Root Cause

## Exact observed error
The owner's approximate wording — “no service provider provides Nuxel bridge” —
is the standard D-Bus service-resolution error. The exact runtime text captured
on the device during the prior failed state was:

```
Call failed: The name org.nuxel.Bridge was not provided by any .service files
```

D-Bus name: `org.freedesktop.DBus.Error.ServiceUnknown`.

## Provider contract (verified live)
| Field | Value |
|---|---|
| Bus | **system bus** (not session) |
| Destination / service name | `org.nuxel.Bridge` |
| Owner | `nuxel-bridge.service` (uid 993 `nuxel-bridge`, GID 992) |
| Object path | `/org/nuxel/Bridge` |
| Interface | `org.nuxel.Bridge` |
| Wi-Fi methods | `NetworkWifiSetEnabled`, `NetworkWifiScan`, `NetworkWifiConnect`, `NetworkWifiDisconnect`, `NetworkWifiSaved`, `NetworkWifiForget` |
| Bluetooth methods | `BluetoothGetStatus`, `BluetoothSetPowered` |
| Location methods | `LocationGetStatus`, `LocationSetEnabled`, `GetLocation` |
| Ping / readiness | `Ping(s)->s`; property `BridgeVersion` = `1` |
| Activation descriptor | `services/nuxel-bridge/dbus/org.nuxel.Bridge.conf` (policy: only root/`nuxel-bridge` may own) |
| systemd unit | `/etc/systemd/system/nuxel-bridge.service` (`Type=simple`, `ExecStart=/usr/bin/nuxel-bridge`) |
| Environment pins | `NUXEL_BRIDGE_PROTOCOL_VERSION=1`, `NUXEL_BRIDGE_VERSION=0.6.5-beta` (after fix) |
| Frontend path | PWA `bridge.call(namespace,verb)` → HTTP `127.0.0.1:8080/api/v1/rpc` → `nuxel-http-bridge` (api.py) → D-Bus `org.nuxel.Bridge` |

## Root cause (proven)
1. `nuxel-bridge.service` was in a **crash-loop** before the fix. The journal
   (Oct 25 20:52 and Oct 26 09:01) shows the exact fault, repeated every
   restart:

   ```
   AttributeError: 'bool' object has no attribute 'get'
   nuxel-bridge.service: Main process exited, code=exited, status=1/FAILURE
   ```

   The old `_load_all_grants()` assumed every value in a capability grant file
   had `.get()`. A legacy/boolean grant (`"capability": true`) raised
   `AttributeError` during `NuxelBridgeService.__init__`, **before the service
   exported its D-Bus object**. With the name not owned, every Quick Settings
   action that resolved through the bridge answered
   `… was not provided by any .service files`.

2. The repository already carried the fix (commit `84e6b2d`): grant values are
   now type-checked (`isinstance(info, dict)` / `info is True` / non-object
   files ignored) and the shared `location-policy.json` document is explicitly
   skipped, so one malformed grant or a location toggle can never crash the
   provider again. The deployed phone, however, was still running an **older
   0.6.1-beta bridge** whose unit env pin and code did not include the bound.

3. Secondary **deployed-version skew**: bridge was pinned `0.6.1-beta`, HTTP
   bridge `0.4.0-alpha`, and `/etc/nuxel/bridge-version.json` said
   `0.4.0-alpha`, while the repo/systemd units expected `0.6.5-beta`. The
   shared PWA client also lacked the radio/privacy “no mock fallback” honesty
   change, so an unreachable provider could report fake success instead of a
   truthful error.

## Fix (narrow, atomic, auto-rollback)
Deployed from repo to the running phone via `tools/beta/live/nuxel-live-deploy.py`:
- `services/nuxel-bridge/src/bridge.py` → `/usr/lib/nuxel/nuxel-bridge/bridge.py`
- `services/nuxel-bridge/src/api.py` → `/usr/lib/nuxel/nuxel-bridge/api.py`
- both `services/nuxel-bridge/systemd/nuxel-*.service` → `/etc/systemd/system/`
- `pwa/nuxel-common/bridge-version.json` → `/etc/nuxel/` and served PWA path
- `pwa/nuxel-common/bridge.js` → `/usr/share/nuxel/pwa/nuxel-common/bridge.js`

Then `systemctl daemon-reload` + restart of `nuxel-bridge.service` and
`nuxel-http-bridge.service`. Both now report `version 0.6.5-beta`,
`bridge_version 1`, and the D-Bus name is owned and introspectable.

## Readiness evidence (after fix)
- `busctl call org.nuxel.Bridge /org/nuxel/Bridge org.nuxel.Bridge Ping s health`
  → `{"status":"ok","service":"nuxel-bridge","version":"0.6.5-beta","bridge_version":"1",…}`
- Introspection lists all expected Wi-Fi/Bluetooth/Location methods and signals.
- `nuxel-bridge.service` `active`, `NRestarts=0`, `ExecMainStatus=0`.

## Proven
`DBUS_PROVIDER_FIXED_NOT_DEVICE_VERIFIED` for the *previously-crashing*
provider (the bridge now starts, owns its name, exports the methods, and the
Wi-Fi/Bluetooth/Location calls return structured results — verified on-device).
See `02C-WIFI-RESTORATION.md` and `02D-BLUETOOTH-LOCATION-STATUS.md` for the
separate backend verdicts.
