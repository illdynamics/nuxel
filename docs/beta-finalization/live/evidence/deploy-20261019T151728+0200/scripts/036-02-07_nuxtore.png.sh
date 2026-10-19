#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-07_nuxtore.png
# previous-hash: 8a91daf351204f2b78db0cf53b22645462d6893a0eb168f9c804df96061e69f4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png.nuxel-staged
printf '%s  %s\n' 8a91daf351204f2b78db0cf53b22645462d6893a0eb168f9c804df96061e69f4 /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-07_nuxtore.png | grep -q 8a91daf351204f2b78db0cf53b22645462d6893a0eb168f9c804df96061e69f4
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
