#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-fb-owner-assert.sh (service: None, risk: medium)
# staged source: tools/beta/live/nuxel-fb-owner-assert.sh
# previous-hash: 46156b3477247549ff6730c9b9dc1180b71ae1bebcb3d116e1528ab2c12a773e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-rollback /usr/local/bin/nuxel-fb-owner-assert.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-fb-owner-assert.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-fb-owner-assert.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-fb-owner-assert.sh)"
if [ -e /usr/local/bin/nuxel-fb-owner-assert.sh ] && [ ! -e /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-fb-owner-assert.sh /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-staged
printf '%s  %s\n' 46156b3477247549ff6730c9b9dc1180b71ae1bebcb3d116e1528ab2c12a773e /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-staged /usr/local/bin/nuxel-fb-owner-assert.sh
sha256sum /usr/local/bin/nuxel-fb-owner-assert.sh | grep -q 46156b3477247549ff6730c9b9dc1180b71ae1bebcb3d116e1528ab2c12a773e
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
