# PWNAGE-44000 rollback

Live backup root: `/root/pwnage-44000/backup-20261031T054927Z`

Restore:

```sh
B=/root/pwnage-44000/backup-20261031T054927Z
install -m 0755 "$B/bin/nuxel-pwa-host" /usr/lib/nuxel/nuxel-pwa-host
install -m 0755 "$B/bin/nuxel-button-manager" /usr/lib/nuxel/nuxel-button-manager
install -m 0755 "$B/bin/nuxel-screenshot" /usr/lib/nuxel/nuxel-screenshot
cp -a "$B/home/." /usr/share/nuxel/nuxel-home/
for a in files photos notes; do cp -a "$B/apps/$a/." "/usr/share/nuxel/pwa/nuxel-apps/$a/"; done
cp -a "$B/bridge/." /usr/lib/nuxel/nuxel-bridge/
install -m 0644 "$B/nuxel-http-bridge.service" /etc/systemd/system/nuxel-http-bridge.service
install -Dm0644 "$B/etc/leds/leds.json" /etc/nuxel/leds/leds.json
systemctl daemon-reload
systemctl restart nuxel-http-bridge nuxel-button-manager
```

No `/dev/fb0`, partition, bootloader or reboot-gate file was modified. The
flashlight is left OFF. The live screenshots in `~/Gallery` are user-visible
artifacts and intentionally retained.

Rollback does not remove `bluez-obexd`; it is an additive Fedora package and
does not start any transfer by itself.
