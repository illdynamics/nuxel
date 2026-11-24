#!/usr/bin/env bash
# Install verified production boot inputs; preserve the Stage04 recovery path.
# Invoked by nuxel-modem-install.sh --production-config CONFIG LOADER.
set -euo pipefail
[[ $# == 2 && $(id -u) == 0 ]] || { echo 'usage (root): install-production CONFIG LOADER' >&2; exit 2; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config=$1
loader=$2
# No changes until the config syntax and supplied binary hash are validated.
python3 - "$config" "$loader" <<'PY'
import hashlib, json, sys
with open(sys.argv[1]) as f:
    config = json.load(f)
with open(sys.argv[2], 'rb') as f:
    actual = hashlib.sha256(f.read()).hexdigest()
if actual != config.get('loader_sha256'):
    raise SystemExit('supplied loader does not match production config')
PY
mkdir -p /var/lib/nuxel
backup=$(mktemp -d /var/lib/nuxel/modem-production-install.XXXXXX)
chmod 0700 "$backup"
paths=(/usr/libexec/nuxel/nuxel-cpbootd-production
       /usr/lib/nuxel/nuxel-modem/nuxel-cpbootd.production.hw
       /etc/nuxel/modem/production.json
       /etc/systemd/system/nuxel-cpbootd-production.service
       /etc/systemd/system/nuxel-radiod.service.d/05-production-boot.conf)
for index in "${!paths[@]}"; do
    path=${paths[$index]}
    if [[ -e "$path" || -L "$path" ]]; then cp -a "$path" "$backup/$index"; fi
    mkdir -p "$(dirname "$path")"
done
rollback() {
    local rc=$?
    trap - EXIT
    if (( rc != 0 )); then
        for index in "${!paths[@]}"; do
            path=${paths[$index]}
            rm -f "$path"
            if [[ -e "$backup/$index" || -L "$backup/$index" ]]; then cp -a "$backup/$index" "$path"; fi
        done
        systemctl daemon-reload
        echo "Install failed; previous files restored. Backup: $backup" >&2
    fi
    exit "$rc"
}
trap rollback EXIT
install -m 0755 "$HERE/nuxel-cpbootd-production" "${paths[0]}"
install -m 0750 "$loader" "${paths[1]}"
install -m 0600 "$config" "${paths[2]}"
"${paths[0]}" --check
install -m 0644 "$HERE/../systemd/nuxel-cpbootd-production.service" "${paths[3]}"
cat > "${paths[4]}" <<'UNIT'
[Unit]
Requires=nuxel-cpbootd-production.service
After=nuxel-cpbootd-production.service
UNIT
systemctl daemon-reload
# The existing enabled radiod service pulls this in on normal startup.
# Do not restart the running modem, radio, session or management services here.
printf 'Production boot installed; rollback files: %s\n' "$backup"
