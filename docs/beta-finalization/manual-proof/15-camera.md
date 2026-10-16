# Area 27 — Camera and Gallery (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for config + diagnostic).
Owner action required? **Yes** — a still and a video can only be produced by
aiming the camera at something real, and only a person can judge the result.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820), three rear sensors (12 MP main `s5k2l4`, 12 MP tele `s5k3m3`, 16 MP
ultra-wide `s5k3p9`) and two front sensors (10 MP `s5k2l4sx`-class, 8 MP depth
`s5k4h7`). **No Android camera HAL is installed or depended on.** The userspace
path is `V4L2 -> PipeWire -> xdg-desktop-portal Camera -> nuxel-home camera UI`.

---

## 1. Feature

`configs/nuxel/camera/camera.json` + `tools/s10plus/a33/nuxel-camera-diag.sh`,
plus the existing portal (`shell/nuxel-camera-portal/`) and the camera app
(`pwa/nuxel-apps/camera-gallery/`, "Nuxel Camera"; browsing continues in
`pwa/nuxel-apps/photos/`, owned by the core-apps group):

* front/rear sensor **inventory** kept separate, with `expected_on_s10plus`
  clearly marked as *shipped hardware, not an observation*;
* **enumeration** of `/dev/video*`, `/dev/v4l-subdev*`, `/dev/media*` and of the
  sensor names the kernel actually binds (glob/candidate based, never a
  hard-coded `/dev/videoN`);
* **firmware** blob presence per expected sensor, with the exact **gap** named
  when a blob is absent;
* the **pipeline** as five independently-reported stages (`dev_nodes`,
  `sensor_names`, `firmware`, `media_graph`, `capture`) with the **first failing
  stage** printed;
* a **bounded, owner-only capture** (`capture --yes <out.jpg>`) that writes
  exactly one still, refuses to overwrite, and never runs automatically;
* **recording privacy** rules (indicator required, no stealth recording, no
  hidden microphone/camera bypass, background recording user-controlled with a
  visible status and an always-available stop control);
* a **portal/gallery verification** (`nuxel-camera-diag.sh portal`): the unit,
  the backend, the install paths, the `org.freedesktop.portal.Camera` methods and
  the capture app are read from `camera.json`, checked against the tree, and the
  app's own declared bridge verbs are compared with the policy's — the portal
  chain gets its own first-failing-stage
  (`unit_installed` → `backend_installed` → `app_installed` → `pipeline_open`).

## 2. Why this matters

Camera is the subsystem where an enthusiastic implementation lies most easily: a
driver name in sysfs is not a picture, a `videotestsrc` colour-bar node is not
the S10+ sensor, and a "camera works" claim printed by the portal proves only the
portal. This work therefore keeps three things separate — the *chain* (proven in
VM by a synthetic node), the *enumeration* (proven offline by fixtures) and the
*frame* (only the owner can observe it) — and the mission's evidence rule is
enforced in the tool itself: every `status` output carries
`"frame_captured_verified": false` and a fully-enumerated device is
`READY_UNTESTED`, never `VERIFIED_ON_S10PLUS`.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode
   (`nuxel-power-diag.sh status`).
2. Console/SSH or the on-device terminal.
3. Something to photograph (a lit scene), a microphone to test video audio, and
   the gallery app reachable from the launcher.
4. Snapshot first — this names the failing stage before you touch the app:

   ```sh
   nuxel-camera-diag.sh status          # nodes, identity, firmware, verdict
   nuxel-camera-diag.sh status --json   # machine-readable
   nuxel-camera-diag.sh list            # every node with its real path
   nuxel-camera-diag.sh fw              # which expected blobs are present/missing
   nuxel-camera-diag.sh pipeline        # stage-by-stage; first failing stage named
   ```

   If the verdict is `NO_V4L2_DEVICE` or `PRESENT_UNREADABLE`, **stop**: record it,
   it is a kernel/driver gap (offline work), and it does not gate other areas. If
   the verdict is `BLOCKED_FIRMWARE`, record `fw`'s "missing" list verbatim —
   that is the exact repair input.

## 4. Exact action

1. **Permission path:** open the camera app; it must ask for camera permission
   through the Nuxel permission manager. Grant it. Deny it once first to confirm
   the app refuses to open the camera rather than silently working.
2. **Viewfinder:** open the camera app and **aim it at a lit scene**. A live
   preview must appear without tearing (the preview path is V4L2 -> PipeWire ->
   portal).
3. **Front/rear switch:** tap the switch; the preview must change sensor and the
   image must differ (not a frozen duplicate).
4. **Still capture:** take a photo. Find the file
   (`ls -lt /var/lib/nuxel/camera/ ~/Pictures/ 2>/dev/null | head`) and open it in
   the **gallery app**; the thumbnail must open full-screen and rotate correctly
   when you turn the phone.
5. **Resolution selection:** change the capture resolution, take a second still
   and confirm the file's pixel dimensions changed
   (`file <still>` / `identify <still>`).
6. **Flash:** in a dark room, enable flash and take a still — the torch must fire
   and the frame must be exposed. (The torch itself is documented in area 9,
   `manual-proof/09-flashlight.md`; here it is only the *camera flash* path.)
7. **Video + microphone:** record ~10 s of video with the microphone enabled,
   then **play it back**; audio must be present and lip-sync plausible. Open the
   microphone permission and deny it, then record again — the video must save
   **without** audio and must say so.
8. **Diagnostic capture (independent path):**

   ```sh
   nuxel-camera-diag.sh capture --yes /var/lib/nuxel/camera/owner-test.jpg
   ```

   Exactly one still, only on this explicit command, and it must refuse if the
   file already exists.
9. **Portal chain (no finger needed for the check itself):**

   ```sh
   nuxel-camera-diag.sh portal        # unit + backend + app + verbs + first failing stage
   ```

   Every hop must be reported present (`state: PORTAL_READY_UNTESTED`). A missing
   hop is reported by name with its install path — and the tool never falls back
   to a hard-coded `/dev/videoN`. A **synthetic** node (`videotestsrc`) proves the
   chain only; if the viewfinder shows colour bars, that is the synthetic backend,
   not the S10+ sensor: record **FAIL** for the hardware claim, not "camera works".
10. **Background recording:** start a recording, switch to the launcher, and
   confirm the **recording indicator stays visible** and the stop control is
   reachable. Stop it and confirm the file is listed in recording history.
11. **No auto-capture:** reboot normally and watch the boot — no frame may be
    captured, no torch may fire and nothing may open the camera at boot.

## 5. Expected result

* `status` prints the enumerated nodes/identity/firmware and one verdict, with
  the first failing stage named when a stage fails.
* With a working sensor path: live viewfinder, a still that opens in the gallery,
  a working front/rear switch, a resolution that actually changes the file, a
  flash that fires, and a video with audio you can hear.
* `capture --yes` writes one still and refuses on an existing path; without
  `--yes` it refuses entirely.
* The recording indicator is visible during background recording; there is no
  stealth mode and no hidden microphone/camera bypass.
* Nothing is captured or lit at boot.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| verdict `NO_V4L2_DEVICE` | No `/dev/video*`, `/dev/v4l-subdev*` or `/dev/media*`: `BLOCKED_KERNEL`. Offline driver work; do not retry in a loop. |
| verdict `PRESENT_UNREADABLE` at `sensor_names` | A node exists but no sensor/bridge name is readable — driver gap, not an app problem. Capture `dmesg \| grep -i -E 'camera\|is-\|v4l2\|s5k'`. |
| verdict `PRESENT_UNREADABLE` at `media_graph` | Nodes + identity exist but no readable media device: the media graph is not exposed. |
| verdict `BLOCKED_FIRMWARE` | Sensor identity present, expected blobs absent. Report `fw`'s missing list verbatim; **never** substitute a Pixel/other-device blob. |
| Viewfinder is a colour-bar test pattern | You are looking at the portal's **synthetic** node (VM / no hardware): the chain works, the S10+ camera is unproven — report that, do not call it a camera. |
| Viewfinder works, gallery shows a black/green frame | Capture/format path broken: record the node, `v4l2-ctl --list-formats-ext` and the raw file size. |
| Video has no audio although the microphone is granted | Microphone/route problem (area 6 audio path): record it as a separate FAIL for the audio route, not for the camera. |
| Video has audio although the microphone was denied | A real privacy defect: report it, the microphone must not be opened without permission. |
| Recording indicator missing in background recording | Privacy defect: report FAIL; there is no supported path without the indicator. |
| A frame exists that you did not capture | Defect: report it, nothing in this subsystem captures automatically. |

## 7. Diagnostic command / log path

* `nuxel-camera-diag.sh status [--json] | list | fw | pipeline | portal | capture --yes <out> | report`
  (`tools/s10plus/a33/nuxel-camera-diag.sh`)
* Evidence log: `/var/log/nuxel/camera-diag.log`
* Kernel side: `dmesg | grep -i -E 'camera|v4l2|media|s5k|is-|exynos'`,
  `ls -l /dev/video* /dev/v4l-subdev* /dev/media* 2>/dev/null`,
  `cat /sys/class/video4linux/*/name 2>/dev/null`,
  `v4l2-ctl --list-devices` and `v4l2-ctl -d <node> --list-formats-ext` when
  `v4l-utils` is installed.
* Portal: `nuxel-camera-diag.sh portal` (data-driven, from `camera.json`),
  `systemctl --user status nuxel-camera-portal` (VM),
  `cat pwa/nuxel-apps/camera-gallery/manifest.json | grep -A5 bridge_verbs`.
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-camera-diag.py`
  and `nuxel-camera-diag.sh selftest` (4 fixtures: absent / present-unreadable /
  blocked-firmware / ready-untested).

## 8. PASS / FAIL

* **PASS** — for the sensor role you claim: `status` enumerates the node and the
  sensor identity, `fw` finds the expected blob, the viewfinder shows a live
  image, a still opens in the gallery, video (with and without permission)
  behaves as described, and the recording indicator is always visible. Record the
  node, the sensor name, the blob name and the still's path and byte size.
* **FAIL** — any of: `NO_V4L2_DEVICE`, `PRESENT_UNREADABLE` for a sensor you
  claim, `BLOCKED_FIRMWARE`, a viewfinder that is only the synthetic pattern, a
  still that will not open, audio present with the microphone denied, a missing
  recording indicator, or any frame you did not capture. Record the verdict, the
  first failing stage, the node paths, the missing blobs and the exact output —
  that is what a repair cycle needs.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-camera-diag.sh selftest` → 4/4 fixtures PASS
  (`fixtures/camera-absent`, `camera-partial`, `camera-nofw`, `camera-ready`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-camera-diag.py` → all
  checks PASS (verdict chain, first-failing-stage naming, dedupe, owner-only
  bounded capture, faked-root refusal, no-frame-claimed contract, privacy rules,
  portal unit/backend/app/verb verification with its own first-failing stage, the
  app-manifest cross-check, fragment completeness).
* `bash tools/s10plus/a33/nuxel-camera-diag.sh portal` → `PORTAL_READY_UNTESTED`
  with every hop present and `bridge verbs … (match)` against
  `pwa/nuxel-apps/camera-gallery/manifest.json`.
* A real frame: **not claimed** — every `status --json` emits
  `"frame_captured_verified": false`, the portal's synthetic node is marked
  `synthetic_is_hardware_evidence: false`, and the capability manifest keeps the
  camera at `NEEDS_OWNER_TEST`.
