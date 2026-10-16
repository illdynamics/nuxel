#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/app-registry/README-app-registry.md (service: None, risk: medium)
# staged source: configs/nuxel/app-registry/README-app-registry.md
# previous-hash: cb3bf374db96bd182b37bc7dfeffad26508cb8fe648df5101ed5c431707a0fcd
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/app-registry/README-app-registry.md.nuxel-rollback ]; then cp -a /etc/nuxel/app-registry/README-app-registry.md.nuxel-rollback /etc/nuxel/app-registry/README-app-registry.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/app-registry/README-app-registry.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/app-registry/README-app-registry.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/app-registry/README-app-registry.md)"
if [ -e /etc/nuxel/app-registry/README-app-registry.md ] && [ ! -e /etc/nuxel/app-registry/README-app-registry.md.nuxel-rollback ]; then cp -a /etc/nuxel/app-registry/README-app-registry.md /etc/nuxel/app-registry/README-app-registry.md.nuxel-rollback; fi
test -f /etc/nuxel/app-registry/README-app-registry.md.nuxel-staged
printf '%s  %s\n' cb3bf374db96bd182b37bc7dfeffad26508cb8fe648df5101ed5c431707a0fcd /etc/nuxel/app-registry/README-app-registry.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/app-registry/README-app-registry.md.nuxel-staged /etc/nuxel/app-registry/README-app-registry.md
sha256sum /etc/nuxel/app-registry/README-app-registry.md | grep -q cb3bf374db96bd182b37bc7dfeffad26508cb8fe648df5101ed5c431707a0fcd
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
