#!/bin/sh
# WLAN/USB SSH console (OpenSSH, public key only) -> /home/nuxel/.ssh/authorized_keys (service: sshd.service, risk: low)
# staged source: configs/nuxel/security/ssh/authorized_keys.nuxel
# previous-hash: 5d070910188a6c8518f5f215f8b4e4871db5797bbaaa49f0bb3e4f3a109a5501
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /home/nuxel/.ssh/authorized_keys.nuxel-rollback.pre-tri-link-ssh-apply-n26000 ]; then cp -a /home/nuxel/.ssh/authorized_keys.nuxel-rollback.pre-tri-link-ssh-apply-n26000 /home/nuxel/.ssh/authorized_keys; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -x /usr/sbin/sshd
test -f /etc/ssh/sshd_config
if [ -e /home/nuxel/.ssh/authorized_keys ]; then printf 'PREV=%s\n' "$(sha256sum /home/nuxel/.ssh/authorized_keys | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /home/nuxel/.ssh/authorized_keys)"
if [ -e /home/nuxel/.ssh/authorized_keys ] && [ ! -e /home/nuxel/.ssh/authorized_keys.nuxel-rollback ]; then cp -a /home/nuxel/.ssh/authorized_keys /home/nuxel/.ssh/authorized_keys.nuxel-rollback; fi
if [ -e /home/nuxel/.ssh/authorized_keys ] && [ ! -e /home/nuxel/.ssh/authorized_keys.nuxel-rollback.pre-tri-link-ssh-apply-n26000 ]; then cp -a /home/nuxel/.ssh/authorized_keys /home/nuxel/.ssh/authorized_keys.nuxel-rollback.pre-tri-link-ssh-apply-n26000; fi
test -f /home/nuxel/.ssh/authorized_keys.nuxel-staged
printf '%s  %s\n' 5d070910188a6c8518f5f215f8b4e4871db5797bbaaa49f0bb3e4f3a109a5501 /home/nuxel/.ssh/authorized_keys.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/.ssh/authorized_keys.nuxel-staged /home/nuxel/.ssh/authorized_keys
sha256sum /home/nuxel/.ssh/authorized_keys | grep -q 5d070910188a6c8518f5f215f8b4e4871db5797bbaaa49f0bb3e4f3a109a5501
install -d -m 0700 -o nuxel -g nuxel /home/nuxel/.ssh
chown nuxel:nuxel /home/nuxel/.ssh/authorized_keys 2>/dev/null || true
chmod 0600 /home/nuxel/.ssh/authorized_keys 2>/dev/null || true
sshd -t
echo INSTALL-OK
