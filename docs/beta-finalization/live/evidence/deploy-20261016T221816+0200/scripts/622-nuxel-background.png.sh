#!/bin/sh
# boot-animation userspace runtime + asset placement -> /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png (service: nuxel-wayland, risk: high)
# staged source: assets/nuxel-background.png
# previous-hash: 6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png.nuxel-staged
printf '%s  %s\n' 6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29 /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png | grep -q 6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb && test -s /usr/share/nuxel/boot/nuxel-boot-animation.mp4 && test -x /usr/lib/nuxel/nuxel-animation-claim
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/assets/nuxel-background.png; systemctl restart nuxel-wayland; fi
