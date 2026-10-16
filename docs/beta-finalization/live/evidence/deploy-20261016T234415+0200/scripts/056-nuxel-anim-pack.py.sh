#!/bin/sh
# boot-animation userspace runtime + asset placement -> /usr/lib/nuxel/nuxel-anim-pack.py (service: None, risk: high)
# staged source: tools/s10plus/nuxel-anim-pack.py
# previous-hash: 2c382f6442369815fc11cfd19b9f3bd6f75f6d94ec40a9e048f4dce5a312a567
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-rollback /usr/lib/nuxel/nuxel-anim-pack.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
if [ -e /usr/lib/nuxel/nuxel-anim-pack.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-anim-pack.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-anim-pack.py)"
if [ -e /usr/lib/nuxel/nuxel-anim-pack.py ] && [ ! -e /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-anim-pack.py /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-staged
printf '%s  %s\n' 2c382f6442369815fc11cfd19b9f3bd6f75f6d94ec40a9e048f4dce5a312a567 /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-anim-pack.py.nuxel-staged /usr/lib/nuxel/nuxel-anim-pack.py
sha256sum /usr/lib/nuxel/nuxel-anim-pack.py | grep -q 2c382f6442369815fc11cfd19b9f3bd6f75f6d94ec40a9e048f4dce5a312a567
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
echo INSTALL-OK
