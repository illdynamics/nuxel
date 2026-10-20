#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png (service: None, risk: high)
# staged source: assets/nuxel-quicksettings-icon-pack/23-firewall.png
# previous-hash: c9aa81a6d6f8fde6075f858ed26111812d317bac665fc157a7ceb7df258e1c68
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png)"
if [ -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png.nuxel-staged
printf '%s  %s\n' c9aa81a6d6f8fde6075f858ed26111812d317bac665fc157a7ceb7df258e1c68 /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png.nuxel-staged /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png
sha256sum /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/23-firewall.png | grep -q c9aa81a6d6f8fde6075f858ed26111812d317bac665fc157a7ceb7df258e1c68
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
