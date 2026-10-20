#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/button-middle.png (service: None, risk: high)
# staged source: assets/button-middle.png
# previous-hash: c9b34ac7e3a387626a5ee6694519b779bced64bf32869be096f73cf4c7011fc1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/button-middle.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/button-middle.png.nuxel-rollback /usr/share/nuxel/assets/button-middle.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/button-middle.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/button-middle.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/button-middle.png)"
if [ -e /usr/share/nuxel/assets/button-middle.png ] && [ ! -e /usr/share/nuxel/assets/button-middle.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/button-middle.png /usr/share/nuxel/assets/button-middle.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/button-middle.png.nuxel-staged
printf '%s  %s\n' c9b34ac7e3a387626a5ee6694519b779bced64bf32869be096f73cf4c7011fc1 /usr/share/nuxel/assets/button-middle.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/button-middle.png.nuxel-staged /usr/share/nuxel/assets/button-middle.png
sha256sum /usr/share/nuxel/assets/button-middle.png | grep -q c9b34ac7e3a387626a5ee6694519b779bced64bf32869be096f73cf4c7011fc1
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
