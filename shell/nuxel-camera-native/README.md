# nuxel-camera-native

A genuinely Nuxel-owned native GTK4 Camera application (Python + PyGObject +
GTK4/libadwaita), independent of the Camera Gallery PWA and of GNOME Snapshot.

- Own application id `org.nuxel.CameraNative`, own `.desktop` entry.
- Honest hardware-status card: never draws a fake live preview.
- Capture (when a real backend exists) is delegated to the Nuxel bridge media
  store; there are no unreviewed root calls.
- Opens the standalone Photos PWA for gallery integration.

On the S10+ the Exynos FIMC-IS vendor driver blocks standard V4L2 capture
(`VIDIOC_S_FMT -> ENOTTY`), so the app opens cleanly and reports
"capture NOT verified" rather than a synthetic preview.  See
`docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md`.
