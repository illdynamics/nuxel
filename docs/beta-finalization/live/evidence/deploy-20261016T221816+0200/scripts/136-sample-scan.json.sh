#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/js/sample-scan.json
# previous-hash: ca13ec71175e3029a598679b1f2c3c0248a96ee1bd4070583e6ddf19930fe5c2
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json.nuxel-staged
printf '%s  %s\n' ca13ec71175e3029a598679b1f2c3c0248a96ee1bd4070583e6ddf19930fe5c2 /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json | grep -q ca13ec71175e3029a598679b1f2c3c0248a96ee1bd4070583e6ddf19930fe5c2
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/sample-scan.json; systemctl restart nuxel-web; fi
