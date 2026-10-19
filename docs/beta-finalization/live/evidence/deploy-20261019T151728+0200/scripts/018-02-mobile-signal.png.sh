#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png
# previous-hash: 7ecf9d4fc640282bfef137e04ba2d189ef5c0bf78cac98159e01b37b5dcdc091
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png.nuxel-staged
printf '%s  %s\n' 7ecf9d4fc640282bfef137e04ba2d189ef5c0bf78cac98159e01b37b5dcdc091 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/02-mobile-signal.png | grep -q 7ecf9d4fc640282bfef137e04ba2d189ef5c0bf78cac98159e01b37b5dcdc091
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
