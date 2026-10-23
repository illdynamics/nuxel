# App registry and camera evidence

Home exposes native/PWA entries including Nuxel Browser, custom Camera, SnekByte and GNOME Snapshot. Snapshot `49.0` and Firefox `157.0.1` are installed on the aarch64 phone.

Camera capability is `HARDWARE_BLOCKED` for genuine capture: `/dev/video*` exists, but there are no `/dev/media*` or `/dev/v4l-subdev*` nodes and no libcamera/PipeWire media graph. App presence is not a frame. Snapshot and the custom camera must still be opened and escaped with Home/Back after normal boot.

The launcher and the older canonical common/native registries are not yet a single identical app set. This is recorded as registry drift; no app-discovery 100% claim is made.
