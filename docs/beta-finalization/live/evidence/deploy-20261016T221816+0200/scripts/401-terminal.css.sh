#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/terminal/terminal.css
# previous-hash: be6132b04a605c6dc0546f8a153da94d0675836b9650c04bcaca5093a2dda41b
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-staged
printf '%s  %s\n' be6132b04a605c6dc0546f8a153da94d0675836b9650c04bcaca5093a2dda41b /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css | grep -q be6132b04a605c6dc0546f8a153da94d0675836b9650c04bcaca5093a2dda41b
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css; systemctl restart nuxel-web; fi
