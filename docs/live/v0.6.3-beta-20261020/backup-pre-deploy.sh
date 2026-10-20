#!/bin/sh
# Nuxel v0.6.3-beta pre-deploy backup. Read-only w.r.t. live target files.
set -eu
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
B=/var/backups/nuxel/v0.6.3-beta-pre-$STAMP
W=/usr/share/nuxel
FILES='pwa/nuxel-home/index.html pwa/nuxel-home/manifest.json pwa/nuxel-home/sw.js pwa/nuxel-home/css/style.css pwa/nuxel-home/css/launcher.css pwa/nuxel-home/js/launcher.js pwa/nuxel-home/js/gestures.js pwa/nuxel-home/js/home-settings.js pwa/nuxel-home/js/apps.js pwa/nuxel-home/assets/nuxel-bottom-bar.jpg pwa/nuxel-home/assets/nuxel-bottom-bar2.png assets/nuxel-bottom-bar.jpg assets/nuxel-bottom-bar2.png pwa/nuxel-apps/settings/index.html pwa/nuxel-apps/settings/settings.css pwa/nuxel-apps/settings/wifi-settings.js pwa/nuxel-common/app-registry.json'
mkdir -p "$B/webroot" "$B/bin" "$B/lib" "$B/units"
for rel in $FILES; do
    src=$W/$rel
    if [ -f "$src" ]; then
        mkdir -p "$B/webroot/$(dirname "$rel")"
        cp -a "$src" "$B/webroot/$rel"
    else
        echo "MISSING $src" >> "$B/missing.txt"
    fi
done
cp -a /usr/bin/nuxel-bridge "$B/bin/nuxel-bridge"
cp -a /usr/bin/nuxel-http-bridge "$B/bin/nuxel-http-bridge"
cp -a /usr/lib/nuxel/nuxel-bridge/api.py "$B/lib/api.py"
cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py "$B/lib/bridge.py"
cp -a /etc/systemd/system/nuxel-bridge.service "$B/units/nuxel-bridge.service" 2>/dev/null || true
cp -a /etc/systemd/system/nuxel-http-bridge.service "$B/units/nuxel-http-bridge.service" 2>/dev/null || true
stat -c '%a %U:%G %n' /usr/bin/nuxel-bridge /usr/bin/nuxel-http-bridge \
    /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/bridge.py \
    /usr/share/nuxel/pwa/nuxel-home/index.html > "$B/stat.txt" 2>&1
systemctl is-active nuxel-web nuxel-bridge nuxel-http-bridge > "$B/services-before.txt" 2>&1 || true
{
    echo "webroot=/usr/share/nuxel"
    echo "server_pid=$(pgrep -f 'http.server 8000' | head -1)"
    echo "server_cwd=$(readlink -f /proc/$(pgrep -f 'http.server 8000' | head -1)/cwd 2>/dev/null || true)"
} > "$B/active-paths.txt" 2>&1
( cd "$B/webroot" && find . -type f -exec sha256sum {} + ) > "$B/SHA256SUMS.webroot"
( cd "$B/bin" && sha256sum nuxel-bridge nuxel-http-bridge ) > "$B/SHA256SUMS.bin"
( cd "$B/lib" && sha256sum api.py bridge.py ) > "$B/SHA256SUMS.lib"
cat > "$B/rollback.sh" <<EOF
#!/bin/sh
set -eu
B=$B
W=/usr/share/nuxel
for rel in $FILES; do
    [ -f "\$B/webroot/\$rel" ] || continue
    mkdir -p "\$W/\$(dirname "\$rel")"
    install -o root -g root -m 0644 "\$B/webroot/\$rel" "\$W/\$rel.rollback.\$\$"
    mv -f "\$W/\$rel.rollback.\$\$" "\$W/\$rel"
done
for p in nuxel-bridge nuxel-http-bridge; do
    install -o root -g root -m 0755 "\$B/bin/\$p" "/usr/bin/\$p.rollback.\$\$"
    mv -f "/usr/bin/\$p.rollback.\$\$" "/usr/bin/\$p"
done
for p in api.py bridge.py; do
    install -o root -g root -m 0644 "\$B/lib/\$p" "/usr/lib/nuxel/nuxel-bridge/\$p.rollback.\$\$"
    mv -f "/usr/lib/nuxel/nuxel-bridge/\$p.rollback.\$\$" "/usr/lib/nuxel/nuxel-bridge/\$p"
done
systemctl restart nuxel-bridge nuxel-http-bridge || true
sleep 2
systemctl is-active nuxel-bridge nuxel-http-bridge || true
echo "ROLLBACK COMPLETE from \$B"
EOF
chmod 755 "$B/rollback.sh"
echo "BACKUP_DIR=$B"
echo "--- SERVICES BEFORE ---"
cat "$B/services-before.txt"
echo "--- ACTIVE PATHS ---"
cat "$B/active-paths.txt"
echo "--- SHA256SUMS.webroot ---"
cat "$B/SHA256SUMS.webroot"
echo "--- SHA256SUMS.bin ---"
cat "$B/SHA256SUMS.bin"
echo "--- SHA256SUMS.lib ---"
cat "$B/SHA256SUMS.lib"
echo "BACKUP_END"
