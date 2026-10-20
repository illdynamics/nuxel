#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/06-05_usb-connection.png
# previous-hash: 8f2b2cb963ba85462b517573940e2a54c38994fd22b69ddd5300193a8b9024d1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-staged
printf '%s  %s\n' 8f2b2cb963ba85462b517573940e2a54c38994fd22b69ddd5300193a8b9024d1 /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png | grep -q 8f2b2cb963ba85462b517573940e2a54c38994fd22b69ddd5300193a8b9024d1
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
