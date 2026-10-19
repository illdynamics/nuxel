#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/04-12_utilities.png
# previous-hash: c5157174a661ad78963907fd90455ee33446f5521c8e619681251b013431dc2c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png.nuxel-staged
printf '%s  %s\n' c5157174a661ad78963907fd90455ee33446f5521c8e619681251b013431dc2c /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-12_utilities.png | grep -q c5157174a661ad78963907fd90455ee33446f5521c8e619681251b013431dc2c
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
