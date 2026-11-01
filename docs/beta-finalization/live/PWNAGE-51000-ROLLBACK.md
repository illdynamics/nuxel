# PWNAGE-51000 — rollback

## Kernel

Verified known-good boot image (the pre-flash `sda14`):

- `evidence/pwnage-51000/twrp/sda14.current.img`
- `build/backup/sda14-known-good-20261101.img`
- SHA-256 `97f78f5da871ef5df55113814096c9fb0c1de2671b04e11c7edd77630a6bc7da`

On-device copy: `/root/pwnage51000/sda14.known-good.img`
(SHA `7f3f4454…`; same kernel payload, partition tail differs).

From TWRP:

```sh
adb -s R58M75KDB2X push twrp/sda14.current.img /tmp/
adb -s R58M75KDB2X shell 'dd if=/tmp/sda14.current.img of=/dev/block/by-name/boot bs=1M; sync'
adb -s R58M75KDB2X shell 'sha256sum /dev/block/sda14'   # 97f78f5d…
adb -s R58M75KDB2X reboot
```

The new kernel image (for reference) is `574c239c…`; do not flash it again
without a new explicit approval.

## Runtime files changed in this run

Backups: `/var/backups/nuxel/pwnage51000-20261101T103722Z/`
(on-device). Restore individual files with `install -m 0644` / `install -m 0755`
then `systemctl daemon-reload` and restart the affected unit.

Changed:
- `/usr/share/nuxel/pwa/nuxel-home/js/launcher.js`
- `/usr/share/nuxel/nuxel-home/js/launcher.js`
- `/usr/share/nuxel/pwa/nuxel-home/js/gestures.js`
- `/usr/share/nuxel/nuxel-home/js/gestures.js`
- `/usr/share/nuxel/*/nuxel-home/js/lockscreen-indicators.js`
- `/usr/lib/nuxel/nuxel-flatpak-{firefox,signal,stremio}`
- `/usr/lib/nuxel/nuxel-bridge/software_provider.py`
- `/usr/share/nuxel/pwa/nuxel-apps/settings/index.html`
- `/usr/lib/nuxel/nuxel-audio-session.sh`
- `/usr/lib/nuxel/nuxel-usb-mode.sh`
- `/etc/systemd/system/nuxel-wayland.service.d/40-bounded-stop.conf`
- `/usr/lib/systemd/system/nuxel-audio-session.service.d/10-stop-bound.conf`
- `/etc/systemd/system/nuxel-abox-firmware-reload.service`
- `/etc/systemd/system/nuxel-abox-firmware-reload.timer`
- `/etc/systemd/system/nuxel-boot-sound.service`
- `/etc/systemd/system/nuxel-boot-sound.service.d/30-defer-abox.conf`
- `/etc/systemd/system/nuxel-usb-mode-restore.service`
- `/usr/lib64/libEGL_mesa.so.0` (symlink)
- `/usr/lib64/libgallium_dri.so` (kbase build)
- `/usr/lib64/dri/{panfrost,exynos}_dri.so` (symlinks)

## Graphics libraries

Known-good kbase set is in `build/out/s10plus/kbase-gpu/lib/` and the rootfs
builder now installs it. The pre-Wayland EGL backup
`/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland` is intact.

## Flatpak / sandbox

No sandbox weakening was deployed. `/usr/bin/bwrap` is 0755 (setuid removed);
to restore the old world, `chmod 4755 /usr/bin/bwrap` — but that is **not**
recommended and is not a supported path.
