#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/icons/icon-152.png
# previous-hash: ec29f0eaca2b0584846a37b8090cb67af09451112d3ad9cc82347a4230ec24e3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png.nuxel-staged
printf '%s  %s\n' ec29f0eaca2b0584846a37b8090cb67af09451112d3ad9cc82347a4230ec24e3 /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-152.png | grep -q ec29f0eaca2b0584846a37b8090cb67af09451112d3ad9cc82347a4230ec24e3
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
