#!/bin/sh
# Crispy Doom touch launcher and bridge route -> /usr/lib/nuxel/nuxel-flatpak-doom (service: nuxel-http-bridge, risk: medium)
# staged source: tools/s10plus/a33/nuxel-flatpak-doom
# previous-hash: 47dbcd3922fc7e5257e73cc31c7bd9cd66df324833df198adc4779dcd2237aa6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-rollback.pre-deploy-20261104T112828-3208175 ]; then cp -a /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-rollback.pre-deploy-20261104T112828-3208175 /usr/lib/nuxel/nuxel-flatpak-doom; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-flatpak-doom ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-flatpak-doom | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-flatpak-doom)"
if [ -e /usr/lib/nuxel/nuxel-flatpak-doom ] && [ ! -e /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-flatpak-doom /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-flatpak-doom ] && [ ! -e /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-rollback.pre-deploy-20261104T112828-3208175 ]; then cp -a /usr/lib/nuxel/nuxel-flatpak-doom /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-rollback.pre-deploy-20261104T112828-3208175; fi
test -f /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-staged
printf '%s  %s\n' 47dbcd3922fc7e5257e73cc31c7bd9cd66df324833df198adc4779dcd2237aa6 /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-flatpak-doom.nuxel-staged /usr/lib/nuxel/nuxel-flatpak-doom
sha256sum /usr/lib/nuxel/nuxel-flatpak-doom | grep -q 47dbcd3922fc7e5257e73cc31c7bd9cd66df324833df198adc4779dcd2237aa6
echo INSTALL-OK
