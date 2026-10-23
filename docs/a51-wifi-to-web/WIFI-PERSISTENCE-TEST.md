# A51 — Wi-Fi Persistence Test (status & owner procedure)

## What was verified WITHOUT the owner's PSK
Live on the S10+ (no secret disclosed, no radio joined):

1. `network.wifi-scan` returns the full contract:
   `{ssid, ssid_hex, strength, security, ap_path, bssid, frequency, device}`.
   Example (redacted/strongest AP): `Undetektable`, bssid `32:01:24:17:CF:1F`,
   2437 MHz, `wpa3`, `ap_path /org/freedesktop/NetworkManager/AccessPoint/3`,
   `device /org/freedesktop/NetworkManager/Devices/2`.
2. `network.wifi-connect` with a deliberately bogus AP path and a fake SSID
   returns `{"success": false, "error": "stale_scan", …}` — proving the `/new`
   sentinel is gone and the stale-AP guard performs **no** activation.
3. `network.wifi-saved` lists the two pre-existing saved profiles (created by
   the earlier `/new`-era attempts):
   - `Nuxel Undetektable` (`Settings/2`, `autoconnect=false`, wpa3)
   - `Nuxel Studio E Guest` (`Settings/1`, `autoconnect=false`, wpa2)

   Both carry `autoconnect=false`, which is exactly why the phone never
   auto-reconnects after reboot. The fix flips `autoconnect=true` and refreshes
   the stored PSK when the owner reconnects.

## Persistence design (implemented)
- New profiles are created with `connection.autoconnect=true` and a sensible
  `autoconnect-priority`; the PSK is stored through NetworkManager's own
  settings service (privileged, root-readable keyfile), never in frontend
  localStorage or unencrypted app JSON.
- Re-connect reuses the matching saved profile and updates autoconnect + secret
  (no duplicate profiles).
- `disconnect` only deactivates (profile kept); `forget` deletes the profile.
- The Settings UI is a view of real NetworkManager state (scan/status/saved),
  not an independent fiction.

## Remaining owner-only steps (required for the non-negotiable result)
These require the owner to enter the PSK and approve a reboot; an agent cannot
and must not do them without credentials:

1. Unlock → Settings → Network → Scan → select home SSID → type PSK on the
   working Stevia OSK → Connect.
2. Observe `associating → ip → online` in the stage line (not an instant "done").
3. `curl -I https://example.org` and a graphical browser page load over Wi-Fi.
4. Wi-Fi off → on: reconnect without re-entering the password.
5. Owner-approved reboot: confirm `Nuxel <SSID>` autoconnects, no PSK prompt.
6. Confirm USB console, Home, lockscreen, native OSK, and the A50 performance
   tuning remain intact after reboot.

Record results in this file once executed. Until then the Wi-Fi fix is
**deployed + contract-verified**, and the physical join/reboot gate is
**pending owner action** (not "assumed success").
