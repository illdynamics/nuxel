#!/bin/sh
# Native browser control FIFO and can_go_back/can_go_forward state -> /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py (service: None, risk: low)
# staged source: shell/nuxel-browser-native/nuxel_browser_native.py
# previous-hash: 190a811d75bf629532fb7abb7c6b017977a751a3a92dc8d004718ae2eabf5700
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-rollback.pre-deploy-20261028T100242-2721366 ]; then cp -a /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-rollback.pre-deploy-20261028T100242-2721366 /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py)"
if [ -e /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py ] && [ ! -e /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py ] && [ ! -e /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-rollback.pre-deploy-20261028T100242-2721366 ]; then cp -a /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-rollback.pre-deploy-20261028T100242-2721366; fi
test -f /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-staged
printf '%s  %s\n' 190a811d75bf629532fb7abb7c6b017977a751a3a92dc8d004718ae2eabf5700 /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py.nuxel-staged /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py
sha256sum /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py | grep -q 190a811d75bf629532fb7abb7c6b017977a751a3a92dc8d004718ae2eabf5700
echo INSTALL-OK
