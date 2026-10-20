#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/04-07_system-info.png
# previous-hash: 0a81ae4c9b7e717d6694ea8a3e90361769dea094934bb862982121371a027ab4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png.nuxel-staged
printf '%s  %s\n' 0a81ae4c9b7e717d6694ea8a3e90361769dea094934bb862982121371a027ab4 /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-07_system-info.png | grep -q 0a81ae4c9b7e717d6694ea8a3e90361769dea094934bb862982121371a027ab4
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
