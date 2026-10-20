#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/06-04_casting-screen.png
# previous-hash: b10a79025ac113dc47462c87e1abfcd5893f3e91ef2ee90647ead42b6b4873c1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-staged
printf '%s  %s\n' b10a79025ac113dc47462c87e1abfcd5893f3e91ef2ee90647ead42b6b4873c1 /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/06-04_casting-screen.png | grep -q b10a79025ac113dc47462c87e1abfcd5893f3e91ef2ee90647ead42b6b4873c1
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
