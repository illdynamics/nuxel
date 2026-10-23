#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/css/launcher.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/launcher.css
# previous-hash: 9d56a005af3bf09e0c31d1869b7c34f071b285676a3cd7184371dd1de18573e3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/launcher.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/launcher.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/launcher.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged
printf '%s  %s\n' 9d56a005af3bf09e0c31d1869b7c34f071b285676a3cd7184371dd1de18573e3 /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/launcher.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/launcher.css | grep -q 9d56a005af3bf09e0c31d1869b7c34f071b285676a3cd7184371dd1de18573e3
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
