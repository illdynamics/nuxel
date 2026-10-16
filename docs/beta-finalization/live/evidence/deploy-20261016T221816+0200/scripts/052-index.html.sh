#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/authenticator/index.html
# previous-hash: 5b45a64049e1f174b5cc7186461bac83c73fc8f24a0231e1a63a2be55c4754cb
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html.nuxel-staged
printf '%s  %s\n' 5b45a64049e1f174b5cc7186461bac83c73fc8f24a0231e1a63a2be55c4754cb /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html | grep -q 5b45a64049e1f174b5cc7186461bac83c73fc8f24a0231e1a63a2be55c4754cb
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/authenticator/index.html; systemctl restart nuxel-web; fi
