# PWNAGE-54000 — Make Nuxel Rotation Actually Work
## Physical display, touchscreen, Quick Settings, VNC and XRDP orientation synchronization

**Target:** Nuxel on Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Priority:** High  
**Scope:** Userspace orientation, display, touch, UI, VNC and XRDP  
**Kernel/firmware flashing:** Explicitly out of scope

### Mission

Finish Nuxel's existing orientation implementation. Do not start over or introduce a competing rotation system. There have already been successful rotations on this device. Find the implementation, configuration, build or runtime path responsible for those successes, reproduce it, and make that path reliable across all seven orientation modes.

A mode change must do more than save a preference. It must actually transform the Nuxel display, preserve correctly mapped touchscreen input, update the visible UI and notify connected remote desktop sessions.

### Required modes

Keep stable internal mode keys and expose these exact user-facing labels:

| UI label | Stable key | Allowed orientation |
|---|---|---:|
| Auto (FULL) | `auto` | 0°, 90°, 180°, 270° |
| Auto (PT) | `auto-portrait` | 0°, 180° |
| Auto (LS) | `auto-landscape` | 90°, 270° |
| Locked (PT) | `portrait` | 0° |
| Locked (LS) | `landscape` | 90° |
| Locked (RPT) | `reverse-portrait` | 180° |
| Locked (RLS) | `reverse-landscape` | 270° |

`PT` means portrait; `LS` means landscape. Do not silently rename or remove existing persisted keys. Migrate aliases safely.

### Implementation requirements

1. **Recover the working rotation first.** Inspect Git history, existing code, previous patches, build scripts, installed binaries, configuration, logs and diagnostics. Identify the exact output, backend and transform mapping that produced the successful rotations. Reproduce that result before refactoring.
2. **Use one orientation authority.** The existing `nuxel-orientationd` implementation should own the selected policy, sensor interpretation, effective orientation, display application, touch coordination, rollback and event publication. Do not add competing daemons or independent polling loops.
3. **Make mode changes real.** The current Bridge/UI path must not merely persist a mode. A successful request must apply the requested transform, verify it, update state and publish an orientation-change event. A failed application must leave the last-known-good state intact.
4. **Rotate the real display.** Use the actual active Phoc output and a backend supported by the running system. Do not assume `DSI-1`, `HEADLESS-1`, `wlr-randr` availability or a historical transform mapping without checking.
5. **Keep touch aligned.** Touch coordinates, pointer input, keyboard, dock, status bar, OSK, windows and screen edges must match the displayed orientation. Prefer compositor-owned input transformation. Do not double-rotate touch.
6. **Make Auto modes genuine.** Auto modes must continuously obtain real sensor readings, debounce and stabilize orientation changes, apply only allowed angles and retain the last good angle when the device is flat or readings are unreliable. A manual diagnostic source must never masquerade as production sensor support.
7. **Make remote sessions follow orientation.**
   - VNC must continue mirroring the actual Phoc session and report updated desktop geometry to connected clients where supported.
   - XRDP sessions must receive the current orientation and appropriate virtual desktop geometry without logging out, killing applications or restarting the session.
   - New and reconnected sessions must initialize from the current effective orientation.
   - A remote resize failure must never undo a successful local phone rotation.
8. **Expose truthful status.** Show selected mode separately from applied orientation. Report sensor, display backend/output, touch mapping, rollback and remote-session status.
9. **Preserve the framebuffer architecture.** `nuxel-wl-fb` remains the sole `/dev/fb0` writer. Do not introduce a second framebuffer writer or an unrelated display server.
10. **Preserve safety.** Use a local rollback watchdog independent of SSH and remote desktop connectivity. Do not flash kernels, firmware, bootloaders or partitions in this task.

### Repository areas to inspect

At minimum:

- `configs/nuxel/orientation/orientation.json`
- `configs/nuxel/orientation/orientation.schema.json`
- `services/nuxel-orientation/nuxel_orientation/policy.py`
- `services/nuxel-orientation/nuxel_orientation/apply.py`
- `services/nuxel-orientation/nuxel_orientation/sensors.py`
- `services/nuxel-orientation/nuxel-orientationd`
- `services/nuxel-orientation/systemd/nuxel-orientationd.service`
- `services/nuxel-bridge/src/bridge.py`
- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-apps/settings/settings.js`
- `tools/s10plus/a45/nuxel-navdock.c`
- The currently active `nuxel-wl-fb` source and its real build/install path
- `docs/A49/OWNER-TEST-ORIENTATION.md`
- `docs/a54-reliability/ORIENTATION-MATRIX.md`
- `docs/a69/ROTATION-HARDWARE-BOUNDARY.md`

Also inspect the XRDP/VNC implementation introduced by the remote-desktop work. Confirm which service actually owns each session.

### Mandatory acceptance tests

- All seven labels appear in Quick Settings and Settings and map to the correct stable keys.
- All four fixed orientations physically work, including reverse portrait and reverse landscape.
- Touch remains accurate at all four screen corners, all four edges, the dock, navigation controls, OSK and ordinary application controls.
- Every supported Auto mode changes orientation from genuine sensor input and obeys its allowed-angle set.
- Auto modes retain the last good orientation when the device is flat or sensor data is invalid.
- A failed or interrupted rotation automatically rolls back locally.
- A connected VNC client sees the updated image, geometry and pointer mapping.
- A connected XRDP client sees the orientation/geometry update without losing its session or applications.
- Disconnecting and reconnecting either remote service starts in the current orientation.
- Jump Desktop on macOS is tested when available; record any client-specific dynamic-resize limitation honestly.
- SSH loss, VNC loss or XRDP failure does not break local rotation.
- Reboot restores the saved policy and starts in a valid orientation.

### Required output

Deliver:

1. Root-cause analysis explaining why some previous rotations worked and why the full path was unreliable.
2. A source-backed implementation plan and list of files changed.
3. The patched source and configuration.
4. Correct package, image and deployment integration.
5. Automated tests and a completed physical-device test matrix.
6. Logs proving display, touch, VNC and XRDP synchronization.
7. A safe Wi-Fi SSH deployment procedure with rollback instructions.
8. A precise list of any remaining hardware, sensor or remote-client limitations.

**Definition of done:** A user selects any of the seven modes and Nuxel behaves accordingly on the phone and in connected remote sessions. No preference-only success, simulated sensor success, unverified transform mapping or misleading green status is acceptable.
