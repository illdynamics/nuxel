# `configs/nuxel/camera/` — camera bring-up, portal and gallery (area 27)

| File | Install to | Purpose |
|---|---|---|
| `camera.json` | `/etc/nuxel/camera/camera.json` | Sensor inventory (front/rear, expected vs observed), V4L2/media node candidates, firmware-blob search paths, pipeline stages, portal contract (unit/backend/methods/install paths/synthetic rule), capture+gallery app contract with bridge verbs, recording-privacy rules, capture output policy |

Runtime state (created on first use): `/var/lib/nuxel/camera/` for owner-test stills.

## Honest boundaries

* **No Android camera HAL is installed or depended on.** The userspace path is
  `V4L2 -> PipeWire -> xdg-desktop-portal Camera -> nuxel-home camera UI`.
* Sensor names, nodes and firmware blobs are **enumerated** and printed with their
  real paths. `expected_on_s10plus` in `camera.json` is the *shipped hardware*
  (from the beyond2lte DTS / S10+ spec) and is never reported as an observation.
* A bound sensor driver is **not** proof that a frame can be captured, so the tool
  never claims one: every status output carries `"frame_captured_verified": false`
  and the verdict for a fully-enumerated device is `READY_UNTESTED`.
* The portal's **synthetic** `videotestsrc` node (VM / no camera) proves the
  *chain* works. It is explicitly reported as `synthetic` and is never evidence
  that the S10+ camera works.
* `nuxel-camera-diag.sh portal` verifies the portal hop-by-hop **from the policy**
  (`pipeline.portal`): unit, backend, install paths, interface methods, the
  capture app and its declared bridge verbs. It names its own first failing stage
  (`unit_installed` → `backend_installed` → `app_installed` → `pipeline_open`) and
  never falls back to a hard-coded `/dev/videoN`; the app/policy verb sets are
  compared and a mismatch is reported rather than assumed away.
* Recording privacy: indicator required, no stealth recording, no hidden
  microphone/camera bypass, background recording user-controlled with a visible
  status and an always-available stop control.

## Commands

```sh
nuxel-camera-diag.sh status [--json]      # inventory + verdict + first failing stage
nuxel-camera-diag.sh list                 # per-node enumeration (video/subdev/media + names)
nuxel-camera-diag.sh fw                   # which expected firmware blobs exist / are missing
nuxel-camera-diag.sh pipeline             # stage-by-stage report, first failing stage named
nuxel-camera-diag.sh portal               # portal unit/backend/app/verbs, verified from camera.json
nuxel-camera-diag.sh capture --yes <out>  # ONE bounded still on an explicit owner command
nuxel-camera-diag.sh report               # append evidence to /var/log/nuxel/camera-diag.log
nuxel-camera-diag.sh selftest             # 4 offline fixtures
```

Owner procedure: `docs/beta-finalization/manual-proof/15-camera.md`.
Verdicts: `READY_UNTESTED`, `PRESENT_UNREADABLE`, `BLOCKED_FIRMWARE`, `NO_V4L2_DEVICE`.
