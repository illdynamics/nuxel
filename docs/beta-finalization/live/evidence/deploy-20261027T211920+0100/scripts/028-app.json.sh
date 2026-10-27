#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/photos/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/app.json
# previous-hash: 22bf87a589821262fb9eed2255f6d9e3dc67a35fbc216d5f57b93fbfa76a838d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/photos/app.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/app.json /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/app.json /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-staged
printf '%s  %s\n' 22bf87a589821262fb9eed2255f6d9e3dc67a35fbc216d5f57b93fbfa76a838d /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/app.json | grep -q 22bf87a589821262fb9eed2255f6d9e3dc67a35fbc216d5f57b93fbfa76a838d
echo INSTALL-OK
