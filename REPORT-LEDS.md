# LED / flash / color report — Galaxy S10+ (`beyond2lte`)

## 1. Executive verdict

`PARTIAL`. The rear torch is real and controllable via `/sys/class/leds/torch-sec1`; a bounded 1-second ON/OFF test completed and the tool forced OFF. There is **no notification LED class** exposed and **no hardware RGB/edge LED**; Samsung “Edge lighting” is a display overlay, not an LED. Physical visibility of the torch needs owner confirmation.

## 2. Target identity

- SM-G975F `beyond2lte`, Exynos 9820, S6E3HA9 AMOLED.
- Live LED classes:
  - `/sys/class/leds/torch-sec1` (rear torch/flash)
  - `/sys/class/leds/leds-sec1`
- Notification LED: absent.
- Edge lighting: display effect, `hardware_led=false`.

## 3. What already exists

| Area | Source/path |
|---|---|
| Policy | `configs/nuxel/leds/leds.json` |
| Providers | `services/nuxel-bridge/src/flashlight_provider.py`, `led_notification_provider.py` |
| Diagnostics | `tools/s10plus/a33/nuxel-led-diag.sh`, `tests/pwnage65000` |
| Safety | OFF by default; `max_on_ms=600000`; explicit `--yes`; forced OFF on exit |
| UI | Quick Settings torch; notification edge/fallback path |

## 4. Latest evidence

| Check | Result | Tier |
|---|---|---|
| `nuxel-led-diag.sh status --json` | flashlight present `/sys/class/leds/torch-sec1`, `on=false`, `state=OK`; notification absent; edge lighting not an LED | `PASS_DEVICE_RUNTIME` |
| Bounded torch test | ON via `torch-sec1/brightness` for 1000 ms; forced OFF at end | `PASS_DEVICE_RUNTIME` (control path) |
| Physical light seen | not confirmed in this session | `NEEDS_OWNER_TEST` |
| Explicit OFF | applied to 2 LED nodes; none auto-on at boot | `PASS_DEVICE_RUNTIME` |
| Notification LED | `NOT_SUPPORTED_ON_DEVICE` | `PASS_DEVICE_RUNTIME` |
| Edge lighting | `NOT_SUPPORTED_ON_DEVICE_AS_LED` (`kind=display_overlay`) | `PASS_DEVICE_RUNTIME` |

## 5. Full dependency chain

| Stage | Current state |
|---|---|
| Rear dual-LED flash/torch | present; PMIC/camera LED path `s2mpb02-led` |
| Kernel LED class | `torch-sec1`, `leds-sec1` |
| PMIC/flash driver | bound (`9-0059/s2mpb02-led`) |
| Userspace provider | bridge flashlight provider; policy bounds |
| UI/permission | Quick Settings/notification path |
| Notification LED | no class; not supported |
| Edge lighting | display overlay only |

## 6. First failing stage

**Notification/RGB LED: not present.** The kernel exposes no notification/RGB LED class. The rear torch is functional; the requested colored notification behavior has no physical LED to drive.

## 7. Why prior attempts have not completed the feature

- `configs/nuxel/leds/leds.json` distinguishes the real rear flash, a possible front notification class, and “edge lighting” as a display effect.
- Live enumeration confirms only the rear torch/leds-sec1 classes; no notification/RGB class exists.
- A sysfs name alone was never treated as RGB proof.

## 8. Best recommended architecture

**Primary:** keep the rear torch as a bounded, explicit flashlight function. Implement notification indication as an **AMOLED edge/notification overlay** in the display bridge, clearly labeled as a display effect, with screen-on/off and lockscreen security preserved.

**Fallback:** if a real notification LED class is discovered on another board variant, drive it only through the LED class with color/blink capability proven.

**Not recommended:** use the camera flash as a continuous notification lamp without current/thermal policy, or write undocumented PMIC registers.

## 9. Required work inventory

| Area | Work |
|---|---|
| Torch | keep bounded ON/OFF, thermal/battery guard, forced OFF |
| Notification | display overlay design, color/animation, screen state handling |
| Color | only if a real multicolor LED class exists; prove channels physically |
| UI | torch toggle, notification color/pattern, OFF state |
| Tests | thermal timeout, forced OFF, screen-off/lockscreen behavior |

## 10. Source/upstream research

- `s2mpb02-led` is the live PMIC LED driver.
- No multicolor notification LED driver/class is exposed on this board.
- Edge lighting is an AMOLED display overlay, not a hardware LED.

## 11. Buildability

- Torch and display-overlay work is buildable from repo sources.
- No LED firmware is required for the current torch path.
- Do not write undocumented PMIC registers or flash LED firmware.

## 12. Risks and constraints

- Torch is a 1 W-class emitter; continuous use needs current/thermal policy.
- Never auto-on at boot; always force OFF on exit/failure.
- Do not use the camera flash as a notification lamp without a supported policy.
- Display overlay must not compromise lockscreen privacy/security.

## 13. Phased roadmap

| Phase | Goal | Gate |
|---|---|---|
| 0 | Confirm torch physically (owner) and OFF-on-exit | Owner visual test |
| 1 | Torch timeout/thermal guard regression | Runtime test |
| 2 | Edge/notification display overlay | Screen-on/off + lockscreen tests |
| 3 | Color/pattern policy in UI | Owner acceptance |
| 4 | Any real LED class on other variants | Class/capability proof |

## 14. Acceptance test matrix

| Test | Required evidence |
|---|---|
| Rear torch | physical light visible, bounded, forced OFF |
| Notification LED | only if a real class exists; color/blink proven |
| Edge overlay | visible on AMOLED, no lockscreen leak |
| Timeout | ON duration bounded, thermal safe |
| Boot | torch OFF by default |
| Screen off/on | overlay behavior correct |

## 15. Owner inputs required

- Visual confirmation that the 1-second torch test produced light.
- Acceptance of display-based edge/notification behavior if no LED exists.
- Thermal/current policy limits if continuous torch use is desired.

## 16. Confidence and gaps

- **Proved:** torch class/control path, forced OFF, no notification/RGB class, edge lighting is an overlay.
- **Inferred:** display overlay is the only honest color/notification route on this board.
- **Unknown:** physical torch visibility in this session; any board-variant LED differences.
