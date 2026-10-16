#!/bin/sh
# boot-animation userspace runtime + asset placement -> /etc/systemd/system/nuxel-animation.service (service: None, risk: high)
# staged source: services/nuxel-animation/systemd/nuxel-animation.service
# previous-hash: 199e1e9805c5b34c3adc8ce5889ea37080dd01f4c2e2ddf09fba2dfddc0b38db
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-animation.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-animation.service.nuxel-rollback /etc/systemd/system/nuxel-animation.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
if [ -e /etc/systemd/system/nuxel-animation.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-animation.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-animation.service)"
if [ -e /etc/systemd/system/nuxel-animation.service ] && [ ! -e /etc/systemd/system/nuxel-animation.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-animation.service /etc/systemd/system/nuxel-animation.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-animation.service.nuxel-staged
printf '%s  %s\n' 199e1e9805c5b34c3adc8ce5889ea37080dd01f4c2e2ddf09fba2dfddc0b38db /etc/systemd/system/nuxel-animation.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-animation.service.nuxel-staged /etc/systemd/system/nuxel-animation.service
sha256sum /etc/systemd/system/nuxel-animation.service | grep -q 199e1e9805c5b34c3adc8ce5889ea37080dd01f4c2e2ddf09fba2dfddc0b38db
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
echo INSTALL-OK
