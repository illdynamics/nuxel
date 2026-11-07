# App responsiveness repair — 2026-11-07

Target: Nuxel on Samsung Galaxy S10+ (`beyond2lte`, aarch64, Fedora Linux 43,
kernel `4.14.253-gf7194c1d15ed-dirty`), reached as `root@192.168.178.167` over
Wi-Fi SSH.  No reboot was performed.

## Reported symptoms

| App | Symptom |
|---|---|
| Signal | running, high CPU/RAM, window not reliably usable |
| Telegram | started but stayed behind Home / unresponsive |
| Caprine | window existed but stayed behind Home |
| ZapZap | did not start (crashed with SIGTRAP) |
| Portal for Teams | did not start (renderer exited) |
| Ferdium | started but stayed behind Home / unresponsive |
| Software center | repeated taps opened duplicate windows |

## Root causes found on the live device

1. **Wayland app_id mismatch.**  Launcher/Flatpak ids are reverse-DNS while the
   compositor publishes the client's own id:
   * `com.sindresorhus.Caprine` → `Caprine`
   * `org.ferdium.Ferdium` → `ferdium`
   * `com.github.IsmaelMartinez.teams_for_linux` → `teams-for-linux` (or the full id)
   The focus/close helper matched the string exactly, so it timed out and Home
   stayed on top.  `watch-lock` correctly raised Home while the session was
   locked, which made the mismatch look like a frozen app.

2. **Focus wait too short.**  The helper waited only 10 s (`40 × 0.25 s`).
   On a loaded device the first toplevel for Telegram/Signal can appear later,
   leaving the app behind Home even though it was healthy.

3. **Electron flags were applied by app name.**  Only Legcord and Vesktop got
   `--disable-gpu --no-sandbox`; Signal/Caprine ran an unnecessary GPU process
   and Teams/Ferdium crashed their renderer with
   `render-process-gone abnormal-exit`.  All Electron apps on this vendor
   kernel need Wayland + software compositing + the inner-Chromium-sandbox
   bypass (the Flatpak/bwrap sandbox remains active).

4. **QtWebEngine had no equivalent path.**  ZapZap failed with
   `Error calling Spawn(): org.freedesktop.DBus.Error.InvalidArgs: Could not
   find requesting pid`, then SIGTRAP.  QtWebEngine ignores application argv
   and needs `QTWEBENGINE_DISABLE_SANDBOX=1` plus
   `QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu ...`.

5. **No launch idempotence.**  Every tap spawned a new `nuxel-app-*` unit.
   Five Software windows plus duplicate Electron processes had reduced
   available RAM to ~80 MB and load average to ~14, making every app sluggish.

## Changes

### New: `services/nuxel-bridge/src/app_surface.py` (deployed as `/usr/lib/nuxel/nuxel-bridge/app_surface.py`)
One normalization rule for launcher → compositor ids:
full id, dotted tail, and `StartupWMClass` from the app's exported desktop
entry; exact match first, then bounded suffix matching.  No caller-supplied
path or command is used.

### `services/nuxel-s10/bin/nuxel-focus-app.sh`
* Normalized candidate matching (caprine/ferdium/teams-for-linux, future apps).
* Wait increased from 10 s to 45 s.
* New `--probe` mode for one-pass existing-window detection.
* Prints `FOCUSED app_id=<real surface>` for evidence.

### `services/nuxel-bridge/src/flatpak_provider.py`
* Generic Electron profile (metadata-detected, cached):
  `ELECTRON_OZONE_PLATFORM_HINT=wayland`,
  `ZYPAK_ZYGOTE_STRATEGY_SPAWN=0`,
  `--ozone-platform=wayland`,
  `--enable-features=UseOzonePlatform,WebRTCPipeWireCapturer`,
  `--disable-gpu`, `--no-sandbox`, `--disable-dev-shm-usage`.
* Generic QtWebEngine profile (metadata-detected, cached):
  `QTWEBENGINE_DISABLE_SANDBOX=1` and a software-compositing
  `QTWEBENGINE_CHROMIUM_FLAGS`.
* All flags are emitted by `launch_argv()`, so `/apps/exec` and
  `/flatpak/launch` cannot diverge.

### `services/nuxel-bridge/src/api.py`
* Pre-launch focus probe and bounded startup-unit check → one instance per tap.
* Active units older than 45 s and windowless are treated as tray processes and
  may be re-activated with a fresh `flatpak run`.
* Close/activate endpoints resolve the real compositor id first.
* Launch evidence window extended to 30 s.

## Live verification (bridge launch path)

Sequential run after deployment; each line required `act=1` on the real
compositor toplevel:

```text
PASS com.sindresorhus.Caprine -> Caprine active=1 in 4s
PASS com.rtosta.zapzap -> com.rtosta.zapzap active=1 in 5s
PASS com.github.IsmaelMartinez.teams_for_linux -> com.github.IsmaelMartinez.teams_for_linux active=1 in 3s
PASS org.ferdium.Ferdium -> ferdium active=1 in 4s
PASS org.signal.Signal -> org.signal.Signal active=1 in 5s
PASS org.telegram.desktop -> org.telegram.desktop active=1 in 0s
RESULT rc=0
```

Additional checks:
* Second launch of Caprine returned `already_running` and focused the existing
  window; unit count and window count stayed at 1.
* Two Software launches produced exactly one `nuxel-app-software-*` unit and
  one `nuxel-software` window.
* Graceful close of `com.sindresorhus.Caprine` resolved to surface `Caprine`
  and closed it (`closed_apps: ["Caprine"]`).
* `systemctl --failed` empty after cleanup.
* Memory after closing verification apps: ~3.4 GiB used / ~3.9 GiB available
  (was ~4.8–5.5 GiB used with duplicate instances).

Automated tests:

```text
tests/pwnage85000/test_app_surface_and_launch_flags.py
tests/pwnage85000/test_flatpak_launch_perf.py
15 passed
```

## Deployed hashes

```text
d5ba55bde59a4375b136d21c298cb874abbbbac0f75fb3d22c0851245c7589a7  api.py
ce853552528550e2a4ae7bd97eb8261b14d91a48d398e6dd3629e58adba9cc29  flatpak_provider.py
4e5c5b5fd21222cd9559530fc1281bc4d7479d89fbaa8367d401ec951256ee11  app_surface.py
384cd3907701eb2c46413460bea153ac75ddceb0bf0ecea49b3651a0f84f8163  nuxel-focus-app.sh
```

## Rollback

Backup: `/root/nuxel-responsive-fix-backup-20261106T231907Z/`

```sh
B=/root/nuxel-responsive-fix-backup-20261106T231907Z
install -m 0644 "$B/api.py"              /usr/lib/nuxel/nuxel-bridge/api.py
install -m 0644 "$B/flatpak_provider.py" /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py
install -m 0755 "$B/nuxel-focus-app.sh"  /usr/lib/nuxel/nuxel-focus-app.sh
rm -f /usr/lib/nuxel/nuxel-bridge/app_surface.py
systemctl restart nuxel-http-bridge.service
```

## Limitations

* Signal performs initial message sync and can use significant CPU/RAM until it
  settles; this is application work, not a launch/focus failure.
* `--no-sandbox` disables only Chromium's inner sandbox.  The Flatpak/bwrap
  sandbox, user separation and per-app filesystem permissions remain active;
  this is required because the vendor 4.14 kernel cannot provide Chromium's
  sandbox helper on this image.
* No reboot was performed; persistence comes from the deployed files in
  `/usr/lib/nuxel`, not from a transient runtime change.
