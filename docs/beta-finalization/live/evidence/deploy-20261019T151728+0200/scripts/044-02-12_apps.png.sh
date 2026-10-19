#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-12_apps.png
# previous-hash: 85b7b81edb1402f00df4803bcfd84680433491f289182e106591ce914aa7a0e7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png.nuxel-staged
printf '%s  %s\n' 85b7b81edb1402f00df4803bcfd84680433491f289182e106591ce914aa7a0e7 /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-12_apps.png | grep -q 85b7b81edb1402f00df4803bcfd84680433491f289182e106591ce914aa7a0e7
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
