#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/22-terminal.png
# previous-hash: 57b852bd3eb0807c1837abe3e6deb033d06cf925e8b3b24c8374868391192e3f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png.nuxel-staged
printf '%s  %s\n' 57b852bd3eb0807c1837abe3e6deb033d06cf925e8b3b24c8374868391192e3f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/22-terminal.png | grep -q 57b852bd3eb0807c1837abe3e6deb033d06cf925e8b3b24c8374868391192e3f
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
