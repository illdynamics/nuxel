#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/04-11_battery-indicator.png
# previous-hash: 499fc20a5131128b6e9d310a2e52571b2ca60c61f8f53fe0245d8a2411e74245
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png.nuxel-staged
printf '%s  %s\n' 499fc20a5131128b6e9d310a2e52571b2ca60c61f8f53fe0245d8a2411e74245 /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-11_battery-indicator.png | grep -q 499fc20a5131128b6e9d310a2e52571b2ca60c61f8f53fe0245d8a2411e74245
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
