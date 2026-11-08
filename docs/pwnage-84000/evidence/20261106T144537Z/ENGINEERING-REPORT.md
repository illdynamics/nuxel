# PWNAGE-84000 (+82000/83000) — Engineering Report

Date: 2026-11-06 (session). Device: SM-G975F (beyond2lte), Linux 4.14.253-gf7194c1d15ed-dirty aarch64, Fedora 43.
SSH: root@192.168.178.167 via ~wicked/.ssh/wicked_wqn_id_rsa (IdentitiesOnly=yes). Helper's pinned 10.20.30.16 was stale; the owner-supplied Wi-Fi host was used. id -u == 0.

## What was already in place (verified, not re-imagined)
- Sound system (81000): nuxel-soundd + nuxel-soundctl central manager, PipeWire 1.4.11, sink "S10+ speaker (RDMA1)", source "S10+ microphone (WDMA1)". Volume cue latency measured 17.99ms (target <100ms).
- Clock (81000) had a page-owned/legacy daemon; the 84000 durable scheduler existed in source but was NOT deployed.
- Flatpak: Legcord 1.3.1 + Vesktop 1.6.8 installed under /var/lib/flatpak/app/*/aarch64/ (ARM64 native). Vesktop was already running.
- Theme: gsettings color-scheme=prefer-dark, gtk-theme=Adwaita-dark; no empty GTK_THEME override.

## Root causes found & fixed this session
1. MICROPHONE (82000 §19 / 84000 §11): capture works but gain was unity (IN3L Digital Volume=128 == 0 dB), so voice was buried at ~-43.7 dBFS noise floor; L/R channels were identical (both fed from ISRC1INT1). Fixed: pin +16 dB default (IN3L=160) in nuxel-mic-route.sh. Measured: 0dB->-42.2dBFS, +16dB->-26.6dBFS, +24dB->-18.5dBFS (linear, proving real hardware preamp). Channel identity is mono-duplicated (documented, not a fake stereo).
2. V4L2 PROBE (83000 §B): old probe used single-planar type 1 on nodes advertising V4L2_CAP_VIDEO_CAPTURE_MPLANE. Rewrote nuxel-v4l2-probe.py with ctypes-correct ABI and mplane type 9 + v4l2_pix_format_mplane + v4l2_plane. Verified on phone: FIMC-IS nodes now correctly classified mplane (e.g. video111=exynos-fimc-is-30c). ENUM_FMT returns empty formats until media/firmware setup (documented next step).
3. STALE TESTS: tests/pwnage82000 expected 82000 IDs (walk-pad/.dpad/900ms dwell) vs the 84000 contract (move-stick/aim-stick/.thumbstick/1000ms). Updated; full suite now green.

## Deployed to phone (backup /var/backups/nuxel/p84000-20261106T145512Z, 83MB)
- PWA tree -> /usr/share/nuxel/pwa/{nuxel-home,nuxel-apps,nuxel-common} (76 files incl. new desktop-layout.js, lockscreen-clock.js, mic/sound/appearance-settings.js, media-downloader.js)
- Bridge -> /usr/lib/nuxel/nuxel-bridge/ (api.py + mic_provider + flatpak/pwa/system_indicators providers)
- nuxel-clockd.py (84000 scheduler), nuxel-soundd.py, nuxel-mic-route.sh, nuxel-software, nuxel-app-prewarm(+.service), nuxel-tri-link-session
- assets/nuxel-alarm.png + nuxel-timer.png -> /usr/share/nuxel/assets/
- Restarted: nuxel-clockd, nuxel-soundd, nuxel-bridge, nuxel-mic-route. Enabled nuxel-app-prewarm.

## Verified results (physical phone)
- ALARM E2E: create-alarm(15:57) -> clockd migrated legacy schedule -> FIRED (occ-..., token clock-alarm-...) -> soundd last_cue_action=alarm, latency 19.68ms -> dismiss -> delete. PASS.
- TIMER E2E: legacy running timer migrated and fired (RING kind=timer) on service restart; stop-timer dismissed. PASS.
- MIC: real PCM captured (arecord hw:0,13), gain control proven linear and persisted. PASS (intelligibility needs owner speech; signal path + gain verified).
- DOWNLOADER: yt-dlp 2026.08.19 + ffmpeg-free 7.1.5 (aarch64, libmp3lame/libfdk_aac). Real `-t mp3` job: Wikimedia Commons webm -> MP3, ffprobe format_name=mp3 duration=12.07s, saved in ~/Downloads. PASS. LIMITATION: no node/deno JS runtime -> YouTube extraction degraded ("No supported JavaScript runtime"); non-YouTube/direct extractors work.
- THEME: prefer-dark + Adwaita-dark active, no empty GTK_THEME override. (Software/Archive visual confirmation requires on-screen interaction.)
- NOTES: ~/Notes exists, pwa_store.py provides atomic notes_list/save/delete rooted at ~/Notes with path-escape protection. note-p82000.json present.
- CHAT CLIENTS: Legcord + Vesktop aarch64 flatpak refs confirmed; Vesktop process running as nuxel user.
- PERFORMANCE: native GTK spawn ~0.48s; flatpak `--command=true` sandbox init ~30.7s x3 (consistent = fixed ~30s timeout, post-context sandbox/dbus-proxy phase). Prewarm service (fontconfig/icon/desktop caches) enabled and run. The 30s flatpak stall needs further root-cause (portal/gvfs), flagged.

## Known limitations / needs owner
- Flatpak 30s init stall root cause not yet resolved.
- YouTube needs node/deno JS runtime for extraction.
- Camera: probe corrected; real streaming still requires firmware/setfile/media-graph steps in full-pwnage-83000.md.
- Software/Archive dark rendering + Doom touch feel + lockscreen gestures require on-device visual/touch confirmation.
- Legcord/Vesktop login left to owner (no credentials used/stored).

## Rollback
Full backup at /var/backups/nuxel/p84000-20261106T145512Z. Restore e.g.:
  cp -a /var/backups/nuxel/p84000-<ts>/pwa/nuxel-apps/. /usr/share/nuxel/pwa/nuxel-apps/
  cp -a /var/backups/nuxel/p84000-<ts>/bridge/nuxel-bridge/. /usr/lib/nuxel/nuxel-bridge/
  cp -a .../bin/nuxel-clockd /usr/libexec/nuxel/nuxel-clockd  (then systemctl daemon-reload && restart services)
Mic gain: amixer -c 0 cset name='IN3L Digital Volume' 128 (restore 0 dB).
