#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-home/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/index.html
# previous-hash: ecb12c7e30d4daaa59c3fe1f14e9f90c7eee9eef669312e3907ea3afe4616803
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-home/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged
printf '%s  %s\n' ecb12c7e30d4daaa59c3fe1f14e9f90c7eee9eef669312e3907ea3afe4616803 /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | grep -q ecb12c7e30d4daaa59c3fe1f14e9f90c7eee9eef669312e3907ea3afe4616803
echo INSTALL-OK
