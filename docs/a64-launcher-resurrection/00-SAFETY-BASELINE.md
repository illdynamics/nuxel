# 00 — Safety baseline

## Live recovery terminal (verified)
- Host console node: `/dev/ttyACM0`, USB `18d1:4ee7` (Google/Nuxel live-console gadget).
- Session: `tools/beta/live/nuxel_live.py` (`open_console`, framed + SHA-256 verified).
- Device shell: `root` (`sh-5.3`), kernel `4.14.253 aarch64`, uptime 17 min at first probe.
- The A63-era `nuxel-web.service` is `inactive` and `disabled`; the real launcher
  server is `nuxel-pwa-host` (child of `phoc`), which serves `/usr/share/nuxel` on
  `127.0.0.1:8000` and spawns the WebKit view (`DEFAULT_URL
  http://127.0.0.1:8000/pwa/nuxel-home/index.html`).
- Active units at repair time: `nuxel-wayland`, `nuxel-wl-fb`,
  `nuxel-button-manager`, `nuxel-touch-arm`, `nuxel-bridge`, `nuxel-http-bridge`,
  `nuxel-notifications`, `nuxel-portal`, `NetworkManager`, `ModemManager`,
  `seatd`. `nuxel-verbose-boot`/`nuxel-anim-handoff`/`nuxel-boot-anim` were already
  `inactive` (boot handoff complete).

## Device backup (outside the replaced path)
- `/var/tmp/nuxel-a64-prebackup-20261023T105215/nuxel-home-tree/` — full byte copy of
  the live launcher tree (`/usr/share/nuxel/nuxel-home`, 9.5M). Note
  `/usr/share/nuxel/pwa/nuxel-home` is a symlink to `../nuxel-home`.
- `/var/tmp/nuxel-a64-prebackup-20261023T105215/SHA256SUMS-text.txt` — pre-fix text-file hashes.
- `/var/tmp/nuxel-a64-prebackup-20261023T105215/launcher.css.broken` — the 0-byte broken CSS (rollback artifact).

## Git baseline
- Repo: `/x/nuxel`, branch `main` at `7972bbf` (ahead of `origin/main` by 3 local
  A63 commits `153e4b8`, `ace883e`, `7972bbf`).
- Worktree pre-existing modifications (NOT part of this repair, left untouched):
  `tools/beta/live/deploy-manifest.json`, `tools/s10plus/a34/nuxel-wl-fb.c`,
  `tools/s10plus/a45/nuxel-button-manager.c`,
  `tools/s10plus/a45/test-lockscreen-unlock.js`.
- Pre-existing untracked launcher files (already deployed, not part of this fix):
  `pwa/nuxel-home/css/lockscreen.css`, `pwa/nuxel-home/js/lockscreen.js`.

## Rollback (short form)
Restore the empty/broken launcher and reload if the fix ever needs to be reverted:
```sh
printf 'action lock\n' > /run/nuxel-pwa-host.cmd  # optional, return to lock
cp -a /var/tmp/nuxel-a64-prebackup-20261023T105215/nuxel-home-tree/css/launcher.css \
      /usr/share/nuxel/nuxel-home/css/launcher.css
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd
```
Restore the display backlight if it was left off:
```sh
echo 0 > /sys/class/backlight/panel/bl_power
echo 12800 > /sys/class/backlight/panel/brightness
```
