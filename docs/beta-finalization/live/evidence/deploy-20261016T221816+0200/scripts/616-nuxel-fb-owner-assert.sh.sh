#!/bin/sh
# boot-animation userspace runtime + asset placement -> /usr/local/bin/nuxel-fb-owner-assert.sh (service: None, risk: high)
# staged source: tools/beta/live/nuxel-fb-owner-assert.sh
# previous-hash: 46156b3477247549ff6730c9b9dc1180b71ae1bebcb3d116e1528ab2c12a773e
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-fb-owner-assert.sh)"
if [ -e /usr/local/bin/nuxel-fb-owner-assert.sh ]; then cp -a /usr/local/bin/nuxel-fb-owner-assert.sh /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-staged
printf '%s  %s\n' 46156b3477247549ff6730c9b9dc1180b71ae1bebcb3d116e1528ab2c12a773e /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-staged /usr/local/bin/nuxel-fb-owner-assert.sh
sha256sum /usr/local/bin/nuxel-fb-owner-assert.sh | grep -q 46156b3477247549ff6730c9b9dc1180b71ae1bebcb3d116e1528ab2c12a773e
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
systemctl daemon-reload
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb && test -s /usr/share/nuxel/boot/nuxel-boot-animation.mp4 && test -x /usr/lib/nuxel/nuxel-animation-claim
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-fb-owner-assert.sh.nuxel-rollback /usr/local/bin/nuxel-fb-owner-assert.sh; true; fi
