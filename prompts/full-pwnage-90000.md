# FULL PWNAGE 90000 — Nuxel Portrait UX, Flatpak Input/Navigation, Audio, Spoofer Apply, and Instant Lockscreen Wake

**Project:** Nuxel  
**Repository:** `~/x/nuxel` (verify the actual checkout)  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), unless live device discovery proves otherwise  
**Round:** PWNAGE 90000

## Mission

Surgically fix the reported defects on the actual Nuxel phone. This is not a redesign. Preserve working behavior, security, app data, graphics, audio, and the existing visual identity. Diagnose the real root cause before changing code. Never report a fix as complete merely because it compiles.

## 0. Non-negotiable working rules

1. Inspect the actual repository, branch, worktree status, commit, project documentation, current installed build, device identity, running services, app versions, display geometry, and logs before editing.
2. Reproduce every issue before changing code. Trace it to the owning source/service/protocol. Do not guess file paths, Flatpak IDs, process names, IPs, geometry, or service names.
3. Fix shared causes first (viewport geometry, input focus, keyboard integration, audio routing, lockscreen ordering), then use minimal app-specific compatibility rules only where necessary.
4. Preserve the existing Nuxel architecture. Historically the S10+ uses Phoc/Wayland and a framebuffer presentation bridge, with Mali/EGL. Verify the live architecture. Do not introduce a second `/dev/fb0` writer, force llvmpipe, disable Mali/EGL, replace the compositor, change global DPI/resolution, or blindly add WLR variables.
5. Do not flash or modify kernel, boot, recovery, modem, firmware, or partitions. None of these requested fixes should need that.
6. Keep changes scoped. In particular, the PenguInterface spoofer requirement is **Apply button only**. Do not redesign, refactor, change values, change defaults, alter scope, or change reset behavior.
7. Back up every deployed file/config before replacing it. Record timestamped backup location and exact rollback commands.
8. Distinguish `implemented`, `automated-tested`, `deployed`, and `physically verified`. Do not conflate them.
9. Do not weaken Flatpak sandboxing, permissions, authentication, cookie consent, or system security to make a test pass.
10. Do not capture or expose private messages, session databases, cookies, tokens, passwords, authentication codes, or private keys. Use dummy accounts/data where practical.
11. No permanent debug overlays, temporary CSS, test settings, or experimental environment variables in production.
12. Keep an implementation log: symptom, reproduction, root cause evidence, files changed, fix, test, deployment, physical verification, and rollback.

### Device access

Use the repository's current supported Wi-Fi SSH/device-debug workflow. Discover the live phone address; do not reuse stale addresses. If the existing maintenance key is available, use it without exposing it:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 \
  root@<DISCOVERED_HOST>
```

Keep host-key verification enabled; never use `StrictHostKeyChecking=no`. Verify device identity and `id -u` before privileged actions. If interactive authentication is needed, pause for the user. Never put credentials in scripts or logs. Keep the maintenance SSH path distinct from Nuxel's user-facing Tri-Link SSH console. If the phone becomes unreachable, stop and use the documented recovery path; do not improvise destructive recovery.

---

# 1. Defects to fix

## 1.1 Signal — compact, responsive portrait layout

**Symptom:** Signal is not sufficiently usable in portrait. The desired result is somewhat like Telegram: compact, with primary chat use fitting without unnecessary scrolling where possible.

### Diagnose

- Discover exact Flatpak ID/package, version, desktop file, launch command, runtime, and whether it is native Wayland or XWayland.
- Identify whether it is Electron, web wrapper, or another client.
- Measure actual logical window/content viewport, scale, device pixel ratio, top/bottom reserved areas, and app minimum dimensions.
- Inspect chat list, navigation rail, header, message list, composer, margins, and responsive breakpoints.
- Compare portrait with landscape, which must not regress.
- Determine whether the wasted space originates in Nuxel's wrapper/insets or Signal itself.

### Implement

- Make the chat list and conversation usable at the phone's real portrait viewport.
- Avoid desktop-width sidebars consuming most of the narrow display; use the app's supported narrow-screen navigation pattern if available.
- Reduce unnecessary padding/margins and excessive header height without making text or touch targets too small.
- Keep conversation header, messages, composer, send action, and attachments accessible.
- Prefer a compact Telegram-like presentation, but do not clip content or disable scrolling merely to claim “no scrolling.” No-scroll is a preference for basic chat interaction where content fits; natural scrolling must remain available for long conversations.
- Prefer supported app settings/responsive breakpoints. If a compatibility stylesheet/wrapper is unavoidable, isolate it, scope it to the verified app identity, make it reversible and update-aware.
- Do not alter Signal encryption, session data, sandboxing, notifications, or update mechanism.

### Verify

Portrait: open chat list, conversation, focus composer, type/send a test message, open attachments, navigate back. No inaccessible controls or horizontal overflow. Compact layout uses width efficiently. Landscape remains as before. Repeat after restart.

## 1.2 Telegram — modestly increase portrait usable area

**Symptom:** Telegram is nearly right; portrait just feels slightly too small.

- Measure actual app viewport and identify wasted space: wrapper padding, titlebar, insets, scale, or app layout.
- Make a small, measured, app-specific increase in usable portrait space.
- Do not change global resolution, DPI, font size, or other apps.
- Preserve readable text, touch targets, header, composer, and landscape behavior.

**Verify:** portrait gains a visibly useful but modest amount of space with no clipping/overlap; landscape remains unchanged; rotate while a conversation is open.

## 1.3 WhatsApp — portrait layout, keyboard, and microphone

These are separate defects and require separate root-cause analysis.

### A. Portrait layout

- Discover exact WhatsApp client/package ID, version, runtime, launch path, and Wayland/XWayland mode.
- Inspect chat list, conversation, header, message list, composer, sidebars, min-width, padding, and viewport.
- Make portrait compact and responsive like the Signal treatment while retaining vertical scrolling.
- Avoid horizontal overflow and inaccessible controls.
- Preserve the currently working landscape behavior.

### B. Keyboard does not appear when tapping the chat field

Trace the entire focus/input chain:

- Does the composer actually receive focus?
- Is the app Wayland or XWayland?
- Which input path does it use (`text-input-v3`, `text-input-v2`, `input-method-v2`, GTK IM context, XIM, or other)?
- Does Nuxel's on-screen keyboard observe the correct focus/text-input events?
- Is a wrapper, focus-stealing surface, or lifecycle manager interfering?
- Is the keyboard requested but hidden behind the app or immediately dismissed?
- Are keyboard geometry and app viewport insets stale after rotation?

Implement the correct integration for the actual runtime:

- Tapping the WhatsApp composer must focus it and invoke the Nuxel on-screen keyboard.
- Keyboard remains visible while the composer owns text focus.
- Hide it when focus legitimately leaves, the user dismisses it, or the app closes, following existing Nuxel policy.
- Correctly resize/inset the app viewport so the keyboard does not cover the field or send button.
- Handle rotation and app switching without stale keyboard state.
- Do not show the keyboard for every pointer click; do not fake focus.
- Preserve hardware keyboard behavior and shortcuts.
- Regression-test Signal, Telegram, native GTK, and other existing apps.

### C. Microphone crackle, glitches, doubling, slow/echo-like recording

Recorder captures the voice more correctly, but still has some glitch/double/slow behavior. Do not just raise gain. Establish whether Recorder and WhatsApp use the same physical source, PipeWire node, sample rate, channel layout, and processing chain.

Before changing settings, capture:

- audio server/session manager versions and status (PipeWire, WirePlumber, PulseAudio compatibility if present);
- physical capture nodes, profiles, routes;
- Recorder and WhatsApp capture streams while actively recording;
- selected source for each stream;
- sample rate, channels, sample format, quantum/buffer, latency, resampling quality, channel mapping;
- echo cancellation, noise suppression, AGC, limiter, denoiser, loopback, monitor source;
- number of simultaneous capture streams and loopback connections;
- XRUN, underrun, overrun, dropped-frame and scheduling evidence.

Investigate, but do not assume, these causes:

- WhatsApp selects a monitor/loopback instead of physical mic;
- duplicated capture routes or stream connections;
- sample-rate or channel-format mismatch;
- mono/stereo mapping error;
- quantum/buffer too small;
- XRUNs or scheduler starvation;
- clipping/excess gain;
- stacked AGC/noise suppression/echo cancellation;
- bad resampling or clock-domain synchronization;
- Nuxel mic-route/gain helper applied twice;
- wrapper environment variables or session policy selecting a different source for Chromium/Electron.

Fix the actual cause. Make WhatsApp use the correct physical microphone and reuse the Recorder route only if it is proven correct. Keep clean headroom; do not apply blanket gain boosts. Ensure one intentional processing chain. Scope per-app rules only to the verified WhatsApp identity. Do not regress Recorder, calls, Bluetooth, speaker playback, or other apps. If the app's own implementation is the blocker, report evidence rather than masking it.

**Physical audio tests:** record the same 10-second phrase in Recorder and WhatsApp at the same distance and normal speaking level; compare crackle, dropouts, clipping, echo/doubling, pitch/time slowdown. Repeat quiet and normal speech, after app restart and reboot. Confirm WhatsApp does not capture its own playback. Provide stream/node/format/XRUN evidence and human listening results. Keep private recordings local and remove temporary samples after analysis unless asked to retain them.

## 1.4 Hardware volume buttons — restore the “pow” feedback sound

**Symptom:** volume changes, but the familiar “pow” cue is no longer audible.

- Trace hardware key event → Nuxel key handler → volume control → cue trigger → sound daemon/player → output route.
- Locate the existing asset and verify it is readable. Do not invent a replacement if the existing asset remains.
- Determine whether the cue was removed, renamed, routed to an unavailable sink, muted, cancelled, or triggered before audio is ready.
- Restore the existing cue on accepted volume changes through the normal Nuxel audio path.
- It must not block or delay volume changes.
- Rapid repeated presses must not create an uncontrolled backlog or overlapping sound; use a small intentional coalescing policy if required.
- Respect mute and output routing.
- Do not alter alarms, timers, notifications, Doom audio, or general sound settings as a side effect.

**Verify:** volume up/down produces the expected audible cue on speaker and supported headphones/Bluetooth; test rapid repeats, immediately after wake, and after cold boot. Confirm alarms/timers remain functional.

## 1.5 Caprine — cookie notice fully reachable in portrait and landscape

**Symptom:** portrait hides cookie notice buttons; landscape shows them partly outside the screen and unpressable.

- Discover actual Flatpak ID, version, runtime, launch flags, backend, and whether consent UI is Caprine's or embedded web content.
- Inspect real viewport, device scale, fixed elements, min sizes, nested scrolling, and touch hit testing.
- Determine whether clipping comes from wrapper height, viewport meta, embedded webview, fixed footer/banner, reserved Nuxel UI areas, scale mismatch, or min-window constraints.
- Make the entire notice and its available accept/reject/manage controls reachable in both orientations.
- Prefer natural vertical scrolling and responsive reflow over shrinking the whole app.
- Keep fixed action footer inside the visible viewport and avoid content overlap.
- Ensure touch coordinates match visual positions.
- Do not auto-accept, auto-reject, hide, or programmatically click consent. Do not alter cookies, accounts, sessions, or privacy choices.

**Verify:** fresh consent state in portrait and landscape; read/scroll notice and physically tap controls; rotate while open; verify app proceeds only after the user makes a choice.

## 1.6 Triple-button Back — make it work inside Flatpak apps

**Symptom:** Nuxel's triple-button Back does not act as Back inside Flatpak apps.

Trace the actual chain:

1. Triple-button touch event.
2. Nuxel input dispatcher and focused-app tracking.
3. Compatibility/navigation bridge.
4. Wayland/XWayland surface and seat focus.
5. Flatpak boundary.
6. App-level navigation behavior.

Determine whether current implementation emits compositor-level key events, Wayland virtual-keyboard events, XTest/X11 events, D-Bus/custom app messages, or app-specific navigation. Verify what the running compositor actually supports.

Implement a supported secure input/navigation path:

- Deliver Back only to the currently focused app/surface.
- Use the established Nuxel Back mapping (e.g. Escape) for apps that interpret it as Back, or native navigation integration where available.
- Do not broadcast to every window or steal focus.
- Do not unexpectedly erase text or dismiss the keyboard when app navigation should take priority.
- Preserve Nuxel Back behavior when no app surface is focused.
- Preserve Home and Tabs.
- Respect Flatpak isolation; do not grant broad host input permissions or inject into apps.
- If compositor support is missing, implement/configure the smallest safe compositor-side mechanism. Do not replace the compositor or rewrite the input stack.

**Verify:** internal navigation in Flatpak GTK and Electron/Chromium apps; web navigation; text field behavior; app with no navigation stack; Home/Tabs unchanged. Test Signal, Telegram, WhatsApp, Caprine, Ferdium, browser, and one native GTK app where installed.

## 1.7 Landscape keyboard — use the full available width

- Inspect keyboard geometry policy, logical vs physical dimensions, scale, anchors/margins, layer-shell/exclusive zone, output transform, and rotation events.
- Determine why it retains a narrow portrait-like width in landscape.
- In landscape, use the full available usable width, respecting system safe insets/reserved areas.
- Reflow keys/rows appropriately; keep comfortable key height and touch targets. Do not stretch keys vertically or distort labels.
- Preserve all modifiers, symbols, language controls, and action keys.
- Correctly inset/resize the active app viewport.
- Recompute geometry on output rotation, size, scale, and keyboard show/hide; do not reuse stale portrait dimensions.
- Do not force full-screen keyboard in portrait.

**Verify:** show keyboard in landscape from WhatsApp and another app; all keys visible and tappable; rotate both directions with keyboard open; test text entry and viewport resize.

## 1.8 PenguInterface spoofer — fix Apply only

**Symptom:** Apply button does not work.

This scope is intentionally narrow.

Before editing, inspect and document the existing spoofer UI, schema, callback, backend/service/script, validation, status display, defaults, profiles, persistence, reset behavior, and process scope. Reproduce the failure and capture the actual error.

**Only permitted change:** repair the existing Apply action so it invokes the existing apply operation with the currently selected values and intended semantics.

- Wire the existing button to the existing backend operation.
- Pass current selected values correctly.
- Preserve existing schema and validation.
- Handle async completion and backend errors correctly.
- Show success only after backend-confirmed success.
- Show a useful error on failure.
- Refresh existing status from real applied state.
- Prevent duplicate concurrent Apply operations while one is in flight, without changing other UI behavior.

**Forbidden:** adding/removing/renaming/reordering fields; changing labels, values, profiles, defaults, scope, persistence, reset behavior, `LD_PRELOAD`, `uname`, `/etc/os-release`, user-agent or any spoof mechanism beyond invoking the existing broken Apply path; global spoofing; privileged-process impact; security/attestation/root-detection bypass; unrelated refactor or redesign.

**Verify:** pre-existing settings preserved; Apply calls existing backend exactly once with selected values; success only after confirmation; failure visible and not falsely reported; reset/persistence unchanged. Review the diff and explicitly prove no other spoofer behavior changed. If intended backend cannot be identified confidently, stop and report evidence rather than inventing one.

## 1.9 Ferdium — responsive portrait and scrollability

- Discover actual Flatpak ID/version/runtime/launch command and Wayland/XWayland mode.
- Inspect workspace/sidebar, service list, active service view, toolbar, viewport, fixed dimensions, min-width, hidden overflow, nested scroll regions, and touch gesture routing.
- Use Ferdium's own collapse/navigation drawer features where available.
- Make portrait usable without horizontal overflow; preserve access to services, workspaces, settings, accounts, and active service.
- Ensure active service content has working vertical scroll and gestures reach the intended container.
- Do not shrink text or touch targets excessively.
- Preserve landscape behavior and all login/session/authentication behavior.

**Verify:** portrait open, switch services, scroll a service, open settings, return; no inaccessible controls or dead scroll areas; restart and switch multiple services.

## 1.10 Power-key wake — eliminate the one-second zoomed desktop flash

**Symptom:** pressing power to wake the display briefly shows a zoomed desktop for about one second before the lockscreen. This must be eliminated. The first visible frame must be the correctly scaled lockscreen. The desktop must never be exposed while locked.

### Trace the real wake lifecycle

Do not add an arbitrary delay. Capture timestamps/logs and, if possible, high-frame-rate video/frame capture around a physical wake. Identify:

- power-key input source/handler;
- display blank/unblank sequence;
- compositor output wake;
- lock manager and lockscreen process/surface lifecycle;
- desktop visibility and output transform restoration;
- animations, zoom transitions, thumbnails, cached frames;
- races between desktop resume, lock surface readiness, and output unblank;
- stale pre-suspend framebuffer frame or incorrect virtual/logical resolution;
- whether lockscreen starts only after display unblank;
- behavior after short/long idle, active app, rotation, or compositor restart.

### Required safe ordering

1. Power key requests wake.
2. Keep display blanked or covered by a trusted opaque lock surface; do not expose desktop pixels.
3. Restore required display/compositor state.
4. Create/map/configure lockscreen surface for current output geometry.
5. Wait for a real readiness signal and at least one valid lockscreen frame presentation.
6. Only then reveal/unblank the display.
7. Keep desktop/app surfaces hidden until successful unlock.
8. After unlock, reveal desktop at correct scale without an intermediate zoomed frame.

Match the implementation to the actual compositor/lock architecture. Prefer a readiness handshake to fixed sleeps.

Requirements:
- Lock screen is first visible frame after every locked wake.
- No desktop, app, old screenshot, stale framebuffer, or incorrect zoom/transform flashes.
- Correct geometry/scale immediately in portrait and landscape.
- If lockscreen is not ready or crashes, fail closed behind opaque cover/blank display.
- Preserve fast wake; do not add a long delay to hide the symptom.
- Preserve notifications, clock, alarm/timer indicators and gestures, audio, and unlock security.
- Do not alter credentials or authentication policy.
- Handle charger/notification/call wake sources where supported.
- Handle rapid repeated power presses without stuck black screen or bypass.
- Never reveal desktop while locked.

**Verify:** at least 20 physical lock/wake cycles: short and long idle, app previously active, portrait, landscape, rapid power presses, pending notification/clock/alarm indicator where supported. Every cycle must show lockscreen first, correct geometry, then correct desktop only after unlock. Test lockscreen crash/restart in a controlled safe test. Report power-key-to-lockscreen-visible latency distribution.

---

# 2. Shared responsive layout and input architecture

Multiple Electron/Chromium/Flatpak defects may share a Nuxel viewport or input integration bug. Do not add arbitrary per-app CSS if the shared contract is wrong.

## 2.1 Runtime geometry matrix

Measure, do not assume:

- physical output dimensions;
- logical compositor dimensions;
- scale and transform;
- actual app viewport;
- top/bottom reserved UI dimensions;
- keyboard geometry/inset;
- app surface size;
- backend (Wayland/XWayland);
- web devicePixelRatio where available.

Create a portrait/landscape matrix for Signal, Telegram, WhatsApp, Caprine, Ferdium, one native GTK app, and another Flatpak.

## 2.2 Viewport contract

If system bars reserve space, apps must be laid out inside the remaining usable area. When bars hide and policy says to reclaim space, apps must expand accordingly. Ensure app-reported viewport equals actual exposed viewport. Recompute on rotation, scale/output changes, keyboard show/hide, and bar visibility. Avoid double insets, double scaling, stale geometry, or touch hit-test mismatch.

## 2.3 Scroll behavior

- Prefer app-native scrolling.
- Correctly identify the intended scroll container.
- Do not leave `overflow:hidden` on a parent that clips the only scrollable child.
- Avoid nested scroll traps.
- Fixed headers/footers must remain in the real viewport.
- Preserve touch targets and accessibility.
- No global CSS injection into all Flatpaks. Any compatibility layer must be opt-in, app-scoped, reversible, and tested.

## 2.4 App identity

Use the actual discovered Flatpak ID, desktop file identity, or stable app identifier. Do not key rules only on display names or guessed process substrings. Centralize app-specific overrides in a documented, validated configuration source.

---

# 3. Execution plan

## Phase A — Baseline and reproduction

1. Inspect repo status, branch, commit, docs, build/test/deploy scripts.
2. Identify deployed phone build and verify device identity.
3. Capture output geometry, compositor/backend, app IDs/versions, services, logs, audio graph, and lockscreen state.
4. Reproduce every issue before editing.
5. Create a defect matrix: reproduction, owner, root cause evidence, minimal fix, tests, physical verification.
6. Check for fixes already present but not deployed; do not duplicate them.

## Phase B — Shared foundations first

Investigate and fix in this order where dependencies justify it:

1. viewport geometry/insets;
2. touch/pointer coordinate mapping;
3. Wayland/XWayland focus and text-input integration;
4. landscape keyboard geometry;
5. Flatpak Back routing;
6. audio routing/format/buffering and volume cue path;
7. lockscreen wake ordering.

Then make minimal Signal/Telegram/WhatsApp/Caprine/Ferdium app-specific adjustments. Keep the spoofer Apply repair isolated.

## Phase C — Automated regression tests

Add tests based on actual discovered architecture, including:

- portrait/landscape geometry and viewport inset calculations;
- bar show/hide and output rotation updates;
- keyboard show/hide, focus ownership, app switching, and rotation;
- Back delivery only to focused surface and preservation of text input;
- stable Flatpak identity resolution;
- audio source selection, channel/format mapping, and single processing chain;
- volume cue dispatch/coalescing and error handling;
- spoofer Apply callback/backend contract, async success, failure, and reset non-regression;
- lockscreen state machine: locked → wake requested → safe cover active → lock surface ready → first frame presented → lockscreen revealed → authenticated unlock → desktop revealed.

Test success and failure paths. Use actual measured logical portrait/landscape dimensions. Do not invent test geometry.

## Phase D — Build and static validation

Run documented project commands and all relevant unit/integration tests, lint/type checks, shell/Python/JS validation, package/build verification, and existing UI/screenshot tests. Run the broad suite if feasible. Report unrelated pre-existing failures honestly; do not conceal them.

## Phase E — Safe deployment

1. Back up every replaced file/config on the phone with timestamp.
2. Record current services and app versions.
3. Deploy only changed components.
4. Validate ownership, permissions, executable bits, labels where applicable, and config syntax.
5. Restart only necessary apps/services. Avoid compositor/display restart unless essential and recovery is available.
6. Keep SSH reachable.
7. Prove the phone runs the new code via build ID/hash/process args or equivalent.
8. Do not claim deployment until confirmed by the device.

## Phase F — Physical testing

Perform the matrix below with real touchscreen, keyboard, speaker, and microphone input. Record results per item.

## Phase G — Final audit and rollback

Review full diff; verify no unrelated files/settings changed; prove spoofer scope is Apply-only; ensure no secrets/private app data were captured; verify no global software rendering or weakened sandboxing; provide exact rollback commands. Keep backups until user confirms stability.

---

# 4. Master physical acceptance matrix

| Area | Portrait | Landscape | Additional checks |
|---|---|---|---|
| Signal | Chat list, conversation, composer, attachments, compact layout | Existing behavior preserved | Send test message; restart |
| Telegram | Slightly larger usable area, no clipping | Existing behavior preserved | Rotate with chat open |
| WhatsApp layout | Chat list/conversation, vertical scrolling | Existing behavior preserved | Rotate while chat open |
| WhatsApp keyboard | Composer opens keyboard and accepts text | Correct landscape geometry | Hide/show, app switch, rotate |
| WhatsApp microphone | 10-second speech recording | If supported | Compare Recorder, crackle/doubling test |
| Volume “pow” | Volume up/down cue | Volume up/down cue | Rapid repeat, after wake/boot |
| Caprine | Notice scrollable, buttons tappable | Buttons fully visible/tappable | Fresh consent, rotate |
| Flatpak Back | Works in each tested app | Works in each tested app | Text field, nested navigation, Home/Tabs |
| Landscape keyboard | N/A | Full usable width; all keys tappable | Rotate both directions |
| Spoofer Apply | Existing controls unchanged; Apply works | N/A | Backend failure, success, reset, persistence |
| Ferdium | Service/workspace navigation and scrolling | Existing behavior preserved | Switch services; restart |
| Lock/wake | First visible frame is lockscreen | First visible frame is lockscreen | 20 cycles; active app; short/long sleep |

Use non-sensitive test data. Do not record private conversations or authentication codes. Remove temporary microphone recordings after analysis unless the user asks to retain them.

---

# 5. Performance and stability constraints

- Do not add multi-second sleeps to hide races.
- Prefer events/readiness handshakes over polling.
- Do not keep multiple hidden app instances alive just to make UI appear correct.
- Avoid substantial background CPU/memory overhead.
- Avoid full-window relayout on every pointer event.
- Coalesce only where appropriate (e.g. rapid volume cue bursts).
- Preserve startup performance, existing prewarm policy, alarms, timers, speaker playback, Bluetooth, display, touch, Wi-Fi, and SSH.
- Measure before/after latency, CPU, memory, and audio where relevant.

---

# 6. Deliverables

Produce:

1. Root-cause report for every item: Signal portrait; Telegram portrait; WhatsApp portrait; WhatsApp keyboard; WhatsApp mic; volume pow; Caprine; Flatpak Back; landscape keyboard; spoofer Apply; Ferdium; lockscreen wake.
2. Implementation summary with exact changed files and reasons.
3. Test report with exact commands, results, and skipped tests.
4. Physical verification table: `PASS`, `FAIL`, `PARTIAL`, or `NOT TESTED`.
5. Before/after layout and wake evidence (screenshots/video where practical and safe).
6. Audio evidence: nodes, stream formats, routing, XRUN/dropout status, listening result; no private recordings unless explicitly requested.
7. Spoofer scope proof: only Apply path changed; settings/reset behavior preserved.
8. Deployment record: installed build/hash, services restarted, backup path.
9. Exact rollback commands.
10. Remaining limitations and blockers.

Do not say “all fixed” if an item is only unit-tested or not physically verified.

---

# 7. Definition of done

PWNAGE 90000 is complete only when:

- Signal is compact and genuinely usable in portrait, with no inaccessible primary controls.
- Telegram has a modestly larger portrait viewport with no landscape regression.
- WhatsApp is responsive in portrait; composer opens Nuxel keyboard; microphone recordings no longer have the diagnosed crackle/glitch/doubling/slowdown defect.
- Hardware volume buttons play the existing “pow” cue while changing volume correctly.
- Caprine consent notice and all available controls are reachable/tappable in both orientations without automatic consent.
- Triple-button Back works in tested Flatpaks via supported focused input/navigation, without breaking text entry, Home, or Tabs.
- Landscape keyboard uses full available width and updates through rotation.
- Spoofer Apply reliably invokes the existing selected configuration; no other spoofer behavior changes.
- Ferdium is usable and scrollable in portrait; landscape remains good.
- Every locked wake presents the correctly scaled lockscreen first; no zoomed desktop or app frame ever flashes.
- No regressions in native GTK, Flatpaks, audio playback, alarms, timers, display, touch, networking, or app lifecycle.
- Changes are deployed to the real phone and physical acceptance results are documented.

If a requirement cannot be completed safely or is technically blocked by the application/runtime, do not fake it. Report the evidence, what was completed, and the safest next step.

---

# 8. Final report format

1. Overall result: `COMPLETE`, `PARTIALLY COMPLETE`, or `BLOCKED`.
2. Root cause per issue.
3. Fixes implemented.
4. Physical test results (`PASS` / `FAIL` / `PARTIAL` / `NOT TESTED`).
5. Explicit spoofer scope confirmation.
6. Exact changed files and purpose.
7. Build/test commands and results.
8. Deployment version/hash and backup path.
9. Exact rollback commands.
10. Remaining work.

Be technically precise, evidence-driven, and conservative. The objective is a phone that works correctly in the user's hands—not a green test summary that conceals unresolved physical behavior.
