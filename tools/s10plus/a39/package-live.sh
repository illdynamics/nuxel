#!/bin/sh
# A39 isolated userspace payload (no boot image/firmware/kernel/partition paths).
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
OUT=${1:-"$ROOT/build/a39/nuxel-a39-home.tar.gz"}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/files" "$(dirname "$OUT")"
cat > "$WORK/includes.txt" <<'EOF'
pwa/nuxel-home/index.html
pwa/nuxel-home/manifest.json
pwa/nuxel-home/sw.js
pwa/nuxel-home/js/home-settings.js
pwa/nuxel-home/js/layout-model.js
pwa/nuxel-home/js/launcher.js
pwa/nuxel-home/js/gestures.js
pwa/nuxel-home/js/navigation.js
pwa/nuxel-home/js/app.js
pwa/nuxel-home/js/status-bar.js
pwa/nuxel-home/js/scroll-indicators.js
pwa/nuxel-home/css/style.css
pwa/nuxel-home/css/status-bar.css
pwa/nuxel-home/css/home-settings.css
pwa/nuxel-home/css/launcher.css
pwa/nuxel-home/assets/nuxel-background.png
pwa/nuxel-home/assets/nuxel-bottom-bar.jpg
pwa/nuxel-home/assets/nuxel-bottom-bar2.png
assets/nuxel-bottom-bar.jpg
assets/nuxel-bottom-bar2.png
EOF
: > "$WORK/manifest.tsv"
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  case "$rel" in pwa/nuxel-home/*|assets/nuxel-bottom-bar*) ;; *) echo "refused $rel" >&2; exit 1;; esac
  test -s "$ROOT/$rel"
  install -D -m 0644 "$ROOT/$rel" "$WORK/files/usr/share/nuxel/$rel"
  sum=$(sha256sum "$WORK/files/usr/share/nuxel/$rel" | awk '{print $1}')
  printf '%s\t0644\t%s\n' "/usr/share/nuxel/$rel" "$sum" >> "$WORK/manifest.tsv"
done < "$WORK/includes.txt"
tar -C "$WORK" -czf "$OUT" manifest.tsv files
sha256sum "$OUT"
