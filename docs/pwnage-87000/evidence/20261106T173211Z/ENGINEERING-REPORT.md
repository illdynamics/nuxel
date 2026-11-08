# PWNAGE-87000 Engineering Report — 2026-11-06

## 1. Connection and root verification
- Transport: Wi-Fi SSH, key `~/.ssh/wicked_wqn_id_rsa` (never printed).
- Host: `root@192.168.178.167` (reachable; helper-pinned `10.20.30.16` was unreachable and was NOT used).
- `id -u` = 0, kernel `Linux 4.14.253-gf7194c1d15ed-dirty aarch64`, Fedora 43.
- Host key: verified against the owner-pinned `~/.ssh/known_hosts` entry (normal verification, no StrictHostKeyChecking=no, no known_hosts deletion).

## 2. Primary fix (verified on hardware): silent alarm/timer sound
### Root cause
`/etc/pipewire/pipewire.conf.d/50-nuxel-s10-alsa.conf` defines the S10+ speaker
sink `alsa_output.hw_0_1` as a **static** `context.objects` node (the image has
no udev, so WirePlumber's ALSA monitor cannot enumerate it). The companion rule
`/etc/wireplumber/wireplumber.conf.d/99-nuxel-s10.conf` sets
`node.suspend-on-idle=false` inside `monitor.alsa.rules`, which **only applies to
monitor-enumerated nodes** — so the static sink never received it.

WirePlumber 0.5.14 `suspend-node.lua` therefore suspended the sink after 5 s of
idle. `nuxel-soundd` keeps one persistent `pw-cat` stream feeding silence (by
design, so short cues are not swallowed by the CS35L41 power-up ramp). Once the
sink suspended, the graph stalled: `pw-cat` stopped draining, soundd's pipe
filled, and soundd's player loop blocked in `os.write()` with a **stuck pending
cue**. Every subsequent alarm/timer cue was accepted ("queued") but never
reached the DAC. This also caused the observed `pw-cat stream write failed:
Broken pipe` restart storm (44 restarts) and the "sluggish with timer open"
symptom.

### Fix
Pin the static sink always-processing at the PipeWire level and set
`session.suspend-timeout-seconds=0` so suspend-node.lua also skips it:
`node.suspend-on-idle=false`, `node.pause-on-idle=false`,
`node.always-process=true`, `session.suspend-timeout-seconds=0` (same file).
Deployed + restarted `nuxel-audio-session`, `nuxel-audio-route`, `nuxel-soundd`.

### Hardware evidence
- Before: sink `SUSPENDED`, PCM `state=SETUP`, `hw_ptr=0`, DAPM `SPEAKER: Off`, `soundd.player.restarts=44`, `last_error="pw-cat restart backoff 500 ms"`, stuck `pending_action`.
- After: sink `RUNNING`, during an alarm cue PCM `state=RUNNING`,
  `hw_ptr=957478` / `appl_ptr=959488` advancing, DAPM `SPEAKER: On in 1 out 1`,
  `restarts=0`, `last_error=None`, `active=None`, `pending=None`.
- `hw_ptr` advancing proves the ALSA RDMA1 PCM actually consumed samples.

## 3. Desktop scroll/scrollbar fix (deployed)
`.app-grid` (Home desktop) was `overflow-y:auto`, making the desktop vertically
scrollable and showing scrollbars. Changed to `overflow:hidden`; the
Applications drawer (`body.app-drawer-open .app-grid`) keeps `overflow-y:auto`.
Desktop switching remains the existing left/right page gesture.

## 4. Alarm penguin follows the finger (deployed)
`js/lockscreen-clock.js` previously only toggled a fixed 14 px hint class. It now
applies `transform:translate3d(dx,0,0) scale(1)` on pointermove (clamped to a
safe band), pauses the shake animation via a `.dragging` class, and snaps back
on release. Added `.lockscreen-clock-penguin.dragging` CSS.

## 5. Charger detection — backend verified correct
`/api/v1/phone/status` and `/api/v1/system/indicators` correctly report
`battery.charging=true`, `external_power=true`, `level=29` (kernel
`battery/status=Charging`, `ac/online=1`). No backend bug found; the
`read_battery_status()` / `power_state()` logic is correct (Full != charging).
Frontend (status-bar.js / lockscreen-indicators.js) consumes these fields
correctly. Marked `NEEDS_OWNER_TEST` for the physical charging glyph.

## 6. Lockscreen "zoomed desktop" — partial
`#lockscreen` is opaque (z-index 500, solid `#04121f`) and `html.nuxel-boot-locked`
hides `#app-grid`. The reported transient "zoomed desktop + penguin on top" is
most consistent with a boot-race where `nuxel-boot-locked` is not yet applied
while the lockhead paints, or the `background-size:cover` wallpaper crop. Not
reproducible over SSH; marked `NEEDS_OWNER_TEST`. The scrollbar/overflow fix and
the audio deadlock fix remove two known contributors to visual/layout noise.

## 7. Deployment manifest (SHA-256)
- `/etc/pipewire/pipewire.conf.d/50-nuxel-s10-alsa.conf` `03f88849…`
- `css/launcher.css` `000abf36…`
- `css/lockscreen.css` `67516e58…`
- `js/lockscreen-clock.js` `7eee76cf…`
- `index.html` `54567db0…`
- `sw.js` `39a8f0e8…`
(Cache version bumped `v85000-pwnage` -> `v87000-pwnage`; query strings `?v=p87000`.)

## 8. Backup and rollback
Backup: `/var/backups/nuxel/pwnage87000-20261106T173211Z/` (configs + PWA files,
`SHA256SUMS.pre`). Rollback:
```
cp -a /var/backups/nuxel/pwnage87000-20261106T173211Z/pipewire__pipewire.conf.d__50-nuxel-s10-alsa.conf /etc/pipewire/pipewire.conf.d/50-nuxel-s10-alsa.conf
systemctl restart nuxel-audio-session nuxel-audio-route nuxel-soundd
# PWA: restore each file under /usr/share/nuxel/pwa/nuxel-home/ and reload the WebView (reboot or session restart)
```

## 9. Honest status
- AUDIO: `VERIFIED_ON_DEVICE` (hardware trace). Physical "can hear it" still `NEEDS_OWNER_TEST`.
- SCROLLBAR/OVERFLOW: `DEPLOYED` (hashes match); visual `NEEDS_OWNER_TEST`.
- ALARM PENGUIN FOLLOW: `IMPLEMENTED` + `DEPLOYED`; touch `NEEDS_OWNER_TEST`.
- CHARGER DETECTION: `VERIFIED` backend only; UI glyph `NEEDS_OWNER_TEST`.
- LOCKSHELL ZOOM: `NOT REPRODUCED` over SSH; `NEEDS_OWNER_TEST`.
- PERFORMANCE: audio deadlock (44 restarts / blocked player loop) removed; broad CPU load remains pre-existing (software-rendering WebKit + vendor TZ/SRPMB D-state threads).
