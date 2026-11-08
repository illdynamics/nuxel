# Camera completion report — Galaxy S10+ (`beyond2lte`)

## 1. Executive verdict

`BLOCKED_FIRMWARE` (first failing stage: **firmware**). The kernel binds five sensor modules and exposes many `exynos-fimc-is-*` V4L2 nodes, but none of the expected sensor/ISP setfiles or calibration blobs are present, no media/subdev graph is exposed, and no integrated frame has ever been captured. A driver-bound node is not a camera.

## 2. Target identity

- SM-G975F `beyond2lte`, Exynos 9820.
- Live sensor modules from `dmesg`:
  - `FIMC-IS-SENSOR-MODULE-2L4` `fimc-is_sensor_2l4@20` (rear main, S5K2L4)
  - `FIMC-IS-SENSOR-MODULE-3M3` `fimc-is_sensor_3m3@5A` (rear tele, S5K3M3)
  - `FIMC-IS-SENSOR-MODULE-3P9` `fimc-is_sensor_3p9@2D` (rear ultra-wide, S5K3P9)
  - `FIMC-IS-SENSOR-MODULE-3J1` `fimc-is_sensor_3j1@10` (front main, S5K3J1)
  - `FIMC-IS-SENSOR-MODULE-4HA` `fimc-is_sensor_4ha@10` (front IR/depth, S5K4H7)
- Confidence: **high** for bound module identities and node names; **unproven** for physical frame output.

## 3. What already exists

| Area | Source/path |
|---|---|
| Policy/config | `configs/nuxel/camera/camera.json`, `configs/nuxel/camera/README.md` |
| Native UI | `shell/nuxel-camera-native/`, `shell/nuxel-camera-portal/` |
| Diagnostics | `tools/s10plus/a33/nuxel-camera-diag.sh`, `tests/pwnage65000` hardware tests |
| Kernel | downstream 4.14.253 Exynos FIMC-IS; live `/dev/video*` nodes; no `/dev/media*`, no `/dev/v4l-subdev*` |
| Firmware search | `/lib/firmware`, `/vendor/firmware`, `/vendor/firmware/camera`, `/vendor/etc/firmware`, `/etc/firmware` |

## 4. Latest evidence

| Check | Result | Tier |
|---|---|---|
| `nuxel-camera-diag.sh status --json` | `state=BLOCKED_FIRMWARE`, `first_failing_stage=firmware` | `PASS_DEVICE_RUNTIME` |
| Video nodes | 39+ nodes, including `/dev/video111` = `exynos-fimc-is-30c`; `/dev/video110` = `-30s`; `/dev/video112` = `-30p` | `PASS_DEVICE_RUNTIME` |
| Media controller | no `/dev/media*`; `media_graph_readable=false` | `PASS_DEVICE_RUNTIME` |
| Subdev nodes | none | `PASS_DEVICE_RUNTIME` |
| Firmware found | `[]` | `PASS_DEVICE_RUNTIME` |
| Firmware missing | `s5k2l4_setfile.bin`, `s5k3m3_setfile.bin`, `s5k3p9_setfile.bin`, `s5k3j1_setfile.bin`, `s5k4h7_setfile.bin`, `exynos9820_camera.bin`, `is-camera.bin`, `is-camera-3.bin`, `camera_calibration.bin`, `setfile.bin` | `PASS_DEVICE_RUNTIME` |
| Physical frame | `frame_captured_verified=false` | `BLOCKED_HARDWARE` |
| Capture command | not run (would require owner action; `capture --yes` is explicit) | `NOT_TESTED` |

## 5. Full dependency chain

| Stage | Current state | Evidence |
|---|---|---|
| Sensor silicon + I2C/control | five modules probed/bound | `dmesg` above |
| Regulators/clocks/reset/GPIO | power sequence messages present; 3P9 reports failed `gpio_subcam_sel` / `gpio_mipi_sel` | `dmesg` |
| MIPI CSI receiver | FIMC-IS sensor platform devices present | `dmesg` / DT |
| FIMC-IS ISP / 3A / MCU | FIMC-IS nodes exist; no ISP firmware | node names + firmware scan |
| V4L2 node / private ioctl | `exynos-fimc-is-*` nodes exist; no standard media graph | `/sys/class/video4linux` |
| DMA buffer / userspace | no libcamera handler; no proven private-ioctl client | source tree |
| PipeWire/portal/app | Camera UI exists; backend capture deferred | `shell/nuxel-camera-native` |

## 6. First failing stage

**Firmware.** Expected sensor setfiles and Exynos ISP firmware/calibration are absent from every searched path. Even if a node accepts an ioctl, the ISP cannot run the sensor tuning/3A pipeline without its setfiles and calibration. The historical A53 report also recorded standard `VIDIOC_S_FMT` returning `errno=25` (`ENOTTY`) on `/dev/video111` and REQBUFS/QUERYBUF failing; that remains consistent with a private, vendor-specific interface rather than a standard V4L2 capture node.

## 7. Why prior attempts have not completed the feature

- `docs/a53/CAMERA-PIPELINE-BLOCKERS.md` documented five driver-bound sensors but no physical frames, no standard media graph, and no compatible libcamera pipeline handler.
- The repo deliberately does not install an Android camera HAL or a vendor `libexynoscamera` (`configs/nuxel/camera/camera.json:never_install`).
- A node name or a successful power-sequence message was never promoted to a captured frame.

## 8. Best recommended architecture

**Primary:** a dedicated **libcamera Exynos FIMC-IS pipeline handler** that speaks the exact private ioctl/control ABI used by this downstream kernel, plus the vendor setfiles/ISP firmware for the five sensors. This keeps the standard Nuxel V4L2 → PipeWire → portal → app path and avoids an Android HAL.

**Fallback:** a narrowly scoped kernel adaptation that exposes a standards-compliant media-controller graph and V4L2 capture nodes, if the vendor ABI cannot be documented safely. This is a larger kernel change and needs a separate bring-up mission.

**Not recommended:** transplanting a Pixel/Qualcomm camera stack, a generic `libcamera` pipeline for a different Exynos generation, or a fake/synthetic capture node.

## 9. Required work inventory

| Area | Work |
|---|---|
| Firmware/provenance | Owner-supplied `s5k2l4/3m3/3p9/3j1/4h7` setfiles, `exynos9820_camera.bin`/`is-camera*.bin`, `camera_calibration.bin`; verify hashes; document license |
| Kernel/DT | Confirm FIMC-IS private ioctl ABI, sensor power sequences, 3P9 GPIO/MIPI selection, IOMMU/DMA heap |
| Userspace | libcamera pipeline handler, format negotiation, request/queue/dequeue, 3A integration |
| Service/API | camera portal/PipeWire node, permission model, privacy indicator |
| UI | native camera preview/still/video; fail-closed when no frames |
| Tests | physical unique-scene stills, repeated capture, suspend/resume, privacy deny |

## 10. Source/upstream research

- Kernel: Samsung downstream `Linux4/android_kernel_samsung_exynos9820` 4.14.253 tree in `kernel/s10plus/`.
- Userspace: no upstream libcamera pipeline for this exact FIMC-IS generation in the repo; a new handler is required.
- Android vendor camera provider is explicitly out of scope for the Nuxel image.

## 11. Buildability

- A userspace libcamera handler can be built from public sources with the current aarch64 toolchain.
- The vendor setfiles/ISP firmware and calibration are **not** in the repo and are not redistributable without owner authorization; without them the ISP pipeline cannot be complete.
- No kernel flash is authorized in this mission.

## 12. Risks and constraints

- Wrong setfile/calibration → bad image quality or sensor/ISP instability.
- Private ioctl misuse → kernel oops or sensor power-sequence damage.
- Privacy: camera must remain fail-closed; no synthetic frames.
- Do not write sensor calibration/EEPROM or raw sensor registers.

## 13. Phased roadmap

| Phase | Goal | Gate |
|---|---|---|
| 0 | Capture a harmless enumeration/private-ioctl trace on one identified node | No stream-on; no frame claim |
| 1 | Minimal rear-main preview with correct setfile | Physical unique-scene frame |
| 2 | Still capture, exposure/WB/focus | Repeated stills + metadata |
| 3 | Front camera and additional lenses | Per-sensor frames |
| 4 | Video, OIS, advanced modes | Sustained capture |
| 5 | Portal/PipeWire integration and privacy UX | App-level capture |

## 14. Acceptance test matrix

| Test | Required evidence |
|---|---|
| Integrated rear frame | unique timestamped frame from real scene, not test pattern/UVC |
| Front frame | same for front sensor |
| Format/control | S_FMT/REQBUFS/QBUF/DQBUF success on the chosen node |
| Repeated capture | ≥100 frames without oops/timeout |
| Suspend/resume | capture resumes after resume |
| Privacy | deny → no frame, indicator correct |

## 15. Owner inputs required

- Vendor setfiles and ISP/calibration blobs for this exact SM-G975F board (or authorization to extract from the owner’s vendor partition).
- One physical camera test session.
- Recovery access if a kernel/userspace experiment misbehaves.

## 16. Confidence and gaps

- **Proved:** five sensor modules bound; FIMC-IS nodes exist; firmware/setfiles missing; no media graph; no verified frame.
- **Inferred:** the private FIMC-IS ioctl ABI is the usable interface; a libcamera handler is the least invasive path.
- **Unknown:** exact vendor ABI revisions, setfile compatibility, 3P9 GPIO/MIPI fix, calibration quality.

## 17. Reflash impact (controlled maintenance)

| Question | Answer |
|---|---|
| Does completing camera require a reflash? | **YES.** Vendor sensor setfiles, Exynos ISP firmware/calibration and the libcamera FIMC-IS handler must live in the system image; a writable `/lib/firmware` paste is not a controlled production path. |
| Boot/kernel too? | Only if the private FIMC-IS ioctl ABI/DT needs kernel changes; the current kernel already binds the sensors. |
| Can it be deployed over SSH now? | **NO** for a complete camera. Userspace-only changes cannot create missing firmware/ISP frames. |
| Batch with PWNAGE-93000? | **YES.** PWNAGE-93000 is already deployed over SSH and needs no flash; include its userspace payload in the same system image so one A/B flash carries both. |
| Controlled batch | System image + (only if needed) boot/kernel. Flash the inactive A/B slot, verify camera enumeration/frame capture, then switch slots. |
| Rollback | Before switching, preserve the current slot; fall back to the previous slot if camera/boot fails. |
| Risk if postponed | No camera frames; no user-visible regression in unrelated features. |
