#!/bin/sh
# nuxel-web single-owner port and Wayland ordering repair -> /usr/lib/nuxel/nuxel-session.sh (service: None, risk: low)
# staged source: tools/s10plus/a29/nuxel-session.sh
# previous-hash: fc202ea3873bc883c51dc07db7b1264be6182c5edbb5ce0749be93f15d6c9e78
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback.pre-deploy-20261027T214530-2399261 /usr/lib/nuxel/nuxel-session.sh; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-session.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-session.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-session.sh)"
if [ -e /usr/lib/nuxel/nuxel-session.sh ] && [ ! -e /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-session.sh /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-session.sh ] && [ ! -e /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/lib/nuxel/nuxel-session.sh /usr/lib/nuxel/nuxel-session.sh.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /usr/lib/nuxel/nuxel-session.sh.nuxel-staged
printf '%s  %s\n' fc202ea3873bc883c51dc07db7b1264be6182c5edbb5ce0749be93f15d6c9e78 /usr/lib/nuxel/nuxel-session.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-session.sh.nuxel-staged /usr/lib/nuxel/nuxel-session.sh
sha256sum /usr/lib/nuxel/nuxel-session.sh | grep -q fc202ea3873bc883c51dc07db7b1264be6182c5edbb5ce0749be93f15d6c9e78
echo INSTALL-OK
