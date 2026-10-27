#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calendar/css/calendar.css
# previous-hash: a2f8aaf4c7e1db972c47b456660f3d276f8adb1bf8eb645295cea701c375039f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-staged
printf '%s  %s\n' a2f8aaf4c7e1db972c47b456660f3d276f8adb1bf8eb645295cea701c375039f /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/css/calendar.css | grep -q a2f8aaf4c7e1db972c47b456660f3d276f8adb1bf8eb645295cea701c375039f
echo INSTALL-OK
