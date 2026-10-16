#!/bin/sh
# touch / hardware buttons -> /etc/systemd/system/nuxel-bootmode-guard.service (service: nuxel-touch-arm, risk: medium)
# staged source: configs/nuxel/touch/nuxel-bootmode-guard.service
# previous-hash: a40e1e6b56da857ffb0fdd04f8092d492c9d4f11c04cfa9debf38f3bda83505d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-bootmode-guard.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bootmode-guard.service.nuxel-rollback /etc/systemd/system/nuxel-bootmode-guard.service; systemctl restart nuxel-touch-arm; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-bootmode-guard.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-bootmode-guard.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-bootmode-guard.service)"
if [ -e /etc/systemd/system/nuxel-bootmode-guard.service ] && [ ! -e /etc/systemd/system/nuxel-bootmode-guard.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bootmode-guard.service /etc/systemd/system/nuxel-bootmode-guard.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-bootmode-guard.service.nuxel-staged
printf '%s  %s\n' a40e1e6b56da857ffb0fdd04f8092d492c9d4f11c04cfa9debf38f3bda83505d /etc/systemd/system/nuxel-bootmode-guard.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-bootmode-guard.service.nuxel-staged /etc/systemd/system/nuxel-bootmode-guard.service
sha256sum /etc/systemd/system/nuxel-bootmode-guard.service | grep -q a40e1e6b56da857ffb0fdd04f8092d492c9d4f11c04cfa9debf38f3bda83505d
systemctl restart nuxel-touch-arm
systemctl is-active nuxel-touch-arm
echo INSTALL-OK
