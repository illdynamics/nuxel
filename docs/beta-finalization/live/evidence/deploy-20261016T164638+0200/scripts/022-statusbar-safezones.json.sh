#!/bin/sh
# launcher safe areas / status bar -> /etc/nuxel/statusbar-safezones.json (service: nuxel-web, risk: low)
# staged source: configs/nuxel/statusbar-safezones.json
# previous-hash: 5dec2d293480f30ea4c6c1cf2b690d7efebd10247a4575a52c9c264c0cd9d9c6
set -eu
mkdir -p "$(dirname /etc/nuxel/statusbar-safezones.json)"
if [ -e /etc/nuxel/statusbar-safezones.json ]; then cp -a /etc/nuxel/statusbar-safezones.json /etc/nuxel/statusbar-safezones.json.nuxel-rollback; fi
test -f /etc/nuxel/statusbar-safezones.json.nuxel-staged
printf '%s  %s\n' 5dec2d293480f30ea4c6c1cf2b690d7efebd10247a4575a52c9c264c0cd9d9c6 /etc/nuxel/statusbar-safezones.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/statusbar-safezones.json.nuxel-staged /etc/nuxel/statusbar-safezones.json
sha256sum /etc/nuxel/statusbar-safezones.json | grep -q 5dec2d293480f30ea4c6c1cf2b690d7efebd10247a4575a52c9c264c0cd9d9c6
systemctl restart nuxel-web
systemctl is-active nuxel-web
test -s /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/statusbar-safezones.json.nuxel-rollback ]; then cp -a /etc/nuxel/statusbar-safezones.json.nuxel-rollback /etc/nuxel/statusbar-safezones.json; systemctl restart nuxel-web; fi
