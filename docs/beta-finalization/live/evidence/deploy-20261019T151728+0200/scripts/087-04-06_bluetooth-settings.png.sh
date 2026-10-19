#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png
# previous-hash: 0d237de9eece6ecafa18768990e7287c7e38c34fc51728f202bef182b4167852
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-staged
printf '%s  %s\n' 0d237de9eece6ecafa18768990e7287c7e38c34fc51728f202bef182b4167852 /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-06_bluetooth-settings.png | grep -q 0d237de9eece6ecafa18768990e7287c7e38c34fc51728f202bef182b4167852
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
