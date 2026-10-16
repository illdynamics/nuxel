#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-keyboard-apply.path (service: None, risk: medium)
# staged source: configs/nuxel/keyboard/nuxel-keyboard-apply.path
# previous-hash: a12740567567fa84cb445023a25d460e0ffe80ffb2b567420be2d44c583cdc17
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-keyboard-apply.path.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-keyboard-apply.path.nuxel-rollback /etc/systemd/system/nuxel-keyboard-apply.path; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-keyboard-apply.path ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-keyboard-apply.path | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-keyboard-apply.path)"
if [ -e /etc/systemd/system/nuxel-keyboard-apply.path ] && [ ! -e /etc/systemd/system/nuxel-keyboard-apply.path.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-keyboard-apply.path /etc/systemd/system/nuxel-keyboard-apply.path.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-keyboard-apply.path.nuxel-staged
printf '%s  %s\n' a12740567567fa84cb445023a25d460e0ffe80ffb2b567420be2d44c583cdc17 /etc/systemd/system/nuxel-keyboard-apply.path.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-keyboard-apply.path.nuxel-staged /etc/systemd/system/nuxel-keyboard-apply.path
sha256sum /etc/systemd/system/nuxel-keyboard-apply.path | grep -q a12740567567fa84cb445023a25d460e0ffe80ffb2b567420be2d44c583cdc17
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
