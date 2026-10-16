#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/penguinterface/icons/icon-48.png
# previous-hash: 65e8c1eb90b0c21db8764db2a2c1847bb901a1deaa2e22e281563d2bcca5602d
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png.nuxel-staged
printf '%s  %s\n' 65e8c1eb90b0c21db8764db2a2c1847bb901a1deaa2e22e281563d2bcca5602d /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png | grep -q 65e8c1eb90b0c21db8764db2a2c1847bb901a1deaa2e22e281563d2bcca5602d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-48.png; systemctl restart nuxel-web; fi
