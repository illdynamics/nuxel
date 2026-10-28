# nuxel-preload-cinema

PWNAGE-31000's bounded, fail-open pre-lockscreen video controller.

## Sequence

```
kernel / existing boot + warning screens        (unchanged)
        |
        v
nuxel-wayland + nuxel-web + nuxel-wl-fb ready   (existing services)
        |
        v
nuxel-preload-cinema starts /usr/bin/mpv (wlshm, no audio) over the real lockscreen
        + existing startup services continue concurrently
        + real lockscreen initializes underneath
        |
        v
video EOF (or bounded pause) AND lockscreen readiness
        |
        v
mpv quits -> the existing real Nuxel lockscreen is revealed
        (one-shot marker prevents a later start over the unlocked desktop)
        |
        v
existing swipe-to-unlock flow (unchanged)
```

## Readiness gates

Only lockscreen-critical signals are used:

- `/run/nuxel-launcher-ready` (non-empty) — written by `nuxel-pwa-host` after the
  launcher document finished loading; `app.js` has already constructed and shown
  the lockscreen synchronously by then.
- `boot=os` is present in `/run/nuxel-home.state` — the launcher is in the
  phone boot mode, not the VM/desktop mode where the lockscreen is intentionally
  hidden.
- `/run/nuxel-wl-fb.state` contains `FRAMES_OK` / `owner=nuxel-wl-fb`, and
  the fresh `/var/lib/nuxel/display` receipt says `DISPLAY_ON`.  The persistent
  receipt is authoritative: on a static lockscreen the `/run` line can remain
  `DISPLAY_SLEEP ... display=off` after the panel is lit, and a stale receipt
  from a previous boot is ignored by comparing its mtime with `/proc/uptime`.
- `/run/nuxel-touch-arm.state` has an `ARMED_OK` status receipt, or an honest
  `NO_TOUCH_DEVICE` / `SCAN_FAIL` warning. Later `TOUCH_POINT` event lines do
  not invalidate the one-shot status line. Input is never reported ready merely
  because a process exists.

NetworkManager, Bluetooth, GNSS, audio and other noncritical services are
deliberately **not** readiness gates. The controller never starts an application
or a second copy of a service.

## Timing

- The supplied clip is H.264 High 1080x1920 at 24 fps, 6.016 s (144 frames),
  with an AAC-LC stereo track that is deliberately muted. mpv decodes it with
  the packaged FFmpeg-free chain at `/usr/bin/mpv`.
- `start_timeout_ms` (default 30 s) waits for the display bridge to take over
  from the initramfs animation; it is a gate wait, not an added delay.
- `max_display_ms` (default 20 s) bounds the moving-video interval. If the clip
  is longer or stalls, mpv is paused on its final frame.
- `hard_timeout_ms` (default 25 s) bounds the final-frame hold when readiness is
  still pending.  With the 30 s start wait the worst case is below the fallback
  unit's 60 s launcher wait. On expiry the controller logs the exact readiness snapshot and
  releases the overlay; the real lockscreen is the safe surface.
- No arbitrary sleep is added after both conditions are true.

## Failure policy

Missing/unreadable asset, hash mismatch, missing player, unready display, decode
failure, IPC failure, player exit, or controller exception all produce a
`FALLBACK` receipt and exit 0. The existing lockscreen/fallback remains. The
controller never calls the unlock action and never writes `/dev/fb0`.

## Deployment

- Runtime binary: `/usr/lib/nuxel/nuxel-preload-cinema`
- Unit: `/etc/systemd/system/nuxel-preload-cinema.service`
- Config: `/etc/nuxel/boot/preload-cinema.json`
- Asset: `/usr/share/nuxel/preload/nuxel-preloading-screen.mp4`
  (SHA-256 `b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1`)
- Receipt: `/run/nuxel/preload-cinema.receipt`
- One-shot boot marker: `/run/nuxel/preload-cinema.done`
- Log: `/var/log/nuxel/preload-cinema.log`

The live-userspace manifest is
`tools/beta/live/nuxel-31000-preload-cinema-manifest.json`.


## Boot ownership (PWNAGE-36000 fix)

On the S10+ the phone session (`nuxel-session.sh`) always starts.  The session
creates `/run/nuxel-preload-session.owner` before the launcher and starts the
controller with `--early`; the early controller waits for
`/run/nuxel-launcher-ready`, maps mpv above WebKit, and publishes `covered` so
the PWA cover can release.  The systemd unit is **not enabled**: it is a
fallback for images without the phone session.  A non-early start now yields
with receipt verdict `YIELD_SESSION` and never writes the one-shot `.done`
marker, so it cannot suppress the session's clip.  The session removes a stale
`preload-status.json` unconditionally at start so a previous `fallback`/`done`
document cannot release the cover early.

The PWA cover has a 15 s fail-open bound (video is 6 s; the early controller
waits up to 6 s for the launcher), and the controller maps 0.8 s after the
launcher marker.  This is what removes the one-second lockscreen flash.
