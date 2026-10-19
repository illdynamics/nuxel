#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/pwa/nuxel-home/css/launcher.css (service: nuxel-wayland, risk: high)
# staged source: pwa/nuxel-home/css/launcher.css
# previous-hash: ca24bbadae42e1236da886bc48ce2104a59a2b0384a2ef305025e2503eae412c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/launcher.css; systemctl restart nuxel-wayland; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/launcher.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/launcher.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged
printf '%s  %s\n' ca24bbadae42e1236da886bc48ce2104a59a2b0384a2ef305025e2503eae412c /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/launcher.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/launcher.css | grep -q ca24bbadae42e1236da886bc48ce2104a59a2b0384a2ef305025e2503eae412c
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
echo INSTALL-OK
