#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
CFG="${1:-}"
[ -f "$CFG" ] || die 'Usage: 16-kernel-config-audit.sh /path/to/Nuxel-kernel/.config[.gz]'
init_out kernel-config
python3 "$PACK_DIR/tools/kernel_config_audit.py" "$CFG" > "$NUXEL_OUT/NUXEL-KERNEL-CONFIG-AUDIT.txt"
cat "$NUXEL_OUT/NUXEL-KERNEL-CONFIG-AUDIT.txt"
say 'Config flags alone do not prove modules/drivers are loadable on the phone.'
