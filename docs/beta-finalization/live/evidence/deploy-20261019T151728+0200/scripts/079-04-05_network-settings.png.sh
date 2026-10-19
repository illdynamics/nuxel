#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/04-05_network-settings.png
# previous-hash: 75fea0f8e2adc902ff88d992991c0b5922b4eb99667146abcf1128e6eee3328a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png.nuxel-staged
printf '%s  %s\n' 75fea0f8e2adc902ff88d992991c0b5922b4eb99667146abcf1128e6eee3328a /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/04-05_network-settings.png | grep -q 75fea0f8e2adc902ff88d992991c0b5922b4eb99667146abcf1128e6eee3328a
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
