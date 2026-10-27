#!/bin/sh
# Settings PWA (Bluetooth/Displays/Audio pages) + Home QS + shared bridge client -> /usr/share/nuxel/pwa/nuxel-home/js/qs.js (service: nuxel-http-bridge, risk: low)
# staged source: pwa/nuxel-home/js/qs.js
# previous-hash: 92bfd26af4cd23ba21f4ee8aac3f841799f736851cf7b3b817a8271bacdddb79
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback.pre-deploy-20261027T173716-2158850 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback.pre-deploy-20261027T173716-2158850 /usr/share/nuxel/pwa/nuxel-home/js/qs.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/qs.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/qs.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/qs.js /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback.pre-deploy-20261027T173716-2158850 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/qs.js /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback.pre-deploy-20261027T173716-2158850; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged
printf '%s  %s\n' 92bfd26af4cd23ba21f4ee8aac3f841799f736851cf7b3b817a8271bacdddb79 /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/qs.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/qs.js | grep -q 92bfd26af4cd23ba21f4ee8aac3f841799f736851cf7b3b817a8271bacdddb79
echo INSTALL-OK
