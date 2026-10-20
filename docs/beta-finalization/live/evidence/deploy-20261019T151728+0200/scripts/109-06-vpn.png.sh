#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/06-vpn.png
# previous-hash: 6d703c349bceb8d5ad969aab7eeb09c19d2f2ddc546e03dabaae04d7ce641839
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png.nuxel-staged
printf '%s  %s\n' 6d703c349bceb8d5ad969aab7eeb09c19d2f2ddc546e03dabaae04d7ce641839 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/06-vpn.png | grep -q 6d703c349bceb8d5ad969aab7eeb09c19d2f2ddc546e03dabaae04d7ce641839
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
