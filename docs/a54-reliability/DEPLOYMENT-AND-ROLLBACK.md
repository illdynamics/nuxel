# A54 Deployment & Rollback

## Deployed files (all SHA-256 verified on-device)
Targets and (local → remote):
- `services/nuxel-bridge/src/bridge.py` → `/usr/lib/nuxel/nuxel-bridge/bridge.py`
- `services/nuxel-bridge/src/media_store.py` → `/usr/lib/nuxel/nuxel-bridge/media_store.py`
- `services/nuxel-bridge/src/api.py` → `/usr/lib/nuxel/nuxel-bridge/api.py`
- `services/nuxel-orientation/nuxel_orientation/policy.py` → `/usr/libexec/nuxel/nuxel_orientation/policy.py`
- `pwa/nuxel-home/index.html`, `sw.js`, `manifest.json`, `css/status-bar.css`,
  `js/status-bar.js`, `js/qs.js` → `/usr/share/nuxel/pwa/nuxel-home/…`
- `pwa/nuxel-apps/settings/settings.js`, `settings-model.js`, `wifi-settings.js`
  → `/usr/share/nuxel/pwa/nuxel-apps/settings/…`
- `shell/nuxel-camera-native/nuxel_camera_native.py` → `/usr/lib/nuxel/nuxel-camera-native/…`
- desktop entry → `/usr/share/nuxel/applications/org.nuxel.CameraNative.desktop`

Transfer: gzip → base64 chunked over USB CDC-ACM (`nuxel_live.push_bytes`,
128-char frames), on-device `gunzip` + SHA-256 readback for every file.

## Service restarts (userspace only)
`nuxel-bridge`, `nuxel-http-bridge`, `nuxel-wayland` (launcher reload). No
partition/kernel/bootloader writes; USB console (`nuxel-console`) untouched.

## Rollback
Every overwritten file has a `.nuxel-a54-rollback` backup captured on first
deploy. Restore any single file:
```sh
cp -a <path>.nuxel-a54-rollback <path>
systemctl restart nuxel-bridge nuxel-http-bridge
```
Orientation config re-key is reversible:
```sh
sed -i 's/-portrait/_portrait/g; s/-landscape/_landscape/g' \
  /etc/nuxel/orientation/orientation.json
```

## Snapshot follow-on (when a package manager is available)
1. Install `dnf5` (or `dnf`) from the Fedora 43 aarch64 repo with its RPM set.
2. `dnf5 --assumeno install snapshot` to preview, then remove `--assumeno`.
3. Verify `rpm -q snapshot`, inspect `rpm -ql snapshot | grep -E '\.desktop$|/bin/'`.
4. Launch as the Nuxel graphical-session user with `XDG_RUNTIME_DIR=/run/nuxel-wayland`
   and the session bus, not from the root serial shell.

## Package-transaction safety
Refused to run any un-resolved `rpm` install or to loosen bridge sandboxing. The
bridge keeps `DevicePolicy=closed`; camera enumeration is provided by a root
snapshot file rather than by weakening the unit.
