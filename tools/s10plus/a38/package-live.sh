#!/bin/sh
# Build the deliberately small, hash-manifested A38 Home payload.  This never
# contains a boot, firmware, kernel, partition image, or user layout data.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
out=${1:-"$root/build/a38/nuxel-a38-home.tar.gz"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/files/usr/share/nuxel/pwa/nuxel-home/js" "$work/files/usr/share/nuxel/pwa/nuxel-home/css" "$(dirname "$out")"
files='
pwa/nuxel-home/index.html
pwa/nuxel-home/sw.js
pwa/nuxel-home/js/layout-model.js
pwa/nuxel-home/js/gestures.js
pwa/nuxel-home/js/launcher.js
pwa/nuxel-home/js/app.js
pwa/nuxel-home/js/recents.js
pwa/nuxel-home/js/qs.js
pwa/nuxel-home/css/launcher.css
pwa/nuxel-home/css/status-bar.css
'
printf '%s\n' "$files" | while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  src="$root/$rel"; target="/usr/share/nuxel/$rel"
  test -f "$src"; install -D -m 0644 "$src" "$work/files$target"
  sum=$(sha256sum "$work/files$target" | awk '{print $1}')
  printf '%s\t0644\t%s\n' "$target" "$sum" >> "$work/manifest.tsv"
done
tar -C "$work" -czf "$out" manifest.tsv files
sha256sum "$out"
