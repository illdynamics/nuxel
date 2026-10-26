# 🐧 NUXEL A70 — OPERATION PENGUIN INDICATOR PRECISION 19000
## ULTIMATE GPT-5.6 SOL HIGH ENGINEERING MISSION — THREE ICONS, TWO REAL FIXES, ZERO REGRESSIONS

> Mission type: **surgical lockscreen-only change** on the running Samsung Galaxy S10+ SM-G975F (Exynos 9820), Fedora ARM64 Nuxel, current Linux 4.14 vendor kernel. **Do not redesign the lockscreen, rebuild the OS, touch boot/kernel/firmware, or undertake unrelated fixes.** The existing indicator artwork and lockscreen already function; restore the exact requested layout and correct USB-data truthfulness. Work in the current Nuxel Git repository on the user's Fedora laptop, using the current physical phone and secure USB Live Console when available. Preserve a reversible device deployment path.

## 0. Owner's exact instructions — acceptance contract

The following three existing lockscreen icons are ALREADY INTEGRATED and must NOT be replaced or redesigned:

- Charging penguin: `./assets/nuxel-charging.png`
- USB connected to computer penguin: `./assets/nuxel-connected-pc.png`
- Live Console active penguin: `./assets/nuxel-live-console-active.png`

**Do only the following:**

1. **MOVE** the entire set of three indicators **UP** on the lockscreen. Position the active-icon group **directly below the clock, date and battery percentage**, and **clearly above the screen's vertical center**. Leave a neat, visible gap below battery and above the icon group. No overlap with the clock, date, percentage, wallpaper art, or draggable lockhead. This was requested before but is STILL visibly unfixed: do not treat existing CSS declarations as proof.
2. **DOUBLE THE VISIBLE SIZE** of the three penguin illustrations relative to how small they currently appear **on the actual S10+ screen**. “Double” refers to the rendered visible penguin, **not just the transparent PNG canvas, parent span, drop shadow, or a CSS width token**. Measure visible artwork, not nominal image size. Preserve crisp pixel art, full silhouettes and correct proportions. Do not let any images overlap, clip essential pixels, become detached from their glow, or obstruct lockscreen swipe-to-unlock. The display is narrow; see geometry rules below.
3. Keep the charging penguin behavior that already works. It must light/appear whenever genuinely externally powered per existing semantics (with charging-specific animation only when charging); it must go away when disconnected. If charger is attached but battery is full or external power is present without charging, preserve intentional charge indicator semantics unless the owner explicitly requests otherwise.
4. **FIX USB PC penguin:** the **middle** icon must appear only when **a real USB DATA link to a PC/host is actually enumerated/connected**. It must disappear when USB is disconnected. It must **never** appear for a charge-only connection or a wall charger. USB VBUS, `power_supply online`, gadget existence or configfs binding alone are NOT evidence of a data-connected PC. A stuck old `pc_connected=true` after unplug is a bug. It must remain off with a charge-only cable/charger even while the charging penguin is on.
5. **Preserve and verify Live Console penguin:** turn it on only when the actual live-console functionality/session is active; turn it off promptly when the console stops, disconnects, or is disabled. Do not equate the mere availability of root, `/dev/ttyGS0`, or a bound USB gadget with an active session. User believes this indicator is already correct: minimize changes to its logic unless measurements show a defect.
6. All three indicators must be **independent and composable**, with real independent visible on/off transitions. The owner explicitly says the middle icon should **disappear**, not just stay visibly dimmed. If the prior “inactive = 26% opacity” rule leaves ghost icons, change off-state visibility semantics to genuinely hidden while maintaining a stable, attractive layout when 1, 2, or 3 indicators are on.
7. **Actually DEPLOY and verify** on the physical S10+. No green check based only on passing source tests, edited CSS, a desktop WebKit preview, mocked sysfs or files copied to the wrong rootfs. Before/after visual proof must be obtained. If the phone cannot be reached or safe conditions are absent, finish the source patch and truthful offline tests, report PHYSICAL_NOT_VERIFIED and the exact next step, without pretending success.

## 1. Grounding: findings from the owner's supplied Nuxel source ZIP

The owner provided `nuxel-main (4)(1).zip`. These file paths and observations are **verified in that attachment**, but may have changed in a newer Git checkout or deployment. Inspect live files and use the newest authoritative code, resolving differences explicitly.

- `pwa/nuxel-home/index.html`: `#lockscreen` contains `#lockscreen-meta` (time, date, battery), then `#lockscreen-handle-wrap` (positioned absolutely), followed by `#lockscreen-indicators` with precisely three `<span>` nodes `lockscreen-indicator-charging`, `lockscreen-indicator-usb`, `lockscreen-indicator-live`. The DOM already puts the icon row *after* the clock/date/battery; so a DOM-only change is not enough.
- `pwa/nuxel-home/css/lockscreen.css`: the icon row is `position: relative`, `margin-top: 10px`, `min-height: 108px`, horizontal `display: flex`; `.lockscreen-indicator` is `width: clamp(100px, 30vw, 108px)` and likewise for height, plus `max-width: calc((100vw - 20px) / 3)`. These hard caps can prevent an apparent size increase.
- SAME CSS: image elements use `width:100%; height:100%; object-fit:contain`, with `clip-path: inset(...)` rules. **Clip-path hides pixels but does NOT enlarge the visible penguin**. Transparent margins plus different source image aspect ratios further reduce visible artwork; establish actual alpha bounds, crop/scale correctly and keep animation transforms coordinated.
- `pwa/nuxel-home/js/lockscreen-indicators.js`: script version `a68.3`; reads `NuxelHost.statusRead('system-indicators')`, fallback `bridge.getSystemIndicators()` or `http://127.0.0.1:8080/api/v1/system/indicators`; applies `.active` according to `charging.external_power`, `usb_data.pc_connected`, and `live_console.active`. It polls at `SAFETY_MS=15000`, with some event-driven refresh. The 15-second safety poll may make USB detach look stuck: inspect event delivery, data source behavior, and refresh races (including in-flight generations) before choosing responsive event handling and a bounded polling fallback.
- `services/nuxel-bridge/src/system_indicators.py`: `get_indicators()` returns the above fields; `usb_connection()` checks configfs bound gadget and UDC `configured` **or `addressed`**, with vendor `/sys/class/android_usb/android0/state == CONFIGURED` fallback. **Do not assume `addressed` guarantees full host configuration**; verify actual phone/PC state and any stale vendor signal before using it. Live-console state is derived from `nuxel-console` process/tty and validated lease; preserve working session detection.
- `services/nuxel-bridge/src/api.py`: serves `/api/v1/system/indicators`. `tools/s10plus/a33/nuxel-pwa-host.c` and `tools/s10plus/a45/nuxel-pwa-host.c` implement phone-host status read paths. `pwa/nuxel-home/js/bridge.js` contains bridge path references. Audit all real code paths, not only the Python endpoint, since the host read is tried first and can supersede fallback data.
- Relevant existing tests: `services/nuxel-bridge/test-system-indicators.py`, `tools/s10plus/a45/test-lockscreen-indicators.js`, `tools/s10plus/a45/test-lockscreen-layout.js`. Existing JS tests exercise synthetic state combinations but do **not** prove the live USB cable scenarios or the physical rendered size/position.
- Assets in the ZIP are not all square: charging 1254×1254, PC 1374×1145, Live Console 1254×1254. They have transparent/near-transparent borders; ensure proper canvas-independent image sizing and alpha-aware visible bounds, with correct object-fit behavior. **Do not modify source PNG artwork unless absolutely necessary**; if preparing derivative trimmed assets, keep originals unchanged and generate deterministic derived artwork with correct transparency and naming.
- Frontend asset links in `index.html` and stylesheet references already have `?v=a68.3` cache stamps. Confirm the deployed app actually loads updated bytes, and update all relevant cache stamps, service worker caches, and any duplicate installed bundles if required. Never claim a visual adjustment from repo diff alone.

**The user's concrete unresolved symptom:** “Still not moved or resized” even though CSS claims the row is already directly below metadata. This suggests actual deployed build/cache mismatch, conflicting styles, scaling/alpha padding, stale CSS, or different live web root. Trace the real cause and fix it rather than appending another overriding stylesheet.

## 2. PRE-FLIGHT: prove what device and files are actually running

1. Confirm repo, branch, commit, working-tree status, file checksums and target S10+ identity. Do not overwrite owner's uncommitted work. Branch/checkpoint only with permission when needed.
2. Establish device access and *a tested way back* before any updates, keeping an alternate console/recovery if the affected USB-data link must be disconnected for testing. Do not cut your sole access by turning off the USB gadget or serial session remotely. Owner or physical operator handles cable swaps and confirmation.
3. Locate actual running launcher: process, service unit, WebKitGTK URI, app document root, deployed CSS/JS/Python/C host binary, service-worker cache/version. Compare deployed SHA-256 with Git source. Document all duplicated files that could override newer patches.
4. Capture **BEFORE** lockscreen screenshot/video from the physical phone showing clock, percentage, three icons, and lockhead. Capture JS `getBoundingClientRect()` / `getComputedStyle()` or equivalent WebKit remote inspection readings for meta, indicator row, actual SVG/PNG image bounds, viewport scale factor, safe-area inset and overlap. If remote inspector is unavailable, use a temporary read-only diagnostic injected behind a disabled-by-default flag; never leave a security-sensitive remote inspector exposed.
5. Record backend JSON from both the host status-read and HTTP bridge and compare against raw sysfs and actual cable topology, including timestamp, kernel states and refresh cadence. No credentials, secrets, or system-wide debug log dumping into the UI.
6. Back up exact modified files and relevant live deployed copies with hashes; create an atomic restore/rollback procedure. Ensure unlock swipe is functioning before changing any layout near the lockhead.

## 3. MAKE THE LAYOUT CHANGE VISIBLE, MEASURABLE, AND RESPONSIVE

- Keep the exact clock, date, battery wording/placement and penguin lockhead artwork/drag behavior. Only move and resize the three small status penguins.
- The whole **visible indicator group** belongs in the top portion, directly under the *bottom of the rendered battery element* (suggest starting with 12–20 CSS pixels of vertical gap), with **its lower visible edge above 50% of the usable lockscreen height**. Use `getBoundingClientRect` measurements rather than guessed body heights. Respect top safe areas/notch and physical viewport.
- Use a stable layout model: the indicators may share a row with reserved slots to avoid layout jumps, but OFF icons should be visually absent, not ghosted. All 1-, 2-, and 3-active combinations must remain centered where aesthetically expected. Make no changes to lockhead resting/gesture calculations unless an actual verified overlap requires it.
- **DOUBLE THE VISIBLE PENGUIN** compared with pre-fix on-phone screenshot. Measure alpha-aware actual icon painted bounds, preferably with image-alpha geometry and phone screenshots; don't just multiply the CSS outer box. Take care with source PC PNG (1374×1145 vs 1254×1254). If object-fit `contain` leaves the glyph tiny, trim transparent margins in rendered derivative assets or use a proper clipping/scaling wrapper—`clip-path` alone is NOT a resize solution. Preserve crisp pixel art and glow. When no two icons can be simultaneously on, icons must still look correct with individual glow and animations.
- **Physics check:** a 360px-wide CSS viewport cannot display three *216px-wide* symbols side by side without overlap (3×216 > 360). Do not fake literal doubling by allowing overlap. Prioritize *2× the visible glyph compared with the current tiny apparent glyph* through alpha-aware cropping, compact gap and sensible responsive sizing, and demonstrate the result. If genuine 2× **visible** size of all three can't fit in one row on the physical viewport, use a clean adaptive two-row 2+1 layout or another unambiguous arrangement **still below the metadata and above screen center** where feasible; explicitly report any tradeoff instead of falsely promising impossible dimensions. Keep all three visible together and leave enough space to drag the lockhead.
- No changes to wallpaper, title, date, percentage, lockhead movement, global launcher, dock, battery measurement, settings, sound, networking or other features.
- Update responsive handling across actual `360×760` CSS-target viewport and variants e.g. `320×640`, `430×900`, landscape; match device pixel ratio / WebKit scaling and portrait locked mode on real phone. Fail closed on layout overlap; no CSS `!important` arms race or duplicated style injection.
- Animation: preserve separate gentle breathe/charge/USB/console effects. Active effects only, pause when screen off, respect `prefers-reduced-motion`, avoid continuous expensive blur composition in software rendering.

## 4. FIX THE PC INDICATOR'S SOURCE-OF-TRUTH, NOT ITS COLOR

### Required semantic contract

**Charging penguin** = `external_power` truth from power subsystem. **PC penguin** = independently verified *USB peripheral data connection to a host*, NOT USB power and NOT mere gadget preconfiguration. **Live Console penguin** = genuinely active console session/functionality, NOT merely physical USB cable.

Do a recorded five-condition matrix using real cables/hosts and raw state snapshots:

| Condition | Charging | PC data | Live Console |
|---|---:|---:|---:|
| No USB / no power | OFF | OFF | OFF unless an independently active non-USB console really exists |
| Wall USB-C charger, power-only | ON (if power present) | **OFF** | OFF |
| USB-C data cable into PC with data enumeration, console not active | According to external power | **ON** | OFF |
| Same real USB data connection, Live Console session actively running | According to external power | **ON** | **ON** |
| Physical PC cable unplugged / disconnected | According to remaining charger/power | **OFF promptly** | OFF when session actually ends |

Additional checks: charge-only cable connected to computer, host with only VBUS and no enumeration, rapid connect/disconnect, PC sleep, PC USB suspend/re-enumeration, device role changes, process restart while cable disconnected, cold boot with charger inserted. If UDC `addressed` occurs before genuine USB `configured`, decide whether to display a data link only after `configured` or another trustworthy equivalent, and back the choice with evidence. A bound gadget remains bound without a PC; do not infer connection from it.

### Read-only diagnostic data to gather (adapt to device paths)

- `/sys/class/udc/*/state` before/after each topology, `/sys/kernel/config/usb_gadget/*/UDC` bound controller, available type-C/USB role sysfs state, Android vendor USB_STATE if present, and `journalctl -k` around attach/detach. Correlate with the *PC host's enumeration evidence* (`lsusb`, kernel event, `dmesg`, actual USB network/serial device). Data from the physical PC is the ground truth for this test, not an old sticky flag.
- `/sys/class/power_supply/*/{type,online,status}` as available; separate charging from PC DATA. Beware host-mode/source-mode power reporting.
- Nuxel bridge API response and `NuxelHost.statusRead('system-indicators')`; check that the host and HTTP fallback never disagree or expose cached state after unplug. Audit actual path in `tools/s10plus/a33/nuxel-pwa-host.c`, `tools/s10plus/a45/nuxel-pwa-host.c`, bridge implementation and deployed binary version.
- Check if `addressed`, `configured`, vendor `USB_STATE=CONFIGURED` persist across a charger-only scenario, whether sysfs UDC states are latched due to gadget driver behavior, and whether actual disconnect uevents are delivered. Add source-specific validation or reliable detach handling as necessary. **Do not force-rebind the gadget or reconfigure USB mode as a test without explicit approval and a tested recovery route.**
- UI lifecycle and stale reads: ensure the indicator updates immediately on lockscreen show/wake and promptly on USB uevent; when status changes during a 15-second poll, a real disconnect must not remain visibly ON for 15 seconds if an event source is available. If no event source, add safe, bounded short polling *only while lockscreen visible*, with no device CPU wake-lock spin. Enforce request ordering so stale callbacks cannot re-light the disconnected PC icon.
- Distinguish backend ON truth from frontend stale `.active` class or alpha/opacity-only OFF look. Use explicitly hidden state if needed; all state combinations remain independent.

### Live Console state

Preserve `system_indicators.live_console()` current process/TTY/lease checks unless a specific physical test fails. Verify a real active tty console session and deactivation. Do not expose root toggles, invent sessions, or couple console icon to charging. If the phrase 'functionality turned on' refers to a listening service rather than an attached session, examine current intended product semantics and preserve the established user setting; do not silently redefine it from UI appearance alone.

## 5. EXACT IMPLEMENTATION TARGETS

Inspect and edit only what testing proves necessary. Likely candidates:

1. `pwa/nuxel-home/css/lockscreen.css` — icon group top placement, image painted size/alpha trim, 1–3 status reflow, visible OFF state and compositor-light animations.
2. `pwa/nuxel-home/index.html` — only if markup/order/asset-version prevents proper layout, or if cache stamps require bump. Do not alter lockhead.
3. `pwa/nuxel-home/js/lockscreen-indicators.js` — correct state visibility and timely USB on/off, timestamp/race guards, get real backend data; preserve 3 independent signals.
4. `services/nuxel-bridge/src/system_indicators.py` — only after identifying concrete `pc_connected` false-positive or stale-state logic, especially `addressed` and Android fallback.
5. `services/nuxel-bridge/src/api.py` / actual nuxel PWA host C source — only if bridge mismatch, event propagation or cached response is the cause.
6. Relevant bundling/deploy code — only to ensure changed bytes actually reach the running phone and WebKit doesn't reuse stale cache.
7. Update current automated tests and add at least one **layout geometry regression test** plus **USB charger versus host enumeration regression tests**, based on measured hardware states and response lifecycle.

**Do not replace the entire launcher, rebuild Nuxel, or touch unrelated A69/A68 code.** Keep the patch small, inspect `git diff` before every deployment, and roll back if unlock starts failing.

## 6. VERIFICATION PLAN — NO MOCK-ONLY PASSES

### Offline/unit tests

- Run `python3 services/nuxel-bridge/test-system-indicators.py` (or appropriate current test invocation) and `node tools/s10plus/a45/test-lockscreen-indicators.js`, `node tools/s10plus/a45/test-lockscreen-layout.js`; adjust exact commands based on present repo.
- Tests must include all 8 state combinations, charger-only PC off, host-enumerated PC on, unplug transition PC off, console starts/stops, async stale response suppression, source mismatch, switch to lockscreen, boot-on-charger, and simultaneous three ON.
- Geometry tests must check no overlap with metadata, lockhead, wallpaper touch affordance, viewport limits; include *visible-artwork bounding box* rather than only element `width`/`height`. Make tests assert the target spatial band and relative size improvement.

### Physical test matrix: required screenshots and evidence

| ID | Test | PASS evidence |
|---|---|---|
| 01 | Cold boot lockscreen on battery | Captured screen, icon row just under metadata, clearly upper-half; all OFF when no power/host/session |
| 02 | Visually compare before and after | Actual visible penguins ~2× prior apparent size, no hidden glyph pixels, no overlap, proof with annotated screenshots/bounds |
| 03 | Charger-only USB-C brick | Charging penguin ON; **PC penguin OFF**; Live Console OFF |
| 04 | Charge-only data-blocked cable | Charging ON; **PC OFF** |
| 05 | Real USB PC enumerated | PC penguin ON only after physical host enumerates data function |
| 06 | Unplug PC data cable | **PC OFF promptly**, verify UI change and API/sysfs signal, no stale ON |
| 07 | Live Console active | Console penguin ON with real session, charging/PC independently correct |
| 08 | Live Console deactivated | Console OFF, charging and PC unaffected |
| 09 | 2–3 indicator combinations | Clean upper layout, correct slot reflow, no overlap or clipping |
| 10 | Lock/wake cycle x5 | Correct icon positioning, no stale states, no phantom indicator after detach |
| 11 | Swipe unlock x10 | Draggable penguin still moves and unlocks reliably; icon area is not a touch blocker |
| 12 | Device restart after approved reboot | Updated source persists; screenshot proves cache/deployment truly updated |
| 13 | Non-regression | Browser and Wi-Fi function, launcher works, Home/Back safe, lockscreen clock/date/battery unchanged |

Keep evidence under `docs/a70-lockscreen-indicator-precision/` or analogous mission-specific folder in the repo: command receipts, before/after screenshots, actual box geometry, test logs, USB scenario table with raw backend states and host enumeration confirmation, deployed hashes and rollback scripts. Redact host/device identifiers where appropriate. Don't log personal data.

**Never** report `PASS_PHYSICAL` unless actually observed from the phone. If charger-only cable and PC host cannot be safely tested because disconnecting the phone would sever the only control path, ask for a local physical operator to perform those individual swaps and mark the test `PENDING_PHYSICAL` rather than faking it.

## 7. EXECUTE AND REPORT

1. Inspect live code and real deployed root. Record baseline and suspected root cause(s) for old no-movement/no-resize and PC false-positive.
2. Implement the minimal auditable patch, update frontend cache version(s), compile/restart only required userspace service(s), and safely deploy actual revised CSS/JS/bridge pieces.
3. Compare SHA-256 hashes of deployed sources/assets against desired commit, then **take a real post-fix S10+ screenshot**. Explicitly prove icon row moved and apparent penguin size doubled. Do not mistake visual size changes in desktop preview for real device progress.
4. Verify PC penguin goes OFF with wall charger and unplug, ON only with real data host enumeration; preserve charging and active console. Record time-to-update in seconds.
5. Run regression matrix, restore if regressions occur, and present succinctly:
   - root cause; precise changed files and commit;
   - measured before vs after group coordinates (px or CSS px), visible image size and ratio;
   - each physical USB scenario + on/off states;
   - real screenshot evidence paths and live hashes;
   - tests passed, tests unverified, remaining honest blockers, rollback command.

**STRICT STOP RULE:** No work outside the lockscreen trio. Never touch the functional Wi-Fi, DNS/TLS/browser, audio, rotation, Bluetooth, camera, shell navigation, performance stack or kernel to fix these three penguins. Don't add a new monitoring framework if existing bridge/sysfs is fixable.

## FINAL ONE-LINE DEFINITION OF DONE

**Three penguins physically ~2× larger, moved directly below the clock/date/percentage above the screen center, charging correct, USB PC icon OFF on a wall charger or unplug and ON only on an enumerated data host, console active status truthful, lockhead unlock preserved; all confirmed on the actual S10+ with screenshots and test evidence.**
