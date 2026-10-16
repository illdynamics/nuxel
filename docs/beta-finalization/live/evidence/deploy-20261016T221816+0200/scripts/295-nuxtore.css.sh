#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/css/nuxtore.css
# previous-hash: 4a003022ef387cbf4884f3a33932bf23cdabaf870a341fb706c8290cce18130f
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-staged
printf '%s  %s\n' 4a003022ef387cbf4884f3a33932bf23cdabaf870a341fb706c8290cce18130f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css | grep -q 4a003022ef387cbf4884f3a33932bf23cdabaf870a341fb706c8290cce18130f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/css/nuxtore.css; systemctl restart nuxel-web; fi
