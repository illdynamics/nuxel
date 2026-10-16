#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/manifest.json
# previous-hash: 6c008a9dc5b68763752fc822f7d064b34cc44afc0ecbd167c595ea1de4e47cfa
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json.nuxel-staged
printf '%s  %s\n' 6c008a9dc5b68763752fc822f7d064b34cc44afc0ecbd167c595ea1de4e47cfa /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/manifest.json | grep -q 6c008a9dc5b68763752fc822f7d064b34cc44afc0ecbd167c595ea1de4e47cfa
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
