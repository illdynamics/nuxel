# PWNAGE-49000 — deployment and rollback

No live deployment was performed in this run: the documented handset address
was not routable and no USB/serial path was present. This is the exact staged
procedure for the owner/next run.

## What changed

| Source | Installed target | Notes |
|---|---|---|
| `pwa/nuxel-home/**` | `/usr/share/nuxel/pwa/nuxel-home/**` | cache `v73-p49000` |
| `pwa/nuxel-apps/authenticator/**` | `/usr/share/nuxel/pwa/nuxel-apps/authenticator/**` | + `vendor/jsQR.js`, SW `v2-p49000` |
| `pwa/nuxel-apps/nuxtore/js/nuxtore.js` | same tree | Live Console alias |
| `tools/s10plus/a45/nuxel-statusbar.c` | `/usr/lib/nuxel/nuxel-statusbar` | rebuild on aarch64 |
| `tools/s10plus/a45/nuxel-navdock.c` | `/usr/lib/nuxel/nuxel-navdock` | rebuild on aarch64 |

The rootfs builder (`images/s10plus/build-phone-rootfs-inside-fedora.sh`)
already copies the whole `pwa/` tree and compiles both native tools from
`tools/s10plus/a45`, so a clean image build contains these changes.

## Pre-deploy backup (on device)

```sh
TS=$(date -u +%Y%m%dT%H%M%SZ)
B=/var/lib/nuxel/pwnage49000-backup-$TS
install -d -m 0700 "$B"
cp -a /usr/share/nuxel/pwa/nuxel-home "$B"/
cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator "$B"/
cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore "$B"/
install -m 0755 /usr/lib/nuxel/nuxel-statusbar "$B"/nuxel-statusbar.prev
install -m 0755 /usr/lib/nuxel/nuxel-navdock "$B"/nuxel-navdock.prev
sha256sum /usr/lib/nuxel/nuxel-statusbar /usr/lib/nuxel/nuxel-navdock > "$B"/sha256.before
```

Do **not** back up or copy the decrypted Authenticator vault; the encrypted
localStorage envelope stays in place.

## Staged install

```sh
# PWA assets (atomic per file; service worker version bump forces a new cache)
rsync -a --checksum pwa/nuxel-home/ /usr/share/nuxel/pwa/nuxel-home/
rsync -a --checksum pwa/nuxel-apps/authenticator/ \
  /usr/share/nuxel/pwa/nuxel-apps/authenticator/
rsync -a --checksum pwa/nuxel-apps/nuxtore/ \
  /usr/share/nuxel/pwa/nuxel-apps/nuxtore/

# Native tools: stop only the two overlay clients, never the compositor or fb owner
systemctl stop nuxel-wayland.service 2>/dev/null || true   # only if the unit owns these two
install -m 0755 build/out/s10plus/nuxel-statusbar /usr/lib/nuxel/nuxel-statusbar
install -m 0755 build/out/s10plus/nuxel-navdock   /usr/lib/nuxel/nuxel-navdock
systemctl start nuxel-wayland.service
```

Preferred: deploy by booting the staged rootfs image, preserving `/home` and
`/var/lib/nuxel/security`.

## Post-deploy checks

```sh
journalctl -u nuxel-wayland -b --no-pager | grep -E 'NAV_DOCK|STATUSBAR'
cat /run/nuxel-navdock.state
cat /run/nuxel-statusbar.state
cat /run/nuxel/security/lock-state.json
curl -s http://127.0.0.1:8080/api/v1/system/security
```

Expected `nuxel-statusbar` state transitions:
`STATUSBAR_START_HIDDEN locked=0 home=1` on Home/lockscreen, then
`STATUSBAR_SHOWN locked=0` only while a native/Flatpak toplevel is on glass.
`STATUSBAR_HIDDEN reason=lock_or_home` on return to Home or lock.

## Rollback

```sh
B=/var/lib/nuxel/pwnage49000-backup-<TS>
rsync -a --delete "$B"/nuxel-home/ /usr/share/nuxel/pwa/nuxel-home/
rsync -a --delete "$B"/authenticator/ /usr/share/nuxel/pwa/nuxel-apps/authenticator/
rsync -a --delete "$B"/nuxtore/ /usr/share/nuxel/pwa/nuxel-apps/nuxtore/
install -m 0755 "$B"/nuxel-statusbar.prev /usr/lib/nuxel/nuxel-statusbar
install -m 0755 "$B"/nuxel-navdock.prev   /usr/lib/nuxel/nuxel-navdock
systemctl restart nuxel-wayland.service
sha256sum -c "$B"/sha256.before
```

If the nav dock or top bar ever fails to start, the compositor/Home/SSH path is
unaffected; the previous binaries restore the prior overlay behaviour. Never
remove the serial console or the single `/dev/fb0` owner as a rollback step.
