# NUXEL A53 — Orientation: Five Primary Modes (implemented & deployed)

## What changed

The A49 orientation service already held all seven policy modes; A53 re-labels and re-orders them so
the five owner-requested primary modes are first and exactly named, with the two reverse poses kept
as advanced options (never hidden/displaced).

| Stable API value | A53 UI label | Allowed target | Type |
|---|---|---|---|
| `auto` | **Auto** | 0 / 90 / 180 / 270 | primary |
| `auto_portrait` | **Auto Portrait** | 0 / 180 only | primary |
| `auto_landscape` | **Auto Landscape** | 90 / 270 only | primary |
| `portrait` | **Forced Portrait** | fixed 0 | primary |
| `landscape` | **Forced Landscape** | fixed 90 (calibratable 270) | primary |
| `reverse_portrait` | Reverse Portrait | fixed 180 | advanced |
| `reverse_landscape` | Reverse Landscape | fixed 270 | advanced |

## Files changed (repo == deployed, SHA-256 identical)

| Repo path | Deployed path | SHA-256 (on-device, verified) |
|---|---|---|
| `services/nuxel-orientation/nuxel_orientation/policy.py` | `/usr/libexec/nuxel/nuxel_orientation/policy.py` | `d84b9052…` |
| `configs/nuxel/orientation/orientation.json` | `/etc/nuxel/orientation/orientation.json` | `006ff7f8…` |
| `pwa/nuxel-home/js/qs.js` | `/usr/share/nuxel/nuxel-home/js/qs.js` | `a4587e5f…` |
| `pwa/nuxel-apps/settings/settings.js` | `/usr/share/nuxel/pwa/nuxel-apps/settings/settings.js` | `d65dea16…` |
| `pwa/nuxel-home/sw.js` | `/usr/share/nuxel/nuxel-home/sw.js` (cache `v31-a53-orientation-five-mode`) | `1536a8d0…` |

(These files were merged against the **live** on-device copies to avoid clobbering A44/A45/A47 drift;
the resulting repo files now match the deployed bytes exactly.)

## Verified live on the S10+ (not simulated)

```
# /usr/libexec/nuxel/nuxel-orientationd modes
auto -> Auto [0,90,180,270] · auto_portrait -> Auto Portrait [0,180] · auto_landscape -> Auto Landscape [90,270]
portrait -> Forced Portrait [0] · landscape -> Forced Landscape [90]
reverse_portrait -> Reverse Portrait [180] · reverse_landscape -> Reverse Landscape [270]

# orientation.get (bridge HTTP RPC)  -> mode_label "Forced Portrait", sensor.available=false,
#                                       compositor.transform_available=false
# orientation.set auto_landscape     -> success:true, effective_orientation 90, state persisted
# orientation.set portrait           -> success:true, effective_orientation 0, state persisted (safe default restored)
# selftest                           -> PASS ; 39 pytest tests pass
```

## Honest physical-rotation blockers (still true, unchanged from A49)

1. **Sensor (auto modes):** `accelerometer_sensor`/`gyro_sensor` IIO devices exist but expose **no**
   `in_accel_*_raw` channels and no `in_accel_scale`; `iio-sensor-proxy` D-Bus service is not
   provided. Auto modes therefore report `sensor unavailable` — they are selectable and persisted
   but cannot follow gravity until a sensor source lands.
2. **Compositor transform (all modes):** the display is Phoc **HEADLESS-1** → `nuxel-wl-fb` →
   `/dev/fb0`. There is no `wlr-randr` and no wlroots output-management transform backend, so
   `transform_available=false`. Rotated **pixels** would require either a presenter-side rotation in
   `nuxel-wl-fb` **plus** a matching libinput touch calibration matrix in Phoc — neither exists
   today, and pixels-without-touch is explicitly rejected by the contract.
3. **Forced Portrait/Landscape:** the policy is fully selectable and persisted, but the physical
   transform is blocked by (2) exactly like the auto modes.

**Result:** the five-mode selector, ordering, labels, persistence and single source of truth are
implemented and live. Physical screen+touch rotation remains `BLOCKED` at the compositor/presenter
and sensor layers; this is recorded, not claimed.
