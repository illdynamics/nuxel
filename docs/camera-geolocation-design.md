# Nuxel Camera & Geolocation Design

This document describes the plumbing for two cross-cutting Phase-4 features:

1.  **Camera** — an `xdg-desktop-portal`-style camera backend that hands PWAs a
    PipeWire node for live camera capture and preview.
2.  **Geolocation** — a shared bridge proxy so PWAs resolve location through the
    Nuxel bridge (GeoClue via the portal on hardware, a synthetic location in
    the VM) instead of the blocked native `navigator.geolocation`.

Both are implemented as *scaffold + design* today. On the ARM64 UTM VM the
backend produces a synthetic color-bar node end to end; on mustang (Phase 2)
the same backend switches to the real camera v4l2 source. No physical hardware
is required to validate the VM path.

---

## 1. Camera

### 1.1 Background

Nuxel restricts native WebRTC camera access in PWAs for the same sandbox reason
it blocks native geolocation: per-app capability gating happens server-side in
`nuxel-bridge` (see `docs/security-model.md`), and the camera stream must be
owned by the compositor / media stack, not the unprivileged Web renderer.

The standard Linux mechanism for granting a compositor-managed video stream to
an app is `org.freedesktop.portal.ScreenCast`. We expose a simplified
`org.freedesktop.portal.Camera` interface modelled on ScreenCast but oriented at
camera capture:

```
org.freedesktop.portal.Camera  /org/freedesktop/portal/camera
  RunCamera(a{sv} options) -> o handle
  Release(nodeid)
  AvailableCameras(a{sv} options) -> a{sv}
  Subscribe() / Unsubscribe()
```

The response to `RunCamera` carries the `node_id` of the PipeWire node plus an
optional file descriptor (fd-passing is disabled in the minimal backend).

### 1.2 Implementation

* **Backend service** — `shell/nuxel-camera-portal/nuxel_camera_portal.py`
  (Python, GTK-free, uses `python3-gi` + `python3-gst`).
* **systemd unit** — `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service`.
* **D-Bus name** — `org.freedesktop.portal.Camera` on the session bus (system
  bus with `--system-bus` for root services).

Two backends are selected by CLI flag:

| Mode         | Flag          | Pipeline                                                     |
|--------------|---------------|--------------------------------------------------------------|
| VM synthetic | `--synthetic` | `videotestsrc ! videoconvert ! pipewiresink` (color bars)   |
| Hardware     | `--hardware`  | `v4l2src device=/dev/video0 ! videoconvert ! pipewiresink`  |

The pipeline publishes a PipeWire node named `org.nuxel.Camera.synthetic`
(VM) or `org.nuxel.Camera.main` (hardware). `RunCamera` starts the selected
pipeline and returns the PipeWire node id dynamically discovered from the
pipewiresink element's `node.id` GObject property, encoded into the returned
object handle (e.g. `/org/nuxel/camera/<node_id>`). The node id is not a fixed
value — the VM typically reports an id determined by the live PipeWire graph
(often not 86) — so the camera PWA should use whatever node id `RunCamera`
returns to attach the preview.

### 1.3 Data flow

```
camera-gallery PWA (manifest capability "camera:preview"/"camera:capture")
        │  bridge.call('camera', 'request', {})
        ▼
nuxel-bridge (services/nuxel-bridge)  — capability gate + session/API token
        │  GDBus org.freedesktop.portal.Camera:RunCamera()
        ▼
nuxel-camera-portal  — builds PipeWire node, returns node_id
        │
        ▼
camera PWA attaches the rendered stream (HTMLVideoElement srcObject / WebRTC)
```

### 1.4 VM validation

From the ARM64 UTM VM:

```bash
# Session scope
install -m0644 shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service \
    /etc/systemd/system/nuxel-camera-portal.service
systemctl daemon-reload
systemctl enable --now nuxel-camera-portal

# Smoke-test (non-daemon): print JSON state
/usr/bin/python3 shell/nuxel-camera-portal/nuxel_camera_portal.py --once --synthetic

# Inspect the PipeWire node
pw-cli list-objects Node | grep -A2 'org.nuxel.Camera'
```

Expected `--once` output when GStreamer/PipeWire are present:

```json
{"status": "ok", "cameras": [{"id":"synthetic","source":"synthetic-colorbar",
 "synthetic":true,"capabilities":["camera:capture","camera:preview"]}], "active": true}
```

### 1.5 mustang (Phase 2) notes

* Replace the device path with the correct SoC camera v4l2 node (usually
  `/dev/video0` on the main sensor). On mustang this is the Samsung ISOCELL
  sensor attached via the Google SoC camera pipeline.
* The backend runs as a service in the graphical session. On the Alpine/pM-OS
  root-init target (mustang) use the OpenRC wrapper equivalent (see
  `docs/init-system.md`).
* FD passing is intentionally disabled in the scaffold; enable it once the
  PipeWire protocol native handle exchange is validated on the VM.

---

## 2. Geolocation

### 2.1 Background

`navigator.geolocation` requires the runtime's permission gate, and on mustang
there is no GeoClue/portal backend wired to the Web runtime. Nuxel therefore
**blocks native** `navigator.geolocation` and resolves all location through the
bridge.

### 2.2 Manifest contract

A PWA must NOT enable native geolocation. Instead it declares the capability and
routes through the shim:

```json
{
  "name": "Nuxel Maps",
  "nuxel": {
    "capabilities": ["location:read"]
  }
}
```

> Do NOT add `"geolocation"` to the manifest `permissions`. The bridge is the
> sole source of location truth.

### 2.3 Implementation — `pwa/nuxel-common/geolocation.js`

`pwa/nuxel-common/geolocation.js` installs a read-only `navigator.geolocation`
shim that proxies all calls through `bridge.call('location', 'request', {...})`.
It exposes:

* `NuxelGeolocation.installShim()` — replace native geolocation (done on load).
* `NuxelGeolocation.getCurrentPosition(success, error, options)`
* `NuxelGeolocation.getCurrentPositionAsync(options)` → Promise
* `NuxelGeolocation.watchPosition(...)` / `clearWatch(id)` — naive poll-based
  watch re-requesting through the bridge.

The bridge `location` capability resolves to:

| Deployment  | Backend                                                        |
|-------------|----------------------------------------------------------------|
| Hardware    | GeoClue via `org.freedesktop.GeoClue2` (xdg-desktop-portal)    |
| VM          | Synthetic fixed location (e.g. Mountain View HQ, `52.3676/4.9041` ref) |

Response shape (from `nuxel-bridge`):

```json
{
  "success": true,
  "coords": {
    "latitude": 52.3676, "longitude": 4.9041, "accuracy": 65,
    "altitude": null, "altitudeAccuracy": null, "heading": null, "speed": null,
    "timestamp": 1765500000000,
    "source": "nuxel-bridge", "synthetic": true
  }
}
```

### 2.4 Data flow

```
map / weather PWA        // navigator.geolocation shim (nuxel-common)
        │  bridge.call('location', 'request')
        ▼
nuxel-bridge             // capability "location:read", token gate
        │
        ├─ hardware: GeoClue2 backend via portal
        └─ VM: synthetic coords
        ▼
response -> PWA coords
```

### 2.5 VM validation

```bash
# In a PWA context (or devtools console):
await NuxelGeolocation.getCurrentPositionAsync({ accuracy: true });
# => { coords: { latitude: ..., ... , synthetic: true }, ... }
```

---

## 3. Capability & token notes

Both features use the same per-session/PWA API-token mechanism described in
`docs/security-model.md`. The bridge refuses `camera:*` / `location:read`
requests without a valid token and an explicit grant recorded under
`org.nuxel.<App>`.

## 4. Artifacts

| Path                                             | Purpose                              |
|--------------------------------------------------|--------------------------------------|
| `shell/nuxel-camera-portal/nuxel_camera_portal.py` | Camera portal backend              |
| `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service` | systemd unit |
| `pwa/nuxel-common/geolocation.js`                | Geolocation bridge proxy             |
| `docs/camera-geolocation-design.md`              | This document                        |
