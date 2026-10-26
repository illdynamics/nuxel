# A75 — Smooth Penguin + Network/Radio Restoration — Summary

## What was actually fixed (evidence-led)
1. **D-Bus / Nuxel bridge provider failure (P0, fixed).** The exact error was
   `The name org.nuxel.Bridge was not provided by any .service files`
   (`org.freedesktop.DBus.Error.ServiceUnknown`), caused by `nuxel-bridge.service`
   crash-looping on `AttributeError: 'bool' object has no attribute 'get'` in the
   grant loader **before it exported its D-Bus object**. The repository already
   had the hardened loader; the phone was running a stale 0.6.1-beta bridge and
   mixed 0.4.0-alpha HTTP bridge. Deployed the 0.6.5-beta lockstep set
   (bridge.py, api.py, both units, bridge-version.json ×2, shared PWA bridge.js)
   and restarted both services. Both now report 0.6.5-beta / protocol 1 and the
   D-Bus name is owned with all Wi-Fi/BT/Location methods exported.

2. **Wi-Fi restored and verified end-to-end on device.** Real scan (AP list with
   BSSIDs), real connect to a public open network (assoc + DHCP), valid IP/route
   (`192.168.3.236/24`, default `via 192.168.3.1`), DNS resolution, HTTP 200.
   HTTPS was blocked only by the public hotspot's captive portal (WISPr document
   captured) — not a Nuxel defect. Saved profiles were never wiped; only my own
   transient test profile was removed.

3. **Bluetooth and Location are now truthful.** Bluetooth returns a precise
   `NO_ADAPTER` hardware blocker (bcm43xx controller never registers hci0) —
   `BLUETOOTH_BLOCKED_HARDWARE`. Location policy toggle round-trips for real;
   GNSS has no wired provider/hardware — `GNSS_BLOCKED_HARDWARE`, no fabricated
   fix.

4. **USB detach** code path is already correct (A74 DWC3 debugfs removal +
   Type-C data_role veto + stale-lease/UDC guards) and its offline tests pass.
   Physical unplug was **not** performed because the USB Live Console is the
   only recovery path — owner-supervised test remains.

## Not done / honest limits
- No physical USB unplug/replug (recovery-path safety rule).
- No HTTPS proof on a clean network (captive portal intercepted).
- No kernel/firmware work for the bcm43xx Bluetooth or GNSS (out of scope).
- Motion/performance: the three-penguin animations already exist in
  `pwa/nuxel-home/css/lockscreen.css` with distinct, state-bound,
  transform/opacity keyframes (charge 1.45s pulse, PC 3.0s sway, live 1.9s
  pulse) and reduced-motion/display-off handling. A full A75 baseline/asset
  pass was not completed in this run; see `docs/performance/A50` and
  `docs/beta-finalization/live/evidence/a75-baseline-20261026` for prior
  baseline captures.

## Deployed commit / rollback
- Repo: `main` @ `d545289`, clean.
- Deployed hashes: `docs/performance/A75/deployed-hashes.json`.
- Rollback: `docs/performance/A75/rollback-a75-bridge.sh` (each file also has a
  `.nuxel-rollback` copy on-device).

## Final status labels
- `DBUS_PROVIDER_FIXED_NOT_DEVICE_VERIFIED` (name/object/interface/methods verified live; the “fixed” claim is on-device, the physical-radio-to-UI acceptance needs owner touch)
- `WIFI_RESTORED`
- `BLUETOOTH_BLOCKED_HARDWARE`
- `LOCATION_SERVICE_VERIFIED`, `GNSS_BLOCKED_HARDWARE`
- USB physical acceptance: `NOT_TESTED`

## Overall verdict
`IMPROVED_BUT_LIMITED` — the shared bridge/provider failure is fixed on-device
and Wi-Fi is restored end-to-end; Bluetooth/GNSS remain genuinely blocked by
hardware/driver/firmware, and the physical USB detach test is still
owner-pending.
