# A51 — Rollback & Recovery

## Deployed change set (all userspace, reversible)
| File | Live path | New sha256 | Pre-deploy sha256 |
|---|---|---|---|
| bridge.py | `/usr/lib/nuxel/nuxel-bridge/bridge.py` | `5735b718…` | `e61f844c…` |
| api.py | `/usr/lib/nuxel/nuxel-bridge/api.py` | `5c7f1848…` | `b9c25815…` |

`wifi-settings.js` was **not** re-deployed (the live copy was already the
correct, newer version); its repo copy was only synced.

## On-device rollback copies (already captured)
```
/usr/lib/nuxel/nuxel-bridge/bridge.py.a51-rollback   # e61f844c…
/usr/lib/nuxel/nuxel-bridge/api.py.a51-rollback      # b9c25815…
```

## Rollback procedure (via live USB console)
```
cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py.a51-rollback /usr/lib/nuxel/nuxel-bridge/bridge.py
cp -a /usr/lib/nuxel/nuxel-bridge/api.py.a51-rollback    /usr/lib/nuxel/nuxel-bridge/api.py
systemctl restart nuxel-bridge nuxel-http-bridge
systemctl is-active nuxel-bridge nuxel-http-bridge   # expect: active active
```

## Recovery invariants preserved
- No partition, kernel, bootloader, firmware, recovery, DTB/DTBO/VBMETA or EFS
  writes. No flashing.
- The USB console (pre-systemd, initramfs-owned) is untouched and remains the
  independent recovery channel even if Wi-Fi is down.
- Home, lockscreen, Stevia OSK, navdock, touch-arm, and the A50 performance
  binaries were **not** modified.
- D-Bus/polkit rules and systemd units on the device were **not** overwritten
  (the live polkit rule is A47-corrected and intentionally left in place).

## No secrets in the change
The Wi-Fi PSK never appears in a commit, log, screenshot, or diagnostic bundle.
Tests use a fake SSID (`NuxelTestNotReal`) and never touch the owner's saved
profiles or radio.
