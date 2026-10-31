# PWNAGE-44000 TODO / STATUS

**Mission:** NUXEL HOME, HARDWARE CONTROLS, GALLERY & FILE SHARING
**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820
**OS:** Fedora 43 ARM64 (Nuxel), kernel 4.14.253
**Live target:** root@192.168.178.167 (Wi-Fi SSH, key ~/.ssh/wicked_wqn_id_rsa)
**Started:** 2026-10-31
**Base commit:** dfd9e76 (feature/pwnage-43000-final, pre-existing dirty tree preserved)

Status: [ ] TODO  [~] WIP  [x] DONE  [B] BLOCKED/EXTERNAL

- [x] Inventory, live baseline, backups (`/root/pwnage-44000/backup-20261031T054927Z`)
- [x] Home icon long-press drag/reorder + pointer capture/cancel
- [x] Notes durable saves + widget desktop mapping (1-based) + sticky widget
- [x] Performance: Files progressive grid, QS/Home Settings polling/caching, idle animation guard
- [x] A34 15-entry extended power menu parity (live OSD confirms 15)
- [x] Screenshot helper build/install path + real PNG in Gallery + toast
- [x] Gallery server-side video thumbnails + cache
- [x] Files large-directory rendering + Bluetooth OBEX Send flow
- [x] Safe flashlight provider (real torch-sec1 on/off, bounded/off/camera/thermal)
- [x] Status bar Location/sound/USB + charging bolt; expanded QS indicators
- [x] Offline regression gate (new + existing) all green
- [x] Non-destructive live deployment of PWA, backend and ARM64 binaries
- [x] Live power-menu, refusal, screenshot, flashlight and thumbnail proofs
- [ ] Physical owner touch test of drag/widgets/BT peer transfer (needs receiver)
- [x] Final gated reboot + post-boot verification (boot 2026-10-31 06:56:46)
