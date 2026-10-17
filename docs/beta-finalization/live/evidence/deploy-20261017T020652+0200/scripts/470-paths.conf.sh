#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/paths.conf (service: None, risk: medium)
# staged source: configs/nuxel/paths.conf
# previous-hash: bcdfc4b4035d4ca86d90bceb50fe9a0b47873f61fa56c10976ac3a75f1e1dffe
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/paths.conf.nuxel-rollback ]; then cp -a /etc/nuxel/paths.conf.nuxel-rollback /etc/nuxel/paths.conf; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/paths.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/paths.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/paths.conf)"
if [ -e /etc/nuxel/paths.conf ] && [ ! -e /etc/nuxel/paths.conf.nuxel-rollback ]; then cp -a /etc/nuxel/paths.conf /etc/nuxel/paths.conf.nuxel-rollback; fi
test -f /etc/nuxel/paths.conf.nuxel-staged
printf '%s  %s\n' bcdfc4b4035d4ca86d90bceb50fe9a0b47873f61fa56c10976ac3a75f1e1dffe /etc/nuxel/paths.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/paths.conf.nuxel-staged /etc/nuxel/paths.conf
sha256sum /etc/nuxel/paths.conf | grep -q bcdfc4b4035d4ca86d90bceb50fe9a0b47873f61fa56c10976ac3a75f1e1dffe
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
