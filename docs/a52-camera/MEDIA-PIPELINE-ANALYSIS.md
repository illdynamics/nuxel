# A52 Media Pipeline Analysis

## Intended pipeline (design) vs reality

Intended (historical `configs/nuxel/camera/camera.json`):
`V4L2 → PipeWire → xdg-desktop-portal Camera → WebKitGTK getUserMedia → Nuxel Camera`.

Observed reality on the device:

| Hop | Design assumption | Observed |
|---|---|---|
| Physical sensor | 5 sensors, ISP | ✅ present + bound (see inventory) |
| V4L2 standard capture | `v4l2src` / libcamera reads a capture node | ❌ nodes are vendor MPLANE + `V4L2_CAP_EXT_PIX_FORMAT`; `VIDIOC_S_FMT → ENOTTY` |
| Media controller | `/dev/media*` | ❌ none |
| PipeWire | camera node publisher | ❌ not installed / not running |
| WirePlumber | video monitor | ❌ not installed |
| xdg-desktop-portal | standard `org.freedesktop.portal.Camera` | ❌ not installed; the repo ships a nonstandard private broker under that name |
| WebKitGTK | `getUserMedia` | ⚠️ runtime present (4.1 + 6.0) but no camera backend beneath it |
| GStreamer | `v4l2src` element | ❌ element absent (only `videotestsrc`) |

## First failing subsystem

**The V4L2 capture interface itself.** The Samsung FIMC-IS vendor driver does not implement
the standard `VIDIOC_S_FMT` ioctl:

```
nuxel-v4l2-capture-test.py /dev/video110 /dev/video111 /dev/video112 /dev/video160
  S_FMT    FAILED errno=25 (Inappropriate ioctl for device)
  REQBUFS  FAILED errno=22 (Invalid argument)
  QUERYBUF FAILED errno=22 (Invalid argument)
```

`errno=25 (ENOTTY)` is definitive: the driver rejects the standard format-negotiation ioctl.
The nodes advertise `V4L2_CAP_VIDEO_CAPTURE_MPLANE` plus `V4L2_CAP_EXT_PIX_FORMAT` (0x00200000),
the Samsung vendor extension that signals the extended/private format path.

## Why libcamera cannot help (today)

- No `/dev/media*` media controller → no media graph for a pipeline handler to walk.
- No subdevices exposed (`/dev/v4l-subdev*` absent) → no sensor pad/link configuration.
- No standard pixel-format ioctls on the capture nodes.
- libcamera is not installed, and installing it would not create a driver (per mission: a
  libcamera install alone is not a functioning camera).

## Scenario classification

**Scenario E** (vendor camera stack demands Samsung proprietary interfaces), with elements of
**Scenario B** (driver present, capture fails). The downstream 4.14 FIMC-IS driver is the Samsung
vendor stack; streaming requires `libexynoscamera` (the Android camera HAL userspace) which:

1. is a proprietary Samsung/Android framework component,
2. is not installed on this Fedora ARM64 rootfs,
3. cannot be lawfully extracted from an unrelated phone or installed "by stealth".

## Userspace path that IS independently buildable/testable

Because the hardware path is blocked, the following userspace pieces remain valid and were the
focus of the app/backend work (see `CAMERA-APP-COMPLETE.md`, `PHOTOS-MEDIA-STORAGE.md`):

- A correct **private Nuxel camera broker** (renamed off the standard portal bus name) that
  reports honest `NO_CAMERA` when no capture device exists and never silently substitutes
  `videotestsrc` as a real camera.
- A **file-backed media store** replacing `localStorage`-as-database (no quota loss).
- A **completed Camera UI** that correctly handles permission deny/allow, front/rear device
  state (persisted before stream teardown), Photo/Video mode, timer, and honest unavailable
  states for flash/focus/zoom.
- A **completed Photos app** over the shared media index with real file-backed thumbnails.
