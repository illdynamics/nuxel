#!/bin/sh
# Start native Stevia OSK + nuxel-navdock from the phone session -> /usr/lib/nuxel/nuxel-session.sh (service: nuxel-wayland, risk: low)
# staged source: tools/s10plus/a29/nuxel-session.sh
# previous-hash: 9fef778096913d63aa2b75221bf5f553487218a9431b63327287275438d1ae07
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback.pre-deploy-20261028T100242-2721366 ]; then cp -a /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback.pre-deploy-20261028T100242-2721366 /usr/lib/nuxel/nuxel-session.sh; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-session.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-session.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-session.sh)"
if [ -e /usr/lib/nuxel/nuxel-session.sh ] && [ ! -e /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-session.sh /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-session.sh ] && [ ! -e /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback.pre-deploy-20261028T100242-2721366 ]; then cp -a /usr/lib/nuxel/nuxel-session.sh /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback.pre-deploy-20261028T100242-2721366; fi
test -f /usr/lib/nuxel/nuxel-session.sh.nuxel-staged
printf '%s  %s\n' 9fef778096913d63aa2b75221bf5f553487218a9431b63327287275438d1ae07 /usr/lib/nuxel/nuxel-session.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-session.sh.nuxel-staged /usr/lib/nuxel/nuxel-session.sh
sha256sum /usr/lib/nuxel/nuxel-session.sh | grep -q 9fef778096913d63aa2b75221bf5f553487218a9431b63327287275438d1ae07
echo INSTALL-OK
