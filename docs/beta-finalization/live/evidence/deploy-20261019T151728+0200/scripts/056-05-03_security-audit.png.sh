#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-03_security-audit.png
# previous-hash: 1299fd4b61eaae90cfd0cfa8a2b77e29a18f46e1fa9f8c6e45c5585718a682bd
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png.nuxel-staged
printf '%s  %s\n' 1299fd4b61eaae90cfd0cfa8a2b77e29a18f46e1fa9f8c6e45c5585718a682bd /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-03_security-audit.png | grep -q 1299fd4b61eaae90cfd0cfa8a2b77e29a18f46e1fa9f8c6e45c5585718a682bd
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
