# NUXEL A74 / 23000 — Rollback

Rollback restores only the three changed live files, then the two services.

```sh
# as root on the phone (USB console or SSH over Wi-Fi)
cp -a /var/lib/nuxel/a74-backup/bridge/system_indicators.py.pre-a74 \
      /usr/lib/nuxel/nuxel-bridge/system_indicators.py
cp -a /var/lib/nuxel/a74-backup/bin/nuxel-pwa-host.pre-a74 \
      /usr/lib/nuxel/nuxel-pwa-host
chmod 0755 /usr/lib/nuxel/nuxel-pwa-host
# a73-logger.sh: either restore the original sampler (NOT recommended) or leave
# the A74 stub; it is not started automatically.
systemctl restart nuxel-http-bridge.service nuxel-wayland.service
systemctl is-active nuxel-http-bridge.service nuxel-wayland.service
```

Verify with:
```sh
sha256sum /usr/lib/nuxel/nuxel-bridge/system_indicators.py \
          /usr/lib/nuxel/nuxel-pwa-host
# expect 93b2d3d0… and cff15529…
```

**Safety note:** the pre-A74 files re-introduce the unsafe DWC3 debugfs
`link_state` read that caused the detach hard-lockup. Roll back only if the A74
fix were somehow found faulty; the physical detach matrix is the authoritative
test (see TEST-MATRIX.md).

## Alternate recovery
SSH over Wi-Fi (`root@192.168.178.167`) was established this session and is the
recovery channel if the USB console is unavailable.
