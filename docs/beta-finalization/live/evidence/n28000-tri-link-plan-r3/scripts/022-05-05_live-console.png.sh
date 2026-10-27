#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png (service: None, risk: low)
# staged source: assets/nuxel-applications-icon-pack/05-05_live-console.png
# previous-hash: c695dedd90d5025e33902e2e8ad5f072480084af8950f7c27f435399ac79e6c2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback.pre-deploy-20261027T164448-2130897 ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback.pre-deploy-20261027T164448-2130897 /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback.pre-deploy-20261027T164448-2130897 ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-rollback.pre-deploy-20261027T164448-2130897; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-staged
printf '%s  %s\n' c695dedd90d5025e33902e2e8ad5f072480084af8950f7c27f435399ac79e6c2 /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-05_live-console.png | grep -q c695dedd90d5025e33902e2e8ad5f072480084af8950f7c27f435399ac79e6c2
echo INSTALL-OK
