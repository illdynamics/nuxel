#!/usr/bin/env bash
# install.sh — REVERSIBLE deployment of nuxel-radiod onto a normally-booted Nuxel.
# SPDX-License-Identifier: GPL-2.0-only
# Builds for the native architecture, installs binary + unit, enables the
# OBSERVER-ONLY service. It does NOT enable or trigger any CP boot.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_BIN=/usr/libexec/nuxel
DEST_SYS=/etc/systemd/system

if [[ "${1:-}" == "--uninstall" ]]; then
    systemctl disable --now nuxel-radiod.service 2>/dev/null || true
    rm -f "$DEST_SYS/nuxel-radiod.service" "$DEST_BIN/nuxel-radiod"
    systemctl daemon-reload
    echo "uninstalled nuxel-radiod"
    exit 0
fi

[[ $(id -u) -eq 0 ]] || { echo "run as root"; exit 1; }
mkdir -p "$DEST_BIN" "$DEST_SYS"

CFLAGS=(-O2 -Wall -Wextra -Werror -std=gnu11)
echo "building nuxel-radiod for $(uname -m)..."
gcc "${CFLAGS[@]}" -I"$HERE/src" -o "$HERE/nuxel-radiod" \
    "$HERE/src/radiod.c" "$HERE/src/transport.c" "$HERE/src/sipc5_fmt.c" \
    "$HERE/src/rfs_proto.c" "$HERE/src/rfs_respond.c" "$HERE/src/fmt_tx.c" \
    "$HERE/src/data_session.c" "$HERE/src/mbim_tx.c" "$HERE/src/rfs_nv.c" -lsystemd
install -m 0755 "$HERE/nuxel-radiod" "$DEST_BIN/nuxel-radiod"
install -m 0644 "$HERE/nuxel-radiod.service" "$DEST_SYS/nuxel-radiod.service"
systemctl daemon-reload
systemctl enable nuxel-radiod.service
echo "installed. start: systemctl start nuxel-radiod  (observer-only; no CP boot)"
