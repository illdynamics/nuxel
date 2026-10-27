#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-common/theme.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/theme.css
# previous-hash: fb39d474dcabf6dfd48c337931068df6f62733716e82cdcc71dc0ed67caa085f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-common/theme.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/theme.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/theme.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/theme.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/theme.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/theme.css /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/theme.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/theme.css /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-staged
printf '%s  %s\n' fb39d474dcabf6dfd48c337931068df6f62733716e82cdcc71dc0ed67caa085f /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/theme.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/theme.css
sha256sum /usr/share/nuxel/pwa/nuxel-common/theme.css | grep -q fb39d474dcabf6dfd48c337931068df6f62733716e82cdcc71dc0ed67caa085f
echo INSTALL-OK
