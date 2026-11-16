codex
I've been going 400+ tool calls without a checkpoint, so I'll pause here and summarize where things stand.

## Done (in the repo; not yet deployed)

**SSH** — works: `root@192.168.178.167` with `~/.ssh/wicked_wqn_id_rsa`.

### Root causes found (verified live)
1. **Can't unlock by swiping the lockhead.** The provider was `locked:true` in swipe mode and the launcher's `verifyUnlock()` rejected the swipe *before* anything released the lock → your exact log `credential-required-on-lockscreen`, four times.
2. **Booted straight into the unlocked phone.** `/run` is a tmpfs and **nothing writes `lock-state.json` at boot** — the file's first timestamp is *after* the session started. The launcher's boot gate also explicitly hid the overlay when the provider said "unlocked", and it never showed the lockscreen again.
3. **Triple buttons dead in Settings/VNC.** Same missing file: nuxel-navdock read `lock=unknown` and refused every `show` (`NAV_DOCK_SHOW_REFUSED` ×40+, `NAV_DOCK_HIDE locked`).
4. **No sound on volume/notification.** nuxel-soundd deadlocked itself: `_start_stream()` held a non-reentrant lock and called `_restart_stream()` → `_start_stream()`. The player thread died; cues stayed "pending" forever (`restarts=39`).
5. **Silent boot video.** Config says `"audio": "mp4"` but the player command hardcoded `--no-audio --mute=yes`.
6. **Archive Manager "locked" → `launch:blocked-locked`**, plus `_active_app_units()` never matches `nuxel-app-fileroller-*` → duplicate instances on a second tap.
7. **Browser** maps fine when launched directly; journal shows the Home-close sequence + `no_surface_timeout` + 2 windows (likely the same lock/duplicate pattern).

### Changes written
- `security-lock.js` (a85): direct swipe now releases a swipe-mode lock via the provider's own `security/unlock`; credentialed modes untouched. `app.js` passes `direct` and arms a boot lock before the overlay decision.
- `security_provider.py`: new idempotent `ensure-state` (swipe → unlocked, pin/pattern/fp → locked), plus `nuxel-security-state-rpc` invoked from the session and shell-chrome startup.
- `nuxel-soundd.py`: re-entrant start lock + `_starting` guard + crash-proof player loop.
- `nuxel-preload-cinema`: honors `audio=mp4` (real `--ao`), receipt reports `embedded`.
- `api.py`: app-unit suffix fix. `nuxel-navdock.c`: honest lock naming.
- Edge FX: polling now always starts (no silent `boot()` failure), and `document.hidden` (focus) no longer suppresses notification effects.

## Not yet done
- **Not deployed to the phone yet** — nothing above is live.
- VNC/RDP: still need to enable/start VNC, verify Jump Desktop negotiation, and confirm RDP's loopback path (both were disabled).
- Navdock binary rebuild on-device (toolchain is present there).
- No end-to-end on-device test of the unlock→dock→app chain yet.

Want me to proceed with the deploy and live verification now?
I've been going 400+ tool calls without a checkpoint, so I'll pause here and summarize where things stand.

## Done (in the repo; not yet deployed)

**SSH** — works: `root@192.168.178.167` with `~/.ssh/wicked_wqn_id_rsa`.

### Root causes found (verified live)
1. **Can't unlock by swiping the lockhead.** The provider was `locked:true` in swipe mode and the launcher's `verifyUnlock()` rejected the swipe *before* anything released the lock → your exact log `credential-required-on-lockscreen`, four times.
2. **Booted straight into the unlocked phone.** `/run` is a tmpfs and **nothing writes `lock-state.json` at boot** — the file's first timestamp is *after* the session started. The launcher's boot gate also explicitly hid the overlay when the provider said "unlocked", and it never showed the lockscreen again.
3. **Triple buttons dead in Settings/VNC.** Same missing file: nuxel-navdock read `lock=unknown` and refused every `show` (`NAV_DOCK_SHOW_REFUSED` ×40+, `NAV_DOCK_HIDE locked`).
4. **No sound on volume/notification.** nuxel-soundd deadlocked itself: `_start_stream()` held a non-reentrant lock and called `_restart_stream()` → `_start_stream()`. The player thread died; cues stayed "pending" forever (`restarts=39`).
5. **Silent boot video.** Config says `"audio": "mp4"` but the player command hardcoded `--no-audio --mute=yes`.
6. **Archive Manager "locked" → `launch:blocked-locked`**, plus `_active_app_units()` never matches `nuxel-app-fileroller-*` → duplicate instances on a second tap.
7. **Browser** maps fine when launched directly; journal shows the Home-close sequence + `no_surface_timeout` + 2 windows (likely the same lock/duplicate pattern).

### Changes written
- `security-lock.js` (a85): direct swipe now releases a swipe-mode lock via the provider's own `security/unlock`; credentialed modes untouched. `app.js` passes `direct` and arms a boot lock before the overlay decision.
- `security_provider.py`: new idempotent `ensure-state` (swipe → unlocked, pin/pattern/fp → locked), plus `nuxel-security-state-rpc` invoked from the session and shell-chrome startup.
- `nuxel-soundd.py`: re-entrant start lock + `_starting` guard + crash-proof player loop.
- `nuxel-preload-cinema`: honors `audio=mp4` (real `--ao`), receipt reports `embedded`.
- `api.py`: app-unit suffix fix. `nuxel-navdock.c`: honest lock naming.
- Edge FX: polling now always starts (no silent `boot()` failure), and `document.hidden` (focus) no longer suppresses notification effects.

## Not yet done
- **Not deployed to the phone yet** — nothing above is live.
- VNC/RDP: still need to enable/start VNC, verify Jump Desktop negotiation, and confirm RDP's loopback path (both were disabled).
- Navdock binary rebuild on-device (toolchain is present there).
- No end-to-end on-device test of the unlock→dock→app chain yet.

Want me to proceed with the deploy and live verification now?
tokens used
45,599,900
[codeseeq] stopping owned bridge process (pid=96869)
(base) ╭─[ꝖꝖ]─wicked↯infranux in ~/x/nuxel

---

## Session 2026-11-14 (A88) — what was actually deployed live

Deployed with `scripts/nuxel-deploy-live.py --apply` (userspace only) and verified
on `root@192.168.178.167`.

### Lockscreen (owner contract)
- **Swipe only is the current permanent state**: `lock.json` has `mode=swipe`
  and **no** verifier/fallback PIN (`pin_fallback_set=false`); the PIN prompt the
  owner could not type into cannot appear any more.  Selecting "swipe only"
  clears the whole credential document; selecting **pin** without a PIN is
  refused (`pin_required`) — the PIN can only be set by entering it twice
  (PIN 383838 is accepted). Pattern and fingerprint require their setup and a
  PIN fallback; fingerprint is refused honestly on this handset (no TEE matcher).
- **Boot** always publishes `locked:true` (`reason=boot`) for every mode, so the
  phone always starts on the lockscreen with the lockhead to swipe.  Verified
  after a real reboot: screenshot shows the wallpaper clock + lockhead only, no
  keypad.  A swipe releases swipe mode via `security/unlock`; PIN/pattern/fp are
  never released by a swipe.
- Frame-buffer screenshot of the boot screen is on the host at
  `/tmp/nuxel-postboot.png`.
- **Geometry**: the PIN keypad and the pattern matrix are centred on the glass
  (symmetric panel insets, `margin:auto`, height-aware size); the PIN fallback
  button is part of the open panel only; no lockhead is painted under the PIN
  prompt; no title/instructions are painted at all.

### Remote desktop (start from the XRDP / VNC apps)
- `nuxel-remote-desktop-ctl start vnc|xrdp` works when invoked by the bridge
  (the app's Start button): `systemctl start/stop` needs root, which the bridge
  reaches through `AmbientCapabilities=cap_setuid cap_setgid cap_setpcap
  cap_dac_override` on `nuxel-bridge.service` (nothing else).
- XRDP publishes its regenerated `xrdp.ini` to
  `/var/lib/nuxel/remote-desktop/xrdp.ini` and the packaged drop-ins
  (`/etc/systemd/system/xrdp.service.d/`) load it as `LoadCredential=` +
  `xrdp -c` — `/etc/xrdp` is intentionally not writable by the bridge.
- Both bind the WLAN address: VNC `192.168.178.167:5900` (wayvnc, PAM, VeNCrypt
  TLS / RSA-AES / Apple DH), RDP `192.168.178.167:3389` (TLS + PAM) mirroring the
  live Phoc screen.  Status RPC reports both `READY`/`WAITING_FOR_CLIENT`.
- Login for **both**: user `nuxel`, password `Enf0rcer#.nux` (SHA-512 shadow,
  verified with `pamtester` for `wayvnc` and `xrdp-sesman`; wrong password and
  `root` refused).

### Other fixes made along the way
- `nuxel-soundd`: no longer opens the speaker before the ABOX route applied
  (cold-boot sink wedged in error → broken pipe); it re-asserts the route,
  restarts a dead player thread and plays the next cue (measured 9 ms latency,
  ALSA `RUNNING`).
- ABOX boot reload restarts `nuxel-flatpak-pulse-relay.service` (it is PartOf
  the audio session it stops) so Flatpak apps keep the microphone/Pulse socket.
- `nuxel-gnss-lhd`: `SuccessExitStatus=2` (its documented proprietary-boundary
  exit) — no more 30 s power-cycle restart loop; the unit is now packaged by the
  live deployer.
