#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/browser/manifest.json
# previous-hash: c69afa805951169bcf4cbe1534a92f282d8d8ba66767e81e0ce4026409003618
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json.nuxel-staged
printf '%s  %s\n' c69afa805951169bcf4cbe1534a92f282d8d8ba66767e81e0ce4026409003618 /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/manifest.json | grep -q c69afa805951169bcf4cbe1534a92f282d8d8ba66767e81e0ce4026409003618
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
