#!/bin/sh
# A37 owner PNG branding + webroot JS/CSS/SW, boot/volume cues, haptics settings -> /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png (service: None, risk: high)
# staged source: assets/nuxel-applications-icon-pack/05-02_system-monitor.png
# previous-hash: 79028fd0deb88fe79659d761fda5530a3140e6aa99cd21763b1f3bd73dee9fda
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png.nuxel-rollback /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png)"
if [ -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png ] && [ ! -e /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png.nuxel-rollback; fi
test -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png.nuxel-staged
printf '%s  %s\n' 79028fd0deb88fe79659d761fda5530a3140e6aa99cd21763b1f3bd73dee9fda /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png.nuxel-staged /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png
sha256sum /usr/share/nuxel/assets/nuxel-applications-icon-pack/05-02_system-monitor.png | grep -q 79028fd0deb88fe79659d761fda5530a3140e6aa99cd21763b1f3bd73dee9fda
( systemctl daemon-reload && systemctl try-restart nuxel-web.service && systemctl enable nuxel-boot-sound.service ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
