#!/bin/sh
# Crispy Doom touch launcher and bridge route -> /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/flatpak_provider.py
# previous-hash: fe0de4b2bd82529e675c970dea7d7bce52b801fd9a41103221f99ae6677aa3cb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-rollback.pre-deploy-20261104T112828-3208175 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-rollback.pre-deploy-20261104T112828-3208175 /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-rollback.pre-deploy-20261104T112828-3208175 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-rollback.pre-deploy-20261104T112828-3208175; fi
test -f /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-staged
printf '%s  %s\n' fe0de4b2bd82529e675c970dea7d7bce52b801fd9a41103221f99ae6677aa3cb /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py
sha256sum /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py | grep -q fe0de4b2bd82529e675c970dea7d7bce52b801fd9a41103221f99ae6677aa3cb
echo INSTALL-OK
