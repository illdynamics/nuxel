#!/bin/sh
# audio / network runtime config -> /etc/nuxel/time/nuxel-chrony.conf (service: None, risk: medium)
# staged source: configs/nuxel/time/nuxel-chrony.conf
# previous-hash: 1d946102f33c56a491cc7d4b89d77466f1ce4301cd80dd17d81cf713054f1ca1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/time/nuxel-chrony.conf.nuxel-rollback ]; then cp -a /etc/nuxel/time/nuxel-chrony.conf.nuxel-rollback /etc/nuxel/time/nuxel-chrony.conf; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/time/nuxel-chrony.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/time/nuxel-chrony.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/time/nuxel-chrony.conf)"
if [ -e /etc/nuxel/time/nuxel-chrony.conf ] && [ ! -e /etc/nuxel/time/nuxel-chrony.conf.nuxel-rollback ]; then cp -a /etc/nuxel/time/nuxel-chrony.conf /etc/nuxel/time/nuxel-chrony.conf.nuxel-rollback; fi
test -f /etc/nuxel/time/nuxel-chrony.conf.nuxel-staged
printf '%s  %s\n' 1d946102f33c56a491cc7d4b89d77466f1ce4301cd80dd17d81cf713054f1ca1 /etc/nuxel/time/nuxel-chrony.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/time/nuxel-chrony.conf.nuxel-staged /etc/nuxel/time/nuxel-chrony.conf
sha256sum /etc/nuxel/time/nuxel-chrony.conf | grep -q 1d946102f33c56a491cc7d4b89d77466f1ce4301cd80dd17d81cf713054f1ca1
( nuxelctl status >/dev/null 2>&1 || true ) || echo DECLARED-RELOAD-DEFERRED
echo INSTALL-OK
