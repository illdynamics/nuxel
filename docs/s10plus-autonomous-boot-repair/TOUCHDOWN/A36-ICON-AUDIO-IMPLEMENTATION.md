# A36 — Nuxel supplied icons + audio cues (source patch)

This is SOURCE-level integration. **Live device deployment, speaker audibility, and physical haptics remain unverified.**

## Implemented

- The supplied navigation PNG files are loaded in Back/Home/Recents, with visual glyph fallback only when an image actually fails. The existing app registry uses the supplied application icon assets, and Quick Settings uses the supplied Quick Settings icons.
- `images/s10plus/build-phone-rootfs-inside-fedora.sh` now copies the full `/nuxel/assets` tree to `/usr/share/nuxel/assets` (the `/assets/...` HTTP URL root), and stages the owner's MP3 files, Python audio helper, and boot unit. It installs `mpg123` from Fedora's package repositories.
- `nuxel-boot-sound.service` waits for the bridge JSON receipt (`owner=ui`, `stage=LAUNCHER_DISPLAY_OWNER`), then plays `nuxel-boot-audio.mp3` once per boot at **44% MP3 decoder PCM gain** (`mpg123 -f 14418`). It never changes the hardware mixer and keeps the existing **25% S10+ audio bring-up ceiling**. Therefore *actual amplifier output isn't 44% of theoretical full hardware output*; this is deliberate safety policy until the speaker signal chain is verified.
- The current A34 button manager spawns an optional, non-blocking sound helper **only after successful ALSA playback-volume changes**. The helper plays `nuxel-pow.mp3` at 100% decoder PCM gain through the **already-selected mixer level**, without re-scaling it a second time. It skips zero volume, silent/vibrate mode and overlapping tones.
- The new manifest extension plans deployment of the UI's **24 actually referenced** icons/MP3 resources (to avoid hundreds of unnecessary 128-byte-chunk USB transfers); the rootfs builder includes the complete packs for the next clean image. Boot-unit + sound helper + previously unlisted haptics sources are staged separately without modifying the protected legacy manifest groups.
- A standalone Python mock-player test checks event timing, 44% scaling, one-shot behavior, and volume cue semantics.

## Deployment and proof

1. Back up live phone files and record hashes. Do not touch partitions.
2. Install/update the current PWA HTML, JS, CSS, and actual referenced PNGs to the verified webroot. Verify HTTP 200 and physically inspect nav/quicksettings/app icons.
3. Install `mpg123` and `/usr/libexec/nuxel/nuxel-sound-cue`, and `nuxel-boot-sound.service`; run `systemctl daemon-reload && systemctl enable nuxel-boot-sound.service`.
4. Build AArch64 `nuxel-button-manager` from patched `tools/s10plus/a34/nuxel-button-manager.c` with ALSA dev headers. Validate ELF architecture. Back up and atomically install it; restart only the affected unit.
5. Trigger a volume-up/down action and inspect `/var/log/nuxel/sound-cues.log`; confirm the owner **heard** the `nuxel-pow.mp3` cue at the adjusted level. No log entry counts as speaker audibility.
6. During one safe normal Nuxel boot, confirm the soundtrack starts **only after** the first launcher ownership receipt. Confirm once-per-boot, 7.7s duration, sane output level and zero repetition on bridge restart.
7. Verify vibration and haptic intensity through the chosen single vibrator owner. Don't enable a second sysfs writer blindly.
8. In case of unexpected audio/graphical behavior, restore previous files and restart services; never reflash the phone.

## Offline test commands

`python3 tools/s10plus/a34/tests/test-sound-cues.py`

`python3 tools/beta/live/tests/test_live_deploy_plan.py`

`bash tools/s10plus/a34/tests/run-a34-tests.sh`

`python3 -m py_compile tools/s10plus/a33/nuxel-sound-cue.py`

`bash -n images/s10plus/build-phone-rootfs-inside-fedora.sh`

The Fedora image build and actual ARM64 hardware audio remain pending until executed on a suitable host and the S10+.
