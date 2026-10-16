#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/power-menu.css
# previous-hash: b649aac15b48d8f5a65115d0a0a79b7b67f5874c805d21561eaace56c7630fdb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-staged
printf '%s  %s\n' b649aac15b48d8f5a65115d0a0a79b7b67f5874c805d21561eaace56c7630fdb /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css | grep -q b649aac15b48d8f5a65115d0a0a79b7b67f5874c805d21561eaace56c7630fdb
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
