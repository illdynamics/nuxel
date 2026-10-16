#!/bin/sh
# boot-animation userspace runtime + asset placement -> /usr/lib/nuxel/nuxel-animation-claim (service: None, risk: high)
# staged source: services/nuxel-animation/bin/nuxel-animation-claim
# previous-hash: b35e63688242a1b1f1381600ede42f559bcd0fee82c75ebcc87b147eb839a10d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-animation-claim.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-animation-claim.nuxel-rollback /usr/lib/nuxel/nuxel-animation-claim; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
if [ -e /usr/lib/nuxel/nuxel-animation-claim ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-animation-claim | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-animation-claim)"
if [ -e /usr/lib/nuxel/nuxel-animation-claim ] && [ ! -e /usr/lib/nuxel/nuxel-animation-claim.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-animation-claim /usr/lib/nuxel/nuxel-animation-claim.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-animation-claim.nuxel-staged
printf '%s  %s\n' b35e63688242a1b1f1381600ede42f559bcd0fee82c75ebcc87b147eb839a10d /usr/lib/nuxel/nuxel-animation-claim.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-animation-claim.nuxel-staged /usr/lib/nuxel/nuxel-animation-claim
sha256sum /usr/lib/nuxel/nuxel-animation-claim | grep -q b35e63688242a1b1f1381600ede42f559bcd0fee82c75ebcc87b147eb839a10d
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
echo INSTALL-OK
