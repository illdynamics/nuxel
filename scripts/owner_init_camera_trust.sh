#!/usr/bin/env bash
# Local owner-only trust bootstrap; never uploads private keys.
set -euo pipefail
umask 077
if [[ $# -ne 2 || "$1" != '--owner-approves-camera-trust' ]]; then
  echo 'Usage: bash owner_init_camera_trust.sh --owner-approves-camera-trust /absolute/private/empty/trust-dir' >&2
  echo 'Run ONLY if the device owner explicitly approves creating a dedicated signing key on THIS Mac.' >&2
  exit 2
fi
DIR="$2"
case "$DIR" in /*) ;; *) echo 'Private directory must be absolute' >&2; exit 2 ;; esac
if [[ -e "$DIR" ]]; then echo 'Refusing to use an existing directory. Choose an entirely new private directory.' >&2; exit 2; fi
if ! command -v openssl >/dev/null; then echo 'openssl missing' >&2; exit 2; fi
PARENT="$(dirname "$DIR")"
[[ -d "$PARENT" ]] || { echo "Private parent directory does not exist: $PARENT" >&2; exit 2; }
CHECK="$(cd "$PARENT" && pwd -P)"
while :; do
  [[ ! -e "$CHECK/.git" ]] || { echo 'Refusing to place private keys under a Git checkout' >&2; exit 2; }
  [[ "$CHECK" == / ]] && break
  CHECK="$(dirname "$CHECK")"
done
[[ -r /dev/tty ]] || { echo 'Interactive owner confirmation terminal required.' >&2; exit 2; }
printf 'Owner: type CREATE_CAMERA_TRUST to approve generating an unencrypted local EC signing key in %s: ' "$DIR" >/dev/tty
IFS= read -r RESPONSE </dev/tty
[[ "$RESPONSE" == CREATE_CAMERA_TRUST ]] || { echo 'Owner did not approve; no key created.' >&2; exit 2; }
mkdir -m 700 -- "$DIR"
chmod 700 -- "$DIR"
KEY="$DIR/owner-camera-manifest-and-receipt-signing.key.pem"
PUB="$DIR/owner-camera-manifest-verification.pub.pem"
openssl ecparam -name prime256v1 -genkey -noout -out "$KEY"
chmod 600 "$KEY"
openssl pkey -in "$KEY" -pubout -out "$PUB"
chmod 600 "$PUB"
echo 'Public-key SHA-256 fingerprint (DER encoding):'
openssl pkey -pubin -in "$PUB" -outform DER | openssl dgst -sha256
printf '%s\n' 'OWNER ACTION: independently record/confirm this public fingerprint; never put private key or raw backups in Git or ChatGPT.'
printf 'Dedicated private key remains local: %s\n' "$KEY"
printf 'Public verification key: %s\n' "$PUB"
