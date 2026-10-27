#!/bin/sh
# WLAN/USB SSH console (OpenSSH, public key only) -> /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf (service: sshd.service, risk: low)
# staged source: configs/nuxel/security/ssh/60-nuxel-tri-link.conf
# previous-hash: 0243d182c6f7012b983431e616726cc5d70614a566d359eb4f75bd2b8138ca11
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-rollback.pre-deploy-20261027T150544-1986364 ]; then cp -a /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-rollback.pre-deploy-20261027T150544-1986364 /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -x /usr/sbin/sshd
test -f /etc/ssh/sshd_config
if [ -e /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf ]; then printf 'PREV=%s\n' "$(sha256sum /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf)"
if [ -e /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf ] && [ ! -e /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-rollback ]; then cp -a /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-rollback; fi
if [ -e /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf ] && [ ! -e /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-rollback.pre-deploy-20261027T150544-1986364 ]; then cp -a /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-rollback.pre-deploy-20261027T150544-1986364; fi
test -f /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-staged
printf '%s  %s\n' 0243d182c6f7012b983431e616726cc5d70614a566d359eb4f75bd2b8138ca11 /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf.nuxel-staged /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf
sha256sum /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf | grep -q 0243d182c6f7012b983431e616726cc5d70614a566d359eb4f75bd2b8138ca11
install -d -m 0700 -o nuxel -g nuxel /home/nuxel/.ssh
chown nuxel:nuxel /home/nuxel/.ssh/authorized_keys 2>/dev/null || true
chmod 0600 /home/nuxel/.ssh/authorized_keys 2>/dev/null || true
sshd -t
echo INSTALL-OK
