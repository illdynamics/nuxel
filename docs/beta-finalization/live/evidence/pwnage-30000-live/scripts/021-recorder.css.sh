#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/css/recorder.css
# previous-hash: b35de68d980bdca8eec2a2cbbb67f1c005907ff63d8846d085d7483740c2ff5e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-staged
printf '%s  %s\n' b35de68d980bdca8eec2a2cbbb67f1c005907ff63d8846d085d7483740c2ff5e /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/css/recorder.css | grep -q b35de68d980bdca8eec2a2cbbb67f1c005907ff63d8846d085d7483740c2ff5e
echo INSTALL-OK
