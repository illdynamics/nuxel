# PWNAGE-51000 — boot, shutdown and drawer performance

## Boot

Same handset, same session data. `systemd-analyze time` after the final reboot:

```
Startup finished in 3.446s (kernel) + 10.027s (userspace) = 13.473s
multi-user.target reached after 9.996s in userspace.
```

Before (first boot of the new kernel, ABOX on the boot path):

```
Startup finished in 3.449s (kernel) + 58.375s (userspace) = 61.825s
multi-user.target reached after 17.259s in userspace.
```

Changes:
- `nuxel-abox-firmware-reload.service` removed from `nuxel-wayland` wants;
  started by `nuxel-abox-firmware-reload.timer` (`OnBootSec=20s`).
- `nuxel-boot-sound.service` no longer wants/orders after ABOX or audio-route;
  its readiness precheck is fast and non-fatal.
- `nuxel-audio-session.service` stop bounded at 4 s (unit-specific, not global).
- `nuxel-wayland.service` stop bounded at 3 s with an explicit TERM/KILL.

Result: total boot −78%, multi-user −42%. ABOX still runs (~23.85 s) after Home
when the timer fires; it no longer holds the initial transaction.

## Shutdown / reboot black screen

Previous boot (monotonic):

```
55.37  nuxel-audio-route.service stopped
55.39  nuxel-audio-session.service stopping
55.50  nuxel-audio-session.service stopped        (0.11 s, was 8.15 s timeout)
55.82  nuxel-wayland.service stopping
59.12  nuxel-wayland.service stopped              (3.29 s, was 8.03 s timeout)
59.57  reboot.target reached
59.81  systemd-shutdown sends SIGTERM
```

Before: `nuxel-wayland` consumed its full 8 s stop timeout and
`nuxel-audio-session` another 8 s. After: wayland 3.29 s and audio 0.11 s.
The user-visible reboot round-trip to SSH fell from 92 s to 86 s (the remainder
is kernel/bootloader/firmware time outside systemd control).

## App drawer

Source changes:
- `openDrawer()` sets `_drawerOpenGuardUntil = now + 250ms`, resets both
  `grid.scrollTop` and `drawerList.scrollTop`, and the capture-phase
  `touchmove` handler cancels residual deltas during that window.
- `gestures.js` marks the opening swipe consumed and sets
  `_drawerGestureUntil = now + 300ms`.
- Tap/scroll discrimination tightened from 24 px to 12 px; movement cancels the
  pending launch and suppresses the compatibility click.
- The drawer list is cached by signature and is not rebuilt on ordinary opens.

Tests:
`tests/pwnage50000/test_drawer_gesture_guard.py` PASS
(`PASS drawer open guard + 12px tap/scroll discrimination`).

Physical touch confirmation (opening swipe does not scroll; scrolling does not
launch; deliberate tap launches once) remains **NEEDS_OWNER_TEST**.
