#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/samples/cover-tone.svg
# previous-hash: e2064fa5c44acd0631093a00fffc863e4ada6b178eb12638f39e1ef197805500
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg.nuxel-staged
printf '%s  %s\n' e2064fa5c44acd0631093a00fffc863e4ada6b178eb12638f39e1ef197805500 /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg | grep -q e2064fa5c44acd0631093a00fffc863e4ada6b178eb12638f39e1ef197805500
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/samples/cover-tone.svg; systemctl restart nuxel-web; fi
