#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/02-02_contacts.png
# previous-hash: a1d161080b61e2549dd1c6a6b3c32c197d204c58e587252286b667ca48a3b07f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png.nuxel-staged
printf '%s  %s\n' a1d161080b61e2549dd1c6a6b3c32c197d204c58e587252286b667ca48a3b07f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/02-02_contacts.png | grep -q a1d161080b61e2549dd1c6a6b3c32c197d204c58e587252286b667ca48a3b07f
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
