#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/mail/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/index.html
# previous-hash: c48488ee5e9f516a59351723f23cef6f1ac958feda5a525067a05d8b7c019a4a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/mail/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/index.html /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/index.html /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-staged
printf '%s  %s\n' c48488ee5e9f516a59351723f23cef6f1ac958feda5a525067a05d8b7c019a4a /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/index.html | grep -q c48488ee5e9f516a59351723f23cef6f1ac958feda5a525067a05d8b7c019a4a
echo INSTALL-OK
