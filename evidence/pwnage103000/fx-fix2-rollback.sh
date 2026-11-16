#!/bin/sh
# PWNAGE-103000 FX follow-up #2 rollback — restores the seven PWA files that
# changed, from the pre-change backup. No partition, no kernel, no reboot.
set -eu
B=/root/nuxel-backup-103000-fxfix2-20261112T120614Z
P=/usr/share/nuxel/pwa
for f in edge-lighting.js edge-lighting.css index.html sw.js manifest.json; do
  cp -a "$B/home-js/$f" "$P/nuxel-home/$f"
done
cp -a "$B/edge-fx/index.html" "$P/nuxel-apps/edge-fx/index.html"
cp -a "$B/edge-fx/edge-fx.js" "$P/nuxel-apps/edge-fx/edge-fx.js"
cp -a "$B/edge-fx/edge-fx.css" "$P/nuxel-apps/edge-fx/edge-fx.css"
grep -q "v097-p103000" "$P/nuxel-home/sw.js" && echo "rollback: cache marker v097-p103000 restored"
echo "rollback: files restored from $B (user Edge Lighting settings untouched)"
