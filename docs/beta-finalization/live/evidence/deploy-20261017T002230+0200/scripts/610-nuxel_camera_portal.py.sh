#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py (service: None, risk: medium)
# staged source: shell/nuxel-camera-portal/nuxel_camera_portal.py
# previous-hash: 664e494a8f3806204c0b86666af3ccd2ee8ef7d979df15a9bde8d4d8a51f7a34
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py.nuxel-rollback /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py)"
if [ -e /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py ] && [ ! -e /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py.nuxel-staged
printf '%s  %s\n' 664e494a8f3806204c0b86666af3ccd2ee8ef7d979df15a9bde8d4d8a51f7a34 /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py.nuxel-staged /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py
sha256sum /usr/lib/nuxel/nuxel-camera-portal/nuxel_camera_portal.py | grep -q 664e494a8f3806204c0b86666af3ccd2ee8ef7d979df15a9bde8d4d8a51f7a34
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
