#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-05_maps.png
# previous-hash: 78813c9510c8752c2f921d9791c8de77b8cf89e27f014b624f781f0be12481d8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png.nuxel-staged
printf '%s  %s\n' 78813c9510c8752c2f921d9791c8de77b8cf89e27f014b624f781f0be12481d8 /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-05_maps.png | grep -q 78813c9510c8752c2f921d9791c8de77b8cf89e27f014b624f781f0be12481d8
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
