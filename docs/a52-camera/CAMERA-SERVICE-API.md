# A52 Camera Service API

## Architecture (chosen, privilege-minimized)

Because the S10+ FIMC-IS hardware cannot be captured through a standard V4L2
path (see `MEDIA-PIPELINE-ANALYSIS.md`), there is **one** authoritative userspace
integration path, with no duplicate daemons:

```
PWA (Camera / Photos)
  → window.NuxelBridge.call(namespace, verb, params)          (local HTTP 127.0.0.1:8080)
  → nuxel-http-bridge (api.py) RPC verb → D-Bus method map
  → nuxel-bridge (system bus, org.nuxel.Bridge)               (capability gate + file store)
  → MediaStore (media_store.py)                               (/var/lib/nuxel/media)
```

The historical non-standard "camera portal" has been **renamed off the standard
`org.freedesktop.portal.Camera` bus name** and is now a **private broker**
(`org.nuxel.Camera`) that reports honest `NO_CAMERA`. It never implements the
standard portal `AccessCamera`/`OpenPipeWireRemote` API under a hijacked name.

## D-Bus / API surface

### `org.nuxel.Bridge` (system bus) — file-backed media verbs

| Verb (namespace.verb) | D-Bus method | In signature | Description |
|---|---|---|---|
| `camera.status` | `CameraStatus` | `s` | honest `{camera_present, capture_verified:false, error}` |
| `camera.list-captures` | `CameraListCaptures` | `ss` | metadata-only list (never base64) |
| `camera.capture` | `CameraCapture` | `ssss` | save a bounded base64 payload (kind,mime,data) |
| `camera.open` | `CameraOpen` | `ss` | return one capture's bytes (bounded) |
| `camera.delete` | `CameraDelete` | `ss` | delete the real file + index entry |

Capability gating: `camera.capture`/`camera.delete` require `camera:capture`;
`camera.list-captures`/`camera.open`/`camera.status` require `camera:preview`.

### `org.nuxel.Camera` (session bus) — private broker (formerly misnamed)

| Method | Signature | Semantics |
|---|---|---|
| `IsCameraPresent` | `s → b` | true iff a real (non-synthetic) capture device node exists |
| `AvailableCameras` | `a{sv} → a{sv}` | enumerated state with `synthetic` flag |
| `RunCamera` | `a{sv} → o` | private: start a stream (never a standard portal handle) |
| `Release` | `o → ()` | stop the stream |
| `Subscribe` / `Unsubscribe` | — | minimal no-op compatibility |

It is **explicitly not** the standard `org.freedesktop.portal.Camera` (whose
real methods are `AccessCamera(options)→handle`, `OpenPipeWireRemote(options)→fd`,
`IsCameraPresent`, `version`). Standard portal integration would require
xdg-desktop-portal + PipeWire + a functioning capture backend, none of which
exist on this device today.

## Lifecycle

`CLOSED → AUTHORIZING → OPENING → STREAMING → CAPTURING/RECORDING → STOPPING → CLOSED`
with explicit `NO_CAMERA`, `PERMISSION_DENIED`, `CAMERA_BUSY`, `LOW_STORAGE`,
`THERMAL_PAUSE`, `DRIVER_UNAVAILABLE` error states. The camera is closed on
`visibilitychange`/`pagehide`/lock/app-terminate; recording auto-stops on lock
(no invisible background recording in this release).

## Security policy

- Media files are owned by the `nuxel-bridge` service user (mode `0640`), written
  atomically (temp → fsync → rename), under `/var/lib/nuxel/media`.
- The list verb returns **metadata only**; pixel data is fetched per-item via
  `camera.open` (bounded by `MAX_PHOTO_BYTES*2`).
- No root-owned unlimited web API; no untrusted-page silent camera/mic access;
  no analytics upload; no EXIF GPS without explicit opt-in.
- Permission grants/revocations are persisted by the portal and mirrored by the
  bridge (existing `permissions.request`/`permissions.revoke` verbs).
