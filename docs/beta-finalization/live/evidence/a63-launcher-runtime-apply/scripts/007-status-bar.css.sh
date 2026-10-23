#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/status-bar.css
# previous-hash: b6e469ee2ee1781f3e855180da40afeb2850563f9907a3a9579744463020e9e3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged
printf '%s  %s\n' b6e469ee2ee1781f3e855180da40afeb2850563f9907a3a9579744463020e9e3 /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css | grep -q b6e469ee2ee1781f3e855180da40afeb2850563f9907a3a9579744463020e9e3
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
