# PWNAGE-44000 — NUXEL HOME, HARDWARE CONTROLS, GALLERY & FILE SHARING

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel — custom Fedora-based ARM64 mobile Linux  
**Primary UI:** `pwa/nuxel-home` + app PWAs  
**Display path:** Phoc/Wayland headless + Pixman/shared-memory capture + single-owner `/dev/fb0` output bridge  
**Mission type:** implementation, repair, performance work, regression testing and safe device deployment

## MISSION

Deeply inspect the current repository and, when the existing SSH deployment target is already configured, the live S10+. Implement the following fixes in the real source, not as mock UI:

1. **Home icon movement:** repair long-press-and-drag so an app icon can be picked up, moved, reordered and dropped on the same or another desktop. Keep the existing Add/Remove from Home behavior. Fix pointer capture, pointer cancellation, touch-action and hit-testing correctly for WebKitGTK touch input.
2. **Performance:** make the lockscreen, app drawer/window transitions, Quick Settings, Home Settings and Files scrolling/rendering noticeably faster on the S10+ software-rendered fbdev path. Measure before/after. Keep the compositor and the single framebuffer owner intact.
3. **Power menu:** restore the complete extended menu on a long Power press. The live image builds the A34 button manager, but its compiled FSM menu has 11 entries while `configs/nuxel/input/button-fsm.json` and the A33 test source define 15. Make the active A34 build, config, OSD and tests agree. Include Restart, Power off and the existing one-shot reboot modes. Preserve the reboot gate, cooldown, hourly cap, rollback-path requirement and `NO_FLASH_INVARIANT`; never bypass them or enter Recovery/Download Mode.
4. **Screenshot:** keep Power + Volume Down as the screenshot chord. Repair the helper packaging mismatch: A45 PWA host expects `/usr/lib/nuxel/nuxel-screenshot`, while the image builder currently installs `nuxel-wl-snapshot` at `/usr/local/bin/nuxel-wl-snapshot`. Build/install a compatible helper or update the host to the verified installed binary. Capture via Wayland screencopy (never a second `/dev/fb0` owner), save a PNG in `/home/nuxel/Gallery`, and show a visible success/failure acknowledgement. The Gallery must index the saved image.
5. **Gallery video thumbnails:** stop creating a WebKit `<video>` decoder for every grid thumbnail. Generate/cache real still thumbnails server-side with an available media decoder, expose a safe authenticated thumbnail route, and display those stills in the grid. Keep actual playback separate; if a codec cannot be played by WebKit, retain the poster and report the real playback limitation honestly.
6. **Files sharing:** speed up large-directory rendering/scrolling. Add a **Send** action for selected files, with a working Bluetooth/BlueZ OBEX send flow, device selection, progress and truthful success/failure. Leave future share methods visibly disabled as “Coming soon”; do not pretend they work.
7. **Notes and widgets:** make Notes saves durable and visible to Home widgets. Fix the desktop numbering mismatch: launcher `currentPage` is zero-based, while the Home Settings desktop selector is one-based. Store/convert this consistently. Add a real sticky Notes widget to desktop 2, allow adding/removing, selecting a note, resizing and repositioning, and persist all changes. Ensure the Notes app’s Bridge storage and the Home widget model stay synchronized.
8. **Flashlight:** make the Quick Settings flashlight action real through one safe hardware owner/provider. The current Quick Settings handler says unavailable; the button manager only writes `/run/nuxel/flashlight.request` and sends a host action. Do not write arbitrary LED sysfs paths from JavaScript. Reuse the configured LED policy, camera arbitration, bounded on-time and explicit-off behavior. If no physical torch class is available, show `NOT_SUPPORTED_ON_DEVICE` rather than a fake ON state.
9. **Status icons and expanded Quick Settings:** add accurate top-bar Location and sound-mode icons; add a compact USB cable icon with `file`, `term` or `chrg` text for the actual state; add charging/USB/console indicators in expanded Quick Settings; add a lightning bolt inside the battery only while actively charging. Use the existing canonical providers, not guessed state.

## IMPORTANT REPOSITORY FINDINGS — DO NOT IGNORE

- The S10+ image builder is `images/s10plus/build-phone-rootfs-inside-fedora.sh`. It compiles `tools/s10plus/a34/nuxel-button-manager.c`, `tools/s10plus/a45/nuxel-pwa-host.c`, `tools/s10plus/a34/nuxel-wl-fb.c` and `nuxel-wl-snapshot`. The installed systemd unit executes `/usr/lib/nuxel/nuxel-button-manager`.
- `tools/s10plus/a34/nuxel-button-fsm.h` has an 11-entry power menu. The JSON and A33 FSM have 15 entries, adding Back, Forward, Stop and Reload launcher. Existing button-FSM tests inspect A33, not the A34 source compiled into the image. Add active-build parity tests.
- A45 PWA host hard-codes `SHOT_BIN` as `/usr/lib/nuxel/nuxel-screenshot`. The image build does not currently install that path. `tools/s10plus/a68/nuxel-screenshot.c` and A34 `nuxel-wl-snapshot.c` are candidate helpers; compare their CLI/output contract before wiring one in.
- `pwa/nuxel-home/js/launcher.js` already has a 450 ms long-press drag implementation. Repair the existing pointer lifecycle; do not bolt on a second drag framework.
- `launcher.currentPage` starts at `0`. Widget UI currently stores desktop numbers like `2` and calls `renderPage(currentPage)`. The current widget test can pass by manually calling `renderPage(2)` even though the actual second desktop is page index `1`. Correct the model and test the real launcher lifecycle.
- `pwa/nuxel-home/js/widgets.js` only renders a basic Notes card; it has no full edit/resize/reposition interaction. `home-settings.js` rebuilds its panel with `innerHTML` on every open.
- `pwa/nuxel-apps/files/js/files.js` rewrites the entire file grid and adds a click listener to each item. No Send/Bluetooth action exists.
- Gallery is `pwa/nuxel-apps/photos`, app ID `org.nuxel.Photos`. `photos.js` currently puts `<video preload="metadata">` in each video grid cell; a browser decoder error replaces it with “Video could not be decoded”. `pwa_store.storage_media_list()` returns metadata only; there is no thumbnail API yet.
- `services/nuxel-bridge/src/system_indicators.py:get_indicators()` already exposes canonical `charging`, `usb_data`, `live_console`, `console_transports`, `file_transfer`, `connection_mode` and Bluetooth state. File transfer is active only after the endpoint really activates; a selected mode is not proof of active transfer. Reuse this contract for the lockscreen and expanded Quick Settings.
- The status bar has no Location, sound-mode or USB status cells. It already adds a `.charging` class to the battery icon, but the CSS has no lightning treatment. `_acceptBatteryLevel()` also currently treats `Full` as active charging despite a contradictory comment; correct this.
- Location controls already exist in Quick Settings. Do not label a service-enabled state as a satellite GPS fix: the S10+ BCM4773 GNSS path is documented as firmware-blocked unless actual GNSS evidence proves otherwise.
- Sound-mode cycling already records `normal → vibrate → silent` in `/var/lib/nuxel/audio/sound-mode`. The button manager mutes for vibrate and silent, but explicitly does not claim that vibrator hardware works. Keep the icon truthful and verify a real haptic owner before claiming vibration.
- Flashlight diagnostics are in `tools/s10plus/a33/nuxel-led-diag.sh` and `configs/nuxel/leds/leds.json`. Offline policy tests do not prove that the physical LED illuminates.
- The display is a Wayland/Pixman/shared-memory pipeline. `nuxel-wl-fb` is the single `/dev/fb0` owner. Never make PWAs or helpers open/write `/dev/fb0`, add a second framebuffer writer, or assume a DRM/EGL GPU path.

## EXECUTION ORDER

1. Inventory, backups, branch/status, live device and baseline performance. Create `docs/beta-finalization/live/PWNAGE-44000-TODO.md` and an evidence directory.
2. Fix and browser-test Home icon drag/reorder.
3. Fix Notes persistence, widget desktop mapping, sticky widget, resize/reposition.
4. Profile and optimize lockscreen, drawer/window, Quick Settings, Home Settings and Files for WebKitGTK + Pixman/fbdev.
5. Restore the full extended A34 hardware power menu and verify all actions/gates.
6. Repair screenshot helper build/install, chord, OSD acknowledgement and Gallery indexing.
7. Implement video-thumbnail generation/cache and Gallery presentation.
8. Implement safe Bluetooth file sharing and large-directory rendering improvements.
9. Implement the safe flashlight owner and wire Quick Settings.
10. Implement top-bar/expanded-QS status indicators and charging bolt.
11. Run all relevant existing tests plus new A34-targeted tests; build the ARM64 image/artifacts; deploy non-destructively over the already-configured Wi-Fi SSH connection if available; verify on the physical S10+.

## PERFORMANCE REQUIREMENTS

The S10+ is CPU-rendered through the Wayland headless/Pixman path and a shared-memory framebuffer bridge. Prefer fewer DOM replacements, delegated events, bounded/lazy media work, cached assets, short/opacity/transform-only transitions and reduced repaint regions. Avoid backdrop blur, expensive filters, large soft shadows, per-frame layout reads, continuous idle animation and duplicated polling. Pause hidden-screen timers and stop polling when a panel is closed. Preserve touch momentum where needed and make drag capture robust.

Measure a baseline and a post-fix run for: lockscreen ready/interaction, drawer open, Quick Settings open/expand/close, Home Settings open/close, Files directory load and scroll, Gallery grid render. Record p50/p95 timings, dropped frames or an equivalent frame-time estimate, CPU usage and any long tasks. Target at least a 25–30% improvement on the slow paths without regressions elsewhere; prioritize stable interaction at the display bridge’s practical frame rate. Do not claim a speedup without before/after evidence.

## SAFETY / DEPLOYMENT RULES

- Preserve user files, photos, notes, configs, app data and SSH access. Back up each modified live file before replacement.
- Do not use Heimdall, Odin, fastboot, bootloader flashing, raw partition writes, `dd` to block devices, sysrq reboot or forced reboot.
- Never weaken or bypass `/etc/nuxel/buttons/reboot-gate.json`, its policy AND, cooldown, hourly cap or rollback-path checks. Recovery and Download Mode remain refused by `NO_FLASH_INVARIANT`.
- Use the existing single Wayland/Pixman/framebuffer ownership chain. No second `/dev/fb0` process.
- Never fake state. Distinguish `UNKNOWN`, `OFF`, selected-but-not-active and genuinely active hardware states.
- Do not assume a device IP or credentials. Use the SSH target already configured by the operator. If none is discoverable, complete repo-side work and provide exact deployment commands without scanning networks or inventing a host.
- Reboot only through the existing gated userspace flow and only when required. Stop and report a gate refusal; never bypass it.

## DEFINITION OF DONE

- Long-press drag works on physical touch, including same-page reorder, cross-page move, pointer cancel rollback and persistence after restart.
- Desktop-2 Notes widget appears on the second actual desktop, loads a selected note, reflects edits, saves, resizes and moves; app saves survive a restart.
- Lockscreen, drawer/window, QS, Home Settings and Files are measurably smoother on the real S10+ software-rendered path.
- Full 15-entry configured extended power menu is actually compiled into the S10+ image and each entry has a tested/valid action or an explicit safe refusal.
- Power+Volume Down captures a real PNG, displays a confirmation and the image appears in Gallery.
- Video grid cells show still thumbnails without starting a decoder per cell; playback behavior remains truthful.
- Files can send selected files over Bluetooth to a chosen device with real transfer completion/error feedback; future share methods are disabled placeholders.
- Flashlight toggles through the actual safe owner and reports unsupported honestly when hardware is absent.
- Location, sound, USB, console, transfer and charging indicators reflect canonical backend state, do not overlap, and the battery lightning bolt appears only during active charging.
- Existing regressions remain green; newly added tests cover the defects described above; final live deployment is verified or an exact, safe deployment handoff is provided.

**Do the implementation, not merely an audit. Leave a clear commit/diff, test evidence, device deployment record, rollback notes and final PWNAGE-44000 completion report.**
