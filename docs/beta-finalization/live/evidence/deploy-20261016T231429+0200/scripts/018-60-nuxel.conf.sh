#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf (service: None, risk: medium)
# staged source: configs/nuxel/bluetooth/main.conf.d/60-nuxel.conf
# previous-hash: 3497a02e5145854e319754f82d03ee2799231f5abb7d1db6d83f5d415cc14112
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-rollback ]; then cp -a /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-rollback /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf)"
if [ -e /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf ] && [ ! -e /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-rollback ]; then cp -a /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-rollback; fi
test -f /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-staged
printf '%s  %s\n' 3497a02e5145854e319754f82d03ee2799231f5abb7d1db6d83f5d415cc14112 /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-staged /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf
sha256sum /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf | grep -q 3497a02e5145854e319754f82d03ee2799231f5abb7d1db6d83f5d415cc14112
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
