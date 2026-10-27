#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console-usb/index.html
# previous-hash: db2b5d0a02701cfcb46333b5d8e241053ccab52c0e5a46c04952ab31c39cb5b9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-rollback.pre-deploy-20261027T181522-2198480 /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-rollback.pre-deploy-20261027T181522-2198480; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-staged
printf '%s  %s\n' db2b5d0a02701cfcb46333b5d8e241053ccab52c0e5a46c04952ab31c39cb5b9 /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-usb/index.html | grep -q db2b5d0a02701cfcb46333b5d8e241053ccab52c0e5a46c04952ab31c39cb5b9
echo INSTALL-OK
