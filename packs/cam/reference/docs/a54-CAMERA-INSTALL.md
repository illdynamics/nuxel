# A54 Camera Install & App Completion

## Why the old "No native camera app installed" persisted
The deployed `nuxel-bridge` and `nuxel-http-bridge` were A51-era (see BASELINE.md):
they lacked the A52 `media_store.py` module, the `CameraStatus/CameraCapture/
CameraListCaptures/CameraOpen/CameraDelete` D-Bus methods, and the
`camera.*` RPC mappings. `camera.status` answered `Unknown RPC` on the live
device, so the Camera PWA had no backend.

## Fix applied (backend, transactional)
- Deployed `bridge.py` (with A52 media-store + camera methods + A54 battery
  semantics), `media_store.py` (new), and `api.py` (camera RPC mappings) to
  `/usr/lib/nuxel/nuxel-bridge/`, all SHA-256 verified on-device.
- Restarted `nuxel-bridge` then `nuxel-http-bridge`; both `active`, no failed units.
- Generated `/var/lib/nuxel/camera-topology.json` (root-generated system
  snapshot) so the bridge — which runs with `DevicePolicy=closed` and cannot see
  `/dev` — can report the real hardware enumeration honestly.

## Live evidence
- `camera.status` RPC → `{"success":true,"camera_present":true,
  "capture_verified":false,"source":"snapshot","video_node_count":68,
  "detail":"V4L2 nodes enumerated (68); the Exynos FIMC-IS vendor interface does
  not expose standard capture …"}`.
- `media_store` offline round-trip + `test-media-store.py` and
  `test-camera-bridge.py` pass (capture/list/open/delete, no base64 pixel dump in
  list, size caps enforced).

## Nuxel-owned native Camera app (genuinely Nuxel, not a webview)
- New `shell/nuxel-camera-native/nuxel_camera_native.py` — a native GTK4/
  libadwaita Python application, app id `org.nuxel.CameraNative`, own desktop
  entry, adaptive touch UI, honest status card, Photos PWA delegation, and
  bridge-delegated capture (no unreviewed root calls).
- Deployed to `/usr/lib/nuxel/nuxel-camera-native/`; desktop entry staged under
  `/usr/share/nuxel/applications/`.
- Launch acceptance: process connects to `wayland-0` and stays alive (killed
  only by the test harness's `timeout`/`kill`). A session-bus warning appears
  when launched from the bare serial shell (no `DBUS_SESSION_BUS_ADDRESS`);
  the proper graphical-session launch path provides that bus.

## GNOME Snapshot (native Fedora Camera)
- **Not installable safely in this session.** `snapshot` RPM is absent; no
  `dnf`/`microdnf`/`dnf5` exists (only `rpm` 6.0.2), so dependency resolution
  cannot be performed transactionally on-device. Dependencies are also absent:
  `pipewire`, `wireplumber`, `gstreamer1-plugin-pipewire`, `libcamera`,
  `gstreamer1-plugins-good`. 1.7 GiB free.
- Fedora 43 aarch64 repo metadata is configured (`/etc/yum.repos.d/fedora*.repo`),
  and network/HTTPS are verified, so the follow-on procedure is to stage the
  signed aarch64 `snapshot` + dependency RPM set and install with `dnf`/`dnf5`
  once a package manager is present (exact URLs to be pinned at install time).

## Camera frames gate (unchanged, honest)
- `/dev/media*`: none. 68 vendor `/dev/video*` nodes enumerate but the FIMC-IS
  driver rejects standard capture (`VIDIOC_S_FMT → ENOTTY`, see
  `docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md`). Installing Snapshot does not
  create a driver and must not be presented as "camera captures images".

## Gate
- **CAMERA-NUXEL:** PASS_INTEGRATION (backend live + distinct native GTK4 app
  deployed and launchable).
- **CAMERA-NATIVE (Snapshot):** BLOCKED_EXTERNAL_RESOURCE (missing package
  manager + dependency set; exact procedure in DEPLOYMENT-AND-ROLLBACK.md).
- **CAMERA-FRAMES:** BLOCKED_HARDWARE (FIMC-IS standard-capture ENOTTY).
