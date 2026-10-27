#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-home/css/widgets.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/widgets.css
# previous-hash: 5c25b127ad02cd885b363217db24ecd61d6fe33264949cf78ff117c297f95c05
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-home/css/widgets.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/widgets.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/widgets.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/widgets.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/widgets.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/widgets.css /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/widgets.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/widgets.css /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-staged
printf '%s  %s\n' 5c25b127ad02cd885b363217db24ecd61d6fe33264949cf78ff117c297f95c05 /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/widgets.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/widgets.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/widgets.css | grep -q 5c25b127ad02cd885b363217db24ecd61d6fe33264949cf78ff117c297f95c05
echo INSTALL-OK
