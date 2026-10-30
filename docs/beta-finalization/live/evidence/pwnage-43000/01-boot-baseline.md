# PWNAGE-43000 — Boot Baseline (cold boot 2026-10-30 14:39 UTC)

## systemd-analyze
```
Startup finished in 3.437s (kernel) + 30.914s (userspace) = 34.351s
multi-user.target reached after 16.029s in userspace.
```

## Monotonic boot event sequence (journalctl -b -o short-monotonic)
| t (s) | Event |
|---|---|
| 3.879 | kernel Booting Linux on physical CPU 0x0 |
| 4.582 | nuxel-init `MP4_PLAYER_ACTIVE` (early boot animation) |
| 6.271 | Starting `nuxel-wayland.service` |
| 6.564 | Started `nuxel-wayland.service` |
| 6.847 | Starting `nuxel-wl-fb.service` |
| 6.858 | Started `nuxel-wl-fb.service` |
| 7.131 | Stopping `nuxel-wayland.service` (ABOX reload begins) |
| 7.421 | `nuxel-wl-fb.service` failed INVALIDARGUMENT (wayland gone) |
| 7.436 | Starting `nuxel-fallback.service` (waits up to 60s) |
| 12.672 | `nuxel-wl-fb` scheduled restart #1; wayland restarts |
| 12.715 | `nuxel-wl-fb` failed FAILURE |
| 17.678 | phoc "Timeout (3000ms) expired with 1 configures pending" |
| 17.966 | `nuxel-wl-fb` restart #2 |
| 18.605 | `ANIMATION_STOPPED` (spinning penguin / early animation ends) |
| 18.872 | `LAUNCHER_DISPLAY owner=nuxel-wl-fb loops=1/1` |
| 19.466 | `nuxel-fallback.service` skipped (launcher owns panel) |
| 26.381 | Stopping `nuxel-wayland.service` (ABOX attempt 2 path) |
| 26.510 | wayland deactivated; `nuxel-wl-fb` failed NOTINSTALLED |
| 30.246 | wayland restarts |
| 31.274 | `nuxel-wl-fb` started (final stable owner) |
| 31.386 | `LAUNCHER_DISPLAY owner=nuxel-wl-fb loops=2/1` |

## ABOX reload timeline (this boot)
- 14:39:40 start; stopped audio session; PM attempt 1 suspended/resumed.
- 14:40:00 attempt 1 did not reach MUB0; PM attempt 2.
- 14:40:03 Calliope core firmware loaded (MUB0) after 2 attempts.
- 14:40:06 `nuxel-abox-firmware-reload.service` finished (25.8s total).

## Root cause of boot churn (diagnosis)
1. `nuxel-abox-firmware-reload.service` is `WantedBy=nuxel-wayland.service` and
   intentionally stops `nuxel-wayland.service` to kill PipeWire (which holds the
   ABOX runtime-PM reference via hw:0,1).
2. Stopping wayland tears down `nuxel-wl-fb` (the AMOLED display bridge) and the
   launcher. wl-fb then restart-loops 3 times before it becomes the stable
   display owner.
3. The UI reaches a stable, interactive state only at ~31.4s, even though
   `multi-user.target` was reached at 16.0s.
4. PipeWire being a child of the `phoc` session is the coupling that forces the
   ABOX reload to stop the whole UI. Decoupling audio from the compositor
   session would let the ABOX reload stop only the audio stack and leave the UI up.
