#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/css/notes.css
# previous-hash: d7b18c9c5befa1cf2412330cc7374c58be2de9635e04ce7b4050e57a46d1bc15
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-staged
printf '%s  %s\n' d7b18c9c5befa1cf2412330cc7374c58be2de9635e04ce7b4050e57a46d1bc15 /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/css/notes.css | grep -q d7b18c9c5befa1cf2412330cc7374c58be2de9635e04ce7b4050e57a46d1bc15
echo INSTALL-OK
