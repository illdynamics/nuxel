#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/_shared/samples/sys-snapshot.json
# previous-hash: 31d707cd898d2fb561478994498446806f75bb431c947a1d117d08e6cfe2ff19
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-staged
printf '%s  %s\n' 31d707cd898d2fb561478994498446806f75bb431c947a1d117d08e6cfe2ff19 /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json | grep -q 31d707cd898d2fb561478994498446806f75bb431c947a1d117d08e6cfe2ff19
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/_shared/samples/sys-snapshot.json; systemctl restart nuxel-web; fi
