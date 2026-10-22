# A55 Camera — Snapshot install + Nuxel Camera + frames

## GNOME Snapshot (native Fedora Camera)
**BLOCKED_EXTERNAL_RESOURCE** — `snapshot` RPM absent; no `dnf`/`flatpak` on the
phone to resolve+install it or its missing deps (`pipewire`, `wireplumber`,
`libcamera`, `gstreamer1-plugin-pipewire`). Installing Snapshot cannot be
claimed; see BROWSER-PACKAGES.md for the package-manager bootstrap.

## Nuxel-owned Camera
A54 `nuxel-camera-native` (GTK4/libadwaita) + A52 media store remain deployed.
Distinct from Snapshot; honest status card; Photos delegation.

## Camera frames
**BLOCKED_HARDWARE** — Exynos FIMC-IS rejects standard capture
(`VIDIOC_S_FMT → ENOTTY`), no `/dev/media*`. Installing Snapshot would not
create a driver. No hardware frames are claimed.
