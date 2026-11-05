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

- `tests/pwnage80000/test_pwnage80000.py`: **93 passed, 0 failed**
- `pwa/nuxel-apps/doom/tests/test-doom.js`: **45 passed, 0 failed**
- `pwa/nuxel-home/tests/test-zoom-policy.js`: **7 passed, 0 failed**
- `pwa/nuxel-apps/nuxtore/tests/test-catalog.js`: **18 passed, 0 failed**
- `pwa/nuxel-apps/nuxtore/tests/test-catalog.py`: **18 + 12 passed, 0 failed**
- `services/nuxel-bridge/test-doom-assets.py`: **16 passed, 0 failed**
- `nuxtore-verify.py --root .`: **all signed packages verified**; unsigned demo correctly refused
