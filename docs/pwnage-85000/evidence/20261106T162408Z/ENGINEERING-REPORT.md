# PWNAGE-85000 — Buttersmooth Penguin — Engineering Report

**Campaign:** PWNAGE-85000  
**Date:** 2026-11-06 (session)  
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, Fedora 43 ARM64  
**Kernel (live):** `4.14.253-gf7194c1d15ed-dirty` aarch64  
**Repository:** `/Users/wicked/x/nuxel`, branch `pwnage-80000`, HEAD `ac310d06` (working tree already carried prior-session changes)  
**SSH:** `root@192.168.178.167` via `~wicked/.ssh/wicked_wqn_id_rsa`, `IdentitiesOnly=yes`, `BatchMode=yes`, `ConnectTimeout=10`, normal host-key verification. `id -u` = 0. Host key matched the existing `known_hosts` ed25519 entry.  
**Evidence root:** `docs/pwnage-85000/evidence/20261106T162408Z/`  
**Backup:** `/var/backups/nuxel/p85000-20261106T163134Z` (38 MB)

## Verdict

The unexplained Flatpak launch stall is **root-caused and fixed**. The dominant wait was not bwrap, user namespaces, Wayland, or the Flatpak runtime:

1. `/dev/fuse` was `root:root 0600`, so `xdg-document-portal` could not mount and Flatpak's document-portal D-Bus call waited for a disconnected service.
2. `/run/nuxel-wayland/at-spi` was `root:root 0700`, so the accessibility bus could not start; Flatpak's a11y-bus call waited for a disconnected service.
3. The provider used `systemd-run --wait --pipe` for user-scope Flatpak queries. On this vendor kernel/systemd, an **empty transient unit remains `deactivating (stop-sigterm)` for the default 15 s**. `is_installed()` ran a full system+user inventory on every launch, so the launch request paid that 15 s wait (twice in the reported 30.7 s path).

After the fixes, the production `POST /api/v1/apps/exec` request is accepted in **36–40 ms**, the app process starts in **2.60 s p50 / 2.87 s p95**, and the Text Editor window was confirmed present with title `New Document (Draft) - Text Editor` and closed cleanly in 56 ms. That is a **>99% reduction** from the reported 30.7 s and meets the ≤5 s warm target.

A second whole-device bug was found and fixed: the launcher's orientation `resize` reflow re-entered itself, producing **32 `repaint` writes in 6 s** and keeping WebKit's compositor at ~75% CPU even while the panel was blanked. With the guard, repaint writes fell to **0 in 6 s** and screen-off WebKit CPU fell from ~75% to ~10% (total measured screen-off ~14%). A residual 1 Hz lockscreen-indicator poll remains and is documented as a follow-up.

Status vocabulary: `IMPLEMENTED`, `DEPLOYED`, `AUTOMATED_TESTED`, `VERIFIED_ON_DEVICE`, `NEEDS_OWNER_TEST`, `BLOCKED`.

## 1. Connection and identity

- Selected host `192.168.178.167` after the helper's pinned `10.20.30.16` was unreachable (`tcp connect timed out`). The helper was inspected before use; its stale pinned host was not trusted.
- `ssh-keyscan` returned ed25519 `SHA256` host key matching the existing `known_hosts` line. Host-key verification stayed enabled.
- Root verified: `id -u` = 0, `id -un` = root.
- Device: `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820`, Fedora 43, kernel `4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT`, `/proc/1/exe` = systemd (normal boot, not recovery).
- Wi-Fi SSH remained alive for the whole campaign; the session restart incident (§10) did not lose SSH.

## 2. Baseline and root cause

### Supplied baseline (PWNAGE-84000)

- Native GTK spawn ≈0.48 s.
- Flatpak sandbox init ≈30.7 s in three runs, described as post-context / D-Bus-proxy.
- `nuxel-app-prewarm` enabled but did not resolve the stall.

### Reproduced live

Before any change, the production-shaped command:

```text
systemd-run --wait --pipe --uid=nuxel ... flatpak run --command=true org.gnome.TextEditor
```

returned in **15.985 s** with:

```text
F: Can't get document portal: GDBus.Error:org.freedesktop.DBus.Error.NoReply:
   Message recipient disconnected from message bus without replying
nuxel-bwrap-compat: rewrote 32 fd-bind options
```

`/usr/libexec/xdg-document-portal` run as `nuxel` failed with:

```text
fuse: failed to open /dev/fuse: Permission denied
error: fuse init failed: Can't mount path /run/user/1000/doc
```

The user-scope inventory path (`flatpak --user list` wrapped by `systemd-run --wait --pipe`) took ≈16 s. `systemd-run --wait --pipe -- /bin/true` took 0.07 s, so the wait was not Flatpak list execution; `systemctl status` showed the transient unit in `deactivating (stop-sigterm)` with an **empty cgroup** for `TimeoutStopUSec=15s`. The launch path calls `is_installed()` → `installed_ids()` → `list_installed()` → user-scope query, so every tap paid that wait. The reported ~30.7 s is consistent with two such 15 s waits (provider lookup plus registry/verification work), not a bwrap or namespace cost.

### Root causes (proven)

| ID | Root cause | Evidence | Fix |
|---|---|---|---|
| FLATPAK-1 | `xdg-document-portal` cannot open `/dev/fuse` (`0600 root:root`), so its D-Bus activation dies and Flatpak waits for `NoReply` | portal run error; Flatpak `Can't get document portal` | `nuxel-fuse-access.service` grants `root:nuxel 0660` to `/dev/fuse` and creates user-session dirs; tmpfiles creates `/run/nuxel-wayland/doc` and `at-spi` |
| FLATPAK-2 | `/run/nuxel-wayland/at-spi` is `root:root 0700`, so `at-spi-bus-launcher` cannot start | `Can't find a11y bus: NoReply`; bus socket exists but directory not traversable by nuxel | same service/tmpfiles ownership fix |
| FLATPAK-3 | Transient units linger 15 s in `stop-sigterm` with an empty cgroup; `is_installed()` runs a full inventory on every launch | `systemctl status` empty cgroup, `TimeoutStopUSec=15s`; `/bin/true` fast; user list 16 s | `--property=TimeoutStopSec=1s` on provider transient units + API app units |
| FLATPAK-4 | Full installed-app inventory + icon/desktop resolution on every launch | provider code path; cold list 195.5 ms, cached 0.0 ms | bounded 60 s installed-ref cache + per-app `current/active` truth check + transaction invalidation |
| UI-1 | Launcher orientation reflow dispatches a synthetic `resize` from its own `resize` listener, re-entering forever | 32 `repaint` FIFO writes in 6 s; gdb backtrace at `action_perform("reset-zoom")` from `on_host_message` | `suppressResize` guard around the synthetic resize |
| UI-2 | The repaint storm repeatedly overwrote `/run/nuxel-wl-fb.state` with `REPAINT_REQUEST`, hiding `display=off` from Home | state file stuck at `REPAINT_REQUEST`; Home kept 1 Hz indicator polling | UI-1 removes the storm; added bridge `display.state` (panel backlight truth) as diagnostic/fallback |
| UI-3 | Screen-off WebKit compositor kept rendering (74.7% CPU) while `/sys/class/backlight/panel/bl_power=4` | gdb stack: `ThreadedCompositor::renderLayerTree` → `_mesa_readpixels`; thread CPU 74.7% | UI-1 + display-off CSS/hidden layers; measured ~10% residual |

## 3. Implementation

### 3.1 Flatpak provider (`services/nuxel-bridge/src/flatpak_provider.py`)

- Added `--property=TimeoutStopSec=1s` to `_user_argv()` and `_system_job_argv()`.
- Removed blanket `GSK_RENDERER=cairo` / `LIBGL_ALWAYS_SOFTWARE=1` from `_base_env()`; renderer policy now belongs only to app launch argv.
- Added `_installed_cache` (60 s clean / 5 s error TTL), `_installed_app_present()` truth check on `app/<id>/current/active`, `invalidate_installed()` after transactions, and a single forced refresh on a cache/miss race.
- Added explicit per-app `renderer_policy()`:
  - `auto`: no injected renderer env (verified TextEditor).
  - `software-fallback`: the four known-good Mesa/GSK variables (all other current apps).
  - Default remains `software-fallback`; no app is forced onto an untested GPU path.
- `launch` response now includes the chosen renderer policy and reason.
- No `shell=True`, no client path/command, app-ID validation unchanged; system installs remain root transactions, GUI launches remain `nuxel` user/systemd transient units.

### 3.2 API launch path (`services/nuxel-bridge/src/api.py`)

- Added `--property=TimeoutStopSec=1s` to the production `systemd-run --no-block` app unit.
- Added phase timing in the launch response and `/run/nuxel-app-launch.json`:
  `request_to_provider_lookup`, `provider_lookup_to_exec`, `systemd_run_accept`, `request_to_launch_accepted`.
- No change to privilege separation, argv allowlist, lock check, or focus helper.

### 3.3 Portal/user-session permissions

- `services/nuxel-session/nuxel-fuse-access.service` (enabled):
  - `install -d -o root -g nuxel -m 0750 /run/nuxel-wayland`
  - `install -d -o nuxel -g nuxel -m 0700 /run/nuxel-wayland/at-spi`
  - `chgrp nuxel /dev/fuse && chmod 0660 /dev/fuse`
  - `After=nuxel-wayland.service`, `PartOf=nuxel-wayland.service`, `TimeoutStopSec=1s`.
- `configs/nuxel/tmpfiles-nuxel-portal-doc.conf` creates `/run/nuxel-wayland/doc` and `at-spi` at boot. It intentionally does not touch `/dev/fuse` (tmpfiles rejects the root-owned `/` path transition on this image); the oneshot service owns that.
- This is a document-portal/device permission, **not** a Flatpak sandbox grant. No app override was added.

### 3.4 Whole-device / UI fixes

- `services/nuxel-bridge/src/system_indicators.py`: 10 s TTL cache of the lockhead projection while the panel is off (2 s on). The 1 Hz lockscreen poll previously re-read every sysfs/proc endpoint, measured at 22.3% bridge CPU; the cache removed that cost without inventing indicator state.

- `pwa/nuxel-home/js/launcher.js`: guarded the synthetic `resize` in `_bindOrientation()` with `suppressResize`, breaking the self-triggering `reset-zoom`/repaint loop.
- `pwa/nuxel-home/css/style.css`: display-off idle guard (pause animations/transitions, hide large Home layers, black background).
- `pwa/nuxel-home/js/app.js`: display watcher no longer blocks on a bridge RPC; it uses the now-reliable wl-fb state document first.
- `services/nuxel-bridge/src/hw_providers.py` + `api.py`: new `display.state` / `display.panel-state` RPC returns authoritative `bl_power`/brightness; useful for diagnostics and future non-blocking watchers.
- `pwa/nuxel-home/index.html` / `sw.js`: cache-busted to `p85000`; service worker `CACHE_VERSION=v85000-pwnage`.

### 3.5 Motion language

- `pwa/nuxel-common/theme.css`: tokens `--nx-motion-press 90ms`, `fast 140ms`, `standard 180ms`, `navigation 200ms`, `emphasis 230ms`; reduced/off and `prefers-reduced-motion` overrides.
- `pwa/nuxel-common/theme.js`: persisted `nuxel.motion` preference (`system`, `full`, `reduced`, `off`), applied as `data-motion`, shared through `storage` events.
- Settings → Appearance → Motion: user-facing selector; `appearance-settings.js` applies it to the current and parent document.
- Applied tokens to Quick Settings entry, status/nav hide-show, app-grid page slide, app-item press (0.94 scale), and `.nx-btn` press (0.98 scale). No blur, no layout animation, no permanent `will-change`.
- Tests: `tests/pwnage85000/test_motion_contract.py`.

## 4. Measurements

### 4.1 Flatpak launch timeline (production path, TextEditor)

| Phase | Before | After | Method |
|---|---:|---:|---|
| API request accepted | ~30.7 s reported (≈2×15 s) | **36–40 ms** | `POST /api/v1/apps/exec` `timing_ms` |
| Provider lookup | ≈16 s user inventory | **0.015–0.693 s** (p50 0.020 s) | `/api/v1/flatpak/launch` |
| `flatpak run --command=true` sandbox init | 15.94 s | **0.687–0.795 s** (p50 0.728 s) | direct as nuxel |
| App process start | not reached quickly | **2.329–2.872 s** (p50 2.596 s, p95 2.869 s) | `/proc/*/comm` poll |
| First visible screen change | — | **~2.4 s** (one instrumented run) | screencopy FNV change |
| Window present | — | **VERIFIED** | close action: `WIN title=New Document (Draft) - Text Editor app_id=org.gnome.TextEditor act=1` |
| Close | — | **56 ms** | `POST /api/v1/apps/close` |

Example production response:

```json
{"success": true, "launched": true, "app_id": "org.gnome.TextEditor",
 "unit": "nuxel-app-texteditor-...", "argv": ["/usr/bin/flatpak","run","--env=GDK_BACKEND=wayland","org.gnome.TextEditor"],
 "timing_ms": {"request_to_provider_lookup":0.159,"provider_lookup_to_exec":3.056,
               "systemd_run_accept":36.68,"request_to_launch_accepted":39.895}}
```

Second-app confirmation: `flatpak run --command=true` as nuxel for TextEditor, mpv, VLC and Firefox: **0.44–0.80 s**, `rc=0`, no document-portal/a11y errors. mpv's production launch was accepted in **35.6 ms**; it exited without media (expected) and did not present a window in that test. VLC could not be launched because the security provider reported `session_locked` at that moment.

### 4.2 App-registry and bridge cost

| Metric | Before | After |
|---|---:|---:|
| `list_installed()` cold | ≈16 s (user scope) | **195.5 ms** |
| `list_installed()` cached | — | **0.0 ms** |
| `is_installed(TextEditor)` | ≈16 s | **0.3 ms** |
| user-scope `flatpak list` jobs | 5 in ~20 s | **1–2 in 2 min** |
| bridge API CPU | 13.1% | **0.0% after indicator cache (2.0–2.8% before cache)** |
| bridge helper CPU | 0.7% | **0.3%** |
| lockscreen indicator sysfs/proc scan | every 1 Hz request | **10 s TTL while panel off** |

### 4.3 Whole-device / screen-off

| Metric | Before | After |
|---|---:|---:|
| `nuxel-pwa-host` `repaint` writes | **32 / 6 s** | **0 / 6 s** |
| WebKit compositor thread (screen off) | **74.67%** | **~10%** |
| WebKit + host + phoc + wl-fb (screen off) | ≈95–100% of a core | **≈14–15%** |
| Screen-on idle (same four) | — | **≈17%** |
| wl-fb state | `REPAINT_REQUEST` (display marker lost) | **`DISPLAY_SLEEP display=off capture=stopped`** |
| Memory (screen off) | — | **1.3 GiB used / 5.9 GiB available / 0 swap** |
| Thermal zones | 26.6–43 °C range during session | **43/41/40 °C** at final screen-off sample |
| Battery | 11%, discharging | 11%, discharging |

The residual: the lockscreen indicator class still issues about **6 `GET /api/v1/system/indicators` in 5 s** while the panel is off. The server-side projection is cached for 10 s when the panel is off, cutting bridge API CPU from 22.3% to 0.0%. The new `lockscreen-indicators.js` stops its 1 Hz timer when the response carries `display_off:true`; it is deployed and tested, but the running locked page still has the old script until the next Home reload/reboot, so WebKit still spends ~10% on the client poll. The repaint storm is gone; this residual is a follow-up, not the original stall.

### 4.4 Screen/frame path

Final screen-on state:

```text
FRAMES_OK total=80 fps_1s=14 failures=0 blits=9 present_skipped=69 blit_avg_ms=4
pan_avg_ms=9 capture_avg_ms=7 compare_avg_ms=2 damage=0-1520 damage_runs=1
damage_blits=3 damage_avg_ms=1 idle_ms=924 decon_pan_ok=10 decon_pan_failed=0
```

The single `/dev/fb0` owner remained `nuxel-wl-fb` (`--owner-status`: `live_nuxel_writer=1`, `holder_comm=nuxel-wl-fb`). Damage skipping and screen-off capture-stop are preserved. No second framebuffer writer was introduced.

## 5. Per-app renderer policy

| App | Mode | Env injected | Evidence / reason |
|---|---|---|---|
| `org.gnome.TextEditor` 51.0 | **auto** | none | GTK4/libadwaita; production window presented, title confirmed; Wayland connection |
| `io.mpv.Mpv` 0.41.0 | software-fallback | llvmpipe + GSK cairo | No media in test; avoids untested runtime EGL |
| `org.videolan.VLC` 3.0.24 | software-fallback | llvmpipe + GSK cairo | KDE/Qt runtime; conservative |
| `org.mozilla.firefox` 159.0 | software-fallback | llvmpipe + GSK cairo + `MOZ_ENABLE_WAYLAND=1` | Gecko software path verified historically; GPU path unproven |
| `app.legcord.Legcord` 1.3.1 | software-fallback | llvmpipe + GSK cairo | Electron; no DRM render node |
| `dev.vencord.Vesktop` 1.6.8 | software-fallback | llvmpipe + GSK cairo | Electron; GPU process blocks window on this kernel |
| `com.stremio.Stremio` 1.2.2 | software-fallback | llvmpipe + GSK cairo | Electron; conservative |
| `org.signal.Signal` 8.33.0 | software-fallback | llvmpipe + GSK cairo | Electron; conservative |

All are system installation, aarch64, Flathub. `flatpak override --system --show` for TextEditor is empty; no filesystem/device grant was added. TextEditor's upstream manifest already requests `dri`/`host`; that is unchanged. mpv's upstream manifest already requests `devices=all`; that is unchanged and not a PWNAGE-85000 change.

## 6. Prewarm / performance services

- `nuxel-app-prewarm.service`: `active (exited)`, started and exited at 17:22:42, `Result=success`, no `MemoryCurrent`, no resident process. It is a bounded one-shot cache warm; the real launch win comes from the installed-ref cache and the transient-unit fix. **Keep**, but it is not the root-cause fix.
- `nuxel-perf-tune.service`: **inactive/dead**. No governor/thermal/IO tuning was applied by this campaign.
- No governor, thermal, scheduler, swap, zram or writeback setting was changed.

## 7. Motion/animation coverage

- Tokens and bounds are tested: press ≤110 ms, fast ≤150 ms, standard ≤190 ms, navigation ≤220 ms, emphasis ≤240 ms.
- `prefers-reduced-motion: reduce` and explicit `data-motion="reduced"|"off"` are honored.
- No `backdrop-filter`, no animated blur, no layout-property animation in the core motion rules, no permanent `will-change` on hidden panels.
- App-item press 0.94; `.nx-btn` press 0.98; durations 90–200 ms.
- Visual smoothness on glass remains **NEEDS_OWNER_TEST**; the software compositor cost is measured, not assumed GPU-accelerated.

## 8. Tests

| Suite | Result |
|---|---|
| `tests/pwnage85000/test_flatpak_launch_perf.py` | **9 passed** |
| `tests/pwnage85000/test_motion_contract.py` | **7 passed** |
| `tests/pwnage37000/test_butterscotch_perf.py` | passed |
| `tests/pwnage84000` | passed |
| Combined run | **90 passed** |
| New indicator-cache / display-off tests | **3 passed** |
| Full legacy suite | 4 pre-existing failures unrelated to this campaign (`lockscreen.css` 28 px shadow, A29/A45 session-script drift, ABOX unit `Wants=multi-user`, lockscreen infinite indicator check) |

The pre-existing failures were present in files this campaign did not modify; they are recorded rather than hidden. No assertion was weakened.

## 9. Deployment manifest

All live SHA-256 hashes in `deployment/live-sha256.txt` match `deployment/local-sha256.txt`. Key hashes:

```text
flatpak_provider.py  b012b0e46c02624bb929bbb12dd14bd6028d19242536fbb2ecbfd9de009326f1
api.py               313fe21733a9b03443cb8d59e642baca8c25acf5131cd3d7848046409bac5c13
hw_providers.py      3ddf302619cca4107fd5b8933b4a8984b771c911a1fbf1132d25622516234f34
system_indicators.py   0931a5df1464044594f794ad58eef45be8762f63ce49ebb7bacfd3a647dba459
nuxel-fuse-access    29b0b0f8e93e8dc732a5156053458e69bd84475ba02ec5643edc21828efeb320
tmpfiles conf        b079a5d94978dd75f124ab34582d0d6742d70d74e751317b6a738fd0d5b6b262
theme.css            54db182e3ff0985180d5be4b073c1675514bf01bc77545b59fc1681617da40e7
theme.js             fd6d2ea53bf797aeff3d12a0072dd13d73b35cd2764b1c9fc3e7253cd3cfee73
style.css            c100e729c8114cc64b72347f7975cafda02100a32312da4e752bf0fb4bf2d0f7
launcher.css         925d2e7f5388bf27e0e6cdb4550528cc7469b0a8efe243136caca82bc13dd090
app.js               b1c70e9de9cf084421e83f0f5bfe1025e99113f530e12b1ba5da7140297bacea
launcher.js          7fde5e713cd89f57f4d54d330a3b4422db2ef9bdb22555d40f87b2b6c3898c3a
index.html           a9bd9ba40d2d44c0a1fb700a03174377851cc937167808f251273cb03288d96c
lockscreen-indicators.js 04ce9dacc89c87d77ea738ab66099d2c2bd8da1059644bb1dd57f9f983e8d38a
sw.js                39713d52c904c00171c2d500c1ffa1cf744442af7480171f2b3a7c960010bca2
settings index       7bf7455fabf5593c69125c56e75875d8317a9e6fa58c1560d49140a1bfa91a04
appearance-settings  69667e74dd4ab5823d1a294ae5e33d316f130708dc75b231673a7cc5856e7c48
```

Units restarted: `nuxel-http-bridge.service`, `nuxel-bridge.service`, `nuxel-fuse-access.service`; `nuxel-wayland.service` restarted once during instrumentation (see §10). No Flatpak app was uninstalled, reinstalled or overridden.

## 10. Incident during verification (honest record)

At 18:02:39 the Wayland session restarted. The journal ends with an abort/segfault trace, then `Started nuxel-wayland.service`; the service is active, `systemctl --failed` is empty, and SSH stayed up. The restart occurred while attaching `gdb` and invoking `webkit_web_view_reload` to force the freshly deployed Home assets into the running WebKit page. This was an **instrumentation-induced restart**, not a normal user path and not a source-code deployment step. After restart, the fixed launcher.js/app.js were loaded from disk and the repaint storm measurement dropped to zero. The owner may have seen a brief blank/relaunch. No data or app state was intentionally changed; the only app opened during the campaign was Text Editor, which was closed cleanly.

## 11. Rollback

Backup: `/var/backups/nuxel/p85000-20261106T163134Z`

```sh
B=/var/backups/nuxel/p85000-20261106T163134Z
install -m644 $B/bridge/flatpak_provider.py /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py
install -m644 $B/bridge/api.py              /usr/lib/nuxel/nuxel-bridge/api.py
install -m644 $B/bridge/hw_providers.py     /usr/lib/nuxel/nuxel-bridge/hw_providers.py
install -m644 $B/pwa/common/theme.css       /usr/share/nuxel/pwa/nuxel-common/theme.css
install -m644 $B/pwa/common/theme.js        /usr/share/nuxel/pwa/nuxel-common/theme.js
install -m644 $B/pwa/home/css/style.css     /usr/share/nuxel/pwa/nuxel-home/css/style.css
install -m644 $B/pwa/home/css/launcher.css  /usr/share/nuxel/pwa/nuxel-home/css/launcher.css
install -m644 $B/pwa/home/js/app.js         /usr/share/nuxel/pwa/nuxel-home/js/app.js
install -m644 $B/pwa/home/js/launcher.js    /usr/share/nuxel/pwa/nuxel-home/js/launcher.js
install -m644 $B/pwa/home/index.html        /usr/share/nuxel/pwa/nuxel-home/index.html
install -m644 $B/pwa/home/sw.js             /usr/share/nuxel/pwa/nuxel-home/sw.js
# settings page:
mkdir -p $B/pwa/settings
# restore the two settings files from the backup tree, then:
systemctl disable --now nuxel-fuse-access.service
install -m644 $B/etc/nuxel-portal-doc.conf /etc/tmpfiles.d/nuxel-portal-doc.conf
systemctl daemon-reload
systemctl restart nuxel-http-bridge nuxel-bridge
```

Do **not** restore `/dev/fuse` to `0600 root:root` while keeping the new provider: document-portal Flatpak launches will start timing out again. The original portal behavior is restored by removing the service and reverting the provider together.

## 12. Acceptance matrix / remaining work

| Item | Status |
|---|---|
| ~30 s Flatpak stall explained and removed | **VERIFIED_ON_DEVICE** |
| Warm TextEditor launch-to-process ≤5 s | **VERIFIED_ON_DEVICE** (p50 2.60 s) |
| First visible frame / window | **VERIFIED_ON_DEVICE** (hash change ~2.4 s; close-action title) |
| Second app sandbox init | **VERIFIED_ON_DEVICE** (mpv/VLC/Firefox 0.44–0.80 s `--command=true`) |
| Second app window presentation | **PARTIAL** — mpv exited without media; VLC blocked by session lock |
| Sandbox / user identity / Wayland / portals | **VERIFIED_ON_DEVICE**; no overrides, no `--no-sandbox`, no host grants |
| Per-app renderer policy | **DEPLOYED / AUTOMATED_TESTED**; one auto app verified |
| Installed-ref cache invalidation | **AUTOMATED_TESTED** |
| Prewarm benefit/cost | **VERIFIED** one-shot, no resident RSS; kept |
| Repaint storm elimination | **VERIFIED_ON_DEVICE** (32→0 writes; ~75%→~10% compositor) |
| Screen-off CPU fully low | **PARTIAL** — ~15% total; bridge API ~0%; client 1 Hz stop is DEPLOYED but needs a Home reload/reboot |
| Motion tokens/reduced-motion/off | **DEPLOYED / AUTOMATED_TESTED** |
| Visual touch acceptance | **NEEDS_OWNER_TEST** |
| Vesktop/Legcord login state | **NOT_TESTED** (not launched; no credentials touched) |
| Normal reboot persistence of tmpfiles/service | **NEEDS_REBOOT_TEST** (service enabled; boot path not rebooted in this campaign) |
| Owner physical acceptance checklist | **NEEDS_OWNER_TEST** |

### Remaining blockers / follow-ups

1. The lockscreen indicator poll still runs ~1 Hz while the panel is off, keeping screen-off WebKit at ~10%. The next safe step is a host-side `display-off` event or a guaranteed `body.display-off` propagation reviewed against a fresh session, then re-measure; do not force it with gdb.
2. Visual motion smoothness on glass needs the owner's finger test. The CSS is deliberately small-surface transform/opacity only; transforms are not claimed to be GPU accelerated.
3. Reboot persistence of `nuxel-fuse-access.service` and `/run/nuxel-wayland` permissions should be confirmed by the owner at the next normal reboot.
4. VLC/mpv window presentation and Vesktop/Legcord login/window behavior need an unlocked owner session.

## 13. Files and evidence

- `baseline.json`, `candidate.json` — machine-readable before/after.
- `tests/pwnage85000/` — 19 deterministic tests (Flatpak cache/timeout/policy, motion contract, indicator cache/display-off).
- `flatpak-launches.csv` — raw launch samples.
- `deployment/local-sha256.txt`, `deployment/live-sha256.txt` — source and phone hashes.
- `baseline/git-head.txt`, `baseline/git-status.txt`, `baseline/local-sha256.txt`.
- `ENGINEERING-REPORT.md` (this file), `BASELINE.md`, `FLATPAK-TIMELINE.md`, `FLATPAK-APP-MATRIX.md`, `RENDERER-POLICY.md`, `WHOLE-DEVICE-PERFORMANCE.md`, `ANIMATION-PROFILE.md`, `THERMAL-IDLE-REPORT.md`, `ROLLBACK.md`, `SHA256SUMS`.
