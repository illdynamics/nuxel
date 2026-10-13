#!/usr/bin/env bash
set -euo pipefail
echo "=== Rolling back to PWA Kiosk Home ==="
systemctl --user disable --now nuxel-home-native.service || true
systemctl --user enable --now nuxel-home-kiosk.service
systemctl --user restart nuxel-home-kiosk.service
echo "Rollback complete. PWA Kiosk Home is now active."
