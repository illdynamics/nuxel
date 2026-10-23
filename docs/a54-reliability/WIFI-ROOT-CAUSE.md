# A54 Wi-Fi Root Cause

## Observed symptom
"Connect hangs at **Associating DHCP...**" after password submit.

## Root cause (two independent layers)
1. **Historical backend bug (already fixed in A51, preserved):** the pre-A51
   revision passed `specific_object = '/new'` to `AddAndActivateConnection`,
   which NetworkManager rejects with `Device.SpecificObjectNotFound`. A51
   (`9fe0ebc`) replaced it with a *verified* AP object path from the current
   scan list on the same device, plus bounded rescan, saved-profile reuse and
   `ActivateConnection` fallback. `test-wifi-activation.py` now asserts
   `specific_object is not /new` in both the new-connection and reuse paths.
2. **Live UI state-machine bug (A54 fix):** `pwa/nuxel-apps/settings/wifi-settings.js`
   reported the string `Associating / DHCP…` once, then never re-rendered the
   authoritative NetworkManager state. The connection actually completed
   (L2 → IP → route → DNS → HTTPS), but the panel was left frozen on the
   "associating" label, conflating association and DHCP.

## Fix applied
- Added `STAGE_LABELS` mapping authoritative NM stages to separate phrases:
  `authenticating`, `associating`, `ip`, `connected`, `online`, plus
  disabled/unavailable/unmanaged/enabled_disconnected.
- Added a **bounded** poll loop (1.5 s) that starts on `wifi-connect` and stops
  as soon as the state settles (`connected`/`internet`/`enabled_disconnected`),
  so the spinner can never stay mounted forever.
- `mutate()` now surfaces `success:false` as an error, keeps the password dialog
  open on failure for in-place re-entry, and never hides the form while
  association/DHCP are still in flight.
- No `/new` path was reintroduced; the backend D-Bus contract is unchanged and
  covered by the passing wifi-activation test.

## Live evidence (device, redacted)
- `nmcli device status`: `wlan0:wifi:connected:<network>`, `connectivity=4`.
- `ip route`: default via gateway, `src 192.168.178.x`.
- `/api/v1/phone/status` (via HTTP bridge): `wifi_state=internet`, `wifi_stage=online`.
- HTTPS: `https://www.gstatic.com/generate_204` → HTTP `204`.
- Saved profiles survive: 3 wireless profiles with `autoconnect=yes` present.

## Gate
- **WIFI-L2 / WIFI-IP / WIFI-PERSIST-profile:** PASS_INTEGRATION (L2/IP/route/DNS/
  HTTPS verified live; profile store verified; UI stage machine fixed).
- **WIFI-PERSIST (after cold boot):** NOT_TESTED this session — reboot requires
  owner approval per mission constraints (see COLD-BOOT-RESULTS.md).

Redaction: network name/passphrase/BSSID/MAC omitted by policy.
