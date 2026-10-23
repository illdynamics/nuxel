# A59 — Rollback paths

## Source (Mac repo)
```sh
git checkout -- pwa/nuxel-common/app-registry.json \
  pwa/nuxel-home/index.html \
  pwa/nuxel-home/js/app.js \
  pwa/nuxel-home/js/apps.js \
  pwa/nuxel-home/sw.js \
  services/nuxel-bridge/src/api.py
# new (remove if desired)
rm -rf tools/s10plus/a59 build/out/s10plus/a59
```
Local `*.a59-bak` copies also exist next to each edited file.

## Device (rootfs) — revert to this session's pre-edit backups
Tag: `20261022T202602`
```sh
for f in /usr/lib/nuxel/nuxel-bridge/api.py \
         /usr/share/nuxel/nuxel-home/js/apps.js \
         /usr/share/nuxel/nuxel-home/js/app.js \
         /etc/nuxel/app-registry/app_registry.json; do
  cp -p "$f.a59-bak-20261022T202602" "$f"
done
# registry is served from the pwa tree, so also restore that copy from /etc copy
cp -p /etc/nuxel/app-registry/app_registry.json \
      /usr/share/nuxel/pwa/nuxel-common/app-registry.json
# index.html + sw.js (bumped cache-busters/version)
#   restored from repo or from their .a59-bak on the Mac, re-PUT to the device.
systemctl restart nuxel-http-bridge nuxel-wayland
```

## New packages installed this session (removable with `rpm -e`)
- `snapshot-49.0-1.fc43.aarch64`
- `gstreamer1-plugins-bad-free-1.26.11-1.fc43.aarch64` (--nodeps)
- `gstreamer1-plugin-gtk4-0.14.2-1.fc43.aarch64` (--nodeps)
- `firefox-157.0.1-1.fc43.aarch64` (--nodeps; note optional deps skipped)
- `mozilla-filesystem-1.9-36`, `fdk-aac-free-2.0.0-16`, `libvpx-1.15.0-4`,
  `pciutils-libs-3.15.0-1`

Remove example (reverse order, dry-run first):
```sh
rpm -e --test firefox snapshot gstreamer1-plugin-gtk4 gstreamer1-plugins-bad-free \
  mozilla-filesystem fdk-aac-free libvpx pciutils-libs
```

## New binary
- `/usr/lib/nuxel/nuxel-foreign-toplevel` (remove: `rm` it; the helper is only
  invoked by `/api/v1/apps/home`).

## USB console
- No kernel/bootloader/recovery flash, no firmware/boot asset write, no
  unapproved reboot, no SELinux/sandbox weakening were performed. The CDC-ACM
  console remained reachable after every userspace restart.
