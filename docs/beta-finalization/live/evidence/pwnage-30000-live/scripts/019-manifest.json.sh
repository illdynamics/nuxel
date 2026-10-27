#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/manifest.json
# previous-hash: 5dcdda22e66f69bffd418ba6cebdc01a81de784c9904be6afbf7102e8a67bcba
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-staged
printf '%s  %s\n' 5dcdda22e66f69bffd418ba6cebdc01a81de784c9904be6afbf7102e8a67bcba /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/manifest.json | grep -q 5dcdda22e66f69bffd418ba6cebdc01a81de784c9904be6afbf7102e8a67bcba
echo INSTALL-OK
