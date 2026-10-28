#!/bin/sh
# Optimized nuxel-wl-fb blit (a67) to reduce frame-bridge latency -> /usr/lib/nuxel/nuxel-wl-fb (service: nuxel-wl-fb, risk: medium)
# staged source: build/out/s10plus/a67/nuxel-wl-fb
# previous-hash: 693bcde0788a6bbf856aee3f57bb707ace36f0feaa06cc5ecf9cfc33c9b2455e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-wl-fb.nuxel-rollback.pre-deploy-20261028T100242-2721366 ]; then cp -a /usr/lib/nuxel/nuxel-wl-fb.nuxel-rollback.pre-deploy-20261028T100242-2721366 /usr/lib/nuxel/nuxel-wl-fb; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-wl-fb ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-wl-fb | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-wl-fb)"
if [ -e /usr/lib/nuxel/nuxel-wl-fb ] && [ ! -e /usr/lib/nuxel/nuxel-wl-fb.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-wl-fb /usr/lib/nuxel/nuxel-wl-fb.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-wl-fb ] && [ ! -e /usr/lib/nuxel/nuxel-wl-fb.nuxel-rollback.pre-deploy-20261028T100242-2721366 ]; then cp -a /usr/lib/nuxel/nuxel-wl-fb /usr/lib/nuxel/nuxel-wl-fb.nuxel-rollback.pre-deploy-20261028T100242-2721366; fi
test -f /usr/lib/nuxel/nuxel-wl-fb.nuxel-staged
printf '%s  %s\n' 693bcde0788a6bbf856aee3f57bb707ace36f0feaa06cc5ecf9cfc33c9b2455e /usr/lib/nuxel/nuxel-wl-fb.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-wl-fb.nuxel-staged /usr/lib/nuxel/nuxel-wl-fb
sha256sum /usr/lib/nuxel/nuxel-wl-fb | grep -q 693bcde0788a6bbf856aee3f57bb707ace36f0feaa06cc5ecf9cfc33c9b2455e
echo INSTALL-OK
