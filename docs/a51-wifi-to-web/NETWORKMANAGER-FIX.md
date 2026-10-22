# A51 — NetworkManager Fix

## What changed
Three files in the live Wi-Fi path (source → HTTP bridge → D-Bus bridge):

1. `services/nuxel-bridge/src/bridge.py`
   - `scan_wifi()` now returns `ssid_hex`, `bssid`, `frequency`, and per-AP
     `device` in addition to `ssid`/`strength`/`security`/`ap_path`.
   - `get_status()` now returns `wifi_stage` (honest lifecycle) and each
     `wifi_devices[]` entry now includes its `path`.
   - `connect_wifi(ssid, password, security, ap_path=None, bssid=None,
     device=None, ssid_hex=None)`:
     * validates SSID (1–32 bytes, no NUL), PSK (8–63 for non-open), security
       (`wpa2`/`wpa3`/`open`; WEP and enterprise are explicitly refused);
     * verifies the caller-supplied device is a real type-2 device, else picks
       the first;
     * resolves the target AP **without trusting the frontend**: (1) the
       supplied `ap_path` only while it is still listed on the same device and
       its SSID bytes match; (2) BSSID+SSID; (3) unique SSID; (4) strongest of
       duplicate SSIDs. SSID is compared as **bytes** (via `ssid_hex` when
       present), never the lossy display string;
     * on a stale AP performs a **bounded re-scan** (≤2 attempts) and returns
       `{"success": false, "error": "stale_scan", …}` if it genuinely vanished —
       no infinite loop, no connecting to a different SSID;
     * reuses an existing saved profile (no `Nuxel <SSID> 2` duplicates) and
       refreshes its `autoconnect=true` + `key-mgmt` + `psk` before
       `ActivateConnection`, so a corrected password persists and the network
       auto-reconnects after reboot;
     * for a new network calls `AddAndActivateConnection(profile, device,
       ap['path'])` with the **verified real AP object path** (never `/new`,
       never blind `/`);
     * captures the returned settings/active paths and returns
       `state=connecting, stage=associating` (activation is asynchronous — the
       UI polls `get_status` for the honest `associating → ip → online`
       progression);
     * maps D-Bus errors to human-readable messages and redacts any PSK that
       could appear in an exception string.
   - New D-Bus methods: `NetworkWifiSaved` and `NetworkWifiForget` (plus the
     `saved_wifi()` / `forget_wifi()` backend).

2. `services/nuxel-bridge/src/api.py`
   - `NetworkWifiConnect` RPC builder now forwards `ap_path`, `bssid`, `device`,
     `ssid_hex`; added `network.wifi-saved` / `network.wifi-forget` RPC maps.

3. `pwa/nuxel-apps/settings/wifi-settings.js`
   - Synced the repo copy to the already-deployed (correct) version that sends
     the full AP identity and renders `wifi_stage`.

## D-Bus contract (typed)
`NetworkWifiConnect` signature widened from `ssss` to `ssssssss`:
`(app_id, ssid, password, security, ap_path, bssid, device, ssid_hex) → s`.
All AP identity arguments are treated as untrusted hints and re-verified
server-side. `AddAndActivateConnection` is called with `a{sa{sv}}` typed profile
and the verified AP object path; `ActivateConnection` may fall back to `/` for
automatic selection only when the AP path fails.

## Secret handling
The PSK travels only inside the typed `802-11-wireless-security.psk` D-Bus
settings payload. It never appears in argv, shell history, or logs; the bridge
runs as the unprivileged `nuxel-bridge` user with
`ProtectSystem=full/PrivateTmp/NoNewPrivileges`. Error strings are PSK-redacted.

## Deployed hashes (verified on device)
| File | sha256 |
|---|---|
| bridge.py | `5735b7184cec6482486a241b2f10a9e9646c9f192b9b1c41e2cf88d1f3781e3c` |
| api.py | `5c7f1848ef5252f48d4fc78ac9b5e3da411531e69ea6b53a151024ffcd831afa` |
| wifi-settings.js | `83bb596edf0e562554a3f7c13de1d5515a7247cba638fc67fcb206042a31523b` |

## Regression guard
`services/nuxel-bridge/test-wifi-activation.py` (offline, no D-Bus daemon) is a
39-assertion gate that fails if:
- the literal `/new` reappears in any activation call site;
- the `NetworkWifiConnect` signature no longer carries AP identity;
- the AP resolver trusts an unverified path, picks a non-strongest duplicate,
  or fabricates an AP for an unknown SSID;
- the profile lacks `autoconnect=true` / wrong `key-mgmt`;
- a reused profile is not refreshed before activation;
- a stale AP or unsafe input still reaches `AddAndActivateConnection`.
