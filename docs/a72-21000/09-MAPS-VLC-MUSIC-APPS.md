# NUXEL A72 / 21000 — 09-MAPS / VLC / MUSIC (live)

## Package manager recovered
dnf5 5.2.18.0 installed (10-package additive bootstrap, GPG-verified) and
verified working: `dnf5 repolist` + `dnf5 list --available alsa-utils` resolve
against Fedora 43 aarch64.

## VLC (installed, root limitation recorded)
- `dnf5 install vlc` (no weak deps) → vlc 3.0.24 + vlc-gui-qt + qt6-qtbase(-gui)
  + qt6-qtsvg + vlc-libs + vlc-cli (30 packages, signed).
- `vlc.desktop` present (Exec=/usr/bin/vlc). `vlc --version` refuses: "VLC is
  not supposed to be run as root." The Nuxel session runs as root, so VLC needs
  a non-root wrapper or the documented `--no-...` mitigation (none is
  safe/appropriate on this root session). Recorded as a genuine limitation;
  VLC remains installed.

## Separate music player (mpv, runtime verified)
- `dnf5 install mpv` (no weak deps) → mpv 0.40.0 + FFmpeg-free codec chain
  (105 packages, signed). `mpv.desktop` present.
- `mpv --version` → mpv v0.40.0, libplacebo v7.351.0.
- `mpv --no-video --ao=null /tmp/nuxel-test-tone.wav` → decodes 44100 Hz S16
  WAV and exits cleanly: **decode/runtime PASS_DEVICE_RUNTIME**.
- Audible output remains firmware-blocked (see 06-AUDIO); decode is reported
  separately from heard playback, never faked.

## Maps
Unchanged from prior A72 run (OSM one-tap tiles + Nominatim search, hash-verified
on device). Online tile path verified reachable earlier this session.
