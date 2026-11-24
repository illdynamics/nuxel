#!/usr/bin/env bash
# nuxel-modem-install.sh — REVERSIBLE userspace deployment (read-only probe + inert CP boot).
#
# Installs (does NOT activate) the S5000AP modem userspace components onto a
# normally-booted Nuxel:
#   - nuxel-cp-status            : read-only CP state probe (safe, always allowed)
#   - nuxel-cpbootd.aarch64      : dry-run/mock build (never physical)
#   - nuxel-cpbootd.aarch64.hw   : HW-compiled build (NEVER run unless approved)
#   - nuxel-cpbootd-manifest-check.sh : manifest preflight
#   - nuxel-cpbootd-stage04-guard     : fail-closed one-shot gate
#   - systemd units (both Restart=no; physical unit NOT enabled)
#
# This script does NOT:
#   - enable or start nuxel-cpbootd.service (physical trial)
#   - invoke --really-boot
#   - write any partition / flash anything
#   - touch /dev/umts_boot0 read-write
#
# Uninstall: nuxel-modem-install.sh --uninstall
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The production path is explicit and preserves the separate Stage04 loader.
if [[ "${1:-}" == "--production-config" ]]; then
    [[ $# == 3 ]] || { echo 'usage: nuxel-modem-install.sh --production-config CONFIG LOADER' >&2; exit 2; }
    exec "$HERE/nuxel-modem-install-production.sh" "$2" "$3"
fi
SRC_BIN="$HERE/../../../tools/s10plus/s5000ap-uapi"
DEST_BIN="/usr/lib/nuxel/nuxel-modem"
DEST_LIBEXEC="/usr/libexec/nuxel"
DEST_SYSTEMD="/etc/systemd/system"
ENV_DIR="/etc/nuxel/modem"
ENV_FILE="$ENV_DIR/stage04-trial.env"

if [[ "${1:-}" == "--uninstall" ]]; then
    echo "Uninstalling nuxel-modem userspace components (reversible)..."
    systemctl --no-block stop nuxel-cp-status.service 2>/dev/null || true
    systemctl --no-block stop nuxel-cpbootd.service 2>/dev/null || true
    systemctl disable nuxel-cp-status.service 2>/dev/null || true
    systemctl disable nuxel-cpbootd.service 2>/dev/null || true
    rm -f "$DEST_SYSTEMD/nuxel-cp-status.service" \
          "$DEST_SYSTEMD/nuxel-cpbootd.service" \
          "$DEST_BIN/nuxel-cp-status" \
          "$DEST_BIN/nuxel-cpbootd.aarch64" \
          "$DEST_BIN/nuxel-cpbootd.aarch64.hw" \
          "$DEST_LIBEXEC/nuxel-cpbootd-stage04-guard" \
          "$DEST_LIBEXEC/nuxel-cpbootd-manifest-check.sh"
    # Never delete the operator-written env file automatically; report it instead.
    if [[ -f "$ENV_FILE" ]]; then
        echo "NOTE: leaving $ENV_FILE in place (operator-owned; review and remove manually)."
    fi
    systemctl daemon-reload
    echo "uninstall complete"
    exit 0
fi

[[ $(id -u) -eq 0 ]] || { echo "error: run as root (device deployment)"; exit 1; }

mkdir -p "$DEST_BIN" "$DEST_LIBEXEC" "$DEST_SYSTEMD" "$ENV_DIR"

install -m 0755 "$SRC_BIN/nuxel-cpbootd.aarch64"       "$DEST_BIN/nuxel-cpbootd.aarch64"
install -m 0750 "$SRC_BIN/nuxel-cpbootd.aarch64.hw"    "$DEST_BIN/nuxel-cpbootd.aarch64.hw"
install -m 0755 "$SRC_BIN/s5000ap-status.aarch64"      "$DEST_BIN/nuxel-cp-status"
install -m 0755 "$SRC_BIN/nuxel-cpbootd-manifest-check.sh" "$DEST_LIBEXEC/nuxel-cpbootd-manifest-check.sh"
install -m 0755 "$HERE/nuxel-cpbootd-stage04-guard"    "$DEST_LIBEXEC/nuxel-cpbootd-stage04-guard"
install -m 0644 "$HERE/../systemd/nuxel-cp-status.service" "$DEST_SYSTEMD/nuxel-cp-status.service"
install -m 0644 "$HERE/../systemd/nuxel-cpbootd.service"  "$DEST_SYSTEMD/nuxel-cpbootd.service"

# Seed a NEVER-POPULATED env template (comment-only) if absent.
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" <<ENVEOF
# Stage-04 physical trial parameters. THIS FILE IS INTENTIONALLY UNSET.
# Populate ONLY with owner-approved values, then invoke:
#   systemctl start nuxel-cpbootd.service
# STAGE04_MANIFEST_SHA256=  (SHA-256 of the immutable proposal file)
# STAGE04_FIRMWARE_PATH=    (read-only RADIO ITOC path)
# STAGE04_DEADLINE_MS=300000
ENVEOF
    chmod 0600 "$ENV_FILE"
    echo "seeded empty $ENV_FILE (unset; physical trial remaines disabled)"
fi

systemctl daemon-reload
# Enable ONLY the read-only probe (safe). NEVER enable the physical unit.
systemctl enable nuxel-cp-status.service 2>/dev/null || true
systemctl --no-block start nuxel-cp-status.service 2>/dev/null || true

echo "deployment complete:"
echo "  read-only probe: systemctl status nuxel-cp-status"
echo "  physical trial: DISABLED by default; requires owner-approved env + explicit start"
echo "  uninstall: nuxel-modem-install.sh --uninstall"
