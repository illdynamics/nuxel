# A65 — Rollback

## Device rollback (per subsystem)
- TLS/GIO:
  - `mv /usr/lib64/gio/modules/giomodule.cache.a65-disabled /usr/lib64/gio/modules/giomodule.cache`
    (restores the old cache; but keep the backup `giomodule.cache.nuxel-a65-bak`).
  - `mv /usr/lib64/gio/modules/libgiognutls.so /usr/lib64/gio/modules/libgiognutls.so.a65-off`
    (removes GnuTLS backend, returns to GDummyTlsBackend — only for regression isolation).
- PWA/browser/native-camera files: each deployed target has `*.nuxel-a65-bak` on the
  device; restore with `cp <target>.nuxel-a65-bak <target>`.
  - calculator.js, camera.js, camera index.html, camera.css,
    nuxel_browser_native.py, nuxel_camera_native.py.
- Browser app restart: `systemctl`-managed app cgroups respawn on next launcher launch;
  no manual rollback needed.

## Git rollback
- Feature branch `nuxel/a65-hyperfix-14000`; pre-merge state is preserved on the
  previous main commit. `git revert` the A65 merge commit if needed.
- VERSION can be reverted to v0.6.4-beta before a release tag is created.

## Recovery console (verified)
- USB CDC ACM: `/dev/ttyACM0`, raw mode. Helper used: `/tmp/nx.sh "<command>"`.
- `echo 1 > /proc/sys/kernel/printk` and `stty -echo` quiet the multiplexed kmsg noise;
  both are non-destructive and reversible (`dmesg -n 7`, `stty echo`).

## Safety invariants kept
- No partition/BOOT/DTC/module flash; no cert-disable; no `wmctrl/xdotool` hacks;
  no blind kill of launcher/system/shared-host processes. Browser kill was scoped to
  the two `org.nuxel.BrowserNative` app cgroups and receipt-logged.
