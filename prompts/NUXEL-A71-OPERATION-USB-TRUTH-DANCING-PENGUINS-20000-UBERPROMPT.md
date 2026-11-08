# 🐧 NUXEL A71 — OPERATION USB TRUTH & DANCING PENGUINS 20000
## GPT-5.6 SOL · HIGH / EXTRA HIGH · S10+ LOCKSCREEN-ONLY SURGICAL REPAIR

> **EXECUTE the repair**, not merely propose one. Work on the actual current Nuxel Git checkout, build and physical Samsung Galaxy S10+ (SM-G975F, Exynos 9820, Fedora ARM64, currently working Linux 4.14 vendor kernel). The owner reports that the three lockscreen indicator penguins have FINALLY reached the desired **position and size**. Keep those exact visuals. Focus ONLY on truthful detach/off states and visible independent animations. Preserve the rest of Nuxel.

## 0. Owner report — immutable acceptance contract

The physical phone now has three PNG indicators in the correct order, location and size:

1. Charging penguin `./assets/nuxel-charging.png` — **already correctly disappears when unplugged**.
2. PC-connected penguin `./assets/nuxel-connected-pc.png` — **WRONG: remains visible after unplugging USB**.
3. Live Console penguin `./assets/nuxel-live-console-active.png` — **WRONG: remains visible after unplugging USB**.

Only the PC penguin visibly moves/animates. Make the **charging** and **Live Console** penguins have their own tasteful, clearly perceptible, lightweight animations, compatible with the existing lockhead aesthetic. Preserve the existing PC animation.

**Do not move, resize, replace, crop, recolor, reorder or redesign any of the three icons. Do not modify the lockscreen clock/date/battery, draggable penguin lockhead, wallpaper, or unrelated system functions.** The previous A70/19000 positioning/sizing work is accepted and is a non-regression gate.

### Exact appearance truth table

| Physical setup | Charging penguin | PC-connected penguin | Live Console penguin |
|---|---|---|---|
| No USB cable, battery powered | OFF (fully gone) | **OFF (fully gone)** | **OFF (fully gone)** |
| Wall USB-C charger / charge-only cable | ON when external charging/power is truly present, per existing good behavior | **OFF** | **OFF** |
| Actual enumerated USB PC, no attached active console session | ON if receiving external power | ON | OFF |
| Real USB PC, active tty USB Live Console session | ON if receiving external power | ON | ON |
| Detach from PC while console was active | OFF (existing behavior) | **OFF promptly** | **OFF promptly** |
| Console closes while USB data stays connected | Charging unaffected | PC stays ON | **OFF** |
| Screen locks/unlocks/wakes after detach | Truthful refreshed state | OFF | OFF |

If product semantics deliberately define Live Console as "session enabled/listening" rather than "active client session," document that distinction and reconcile with the owner's explicit requirement: **the live-console-on penguin must not falsely remain illuminated once the USB PC connection has ended**. Do not redefine "active" silently and do not kill or disable the actual console to force the indicator off. If the device supports independently reachable non-USB console sessions, document and handle that separately without silently misrepresenting a live USB PC connection.

Inactive means **not rendered at all**, not faintly at 26% opacity. Layout must not shift unexpectedly between the 0–3 active-state cases; preserve the current positions of visible icons. Touch-to-unlock and other touches must remain unaffected.

## 1. What earlier archived Nuxel source demonstrates (verify against CURRENT tree first)

The prior owner-uploaded `nuxel-main (4)(1).zip` was inspected. It is historical context, NOT proof the latest deployed code is identical. Key areas to audit:

- `services/nuxel-bridge/src/system_indicators.py`: `usb_connection()` considers any bound configfs gadget plus UDC `configured` **or `addressed`** as `pc_connected=True`; if no gadget is bound, the vendor `/sys/class/android_usb/android0/state=CONFIGURED` fallback may still yield TRUE. These states may be stale or weaker than actual host enumeration. `live_console()` scans for `nuxel-console` with `ttyGS0` FD or process lease and subsequently checks only `gadget_bound` and tty registration; **a still-running process + registered gadget/tty does not prove a live host after disconnect**. These are concrete suspect conditions, not a guaranteed diagnosis.
- `pwa/nuxel-home/js/lockscreen-indicators.js`: the UI primarily calls `NuxelHost.statusRead('system-indicators')`, then bridge/API fallback, so editing only the Python HTTP endpoint may not affect the phone. The historical JS uses `SAFETY_MS = 15000`; failed reads leave last-known state forever; `refresh()` increments generation while `_inFlight` may suppress the new fetch, and callbacks can be discarded. This can leave stale ON icons for extended periods. Audit current source and deployed WebKit host implementation before patching.
- `pwa/nuxel-home/css/lockscreen.css`: animations **already exist** for all three icons. Charging image animation selector `.lockscreen-indicator.charging-ind.active.charging img` requires a real `.charging` flag, not merely external power; PC `.usb-ind.active img` has a small 3-second float; Live Console `.live-ind.active img` uses a subtle 1.9-second opacity pulse. The row also animates glow. Verify actual rendered classes, style overrides, WebKit support and `prefers-reduced-motion` before replacing animation logic. `body.display-off` correctly pauses hidden animations; maintain that.
- `pwa/nuxel-home/index.html` lockscreen indicator elements / referenced assets / cache-busting versions, `pwa/nuxel-home/js/bridge.js`, `services/nuxel-bridge/src/api.py`, `tools/s10plus/a33/nuxel-pwa-host.c`, `tools/s10plus/a45/nuxel-pwa-host.c`, and current service/deployment bundles may publish or cache different status payloads. Locate authoritative modern paths through repository searches rather than assuming A45 is still active.
- Existing tests to investigate/extend: `services/nuxel-bridge/test-system-indicators.py`, `tools/s10plus/a45/test-lockscreen-indicators.js`, `tools/s10plus/a45/test-lockscreen-layout.js` and appropriate newer equivalents. Mock tests alone do not establish physical truth.

## 2. Safety: keep access, keep functionality

1. Check repo status, uncommitted edits, branch, intended device, current OS and USB gadget/console service. Establish a safe backup and rollback for every changed file, service and generated bundle.
2. Before unplug testing, identify whether Live Console is your **only control channel**. Arrange owner/operator cable swaps or another tested access/recovery channel (on-device interaction, alternate network console, or proven recovery). You must not attempt a remote detach/rebind that strands the device. Do not flash boot, kernel, partitions, recovery or firmware; do not migrate kernel versions.
3. Do not "fix" it by stopping the console service, unlinking gadget configfs, disabling USB, hiding all icons unconditionally, tampering with power_supply, or altering security permissions. Existing USB Live Console must continue to function when connected.
4. Audit what's **actually running on the S10+**: source paths, installed host binary and status-read implementation, JS/CSS loaded in WebKitGTK, service version, symlinks, timestamps, content hashes, caching/service workers, stale process instances. Source-only edits and cache stamps do not constitute deployment.
5. Preserve current exact position/size/quality of all three PNGs and previously functioning charging connect/disconnect behavior. No broad launcher, graphics, Wi-Fi, audio, Bluetooth, navigation, battery or UI refactor.

## 3. Reproduce and instrument the actual BUG

**Collect timestamp-correlated data** for baseline PC attached/console active -> PC unplugged -> wall charger -> USB data host reconnect -> console ends. Take lockscreen screenshots or video, frontend classes/styles, phone sysfs/proc snapshot, backend `get_indicators()` JSON and native host `NuxelHost.statusRead('system-indicators')` response for each scenario; PC-side `lsusb`/udev/serial enumeration if physically available.

Read-only candidate diagnostics (use actual phone paths; gracefully handle missing files):

```sh
find /sys/class/udc -mindepth 1 -maxdepth 2 -name state -print -exec cat {} \;
find /sys/kernel/config/usb_gadget -mindepth 2 -maxdepth 2 -name UDC -print -exec cat {} \;
cat /sys/class/android_usb/android0/state 2>/dev/null || true
for x in /sys/class/power_supply/*; do printf '%s ' "$x"; cat "$x/type" "$x/online" "$x/status" 2>/dev/null; done
journalctl -k --no-pager --since '-5 minutes' | grep -Ei 'usb|udc|gadget|ttyGS|disconnect|vbus|typec' | tail -100
```

Also inspect `/sys/class/usb_role`, `typec` class and extcon interfaces if present, actual UDC `state`, current `usb_role`, relevant binder/service and console process FDs. Not all 4.14 kernels export modern interfaces: never invent a file or assume values mean the same as upstream.

Correlate the **authoritative cable-detached physical event** with all observable states. Determine for each wrong icon whether:

A. backend truth itself is wrong (`pc_connected=True` / `live_console.active=True` after actual detach);
B. native host/status path returns a stale cached JSON snapshot;
C. HTTP and native paths disagree and fallback logic prefers the old one;
D. frontend subscription/refresh isn't triggered promptly on actual detach;
E. a request-ordering `_inFlight`/generation bug discards a state update;
F. backend reads fail after detach and the frontend retains the old ON state forever;
G. `.active` is removed but CSS still paints a dim/ghost indicator; or
H. phone loads an older JS/CSS/service binary than the repo, or some combination.

Log the moment of disconnect, data change, UI update and any intermediate error **without logging secrets**. Investigate these actual causes before deciding on patch.

## 4. Fix PC-connected signal with actual link evidence

- **USB VBUS or charging is NOT a PC data connection.** Neither `power_supply.online`, configfs gadget existence, gadget binding alone, `ttyGS0` existence, nor `addressed` alone constitutes proof of a currently functioning USB data host.
- Use the best actually working signals the S10+ exposes: an up-to-date UDC configured state *with reliable detach transition*, verified external host enumeration, vendor state with fresh attach/detach event, or a proven gadget data-function handshake. Prefer a clear state machine with evidence provenance and an authoritative false-on-detach transition. If one sysfs indicator demonstrably remains configured while physically unplugged, treat it as unreliable alone and correlate a second link-presence signal; do not add arbitrary sleep delays as a substitute.
- When physical disconnect is observable, clear `pc_connected` promptly. Never let an old vendor `CONFIGURED` value reassert TRUE after the host is unplugged. If the hardware exports no trustworthy data signal, return **unknown/inactive safely** and log `LINK_EVIDENCE_UNAVAILABLE`; explain the limitation rather than claiming PC is still connected.
- Wall-charger and charge-only scenarios must always show PC OFF; allow charge penguin to remain ON.
- Eliminate stale state leakage across process restart, new lockscreen instance, reboot or live console service restart.

## 5. Fix Live Console indicator independently, with physical-session truth

- Audit whether it represents **service enabled**, **tty handler active**, or **connected client session**; compare owner's desired ON/OFF and current implementation, and use the established product meaning with a real session criterion.
- A long-running `nuxel-console` process and an open `ttyGS0` file descriptor can survive unplugging; they may mean "listener available" rather than "host currently connected." Don't infer an active host session just because the PID, FD or lease survives.
- A lease is trustworthy only if authored by the active console implementation, tied to session generation or lifetime and refreshed/cleared appropriately. Handle PID reuse and stale state files. Prefer existing connect/disconnect/session events when available. Make the live indicator turn OFF on actual USB detach even when daemon remains alive, and OFF when the session terminates while data remains connected.
- **Do not tie the animation's logic to charging.** PC-data state and live-console state must be independently derived. A genuine live USB console requires a viable data host; when USB disconnects, the USB-console-active icon cannot remain illuminated. If a genuinely independent network console exists, only display a console-active icon for that distinct session per documented UI semantics.
- Preserve root console availability and login/session integrity. No making/faking a console process for passing tests.

## 6. Deliver reliable, promptly updated frontend truth

- Trace full live path: kernel event → bridge native status → (host API/fallback) → JS normalisation → DOM class → CSS painted state. Validate the path WebKit actually uses.
- Prefer event-driven refresh on kernel gadget/USB state changes and explicit console session transitions if supported. Provide bounded polling as a fail-safe while the **lockscreen is visible**, e.g. around 0.75–2 seconds subject to measured CPU budget; return to idle/stop entirely when screen off or lockscreen hidden. Avoid 15-second lingering false-ON after a detach.
- Resolve `_inFlight` / `refresh()` races: queue a refresh if the current one is running, cancel or ignore out-of-order responses using a monotonic sequence, and issue a new request immediately after previous read completes. An older cached TRUE must never overwrite a newer proven FALSE. Explicit timeout handling for native host and HTTP fallback. Do not spin continuously or create duplicate event listeners/timers on repeated locks/wakes.
- On **loss of reliable state** (backend unreachable, malformed/stale payload) do not display confidently stale PC/console TRUE indefinitely. Use a short bounded grace interval against transient failures then fail closed for these two status indicators until fresh positive evidence arrives, without wrongly suppressing the independent charger indicator. Report unknown in diagnostics; never invent a real USB connect. On actual unplug event, clear them without grace once detach is confirmed.
- Inactive icons must be **fully hidden**, not dim at `.26` opacity. The existing layout/slot geometry must remain stable exactly as currently approved. Keep no extra click/touch interception and prevent misleading transition ghosts.
- Add safe timestamp/age metadata if required, preserving backward-compatible API fields. Cache-bust current deployed JS/CSS/asset references appropriately; validate actual loaded hashes.

## 7. Make charging and live penguins unmistakably animated (without moving the row)

The PC penguin already visibly animates. Preserve its feel. The other two animations should **visibly move, glow or pulse when truly active**, never animate while inactive:

**Charging penguin**
- External power present: visible gentle breathing, tiny 2–4% bob or scaling motion, and restrained soft green pulse/glow. If battery is actually in `Charging` state, add a modest rhythmic "energy" pulse; when external power is present but battery full/Not charging, use slower idle/connected charging-style animation so it does not appear frozen. This respects existing charging truth instead of pretending a full battery is charging.
- Implement the animation through the correct active classes, or otherwise ensure it triggers for the state in which its penguin is actually visible. Current historical CSS ties the image animation to `.active.charging`; if external power is true and `.charging` false, the artwork may stay static. Verify actual WebKit computed styles and classes live.

**Live Console penguin**
- While **genuinely active**, show a legible, tasteful amber/orange pulse with a very slight tilt or scale/terminal heartbeat, visually distinct from the charging and PC animations; no flickering and no large movement. Use transform/opacity on image/glow so the whole icon is recognizably alive, rather than only changing opacity by a tiny invisible amount.
- It must stop animating immediately when the session ends or USB disconnects, and the icon must disappear.

**Efficiency + aesthetic requirements**
- Do NOT alter icon row coordinates, widths/heights, alpha crop, source PNG dimensions, lockhead position or any previously approved design. Animations must be on *child image or glow only*, not the icon's layout box; don't interfere with unlock gestures.
- Avoid animating layout dimensions, top/left, shadows/filters that trigger expensive software repaint, or stacking huge compositing layers. Use modest `transform`/`opacity`, mindful of Nuxel's current compositor efficiency and reduced GPU acceleration.
- Pause animation on screen-off, unlock/hidden lockscreen, and `prefers-reduced-motion: reduce`. Preserve status truth even with animations disabled.
- Distinguish active/inactive classes so three penguins can animate independently at once; multiple active states must not cancel each other's keyframes. Ensure the normal CSS cascade, prefixed compatibility if needed, and optional power-save mode don't silently disable one.
- Include a short physical video (or timed screenshots/computed-style trace when capture is impractical) proving **charging moves**, **PC moves**, **Live Console moves**, each only while ON.

## 8. Code boundaries, tests, deployment

Primary potential files, depending on the current checkout:

- `services/nuxel-bridge/src/system_indicators.py` + tests: USB/console truth, edge-triggered state and stale lease detection;
- `pwa/nuxel-home/js/lockscreen-indicators.js`: refresh lifecycle, failure-to-unknown, actual DOM class updates;
- `pwa/nuxel-home/css/lockscreen.css`: hide truly inactive nodes + visible charging/live animations while preserving exact artwork geometry;
- `pwa/nuxel-home/index.html`: only if genuine loaded bundle or version stamp needs updating;
- actual current `nuxel-pwa-host.c` / bridge status provider(s) and deploy code: only if used and causally involved.

Add/extend unit & integration tests without changing production behavior just to satisfy tests. Include:

1. All 8 truth combinations, and charger-only with data indicator always off.
2. `addressed` alone and stale `CONFIGURED` fallback do NOT keep PC ON after detach.
3. Live Console process/tty alive after USB unplug does NOT keep live indicator ON.
4. Session lease stale after disconnect, PID reuse, console restart, no session, active session.
5. Read succeeds TRUE → detach → read fails/stale → UI converges FALSE promptly (not indefinitely stuck TRUE).
6. Concurrent reads, event burst, 15-second legacy poll race, hidden/visible/lock/wake, duplicate listeners and teardown.
7. CSS active class conditions: charger animation when externally powered, extra charging pulse when battery genuinely charging, live pulse when active; none when off; reduced-motion and display-off pause.
8. Snapshot/layout geometry: **same before/after icon positions and visible sizes**, no regression in clock/date/lockhead swipe.
9. Real USB detach/reconnect and real live-console activation/deactivation on device; no `PASS_PHYSICAL` from fake sysfs.

**Safe deploy sequence:** Baseline and backup; patch minimal sources; run tests; audit diff; deploy only changed files/binary; ensure restart doesn't strand console; confirm live WebKit loaded correct bytes (SHA-256/version), not old assets; physically test; retain rollback commands and screenshots. Test detach only with owner physically present and safe recovery. Never disable USB console, unbind controller or reboot without explicit approval.

### Physical acceptance matrix — DO NOT SKIP

| Test | Expected evidence |
|---|---|
| Normal battery power, no cable | All three completely absent; lockscreen geometry unchanged |
| Plug wall charger | Charging penguin appears and **visibly animates**; PC and console absent |
| Plug charge-only cable to PC | Charging ON, PC OFF, console OFF |
| Plug a data-capable PC cable, host enumerates | PC ON and existing PC animation, charging as appropriate |
| Open a real Live Console session | Live ON and **visibly animating** |
| Unplug USB during console session | PC OFF and Live OFF promptly; charge OFF per existing behavior; neither is a faint ghost |
| Reconnect PC without console session | PC ON, Live OFF |
| Close console while PC remains connected | Live OFF; PC stays ON |
| Switch lock/unlock/wake 5× | Consistent truthful indicators; no stuck caches/listeners |
| Resume after approved reboot | Same state truth, no old cached JS, animations work |
| Existing UI baseline | Sizes, positions, wallpaper, lockhead unlock, Wi-Fi/browser, charging behavior unchanged |

Time-to-off target: prefer **~1 second** after an authoritative detach event; otherwise a **measured bounded couple of seconds** via safe polling. Do not fake timing measurements or claim instant hardware event delivery when unavailable.

## 9. Required report

Under `docs/a71-usb-truth-dancing-penguins/` save:
- Current repo/deployment versions and hashes; comparison to archived A70 assumptions.
- Before/after screenshot or video and timing (charge, PC, live).
- Raw phone `power_supply`, UDC, gadget, vendor fallback, process/lease state (redacted), API and native-host response in connected/disconnected cases.
- Root cause for PC staying ON and separate root cause for Live Console staying ON; note frontend/backend causes distinctly.
- Exact changed files, test commands/results, rollback, untouched components and commit reference.
- Table: `PASS_PHYSICAL`, `PASS_OFFLINE_ONLY`, `BLOCKED`, `FAILED`, `NOT_TESTED` for every physical scenario; never conflate a unit test with real device validation.

**DONE ONLY WHEN:** On the actual S10+ USB removal makes **BOTH** PC and USB Live Console penguins disappear, the already-correct charging penguin continues working, charging and live-console icons now visibly animate *while their true states are ON*, and **ALL three penguins retain the exact approved current size and top-of-lockscreen position**. No fake PASS and no other Nuxel component damaged.
