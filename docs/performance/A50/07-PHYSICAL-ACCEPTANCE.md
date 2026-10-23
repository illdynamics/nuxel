# A50 — 07: Physical acceptance (required regression matrix)

**Status: BLOCKED for physical checks.** This autonomous run had no physical
finger, no button access, and no high-frame-rate camera on the handset. Per the
prime directive ("Do not simulate tests then call them physical proof"), every
physical item is marked `NOT_EXECUTED` rather than passed.

| # | Physical check | Result |
|---|---|---|
| 1 | Penguin lockhead unlock gesture | NOT_EXECUTED (no physical gesture) |
| 2 | Home swipe left/right, all desktops | NOT_EXECUTED |
| 3 | Tap 10 app icons in a row | NOT_EXECUTED |
| 4 | Open/close app drawer 5× | NOT_EXECUTED |
| 5 | Quick Settings open/toggle/close | NOT_EXECUTED |
| 6 | Short/long Back, Home, Recents | NOT_EXECUTED |
| 7 | Keyboard focus/typing/haptics | NOT_EXECUTED |
| 8 | Battery percentage/icon after restart | NOT_EXECUTED (no reboot) |
| 9 | Wi-Fi scan/join while Home stays fluid | NOT_EXECUTED |
| 10 | Locked screen hides nav; power menu | NOT_EXECUTED |
| 11 | Screen-off dwell + wake without stale frame | PARTIAL (software): wake path verified, first frame healthy; glass not visually observed |
| 12 | Orientation + rotated touch/keyboard safe zones | NOT_EXECUTED |
| 13 | Boot splash/warning/spinning penguin unchanged | NOT_EXECUTED (no reboot) |
| 14 | Stress cycle (30 swipes/20 launches/…) | NOT_EXECUTED |
| 15 | Wired HDMI/cast if working | NOT_EXECUTED |

## What software evidence *was* obtained on the real device
- Wake/unlock-independent: `DISPLAY_ON` transition, `decon_pan_failed=0`,
  `present_skipped` damage-skip active, FRAMES_OK healthy.
- Screen-off quiet: bridge capture stopped, <1 % CPU.
- Single framebuffer owner, zero failed units, zero service restarts.

Owner-observed PASS/FAIL on the physical matrix is required before any
`VERIFIED_ON_DEVICE` claim.
