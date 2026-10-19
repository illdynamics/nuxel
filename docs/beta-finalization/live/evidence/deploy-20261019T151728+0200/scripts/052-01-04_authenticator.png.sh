#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/01-04_authenticator.png
# previous-hash: ba0fc865cc3c054e5bc86e8d0c3b684a6f1cf77e78824095e0553ab92d289bff
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png.nuxel-staged
printf '%s  %s\n' ba0fc865cc3c054e5bc86e8d0c3b684a6f1cf77e78824095e0553ab92d289bff /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-04_authenticator.png | grep -q ba0fc865cc3c054e5bc86e8d0c3b684a6f1cf77e78824095e0553ab92d289bff
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
