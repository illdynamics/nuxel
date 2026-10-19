#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/01-01_terminal.png
# previous-hash: b23d3cbfe130bcb6ecaa209e2e51f303f01aed1c20fd40b3b448da33d605ce3d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png.nuxel-staged
printf '%s  %s\n' b23d3cbfe130bcb6ecaa209e2e51f303f01aed1c20fd40b3b448da33d605ce3d /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png | grep -q b23d3cbfe130bcb6ecaa209e2e51f303f01aed1c20fd40b3b448da33d605ce3d
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
