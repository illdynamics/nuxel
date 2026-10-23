# A59 — Camera: native GNOME Snapshot + custom Nuxel Camera

The camera result is split into "application installed/launchable" versus
"Exynos sensor produces live frames" (the A52 blocker is NOT solved by this).

## Result gates (honest)
| Gate | Status |
|---|---|
| `SNAPSHOT_INSTALLED` | YES — `snapshot-49.0-1.fc43.aarch64` |
| `SNAPSHOT_LAUNCHABLE` | YES — native `Camera` (app_id `snapshot`) window appears |
| `NUXEL_CAMERA_LAUNCHABLE` | YES — custom `Nuxel Camera` native window appears |
| `CAMERA_SENSOR_DETECTED` | YES — 68 `/dev/video*` nodes enumerate (FIMC-IS), 0 `/dev/media*` |
| `LIVE_REAL_FRAMES` | BLOCKED — no PipeWire/libcamera camera source; Exynos ISP pipeline not functional |
| `REAL_JPEG_PERSISTED` | BLOCKED (no live frames to persist) |

## GNOME Snapshot (native)
- Installed from signed Fedora 43 aarch64 RPM `snapshot-49.0-1.fc43.aarch64`
  (verified available in the Everything repo).
- To make its viewfinder shell start, the missing GStreamer pieces were
  installed from the same Fedora repos: `gstreamer1-plugins-bad-free-1.26.11`
  (provides `camerabin`) and `gstreamer1-plugin-gtk4-0.14.2` (GTK4 sink).
  `glycin-loaders` was already present (2.0.8).
- Launch: `/usr/sbin/snapshot` under the Wayland session. It runs as a real
  native GTK4 window (foreign-toplevel shows `title=Camera app_id=snapshot`).
- Honest remaining blocker for a live feed:
  `aperture … missing gstreamer plugins: ["pipewire"]` →
  `Could not create DeviceProviderFactory with name pipewiredeviceprovider`.
  The Exynos camera has no media-controller device and no libcamera/PipeWire
  camera source, so the app shows "no camera" rather than frames. This is a
  hardware/kernel/driver gap, not a UI defect.

## Custom Nuxel Camera (separate app, separate identity)
- `shell/nuxel-camera-native/nuxel_camera_native.py` (GTK4 + libadwaita) is a
  distinct Nuxel-owned app; it is NOT a renamed Snapshot window.
- Registered as `nuxel-camera` (`nativeAppId org.nuxel.CameraNative`) in the
  launcher and `org.nuxel.CameraNative` in the canonical registry.
- It reads the honest hardware status (bridge `CameraStatus` /
  `/var/lib/nuxel/camera-topology.json`) and reports
  `Camera present` + `Live capture: NOT verified` with the FIMC-IS reason,
  plus a `Refresh status` and `Open Photos` action. It never draws a fake
  preview or synthetic test pattern.
- Launches from the drawer as a native window
  (foreign-toplevel `title=Nuxel Camera app_id=nuxel_camera_native.py`).

## Preserved A52 backend
- File-backed `media_store.py`, atomic saves, `camera.status`, `camera.capture`,
  `camera.list-captures`, `camera.open`, `camera.delete`, private
  `org.nuxel.Bridge`, camera/microphone access controls, privacy indicator and
  Photos integration are unchanged (see `services/nuxel-bridge/src/`).

## Safe next step for live frames (not attempted)
- Bring up `pipewire` + `wireplumber` + `gstreamer1-plugin-libcamera` +
  `libcamera`, and confirm whether any FIMC-IS node exposes a media-controller
  topology a libcamera pipeline-handler can consume. Until a real frame is
  captured, `LIVE_REAL_FRAMES` stays BLOCKED with the evidence above.
