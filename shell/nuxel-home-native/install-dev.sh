#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== Installing Nuxel Home (dev mode) ==="
sudo cp "$SCRIPT_DIR/nuxel-home-launcher" /usr/local/bin/nuxel-home
sudo chmod +x /usr/local/bin/nuxel-home
mkdir -p ~/.config/systemd/user
echo "Done. Run: /usr/local/bin/nuxel-home --debug"
