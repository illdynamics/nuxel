# PWNAGE-31000 — live S10+ evidence

Date: 2026-10-28 (Europe/Amsterdam)

## Target identity

```
model   Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820
kernel  Linux 4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64
os      Fedora Linux 43 (Forty Three)
console /dev/ttyACM0  (NUXEL-S10PLUS-0001, 18d1:4ee7)
ssh     nuxel@10.20.30.16:22 (pinned host key, public-key auth)
mpv     /usr/bin/mpv, mpv v0.40.0, FFmpeg 7.1.1 runtime / 7.1.5 libs
```

Boot IDs observed:

```
before deployment   fd90d418-cb94-4130-91da-83c5c3b49a25
failed first boot   38b9bea3-1f04-40d0-a1cb-51b61a239e2a
first successful    c20cd499-0fcb-4b00-847e-01d49899a6d1  (45 s hard bound; visual evidence)
final bound boot    91dfb631-bd6b-40ed-aa8f-30beb9cef6fd  (25 s hard bound; final config)
```

## Asset

```
source   assets/nuxel-preloading-screen.mp4
runtime  /usr/share/nuxel/preload/nuxel-preloading-screen.mp4
bytes    7,630,092
sha256   b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1
video    H.264 High 1080x1920 24 fps, 144 frames, yuv420p, bt709/tv
audio    AAC-LC 48 kHz stereo (present; controller always passes --no-audio --mute=yes)
```

The 7.6 MB payload was transferred over the approved Tri-Link WLAN `put`
(SCP to a temporary name, remote SHA-256 checked, atomic rename, final SHA-256
checked), then installed by the serial root console into
`/usr/share/nuxel/preload/` with the same SHA-256 check.  The real
`nuxel-live-deploy.py` manifest transaction then saw the target already matched
the source hash (idempotent skip), installed the controller/config/unit/doc,
ran `daemon-reload` + `systemctl enable`, and passed the manifest health check.
No block device, BOOT partition, kernel, DTB or recovery area was touched.

## Deployment evidence

- Dry-run: `dry-run-plan.json` — 5 steps, no violations,
  `IMPLEMENTED_NOT_DEPLOYED`, no compositor restart.
- Final transaction: `deploy-rev3.json` — `DEPLOYED_UNVERIFIED`,
  boot ID unchanged (`2e364ecf…`), 3 changed files, 0 restarts,
  `[HEALTH_CHECK] health checks passed`.
- The asset and unit were unchanged/`already_deployed` in rev3; their hashes
  were re-read by the health check.

`DEPLOYED_UNVERIFIED` was the correct pre-reboot state; the physical boot below
is the observation that upgrades it to verified playback.

After the physical run only `docs/pwnage-31000/IMPLEMENTATION.md` changed.
Two re-runs of the full serial transaction then hit intermittent console
frame-integrity failures (`BLOCKED_EXTERNAL_RESOURCE`, no writes, no leftover
`.nuxel-staged` files); the evidence directories are
`pwnage31000-preload-cinema-final` and `...-doc-final`.  The documentation file
alone was then synced through the approved Tri-Link WLAN `put` to `/var/tmp`
(SHA-256 verified) and installed atomically by the root serial console with a
second SHA-256 check.  The final manifest health check returned 0, and every
runtime file on the phone matches the manifest's current source hash.

## Physical boot

First successful boot `c20cd499-0fcb-4b00-847e-01d49899a6d1` (45 s hard bound):

- Controller start: 10:58:32 (+0100).
- Launcher document ready: 10:58:34.892.
- Display handoff receipt (`DISPLAY_ON`) appeared after the initramfs animation
  handed the panel to `nuxel-wl-fb`.
- `player_started`: 10:58:46.815.
- `video_eof`: 10:58:53.577, elapsed 6.309 s.
- `player_stopped`: 10:58:53.594; service deactivated successfully at
  10:58:53.745.
- Receipt: `PLAYED`, `reason=video-and-lockscreen-ready`, `video_eof=true`,
  `video_held=false`, `bounded=false`, `asset_sha256` matches, `audio=disabled`,
  `unlock_actions=0`, readiness `critical=true`, `ready=true`,
  `display_state_fresh=true`.
- `pgrep -a mpv` after handoff: no process.  IPC socket absent.
- At handoff the lockscreen remained visible/locked (`NUXEL_INPUT LOCKS[a45.1]`
  lines).  A later normal unlock at 11:15:03 completed through the existing
  `penguin-host-event` gesture path (`unlock:complete`, `locked=0`); the
  controller itself performed no unlock action (`unlock_actions=0`).

Boot timing, measured on the same device:

```
baseline (no preload)  3.771 s kernel + 1m47.885 s userspace = 1m51.657 s
                       multi-user.target after 47.905 s userspace
with preload           3.763 s kernel + 1m48.022 s userspace = 1m51.786 s
                       multi-user.target after 48.065 s userspace
```

The user-visible video interval is 6.309 s after the display handoff; the boot
target is not held open by it (`Type=simple`).  The only failing unit before
and after is the pre-existing `NetworkManager-wait-online.service`.

After the normal unlock, a deliberate `systemctl start nuxel-preload-cinema`
returned `ALREADY_RAN` (`one-shot-boot-marker-present`), spawned no mpv process
and left the desktop untouched.  This is the physical check that the clip
cannot paint over an unlocked session in the same boot.

## Final bound re-verification

After tightening `hard_timeout_ms` from 45 s to 25 s (so the worst-case overlay
release is `30 s start wait + 25 s hold`, safely inside the fallback unit's 60 s
launcher wait), the final controller/config were installed and the device was
rebooted again:

```
boot_id 91dfb631-bd6b-40ed-aa8f-30beb9cef6fd
controller start 11:12:38.040
launcher ready   11:12:40.784
display handoff  11:12:51.704  (/var/lib/nuxel/display DISPLAY_ON)
player start     11:12:52.914
video EOF        11:12:59.658  elapsed 6.290 s
handoff done     11:12:59.836
verdict          PLAYED, video_eof=true, hard_timeout_ms=25000, unlock_actions=0
no mpv process after handoff; lockscreen LOCKS[a45.1] lines present
```

Final boot timing (same baseline definition):

```
baseline   3.771 s kernel + 1m47.885 s userspace = 1m51.657 s; multi-user 47.905 s
final      3.764 s kernel + 1m47.953 s userspace = 1m51.717 s; multi-user 47.972 s
```

The visual frame-match evidence below was captured on the first successful boot;
the only runtime difference in the final boot is the shorter worst-case hold,
which was not reached in either successful boot.

## Visual/frame evidence

`nuxel-wl-snapshot` captured 40 frames from the compositor output during boot
(720x1520, no `/dev/fb0` open).  Frames 22–35 have black top/bottom bars
(0,0,0) and match the supplied clip's 144-frame sequence in order:

```
snapshot 22 -> video frame 009    snapshot 30 -> video frame 074
snapshot 23 -> video frame 017    snapshot 31 -> video frame 082
snapshot 24 -> video frame 025    snapshot 32 -> video frame 091
snapshot 25 -> video frame 033    snapshot 33 -> video frame 099
snapshot 26 -> video frame 041    snapshot 34 -> video frame 107
snapshot 27 -> video frame 049    snapshot 35 -> video frame 112
snapshot 28 -> video frame 057    snapshot 38 -> video frame 140
snapshot 29 -> video frame 066
```

The 8-frame step per ~0.33 s snapshot is exactly 24 fps.  The black bars confirm
`--keepaspect=yes --panscan=0` on the 720x1520 output (video painted at
y=120, 720x1280, as the mpv log records).  Frames 39–40 return to the real
lockscreen (no black bars, no clip match).  See `frame-match.tsv` and
`frame-match-contact-sheet.jpg`.

mpv used software decode (`libopenh264`, `DR failed - disabling`, then
`Using software decoding`), `VO: [wlshm] 1080x1920`, `Video display:
1080x1920 -> (0,120) 720x1280`, and reached `video EOF reached` at 6.333 s.
No dropped-frame counter or decoder error appears in `mpv.log`.

## Failure-path evidence

With the asset temporarily renamed, `systemctl start nuxel-preload-cinema`
produced:

```
verdict FALLBACK
reason  asset-missing
unlock_actions 0
```

No mpv process was created; `nuxel-wayland` and `nuxel-wl-fb` stayed active.
The asset was immediately restored and re-hashed to
`b059f121…cdbbf1`; the service was reset to inactive/enabled for the next boot.
See `fallback-missing-asset.txt`.

## Limitations / not claimed

- The unlock at 11:15:03 was performed through the existing device gesture
  path (not injected by the controller); this automation did not itself swipe
  the panel.  It confirms the normal unlock flow and desktop handoff still work.
- A second *manual* start within the 120 s `StartLimitBurst=1` window is
  refused by systemd (`start-limit-hit`); this is the intended restart-loop
  guard and is reset on reboot.  Automated tests cover repeat controller entry
  via the one-shot `/run/nuxel/preload-cinema.done` marker.
- CPU/RSS was not sampled with `/usr/bin/time` because that binary is absent;
  the real 6.333 s wall-clock playback and mpv log are the measured evidence.

## Final device state (post-evidence)

`final-device-state.txt` records the state after the fallback test and the final
documentation sync:

```
boot_id 91dfb631-bd6b-40ed-aa8f-30beb9cef6fd
nuxel-preload-cinema: enabled, inactive (played and exited)
nuxel-wayland / nuxel-wl-fb / nuxel-touch-arm / nuxel-bridge / nuxel-web: active
asset sha256 b059f121…cdbbf1
controller 9c93c58d…655dc5   config 23a2d7a0…d4fd2b262
unit 070566f5…f07d865       doc c36ce8eb…7c9065d
/run/nuxel/preload-cinema.done present from the boot; post-unlock start = ALREADY_RAN
no mpv process
normal unlock at 11:15:03 (`penguin-host-event`, locked=0), not initiated by the controller
only NetworkManager-wait-online.service failed (pre-existing)
```
