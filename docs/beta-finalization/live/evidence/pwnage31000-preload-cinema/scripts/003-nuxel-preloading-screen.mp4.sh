#!/bin/sh
# Bounded pre-lockscreen video controller, systemd unit, durable config and supplied clip -> /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 (service: None, risk: low)
# staged source: assets/nuxel-preloading-screen.mp4
# previous-hash: b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-rollback.pre-deploy-20261028T105005-2828527 ]; then cp -a /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-rollback.pre-deploy-20261028T105005-2828527 /usr/share/nuxel/preload/nuxel-preloading-screen.mp4; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/preload/nuxel-preloading-screen.mp4)"
if [ -e /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 ] && [ ! -e /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-rollback ]; then cp -a /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-rollback; fi
if [ -e /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 ] && [ ! -e /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-rollback.pre-deploy-20261028T105005-2828527 ]; then cp -a /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-rollback.pre-deploy-20261028T105005-2828527; fi
test -f /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-staged
printf '%s  %s\n' b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1 /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-staged /usr/share/nuxel/preload/nuxel-preloading-screen.mp4
sha256sum /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 | grep -q b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1
echo INSTALL-OK
