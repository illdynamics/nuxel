# NUXEL A53 — Native Camera Application (GNOME Snapshot)

## Gate status: `BLOCKED_NETWORK` / `BLOCKED_SESSION` (installation impossible this session)

The owner asked for a genuine native ARM64 camera app, preferably Fedora's `snapshot`. That is a
real, appropriate target. On this device it **cannot be installed** this session for these exact,
independently-verified reasons:

1. **No package manager.** `dnf`, `dnf5`, `microdnf` and PackageKit are all absent; only `rpm` 6.0.2
   exists. There is no `dnf install` to run.
2. **No network.** `wlan0`/`wlan1` are `DORMANT`, no `usb0`, no default route; the Wi-Fi PSK is an
   owner-only input. The only transport is a 115200-baud serial console (≈11 KB/s), impractical for
   the multi-hundred-MB `snapshot`+PipeWire+GStreamer dependency tree.
3. **Missing runtime prerequisites.** `snapshot` is a GTK4/PipeWire app; `pipewire`, `wireplumber`,
   `gstreamer1-plugin-pipewire`, and libcamera are all absent. Even a manual `rpm -ivh` bootstrap
   would need those first.

## What `snapshot` would honestly show even if installed

`snapshot` reads frames through PipeWire/libcamera. With no working camera pipeline (see
`CAMERA-PIPELINE-BLOCKERS.md`) it would correctly show a "No Camera" / empty state — installing it
is one milestone, obtaining a real frame is a separate hardware gate. Neither is claimed.

## On-device discovery evidence (read-only)

```
# for t in dnf dnf5 microdnf pkcon packagekitd snapshot gnome-software; do command -v $t || echo MISSING; done
dnf: MISSING · dnf5: MISSING · microdnf: MISSING · pkcon: MISSING · packagekitd: MISSING
snapshot: MISSING · gnome-software: MISSING
# rpm -q snapshot gnome-software pipewire wireplumber
package snapshot is not installed ... package pipewire is not installed ... package wireplumber is not installed
```

## Verdict

- **Native camera app installed → BLOCKED_NETWORK / BLOCKED_SESSION** (no dnf, no network).
- **Native camera app shown on device → BLOCKED** (cannot install).
- **Real S10+ camera frame captured → BLOCKED_HARDWARE** (separate, pre-existing; see next doc).

The existing A52 Camera PWA (`org.nuxel.Camera`, private) and its durable `media_store.py` were
preserved untouched. No simulated camera app or fake frame was substituted.
