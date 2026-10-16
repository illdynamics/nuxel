#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/samples/tone-440.wav
# previous-hash: 940d094f04d24371f4b51619613058543db8a934c4a0926990e6536a7999b386
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav.nuxel-staged
printf '%s  %s\n' 940d094f04d24371f4b51619613058543db8a934c4a0926990e6536a7999b386 /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/samples/tone-440.wav | grep -q 940d094f04d24371f4b51619613058543db8a934c4a0926990e6536a7999b386
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
