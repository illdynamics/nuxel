#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calendar/index.html
# previous-hash: 484cfa8b0ad600e6947399c961d322b52c8dcfb284f6c7a08153820f7926259a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-staged
printf '%s  %s\n' 484cfa8b0ad600e6947399c961d322b52c8dcfb284f6c7a08153820f7926259a /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/index.html | grep -q 484cfa8b0ad600e6947399c961d322b52c8dcfb284f6c7a08153820f7926259a
echo INSTALL-OK
