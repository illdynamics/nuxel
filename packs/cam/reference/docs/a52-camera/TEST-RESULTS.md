# A52 Test Results

## Automated (offline, host) — all PASS

Run with `bash tests/a52/run-all.sh`.

| Suite | Checks | Result |
|---|---|---|
| `tests/a52/test-portal-contract.py` | 9 | PASS — private `org.nuxel.Camera`, IsCameraPresent, no freedesktop collision, no `--synthetic` default |
| `tests/a52/test-camera-frontend.py` | 17 | PASS — no localStorage database, no 1440×3120, facingMode persisted, MediaRecorder, file-backed capture, honest states |
| `tests/a52/test-camera-inventory.py` | 7 | PASS — front sensor s5k3j1 corrected, synthetic opt-in, owner-initiated capture |
| `services/nuxel-bridge/test-media-store.py` | 21 | PASS — atomic write, collision-safe, rebuildable index, delete, size cap, honest extensions |
| `services/nuxel-bridge/test-camera-bridge.py` | 19 | PASS — permission gating, capture→list→open→delete round trip, no base64 in list, D-Bus signatures |
| `tools/s10plus/a33/tests/hw-subsystems/test-camera-diag.py` | all | PASS — config + diagnostic OFFLINE_TESTED |
| `nuxel-camera-diag.sh selftest` | 4 fixtures | PASS |

**Total: 73+ offline checks pass.**

## Physical handset acceptance — NOT RUN (hardware blocked)

The owner-assisted physical gates (real rear preview, real JPEG still, 10 s
video, front camera, reboot persistence) are **not applicable** until a lawful
FIMC-IS capture path exists. No mock data was substituted, and no physical
camera claim is made. The device-side read-only discovery that WAS performed is
in `EVIDENCE-INDEX.md` / `HARDWARE-INVENTORY.md`.

## What was physically verified on the device (read-only)

- Device identity, kernel, bootloader, thermal (21–27 °C).
- All 5 sensors + ISP + OIS + EEPROM enumerated and bound.
- `VIDIOC_S_FMT → ENOTTY` on every FIMC-IS capture node (reproducible).
- No PipeWire/WirePlumber/xdg-desktop-portal/v4l2src/libcamera on the device.
