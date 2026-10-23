# NUXEL A53 — Rollback & Recovery

## Deployed change set (all userspace, reversible, verified SHA-256)

| Deployed path | New SHA-256 | Pre-deploy SHA-256 |
|---|---|---|
| `/usr/libexec/nuxel/nuxel_orientation/policy.py` | `d84b9052…` | `9357f96b…` |
| `/etc/nuxel/orientation/orientation.json` | `006ff7f8…` | `b1158485…` |
| `/usr/share/nuxel/nuxel-home/js/qs.js` | `a4587e5f…` | `353c9de0…` |
| `/usr/share/nuxel/pwa/nuxel-apps/settings/settings.js` | `d65dea16…` | `e4ff9fb9…` |
| `/usr/share/nuxel/nuxel-home/sw.js` | `1536a8d0…` | `74fcf590…` |
| `/usr/libexec/nuxel/nuxel-v4l2-capture-test.py` | `e294a500…` | (new) |
| `/usr/libexec/nuxel/nuxel-v4l2-probe.py` | `867b0ef2…` | (new) |

## On-device rollback copies (already captured before deploy)

```
/root/nuxel-a53-rollback/_usr_libexec_nuxel_nuxel_orientation_policy.py.a53-rollback
/root/nuxel-a53-rollback/_etc_nuxel_orientation_orientation.json.a53-rollback
/root/nuxel-a53-rollback/_usr_share_nuxel_nuxel-home_js_qs.js.a53-rollback
/root/nuxel-a53-rollback/_usr_share_nuxel_pwa_nuxel-apps_settings_settings.js.a53-rollback
/root/nuxel-a53-rollback/_usr_share_nuxel_nuxel-home_sw.js.a53-rollback
```

## Rollback procedure (via the same USB Live Console)

```sh
cp -a /root/nuxel-a53-rollback/_usr_libexec_nuxel_nuxel_orientation_policy.py.a53-rollback \
      /usr/libexec/nuxel/nuxel_orientation/policy.py
cp -a /root/nuxel-a53-rollback/_etc_nuxel_orientation_orientation.json.a53-rollback \
      /etc/nuxel/orientation/orientation.json
cp -a /root/nuxel-a53-rollback/_usr_share_nuxel_nuxel-home_js_qs.js.a53-rollback \
      /usr/share/nuxel/nuxel-home/js/qs.js
cp -a /root/nuxel-a53-rollback/_usr_share_nuxel_pwa_nuxel-apps_settings_settings.js.a53-rollback \
      /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js
cp -a /root/nuxel-a53-rollback/_usr_share_nuxel_nuxel-home_sw.js.a53-rollback \
      /usr/share/nuxel/nuxel-home/sw.js
rm -f /usr/libexec/nuxel/nuxel-v4l2-capture-test.py /usr/libexec/nuxel/nuxel-v4l2-probe.py
```

No service restart is required: `nuxel-orientationd` is spawned fresh per call by the bridge, and
the static JS is re-fetched by the service worker after its cache version reverts. To return the
selected mode to the safe default, delete `/var/lib/nuxel/orientation/state.json` (daemon falls
back to `portrait`).

Repository rollback: `git revert <a53-commit>` (host only).

## Recovery invariants preserved

- No partition/kernel/boot/recovery/firmware/DTB/DTBO/VBMETA/EFS writes. No flashing.
- The USB Live Console (pre-systemd, initramfs-owned) was never detached or reconfigured.
- No `/dev/fb0` open from the host (the framebuffer-close danger is avoided).
- Home, lockscreen, Stevia OSK, navdock, touch-arm, Wi-Fi profiles, `media_store.py` and the A52
  Camera/Photos PWAs were not modified.
- No reboot was performed.
