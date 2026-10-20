# Nuxel A37 — live S10+ icon, audio and keyboard-haptics deployment

**Hardware status:** REQUIRES LIVE PHONE TEST. This repository contains the owner's PNGs and MP3s and a repaired delivery/diagnostic path. No claim of audible output, functional CS35L40 route or keyboard vibration has been made on the phone.

**Forbidden:** flashing, partition writes, kernel/bootloader/modem changes, guessed ALSA/amp register writes, disabling the protective hardware-volume cap, stopping the USB recovery console, enabling two vibrator writers. Source tree preserves the existing launcher and physical three-button navigation.

## 0. Secure current recoverable state

Use the EXISTING framed live USB-console tooling and current known-good connection. Identify the real serial port, phone architecture, running Nuxel version and exact `nuxel-web` document root via `systemctl cat nuxel-web`, `/proc/$PID/environ`, `systemctl show nuxel-web -p Environment`, and `readlink -f /usr/share/nuxel`. Do not invent transport commands or assume SSH works. Confirm USB session can reconnect before every service restart.

Before any install, use the existing guarded deployer to record **hashes + byte-for-byte backups** of all affected files in `/usr/share/nuxel/pwa/nuxel-home/`, `/usr/share/nuxel/assets/`, `/usr/libexec/nuxel/nuxel-sound-cue`, `/etc/systemd/system/nuxel-boot-sound.service`, and `/usr/lib/nuxel/nuxel-button-manager`. Preserve `nuxel-haptics` preferences. Log active browser/Wayland and speaker/haptics service states. Establish tested rollback commands for each deployed artifact; never overwrite an unbacked-up live file.

## 1. Apply A37's guarded source/asset updates

The `nuxel-branding-sounds-and-icons` group in `tools/beta/live/deploy-manifest.json` stages all supplied app/Quick Settings/nav PNGs, A37 `index.html`, `apps.js`, `qs.js`, `touch-keyboard.js`, `launcher.css`, `sw.js`, both MP3s, `nuxel-sound-cue`, the systemd unit, A37 audit and existing haptics daemon data. **Important:** the manifest intentionally authors `/home/nuxel/nuxel/...` paths, and the guarded deployer REMAPS them to `/usr/share/nuxel/...` on the S10+. Do **not** separately upload to both paths unless the live system independently proves both are real docroots; duplicate remapped writes can conceal errors.

`images/s10plus/build-phone-rootfs-inside-fedora.sh` copies `/nuxel/pwa` plus `/nuxel/assets` into the canonical `/usr/share/nuxel` webroot for future rootfs builds. Extra brand assets at `pwa/nuxel-home/assets/branding` exist as local compatibility copies, not an independent source of truth.

Run before deploy:

```sh
python3 tools/s10plus/a34/tests/test-icon-assets.py
python3 tools/s10plus/a34/tests/test-sound-cues.py
node tools/s10plus/a34/tests/test-touch-keyboard.js
python3 tools/s10plus/a37/nuxel-a37-check.py --root "$PWD" --offline
```

Use the project's live plan/guarded USB transfer to transfer and atomically replace files. Verify hashes **on the phone**. Validate actual WebKit docroot — do not assume the Git checkout on the Mac is what the phone serves. When JavaScript/HTML/assets verified, prefer **reloading only the launcher WebKit view** (through existing safe launcher reload hook) over restarting the whole display stack. Restart only `nuxel-web.service` if it must reload, preserve Wayland/console/bridge ownership, and ensure the browser advances from stale service worker to cache `v14-a37-live-assets-and-audio`.

Live HTTP probes from the PHONE itself (200, correct `Content-Type`, and SHA-256 matching staged bytes):

```sh
curl -fsSI 'http://127.0.0.1:8000/assets/button-left.png?v=a37'
curl -fsSI 'http://127.0.0.1:8000/assets/nuxel-applications-icon-pack/01-01_terminal.png?v=a37'
curl -fsSI 'http://127.0.0.1:8000/assets/nuxel-quicksettings-icon-pack/01-wifi.png?v=a37'
curl -fsSI 'http://127.0.0.1:8000/pwa/nuxel-home/sw.js'
/usr/local/bin/nuxel-a37-check --root /usr/share/nuxel
```

Make sure the real launcher uses `index.html`, JS and SW from the active webroot. The assets use absolute `/assets/...png?v=a37` and the service worker uses **network-first** for owner PNGs. On the glass inspect app grid, dock, search, Recents, Quick Settings and each of Back/Home/Recents, not merely HTTP 200.

## 2. Volume preview and startup sound

Validate `mpg123`, ALSA (`aplay -l`, `aplay -L`, `amixer`, `alsaucm`), loaded vendor firmware and the observed `beyond-madera` UCM route; package manager installations, if necessary, must exclude kernel changes and preserve rootfs recovery. Use `nuxelctl audio pipeline` (or `tools/s10plus/a33/nuxel-audio-diag.sh pipeline` with the proper phone path) to locate the **first** broken link. The tracked UCM `configs/alsa-ucm/beyond-madera/HiFi.conf` has EMPTY route sequences until verified real hardware settings are captured. Do not fabricate CS47L93/CS35L40 amplifier control names or assert success from an MP3 exit code.

`nuxel-sound-cue` now explicitly calls `mpg123 -o alsa` and records output backend, return code, diagnostics, PCM gain and `audible=unverified`. It defaults to ALSA's genuine default device. Only when a real working playback device is measured may you set `NUXEL_SOUND_ALSA_DEVICE` in the boot service and button-manager environment (the helper passes `-a DEVICE`); do not guess card indices or persist speculative mixer values.

`nuxel-button-manager.c` must be cross-compiled/deployed as a **Linux AArch64 ELF**, installed atomically into `/usr/lib/nuxel/nuxel-button-manager`, with `readelf -h` and `ldd` checked on-device, ONLY if the deployed binary doesn't contain its cue hook. Never copy a macOS-architecture binary. After backup, restart `nuxel-button-manager.service` only. Its cue fires after a SUCCESSFUL protected mixer change; if the actual mixer is missing, fix the measured mixer route rather than claiming volume previews work. The `--level` argument is telemetry, the existing hardware mixer cap remains in effect.

Enable `nuxel-boot-sound.service` after verifying files and service. On the next **single safe normal reboot** it waits for `/run/nuxel-anim-handoff` = `{ "owner":"ui", "stage":"LAUNCHER_DISPLAY_OWNER" }` and calls the supplied boot MP3 at 44% PCM gain ONCE per boot. If playback fails, the attempted marker prevents automatic loud retry loops; collect the actual fault, correct it, and only retry manually under physical owner supervision.

Collect `journalctl -b -u nuxel-boot-sound.service -u nuxel-button-manager.service -u nuxel-web.service`, `/var/log/nuxel/sound-cues.log`, `aplay -l`, ALSA UCM output, and exact `mpg123` stderr for both cues. Never increase the protection cap to force a result. `player_ok` means decode/output command completed; **it does not mean owner heard audio**.

## 3. Keyboard haptics

Verify which SINGLE service owns `/run/nuxel-haptics/haptics.cmd` and `/sys/class/timed_output/vibrator/enable`; do not enable the older bridge and new `nuxel-hapticsd` simultaneously. A37 requests `haptics-tap` on software-keyboard **pointerdown** while retaining click-only accessibility fallback. `qs.js` now uses the same native host actuator rather than additionally invoking `navigator.vibrate()`. Confirm host's `nuxelHost` script channel works from the active WebKit view and phone's FIFO exists. Verify the actual virtual keyboard used by Nuxel — if an external input method is active, this page's keyboard will not receive its events; test integration with that actual input method instead. Test taps in Search and iframe PWAs, observe state but do not log typed content.

## 4. Real acceptance and rollback

Announce: **"90-second physical test starts NOW: verify PNG app/dock/nav/Quick Settings artwork, tap Search keyboard keys and feel vibration, press Volume +/- and listen for POW; report PASS/FAIL per category."** Keep capturing logs, wait for owner feedback, then classify icon 404/mismatch, stale SW, haptics FIFO/host, ALSA card/PCM/route, mute policy, or boot handoff as separate root causes. Repair the specific first failure and retest without unnecessary whole-OS restarts. Once assets, hardware keys and audio diagnostics are stable, and the USB live console is confirmed recoverable, perform **one** ordinary Nuxel reboot and confirm startup cue begins after UI ownership and occurs only once.

**Do not call deployment complete unless real PNGs appear and owner confirms physical haptics/audio.** If speaker output remains unavailable, provide the first failing ALSA/DAPM/UCM stage, supporting logs and rollback status. Roll back affected files and services immediately on launcher/console regression, retaining existing boot and USB console functionality.
