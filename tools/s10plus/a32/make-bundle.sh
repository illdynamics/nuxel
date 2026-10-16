#!/usr/bin/env bash
# make-bundle.sh — stage every A32 artifact into one deployable tree.
#
# The tree mirrors the target layout (paths under ./root/), so the phone-side
# installer can copy each file with a backup and a hash check.  Nothing here
# touches the phone.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="$ROOT/build/out/s10plus/a32"
B="$ROOT/build/out/s10plus/a32/bundle"
rm -rf "$B"; mkdir -p "$B/root"

# 1. binaries
mkdir -p "$B/root/usr/lib/nuxel" "$B/root/usr/bin" "$B/root/etc/systemd/system"
for b in nuxel-wl-fb nuxel-pwa-host nuxel-button-manager; do
  install -m 755 "$OUT/$b" "$B/root/usr/lib/nuxel/$b"
done
mkdir -p "$B/root/usr/bin"; cp -p "$HERE/nuxelctl" "$B/root/usr/bin/nuxelctl"; chmod 755 "$B/root/usr/bin/nuxelctl"
cp -p "$HERE/nuxel-button-manager.service" "$B/root/etc/systemd/system/nuxel-button-manager.service"; chmod 644 "$B/root/etc/systemd/system/nuxel-button-manager.service"

# 2. launcher PWA (only the files this cycle changed or added)
mkdir -p "$B/root/usr/share/nuxel/nuxel-home/js" "$B/root/usr/share/nuxel/nuxel-home/css"
for f in index.html js/app.js js/apps.js js/status-bar.js js/host-bridge.js js/safe-zones.js js/osd.js; do
  mkdir -p "$B/root/usr/share/nuxel/nuxel-home/$(dirname "$f")"
  cp -p "$ROOT/pwa/nuxel-home/$f" "$B/root/usr/share/nuxel/nuxel-home/$f"
done

# 3. Nuxel Settings + Nuxel Terminal apps (the authoritative pwa tree layout)
for a in settings terminal; do
  mkdir -p "$B/root/usr/share/nuxel/pwa/nuxel-apps/$a"
  for f in "$ROOT/pwa/nuxel-apps/$a"/*; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in .keep) continue ;; esac
    cp -p "$f" "$B/root/usr/share/nuxel/pwa/nuxel-apps/$a/$(basename "$f")"
  done
done

# 4. default configuration (installed only when absent, so a user's own choice is
#    never overwritten by an upgrade)
mkdir -p "$B/root/etc/nuxel/display" "$B/root/etc/nuxel/input"
cat > "$B/root/etc/nuxel/display/statusbar-safezones.json" <<'JSON'
{
  "schema_version": 1,
  "zones": 10,
  "profiles": {
    "s10plus": { "portrait": [9, 10], "landscape_left": [], "landscape_right": [] },
    "pixel_center": { "portrait": [5, 6], "landscape_left": [], "landscape_right": [] },
    "none": { "portrait": [], "landscape_left": [], "landscape_right": [] },
    "left_camera": { "portrait": [1, 2], "landscape_left": [1, 2], "landscape_right": [9, 10] },
    "right_camera": { "portrait": [9, 10], "landscape_left": [9, 10], "landscape_right": [1, 2] }
  },
  "padding_dp": 6,
  "profile": "s10plus",
  "orientation": "portrait",
  "custom": { "portrait": [], "landscape_left": [], "landscape_right": [] }
}
JSON
cat > "$B/root/etc/nuxel/input/buttons.json" <<'JSON'
{
  "schema_version": 1,
  "bixby_short": "open-terminal",
  "bixby_long": "disabled",
  "power_short": "screen-toggle",
  "power_long": "power-menu",
  "volume_up": "volume-up",
  "volume_down": "volume-down"
}
JSON

# 5. the installer that runs ON the phone
cp -p "$HERE/install-on-phone.sh" "$B/install-on-phone.sh"; chmod 755 "$B/install-on-phone.sh"

( cd "$B" && find . -type f | sort > MANIFEST.txt )
tar czf "$OUT/nuxel-a32-bundle.tar.gz" -C "$B" .
echo "== bundle =="
ls -l "$OUT/nuxel-a32-bundle.tar.gz"
cat "$B/MANIFEST.txt"
