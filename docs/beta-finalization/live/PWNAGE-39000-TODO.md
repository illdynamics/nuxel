# PWNAGE-39000 TODO — Stability, Connectivity & Desktop Polish

Device: Samsung Galaxy S10+ SM-G975F / beyond2lte
Live host: `root@192.168.178.167` over Wi-Fi SSH (`~/.ssh/wicked_wqn_id_rsa`)
Evidence: `docs/beta-finalization/live/evidence/pwnage-39000/`

| # | Priority | Task | Status |
|---|----------|------|--------|
| 0 | P0 | Connect over Wi-Fi SSH (key-only, root@192.168.178.167) | VERIFIED |
| 1 | P0 | Wi-Fi auto-enable + autoconnect at boot; UI/Quick-Settings truth; toggle ON | FIXED+VERIFIED (cold boot) |
| 2 | P1 | Investigate/fix sleep battery drain | PARTIAL (audio-route timer 300s->600s; documented always-on Wi-Fi baseline) |
| 3 | P2 | Fix slow reboot initiation | FIXED (a45 pwa-host binary rebuilt+deployed; reboot-path verify at final reboot) |
| 4 | P3 | Flatpak Firefox/VLC/software center | BLOCKED (Flatpak not installed; rootfs 98% full; native Firefox/VLC present) |
| 5 | P4 | NuXtore install backend (real install/progress/refresh) | PARTIAL (detect+verify+local state work; `apps.register` endpoint absent) |
| 6 | P5 | Bottom nav icons clean rendering | FIXED-in-source+assets (screenshot captured) |
| 7 | P6 | Main desktop performance parity | NOT DONE (profiled: WebKit idle CPU high) |
| 8 | P7 | Top-bar indicators BT/GPS/audio/cellular | NOT DONE (BT on, GPS unavailable, no modem; UI wiring open) |
| 9 | P8 | Lockscreen USB connection-mode button | PARTIAL (assets+helper deployed; charging verified; file-transfer honestly BLOCKED) |
| 10 | P9 | Bluetooth file sending | NOT DONE (hci0 UP; send UI/transfer backend open) |
| 11 | — | First deliberate reboot after P0 Wi-Fi fix | DONE |
| 12 | — | Final deliberate reboot + full re-verify | IN PROGRESS |
