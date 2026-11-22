#!/usr/bin/env bash
# Owner must inspect and approve exact filled manifest before signing.
set -euo pipefail
umask 077
if [[ $# -ne 4 || "$1" != '--owner-reviewed-manifest' ]]; then
  echo 'Usage: bash owner_sign_camera_manifest.sh --owner-reviewed-manifest /private/manifest.json /private/owner-key.pem /private/owner-pub.pem' >&2
  exit 2
fi
M="$2"; KEY="$3"; PUB="$4"
for f in "$M" "$KEY" "$PUB"; do [[ -f "$f" ]] || { echo "Missing: $f" >&2; exit 2; }; done
[[ "$M" = /* && "$KEY" = /* && "$PUB" = /* ]] || { echo 'Absolute paths required' >&2; exit 2; }
case "$M" in *NOT_SIGNED*|*template*) echo 'Refusing to sign an unsigned TEMPLATE.' >&2; exit 2 ;; esac
python3 - "$M" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
if m.get('schema') != 'nuxel.camera.prompt00/v1':
 raise SystemExit('Wrong schema')
for key in ('off_device','rollback_ready','selected_overlay_verified','active_tree_matches_onflash'):
 if m.get('proof',{}).get(key) is not True:
  raise SystemExit('Not permitted to sign unproven manifest: ' + key)
if m.get('device',{}).get('status') != 'NUXEL_HEALTHY':
 raise SystemExit('Current healthy-device proof not recorded')
PY
if [[ -e "$M.sig" ]]; then echo 'Refusing to replace existing detached signature' >&2; exit 2; fi
[[ -r /dev/tty ]] || { echo 'Interactive owner confirmation terminal required.' >&2; exit 2; }
if command -v shasum >/dev/null; then shasum -a 256 "$M"; else sha256sum "$M"; fi
printf 'Owner: verify the full manifest and above checksum, then type SIGN_CAMERA_MANIFEST to sign it: ' >/dev/tty
IFS= read -r RESPONSE </dev/tty
[[ "$RESPONSE" == SIGN_CAMERA_MANIFEST ]] || { echo 'Not approved; no signature created.' >&2; exit 2; }
openssl dgst -sha256 -sign "$KEY" -out "$M.sig" "$M"
openssl dgst -sha256 -verify "$PUB" -signature "$M.sig" "$M"
if command -v shasum >/dev/null; then shasum -a 256 "$M" "$M.sig"; else sha256sum "$M" "$M.sig"; fi
printf '%s\n' 'A valid signature means the owner signed these bytes; it does NOT independently certify hardware truth or permit flashing.'
