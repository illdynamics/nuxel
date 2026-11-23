#!/usr/bin/env bash
# Copy the current PenGuru PWA into the APK asset tree. The PWA remains the
# single source of truth; this directory is generated and never edited.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/assets/public"

python3 - "$OUT" <<'PY'
import shutil, sys
from pathlib import Path
out = Path(sys.argv[1])
if out.exists():
    shutil.rmtree(out)
(out / 'pwa/nuxel-apps/penguru').mkdir(parents=True)
(out / 'pwa/nuxel-common').mkdir(parents=True)
(out / 'assets').mkdir(parents=True)
PY

APP="$ROOT/pwa/nuxel-apps/penguru"
COMMON="$ROOT/pwa/nuxel-common"
for name in index.html penguru.js penguru.css voice.js model-library.js manifest.json; do
  cp "$APP/$name" "$OUT/pwa/nuxel-apps/penguru/$name"
done
for name in bridge.js bridge-version.json theme.css; do
  cp "$COMMON/$name" "$OUT/pwa/nuxel-common/$name"
done
cp "$ROOT/assets/nuxel-penguru-squad.png" "$OUT/assets/nuxel-penguru-squad.png"

test -s "$OUT/pwa/nuxel-apps/penguru/index.html"
test -s "$OUT/pwa/nuxel-common/bridge.js"
test -s "$OUT/assets/nuxel-penguru-squad.png"
echo "Staged PenGuru web assets into $OUT"
find "$OUT" -type f -printf '  %P\n' | sort
