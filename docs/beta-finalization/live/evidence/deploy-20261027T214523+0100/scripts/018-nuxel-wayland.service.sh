#!/bin/sh
# nuxel-web single-owner port and Wayland ordering repair -> /etc/systemd/system/nuxel-wayland.service (service: None, risk: low)
# staged source: services/nuxel-session/systemd/nuxel-wayland.service
# previous-hash: 11a5d6725fa997ca9a6fc314ec3a1931b0b680f38655e5520f7010b9d7660a80
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-wayland.service.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /etc/systemd/system/nuxel-wayland.service.nuxel-rollback.pre-deploy-20261027T214523-2399095 /etc/systemd/system/nuxel-wayland.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-wayland.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-wayland.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-wayland.service)"
if [ -e /etc/systemd/system/nuxel-wayland.service ] && [ ! -e /etc/systemd/system/nuxel-wayland.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-wayland.service /etc/systemd/system/nuxel-wayland.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-wayland.service ] && [ ! -e /etc/systemd/system/nuxel-wayland.service.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /etc/systemd/system/nuxel-wayland.service /etc/systemd/system/nuxel-wayland.service.nuxel-rollback.pre-deploy-20261027T214523-2399095; fi
test -f /etc/systemd/system/nuxel-wayland.service.nuxel-staged
printf '%s  %s\n' 11a5d6725fa997ca9a6fc314ec3a1931b0b680f38655e5520f7010b9d7660a80 /etc/systemd/system/nuxel-wayland.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-wayland.service.nuxel-staged /etc/systemd/system/nuxel-wayland.service
sha256sum /etc/systemd/system/nuxel-wayland.service | grep -q 11a5d6725fa997ca9a6fc314ec3a1931b0b680f38655e5520f7010b9d7660a80
echo INSTALL-OK
