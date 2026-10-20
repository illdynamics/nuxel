#!/bin/sh
# Nuxel v0.6.3-beta live userspace deploy.
# Userspace only: no partition, kernel, modem or firmware writes.
set -eu
PAYLOAD=/tmp/nuxel-v0.6.3-beta-live-userspace.tar.gz
EXPECT=012c14cb74f26098dab965ba04dbbd99fcef53eb4ec654bd246671a2741e52b8
W=/usr/share/nuxel
LIB=/usr/lib/nuxel/nuxel-bridge
FILES='pwa/nuxel-home/index.html pwa/nuxel-home/manifest.json pwa/nuxel-home/sw.js pwa/nuxel-home/css/style.css pwa/nuxel-home/css/launcher.css pwa/nuxel-home/js/launcher.js pwa/nuxel-home/js/gestures.js pwa/nuxel-home/js/home-settings.js pwa/nuxel-home/js/apps.js pwa/nuxel-home/assets/nuxel-bottom-bar.jpg pwa/nuxel-home/assets/nuxel-bottom-bar2.png assets/nuxel-bottom-bar.jpg assets/nuxel-bottom-bar2.png pwa/nuxel-apps/settings/index.html pwa/nuxel-apps/settings/settings.css pwa/nuxel-apps/settings/wifi-settings.js pwa/nuxel-common/app-registry.json'

ACTUAL=$(sha256sum "$PAYLOAD" | cut -d' ' -f1)
if [ "$ACTUAL" != "$EXPECT" ]; then
    echo "PAYLOAD_HASH_MISMATCH actual=$ACTUAL expected=$EXPECT"
    exit 2
fi
STAGE=$(mktemp -d /var/tmp/nuxel-stage.XXXXXX)
python3 - "$PAYLOAD" "$STAGE" <<'PY'
import tarfile, os, sys, hashlib, json
p, stage = sys.argv[1], sys.argv[2]
with tarfile.open(p, 'r:gz') as tf:
    man = json.load(tf.extractfile('manifest.json'))
    assert man['version'] == 'v0.6.3-beta', man['version']
    assert len(man['files']) == 19, len(man['files'])
    for e in man['files']:
        rel = e['source']
        assert '..' not in rel.split('/') and not rel.startswith('/'), rel
        m = tf.getmember('files/' + rel)
        assert m.isfile() and not m.issym(), rel
        data = tf.extractfile(m).read()
        assert len(data) == e['bytes'], rel
        assert hashlib.sha256(data).hexdigest() == e['sha256'], rel
        dest = os.path.join(stage, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(data)
print('STAGED', len(man['files']), stage)
PY
python3 -m py_compile "$STAGE/services/nuxel-bridge/src/bridge.py" "$STAGE/services/nuxel-bridge/src/api.py" || { echo BRIDGE_SYNTAX_FAIL; exit 3; }
for rel in $FILES; do
    src="$STAGE/$rel"
    dest="$W/$rel"
    [ -f "$src" ] || { echo "STAGE_MISSING $rel"; exit 4; }
    mkdir -p "$(dirname "$dest")"
    install -o root -g root -m 0644 "$src" "$dest.deploy.$$"
    mv -f "$dest.deploy.$$" "$dest"
    echo "INSTALLED $dest"
done
install_atomic() {
    src=$1; dest=$2; mode=$3
    install -o root -g root -m "$mode" "$src" "$dest.deploy.$$"
    mv -f "$dest.deploy.$$" "$dest"
    echo "INSTALLED $dest"
}
install_atomic "$STAGE/services/nuxel-bridge/src/bridge.py" /usr/bin/nuxel-bridge 0755
install_atomic "$STAGE/services/nuxel-bridge/src/api.py" /usr/bin/nuxel-http-bridge 0755
install_atomic "$STAGE/services/nuxel-bridge/src/bridge.py" "$LIB/bridge.py" 0644
install_atomic "$STAGE/services/nuxel-bridge/src/api.py" "$LIB/api.py" 0644
echo "--- POST-INSTALL HASHES ---"
for rel in $FILES; do sha256sum "$W/$rel"; done
sha256sum /usr/bin/nuxel-bridge /usr/bin/nuxel-http-bridge "$LIB/bridge.py" "$LIB/api.py"
echo "STAGE_DIR=$STAGE"
echo "DEPLOY_COMPLETE"
