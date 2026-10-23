#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/osd.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/osd.js
# previous-hash: 7c658be63ae365cc4bcf84d9b3975d14108fae5ce37a3c5cca120ceb49c427b6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/osd.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/osd.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/osd.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/osd.js /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged
printf '%s  %s\n' 7c658be63ae365cc4bcf84d9b3975d14108fae5ce37a3c5cca120ceb49c427b6 /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/osd.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/osd.js | grep -q 7c658be63ae365cc4bcf84d9b3975d14108fae5ce37a3c5cca120ceb49c427b6
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
