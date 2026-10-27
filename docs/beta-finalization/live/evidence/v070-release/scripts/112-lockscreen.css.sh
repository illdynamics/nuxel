#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/css/lockscreen.css
# previous-hash: 74bf60926bcd256008a2428bdb33eedcf5ea53016fc952725aa1d8e26f08f01d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-staged
printf '%s  %s\n' 74bf60926bcd256008a2428bdb33eedcf5ea53016fc952725aa1d8e26f08f01d /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css | grep -q 74bf60926bcd256008a2428bdb33eedcf5ea53016fc952725aa1d8e26f08f01d
echo INSTALL-OK
