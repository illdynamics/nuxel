#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/manifest.json
# previous-hash: 0376ed07583a5009a95eb5f366950e865dc69edc4de098dcb634b80324f22f05
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json.nuxel-staged
printf '%s  %s\n' 0376ed07583a5009a95eb5f366950e865dc69edc4de098dcb634b80324f22f05 /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/manifest.json | grep -q 0376ed07583a5009a95eb5f366950e865dc69edc4de098dcb634b80324f22f05
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
