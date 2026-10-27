#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/clock/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/clock/index.html
# previous-hash: 73713b0f3eb5ce33acabca87b0df1b0fabb3fb6e2d0030eb919c112d5def603a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/clock/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/clock/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/index.html /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/index.html /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-staged
printf '%s  %s\n' 73713b0f3eb5ce33acabca87b0df1b0fabb3fb6e2d0030eb919c112d5def603a /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/clock/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/index.html | grep -q 73713b0f3eb5ce33acabca87b0df1b0fabb3fb6e2d0030eb919c112d5def603a
echo INSTALL-OK
