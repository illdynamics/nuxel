#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/01-11_settings.png
# previous-hash: e1475756010e3314ce9b2cf47286c719971bbd40b56ed2e46e6999854bc584c8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png.nuxel-staged
printf '%s  %s\n' e1475756010e3314ce9b2cf47286c719971bbd40b56ed2e46e6999854bc584c8 /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-11_settings.png | grep -q e1475756010e3314ce9b2cf47286c719971bbd40b56ed2e46e6999854bc584c8
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
