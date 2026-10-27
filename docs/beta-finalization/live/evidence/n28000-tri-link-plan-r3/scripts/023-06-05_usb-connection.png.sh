#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png (service: None, risk: low)
# staged source: assets/nuxel-applications-icon-pack/06-05_usb-connection.png
# previous-hash: 8f2b2cb963ba85462b517573940e2a54c38994fd22b69ddd5300193a8b9024d1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback.pre-deploy-20261027T164448-2130897 ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback.pre-deploy-20261027T164448-2130897 /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback.pre-deploy-20261027T164448-2130897 ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-rollback.pre-deploy-20261027T164448-2130897; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-staged
printf '%s  %s\n' 8f2b2cb963ba85462b517573940e2a54c38994fd22b69ddd5300193a8b9024d1 /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-05_usb-connection.png | grep -q 8f2b2cb963ba85462b517573940e2a54c38994fd22b69ddd5300193a8b9024d1
echo INSTALL-OK
