# Edge screen completion report — Galaxy S10+ (`beyond2lte`)

## 1. Executive verdict

`NOT_IMPLEMENTED` (userspace-achievable). The S10+ has a real curved 1440×3040
Dynamic AMOLED panel and a Samsung `sec_ts` (S6SY761 / Y771) touch controller
whose downstream kernel driver contains edge-handler, edge-zone and edge-dead-
zone support. Nuxel currently runs none of the Samsung "Edge screen" feature
set: there is no edge-panel UI, no edge-swipe recognizer, no edge-lighting
overlay and no service that configures the controller's edge/grip zones. The
driver's live grip state is still the default `grip(0), edh:0, edg:0, lan:0`
(all edge handling disabled). This is a missing **userspace feature layer**, not
a missing display or touch transport.

## 2. Target identity

- SM-G975F `beyond2lte`, Exynos 9820, 6.4-inch curved Dynamic AMOLED.
- Framebuffer: `fb0` virtual size `1440,6080` (double-buffered), stride `5760`,
  32 bpp → real panel mode 1440×3040.
- Touch: `sec_touchscreen`, Samsung S6SY761 (`sec_ts`, I²C `hsi2c_10` @ `0x48`,
  driver module id `SE56023300L1`, vendor `LSI_y771`).
- Touch coordinate space: DT `sec,max_coords = <0x1000 0x1000>` (4096×4096 raw).
- Edge geometry from DT `sec,area-size = <0x85 0x10a 0x155>`:
  - indicator `133` raw units
  - navigation `266` raw units
  - **edge `341` raw units** ≈ 120 physical px per side at 1440 wide, ≈ 30
    logical px in the current 360×760 Home viewport.
- Confidence: **high** for panel/touch identities, edge geometry and driver
  capability; **unproven** for physical edge-swipe ergonomics and curved-edge
  visual treatment on the owner's unit.

## 3. What already exists

| Area | Source/path |
|---|---|
| Display bridge | `tools/s10plus/a29/nuxel-wl-fb.c`, `nuxel-wl-fb.service` |
| Touch arming | `services/nuxel-s10/`, `nuxel-touch-arm.service` |
| Touch driver | downstream `sec_ts/y771` in `kernel/s10plus/.build/src/drivers/input/touchscreen/sec_ts/` |
| Touch DT | `/sys/firmware/devicetree/base/hsi2c@104B0000/touchscreen@48` (max coords, area-size, FOD, AOT, 120 Hz) |
| Home/PWA host | `pwa/nuxel-home`, `tools/s10plus/a45/nuxel-pwa-host.c` |
| Native chrome | `tools/s10plus/a45/nuxel-statusbar.c`, `nuxel-navdock.c`, `nuxel-osd.c` |
| Gesture owner | `pwa/nuxel-home/js/gestures.js`, `js/qs.js`, `js/launcher.js` |
| Notifications | `services/nuxel-notifications`, expanded Quick Settings list |
| Edge-specific UI/service | **none in the repository** |

## 4. Latest evidence

| Check | Result | Tier |
|---|---|---|
| Panel framebuffer | `1440,6080`, stride `5760`, 32 bpp (1440×3040 real) | `PASS_DEVICE_RUNTIME` |
| Touch input device | `sec_touchscreen` on `/dev/input/event2`, `sec_touchpad` on `event3`, `sec_touchproximity` on `event4` | `PASS_DEVICE_RUNTIME` |
| Touch controller | `module_id=SE56023300L1`, `vendor=LSI_y771`, `support_feature=5 aot RR120hz` | `PASS_DEVICE_RUNTIME` |
| Edge geometry | DT `area-size = 133 / 266 / 341` raw units; edge band ≈ 120 px physical | `PASS_DEVICE_RUNTIME` |
| Grip sensor input | `grip_sensor` on `/dev/input/event5`, `REL=0x200`, `EV=0x5` | `PASS_DEVICE_RUNTIME` |
| Driver edge support | `SEC_TS_CMD_EDGE_HANDLER 0xAA`, `SEC_TS_CMD_EDGE_AREA 0xAB`, `SEC_TS_CMD_EDGE_DEADZONE 0xE5`, `set_grip_data` | `PASS_SOURCE` |
| Live edge state | dmesg `sec_ts_set_grip_type: re-init grip(0), edh:0, edg:0, lan:0` → **disabled** | `PASS_DEVICE_RUNTIME` |
| Kernel config | `CONFIG_TOUCHSCREEN_SEC_TS_Y771=y`; no `CONFIG_JOYSTICK_GRIP*` | `PASS_DEVICE_RUNTIME` |
| Nuxel edge panel / lighting / gesture | no source, service or config found | `PASS_SOURCE` |
| Synthetic edge-swipe injection | uinput probe created a virtual touch device, but Home received no pointer/touch event; **not evidence of physical acceptance** | `BLOCKED_SYNTHETIC` |
| Physical edge swipe | not yet performed by the owner | `NOT_TESTED` |

## 5. Full dependency chain

| Stage | Current state | Evidence |
|---|---|---|
| Curved AMOLED panel + DSI | working | framebuffer geometry |
| Touch controller + firmware | working, no separate firmware file (`embedded-in-sec_ts`) | input device + module id |
| Raw multitouch events | working (Home/QS/nav gestures already use them) | live UI tests |
| Edge geometry (`area_edge`) | present in DT (341 raw units) | DT `sec,area-size` |
| Edge handler / grip rejection | driver code present, **disabled at runtime** | dmesg `edh:0, edg:0` |
| Edge gesture recognizer | **missing** | no edge code in `gestures.js`/`nuxel-pwa-host` |
| Edge panel UI | **missing** | no panel/overlay assets or service |
| Edge lighting overlay | **missing**; not an LED path | `REPORT-LEDS.md` confirms no edge LED |
| Notification/tool content API | notifications and app registry already exist | bridge APIs |
| Haptics/visual feedback | OSD + haptics services exist | `nuxel-osd`, `nuxel-haptics` |

## 6. First failing stage

**Userspace edge-feature layer.** Everything needed to detect a deliberate
inward swipe from the curved side and draw a panel already exists. The kernel
driver even exposes `set_grip_data` for the controller's edge handler and edge
zone. What is absent is:

- an edge-band gesture recognizer with arbitration against the existing Home
  drawer, Quick Settings and bottom nav gestures;
- an edge-panel surface and its content model;
- an edge-lighting presentation for notifications;
- a service/policy that configures and verifies the controller's edge/grip
  zones instead of leaving them at `0`.

## 7. Why prior attempts have not completed the feature

- Samsung's "Edge panels", "Edge lighting" and "Edge touch" are proprietary
  One UI userspace features. Nuxel intentionally does not ship the Samsung
  Android framework or its edge services.
- The existing gesture owner (`js/gestures.js`) only handles the top-edge
  Quick Settings pull and the bottom-up app drawer. It has no left/right edge
  band and rejects scroll-origin gestures.
- The touch driver's edge handler is disabled; no Nuxel code calls
  `set_grip_data`, so palm/grip rejection and deliberate edge gestures cannot be
  distinguished.
- `REPORT-LEDS.md` already established that "Edge lighting" is a display
  overlay, not an LED; no display overlay was implemented.

## 8. Best recommended architecture

**Primary (v1, no reflash): Nuxel-native edge layer in the Home PWA.**

1. **Edge-band recognizer** (`pwa/nuxel-home/js/edge-panel.js` or an extension of
   `gestures.js`):
   - left/right band ≈ 24–32 logical px, derived from DT `area_edge`;
   - require an inward horizontal swipe of ≥ 42 px with vertical skew below a
     bounded ratio;
   - establish direction before acting; never steal vertical scrolling;
   - `pointercancel`/`touchcancel` and panel close reset all state;
   - an accessibility alternative (edge button in Quick Settings or a panel
     entry in Home settings).
2. **Edge panel overlay**:
   - bounded panel, not a full-screen modal backdrop;
   - quick app shortcuts from the canonical registry, plus notifications and a
     clipboard/tool section;
   - no invented app identities; reuse the icon-origin policy from PWNAGE-93000;
   - close on outside tap, Back, or an outward swipe.
3. **Edge lighting**:
   - a restrained two-edge gradient overlay driven by the notification hub;
   - no continuous animation, no blur-heavy effects, respect reduced-motion and
     DND; it is presentation only and never claims a notification was read.
4. **Optional controller tuning** (only after verification):
   - use the already-registered `set_grip_data` TSP command to set a documented
     edge zone/grip policy, e.g. `set_grip_data,1,<edge>,<up_x>,<dn_x>,<y>`;
   - read back `cmd_status`/`cmd_result` and dmesg (`edh`, `edg`) before claiming
     success;
   - never write raw sensor registers, calibration or EEPROM.
5. **Do not** introduce a second compositor or a `/dev/fb0` writer. The Home
   WebView, native navdock and layer-shell status bar remain the presentation
   path.

**Alternative:** a native layer-shell edge surface if the PWA gesture path
proves unreliable under compositor-level edge grabs. This is a larger native
change and should only follow measured failure of the PWA path.

## 9. Required work inventory

| Area | Work |
|---|---|
| Gesture | left/right edge band, inward-swipe recognizer, arbitration, cancel/reset, accessibility |
| UI | edge panel markup/CSS, app/notification/tool sections, open/close animation budget |
| Notifications | edge-lighting event source from the PWNAGE-93000 hub; DND/reduced-motion policy |
| Bridge | read-only panel content RPCs (apps already exist; add clipboard/tools only if a real provider exists) |
| Touch policy | optional `set_grip_data` edge zone + readback; landscape/portrait behavior |
| Diagnostics | edge-band geometry, gesture state, panel state, controller `edh/edg`, last gesture result |
| Tests | left/right swipe, accidental palm, vertical scroll arbitration, drawer/QS coexistence, rotation, panel reopen, DND |
| Physical | owner finger sweeps on both curved sides in portrait and landscape |

## 10. Source/upstream research

- Kernel: Samsung downstream `sec_ts/y771` driver. It exposes:
  - `SEC_TS_CMD_EDGE_HANDLER (0xAA)`
  - `SEC_TS_CMD_EDGE_AREA (0xAB)`
  - `SEC_TS_CMD_EDGE_DEADZONE (0xE5)`
  - `set_grip_data` with portrait/landscape edge and dead-zone parameters.
- `location_detect()` classifies raw X as `E.`/`C.`/`e.` using `area_edge`,
  proving the driver already knows the curved-side bands.
- Samsung One UI Edge Panels/Edge Lighting are proprietary and are not a
  dependency we can ship. Nuxel should implement an equivalent feature rather
  than transplanting Android framework code.
- No upstream Linux edge-panel service exists for this device; the natural
  owner is Nuxel Home because it already owns gestures, notifications and the
  app registry.

## 11. Buildability

- The v1 PWA + bridge implementation builds with the existing Nuxel Home
  pipeline (`nuxel-web`, `nuxel-pwa-host`, service-worker cache bump).
- No kernel/boot flash is required for v1.
- Controller `set_grip_data` is already registered in the live driver; test it
  with a reversible, logged command and read back the result.
- Physical ergonomics (edge band width, palm rejection) cannot be validated from
  source alone; owner sweeps are required.

## 12. Risks and constraints

- Over-wide edge bands can steal normal app edge touches and Back gestures.
- Aggressive grip rejection can make thin controls near the sides unusable.
- `set_grip_data` values are controller/panel-specific; incorrect values can
  make edge touches dead or oversensitive.
- Edge lighting must not become a continuous animation or a fake "notification
  cleared" indicator.
- The curved sides are part of the active display; do not mask them with a
  permanent opaque frame.

## 13. Phased roadmap

| Phase | Goal | Gate |
|---|---|---|
| 0 | Read-only edge diagnostic: DT geometry, `edh/edg`, gesture hit bands | No input policy change |
| 1 | Edge panel opens from a deliberate inward swipe on one side | Physical owner swipe |
| 2 | Both sides, portrait + landscape, panel content from real registry | No drawer/QS regression |
| 3 | Optional `set_grip_data` edge/grip tuning with readback | dmesg + touch tests prove improvement |
| 4 | Edge lighting from real notifications, DND/reduced-motion aware | No fake state, no continuous animation |
| 5 | Accessibility and settings controls | Owner acceptance |

## 14. Acceptance test matrix

| Test | Required evidence |
|---|---|
| Left inward swipe | panel opens, exactly one open event, no app launch |
| Right inward swipe | same, independent state |
| Vertical scroll from edge | scroll wins; panel never opens |
| Palm/grip contact | no accidental panel, no stuck gesture |
| Drawer/QS coexistence | top pull, bottom-up drawer and edge swipe all work after each other |
| Panel close | outside tap/Back/outward swipe all close; state resets |
| Rotation | gesture state resets; panel usable in both orientations |
| Notification edge lighting | real notification produces a bounded glow; read/archive semantics unchanged |
| DND/reduced motion | lighting suppressed appropriately |
| Repeated cycles | ≥20 edge open/close cycles with no stuck input |

## 15. Owner inputs required

- Physical edge-swipe ergonomics session on the S10+ (both sides, portrait and
  landscape).
- Decision on edge-panel content (apps only vs. apps + notifications + tools).
- Permission to tune controller edge/grip zones if defaults are poor.
- Confirmation of preferred edge-lighting intensity/colour within the Nuxel
  theme.

## 16. Confidence and gaps

- **Proved:** curved 1440×3040 panel; `sec_ts` edge-capable driver; DT edge
  geometry; grip sensor present; edge handling disabled at runtime; no Nuxel
  edge UI/service exists.
- **Inferred:** a PWA edge band + panel is the least invasive path and can ship
  without a kernel flash.
- **Unknown:** physical palm-rejection quality, best edge-band width, owner
  preference for panel content, whether controller edge tuning is needed.
- **Blocked for physical acceptance:** no owner finger sweep was available in
  this run; the synthetic uinput probe did not reach Home and is explicitly not
  promoted as touch acceptance.

## 17. Reflash impact (controlled maintenance)

| Question | Answer |
|---|---|
| Does the v1 edge feature require a reflash? | **NO.** PWA + bridge + service-worker update only. |
| Does edge/grip tuning require a reflash? | **NO**, while the existing `set_grip_data` TSP command is used and read back. |
| What would force a reflash? | Only a kernel/DT change (new sysfs ABI, changed edge defaults, or a native compositor surface that must be in the base image). |
| Can this be batched with other missions? | **YES, but it should not block them.** Edge v1 can ship in the same userspace batch as PWNAGE-93000 without a flash. |
| Controlled reflash batch rule | If a later edge change needs kernel/DT work, batch it with the camera/fingerprint/GPS/NFC/USBNET reflash list in one A/B system+boot flash, not a separate emergency flash. |
| Rollback | Revert the PWA/bridge files and bump the service-worker cache; no partition restore needed for v1. |
