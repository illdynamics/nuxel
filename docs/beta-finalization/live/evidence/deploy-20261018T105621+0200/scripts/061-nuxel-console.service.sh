#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-console.service (service: None, risk: medium)
# staged source: services/nuxel-console/systemd/nuxel-console.service
# previous-hash: 94802ce65133408688877ffde10c97ada244d262d1b8e928cf6f94d4af8e67e1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-console.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-console.service.nuxel-rollback /etc/systemd/system/nuxel-console.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-console.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-console.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-console.service)"
if [ -e /etc/systemd/system/nuxel-console.service ] && [ ! -e /etc/systemd/system/nuxel-console.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-console.service /etc/systemd/system/nuxel-console.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-console.service.nuxel-staged
printf '%s  %s\n' 94802ce65133408688877ffde10c97ada244d262d1b8e928cf6f94d4af8e67e1 /etc/systemd/system/nuxel-console.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-console.service.nuxel-staged /etc/systemd/system/nuxel-console.service
sha256sum /etc/systemd/system/nuxel-console.service | grep -q 94802ce65133408688877ffde10c97ada244d262d1b8e928cf6f94d4af8e67e1
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
