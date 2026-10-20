#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/26-screenshot.png
# previous-hash: e86943313e2aee81fbbead831cc1ece2c59d3eaa298ec0c3a95f24b015afef21
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png.nuxel-staged
printf '%s  %s\n' e86943313e2aee81fbbead831cc1ece2c59d3eaa298ec0c3a95f24b015afef21 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/26-screenshot.png | grep -q e86943313e2aee81fbbead831cc1ece2c59d3eaa298ec0c3a95f24b015afef21
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
