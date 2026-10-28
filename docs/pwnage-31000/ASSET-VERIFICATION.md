# PWNAGE-31000 supplied asset — verification record

## File

```
assets/nuxel-preloading-screen.mp4
size    7,630,092 bytes
sha256  b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1
```

The file was supplied by the owner and is packaged unchanged. It is not the
existing `assets/nuxel-boot-animation.mp4` (whose pinned SHA-256 is
`280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c`).

## ffprobe

```
Stream #0:0 video: h264 (High), yuv420p(tv, bt709, progressive), 1080x1920,
                 24 fps, 144 frames, duration 6.000 s
Stream #1:1 audio: aac (LC), 48000 Hz, stereo, duration 6.016 s
Format duration: 6.016 s; bit rate: 10,146,398 bit/s
```

## Decode check

```
$ ffmpeg -v error -i assets/nuxel-preloading-screen.mp4 -map 0:v:0 -f null -
$ echo $?
0
```

## Policy consequences

- Timing is based on the real 6.016 s timeline, not an assumed six seconds;
  mpv EOF remains authoritative.
- The AAC track is present. The controller unconditionally passes `--no-audio
  --mute=yes`; no boot audio is invented and an audio-device failure cannot
  block playback or the lockscreen.
- The 1080x1920 portrait frame is scaled with aspect ratio preserved.
- Software H.264 decoding through the packaged mpv/FFmpeg-free chain is the
  selected path; no hardware decoder or additional graphics path is assumed.

## Packaging verification

The SHA-256 above is pinned in three places and cross-checked by
`tools/pwnage31000/verify-preload-cinema.py`:

1. `configs/nuxel/boot/preload-cinema.json` (`asset_sha256`);
2. the image builders, which abort on a mismatch before producing a rootfs;
3. `tools/beta/live/nuxel-31000-preload-cinema-manifest.json`, whose file entry
   and health check both carry the hash.

The deploy planner computes the staged source hash independently and the
installer re-checks it on the device before the atomic rename.
