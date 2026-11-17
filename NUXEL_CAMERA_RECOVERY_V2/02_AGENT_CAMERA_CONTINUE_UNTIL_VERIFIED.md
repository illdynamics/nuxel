# NUXEL S10+ — EXYNOS9820 CAMERA: VERIFIED FIRMWARE → FIRST REAL FRAME → FULL CAMERA STACK
**Engineering continuation / 2026-11-17 / standalone agent mission**

## HARD SUCCESS DEFINITION

Restore the Samsung Galaxy S10+ (SM-G975F, EXYNOS9820, hardware rev 26) camera stack under Nuxel to **genuine, physically captured, verified still and video frames**, then expose the working cameras through appropriate PipeWire, portal, application and permission mechanisms. Complete the supported rear/front module matrix with calibration, autofocus, exposure, preview, photo, recording, privacy, sleep/reboot and stability checks. Distinguish features not available from the current hardware or kernel.

**Never report physical success from enumerated nodes, simulated video, a nonempty device list, `S_FMT` success, a successful `G_FMT` with unusable dimensions, firmware presence, or services merely running.**

Proceed through useful offline work autonomously; do not stop at a narrative summary when there is implementable, testable safe work. However do not autonomously flash, reset, toggle camera power, expose an unrestricted host /sys, install unverified camera blobs, repeatedly force failing sensor initialization, or perform irreversible handset operations. Any actual state-changing hardware trial requires explicit owner approval after a reviewed, bounded procedure and recovery plan.

## CURRENT EVIDENCE AND REPOSITORY RECONCILIATION

Repository: `/Users/wicked/x/nuxel`.
User's reported camera worktree: `/tmp/nuxel-camera-endgame-audit`.
Reported commits:
- `180d9839 camera: fail closed on uncommitted FIMC formats`
- `a4ad813c camera: record live firmware selection gate`

Reported findings (confirm from the worktree and live logs; not re-measured here):
- Live: SM-G975F rev 26, kernel `4.14.253-gf7194c1d15ed-dirty`
- 68 FIMC-IS video nodes; no media/subdev nodes seen
- Rear main 2L4 sensor enum 37 selected once by explicit test permission; EEPROM read
- Failure: `Camera: Failed open phone firmware`, `fimc_is_sec_run_fw_sel ... (-5)`
- No real frame or buffer streaming, no persistent deployment, no camera firmware installed
- No panic/IOMMU fault in the bounded trial

First reconcile `git status`, HEAD, branch, worktrees, their relationships, and the files in `/tmp/nuxel-camera-endgame-audit`. Preserve the existing work and fetch/cherry-pick changes ONLY after confirming patch content, ancestry and tests. Do not overwrite unrelated Nuxel changes. This kit's initial user ZIP upload lacked its central-directory record; the included independent audit nevertheless CRC-checked the eight camera blob members and verified that 7/8 disagree with `firmware/s10plus/manifest.yml`. Re-run that comparison against the **actual live working tree**, which is authoritative over a partial ZIP.

Read:
- `NUXEL_CAMERA_RECOVERY_V2/01_DEEP_CAMERA_AUDIT.md`
- `NUXEL_CAMERA_RECOVERY_V2/ARCHIVE_CAMERA_SHA256_AUDIT.json`
- This complete prompt, and README
- `reports/CAMERA-FIRST-REAL-FRAME.md` in the reported camera worktree (if present)
- `firmware/s10plus/manifest.yml`, original installer/verifier/fetcher
- `configs/nuxel/camera/camera.json` and its README
- Existing FIMC-IS capture client and tests
- Kernel sources, local modifications and exact kernel build configuration
- Earlier camera reports, portal tests and runtime diagnostics.

Make a short reproducible baseline before editing. If local reports, worktrees or artifacts have disappeared, state that fact and recover by verified Git history, not guesses.

## PHASE 1 — ESTABLISH THE EXACT FAILURE IN THE RUNNING KERNEL

Search the real running-kernel-compatible FIMC-IS source for:
`fimc_is_sec_run_fw_sel`, `Failed open phone firmware`, firmware search paths, module/ROM mappings, `fimc_is_sec_fw_find`, `request_firmware`, calibration validation and error propagation.

Do not equate the displayed `-5` with a confirmed `ENOENT`: `-EIO` is an outcome and the failing operation must be identified at source level. Determine:
- exact requested firmware basename, full configured lookup directories, fallback order
- whether it requests `/vendor/firmware`, `/system/vendor/firmware`, `/lib/firmware`, a module-selected path, or a separate phone firmware filename
- whether it reads EEPROM and compares expected module/ROM/phone FW versions before load
- any I/O error translation, filesystem permission/label, firmware signature/version/size checks
- status of `fimc_is_lib`, RTA, MCU, setfiles and independent OIS calibration/focus firmware
- whether the "phone firmware" failure is the first fatal error or a symptom of earlier calibration/ROM selection problems.

Correlate this with read-only actual phone path inventory, mounted filesystem state, firmware loader helper paths, kernel logs and exact device model/revision. Do not mount unknown phone partitions or deploy files as part of discovery. Use grep/find/source inspection first, not repeated live `S_INPUT`.

Deliver: `camera-loader-paths.json` and annotated source references, identifying the first fatal condition and an actionable fix hypothesis.

## PHASE 2 — RECOVER AUTHORITATIVE MATCHING BLOBS

The user previously downloaded the exact Samsung `G975FXXS9DTK9` stock AP archive for SSP recovery. Look for its owner-held local folder containing:
`AP_G975FXXS9DTK9_CL20034833_QB35905779_REV01_user_low_ship_meta_OS10.tar.md5`
and/or the extracted `/vendor/firmware` filesystem under the known owner-local stock staging area. Do not presume the temporary directory from the SSP effort still exists.

**Use this owner-held AP first.** Work offline with read-only extraction and hash verification, outside the Git repository. Validate archive identity, build fingerprint, any vendor build props and the exact SM-G975F/rev-26 camera module selection. Do not take firmware from a different S10 variant or Android release merely because it has the same basename.

The independent attached ZIP audit found:
- `fimc_is_fw_mcu.bin`: manifest SHA matches
- `fimc_is_lib.bin`, `fimc_is_rta.bin` and all five setfiles: SHA differs from manifest
- `setfile_3j1.bin` and `setfile_4ha.bin`: identical both in archived blob hashes AND in the old manifest expectations (not independently a corruption proof).

Inspect `NUXEL_CAMERA_RECOVERY_V2/camera_firmware_audit.py` and run its host tests. Then run it with the current repo root and candidate extracted stock firmware root. Save JSON. Determine for each file: owner-stock hash, archived hash, pinned-manifest hash, source path, size and relevant version/compatibility metadata.

The repository's `firmware/s10plus/fetch-vendor-blobs.sh` names `Linux4/proprietary_vendor_samsung@05c9ef8f16e0ad5ab274e408c120dfd99fd5c628` as the source of its manifest. Use `fetch_pinned_camera_reference.py` as a **host-only optional comparator**, never an installer. It defaults to PLAN ONLY and in download mode only accepts files with hashes matching the pinned manifest; different public source revisions remain unverified until compared. It does not prove compatibility with the owner-held stock firmware.

Also review Evolution-X beyond2lte vendor manifest and other exact-device sources. Record exact revision, URL, hash, license/provenance, kernel differences. Do not use cross-chip Exynos camera firmware, blindly regenerate manifest hashes to accept mismatch, or use arbitrary Internet blobs.

The correct outcome of this phase is a single **coherent** group of firmware/lib/RTA/setfile files that the actual loader selects, with strong provenance, hash evidence, compatible kernel/DDK build and the right sensor/ROM identity. Reject mixtures with unresolved origin.

Do NOT redistribute proprietary blobs into ordinary Git commits. Stage owner-held files into a separate host directory with a hash manifest.

## PHASE 3 — EXPLAIN AND FIX THE LOADER WITHOUT GUESSING

Once the specific source-level failing open/read/version predicate is identified, implement the smallest justified correction.

Possible outcomes (choose only from proof):
- firmware absent on the kernel's effective firmware search paths → prepare a clean install into an exact verified path, with correct ownership/mode/label and provenance
- wrong filename or legacy Samsung path assumptions → fix configuration/search path with tests, rather than silently aliasing arbitrary binaries
- module ID or calibration mismatch → select the correct OEM module package; **never overwrite EEPROM calibration or fabricate IDs**
- size, version, ABI or corruption mismatch → repair the source selection and package; never mask validation failures
- driver defect in FIMC-IS firmware selection → prepare a minimal source patch and regression tests tied to the deployed kernel.

Produce a deployment transaction **plan** showing all files, intended targets, hashes, prerequisites, risks and rollback. No handset writes or kernel flashes without explicit approval for that exact plan. Keep current Nuxel boot image and owner-verified TWRP recovery route available. The device is A-only: never assume inactive A/B partitions.

Preserve/extend the existing safe V4L2 probe changes: `S_FMT` must be followed by valid `G_FMT` and planes/strides; an unsuccessful or zeroed result is not success. `VIDIOC_S_INPUT` physically initializes sensors and requires informed opt-in.

## PHASE 4 — FIRST PHYSICAL FRAME

After owner approval and successful firmware load evidence, perform **one** bounded rear-main 2L4 capture test, not a multi-sensor scan.

Require:
- real kernel-selected firmware and ISP initialization success
- valid V4L2 capture endpoint (not a sensor-management node)
- real pixel format/width/height, multi-planar buffer accounting and correct stride
- bounded buffer allocation/queue, STREAMON, timestamped DQBUF and STREAMOFF
- >0 actual bytes of unique frame payload and validate against all-zero/repeated/fake patterns
- physical capture test under at least two distinguishable real scenes/light changes
- detailed capture logs, image metadata and SHA-256, and no privacy leaks in evidence files
- complete cleanup, closure and post-test kernel log review for IOMMU, faults or leaks.

Failure at any step must be reported as that step; no fabricated screenshot or virtual source can count as a camera frame. Do not silently retry sensor power resets or flash after faults.

## PHASE 5 — ALL CAMERAS AND USERSpace INTEGRATION

Only after one real frame works, map the remaining bound camera modules and independently verify their sensor ID, firmware/setfile/calibration requirements, viewfinder/still/video capabilities, capture controls, and any remaining hardware dependencies. Do not assume all five work because 2L4 works.

Decide whether the existing FIMC-IS V4L2 path can be adapted directly to a stable PipeWire producer and camera portal without an upstream libcamera pipeline. Upstream libcamera does **not** currently advertise Exynos9820 FIMC-IS2 as a supported pipeline; writing a new libcamera pipeline is optional and only justified if existing V4L2/PipeWire integration is inadequate.

Build/test appropriate app integration with:
- preview, stills, recording, stop control
- reasonable focus/exposure/white-balance and orientation metadata where supported
- permission prompts, privacy indicator, no covert/background capture
- user-facing selection of available front/rear cameras
- no synthetic capture reported as physical
- suspend/resume, warm/cold reboot and repeated start/stop stability
- preservation of UI, GNSS, SSP and unrelated Nuxel functionality.

## PHASE 6 — AUTOMATED TESTS, REPORTS AND ITERATION

Carry forward existing 180d9839/a4ad813c tests and prior camera inventory/portal fail-closed tests. Add host-only unit tests for hash mismatches, provenance mismatch, duplicate source blobs, wrong paths, empty formats, wrong endpoint types, buffer plane validation, unexpected EOF and physical-capture evidence gating. Build with `-Wall -Wextra -Werror` as appropriate, use ASan/UBSan for host tests where available, test the AArch64 capture client with appropriate warnings.

Commit small, independently validated fixes. Keep a dated summary: precise verified claims, source citations, files, hashes, commands, test results, phone state and rollback. Never claim any physical result from the offline harness.

The work loop is: find the next highest-impact unresolved **safe** issue → inspect exact source → implement minimal fix → test → commit → update evidence → continue. Avoid wasting tokens recreating past reports or rediscovering downloaded files. Do not stop merely because an easy host test passes.

If a specific missing external artifact, owner authorization or live hardware action is truly required, stop at that boundary and ask for the exact input/approval rather than guessing. **Do not use unlimited reflash/reboot loops or `danger-full-access`/`approval_policy=never` for hardware operations.**

## FINAL ACCEPTANCE

Only mark **FIRST_FRAME_VERIFIED** after an actual rear-main frame from the physical S10+ passes both format and scene-correlation tests. Only mark **CAMERA_FULLY_FUNCTIONAL** when the full supported camera matrix, camera app/portal/video, permissions and stability checks pass on the real phone.

Your immediate deliverables are:
1. Current branch/worktree reconciliation and preserved latest camera commits.
2. `camera-loader-paths.json` with exactly why firmware selection failed.
3. A verified, matching owner-stock vs manifest vs live firmware comparison.
4. A host-staged, coherent candidate set (never installed without review).
5. A minimal supported fix or an exact approved-deployment proposal.
6. Clear first-frame and full-acceptance evidence, or a precise remaining blocker.

Keep pursuing all useful safe engineering work toward real 100%-functional camera behavior, while preserving hardware integrity and honest reporting.
