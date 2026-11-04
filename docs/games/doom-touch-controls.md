# Nuxel Doom touch controls

Nuxel Doom must be playable with two thumbs and no keyboard. The input model is
built around independent SDL-style pointer IDs replicated by the browser Pointer
Events API.

## Layout

```
┌──────────────────────────────────────────────────────────────┐
│ HEALTH  ARMOR  AMMO  WEAPON  KILLS  SECTOR                   │
│                                                              │
│                                                              │
│   (left thumb)                    (right thumb)              │
│      joystick          FIRE       USE                        │
│                        WPN- WPN+  RUN  MENU                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

The right side is divided into:

- a transparent **look surface** for drag-to-aim;
- a **fire** button large enough to hold while moving;
- **use/doors**, **weapon previous/next**, **run** and **pause/menu**.

## Multitouch contract

- The joystick keeps its own `pointerId`; a second finger cannot steal it.
- The look surface keeps a separate `pointerId`.
- Fire/use/weapon/run each keep their own press state.
- `pointercancel`, `lostpointercapture`, window blur, page hide, visibility
  change, pause and app exit call `releaseAllInput()`.
- Fire is rate-limited by the engine cooldown, not by render frames.

This permits the required combinations:

| Combination | Supported |
|---|---|
| Move + aim | yes |
| Move + fire | yes |
| Aim + fire | yes |
| Move + aim + fire | yes |
| Strafe + use door | yes |
| Turn + switch weapon | yes |

## Sensitivity and handedness

The settings screen persists:

- look sensitivity from `0.0015` to `0.0080`;
- inverted vertical aim;
- left-handed mirroring;
- sound and haptics toggles.

The layout uses the runtime viewport and safe-area insets. It is not hard-coded
to 1520×720 or any one panel resolution. A landscape-specific compact layout
engages below 560 px height, and short phones below 430 px height get a scrolling
launch/settings sheet.

## Keyboard and controller

Keyboard input remains available on desktop/VM builds as a convenience:

| Key | Action |
|---|---|
| W/A/S/D or arrows | Move |
| Arrow left/right | Turn |
| Space | Fire |
| E | Use |
| 1 / 2 / 3 | Pistol / shotgun / plasma |
| Esc | Pause |

The phone experience never requires these keys. Bluetooth gamepads are handled
by the host's normal input stack; the touch HUD does not fight a gamepad because
it only emits its own engine input when a pointer is active.

## Pause and lifecycle

The game pauses automatically when the document becomes hidden. The pause
screen offers Resume, Restart Sector, Return to Campaign and Exit Doom. Exiting
restores the previous orientation and releases every touch state.
