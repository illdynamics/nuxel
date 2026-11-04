# PWNAGE-62000 Patch Manifest

**Deploy package root:** `/x/nuxel`  
**Target:** S10+ aarch64 Fedora 43, WiFi SSH `root@10.20.30.16`  
**Backup:** `/var/backups/nuxel/p62000-20261103T080758Z`  
**Checksum strategy:** SHA-256 for every source and installed target; backup manifest
excludes itself (`! -name 'SHA256SUMS*'`) and is verified with
`sha256sum -c SHA256SUMS --quiet`.

## Source → target mapping

| Source | Target | Mode | Source SHA-256 | Installed SHA-256 |
|---|---|---:|---|---|
| `tools/s10plus/a45/nuxel-navdock.c` (built) | `/usr/lib/nuxel/nuxel-navdock` | 0755 | source `427dce24…0edb` | binary `a0d1d66c…82948` |
| `tools/s10plus/a45/nuxel-statusbar.c` (built) | `/usr/lib/nuxel/nuxel-statusbar` | 0755 | source `25216399…e202` | binary `b9433451…0535` |
| `tools/s10plus/a59/nuxel-foreign-toplevel.c` (built) | `/usr/lib/nuxel/nuxel-foreign-toplevel` | 0755 | source `9e39d9fe…1cc8` | binary `4b7fb38c…c03b` |
| `tools/s10plus/a45/nuxel-pwa-host.c` (built) | `/usr/lib/nuxel/nuxel-pwa-host` | 0755 | source `61fa1530…7efb` | binary `17256b90…1af3` |
| `tools/s10plus/a45/nuxel-button-manager.c` (built) | `/usr/lib/nuxel/nuxel-button-manager` | 0755 | built on target | built on target |
| `tools/s10plus/a45/nuxel-shell-chrome.sh` | `/usr/lib/nuxel/nuxel-shell-chrome.sh` | 0755 | `644b564a…1360` | `644b564a…1360` |
| `tools/s10plus/a45/nuxel-security-lock-rpc` | `/usr/lib/nuxel/nuxel-security-lock-rpc` | 0755 | staged/deployed | deployed |
| `tools/s10plus/a45/nuxel-session.sh` | `/usr/lib/nuxel/nuxel-session.sh` | 0755 | staged/deployed | deployed |
| `services/nuxel-preload-cinema/nuxel-preload-cinema` | `/usr/lib/nuxel/nuxel-preload-cinema` | 0755 | `31393720…7508` | `31393720…7508` |
| same | `/usr/lib/nuxel/stage36000/nuxel-preload-cinema/nuxel-preload-cinema` | 0755 | `31393720…7508` | `31393720…7508` |
| `services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh` | `/usr/lib/nuxel/stage36000/apply-pwnage36000.sh` | 0755 | `aa5463d2…2e4a` | `aa5463d2…2e4a` |
| `services/nuxel-s10/bin/nuxel-wayland-stop.sh` | `/usr/lib/nuxel/nuxel-wayland-stop.sh` | 0755 | `ad223d06…c1e6` | `ad223d06…c1e6` |
| `services/nuxel-s10/bin/nuxel-audio-stop.sh` | `/usr/lib/nuxel/nuxel-audio-stop.sh` | 0755 | `24e33573…ee20` | `24e33573…ee20` |
| `services/nuxel-bridge/src/system_indicators.py` | `/usr/lib/nuxel/nuxel-bridge/system_indicators.py` | 0644 | `ae3ecb06…c1b6` | `ae3ecb06…c1b6` |
| `configs/nuxel/boot/preload-cinema.json` | `/etc/nuxel/boot/preload-cinema.json` | 0644 | staged/deployed | deployed |
| `services/nuxel-s10/systemd/nuxel-wayland.service.d/30-fast-stop.conf` | `/etc/systemd/system/nuxel-wayland.service.d/30-fast-stop.conf` | 0644 | staged/deployed | deployed |
| `services/nuxel-s10/systemd/nuxel-wayland.service.d/40-bounded-stop.conf` | `/etc/systemd/system/nuxel-wayland.service.d/40-bounded-stop.conf` | 0644 | staged/deployed | deployed |
| `services/nuxel-s10/systemd/nuxel-wl-fb.service.d/25-reboot-hold.conf` | `/etc/systemd/system/nuxel-wl-fb.service.d/25-reboot-hold.conf` | 0644 | staged/deployed | deployed |
| `services/nuxel-s10/systemd/nuxel-audio-session.service.d/10-stop-bound.conf` | `/etc/systemd/system/nuxel-audio-session.service.d/10-stop-bound.conf` | 0644 | staged/deployed | deployed |
| `pwa/nuxel-home/index.html` | `/usr/share/nuxel/{pwa/,}nuxel-home/index.html` | 0644 | deployed, `app.js?v=p62000` | deployed |
| `pwa/nuxel-home/sw.js` | `/usr/share/nuxel/{pwa/,}nuxel-home/sw.js` | 0644 | cache `v62000-pw62000` | deployed |
| `pwa/nuxel-home/js/app.js` | `/usr/share/nuxel/{pwa/,}nuxel-home/js/app.js` | 0644 | `32724593…e84e` | `32724593…e84e` |
| `pwa/nuxel-home/js/gestures.js` | `/usr/share/nuxel/{pwa/,}nuxel-home/js/gestures.js` | 0644 | `addb3071…43a5` | `addb3071…43a5` |
| `pwa/nuxel-home/js/navigation.js` | `/usr/share/nuxel/{pwa/,}nuxel-home/js/navigation.js` | 0644 | deployed | deployed |
| `pwa/nuxel-home/js/launcher.js` | `/usr/share/nuxel/{pwa/,}nuxel-home/js/launcher.js` | 0644 | deployed | deployed |
| `pwa/nuxel-home/js/apps.js` | `/usr/share/nuxel/{pwa/,}nuxel-home/js/apps.js` | 0644 | deployed | deployed |
| `pwa/nuxel-home/js/lockscreen-indicators.js` | `/usr/share/nuxel/{pwa/,}nuxel-home/js/lockscreen-indicators.js` | 0644 | deployed | deployed |
| `pwa/nuxel-home/css/{launcher,style,status-bar}.css` | `/usr/share/nuxel/{pwa/,}nuxel-home/css/` | 0644 | deployed | deployed |

Full exact hashes: `evidence/pwnage62000/source-sha256.txt` and
`evidence/pwnage62000/installed-sha256.txt` (truncated hashes in the table above are
only for readability).

## Service reload / restart

```sh
systemctl daemon-reload
systemctl restart nuxel-http-bridge.service
systemctl restart nuxel-button-manager.service
systemctl restart nuxel-wayland.service
systemctl restart nuxel-wl-fb.service
```

`nuxel-audio-session.service` is not restarted by deploy (avoid interrupting audio);
its 2 s helper/drop-in is picked up on the next normal start/stop.

## Health gate

```sh
systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-http-bridge \
  nuxel-button-manager nuxel-bridge
systemctl show nuxel-wayland.service -p TimeoutStopUSec -p ExecStop --value   # 2s + helper
systemctl show nuxel-wl-fb.service  -p TimeoutStopUSec -p ExecStop --value   # 5s + hold
systemctl show nuxel-audio-session.service -p TimeoutStopUSec -p ExecStop --value # 2s + helper
grep FRAMES_OK /run/nuxel-wl-fb.state
test -f /run/nuxel-navdock.json
test -f /run/nuxel-statusbar.state
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
  /usr/lib/nuxel/nuxel-foreign-toplevel list | grep app_id=nuxel-pwa-host
```

Indicator gate (inside bridge):

```python
w = get_indicators()["console_transports"]["wlan"]
assert not (w["available"] and w["sessions"] == 0 and w["active"])
assert w["active"] == (w["sessions"] > 0)
```

## Rollback manifest

The exact restore list is encoded in
`tools/pwnage62000/rollback-pwnage62000.sh`; it mirrors the deploy targets and
restores only files present in the timestamped backup. The backup is verified before
reboot with `sha256sum -c SHA256SUMS --quiet`.

## Forbidden operations (not performed)

No kernel, DTB, BOOT, modem, partition, recovery, initramfs, Flatpak-sandbox, SSH
policy, `authorized_keys`, host-key or forced-reboot operation was performed.
`nuxel-wl-fb` remains the only `/dev/fb0` writer.
