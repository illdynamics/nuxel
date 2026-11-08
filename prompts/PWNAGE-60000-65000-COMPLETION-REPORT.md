# PWNAGE 60000–65000 — final completion report

## Executive summary

The existing work was preserved. The GPU path is genuinely working and now has
direct runtime proof, including a first-party A/B benchmark and hardware
telemetry. MFC remains safely blocked on firmware + an unflashed kernel patch.
The shell and keyring stacks are live and healthy. GNSS was finished as far as
the missing proprietary BBD patch permits; the canonical inventory and
diagnostics were fixed, tested and deployed. NFC is deployed as an OFF-by-default
native service with unit/mock tests passing; a physical tag read remains an owner
test.

## GPU acceleration — highest priority

- **GPU:** Mali-G76 MC12, Exynos 9820; kbase `r26p0-01eac0 (UK 11.27)` built in, `/dev/mali0`.
- **Kernel/userspace:** vendor kbase → Mesa Panfrost `26.3.0-devel`
  (`a5010bb447`) → Phoc/wlroots 0.19.3.
- **Firmware:** none required by this kbase path; no load failure.
- **Backend:** Phoc GLES2 + GTK3/4 GL + WebKit GPU-SHM. Phoc has 3 ×
  `/dev/mali0`, 0 llvmpipe threads; Home WebKit has 3 × `/dev/mali0` and
  `NUXEL_GRAPHICS_PROFILE_ACTIVE=gpu-rendered-shm-presented`.
- **Hardware rendering proven:** yes. `nuxel-gles-bench` 512×512/128-iteration
  shader: **Mali median 176.3 fps** vs **llvmpipe median 20.2 fps** = **8.73×**
  on identical pixels.
- **Hardware activity:** `gpu_busy` **78–86 %**, `gpu_clock` **200–377 MHz**
  during the burn; `mali_trace` shows `JM_SUBMIT`/`JM_JOB_DONE`.
- **Display:** `FRAMES_OK`, `decon_pan_ok=4936`, `decon_pan_failed=0`, one
  `/dev/fb0` writer, 1440×3040 panel; non-blank screenshot.
- **Software fallback detected?** Not in the active path. llvmpipe was used only
  for the deliberate A/B control. `software-safe` remains available.
- **Reboot persistence:** on-disk profile default and enabled units; not
  re-tested by a reboot in this run (no authorization). Prior cold-boot evidence
  is retained.
- **Remaining blocker:** WebKit DMA-BUF/zero-copy requires a real DRM/GBM node
  (`drmMainDevice()`), absent by design (`CONFIG_DRM_VGEM/EXYNOS` unset). No
  fake node/symlink was created.
- **Final classification:** **`GPU_ACCELERATION_VERIFIED`** (GPU-SHM path);
  `fully-accelerated`/zero-copy remains unavailable.

## Mission completion table

| Mission | Starting state | Work completed | Tests | Final status |
|---|---|---|---|---|
| 60000 GPU | implemented, production default already set | live revalidation, new GLES bench, A/B + telemetry + screenshot evidence | 31 + bench | **GPU_ACCELERATION_VERIFIED** |
| 61000 MFC | implemented, no live userspace | read-only diag/policy deployed; live blocked status proven; no node open | 36 + self-test 17 | **BLOCKED** (firmware + unflashed boot) |
| 62000 shell | implemented/verified | live services, lock/chrome/navdock health audit | 4 (+13 contract) | **COMPLETE AND VERIFIED** (touch owner) |
| 63000 Vault | implemented/verified | live Secret Service owner/collection verification | 25 | **PROVIDER VERIFIED** (owner init) |
| 64000 GNSS | partial canonical inventory | fixed 3 inventory bugs, bridge refactor, diag selftest, tests, deploy/rollback, live deploy | 10 + 13 + diag | **BLOCKED_FIRMWARE** (implemented) |
| 65000 NFC | implemented/deployed | live default-OFF service + selftest + unit tests + docs | 17 + diag | **IMPLEMENTED — HARDWARE VERIFICATION REQUIRED** |

## Test evidence

All commands and per-suite results are in `evidence/regression-tests.txt`.
**316 targeted tests passed**, plus bridge indicator tests and both hardware
diagnostic suites. Live self-tests: MFC 17 checks, NFC PASS, GNSS 5 fixtures.

## Regressions

Checked: services, bridge health, GPU frames, one-writer contract, NFC OFF
state, GNSS rail OFF, no BBD/NFC device open, no new failed units, no MFC
D-state. Two stale test assertions were updated to the shipped/62000 contracts
(details in `regression-report.md`). No working component was rewritten.

## Hardware verification vs static/offline

- **Actual phone:** GPU renderer/maps/fps/telemetry/screenshot/display frames,
  bridge inventory, GNSS inventory, NFC service/status/selftest, keyring owner,
  MFC inventory, service/lock state.
- **Offline/host:** all pytest suites, diagnostic fixture tests, source audits.
- **Not physically tested:** reboot, MFC decode, satellite fix, NFC tag,
  touch/rotation/suspend, HDMI/casting.

## Owner actions

See `owner-actions.md`. The critical ones are: owner reboot observation, explicit
approval for the staged MFC boot image + firmware, GNSS patch/outdoor test, NFC
tag test, and Vault master-password setup.

## Next recommended work

1. Owner reboot → confirm `nuxel-gpu-status --deep` still reports Mali and
   `FRAMES_OK`.
2. If MFC is desired: approve the prepared boot image, install verified
   `mfc_fw.bin`, then bounded QUERYCAP/decode with rollback ready.
3. Obtain the exact BCM4773 BBD patch; implement the native BBD/LHD provider and
   run outdoor acquisition.
4. Owner NFC tag read; then optionally add safe NDEF writing.

- **Live GPU release verifier:** `GPU IMAGE VERIFY: PASS (10 files, 3 symlinks)` against `/` (warning: `file(1)` absent on the phone; ELF arch check skipped).
