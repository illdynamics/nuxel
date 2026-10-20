#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/01-05_penguinterface.png
# previous-hash: c53c006b6e082b2b7bb81e23a34e51cd6e0246af27ae2f5d1f6af197a548c031
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png.nuxel-staged
printf '%s  %s\n' c53c006b6e082b2b7bb81e23a34e51cd6e0246af27ae2f5d1f6af197a548c031 /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-05_penguinterface.png | grep -q c53c006b6e082b2b7bb81e23a34e51cd6e0246af27ae2f5d1f6af197a548c031
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
