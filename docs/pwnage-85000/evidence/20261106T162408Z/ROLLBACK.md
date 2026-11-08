# Rollback — PWNAGE-85000

## Backup

`/var/backups/nuxel/p85000-20261106T163134Z` (38 MB)

Contents: live bridge (`flatpak_provider.py`, `api.py`, `hw_providers.py`), PWA `nuxel-home`, `nuxel-common`, Settings tree, `nuxel-portal-doc.conf`, Wayland unit/drop-ins, prewarm/bridge unit snapshots, pre-change SHA-256 list.

## Restore source

```sh
B=/var/backups/nuxel/p85000-20261106T163134Z
install -m644 $B/bridge/flatpak_provider.py /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py
install -m644 $B/bridge/api.py              /usr/lib/nuxel/nuxel-bridge/api.py
install -m644 $B/bridge/hw_providers.py     /usr/lib/nuxel/nuxel-bridge/hw_providers.py
install -m644 $B/pwa/common/theme.css       /usr/share/nuxel/pwa/nuxel-common/theme.css
install -m644 $B/pwa/common/theme.js        /usr/share/nuxel/pwa/nuxel-common/theme.js
install -m644 $B/pwa/home/css/style.css     /usr/share/nuxel/pwa/nuxel-home/css/style.css
install -m644 $B/pwa/home/css/launcher.css  /usr/share/nuxel/pwa/nuxel-home/css/launcher.css
install -m644 $B/pwa/home/js/app.js         /usr/share/nuxel/pwa/nuxel-home/js/app.js
install -m644 $B/pwa/home/js/launcher.js    /usr/share/nuxel/pwa/nuxel-home/js/launcher.js
install -m644 $B/pwa/home/index.html        /usr/share/nuxel/pwa/nuxel-home/index.html
install -m644 $B/pwa/home/sw.js             /usr/share/nuxel/pwa/nuxel-home/sw.js
install -m644 $B/pwa/settings/index.html    /usr/share/nuxel/pwa/nuxel-apps/settings/index.html
install -m644 $B/pwa/settings/appearance-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/appearance-settings.js
```

## Restore permissions / units

```sh
systemctl disable --now nuxel-fuse-access.service
rm -f /etc/systemd/system/nuxel-fuse-access.service
install -m644 $B/etc/nuxel-portal-doc.conf /etc/tmpfiles.d/nuxel-portal-doc.conf
systemctl daemon-reload
systemctl restart nuxel-http-bridge nuxel-bridge
```

If reverting only the provider but keeping the fuse service, Flatpak launches still work. If reverting the fuse service but keeping the new provider, document-portal launches will time out again; restore both together for a true pre-85000 state.

## Verification after rollback

```sh
systemctl --failed
systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-bridge nuxel-http-bridge
curl -s http://127.0.0.1:8080/api/v1/health
flatpak run --command=true org.gnome.TextEditor
```

Do not delete `/var/backups/nuxel/p84000-*` or any earlier restore point.
