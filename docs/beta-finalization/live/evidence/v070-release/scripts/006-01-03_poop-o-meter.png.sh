#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png
# previous-hash: 6b113b3cd9559924b6c534a93d6154efcb08c1a0a25fa21ae2cd646e4e8b6c40
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-staged
printf '%s  %s\n' 6b113b3cd9559924b6c534a93d6154efcb08c1a0a25fa21ae2cd646e4e8b6c40 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-03_poop-o-meter.png | grep -q 6b113b3cd9559924b6c534a93d6154efcb08c1a0a25fa21ae2cd646e4e8b6c40
echo INSTALL-OK
