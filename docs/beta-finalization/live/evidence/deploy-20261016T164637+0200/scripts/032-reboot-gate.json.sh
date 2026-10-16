#!/bin/sh
# touch / hardware buttons -> /etc/nuxel/buttons/reboot-gate.json (service: nuxel-touch-arm, risk: medium)
# staged source: configs/nuxel/buttons/reboot-gate.json
# previous-hash: 1b23b50f22bbcf12452ea1eb5abb0ad24a6184a0e9f5902bd69882e14bbd30fd
set -eu
mkdir -p "$(dirname /etc/nuxel/buttons/reboot-gate.json)"
if [ -e /etc/nuxel/buttons/reboot-gate.json ]; then cp -a /etc/nuxel/buttons/reboot-gate.json /etc/nuxel/buttons/reboot-gate.json.nuxel-rollback; fi
test -f /etc/nuxel/buttons/reboot-gate.json.nuxel-staged
printf '%s  %s\n' 1b23b50f22bbcf12452ea1eb5abb0ad24a6184a0e9f5902bd69882e14bbd30fd /etc/nuxel/buttons/reboot-gate.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/buttons/reboot-gate.json.nuxel-staged /etc/nuxel/buttons/reboot-gate.json
sha256sum /etc/nuxel/buttons/reboot-gate.json | grep -q 1b23b50f22bbcf12452ea1eb5abb0ad24a6184a0e9f5902bd69882e14bbd30fd
systemctl restart nuxel-touch-arm
systemctl is-active nuxel-touch-arm
systemctl is-active nuxel-touch-arm
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/buttons/reboot-gate.json.nuxel-rollback ]; then cp -a /etc/nuxel/buttons/reboot-gate.json.nuxel-rollback /etc/nuxel/buttons/reboot-gate.json; systemctl restart nuxel-touch-arm; fi
