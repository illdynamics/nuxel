# PWNAGE-88000 Engineering Report — Operation Zero-Flash, Heard Doom, Real Services & Living Spoof

- **UTC timestamp:** 2026-11-07T12:10:39Z
- **Target:** Nuxel on Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820, ARM64)
- **Transport:** Wi-Fi SSH, root, key `~/.ssh/wicked_wqn_id_rsa` (never printed)
- **Live host:** `root@192.168.178.167` (helper-pinned 10.20.30.16 was unreachable and NOT used)
- **Kernel (live):** `4.14.253-gf7194c1d15ed-dirty` aarch64; Fedora Linux 43
- **Version:** bumped `v0.7.7-beta` → `v0.7.8-beta`

## 1. Connection + baseline
- `id -u` = 0. Host key verified against the pinned entry (no `StrictHostKeyChecking=no`, no known_hosts deletion).
- Baseline captured: `baseline/unit-files.txt`, `baseline/systemd-analyze.txt`, `baseline/waydroid-gate.txt`, `baseline/runtime-state.txt`.
- Boot before: `Startup finished in 3.586s (kernel) + 46.973s (userspace) = 50.559s`; `multi-user.target @45.877s`. Critical chain: `nuxel-soundd.service @4.237s +41.633s` → `nuxel-clockd.service @45.877s`.
- No failed units at baseline or after deployment.

## 2. Workstream status (source + live evidence)

### A — Zero-flash wake (`tools/s10plus/a67/nuxel-wl-fb.c`, Home CSS/JS)
- Completed the half-written two-phase wake: `display_set(1)` no longer unblanks; it sets `wake_pending`. The ownership loop now unblanks (`bl_power_write(0)` + `panel_assert`) only after a fresh post-wake frame commit, with an 8-try bounded fallback. (`DISPLAY_WAKE_COMMIT` / `DISPLAY_WAKE_FALLBACK` receipts.)
- Removed `body.display-off #lockscreen/.lockscreen-handle { visibility:hidden }` so the lockscreen stays rendered while the panel is dark. Only the desktop layers are detached.
- Wake re-asserts the locked presentation + forces a compositor redraw on `nuxel:display-on`.
- **Physical proof:** deferred to the release build/reboot; the C binary is rebuilt by CI. The Home CSS/JS changes are deployed to the phone and syntax-verified.

### B — Doom audio + top controls + 3x sensitivity
- Removed the unconditional `-nomusic`; `-nosound -nomusic` only when sound is off.
- Added trusted-gesture audio priming (`primeAudio`) on Play and a truthful `audio-note`.
- Added persisted `sensitivity` (default `3`), a real `aimDuty(magnitude*sens)` multiplier, and a `−/+` settings control.
- Moved Use/Map top-left and −/+/Menu top-right; Menu now sends the engine Escape menu (not only the app overlay); desktop Escape shortcut ignores synthetic events.
- Tests: `pwa/nuxel-apps/doom/tests/test-doom.js` → **54 passed, 0 failed** (new PWNAGE-88000 section).

### C — Waydroid
- **BLOCKED_KERNEL.** Live gate: `/dev/binder`+`/dev/hwbinder`+`/dev/vndbinder` and `/dev/ashmem` present; `CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_ASHMEM=y`, `CONFIG_USER_NS=y`, user namespaces work (`unshare -Ur true` ok).
- Missing prerequisites: **`CONFIG_PSI` is absent**, **`CONFIG_ANDROID_BINDERFS` is absent**, and cgroup v2 exposes only `memory pids` controllers (no `cpu`/`freezer` for a real LXC/Waydroid container). No Waydroid package was faked or half-installed. A kernel change is a separate, explicitly approved gate.

### D — Triple buttons / top bar
- Confirmed the native swipe directions and opaque full-dock mat were already correct in the working tree.
- Enlarged the nav/top strip **input band** to 40 logical px (`NAV_STRIP_INPUT_HEIGHT` / `BAR_STRIP_INPUT_HEIGHT`) while keeping the thin visual handle.
- Consolidated to one bottom stripe: the Home CSS pill now only renders on non-native runs (`html:not(.native-nav-present)`).
- C binaries rebuild in CI; Home CSS deployed.

### E/F/G — Timer / alarm penguins + clock authority
- Fixed `_normalise_timer` zero-coercion bug (the real "set 0:30 but daemon shows 5:00" root cause).
- Added authoritative `set-timer` verb to `nuxel-clockd` + bridge alias + client `Set`/presets.
- Added `fmtTimer` (MM:SS / H:MM:SS, never `0:00`), a 250 ms local deadline paint loop, and exposed `fmtTimer`.
- Centered the timer penguin over the wallpaper penguin and the alarm penguin below it/above the lockhead via measured CSS anchors (`--lockscreen-timer-center-y` / `--lockscreen-alarm-center-y`); reordered lanes (timer above alarm).
- Heavy shake now animates the inner image (no conflict with lane/drag transforms).
- Tests: `tests/pwnage84000/test_clock_scheduler.py` → **10 passed** (3 new: set-timer persistence, zero-preservation, disabled-alarm projection).

### H — Foreground visibility truth
- Added `_foregroundSurfaceVisible()` / `isForegroundVisible()` (iframe hidden/zero-size/display:none/document.hidden) and a 1–2 s watchdog that backgrounds an invisible ACTIVE PWA.
- `gestures.js` permits the drawer whenever no visible foreground surface exists.
- `back()` now counts invisible-handled strikes and recovers after two.

### I — Services section
- Shipped `configs/nuxel/services/service-policy.json` (allowlist + essential set).
- Bridge `services` namespace: `list`, `unlock`/`lock` (server-side), allowlisted `start/stop/restart/reload/enable/disable`, protected essential units, and confirmed `daemon-reload`/`daemon-reexec`.
- Settings UI: new Services tab + `services-settings.js`.
- Live smoke: endpoint reachable; non-owner call returns `capability_denied` (fails closed).

### J — PenguInterface spoofing
- New aarch64 `spoof/libnuxel-spoof.c` (recursion-safe, correct varargs, `uname`/`fopen`/`fopen64`/`open`/`open64`/`openat`/`openat64`).
- **Live hardware proof:** built on-device with gcc; `LD_PRELOAD=/usr/lib/nuxel/spoof/libnuxel-spoof.so uname -a` → `Linux spoofed-node 9.9.9-spoof #1 aarch64`; `cat /etc/os-release` → spoofed; real `uname -a` unchanged. Test state cleared afterwards.
- Bridge `spoof` namespace (status/set/reset + real-identity verification) and PenguInterface spoof panel (current UA, UA editor, os-release, uname, targets, apply/reset).

### K — Dark GTK/Flatpak + browsers + DevMgmt
- Injected `GTK_APPLICATION_PREFER_DARK_THEME=1` + `GTK_THEME=Adwaita:dark` for native and Flatpak GTK launches.
- Nuxel Browser: `win.maximize()` + mobile WebKit UA.
- DevMgmt tabs: `flex-shrink:0`, `scroll-padding`, active-tab `scrollIntoView({inline:'center'})`, hidden scrollbar retained.

### L — Software post-install + M — desktop/widget Move
- Launcher action row now `Resize / Remove / Move / Desktop N / Done` (replaced Home settings); Move arms an explicit drag; Desktop N opens a picker and moves to a free cell via `desktopLayout.move`.
- Widgets gained a `Desktop N` control (same picker); Move remains the long-press drag.
- Software post-install: `flatpak_provider` detection metadata is already cached; a generic launch profile is applied in `launch_argv`. Full post-install hook is noted as follow-up.

### N — Performance/boot
- Decoupled `nuxel-clockd.service` from `nuxel-soundd.service` (`After` removed, `Wants` retained): clockd only needs soundd at fire time, so it no longer serializes behind soundd's ~41 s boot ExecStartPre. Deployed + `daemon-reload` on the phone.
- Documented the remaining audio boot serialization (`nuxel-soundd`/`nuxel-mic-route`/`nuxel-abox-firmware-reload`) as the next boot target.

### O — Preloading video
- Last-boot receipt (`baseline/runtime-state.txt`) already shows `verdict=PLAYED`, `duration_s=6.016`, `video_eof=true`, `eof_at_s=6.279`, `elapsed_s=6.299`. The "not playing fully" symptom is a z-order/visibility presentation issue, not a decoder-duration bug; the controller is a correct duration/EOF implementation. Z-order hardening is follow-up.

## 3. Files changed (this round highlights)
- `tools/s10plus/a67/nuxel-wl-fb.c`, `tools/s10plus/a45/nuxel-navdock.c`, `tools/s10plus/a45/nuxel-statusbar.c`
- `pwa/nuxel-home/js/app.js`, `gestures.js`, `launcher.js`, `widgets.js`, `lockscreen.js`; `css/style.css`, `lockscreen.css`, `launcher.css`; `index.html`
- `pwa/nuxel-apps/doom/{js/doom.js,css/doom.css,index.html,tests/test-doom.js}`
- `pwa/nuxel-apps/clock/js/clock.js`
- `pwa/nuxel-apps/settings/{index.html,settings.css,services-settings.js}`
- `pwa/nuxel-apps/penguinterface/{index.html,css/pengu.css,js/spoof.js}`
- `pwa/nuxel-apps/devmgmt/{js/devmgmt.js,css/devmgmt.css}`
- `services/nuxel-clock/nuxel-clockd.py`, `nuxel-clockd.service`
- `services/nuxel-bridge/src/api.py`, `flatpak_provider.py`
- `configs/nuxel/services/service-policy.json`, `spoof/libnuxel-spoof.c`, `shell/nuxel-browser-native/nuxel_browser_native.py`
- `VERSION` → `v0.7.8-beta` (+ manifest/bridge/package version bumps)

## 4. Services restarted on the phone
- `systemctl daemon-reload`
- `systemctl restart nuxel-http-bridge.service nuxel-clockd.service`
- `systemctl is-active` verified for `nuxel-http-bridge`, `nuxel-clockd`, `nuxel-wl-fb`, `nuxel-soundd` → all `active`.

## 5. Automated tests
- Doom: 54 passed, 0 failed.
- Clock scheduler: 10 passed.
- App surface / flatpak launch flags: 15 passed.
- `node --check` + `python3 ast.parse` clean on all changed JS/Python files.

## 6. Backup + rollback
- Phone backup: `/var/backups/nuxel/pwnage88000-20261107T121039Z/` (pre-deploy copies of key files).
- Deployed tarball sha256: `3517e2f1b801edb887b2675b59ab2670c118e9f0f2bb635b52976fdfef9404b0`.
- Rollback (per-file on device):
```sh
B=/var/backups/nuxel/pwnage88000-20261107T121039Z
cp -a "$B/..." /usr/lib/nuxel/nuxel-bridge/api.py   # etc. (map _ to /)
systemctl daemon-reload
systemctl restart nuxel-http-bridge.service nuxel-clockd.service
```

## 7. Known limitations / honest status
- **C binaries (`nuxel-wl-fb`, `nuxel-navdock`, `nuxel-statusbar`) were not rebuilt on-device this session**; their source changes are committed and will be compiled by the release workflow, then exercised on the physical handset after the release image is flashed/rebooted.
- **Waydroid:** `BLOCKED_KERNEL` (exact missing prerequisites above).
- **Physical visual/audio acceptance** (zero-flash frames, Doom sound, heavy shake, dark theme, browser viewport, preload z-order) is `NEEDS_OWNER_TEST` after the release image boots; code + unit tests + live spoof/build evidence are provided.
- No kernel/boot/recovery/userdata flashing performed. No credentials, seeds, tokens, or private keys were stored or captured.
