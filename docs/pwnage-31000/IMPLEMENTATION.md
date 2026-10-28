# PWNAGE-31000 — Nuxel Preload Cinema

Status: implemented, offline-verified and **physically boot-verified on the
S10+** on 2026-10-28 (final boot ID `91dfb631-bd6b-40ed-aa8f-30beb9cef6fd`,
with visual frame evidence from the first successful boot
`c20cd499-0fcb-4b00-847e-01d49899a6d1`).  The normal unlock flow completed
through the existing `penguin-host-event` gesture path at 11:15:03; the
controller itself performed no unlock action.  Evidence:
`docs/beta-finalization/live/evidence/pwnage-31000/`.

## Discovered boot architecture

The shipping S10+ path is:

```
initramfs: existing Nuxel boot/warning assets, first-light frame, nuxel-anim-player
    -> switch_root
    -> systemd
       nuxel-web (:8000 static PWA server)
       nuxel-wayland (phoc headless + nuxel-pwa-host -> pwa/nuxel-home?boot=os)
       nuxel-wl-fb (single /dev/fb0 owner, screencopy -> DECON)
       nuxel-touch-arm, nuxel-button-manager, nuxel-bridge/portal/notifications
```

The existing warning screen and initramfs animation are untouched. The real
lockscreen is the `#lockscreen` overlay in `pwa/nuxel-home`. In phone mode
`nuxel-pwa-host` opens the launcher with `?boot=os`; `app.js` constructs and
shows the lockscreen synchronously during `NuxelHome._init()`, and the host
writes `/run/nuxel-launcher-ready` after the document load finishes. The
launcher never shows the desktop until the normal swipe-up unlock succeeds.

## Why the controller is native and not a WebKit `<video>`

The deployed WebKitGTK host deliberately disables media when
`libgstautodetect.so` is absent. The measured A29b failure is `GStreamer element
autoaudiosink not found`, followed by a WebKitWebProcess abort. The image has
GStreamer base/bad-free but not `gstreamer1-plugins-good`.

The S10+ live userspace has **mpv 0.40.0** with the FFmpeg-free decode chain.
A one-frame decode of the repository's existing H.264 asset succeeds on the
device, and a one-second `wlshm` fullscreen run exits 0. The preload clip is
therefore a separate, audio-free **mpv Wayland client**. It does not add a
second framebuffer owner and does not change WebKit's media policy.

The controller invokes `/usr/bin/mpv` by absolute path. The image builder now
installs `mpv` and fails the build if `/usr/bin/mpv` is absent, so a fresh
image cannot silently depend on a previous live `dnf5 install`.

## Supplied asset (measured)

| Property | Value |
|---|---|
| Source | `assets/nuxel-preloading-screen.mp4` |
| Bytes | 7,630,092 |
| SHA-256 | `b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1` |
| Container | ISO-BMFF / MP4, `mvhd` duration 6016 ms |
| Video | H.264 High (`avc1`), 1080x1920, 24 fps, 144 frames, yuv420p, tv range, bt709 primaries |
| Audio | AAC-LC, 48 kHz, stereo — present but deliberately not played |
| Decode | `ffmpeg -i ... -map 0:v:0 -f null -` => exit 0 on the build host |
| Runtime path | `/usr/share/nuxel/preload/nuxel-preloading-screen.mp4` |

The asset is packaged byte-for-byte. It is not re-encoded, renamed from
`nuxel-boot-animation.mp4`, or substituted with any other artwork.

## Playback command

The controller runs mpv as a fullscreen Wayland SHM client:

```
mpv --no-config --no-audio --mute=yes --vo=wlshm --fullscreen --no-border \
    --osc=no --osd-bar=no --osd-level=0 --input-default-bindings=no \
    --input-terminal=no --input-vo-keyboard=no --no-input-cursor \
    --cursor-autohide=no --keepaspect=yes --panscan=0 \
    --background-color=#000000 --keep-open=yes --idle=yes --hwdec=no \
    --vd-lavc-threads=4 --really-quiet --no-terminal \
    --log-file=/run/nuxel/preload-cinema-mpv.log \
    --input-ipc-server=/run/nuxel/preload-cinema.sock --title=Nuxel \
    -- /usr/share/nuxel/preload/nuxel-preloading-screen.mp4
```

`--keepaspect=yes --panscan=0` preserves the 9:16 aspect ratio.
`--no-audio --mute=yes` is unconditional; the AAC track is never routed to a
speaker. Player controls and pointer input are disabled. `--keep-open=yes`
holds the final frame if the lockscreen is slower than the clip, and the
controller holds it no longer than `hard_timeout_ms`.

## Readiness gates

| Gate | Source | Required |
|---|---|---|
| Real lockscreen document loaded | `/run/nuxel-launcher-ready` non-empty | yes |
| Phone boot mode | `/run/nuxel-home.state` contains `boot=os` | yes |
| Display bridge healthy | `/run/nuxel-wl-fb.state` has `FRAMES_OK` / `owner=nuxel-wl-fb`, and the fresh `/var/lib/nuxel/display` receipt says `DISPLAY_ON` (a stale receipt from a previous boot is ignored) | yes |
| Touch settled | `/run/nuxel-touch-arm.state` contains an `ARMED_OK` status receipt (ignoring later `TOUCH_POINT` event lines), or an honest `NO_TOUCH_DEVICE` / `SCAN_FAIL` warning | yes, with a bounded unknown grace |

Measured on the S10+ during PWNAGE-31000 bring-up: after the initramfs
animation handed the panel to `nuxel-wl-fb`, `/run/nuxel-wl-fb.state` could
still end in `DISPLAY_SLEEP ... display=off` while `/var/lib/nuxel/display`
said `DISPLAY_ON` and the glass was lit.  The controller therefore treats the
fresh persistent display receipt as authoritative and ignores a receipt whose
mtime predates this boot.

Noncritical services (NetworkManager, Bluetooth, GNSS, audio, optional app
services) are deliberately not gates. The controller never starts or stops
them, never launches applications, and never writes a progress percentage.
The service is `Type=simple`, so it starts concurrently with the rest of
`multi-user.target`; it does not hold the boot transaction open.

## Timing policy

- The real clip duration is 6.016 s. The stdlib `mvhd` parser reports it, and
  mpv's `eof-reached` property remains authoritative.
- `start_timeout_ms` (30 s default) is a **gate wait**, not a fixed delay.  It
  covers the measured initramfs animation handoff (the animation owns the
  panel until ~21 s, then `nuxel-wl-fb` publishes the display receipt).  The
  controller starts playback as soon as the receipt appears.
- `max_display_ms` (20 s default) bounds the moving-video interval. If the clip
  stalls past that bound, mpv is paused on its final frame.
- `hard_timeout_ms` (25 s default) bounds the final-frame hold.  With the
  30 s start wait this keeps the worst-case overlay release before
  `nuxel-fallback.service`'s 60 s launcher wait, so a failed launcher cannot
  race two surfaces. On expiry the controller records the exact readiness
  snapshot and releases the overlay.
- The overlay is released immediately when video EOF and readiness are both
  true; there is no fixed post-readiness sleep.
- If video EOF arrives before readiness, the final frame is held; if readiness
  arrives before video EOF, the clip completes normally.

## Handoff and security

At handoff the controller quits mpv, waits for it to exit (SIGTERM then
SIGKILL), removes the IPC socket, and releases its single-instance lock.  A
one-shot `/run/nuxel/preload-cinema.done` marker (tmpfs, cleared at boot) makes a
later manual `systemctl start` return `ALREADY_RAN` instead of painting the clip
over an unlocked desktop. The
real `pwa/nuxel-home` lockscreen is already underneath the overlay, so there is
no desktop flash and no second lockscreen. The controller never calls the
unlock action, never writes `/dev/fb0`, and never modifies the lockscreen
assets, lockhead, gestures or input routing. `nuxel-wl-fb` remains the single
framebuffer owner. The live console/recovery path is not touched.

## Failure policy

`FALLBACK` receipt and exit 0 for: missing/unreadable/empty asset, optional hash
mismatch, missing player, display not ready, non-phone launch mode, decode
preflight failure, IPC failure, player exit before EOF, display-off during
playback, and any controller exception. A `DUPLICATE` receipt is written when
the single-instance lock is held. In every case the existing lockscreen or
fallback surface remains. The unit is `Restart=no` with a one-attempt start
limit, so a bad decoder cannot restart-loop.

## Packaging

- Phone rootfs builder: installs controller, unit, config, doc and the supplied
  asset; verifies the asset SHA-256 against the config; installs `mpv`; removes
  the duplicate broad `assets/` copy from the static webroot; enables the unit
  only when `nuxel-wl-fb` and `mpv` exist.
- VM builder: installs the controller/config/asset and verifies the same hash;
  enables only when the launcher bridge and `/usr/bin/mpv` exist.
- Rootfs verifier: requires `/usr/bin/mpv`, the controller files and the runtime
  asset, and checks source/image byte parity for the asset.
- Live manifest: `tools/beta/live/nuxel-31000-preload-cinema-manifest.json`
  includes the asset at
  `/usr/share/nuxel/preload/nuxel-preloading-screen.mp4`, mode `0644`, with the
  expected SHA-256 in its file entry and health check. The real planner hash-
  covers the 7.6 MB file before install. No service restart is planned for this
  boot asset; only `systemctl daemon-reload` is deliberate.
- Package metadata: `mpv` is in
  `images/s10plus/packages-manifest.json` and in
  `tools/s10plus/a33/verify-packages.py` essential groups.

## Verification commands

```bash
python3 -m pytest -q tests/pwnage31000
python3 tools/pwnage31000/verify-preload-cinema.py
python3 tools/s10plus/a33/verify-service-graph.py
python3 tools/s10plus/a33/verify-packages.py --validate-manifest
# Dry-run (validates and plans; writes nothing)
python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/nuxel-31000-preload-cinema-manifest.json --json

# Approved live transaction (serial console; the tool stages, SHA-256 verifies,
# installs atomically, runs the health check and rolls back on failure)
sudo python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/nuxel-31000-preload-cinema-manifest.json \
  --dev /dev/ttyACM0 --apply
```

The pytest suite uses a fake mpv/IPC peer. It proves controller behavior and
fallback logic offline; it is not physical-device proof.

Physically measured on the S10+ (2026-10-28):

- first successful boot `c20cd499`: controller start 10:58:32, player start
  10:58:46.815, video EOF 10:58:53.577, handoff complete 10:58:53.745; `PLAYED`,
  6.309 s, `unlock_actions=0`;
- final bound boot `91dfb631` (`hard_timeout_ms=25000`): launcher ready
  11:12:40.784, display handoff 11:12:51.704, player start 11:12:52.914,
  video EOF 11:12:59.658, elapsed 6.290 s; `PLAYED`, `video_eof=true`,
  `unlock_actions=0`;
- mpv software-decoded 1080x1920 H.264 and presented 720x1280 at y=120 on the
  720x1520 output (`wlshm`), with black bars and no dropped-frame messages;
- 40 compositor snapshots covered the boot; frames 22–35 match consecutive
  source frames 009→112 at 24 fps, frames 39–40 are the real lockscreen;
- missing-asset fallback produced `FALLBACK asset-missing` with no mpv process
  and the lockscreen/display bridge still active;
- the normal unlock flow completed at 11:15:03 through `penguin-host-event`
  (`locked=0`); a subsequent manual start returned `ALREADY_RAN`, spawned no
  mpv and left the desktop untouched;
- `multi-user.target` reached 47.972 s on the final bound boot vs 47.905 s
  baseline (+0.067 s); the pre-existing `NetworkManager-wait-online.service`
  is the only failed unit.

## Rollback

Source rollback (the files added/changed by PWNAGE-31000):

```bash
git restore -- \
  images/mkrootfs.sh \
  images/s10plus/build-phone-rootfs-inside-fedora.sh \
  images/s10plus/packages-manifest.json \
  tools/s10plus/verify-fedora-phone-rootfs.py \
  tools/s10plus/a33/verify-packages.py \
  tools/s10plus/a33/verify-service-graph.py \
  tools/beta/run-all-tests.sh
rm -rf services/nuxel-preload-cinema configs/nuxel/boot/preload-cinema.json \
       tools/pwnage31000 tests/pwnage31000 docs/pwnage-31000 \
       tools/beta/live/nuxel-31000-preload-cinema-manifest.json
```

Live rollback.  These files did not exist before PWNAGE-31000, so a full
rollback removes them; the `.nuxel-rollback` copies are intermediate feature
revisions from the deploy transaction, not a pre-feature baseline:

```bash
sudo systemctl disable --now nuxel-preload-cinema.service || true
sudo rm -f /etc/systemd/system/multi-user.target.wants/nuxel-preload-cinema.service
sudo rm -f /usr/lib/nuxel/nuxel-preload-cinema \
           /etc/systemd/system/nuxel-preload-cinema.service \
           /etc/nuxel/boot/preload-cinema.json \
           /usr/share/nuxel/preload/nuxel-preloading-screen.mp4 \
           /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.sha256 \
           /usr/share/nuxel/doc/PWNAGE-31000.md
sudo rm -f /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback \
           /etc/systemd/system/nuxel-preload-cinema.service.nuxel-rollback \
           /etc/nuxel/boot/preload-cinema.json.nuxel-rollback \
           /usr/share/nuxel/preload/nuxel-preloading-screen.mp4.nuxel-rollback \
           /usr/share/nuxel/doc/PWNAGE-31000.md.nuxel-rollback
sudo rm -f /usr/lib/nuxel/*.nuxel-staged /etc/nuxel/boot/*.nuxel-staged \
           /etc/systemd/system/*.nuxel-staged /usr/share/nuxel/preload/*.nuxel-staged
sudo systemctl daemon-reload
```

No BOOT partition, kernel, DTB, recovery, modem or partition is touched.
