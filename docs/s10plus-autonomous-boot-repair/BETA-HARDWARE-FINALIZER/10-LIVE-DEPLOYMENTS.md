# 10 — LIVE DEPLOYMENTS

Every change in this cycle was deployed over the live USB console with a verified
transport, a backup of the previous file, and a hash check on the target.  No BOOT,
USERDATA, DTBO, PIT or bootloader write was made; TWRP was never needed.

## 1. Transport (measured, then fixed twice)

| Finding | Consequence |
|---|---|
| The link carries ~960 B/s at 9600 baud and the target’s N_TTY input buffer is 4 KiB | one bulk write loses everything past the buffer: 14,688 bytes written as 48 lines in a single `write()` landed as **1,769 bytes** |
| Framed commands longer than ~512 characters are dropped by the far-end shell | a 2,792-character command never executed |
| The far end interleaves a live `/dev/kmsg` mirror with shell output | any framing must be marker/hash based, not timing based |

Final tool: `tools/s10plus/a32/nuxel-push-hybrid.py` — the payload travels as
individually padded 512-character base64 lines on the raw port (**throughput**: 99,496
base64 chars in 122 s), while **every assertion** (bytes landed, decode, hash, install,
re-hash) goes through `nuxel-live.sh`’s framed, SHA-verified channel (**trustworthiness**).
A block that does not land exactly is replayed from the last verified offset.

## 2. What was deployed (each with a `.prev-a32` backup)

| Path | Purpose |
|---|---|
| `/usr/lib/nuxel/nuxel-wl-fb` | colour conversion, animation-length gate, screen on/off FIFO |
| `/usr/lib/nuxel/nuxel-pwa-host` | host API (settings/actions/terminal), PTY terminal, cache purge, JS-error relay |
| `/usr/lib/nuxel/nuxel-button-manager` | power/volume/Bixby manager (new) |
| `/usr/bin/nuxelctl` | console control of the same configuration (new) |
| `/etc/systemd/system/nuxel-button-manager.service` | the manager unit (new, enabled) |
| `/usr/share/nuxel/nuxel-home/{index.html,js/*.js}` | launcher: host bridge, safe zones, OSD, status bar, registry, action handling |
| `/usr/share/nuxel/pwa/nuxel-apps/settings/*` | Nuxel Settings PWA (Display/Sound/Buttons/Developer) |
| `/usr/share/nuxel/pwa/nuxel-apps/terminal/*` | Nuxel Terminal PWA (real PTY) |
| `/etc/nuxel/display/statusbar-safezones.json`, `/etc/nuxel/input/buttons.json` | configuration (created only when absent: `KEEP existing …` on every later deploy) |

Install is atomic per file (`cp` to `.new-a32` → `mv`), mode-preserving, and re-hashes
source vs destination; on a mismatch it restores the `.prev-a32` copy and counts a
failure.  Final run: `FAILURES=0`.

## 3. Bugs found by deploying (and fixed)

1. **Installer variable clobbering** — the phone-side installer used `$a`/`$b` for hashes
   while the caller looped over `$a` for the app name, so `settings`/`terminal` assets
   were written to a directory named after a SHA-256 sum.  All installer locals are now
   prefixed (`_rel`, `_src`, `_dst`, `_sa`, `_sb`) and the run reports `FAILURES=0`.
2. **WebKit data-manager cache purge crashed the host** (`SIGSEGV`,
   `coredumpctl` confirms 2.2 MB cores) when `webkit_website_data_manager_clear()` was
   called during startup.  Replaced by a filesystem purge of exactly three persisted
   subtrees (`serviceworkers`, `CacheStorage`, `WebKitCache`) performed **before** WebKit
   initialises; `localStorage` is preserved.  Verified: the launcher now fetches all
   assets from the server again (`/run/nuxel-web.log`).
3. **No `tar` on the handset** — extraction uses `python3 -c "import tarfile; …"`.
4. **Stale service-worker cache** — see `03-UTM-LAUNCHER-PARITY.md` §1.

## 4. Service restarts used

```
systemctl daemon-reload
systemctl stop nuxel-wl-fb          # stop the fb owner first
systemctl restart nuxel-wayland     # phoc + session script + nuxel-pwa-host
systemctl start  nuxel-wl-fb        # re-take the panel after hand-off
systemctl enable --now nuxel-button-manager
```

Only affected units were restarted; the panel briefly blanks while no owner exists
(expected and documented), and no reboot at all is required for launcher/CSS/JS/
wallpaper/button-mapping changes.

## 5. Rollback

* every replaced file has `<path>.prev-a32`;
* `nuxelctl buttons|statusbar` only ever edit JSON, so a bad mapping is one command away
  from being corrected, and the manager reloads within 1 s;
* the display bridge's `screen-off` is reversible by `screen-on` from the same FIFO, and
  brightness is saved before it is zeroed;
* if `nuxel-wayland` ever fails to become ready, `nuxel-fallback.service` takes the panel
  (single owner) and the console stays usable.
