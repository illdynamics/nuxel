#!/bin/sh
# boot graph / session units -> /etc/systemd/system/nuxel-wl-fb.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/nuxel-wl-fb.service
# previous-hash: 75d7091c864913d3a7b1c9688d97b169239e37fef1aad3c844b9b263f1a48da4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-wl-fb.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-wl-fb.service.nuxel-rollback /etc/systemd/system/nuxel-wl-fb.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-wl-fb.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-wl-fb.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-wl-fb.service)"
if [ -e /etc/systemd/system/nuxel-wl-fb.service ] && [ ! -e /etc/systemd/system/nuxel-wl-fb.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-wl-fb.service /etc/systemd/system/nuxel-wl-fb.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-wl-fb.service.nuxel-staged
printf '%s  %s\n' 75d7091c864913d3a7b1c9688d97b169239e37fef1aad3c844b9b263f1a48da4 /etc/systemd/system/nuxel-wl-fb.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-wl-fb.service.nuxel-staged /etc/systemd/system/nuxel-wl-fb.service
sha256sum /etc/systemd/system/nuxel-wl-fb.service | grep -q 75d7091c864913d3a7b1c9688d97b169239e37fef1aad3c844b9b263f1a48da4
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
