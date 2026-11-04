#!/usr/bin/env bash
# PWNAGE-63000 — rollback the userspace deployment.
#
# Usage (on the handset, as root):
#   /usr/lib/nuxel/rollback-pwnage63000.sh /var/backups/nuxel/p63000-<stamp>
#
# It restores only files present in the timestamped backup.  It NEVER deletes
# /root/.local/share/keyrings, Secret Service items, the Authenticator
# localStorage envelope or any other user data.
set -Eeuo pipefail
BACKUP="${1:?usage: rollback-pwnage63000.sh /var/backups/nuxel/p63000-<stamp>}"
[ -d "$BACKUP" ] || { echo "no backup at $BACKUP" >&2; exit 1; }
[ -f "$BACKUP/SHA256SUMS" ] || { echo "backup manifest missing" >&2; exit 1; }
cd "$BACKUP"
sha256sum -c SHA256SUMS --quiet

say() { printf '== %s\n' "$*"; }

restore() { # <absolute target>
  local f="$1"
  if [ -e "$BACKUP$f" ]; then
    mkdir -p "$(dirname "$f")"
    cp -a "$BACKUP$f" "$f"
    echo "restored $f"
  else
    echo "kept new file (not in backup): $f"
  fi
}

say "restoring previous userspace files"
restore /usr/lib/nuxel/nuxel-bridge/api.py
restore /usr/lib/nuxel/nuxel-bridge/capabilities.py
restore /usr/lib/nuxel/nuxel-pwa-host
restore /etc/systemd/system/nuxel-http-bridge.service
restore /usr/lib/nuxel/nuxel-session.sh
restore /usr/share/nuxel/pwa/nuxel-common/bridge.js
restore /usr/share/nuxel/pwa/nuxel-common/app-registry.json
restore /usr/share/nuxel/pwa/nuxel-home/js/apps.js
restore /usr/share/nuxel/pwa/nuxel-home/js/app.js
restore /usr/share/nuxel/pwa/nuxel-home/sw.js
restore /usr/share/nuxel/pwa/nuxel-home/manifest.json
restore /etc/nuxel/app-registry/app_registry.json
restore /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json
restore /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json
restore /usr/share/nuxel/pwa/nuxel-apps/clipper/manifest.json

# A pre-mission backup made by an earlier deploy script may lack the native
# host.  Restore the separately captured original binary if present.
if [ ! -e "$BACKUP/usr/lib/nuxel/nuxel-pwa-host" ] &&    [ -e /var/backups/nuxel/p63000-host-20261103/nuxel-pwa-host ]; then
  install -m 0755 /var/backups/nuxel/p63000-host-20261103/nuxel-pwa-host     /usr/lib/nuxel/nuxel-pwa-host
  echo "restored original native host from /var/backups/nuxel/p63000-host-20261103"
fi

say "restoring app directories"
if [ -d "$BACKUP/usr/share/nuxel/pwa/nuxel-apps/authenticator" ]; then
  rm -rf /usr/share/nuxel/pwa/nuxel-apps/authenticator
  cp -a "$BACKUP/usr/share/nuxel/pwa/nuxel-apps/authenticator" /usr/share/nuxel/pwa/nuxel-apps/authenticator
  echo "restored authenticator app"
fi
if [ -d "$BACKUP/usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog" ]; then
  rm -rf /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog
  cp -a "$BACKUP/usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog" /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog
  echo "restored nuxtore catalog"
fi

say "removing mission-only files absent from the backup"
# The Vault app was new in this mission.  Remove only if it was not in the backup.
if [ ! -d "$BACKUP/usr/share/nuxel/pwa/nuxel-apps/vault" ]; then
  rm -rf /usr/share/nuxel/pwa/nuxel-apps/vault
  echo "removed new vault app tree"
fi
if [ ! -e "$BACKUP/usr/lib/systemd/system-sleep/nuxel-keyring-lock" ]; then
  rm -f /usr/lib/systemd/system-sleep/nuxel-keyring-lock
  echo "removed new suspend hook"
fi
if [ ! -e "$BACKUP/etc/nuxel/keyring-launcher.secret" ]; then
  rm -f /etc/nuxel/keyring-launcher.secret
  echo "removed mission launcher secret"
fi
# New keyring modules are mission-only; remove only these three files.
for f in secret_service.py keyring_api.py; do
  if [ ! -e "$BACKUP/usr/lib/nuxel/nuxel-bridge/$f" ]; then
    rm -f "/usr/lib/nuxel/nuxel-bridge/$f"
    echo "removed new module $f"
  fi
done
# capabilities.py existed before; restore() already handled it.

say "services"
systemctl daemon-reload
systemctl restart nuxel-http-bridge
systemctl restart nuxel-bridge
sleep 2
systemctl is-active nuxel-http-bridge nuxel-bridge nuxel-web || true
cat <<'NOTE'
Reboot (or deliberately restart nuxel-wayland) to load the restored native host
and Home app files.  The running WebKit process still has the mission files in
memory until that restart.
NOTE

say "preserved user data (never touched by rollback)"
if [ -d /root/.local/share/keyrings ]; then
  echo "keyring directory present: /root/.local/share/keyrings"
else
  echo "keyring directory absent"
fi
cat <<'NOTE'
Rollback does not remove:
  - /root/.local/share/keyrings (encrypted keyring database)
  - any Secret Service item
  - the Authenticator localStorage envelope
  - downloaded encrypted archives
The old Authenticator manual passphrase path remains functional.  A saved
Authenticator keyring credential becomes unused; it is not deleted by rollback.
If the owner wants it gone after rollback, do that deliberately from the old
Authenticator UI or a reviewed keyring tool, never with rm -rf.
NOTE
