#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png
# previous-hash: 34e095eeee848c5d14161f937410a8e3ab40bac1b3ed2d57f9b3e1bf18c3e0a1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-staged
printf '%s  %s\n' 34e095eeee848c5d14161f937410a8e3ab40bac1b3ed2d57f9b3e1bf18c3e0a1 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/29-terminal-alternate.png | grep -q 34e095eeee848c5d14161f937410a8e3ab40bac1b3ed2d57f9b3e1bf18c3e0a1
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
