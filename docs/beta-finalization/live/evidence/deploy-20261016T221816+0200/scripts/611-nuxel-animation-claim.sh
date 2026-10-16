#!/bin/sh
# boot-animation userspace runtime + asset placement -> /usr/lib/nuxel/nuxel-animation-claim (service: None, risk: high)
# staged source: services/nuxel-animation/bin/nuxel-animation-claim
# previous-hash: b35e63688242a1b1f1381600ede42f559bcd0fee82c75ebcc87b147eb839a10d
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-animation-claim)"
if [ -e /usr/lib/nuxel/nuxel-animation-claim ]; then cp -a /usr/lib/nuxel/nuxel-animation-claim /usr/lib/nuxel/nuxel-animation-claim.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-animation-claim.nuxel-staged
printf '%s  %s\n' b35e63688242a1b1f1381600ede42f559bcd0fee82c75ebcc87b147eb839a10d /usr/lib/nuxel/nuxel-animation-claim.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-animation-claim.nuxel-staged /usr/lib/nuxel/nuxel-animation-claim
sha256sum /usr/lib/nuxel/nuxel-animation-claim | grep -q b35e63688242a1b1f1381600ede42f559bcd0fee82c75ebcc87b147eb839a10d
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
systemctl daemon-reload
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb && test -s /usr/share/nuxel/boot/nuxel-boot-animation.mp4 && test -x /usr/lib/nuxel/nuxel-animation-claim
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-animation-claim.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-animation-claim.nuxel-rollback /usr/lib/nuxel/nuxel-animation-claim; true; fi
