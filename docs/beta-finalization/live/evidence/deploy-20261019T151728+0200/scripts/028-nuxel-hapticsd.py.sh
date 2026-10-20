#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/lib/nuxel/nuxel-hapticsd.py (service: None, risk: high)
# staged source: services/nuxel-haptics/nuxel-hapticsd.py
# previous-hash: 9264f64d952adb8a52f3e9169726ce51ad1184a634e8448b1a5680e79f86e8ff
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-hapticsd.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-hapticsd.py.nuxel-rollback /usr/lib/nuxel/nuxel-hapticsd.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-hapticsd.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-hapticsd.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-hapticsd.py)"
if [ -e /usr/lib/nuxel/nuxel-hapticsd.py ] && [ ! -e /usr/lib/nuxel/nuxel-hapticsd.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-hapticsd.py /usr/lib/nuxel/nuxel-hapticsd.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-hapticsd.py.nuxel-staged
printf '%s  %s\n' 9264f64d952adb8a52f3e9169726ce51ad1184a634e8448b1a5680e79f86e8ff /usr/lib/nuxel/nuxel-hapticsd.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-hapticsd.py.nuxel-staged /usr/lib/nuxel/nuxel-hapticsd.py
sha256sum /usr/lib/nuxel/nuxel-hapticsd.py | grep -q 9264f64d952adb8a52f3e9169726ce51ad1184a634e8448b1a5680e79f86e8ff
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
