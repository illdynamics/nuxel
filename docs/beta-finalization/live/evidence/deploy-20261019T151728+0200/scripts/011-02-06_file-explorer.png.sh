#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-06_file-explorer.png
# previous-hash: 94a22e4b05e0a7a7805e6f3d471639e541a923f379a055d5af9e57d7368d122d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png.nuxel-staged
printf '%s  %s\n' 94a22e4b05e0a7a7805e6f3d471639e541a923f379a055d5af9e57d7368d122d /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-06_file-explorer.png | grep -q 94a22e4b05e0a7a7805e6f3d471639e541a923f379a055d5af9e57d7368d122d
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
