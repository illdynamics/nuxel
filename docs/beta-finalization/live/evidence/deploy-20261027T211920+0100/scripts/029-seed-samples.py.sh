#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/tools/seed-samples.py
# previous-hash: 194abafa2f32febd749ce1301d223322f4d227a89c9783f6d83ed6a0c89ec689
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-staged
printf '%s  %s\n' 194abafa2f32febd749ce1301d223322f4d227a89c9783f6d83ed6a0c89ec689 /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/tools/seed-samples.py | grep -q 194abafa2f32febd749ce1301d223322f4d227a89c9783f6d83ed6a0c89ec689
echo INSTALL-OK
