#!/bin/sh
set -eu
B=/var/backups/nuxel/p89000-20261107T151308Z
[ -d "$B" ] || { echo "backup missing: $B" >&2; exit 1; }
tar -C / -xpf "$B/systemd-units.tar"
tar -C / -xpf "$B/nuxel-scripts.tar"
tar -C / -xpf "$B/nuxel-state.tar" || true
systemctl daemon-reload
# Restore enablement is already inside systemd-units.tar; re-assert key links.
systemctl enable nuxel-soundd.service nuxel-clockd.service nuxel-web.service nuxel-wayland.service nuxel-wl-fb.service nuxel-interface-state.service >/dev/null 2>&1 || true
systemctl disable nuxel-mic-route.path >/dev/null 2>&1 || true
systemctl restart nuxel-soundd.service nuxel-clockd.service
echo "rollback restored $B; verify systemctl --failed"
