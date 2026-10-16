#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/maps/css/maps.css
# previous-hash: 2a2ffe347766a678d177166bd53f2bc4e6cc668c19d67700211d44c58f93b79d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged
printf '%s  %s\n' 2a2ffe347766a678d177166bd53f2bc4e6cc668c19d67700211d44c58f93b79d /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css | grep -q 2a2ffe347766a678d177166bd53f2bc4e6cc668c19d67700211d44c58f93b79d
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
