# Nuxel Doom touch controls

Nuxel Doom is played with two thumbs. The HUD lives above the WebAssembly
canvas and translates pointer gestures into the Chocolate Doom engine's own
keyboard events. No global input injection or privileged `uinput` daemon is
used.

## Layout

```
┌──────────────────────────────────────────────────────────────┐
│ CHOCOLATE DOOM · FREEDOOM                                    │
│                                                              │
│                                                              │
│   (left thumb)          LOOK      FIRE       USE             │
│      joystick          [◀][▶]     WPN- WPN+  RUN  MENU        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

The right side is divided into:

- a transparent **look surface** for drag-to-turn;
- a right-thumb **LOOK D-pad**: hold **◀** / **▶** to turn without swiping;
- a large **FIRE** button (hold to keep firing);
- **USE** (doors/switches), **WPN +/−**, **RUN** and **MENU**.

Chocolate Doom has no vertical free-look, so the look pad deliberately exposes
only the horizontal turn axis. The stock engine config is written with DOS
set-1 scan codes (`key_fire 29` = left Ctrl), which is why the Fire button now
matches the engine's fire binding.

## Engine mapping

| HUD action | Engine event | Chocolate Doom binding |
|---|---|---|
| Joystick up/down | `ArrowUp` / `ArrowDown` | move forward/back |
| Joystick left/right | `,` / `.` (strafe mode) | strafe left/right |
| Joystick sideways in turn mode | `ArrowLeft` / `ArrowRight` | turn |
| Drag to turn | `ArrowLeft` / `ArrowRight` | turn |
| Look pad ◀ / ▶ | `ArrowLeft` / `ArrowRight` | turn |
| FIRE | `ControlLeft` | fire |
| USE | `Space` | use / open |
| WPN +/− | `1`..`7` | weapon select |
| RUN | `ShiftLeft` | run |
| MENU | in-app pause + engine loop suspend | pause overlay |
| System Back | pause overlay | — |

The engine's config is written with explicit bindings before `callMain`, so a
WAD cannot silently change the touch contract.

## Multitouch contract

- The joystick keeps its own `pointerId`; a second finger cannot steal it.
- The look surface keeps a separate `pointerId`.
- Fire/use/weapon/run/menu each keep their own press state.
- `pointercancel`, `lostpointercapture`, window blur, page hide, visibility
  change, pause and exit call `releaseAllInput()` and emit the matching key-up
  events.
- Fire is held by the engine, not re-sent per animation frame.
- Diagonal movement is supported (forward/back + strafe).

| Combination | Supported |
|---|---|
| Move + aim | yes |
| Move + fire | yes |
| Aim + fire | yes |
| Move + aim + fire | yes |
| Strafe + use door | yes |
| Turn + switch weapon | yes |

## Settings

The settings screen persists:

- sound on/off (`-nosound` when off);
- haptics on/off;
- strafe joystick on/off;
- left-handed mirroring;
- turn sensitivity from 0.4 to 2.5.

The layout uses the runtime viewport and safe-area insets, not a hard-coded
resolution. A compact landscape layout engages below 560 px height.

## Fullscreen chrome

Every foreground app, including Doom, hides the triple buttons and top bar by
default.

- **Swipe up from the bottom edge** to reveal Back/Home/Recents.
  - Back opens the pause overlay.
  - Home minimises Doom; the session is not killed.
  - Recents allows a real kill.
- **Pull down from the top edge** to reveal the status bar.
- Both hide again automatically after a few seconds.
- Nuxel Home and the lockscreen deliberately keep their normal chrome.

## Pause and lifecycle

Pause suspends the engine main loop, hides the HUD and releases every held key.
Resume restarts the loop from a clean input state. Focus loss and page hide
pause automatically. Exit restores the previous display orientation and
returns Home.
