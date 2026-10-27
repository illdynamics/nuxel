#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-home/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/index.html
# previous-hash: 16a2ded2bc54fd3304e697c7ac9779469d46b0e9b8e2e6e5d5eb9f9b2cf19328
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-n28000-tri-link-apply ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-n28000-tri-link-apply /usr/share/nuxel/pwa/nuxel-home/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-n28000-tri-link-apply ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-n28000-tri-link-apply; fi
test -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged
printf '%s  %s\n' 16a2ded2bc54fd3304e697c7ac9779469d46b0e9b8e2e6e5d5eb9f9b2cf19328 /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | grep -q 16a2ded2bc54fd3304e697c7ac9779469d46b0e9b8e2e6e5d5eb9f9b2cf19328
echo INSTALL-OK
