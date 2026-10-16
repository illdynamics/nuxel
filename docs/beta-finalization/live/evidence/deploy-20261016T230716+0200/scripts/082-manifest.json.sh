#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/manifest.json
# previous-hash: c904a9b5ad01eb8f498aacb0ea3f09fe815fae0a24668f22fa72b642210a7938
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json.nuxel-staged
printf '%s  %s\n' c904a9b5ad01eb8f498aacb0ea3f09fe815fae0a24668f22fa72b642210a7938 /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/manifest.json | grep -q c904a9b5ad01eb8f498aacb0ea3f09fe815fae0a24668f22fa72b642210a7938
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
