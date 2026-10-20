#!/bin/sh
# Restore the exact pre-deploy Nuxel v0.6.3-beta live files, then restart
# only the two bridge services. Safe to run from the USB console.
set -eu
B=/var/backups/nuxel/v0.6.3-beta-pre-20261020T123441Z
W=/usr/share/nuxel
FILES='pwa/nuxel-home/index.html pwa/nuxel-home/manifest.json pwa/nuxel-home/sw.js pwa/nuxel-home/css/style.css pwa/nuxel-home/css/launcher.css pwa/nuxel-home/js/launcher.js pwa/nuxel-home/js/gestures.js pwa/nuxel-home/js/home-settings.js pwa/nuxel-home/js/apps.js pwa/nuxel-home/assets/nuxel-bottom-bar.jpg pwa/nuxel-home/assets/nuxel-bottom-bar2.png assets/nuxel-bottom-bar.jpg assets/nuxel-bottom-bar2.png pwa/nuxel-apps/settings/index.html pwa/nuxel-apps/settings/settings.css pwa/nuxel-apps/settings/wifi-settings.js pwa/nuxel-common/app-registry.json'
for rel in $FILES; do
    [ -f "$B/webroot/$rel" ] || continue
    mkdir -p "$W/$(dirname "$rel")"
    install -o root -g root -m 0644 "$B/webroot/$rel" "$W/$rel.rollback.$$"
    mv -f "$W/$rel.rollback.$$" "$W/$rel"
done
# A file that did not exist before the deploy must be absent after rollback.
if [ -f "$B/missing.txt" ]; then
    while read tag path; do
        [ "$tag" = MISSING ] || continue
        case "$path" in
            /usr/share/nuxel/*)
                if [ -e "$path" ]; then
                    mv "$path" "$B/created-by-deploy-$(basename "$path")"
                fi
                ;;
        esac
    done < "$B/missing.txt"
fi
for p in nuxel-bridge nuxel-http-bridge; do
    install -o root -g root -m 0755 "$B/bin/$p" "/usr/bin/$p.rollback.$$"
    mv -f "/usr/bin/$p.rollback.$$" "/usr/bin/$p"
done
for p in api.py bridge.py; do
    install -o root -g root -m 0644 "$B/lib/$p" "/usr/lib/nuxel/nuxel-bridge/$p.rollback.$$"
    mv -f "/usr/lib/nuxel/nuxel-bridge/$p.rollback.$$" "/usr/lib/nuxel/nuxel-bridge/$p"
done
systemctl restart nuxel-bridge nuxel-http-bridge || true
sleep 2
systemctl is-active nuxel-bridge nuxel-http-bridge || true
echo "ROLLBACK COMPLETE from $B"
