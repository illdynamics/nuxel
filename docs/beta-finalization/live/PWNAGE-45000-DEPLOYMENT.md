# PWNAGE-45000 — deployment and rollback

Live target: `root@192.168.178.167` (Wi-Fi SSH), S10+ `beyond2lte`, kernel
`4.14.253-gf7194c1d15ed-dirty`.

## Backup

All pre-existing changed files were copied before replacement to:

```
/var/lib/nuxel/pwnage45000-backup-20261031T182512Z/
```

The backup preserves the relative paths (for example
`usr/lib/nuxel/nuxel-bridge/api.py`).

## Deployed paths

| Path | Purpose |
|---|---|
| `/usr/lib/nuxel/nuxel-bridge/{api,dnd_provider,nfc_provider,fingerprint_provider,security_provider,led_notification_provider,app_manager,software_provider}.py` | Bridge APIs/providers |
| `/usr/lib/nuxel/nuxel-notifications/notifications.py` | DND-aware history |
| `/usr/lib/nuxel/nuxel-usb-mode.sh`, `/usr/lib/nuxel/nuxel-mtp-server` | MTP/ACM owner and responder |
| `/usr/lib/nuxel/nuxel-wl-fb` | rebuilt display owner with bounded edge-light |
| `/usr/lib/nuxel/nuxel-navdock` | rebuilt native dock with regenerated art |
| `/usr/lib/nuxel/nuxel-session.sh` | session runtime/socket/dconf + Wayland polkit agent |
| `/usr/lib/nuxel/nuxel-software` | GTK3 PackageKit software center |
| `/usr/local/bin/nuxel-nfc-diag.sh`, `/usr/local/bin/nuxel-led-diag.sh` | diagnostics |
| `/usr/share/nuxel/pwa/nuxel-home/*`, `/usr/share/nuxel/pwa/nuxel-apps/{settings,nuxtore,penguinterface}/*` | PWA changes |
| `/etc/nuxel/app-registry/app_registry.json` | canonical registry (40 apps) |
| `/etc/nuxel/notifications/dnd.json`, `/etc/nuxel/nfc/nfc.json` | policy |
| `/etc/systemd/system/nuxel-http-bridge.service` | registry path + writable policy dirs |
| `/etc/systemd/system/nuxel-notifications.service` (package default) | history path |

`/home/nuxel/Shared/{Downloads,Pictures,Documents,Music,Videos}` is the only MTP
export root. It was created with user ownership.

## Deployed hashes

See `evidence/pwnage-45000/live/deployed-sha256.txt`.

## Post-deploy commands

```sh
chgrp nuxel /run/nuxel-wayland /run/nuxel-wayland/wayland-0
chmod 0750 /run/nuxel-wayland; chmod 0660 /run/nuxel-wayland/wayland-0
systemctl restart nuxel-http-bridge nuxel-notifications nuxel-wl-fb
# native dock restart (session-owned)
pkill nuxel-navdock; XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
  /usr/lib/nuxel/nuxel-navdock >/run/nuxel-navdock.out 2>&1 &
```

## Rollback

Never remove user data, authenticator storage, app data or SSH keys.

1. Stop new services: `systemctl stop nuxel-mtp 2>/dev/null || true`
2. Restore the Bridge/provider files from the backup:
   ```sh
   test -d /var/lib/nuxel/pwnage45000-backup-20261031T182512Z
   cp -a /var/lib/nuxel/pwnage45000-backup-20261031T182512Z/usr/lib/nuxel/nuxel-bridge/. \
         /usr/lib/nuxel/nuxel-bridge/
   cp -a /var/lib/nuxel/pwnage45000-backup-20261031T182512Z/usr/lib/nuxel/nuxel-notifications/notifications.py \
         /usr/lib/nuxel/nuxel-notifications/notifications.py
   cp -a /var/lib/nuxel/pwnage45000-backup-20261031T182512Z/usr/lib/nuxel/nuxel-usb-mode.sh \
         /usr/lib/nuxel/nuxel-usb-mode.sh
   ```
3. Restore display/nav binaries and PWA files from the same backup tree.
4. Restore `/etc/nuxel/app-registry/app_registry.json` from the backup.
5. Leave `/var/lib/nuxel/security/lock.json` intact (do not strand the owner);
   to deliberately reset the lock, use the Security tab with the current
   credential or the documented owner recovery path.
6. Restart only: `systemctl restart nuxel-http-bridge nuxel-notifications nuxel-wl-fb`.
7. USB recovery: `/usr/lib/nuxel/nuxel-usb-mode.sh charging` restores acm-only
   and removes the MTP function. Never leave a half-bound UDC.

## Reboot

The handset was rebooted after deployment with the existing safe user-space path.
SSH over Wi-Fi is independent of Phoc/USB; the CDC-ACM console remains enabled.

## Follow-up 2026-10-31: lockscreen top bar removal

Backup:
`/var/lib/nuxel/pwnage45000-followup-20261031T191613Z`

Deployed:

- `/usr/lib/nuxel/nuxel-statusbar` sha256
  `ddcf5092a5dae376f95f47fc99ceec438adcc34454d98fd90cba2b598223c812`
- `/usr/share/nuxel/pwa/nuxel-home/{index.html,manifest.json,sw.js}`
- `/usr/share/nuxel/pwa/nuxel-home/css/{status-bar.css,style.css}`
- `/usr/share/nuxel/pwa/nuxel-home/assets/button-{left,middle,right}.png`

Rollback:

```sh
BK=/var/lib/nuxel/pwnage45000-followup-20261031T191613Z
pkill -x nuxel-statusbar || true
cp -a "$BK/usr/lib/nuxel/nuxel-statusbar" /usr/lib/nuxel/nuxel-statusbar
cp -a "$BK/usr/share/nuxel/pwa/nuxel-home/." /usr/share/nuxel/pwa/nuxel-home/
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
  nohup /usr/lib/nuxel/nuxel-statusbar </dev/null >/run/nuxel-statusbar.out 2>&1 &
```

Rebuild artifact (not raw-flashed):
`build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-p45001.img`
sha256 `4f91d673e2e46528acb1ddc029c819140832d1e4bfb0c8f8588ebb89af89e1e1`.


## Post-reboot result

The handset rebooted successfully and SSH returned over Wi-Fi. The native
top bar starts hidden because the lock state is fail-closed before the first
unlock. Verified: kernel `4.14.253-gf7194c1d15ed-dirty`; `nuxel-http-bridge`,
`nuxel-notifications`, `nuxel-wl-fb`, `nuxel-web` and `nuxel-wayland` active;
deployed hashes unchanged; served PWA `v71-p45001`; post-reboot screenshot
`evidence/pwnage-45000/screenshots/post-reboot-lockscreen-no-topbar.png`.
