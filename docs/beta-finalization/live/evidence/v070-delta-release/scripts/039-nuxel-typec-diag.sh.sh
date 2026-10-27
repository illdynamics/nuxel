#!/bin/sh
# Typecast and Type-C diagnostics -> /usr/local/bin/nuxel-typec-diag.sh (service: None, risk: low)
# staged source: tools/s10plus/a33/nuxel-typec-diag.sh
# previous-hash: 9eaa18184750d0b3a17d0178aa996af42871a06cdc709d70d1e474dbde32005b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-typec-diag.sh.nuxel-rollback.pre-v070-delta-release ]; then cp -a /usr/local/bin/nuxel-typec-diag.sh.nuxel-rollback.pre-v070-delta-release /usr/local/bin/nuxel-typec-diag.sh; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/local/bin/nuxel-typec-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-typec-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-typec-diag.sh)"
if [ -e /usr/local/bin/nuxel-typec-diag.sh ] && [ ! -e /usr/local/bin/nuxel-typec-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-typec-diag.sh /usr/local/bin/nuxel-typec-diag.sh.nuxel-rollback; fi
if [ -e /usr/local/bin/nuxel-typec-diag.sh ] && [ ! -e /usr/local/bin/nuxel-typec-diag.sh.nuxel-rollback.pre-v070-delta-release ]; then cp -a /usr/local/bin/nuxel-typec-diag.sh /usr/local/bin/nuxel-typec-diag.sh.nuxel-rollback.pre-v070-delta-release; fi
test -f /usr/local/bin/nuxel-typec-diag.sh.nuxel-staged
printf '%s  %s\n' 9eaa18184750d0b3a17d0178aa996af42871a06cdc709d70d1e474dbde32005b /usr/local/bin/nuxel-typec-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-typec-diag.sh.nuxel-staged /usr/local/bin/nuxel-typec-diag.sh
sha256sum /usr/local/bin/nuxel-typec-diag.sh | grep -q 9eaa18184750d0b3a17d0178aa996af42871a06cdc709d70d1e474dbde32005b
echo INSTALL-OK
