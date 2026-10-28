#!/bin/sh
# Bounded pre-lockscreen video controller, systemd unit, durable config and supplied clip -> /etc/nuxel/boot/preload-cinema.json (service: None, risk: low)
# staged source: configs/nuxel/boot/preload-cinema.json
# previous-hash: fc1f578ceee799e86130833325fab75f80c92e414233ce04cd743594dfb8810b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/boot/preload-cinema.json.nuxel-rollback.pre-deploy-20261028T105710-2836090 ]; then cp -a /etc/nuxel/boot/preload-cinema.json.nuxel-rollback.pre-deploy-20261028T105710-2836090 /etc/nuxel/boot/preload-cinema.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/boot/preload-cinema.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/boot/preload-cinema.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/boot/preload-cinema.json)"
if [ -e /etc/nuxel/boot/preload-cinema.json ] && [ ! -e /etc/nuxel/boot/preload-cinema.json.nuxel-rollback ]; then cp -a /etc/nuxel/boot/preload-cinema.json /etc/nuxel/boot/preload-cinema.json.nuxel-rollback; fi
if [ -e /etc/nuxel/boot/preload-cinema.json ] && [ ! -e /etc/nuxel/boot/preload-cinema.json.nuxel-rollback.pre-deploy-20261028T105710-2836090 ]; then cp -a /etc/nuxel/boot/preload-cinema.json /etc/nuxel/boot/preload-cinema.json.nuxel-rollback.pre-deploy-20261028T105710-2836090; fi
test -f /etc/nuxel/boot/preload-cinema.json.nuxel-staged
printf '%s  %s\n' fc1f578ceee799e86130833325fab75f80c92e414233ce04cd743594dfb8810b /etc/nuxel/boot/preload-cinema.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/boot/preload-cinema.json.nuxel-staged /etc/nuxel/boot/preload-cinema.json
sha256sum /etc/nuxel/boot/preload-cinema.json | grep -q fc1f578ceee799e86130833325fab75f80c92e414233ce04cd743594dfb8810b
echo INSTALL-OK
