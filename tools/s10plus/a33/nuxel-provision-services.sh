#!/bin/sh
# nuxel-provision-services.sh — provision the Nuxel service users/groups/dirs
# that the hardened systemd units require (briq-10b live deploy, 2026-10-17).
#
# WHY THIS EXISTS
#   The service units nuxel-bridge.service / nuxel-http-bridge.service run as
#   User=nuxel-bridge, nuxel-notifications.service as User=nuxel-notifications,
#   and nuxel-portal.service requires ReadWritePaths=/var/lib/nuxel/permissions.
#   On the live S10+ those identities and paths did not exist, so the units
#   failed at step USER (status=217/USER) and step NAMESPACE (status=226/NAMESPACE).
#   This script is the idempotent, no-flash, userspace-only fix.
#
# SAFETY: userspace only. Never flashes, never touches a partition, never changes
# a kernel or bootloader. Idempotent: safe to run more than once.
set -eu

need_user() {
    if ! id "$1" >/dev/null 2>&1; then
        useradd --system --no-create-home --shell /usr/sbin/nologin "$1"
        echo "created user $1"
    else
        echo "user $1 already present"
    fi
}

need_user nuxel-bridge
need_user nuxel-notifications

mkdir -p /var/lib/nuxel/permissions /var/log/nuxel
chown nuxel:nuxel /var/lib/nuxel/permissions
echo "directories ready: /var/lib/nuxel/permissions (nuxel:nuxel), /var/log/nuxel"

echo "provisioning complete"
