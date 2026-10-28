#!/bin/sh
# Bounded pre-lockscreen video controller, systemd unit, durable config and supplied clip -> /etc/nuxel/boot/preload-cinema.json (service: None, risk: low)
# staged source: configs/nuxel/boot/preload-cinema.json
# previous-hash: 43efe695788c8480e0ad116faa02f2683c0b45d395b3833c06899021464c5e65
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/boot/preload-cinema.json.nuxel-rollback.pre-deploy-20261028T105440-2833780 ]; then cp -a /etc/nuxel/boot/preload-cinema.json.nuxel-rollback.pre-deploy-20261028T105440-2833780 /etc/nuxel/boot/preload-cinema.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/boot/preload-cinema.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/boot/preload-cinema.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/boot/preload-cinema.json)"
if [ -e /etc/nuxel/boot/preload-cinema.json ] && [ ! -e /etc/nuxel/boot/preload-cinema.json.nuxel-rollback ]; then cp -a /etc/nuxel/boot/preload-cinema.json /etc/nuxel/boot/preload-cinema.json.nuxel-rollback; fi
if [ -e /etc/nuxel/boot/preload-cinema.json ] && [ ! -e /etc/nuxel/boot/preload-cinema.json.nuxel-rollback.pre-deploy-20261028T105440-2833780 ]; then cp -a /etc/nuxel/boot/preload-cinema.json /etc/nuxel/boot/preload-cinema.json.nuxel-rollback.pre-deploy-20261028T105440-2833780; fi
test -f /etc/nuxel/boot/preload-cinema.json.nuxel-staged
printf '%s  %s\n' 43efe695788c8480e0ad116faa02f2683c0b45d395b3833c06899021464c5e65 /etc/nuxel/boot/preload-cinema.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/boot/preload-cinema.json.nuxel-staged /etc/nuxel/boot/preload-cinema.json
sha256sum /etc/nuxel/boot/preload-cinema.json | grep -q 43efe695788c8480e0ad116faa02f2683c0b45d395b3833c06899021464c5e65
echo INSTALL-OK
