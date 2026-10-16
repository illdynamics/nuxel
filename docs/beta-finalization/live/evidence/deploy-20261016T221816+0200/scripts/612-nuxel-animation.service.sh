#!/bin/sh
# boot-animation userspace runtime + asset placement -> /etc/systemd/system/nuxel-animation.service (service: None, risk: high)
# staged source: services/nuxel-animation/systemd/nuxel-animation.service
# previous-hash: 199e1e9805c5b34c3adc8ce5889ea37080dd01f4c2e2ddf09fba2dfddc0b38db
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-animation.service)"
if [ -e /etc/systemd/system/nuxel-animation.service ]; then cp -a /etc/systemd/system/nuxel-animation.service /etc/systemd/system/nuxel-animation.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-animation.service.nuxel-staged
printf '%s  %s\n' 199e1e9805c5b34c3adc8ce5889ea37080dd01f4c2e2ddf09fba2dfddc0b38db /etc/systemd/system/nuxel-animation.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-animation.service.nuxel-staged /etc/systemd/system/nuxel-animation.service
sha256sum /etc/systemd/system/nuxel-animation.service | grep -q 199e1e9805c5b34c3adc8ce5889ea37080dd01f4c2e2ddf09fba2dfddc0b38db
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
systemctl daemon-reload
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb && test -s /usr/share/nuxel/boot/nuxel-boot-animation.mp4 && test -x /usr/lib/nuxel/nuxel-animation-claim
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-animation.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-animation.service.nuxel-rollback /etc/systemd/system/nuxel-animation.service; true; fi
