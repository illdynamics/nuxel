#!/bin/sh
# boot-animation userspace runtime + asset placement -> /usr/lib/nuxel/nuxel-anim-pack.py (service: None, risk: high)
# staged source: tools/s10plus/nuxel-anim-pack.py
# previous-hash: 2c382f6442369815fc11cfd19b9f3bd6f75f6d94ec40a9e048f4dce5a312a567
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-anim-pack.py)"
if [ -e /usr/lib/nuxel/nuxel-anim-pack.py ]; then cp -a /usr/lib/nuxel/nuxel-anim-pack.py /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-staged
printf '%s  %s\n' 2c382f6442369815fc11cfd19b9f3bd6f75f6d94ec40a9e048f4dce5a312a567 /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-staged /usr/lib/nuxel/nuxel-anim-pack.py
sha256sum /usr/lib/nuxel/nuxel-anim-pack.py | grep -q 2c382f6442369815fc11cfd19b9f3bd6f75f6d94ec40a9e048f4dce5a312a567
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
systemctl daemon-reload
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb && test -s /usr/share/nuxel/boot/nuxel-boot-animation.mp4 && test -x /usr/lib/nuxel/nuxel-animation-claim
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-rollback /usr/lib/nuxel/nuxel-anim-pack.py; true; fi
