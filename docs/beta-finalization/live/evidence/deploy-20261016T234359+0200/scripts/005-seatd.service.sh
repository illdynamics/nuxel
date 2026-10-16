#!/bin/sh
# boot graph / session units -> /etc/systemd/system/seatd.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/seatd.service
# previous-hash: ea2b125001a1e22f50422d28edb2b0feef53fe1a2f3548489b1407adbb13b001
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/seatd.service.nuxel-rollback ]; then cp -a /etc/systemd/system/seatd.service.nuxel-rollback /etc/systemd/system/seatd.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/seatd.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/seatd.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/seatd.service)"
if [ -e /etc/systemd/system/seatd.service ] && [ ! -e /etc/systemd/system/seatd.service.nuxel-rollback ]; then cp -a /etc/systemd/system/seatd.service /etc/systemd/system/seatd.service.nuxel-rollback; fi
test -f /etc/systemd/system/seatd.service.nuxel-staged
printf '%s  %s\n' ea2b125001a1e22f50422d28edb2b0feef53fe1a2f3548489b1407adbb13b001 /etc/systemd/system/seatd.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/seatd.service.nuxel-staged /etc/systemd/system/seatd.service
sha256sum /etc/systemd/system/seatd.service | grep -q ea2b125001a1e22f50422d28edb2b0feef53fe1a2f3548489b1407adbb13b001
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
