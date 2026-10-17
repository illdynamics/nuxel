#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/manifest.json
# previous-hash: 294e53dcd58ae2f402692223b6db81e86058a5aac1bcbad9ff1655a3136239d0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json.nuxel-staged
printf '%s  %s\n' 294e53dcd58ae2f402692223b6db81e86058a5aac1bcbad9ff1655a3136239d0 /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/manifest.json | grep -q 294e53dcd58ae2f402692223b6db81e86058a5aac1bcbad9ff1655a3136239d0
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
