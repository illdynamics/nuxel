# PWNAGE-80000 — Acceptance Matrix

Legend: **PASS-LIVE** = exercised on `root@192.168.178.167`; **PASS-OFFLINE** = deterministic source/packaging test; **LIMITED** = code path/runtime surface verified, but the destructive or physical action was not executed from SSH.

| Area | Portrait | Landscape | Reverse portrait | Reverse landscape | Result |
|---|---|---|---|---|---|
| Drawer default 3 columns | 3 | 3 | 3 | 3 | PASS-LIVE |
| Drawer horizontal overflow | none | none | none | none | PASS-LIVE |
| Zoom viewport scale | 1 | 1 | 1 | 1 | PASS-LIVE via `visualViewport` |
| Orientation transform verified | normal | 270 | 180 | 90 | PASS-LIVE |

| Lifecycle / input case | Evidence | Result |
|---|---|---|
| Keyboard open + single Back | `back:keyboard-dismiss`, keyboard 0, app stays ACTIVE | PASS-LIVE |
| Back in Calendar editor | `back:pwa-app-control`, editor hidden | PASS-LIVE |
| Back in Calendar keypad | keypad closes | PASS-LIVE |
| Back at Calendar root | `back:pwa-at-root-graceful-close`, app CLOSED | PASS-LIVE |
| Back at Doom root | app CLOSED, hidden pause control not clicked | PASS-LIVE |
| Long Back force-kill | `app:force-killed`, overlays 0 | PASS-LIVE |
| Force-kill with keyboard open | keyboard 1 → 0, overlays 0 | PASS-LIVE |
| Recents swipe left PWA | `native=0`, graceful close path | PASS-LIVE |
| Recents swipe right | `force:recents-swipe-right`, overlays 0 | PASS-LIVE |
| Overlay cleanup after close | `frames=0, iframes=0, powerMenus=0, folderSheets=0` | PASS-LIVE |
| Desktop input after close | drawer opened with 45 children | PASS-LIVE |
| Calendar numeric/time entry | `09:30`, keypad open/close, keyboard 0 | PASS-LIVE |
| Calendar triple buttons | navdock `visible:true, mapped:true` | PASS-LIVE |
| Calendar init regression | `bound:true`, 42 day cells | PASS-LIVE |
| Power menu input region | `OSD_INPUT interactive=1 rows=16` | PASS-LIVE |
| Power menu single instance | one `nuxel-osd`, duplicate open still one process | PASS-LIVE |
| Power menu screenshot | Gallery count 26 → 27 | PASS-LIVE |
| Power menu Lock | lock state true, display off, unlock restored | PASS-LIVE |
| Power menu Back | `MENU_SELECT id=back` | PASS-LIVE |
| Recovery/Download refusal | `MENU_REFUSED … NO_FLASH_INVARIANT` | PASS-LIVE |
| Restart backend | `REBOOT_ACCEPTED` 133 ms after spawn | PASS-LIVE |
| Reboot UI/backend verdict | Settings polls `power-action.result`; native OSD publishes accepted | PASS-LIVE / PASS-OFFLINE |
| Suspend | code/gate path verified; not executed to preserve SSH | LIMITED |
| Power off | code/gate path verified; not executed to preserve SSH | LIMITED |
| Blue rectangle samples | no isolated stale top band at 0.15/0.5/1/5/11 s | PASS-LIVE |
| Zoom gestures disabled | all-frame policy, GTK capture denial, magnification/zoom pinned | PASS-OFFLINE + host runtime log |
| Four-orientation changes | authoritative orientation daemon, transforms verified | PASS-LIVE |
| Physical finger rotation | accelerometer unavailable on this image | LIMITED |

## Offline suites

- `tests/pwnage80000/test_pwnage80000.py`: **96 passed, 0 failed**
- `pwa/nuxel-apps/doom/tests/test-doom.js`: **45 passed, 0 failed**
- `pwa/nuxel-home/tests/test-zoom-policy.js`: **7 passed, 0 failed**
- `pwa/nuxel-apps/nuxtore/tests/test-catalog.js`: **18 passed, 0 failed**
- `pwa/nuxel-apps/nuxtore/tests/test-catalog.py`: **18 + 12 passed, 0 failed**
- `services/nuxel-bridge/test-doom-assets.py`: **16 passed, 0 failed**
- `nuxtore-verify.py --root .`: **all signed packages verified**; unsigned demo correctly refused


## Continuation rows (post-reboot hardening)

| Case | Evidence | Result |
|---|---|---|
| Boot cue fresh path | `start_rc=0`, `Result=success`, warm-up helper still alive | PASS-LIVE |
| Boot cue after full reboot | `nuxel-boot-sound.service` inactive/dead, `Result=success`, `KillMode=process` | PASS-LIVE |
| Failed units after reboot | `systemctl --failed` empty | PASS-LIVE |
| Wayland restart rebind | before `WL_DISPATCH_FAIL errno=32`; after `FRAMES_OK display=on` | PASS-LIVE |
| App-close native focus | `HOST_HOME_REFOCUS active=1 view_focus=1` | PASS-LIVE |
| App-close overlays/keyboard | frames/iframes/powerMenus/folderSheets 0; keyboard 0 | PASS-LIVE |
| Desktop after close | drawer opened, 45 items, 3 columns | PASS-LIVE |
| Calendar post-reboot Back chain | keyboard-dismiss → app-control ×2 → root graceful close | PASS-LIVE |
| Calendar navdock with keyboard | `visible:true`, `mapped:true`, keyboard 1 | PASS-LIVE |
| Recents swipe left/right post-reboot | graceful-start / force-killed | PASS-LIVE |
| Power menu post-reboot | 1 OSD, interactive 16 rows, screenshot 27→28, back closes | PASS-LIVE |
| Final reboot acceptance | `REBOOT_SPAWNED` → `REBOOT_ACCEPTED` +102 ms | PASS-LIVE |
| Final reboot target | selection 15:29:47.746Z → reboot.target 16:29:51.640 CET ≈3.9 s | PASS-LIVE |
| Post-reboot service matrix | Wayland, wl-fb, buttons, web, HTTP bridge, orientation all active | PASS-LIVE |
| Post-reboot orientation | portrait, effective 0, applied True | PASS-LIVE |
| Post-reboot zoom policy | all-frames default deny; guard installed | PASS-LIVE |
| Post-reboot Doom package | signed catalog verifies; 4 WADs; only org.nuxel.Doom exposed | PASS-LIVE |
| Blue rectangle after close | top-500 mean diff 0.09; no >80% blue rows | PASS-LIVE |
| Physical touch injection | still unavailable via phoc no-udev hotplug; UI FIFO/Recents harness used | LIMITED |
| Swipe-down keyboard gesture | button-manager code path verified; no physical injection | LIMITED |
| Suspend / power-off | gate/backend shared with restart; not executed to preserve SSH | LIMITED |
