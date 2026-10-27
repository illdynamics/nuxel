#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/notes/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/index.html
# previous-hash: bc3691a908ca314d7d7ec799214548b4acfd7eed7783a0fc2e8f63a569da038d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/notes/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/index.html /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/index.html /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged
printf '%s  %s\n' bc3691a908ca314d7d7ec799214548b4acfd7eed7783a0fc2e8f63a569da038d /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/index.html | grep -q bc3691a908ca314d7d7ec799214548b4acfd7eed7783a0fc2e8f63a569da038d
echo INSTALL-OK
