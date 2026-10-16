#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/css/media.css
# previous-hash: 02664d79bc4953146d3761c781328ebecf79f0e40ac1d5b72fb04b7ce10f4134
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css.nuxel-staged
printf '%s  %s\n' 02664d79bc4953146d3761c781328ebecf79f0e40ac1d5b72fb04b7ce10f4134 /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/css/media.css | grep -q 02664d79bc4953146d3761c781328ebecf79f0e40ac1d5b72fb04b7ce10f4134
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
