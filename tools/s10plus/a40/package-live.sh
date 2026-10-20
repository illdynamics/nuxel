#!/bin/sh
# Build the A40 monitor userspace payload only. It contains no boot/kernel,
# partition, firmware, or device-node paths.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
OUT=${1:-"$ROOT/build/a40/nuxel-a40-monitor.tar.gz"}
"$ROOT/tools/s10plus/a40/build-metrics.sh" "$ROOT/build/a40/nuxel-metricsd"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/files" "$(dirname "$OUT")"
python3 - "$ROOT" "$WORK" <<'PY'
import hashlib, json, shutil, stat, sys
from pathlib import Path
root, work = map(Path, sys.argv[1:])
rows = [
 ('pwa/nuxel-home/index.html', '/usr/share/nuxel/pwa/nuxel-home/index.html', 0o644),
 ('pwa/nuxel-home/js/app.js', '/usr/share/nuxel/pwa/nuxel-home/js/app.js', 0o644),
 ('pwa/nuxel-home/js/launcher.js', '/usr/share/nuxel/pwa/nuxel-home/js/launcher.js', 0o644),
 ('pwa/nuxel-home/js/layout-model.js', '/usr/share/nuxel/pwa/nuxel-home/js/layout-model.js', 0o644),
 ('pwa/nuxel-home/js/gestures.js', '/usr/share/nuxel/pwa/nuxel-home/js/gestures.js', 0o644),
 ('pwa/nuxel-home/js/navigation.js', '/usr/share/nuxel/pwa/nuxel-home/js/navigation.js', 0o644),
 ('pwa/nuxel-home/js/recents.js', '/usr/share/nuxel/pwa/nuxel-home/js/recents.js', 0o644),
 ('pwa/nuxel-home/js/scroll-indicators.js', '/usr/share/nuxel/pwa/nuxel-home/js/scroll-indicators.js', 0o644),
 ('pwa/nuxel-home/js/home-settings.js', '/usr/share/nuxel/pwa/nuxel-home/js/home-settings.js', 0o644),
 ('pwa/nuxel-home/js/system-monitor.js', '/usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js', 0o644),
 ('pwa/nuxel-home/js/status-bar.js', '/usr/share/nuxel/pwa/nuxel-home/js/status-bar.js', 0o644),
 ('pwa/nuxel-home/css/launcher.css', '/usr/share/nuxel/pwa/nuxel-home/css/launcher.css', 0o644),
 ('pwa/nuxel-home/css/style.css', '/usr/share/nuxel/pwa/nuxel-home/css/style.css', 0o644),
 ('pwa/nuxel-home/css/status-bar.css', '/usr/share/nuxel/pwa/nuxel-home/css/status-bar.css', 0o644),
 ('pwa/nuxel-home/css/home-settings.css', '/usr/share/nuxel/pwa/nuxel-home/css/home-settings.css', 0o644),
 ('pwa/nuxel-home/sw.js', '/usr/share/nuxel/pwa/nuxel-home/sw.js', 0o644),
 ('pwa/nuxel-home/manifest.json', '/usr/share/nuxel/pwa/nuxel-home/manifest.json', 0o644),
 ('services/nuxel-metrics/nuxel-metrics.service', '/etc/systemd/system/nuxel-metrics.service', 0o644),
 ('services/nuxel-metrics/nuxel-metrics.socket', '/etc/systemd/system/nuxel-metrics.socket', 0o644),
 ('build/a40/nuxel-metricsd', '/usr/lib/nuxel/nuxel-metricsd', 0o755),
 ('services/nuxel-bridge/src/bridge.py', '/usr/bin/nuxel-bridge', 0o755),
 ('tools/s10plus/a33/nuxel-sound-cue.py', '/usr/libexec/nuxel/nuxel-sound-cue', 0o755),
 # The measured 72-second failure is nonessential boot audio. This unit moves
 # it off multi-user's critical path and gives it an evidence-based bound.
 ('services/nuxel-session/systemd/nuxel-boot-sound.service', '/etc/systemd/system/nuxel-boot-sound.service', 0o644),
]
# Artwork is separately hash-audited before deployment.  It is deliberately
# excluded from this small live delta because the verified CDC console moves
# binary image chunks at 128 base64 characters/frame; resending unchanged PNGs
# would turn a launcher repair into an hours-long, interruption-prone transfer.
manifest=[]
for rel, target, mode in rows:
    source=root/rel
    if not source.is_file(): raise SystemExit('missing '+str(source))
    body=source.read_bytes(); dest=work/'files'/target.lstrip('/')
    dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(body); dest.chmod(mode)
    manifest.append({'path': target, 'source': rel, 'mode': mode, 'sha256': hashlib.sha256(body).hexdigest()})
(work/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
PY
tar -C "$WORK" -czf "$OUT" manifest.json files
sha256sum "$OUT"
