#!/usr/bin/env bash
# PWNAGE-63000 — deploy the Nuxel Vault / keyring stack to the S10+.
#
# Usage:
#   SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
#     tools/pwnage63000/deploy-pwnage63000.sh root@10.20.30.16
#
# This deploys userspace files only.  It never flashes the kernel/bootloader,
# never touches modem/partition data and never creates or deletes a keyring
# collection.  The owner creates the first master password in the Vault UI.
set -Eeuo pipefail

TARGET="${1:?usage: deploy-pwnage63000.sh root@HOST}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
ROOT="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/var/backups/nuxel/p63000-$STAMP"
STAGE="/tmp/p63000-stage-$STAMP"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 "$TARGET")
SCP=(scp -q -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes)

say() { printf '%s\n' "== $*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[ -f "$KEY" ] || fail "SSH key not found: $KEY"
[ -f "$ROOT/services/nuxel-bridge/src/keyring_api.py" ] || fail "run from the Nuxel checkout"
[ -d "$ROOT/pwa/nuxel-apps/vault" ] || fail "Vault app tree missing"

say "preflight: target identity"
"${SSH[@]}" '
  set -eu
  [ "$(uname -m)" = aarch64 ] || { echo "not aarch64"; exit 1; }
  grep -qi "Fedora" /etc/os-release || { echo "not Fedora"; exit 1; }
  [ -x /usr/lib/nuxel/nuxel-pwa-host ] || { echo "nuxel-pwa-host missing"; exit 1; }
  [ -d /usr/lib/nuxel/nuxel-bridge ] || { echo "bridge dir missing"; exit 1; }
  [ -d /usr/share/nuxel/pwa/nuxel-apps ] || { echo "pwa docroot missing"; exit 1; }
  echo "target-ok $(uname -m) $(rpm -q --qf "%{VERSION}" fedora-release 2>/dev/null || true)"
'

say "preflight: Secret Service packages"
"${SSH[@]}" '
  set -eu
  missing=""
  for p in gnome-keyring gcr3 libsecret; do rpm -q "$p" >/dev/null 2>&1 || missing="$missing $p"; done
  if [ -n "$missing" ]; then
    echo "installing:$missing"
    dnf install -y $missing
  else
    rpm -q gnome-keyring gcr3 libsecret
  fi
'

say "backup: $BACKUP"
"${SSH[@]}" "
  set -eu
  mkdir -p '$BACKUP'
  for f in \
    /usr/lib/nuxel/nuxel-bridge/api.py \
    /usr/lib/nuxel/nuxel-bridge/capabilities.py \
    /usr/lib/nuxel/nuxel-bridge/secret_service.py \
    /usr/lib/nuxel/nuxel-bridge/keyring_api.py \
    /usr/lib/nuxel/nuxel-pwa-host \
    /etc/nuxel/keyring-launcher.secret \
    /etc/systemd/system/nuxel-http-bridge.service \
    /usr/lib/nuxel/nuxel-session.sh \
    /usr/share/nuxel/pwa/nuxel-common/bridge.js \
    /usr/share/nuxel/pwa/nuxel-common/app-registry.json \
    /usr/share/nuxel/pwa/nuxel-home/js/apps.js \
    /usr/share/nuxel/pwa/nuxel-home/js/app.js \
    /usr/share/nuxel/pwa/nuxel-home/sw.js \
    /usr/share/nuxel/pwa/nuxel-home/manifest.json \
    /etc/nuxel/app-registry/app_registry.json \
    /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json \
    /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json \
    /usr/share/nuxel/pwa/nuxel-apps/clipper/manifest.json ; do
    if [ -e \"\$f\" ]; then
      mkdir -p \"$BACKUP\$(dirname \"\$f\")\"
      cp -a \"\$f\" \"$BACKUP\$f\"
    fi
  done
  for d in /usr/share/nuxel/pwa/nuxel-apps/authenticator \
           /usr/share/nuxel/pwa/nuxel-apps/vault \
           /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog \
           /usr/lib/systemd/system-sleep/nuxel-keyring-lock ; do
    if [ -e \"\$d\" ]; then
      mkdir -p \"$BACKUP\$(dirname \"\$d\")\"
      cp -a \"\$d\" \"$BACKUP\$d\"
    fi
  done
  cd '$BACKUP'
  find . -type f ! -name SHA256SUMS -print0 | xargs -0 sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS --quiet
  echo 'backup-verified'
  echo '$BACKUP' > /run/nuxel-p63000-backup-dir
"

say "stage: payloads"
"${SSH[@]}" "mkdir -p '$STAGE' && chmod 0700 '$STAGE'"
tar -C "$ROOT/pwa/nuxel-apps" -czf "/tmp/p63000-vault-$STAMP.tgz" vault
tar -C "$ROOT/pwa/nuxel-apps" -czf "/tmp/p63000-auth-$STAMP.tgz" authenticator
tar -C "$ROOT/pwa/nuxel-apps/nuxtore" -czf "/tmp/p63000-nuxtore-$STAMP.tgz" catalog
"${SCP[@]}" \
  "$ROOT/services/nuxel-bridge/src/api.py" \
  "$ROOT/services/nuxel-bridge/src/capabilities.py" \
  "$ROOT/services/nuxel-bridge/src/secret_service.py" \
  "$ROOT/services/nuxel-bridge/src/keyring_api.py" \
  "$ROOT/services/nuxel-bridge/systemd/nuxel-http-bridge.service" \
  "$ROOT/tools/s10plus/a45/nuxel-session.sh" \
  "$ROOT/tools/s10plus/a45/nuxel-pwa-host.c" \
  "$ROOT/tools/pwnage63000/nuxel-keyring-lock.sh" \
  "$ROOT/tools/pwnage63000/rollback-pwnage63000.sh" \
  "$ROOT/pwa/nuxel-common/bridge.js" \
  "$ROOT/pwa/nuxel-common/app-registry.json" \
  "$ROOT/pwa/nuxel-home/js/apps.js" \
  "$ROOT/pwa/nuxel-home/js/app.js" \
  "$ROOT/pwa/nuxel-home/sw.js" \
  "$ROOT/pwa/nuxel-home/manifest.json" \
  "$ROOT/pwa/nuxel-apps/clipper/manifest.json" \
  "$ROOT/shell/nuxel-home-native/nuxel_home/app_registry.json" \
  "/tmp/p63000-vault-$STAMP.tgz" "/tmp/p63000-auth-$STAMP.tgz" "/tmp/p63000-nuxtore-$STAMP.tgz" \
  "$TARGET:$STAGE/"

say "install: userspace"
"${SSH[@]}" "
  set -eu
  cd '$STAGE'
  mkdir -p /usr/lib/systemd/system-sleep /run/nuxel
  tar -tzf p63000-vault-*.tgz >/dev/null
  tar -tzf p63000-auth-*.tgz >/dev/null
  tar -tzf p63000-nuxtore-*.tgz >/dev/null
  tar -tzf p63000-vault-*.tgz | grep -q '^vault/index.html$'
  tar -tzf p63000-auth-*.tgz | grep -q '^authenticator/index.html$'
  install -m 0644 api.py /usr/lib/nuxel/nuxel-bridge/api.py
  install -m 0644 capabilities.py /usr/lib/nuxel/nuxel-bridge/capabilities.py
  install -m 0644 secret_service.py /usr/lib/nuxel/nuxel-bridge/secret_service.py
  install -m 0644 keyring_api.py /usr/lib/nuxel/nuxel-bridge/keyring_api.py
  install -m 0644 nuxel-http-bridge.service /etc/systemd/system/nuxel-http-bridge.service
  install -m 0755 nuxel-session.sh /usr/lib/nuxel/nuxel-session.sh
  install -m 0755 nuxel-keyring-lock.sh /usr/lib/systemd/system-sleep/nuxel-keyring-lock
  install -m 0755 rollback-pwnage63000.sh /usr/lib/nuxel/rollback-pwnage63000.sh
  # Preserve the owner of an existing PWA file; root ownership is fine for new ones.
  cp -f bridge.js /usr/share/nuxel/pwa/nuxel-common/bridge.js
  chmod 0644 /usr/share/nuxel/pwa/nuxel-common/bridge.js
  cp -f apps.js /usr/share/nuxel/pwa/nuxel-home/js/apps.js
  chmod 0644 /usr/share/nuxel/pwa/nuxel-home/js/apps.js
  cp -f app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js
  chmod 0644 /usr/share/nuxel/pwa/nuxel-home/js/app.js
  cp -f sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js
  chmod 0644 /usr/share/nuxel/pwa/nuxel-home/sw.js
  install -m 0644 manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json
  install -m 0644 app-registry.json /usr/share/nuxel/pwa/nuxel-common/app-registry.json
  install -m 0644 app-registry.json /etc/nuxel/app-registry/app_registry.json
  install -m 0644 app_registry.json /usr/share/nuxel/shell/nuxel-home-native/nuxel_home/app_registry.json
  install -m 0644 app_registry.json /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json
  install -m 0644 manifest.json /usr/share/nuxel/pwa/nuxel-apps/clipper/manifest.json
  rm -rf /usr/share/nuxel/pwa/nuxel-apps/vault
  tar -xzf p63000-vault-*.tgz -C /usr/share/nuxel/pwa/nuxel-apps
  rm -rf /usr/share/nuxel/pwa/nuxel-apps/authenticator
  tar -xzf p63000-auth-*.tgz -C /usr/share/nuxel/pwa/nuxel-apps
  rm -rf /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog
  tar -xzf p63000-nuxtore-*.tgz -C /usr/share/nuxel/pwa/nuxel-apps/nuxtore
  # The catalog ships a PUBLISHED DEV signing key in the repository fixture.
  # The device only needs the public half to verify packages.
  rm -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/*.key.txt
  chmod -R a+rX /usr/share/nuxel/pwa/nuxel-apps/vault /usr/share/nuxel/pwa/nuxel-apps/authenticator \
    /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog
  python3 -m py_compile /usr/lib/nuxel/nuxel-bridge/api.py \
    /usr/lib/nuxel/nuxel-bridge/capabilities.py \
    /usr/lib/nuxel/nuxel-bridge/secret_service.py \
    /usr/lib/nuxel/nuxel-bridge/keyring_api.py
  # Per-device launcher keyring secret.  The native top-frame relay holds it in
  # a closure; the Bridge reads the same root-only file.  Never bake it into an
  # image or commit it.
  umask 077
  if [ ! -s /etc/nuxel/keyring-launcher.secret ]; then
    od -An -v -tx1 -N32 /dev/urandom | tr -d ' \n' > /etc/nuxel/keyring-launcher.secret
    printf '\n' >> /etc/nuxel/keyring-launcher.secret
  fi
  chown root:root /etc/nuxel/keyring-launcher.secret
  chmod 0600 /etc/nuxel/keyring-launcher.secret
  # Native host: launcher-minted keyring tokens for iframe PWAs (WebKit sends
  # no Referer from those frames).  Compile to a temporary name first; a failed
  # build leaves the running/backed-up binary in place.
  gcc -O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11 \
    \$(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) \
    -o nuxel-pwa-host.new nuxel-pwa-host.c \
    \$(pkg-config --libs gtk+-3.0 webkit2gtk-4.1) -lutil
  install -m 0755 nuxel-pwa-host.new /usr/lib/nuxel/nuxel-pwa-host
  strings /usr/lib/nuxel/nuxel-pwa-host | grep -q NUXEL_KEYRING_MINT
  echo installed
"

say "services: reload and restart"
"${SSH[@]}" '
  set -eu
  systemctl daemon-reload
  systemctl restart nuxel-http-bridge
  systemctl restart nuxel-bridge
  sleep 2
  systemctl is-active nuxel-http-bridge nuxel-bridge nuxel-web
'

say "verify: live keyring status through the scoped API"
"${SSH[@]}" '
  set -eu
  python3 - <<"PY"
import json, urllib.request
API="http://127.0.0.1:8080/api/v1"
ORIGIN="http://127.0.0.1:8000"
REF="http://127.0.0.1:8000/pwa/nuxel-apps/vault/index.html"
def post(path, body, token=None, referer=REF):
    data=json.dumps(body).encode()
    req=urllib.request.Request(API+path, data=data, method="POST")
    req.add_header("Content-Type","application/json")
    req.add_header("Origin",ORIGIN)
    req.add_header("Referer",referer)
    req.add_header("X-Nuxel-Bridge-Version","1")
    if token: req.add_header("Authorization","Bearer "+token)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())
tok=post("/auth/token", {"app_id":"org.nuxel.Vault"})["token"]
status=post("/rpc", {"app_id":"org.nuxel.Vault","namespace":"keyring","verb":"status","params":{}}, tok)
print("vault-status", json.dumps(status, sort_keys=True))
assert status.get("result",{}).get("success") is True, status
assert status["result"].get("state") in ("not_initialized","collection_locked","unlocked"), status
# A token issued for Home must not be replayable as Vault.
home=post("/auth/token", {"app_id":"org.nuxel.Home"}, referer="http://127.0.0.1:8000/pwa/nuxel-home/index.html")["token"]
spoof=post("/rpc", {"app_id":"org.nuxel.Vault","namespace":"keyring","verb":"status","params":{}}, home)
print("spoof", json.dumps(spoof, sort_keys=True))
assert spoof.get("result",{}).get("success") is False, spoof
assert spoof["result"].get("error") in ("identity_mismatch","permission_denied"), spoof
print("api-identity-ok")
PY
  echo "secret-service-owner:"
  busctl --address=unix:path=/run/nuxel-wayland/bus status org.freedesktop.secrets 2>&1 | grep -E "^(PID|UID|EUID)=" || true
  if [ -f /root/.local/share/keyrings/login.keyring ]; then
    echo "keyring-present: yes (owner data preserved; not modified)"
  else
    echo "keyring-present: no (owner has not initialized it yet)"
  fi
  rpm -q gnome-keyring gcr3 libsecret
  ls -l /etc/nuxel/keyring-launcher.secret
  strings /usr/lib/nuxel/nuxel-pwa-host | grep -q NUXEL_KEYRING_MINT && echo 'host-keyring-relay=present'
  sha256sum /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/keyring_api.py \
    /usr/lib/nuxel/nuxel-bridge/secret_service.py /usr/lib/nuxel/nuxel-pwa-host \
    /usr/share/nuxel/pwa/nuxel-apps/vault/index.html
'

say "record deployment"
"${SSH[@]}" "
  set -eu
  cat > /run/nuxel-p63000-deploy.json <<JSON
{\"stamp\":\"$STAMP\",\"backup\":\"$BACKUP\",\"target\":\"$TARGET\",
 \"status\":\"deployed_userspace\",\"reboot_required_for_session_script\":true,
 \"kernel_or_boot_flash\":false,\"keyring_initialized_by_agent\":false}
JSON
  cat /run/nuxel-p63000-deploy.json
"
say "done. Backup: $BACKUP"
say "Next: reboot (or restart nuxel-wayland) and initialize Vault with the owner's master password."
