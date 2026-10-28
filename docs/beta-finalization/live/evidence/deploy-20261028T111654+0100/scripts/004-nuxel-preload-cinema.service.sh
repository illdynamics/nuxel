#!/bin/sh
# Bounded pre-lockscreen video controller, systemd unit, durable config and supplied clip -> /etc/systemd/system/nuxel-preload-cinema.service (service: None, risk: low)
# staged source: services/nuxel-preload-cinema/nuxel-preload-cinema.service
# previous-hash: 070566f55b4cdd9dcc792e2d02026d1b57bd468d20a62bf98acb72b02f07d865
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-preload-cinema.service.nuxel-rollback.pre-deploy-20261028T111654-2859179 ]; then cp -a /etc/systemd/system/nuxel-preload-cinema.service.nuxel-rollback.pre-deploy-20261028T111654-2859179 /etc/systemd/system/nuxel-preload-cinema.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-preload-cinema.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-preload-cinema.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-preload-cinema.service)"
if [ -e /etc/systemd/system/nuxel-preload-cinema.service ] && [ ! -e /etc/systemd/system/nuxel-preload-cinema.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-preload-cinema.service /etc/systemd/system/nuxel-preload-cinema.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-preload-cinema.service ] && [ ! -e /etc/systemd/system/nuxel-preload-cinema.service.nuxel-rollback.pre-deploy-20261028T111654-2859179 ]; then cp -a /etc/systemd/system/nuxel-preload-cinema.service /etc/systemd/system/nuxel-preload-cinema.service.nuxel-rollback.pre-deploy-20261028T111654-2859179; fi
test -f /etc/systemd/system/nuxel-preload-cinema.service.nuxel-staged
printf '%s  %s\n' 070566f55b4cdd9dcc792e2d02026d1b57bd468d20a62bf98acb72b02f07d865 /etc/systemd/system/nuxel-preload-cinema.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-preload-cinema.service.nuxel-staged /etc/systemd/system/nuxel-preload-cinema.service
sha256sum /etc/systemd/system/nuxel-preload-cinema.service | grep -q 070566f55b4cdd9dcc792e2d02026d1b57bd468d20a62bf98acb72b02f07d865
echo INSTALL-OK
