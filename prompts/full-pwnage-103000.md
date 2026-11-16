# FULL-PWNAGE-103000 — Nuxel LED, Torch, Edge Lighting & Edge Screen

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte` / Exynos 9820  
**Mission type:** userspace feature implementation + live-device verification  
**Deployment:** Wi-Fi SSH to the owner's running Nuxel phone  
**Reflash requirement:** none for the intended v1 implementation  
**Priority:** correctness and safety first; polished, buttery-smooth UI second

---

## 0. Mission directive

Implement and verify Nuxel's real rear flashlight/torch path, an honest notification-lighting architecture, and a Nuxel-native equivalent of the Galaxy S10+'s Samsung Edge lighting / Edge screen experience.

The finished result must provide:

1. A safe, explicit rear torch toggle using the real `torch-sec1` LED class, with strict OFF-by-default, timeout, cleanup and thermal/battery policy.
2. A notification Edge Lighting engine rendered on the curved AMOLED display, driven by real Nuxel notification events—not by a fake LED device and never by the camera flash.
3. Several selectable effects inspired by the original S10 Edge lighting styles. Implement the full eight-style family if feasible: **Basic, Wave, Bubble, Multicolor, Heart, Fireworks, Eclipse and Echo**.
4. **Wave selected by default**, with the current Nuxel theme accent as its default color. The default must be stored in the real settings/policy path and survive service-worker reloads/reboots.
5. User controls for effect, color, width/intensity, transparency, duration, notification sources, screen-state behavior and a safe preview/test action.
6. A Nuxel Edge Panel opened by a deliberate inward swipe from either curved side, with real app shortcuts and notifications from canonical Nuxel providers. Include accessibility/Quick Settings access so the panel is not gesture-only.
7. Correct portrait/landscape handling and strict arbitration with existing Home, Quick Settings, Back/navigation, launcher and app scrolling gestures.
8. Diagnostics, tests, deployment evidence and rollback instructions. Do not claim physical acceptance where only a software/synthetic test was performed.

Do not merely write a plan. Inspect the repository, implement the feature, build/test it, deploy the userspace changes to the connected phone, and verify the live runtime. If a stage cannot safely be completed, finish all independent work and report the exact blocker and evidence.

## 1. Live target and SSH connection — mandatory

The phone is expected to be powered on and connected to Wi-Fi when this mission is executed.

- Remote user: `root`
- Remote address: `192.168.178.167`
- SSH identity: `~wicked/.ssh/wicked_wqn_id_rsa`
- Expected device: Samsung Galaxy S10+ `SM-G975F`, codename `beyond2lte`, Exynos 9820

Connect from the development machine (not from an assumed shell on the phone):

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o BatchMode=yes -o ConnectTimeout=8 \
  root@192.168.178.167
```

Before doing anything mutating:

1. Confirm the key path is readable by the current local execution user. `~wicked` means the local account named `wicked`; do not silently substitute another key or print/copy the private key.
2. Use normal SSH host-key verification. Do **not** add `StrictHostKeyChecking=no`, disable host-key checking, or blindly rewrite `known_hosts`. If host identity cannot be verified, stop the remote mutation stage and report the fingerprint/verification blocker.
3. Confirm SSH is actually connected and that the remote account is `root` (`id -u` must be `0`).
4. Verify model/codename from live device properties/sysfs. Do not assume the IP still points to the intended phone merely because SSH succeeds.
5. Record date/time, kernel, OS release, current service state and current git/build identifiers if available.
6. Use this exact SSH target for remote work. Do not scan other LAN hosts or change Wi-Fi/network configuration.

Suggested read-only preflight:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o BatchMode=yes -o ConnectTimeout=8 \
  root@192.168.178.167 \
  'id; uname -a; cat /etc/os-release 2>/dev/null; \
   for p in /sys/firmware/devicetree/base/model /sys/class/leds/torch-sec1/max_brightness; do \
     [ -r "$p" ] && { printf "\\n--- %s ---\\n" "$p"; cat "$p"; }; \
   done'
```

The path above may need to be adjusted for the actual device-tree representation; preserve the raw evidence. Never expose secrets, private key material, notification contents or other personal data in the final report.

## 2. Authoritative hardware and software facts

Treat the following as supplied diagnostic evidence, not as a substitute for a fresh read-only check. Reconcile any differences with the live device and clearly label the newer result.

### 2.1 Device/display/touch

- Device: `SM-G975F` (`beyond2lte`), Exynos 9820.
- Panel: curved 6.4-inch Dynamic AMOLED, nominal active mode 1440×3040.
- Framebuffer previously observed: `fb0` virtual size `1440,6080`, stride `5760`, 32 bpp (double-buffered).
- Touch controller: Samsung `sec_ts`, S6SY761 / Y771, I²C `hsi2c_10` at `0x48`.
- Touch input device previously observed as `sec_touchscreen` at `/dev/input/event2`; `sec_touchpad` event3; `sec_touchproximity` event4; `grip_sensor` event5.
- Controller module ID previously observed: `SE56023300L1`, vendor `LSI_y771`.
- Device-tree `sec,max_coords` previously observed as `4096 × 4096`.
- Device-tree `sec,area-size` previously observed as `133 / 266 / 341` raw units. The final edge band is 341 raw units, estimated at ~120 physical pixels per side or ~30 CSS/logical px in the current 360px-wide Home viewport. Treat this as an initial calibration hint, not a universal hard-coded value.
- Driver source previously exposed `SEC_TS_CMD_EDGE_HANDLER (0xAA)`, `SEC_TS_CMD_EDGE_AREA (0xAB)`, `SEC_TS_CMD_EDGE_DEADZONE (0xE5)` and `set_grip_data`.
- Runtime grip state previously logged `grip(0), edh:0, edg:0, lan:0`; edge handling was disabled.

### 2.2 Actual LEDs

Previously enumerated live classes:

- `/sys/class/leds/torch-sec1` — rear camera torch/flash path. Its `brightness` control worked for a bounded one-second ON/OFF test. Physical illumination was not confirmed by the owner in that test session.
- `/sys/class/leds/leds-sec1` — second Samsung/PMIC LED-class node. Do not assume it is a notification RGB LED; inspect `type`, `brightness`, `max_brightness`, `trigger`, device symlink, driver binding and source semantics before assigning it any user-facing role.

Previously established:

- PMIC driver binding: `9-0059/s2mpb02-led` / `s2mpb02-led`.
- No dedicated notification LED class was exposed.
- No verified RGB/multicolor notification LED channels were exposed.
- The Galaxy S10 family has no conventional notification LED. Samsung's documented replacement is display-based Edge lighting.
- Samsung Edge lighting is a **display effect**, not a physical LED and not a reason to drive the camera flash.

### 2.3 Existing Nuxel components to inspect and reuse

The supplied reports identify these paths. Confirm the actual current repository layout before editing:

| Component | Existing path / responsibility |
|---|---|
| LED policy | `configs/nuxel/leds/leds.json` |
| Flashlight provider | `services/nuxel-bridge/src/flashlight_provider.py` |
| LED/notification provider | `services/nuxel-bridge/src/led_notification_provider.py` |
| LED diagnostics | `tools/s10plus/a33/nuxel-led-diag.sh` |
| LED safety tests | `tests/pwnage65000` and related tests |
| Display bridge | `tools/s10plus/a29/nuxel-wl-fb.c`, `nuxel-wl-fb.service` |
| Touch arming | `services/nuxel-s10/`, `nuxel-touch-arm.service` |
| Downstream touch driver | `kernel/s10plus/.build/src/drivers/input/touchscreen/sec_ts/` |
| Home/PWA host | `pwa/nuxel-home`, `tools/s10plus/a45/nuxel-pwa-host.c` |
| Native chrome | `tools/s10plus/a45/nuxel-statusbar.c`, `nuxel-navdock.c`, `nuxel-osd.c` |
| Existing gesture owner | `pwa/nuxel-home/js/gestures.js`, `js/qs.js`, `js/launcher.js` |
| Notification service | `services/nuxel-notifications` |
| Haptics | existing `nuxel-haptics` service/provider |
| Edge panel/edge lighting feature | no implementation was found in the supplied report |

The owner also reports a prior Nuxel userspace mission (`PWNAGE-93000`) involving the notification hub. Inspect its current implementation and API; do not invent a second competing notification source or duplicate notification state.

## 3. Critical product interpretation: what Samsung Edge lighting actually does

The original Galaxy S10/S10+ manual documents Edge lighting as a temporary visual alert on the screen edges when a call or notification arrives. It makes alerts visible when the phone is face-down. Its original eight selectable effect names are:

| Effect | Nuxel-native visual target |
|---|---|
| **Basic** | A clean, continuous illuminated edge outline/pulse. |
| **Wave** | Several curved wave/trail bands travel or ripple along the two side edges. |
| **Bubble** | Small light dots/bubbles rise or drift along the side edges and fade. |
| **Multicolor** | A smooth multi-hue edge border/gradient; use restrained color transitions, not a flashing rainbow strobe. |
| **Heart** | Small heart-shaped particles travel/fade near the edge bands. |
| **Fireworks** | Brief radial/starburst-like particle bursts near the side edges, then fade. |
| **Eclipse** | A round/crescent or eclipse-like light shape grows/fades near an upper edge region. |
| **Echo** | Repeated parallel wave/ring-like vertical bands pulse along both sides. |

The visual targets above are an interpretation of Samsung's documented effect names and S10 manual preview thumbnails. Recreate the visual language with original Nuxel code/assets; do not copy Samsung binaries, private APIs, artwork, or proprietary framework code.

**Important correction:** this is not normally a permanently animated edge decoration that runs just because the display is on. It is a transient event effect triggered by incoming notifications/calls. The S10 manual documents `While screen is on`, `While screen is off`, and `Always` behavior. It also documents configurable effect, color, transparency, width and duration, plus choosing which apps can activate the effect. Samsung's current support material describes Edge lighting as lighting around the screen/camera cutout for notifications, and confirms that S10/Note10 and newer devices do not have a conventional notification LED.

For Nuxel, implement notification effects as event-driven, bounded animations. Do not run an idle loop. If a separate camera-cutout ring effect is considered, treat it as an optional later enhancement; do not misrepresent it as one of the eight S10 manual effects or block this mission on it.

## 4. Repository reconnaissance — do this before coding

Find the real Nuxel repository on the development machine. Start with the current working directory and `git rev-parse --show-toplevel`. If that fails, inspect likely workspace locations (including `~/x/nuxel`) and verify the Git remote is the Nuxel repository before proceeding. Do not assume the phone itself is the source repository.

Record:

- current branch, commit, dirty/untracked files; never discard user changes;
- PWA build/test commands and current service-worker cache/version mechanism;
- how Home JS modules are registered/bundled;
- current notification event schema, API, app/source identity and notification action semantics;
- current Quick Settings settings/persistence architecture;
- current settings/preferences storage and schema migration conventions;
- current display/compositor layering and how notifications/OSD overlays are drawn;
- current orientation/viewport handling;
- flashlight provider API, permissions, timeout code, and policy loading path;
- existing service restart/reload mechanisms;
- all relevant tests and the repo's golden/smoke gates.

Search for existing LED/flashlight/edge/notification implementations and reuse their owners. Do not add a duplicate daemon if an existing bridge/service can own the functionality. Read complete relevant files and call sites rather than editing from a grep snippet alone.

Before modifying any file, create a reversible working diff/backup according to repo conventions. Preserve unrelated changes. Do not reset, clean, force checkout, rewrite history, or overwrite unrelated user work.

## 5. Desired architecture

### 5.1 Torch: real flashlight only

Keep torch control in the existing flashlight provider/bridge and policy file. The rear torch is the only LED capability that is positively established.

Requirements:

- Use the existing supported LED-class/provider path. Confirm the live class and device binding before every hardware test.
- Default OFF at boot, service start, provider initialization, exception, timeout and shutdown.
- Explicit user action required to turn it ON. Never turn it on for notifications, edge effects, boot animation, camera-independent animation or a scheduled task.
- Enforce the existing policy ceiling `max_on_ms=600000` (10 minutes) unless the live code has a stricter documented policy. Do not increase it. Prefer a substantially shorter UI/session default timeout if the established product policy supports it; expose remaining time and explicit OFF.
- Use existing battery and thermal telemetry providers if available. Inspect their real fields, units and freshness. Do not invent thermal thresholds or trust stale/unknown telemetry. If telemetry is unavailable, fail conservatively and retain a hard timeout.
- Always schedule an OFF operation that survives provider exceptions and request cancellation. Ensure the timeout is enforced by the provider/daemon, not only by a browser timer.
- Make ON/OFF operations idempotent, serialized and race-safe. On a failed write, re-read state and make a best-effort OFF; report the exact error.
- No automatic boot activation, no continuous notification lamp, no Morse/SOS behavior in this mission.
- Do not manipulate undocumented PMIC registers or camera-flash driver internals.
- Do not infer physical LED visibility from sysfs writes. Record `CONTROL_PATH_OK` separately from `OWNER_PHYSICAL_VISIBILITY_CONFIRMED`.

Inspect `torch-sec1` and `leds-sec1` attributes and their driver bindings. Determine whether `leds-sec1` has a real documented use; leave it untouched unless source and physical/capability evidence justify a role. Do not label it RGB or notification merely from its name.

### 5.2 Notification indication: AMOLED overlay, never a fake LED

Implement a display-based notification effect integrated with the existing Home/display stack and the actual notification service.

- The notification provider publishes event metadata to one canonical edge-lighting controller.
- Edge-lighting subscribes to real, supported events and uses only non-sensitive display metadata by default (source/app, category, chosen color). Never expose private message bodies or contact names on the lockscreen by default.
- The animation is presentation-only. It must not mark a notification read, dismiss, archive, reorder or mutate its state.
- Notification click/open behavior must call the existing canonical notification action; do not fabricate app IDs or deep links.
- Do not add a second compositor, second framebuffer writer, raw `/dev/fb0` drawing path, or a competing notification daemon.
- Render through the existing PWA/WebView/compositor layer. Reuse the existing OSD/overlay conventions where possible.
- The overlay must respect the display safe areas and the curved edges; no permanent opaque side mask/frame.
- Use a single reusable overlay root and effect renderer. Remove/destroy animations after their bounded lifecycle. Prevent detached DOM, RAF/timer and event-listener leaks.

#### Event behavior

- One real notification event produces one bounded animation. A reasonable default total duration is about 1.5–2 seconds, configurable by the user; no infinite looping.
- Coalesce bursts/repeated notifications. Avoid restarting the animation on every progress update or duplicate event. Define a short deduplication window using the real notification ID/provider semantics.
- Respect DND/silent policy, per-app allowlist, reduced-motion preference and system power policy.
- If notification metadata is missing or stale, use the default theme color; do not invent an app color.
- Never treat a test/preview event as a real notification or change notification state.
- Do not show private notification text on the lockscreen unless a separate existing privacy setting explicitly allows it.

#### Screen state policy

Provide these user-facing modes if and only if the current display stack can genuinely support them:

1. **Screen on** — show the event animation while the display is active. This is the required v1 mode.
2. **Screen off** — show only if the existing Nuxel display/power architecture has a safe, supported way to render a short edge-only/low-power effect while the panel is otherwise off.
3. **Always** — apply the effect to supported notification events regardless of screen state, only if the underlying off-screen behavior is actually supported.

Do not claim screen-off Edge lighting works merely because the WebView can draw while the display is on. Do not wake the whole panel or expose a notification body to simulate edge-only lighting. First inspect the existing display bridge, backlight/blanking path, AOD capabilities and notification wake policy. If there is no real low-power edge-only render path, ship the screen-on mode and expose screen-off/always as clearly unavailable (or omit those choices with an honest explanation). No custom framebuffer hacks.

### 5.3 Effect engine and styles

Implement the eight S10-style choices as original Nuxel animations where practical. The design must be buttery-smooth on the S10+ and remain lightweight on the live display path.

**Required effects:**

- `basic`
- `wave`
- `bubble`
- `multicolor`
- `heart`
- `fireworks`
- `eclipse`
- `echo`

Use CSS transforms/opacity and existing supported animation primitives first. Avoid blur-heavy filters, huge particle counts, continuous layout measurement, large canvases, per-frame React/PWA state updates, GPU-unfriendly `box-shadow` animation, or unbounded Web Animations. Keep the number of animated elements small, prefer transform/opacity, and use `will-change` only while an animation is active.

Implementation detail targets:

- **Basic:** edge glow line/pulse, restrained, follows both curved sides.
- **Wave:** two or three staggered curved light traces moving along the side bands; selected as the default.
- **Bubble:** small low-count dots rising/fading with varied phase; no random DOM creation per frame.
- **Multicolor:** controlled gradient shift or color sweep; do not strobe or flash full brightness.
- **Heart:** small simple vector/CSS heart particles; use original shapes, low particle count.
- **Fireworks:** short radial strokes/dots near the side edges; brief burst and quick fade.
- **Eclipse:** one/two crescent/ring forms near the upper corners/edge bands, expanding/fading.
- **Echo:** several narrow parallel bands that pulse/fade in sequence along the sides.

All eight effects must:

- animate from one central controller with one cancellable lifecycle;
- support both sides and rotation/resizing;
- stop immediately when disabled, DND activates, notification is withdrawn where relevant, display policy requires it, or reduced motion says to suppress motion;
- have a static/near-static alternative for reduced motion;
- avoid covering tappable Home/navigation controls longer than necessary;
- use pointer-events none except any deliberately implemented notification pop-up interaction target;
- include a preview/test action that does not create a real notification or mutate its state;
- be deterministic enough for reliable screenshot/visual regression tests.

If a style cannot be made performant or visually credible, mark it unavailable rather than presenting a fake tile. The target is eight usable effects, but six polished styles are better than eight broken ones. Do not copy Samsung preview images or assets.

### 5.4 Defaults and settings UI

Set the actual persisted default to:

```json
{
  "enabled": true,
  "effect": "wave",
  "color_mode": "theme",
  "color": null,
  "width": "medium",
  "transparency": "medium",
  "duration_ms": 1800,
  "screen_mode": "screen_on",
  "respect_dnd": true,
  "respect_reduced_motion": true
}
```

This is a target schema/example, not permission to overwrite the real config schema. Adapt it to the repository's existing policy format and add a compatible migration/defaulting path. Do not leave JSON comments or unsupported fields in a real JSON file. `enabled: true` means notification edge lighting is enabled; it must not mean the torch turns on.

Default behavior:

- Effect: **Wave**.
- Color: current Nuxel theme accent token. Resolve it from the theme at runtime. Use a subtle cyan/blue fallback only if the theme has no accent token; do not fork hard-coded colors across effects.
- Width/intensity: medium.
- Transparency: medium.
- Duration: approximately 1800 ms.
- Screen policy: `screen_on` until screen-off support is independently proven.
- DND and reduced-motion: respected by default.

Settings UX should provide:

- master Edge Lighting on/off switch;
- effect picker with recognizable preview tiles for every implemented effect;
- per-effect preview/test action;
- theme accent, preset color and custom color where the current color model supports it;
- optional app/source color mapping only from real app identities; fallback to theme color;
- width/intensity, transparency and duration controls;
- screen-state policy with capability-based availability;
- manage-app/source list using canonical notification provider IDs;
- DND and reduced-motion status/behavior;
- reset to default;
- a clear explanation: **display animation, not a physical notification LED**.

Expose the same key state/status in the appropriate Quick Settings or notifications settings area. Do not clutter the global status bar with a permanently running animation.

### 5.5 Edge Panel: real side-swipe feature

Implement a Nuxel-native Edge Panel inspired by the Galaxy S10 Edge screen. This is distinct from Edge Lighting: the panel is opened by a deliberate user gesture, whereas Edge Lighting is a temporary notification effect.

**Gesture recognizer**

- Integrate with the existing gesture owner (`js/gestures.js`) or its established extension point. Do not create a second global pointer/touch listener that races the existing recognizer.
- Initial side hit band: approximately 24–32 CSS/logical px (start around 30px), derived from the supplied device-tree estimate but configurable and validated against the real viewport.
- Require a clearly inward horizontal swipe of at least ~42 CSS px. Use a bounded horizontal-dominance ratio (for example `abs(dx) >= 1.5 * abs(dy)`) and establish direction before opening.
- Do not steal vertical scrolls, browser back/forward gestures, native Back, app edge interactions, top-edge Quick Settings pull, bottom-up drawer gesture, bottom dock/nav taps or text selection.
- Use pointer capture only after the gesture has crossed a deliberate threshold and arbitration says the edge panel owns it.
- Handle `pointercancel`, `touchcancel`, lost capture, window blur, orientation change, panel close and display sleep. Every path must reset all recognizer state.
- Debounce duplicate opens; one physical swipe must create exactly one open event.
- Support left and right edges, portrait and landscape. Recompute logical bounds on `resize`/orientation changes. Never use stale 360×760 dimensions in landscape.
- Include an accessible alternative: Quick Settings item and/or Home settings/launcher entry.

**Panel surface/content**

- Build as a lightweight PWA overlay in the current Home stack. Do not create a second compositor or write to the framebuffer.
- Use a bounded side panel with a restrained dim/transparent backdrop; preserve the active app context as much as the current architecture permits.
- Provide at minimum an Apps panel populated from the canonical Nuxel app registry and a Notifications panel populated from the notification service.
- Optional Tools/clipboard entries only when there is a real provider and a real action. Never create fake app identities, placeholder apps or fake clipboard data.
- Reuse current icon-origin/trust rules: real application icons from the canonical app registry only; do not invent icon paths or substitute arbitrary image files.
- Panel items must use existing app launch and notification actions. No hard-coded package IDs unless they are already canonical registry entries.
- Close on outside tap, Back, an outward swipe, selecting an action where appropriate, display sleep or explicit close.
- Panel content must not reveal private notifications on a locked device beyond the existing lockscreen policy.
- Add sensible panel position/side and visibility settings only if they fit the established settings architecture.

### 5.6 Touch controller / grip tuning: optional, last resort

The downstream `sec_ts/y771` driver appears to support edge/grip commands, but controller values are panel-specific. The currently observed controller edge state was disabled.

Do not blindly enable or tune the controller just to make the PWA gesture recognizer work.

If and only if the current touch event stream shows a measured need for controller-side tuning:

1. Read the exact driver implementation and the exact registered `set_grip_data` command grammar for this kernel build.
2. Inspect the current controller state and command status/result interfaces.
3. Save the current state and the reversible restore procedure.
4. Try only a documented, source-verified value through the driver's supported command path.
5. Read back command status/result and inspect dmesg for `edh`, `edg`, `lan` and grip state.
6. Test ordinary center touches, side touches, palms, vertical scrolls and both edges.
7. Restore the previous value immediately if touches become dead, over-sensitive or regress.
8. Do not write raw sensor registers, calibration data, EEPROM, undocumented I²C transactions or arbitrary sysfs nodes.
9. Never claim physical acceptance based only on source inspection or synthetic `uinput` events.

If source-verified tuning is not obviously safe, leave the controller untouched and deliver the userspace gesture feature with diagnostics that state the controller policy remains unchanged.

## 6. Diagnostics and truthful capability model

Extend the existing LED diagnostic tool or add a small companion diagnostic with machine-readable JSON and a readable summary.

Report at least:

- model/codename and kernel;
- available LED classes and each node's driver, type, max brightness, trigger and live state;
- explicit capability labels for `rear_torch`, `notification_led`, `rgb_notification_led`, and `edge_display_overlay`;
- torch current state, timeout state, provider state and last error;
- notification-edge settings/default/effect availability;
- current display/screen state and whether screen-off edge lighting is genuinely supported;
- edge panel enabled/open state, last gesture outcome and current orientation;
- touch controller identity, DT edge geometry, current edge/grip state and whether controller tuning was attempted;
- DND/reduced-motion state where available;
- last real notification event timestamp/ID only if safe and non-sensitive; redact message text and personal identifiers.

Use explicit evidence tiers, for example:

- `PASS_DEVICE_RUNTIME`
- `PASS_SOURCE`
- `PASS_BUILD_TEST`
- `PASS_UI_PREVIEW`
- `NEEDS_OWNER_PHYSICAL_TEST`
- `NOT_SUPPORTED_ON_DEVICE`
- `NOT_SUPPORTED_BY_CURRENT_DISPLAY_STACK`
- `BLOCKED`

Do not report a class name as proof of RGB capability. Do not report a successful write as proof that the rear torch was physically visible. Do not report an animation preview as proof that a real notification drove the event path.

## 7. Implementation sequence

Work in these phases; do not skip the diagnostic gates.

### Phase 0 — connect, inventory, baseline

- Connect to the exact target over the supplied SSH command.
- Verify the phone identity and root access.
- Capture read-only device, LED, framebuffer/display, touch and service baselines.
- Inspect repository/current diff and current services/providers.
- Run current relevant tests before changes if feasible; record baseline failures without “fixing” unrelated issues.

**Gate:** verified target, no secrets exposed, no user work overwritten.

### Phase 1 — torch/LED truth and safety

- Verify `torch-sec1` and `leds-sec1` capabilities from live sysfs and source.
- Fix provider/policy/UI mismatches, preserve OFF-by-default and hard timeout.
- Add tests for timeout, OFF-on-exit, error cleanup, repeated ON/OFF, stale requests and boot default.
- A controlled one-second hardware ON/OFF test may be performed only through the existing supported diagnostic/provider interface, after reading its help and confirming the explicit-approval option. Always force OFF and verify the readback.
- Do not use `leds-sec1` as a notification/RGB output without proof.

**Gate:** torch software control and cleanup proven; physical visibility clearly marked owner-confirmation-needed unless an owner physically observes it.

### Phase 2 — notification Edge Lighting engine

- Connect the single edge-lighting controller to the real notification event service.
- Implement the effect registry and the supported styles.
- Implement settings, defaults, theme color resolution, DND/reduced-motion and notification deduplication.
- Implement safe screen-on rendering first. Investigate screen-off capability separately; do not promise it if the display stack cannot deliver it.
- Add preview/test without mutating notifications.

**Gate:** each effect previews correctly; a real notification creates one correct event; no notification read/dismiss side effects.

### Phase 3 — Edge Panel and side gestures

- Add side swipe recognition under the existing gesture owner.
- Add accessible entry points and real app/notification content.
- Add panel close paths, orientation handling, hit testing, lockscreen/privacy behavior and instrumentation.

**Gate:** both sides work; vertical scroll, Quick Settings, drawer, Back, dock and app controls remain functional.

### Phase 4 — controller tuning only if required

- Follow §5.6 exactly.
- Never introduce unsafe raw register or calibration writes.

**Gate:** measurable improvement and a verified restore path, or leave controller unchanged and document why.

### Phase 5 — deploy userspace, regression and rollback proof

- Build the relevant PWA/bridge/services using the repository's existing commands.
- Run unit/integration and relevant golden/smoke gates.
- Deploy only the required userspace artifacts to the connected phone.
- Bump the service-worker cache/version using the established project mechanism.
- Restart/reload only the specific service(s) required, after checking their unit definitions and impact. Do not restart the display bridge or compositor blindly.
- Verify the live UI and service status over SSH. Keep the phone usable during deployment.
- Test rollback procedure without wiping unrelated state; at minimum verify the exact prior files/config and service-worker version can be restored.

**Gate:** no partition changes, live UI works, services healthy, rollback available.

## 8. Test matrix — mandatory evidence

### 8.1 Torch

- [ ] class/provider discovery correct;
- [ ] torch OFF on boot/startup;
- [ ] ON by explicit UI action only;
- [ ] OFF by explicit action;
- [ ] short timeout forces OFF;
- [ ] global max-on policy cannot be bypassed by UI/API;
- [ ] OFF on provider exception, client disconnect, service stop and restart;
- [ ] repeated rapid toggle requests are serialized and cannot leave it ON;
- [ ] battery/thermal guard behavior uses real telemetry and fails conservatively;
- [ ] `leds-sec1` is not incorrectly advertised as RGB/notification;
- [ ] physical torch visibility is separately owner-confirmed or left pending.

### 8.2 Edge Lighting

- [ ] Basic preview;
- [ ] Wave preview;
- [ ] Bubble preview;
- [ ] Multicolor preview;
- [ ] Heart preview;
- [ ] Fireworks preview;
- [ ] Eclipse preview;
- [ ] Echo preview;
- [ ] Wave is persisted and selected by default on a clean profile and after upgrade;
- [ ] theme accent color resolves correctly;
- [ ] custom/preset color and width/transparency/duration persist;
- [ ] one real notification triggers one bounded animation;
- [ ] duplicate/progress events do not create animation spam;
- [ ] click/open does not mark unrelated notifications read or dismiss them;
- [ ] DND suppresses the effect according to policy;
- [ ] reduced-motion uses a static/minimal alternative;
- [ ] lockscreen privacy remains intact;
- [ ] display sleep/off mode is either physically proven through supported architecture or clearly reported as unavailable;
- [ ] repeated notifications do not create an endless loop or leak timers/DOM.

### 8.3 Edge Panel / gesture arbitration

- [ ] left inward swipe opens exactly once;
- [ ] right inward swipe opens exactly once;
- [ ] vertical scroll starting near either edge still scrolls;
- [ ] short side touch does not open;
- [ ] diagonal swipe does not open unless clearly horizontal by the chosen threshold;
- [ ] outside tap closes;
- [ ] Back closes;
- [ ] outward swipe closes;
- [ ] pointercancel/touchcancel resets state;
- [ ] panel content comes from canonical app registry/notification provider;
- [ ] top Quick Settings pull still works;
- [ ] bottom drawer gesture still works;
- [ ] Back/navigation/dock taps still work;
- [ ] orientation change resets recognizer and panel remains usable;
- [ ] both sides tested in portrait and landscape;
- [ ] at least 20 open/close cycles per side without stuck state;
- [ ] locked-screen content follows privacy policy.

### 8.4 Runtime and stability

- [ ] no PWA console errors;
- [ ] no service crash/restart loop;
- [ ] no new busy loop or sustained animation while idle;
- [ ] no significant scroll/gesture regression;
- [ ] no second framebuffer writer/compositor;
- [ ] no auto torch on boot/restart;
- [ ] display bridge and native chrome remain intact;
- [ ] service-worker cache refresh delivers the new code;
- [ ] rollback artifacts and commands recorded.

Do not treat unit tests, synthetic `uinput`, simulated DOM pointer events or screenshots as substitutes for owner finger sweeps on the physical curved panel. Keep the evidence tier explicit.

## 9. Performance and visual quality requirements

- Prioritize smooth rendering on the S10+ and the existing fbdev/display bridge. Avoid demanding GPU capabilities that are not exposed.
- Effects should be subtle enough to read as notification feedback, but visually recognizable as distinct styles.
- Maintain good contrast on dark and light Home states; use the existing theme system.
- No continuous animation when idle. No high-frequency polling for notifications; use existing event/callback APIs.
- Limit simultaneous active visual notifications and coalesce bursts.
- Honor orientation and viewport changes. Avoid hard-coded physical pixel offsets; use logical CSS pixels with runtime device pixel ratio only where required.
- No permanent frame or black mask over the curved display.
- Maintain safe areas around the front camera, status bar and native nav dock.
- Animations must not block taps or steal scroll input.
- Expose a preview so the owner can compare all effects in the real phone UI.

## 10. Deployment, change safety and no-reflash rules

This is a userspace mission.

**Do not:**

- flash boot, vendor_boot, dtbo, system, vendor or any partition;
- reboot the phone merely to apply a PWA/config change;
- rebuild or replace the kernel for the v1 feature;
- write undocumented PMIC registers;
- write raw touch controller registers, calibration or EEPROM;
- run an unbounded flash/torch test;
- use the camera flash as a notification lamp;
- introduce a direct framebuffer writer or second compositor;
- disable SSH host-key verification;
- delete/overwrite user data, private notifications or unrelated app settings.

**Expected deployment:** update Nuxel source/build outputs and relevant userspace policy/services, transfer the verified artifacts over the existing SSH connection, update the existing service-worker cache version, and reload only the minimum affected component(s). The supplied reports state this feature is deployable without a reflash; maintain that boundary unless code inspection proves a true kernel/DT ABI change is unavoidable. If a kernel change appears necessary, stop before flashing and report why; do not expand the scope into a flash operation.

Keep a manifest of every remote file changed, checksum, prior backup path, deployment command, service action and rollback command. Use atomic writes/renames for config and generated assets where appropriate. Validate JSON before installation. Preserve correct ownership and permissions.

## 11. Required final deliverables

At completion, provide:

1. A concise implementation summary and a truthful verdict: `FULLY_DONE`, `PARTIAL`, or `BLOCKED`.
2. Exact source files created/modified and the reason for each.
3. The effect list implemented; note unavailable styles if any; confirm `Wave` default and where it is stored.
4. Exact LED capability result (`torch-sec1`, `leds-sec1`, no notification/RGB class unless live evidence differs).
5. Torch control evidence, forced-OFF evidence and whether the physical flash was owner-confirmed.
6. Edge Lighting evidence from preview and a real notification event; report screen-on/off capability truthfully.
7. Edge Panel and gesture test results including orientation and arbitration outcomes.
8. Build/test commands and pass/fail output summaries. Include existing baseline failures separately from regressions.
9. Live device verification: model, SSH target, service health and UI/runtime evidence. Do not expose credentials or private notification text.
10. Remote deployment manifest, backup location and rollback commands.
11. Any owner-only physical acceptance steps remaining, clearly separated from completed implementation.
12. A short `PWNAGE-103000-REPORT.md` in the repository's established report location (or a sensible existing diagnostics/report folder), with evidence tiers and the same honest verdict.

Do not declare `FULLY_DONE` while the torch's physical visibility, physical edge gestures, or screen-off overlay (if advertised) still require owner verification. Use `PARTIAL` with precise owner-test items when the software work is complete but physical acceptance is pending.

## 12. Completion criteria

This mission is complete when:

- the rear torch is safe, explicit, bounded and forced OFF on all failure paths;
- Nuxel reports the absence of a physical notification/RGB LED honestly;
- notification lighting is a real display overlay driven by real notification events;
- several original S10-style effects are implemented and selectable, with Wave as the persisted default;
- DND, reduced motion and lockscreen privacy are respected;
- the Edge Panel is reachable through deliberate left/right inward swipes and an accessible alternative;
- app/notification content is real and canonical;
- portrait/landscape and gesture coexistence pass the regression matrix;
- userspace changes are live on the connected S10+ with no reflash;
- diagnostics, evidence, backup and rollback are delivered.

If any criterion cannot be met safely, do not fake it. Finish what can be completed and report the exact missing capability.

## 13. Reference material

Use these as product behavior references, not as permission to copy Samsung implementation code/assets:

- Samsung Galaxy S10e/S10/S10+ User Manual, Edge screen / Edge lighting sections (the manual documents the eight effects, color/advanced controls, app selection and screen-on/screen-off/always modes):  
  https://content.syndigo.com/asset/9cfd72b2-8ffb-494f-889a-c92daa7adafe/original.pdf
- Samsung Support — Edge lighting and LED notifications on Galaxy phones (describes notification-triggered display lighting and states Galaxy S10/Note10 and newer do not have a notification LED):  
  https://www.samsung.com/us/support/answer/ANS10003383/
- Samsung Support UK — What is Edge Lighting and how do I use it? (describes screen-on/off behavior and custom effect, color, transparency, width and duration):  
  https://www.samsung.com/uk/support/mobile-devices/what-is-edge-lighting/

---

**Execution directive:** Begin with Phase 0 now. Connect to `root@192.168.178.167` using `~wicked/.ssh/wicked_wqn_id_rsa`, verify the phone identity, inspect the repository and live device read-only, then execute the phases in order. Do not stop after writing a plan.
