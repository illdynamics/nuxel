#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/03-02_gallery.png
# previous-hash: ba6ca7fc18f622362b4ad336d3f344fcb960a2cf4386b12343782567a21466b7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png.nuxel-staged
printf '%s  %s\n' ba6ca7fc18f622362b4ad336d3f344fcb960a2cf4386b12343782567a21466b7 /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/03-02_gallery.png | grep -q ba6ca7fc18f622362b4ad336d3f344fcb960a2cf4386b12343782567a21466b7
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
