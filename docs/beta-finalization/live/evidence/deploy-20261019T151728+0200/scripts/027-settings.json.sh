#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /etc/nuxel/haptics/settings.json (service: None, risk: high)
# staged source: configs/nuxel/haptics/settings.json
# previous-hash: 4ee3f014ce668564103ea4620fb04f47a33622722d88221a7b2fefcd96142acb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/haptics/settings.json.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/settings.json.nuxel-rollback /etc/nuxel/haptics/settings.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/haptics/settings.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/haptics/settings.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/haptics/settings.json)"
if [ -e /etc/nuxel/haptics/settings.json ] && [ ! -e /etc/nuxel/haptics/settings.json.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/settings.json /etc/nuxel/haptics/settings.json.nuxel-rollback; fi
test -f /etc/nuxel/haptics/settings.json.nuxel-staged
printf '%s  %s\n' 4ee3f014ce668564103ea4620fb04f47a33622722d88221a7b2fefcd96142acb /etc/nuxel/haptics/settings.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/haptics/settings.json.nuxel-staged /etc/nuxel/haptics/settings.json
sha256sum /etc/nuxel/haptics/settings.json | grep -q 4ee3f014ce668564103ea4620fb04f47a33622722d88221a7b2fefcd96142acb
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
