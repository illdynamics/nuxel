# Camera recovery — 17 November 2026

**Physical camera remains blocked. No frame, firmware installation, sensor
initialization, reboot or flash was performed in this session.** Host firmware
recovery is complete; executable DDK compatibility is not established.

## Repository reconciliation

Started at `feat/cam` / `380d8ee1` with only untracked owner kit and `cam.md`.
`/private/tmp/nuxel-camera-endgame-audit` was clean at `a4ad813c` and was exactly
two commits ahead. Reviewed both patches and fast-forwarded the current branch,
preserving original commit identities `180d9839` and `a4ad813c`. The separate
worktree and all unrelated local files remain intact. The kernel's ignored
`.build/src` has existing modifications and was inspected without changing it.

## Exact failure

[Machine-readable loader map](evidence/camera-recovery-20261117/camera-loader-paths.json)
and [numbered source excerpts](evidence/camera-recovery-20261117/loader-source-excerpts.txt).
The phone's `/root/kbuild` and `/root/kbuild/src` copies of `fimc-is-sec-define.c`
match the pinned Git source byte-for-byte (SHA `a0e906f5808885948f50c337cedfed33d4f95900497d4b7886740007eaee72ce`).
The associated build object was also retrieved read-only and inspected.
This correlates the build tree; it is not a running BOOT partition attestation.

`fimc_is_sec_sensorid_find()` assigns `FIMC_IS_DDK = fimc_is_lib.bin`.
`fimc_is_sec_fw_sel_eeprom()` lines 3237–3247 constructs
**`/system/vendor/firmware/fimc_is_lib.bin`**, calls `filp_open(O_RDONLY)`, and
on `IS_ERR(fp)` prints the exact unqualified failure message and returns `-EIO`.
It discards the underlying errno. There is **no fallback** in this reader.
Current read-only inventory confirms `/system` is absent. Missing path is the
supported explanation, but the historical open errno was never recorded.
Fresh kernel/journal searches no longer contained the earlier camera log;
EEPROM progress remains the prior report's observation, not a new measurement.

This error precedes reading the phone firmware version, size/signature checks,
and DDK execution. The subsequent version read takes 11 bytes 539 bytes before
EOF (528-byte signature padding). The source lacks a short-file guard there;
all independently recovered candidates exceed the offset. No validation was
masked. The direct reader cannot benefit from patch 0022. That patch is also
absent from the retrieved phone build-tree binary loader.

Later DDK/RTA loading uses `request_binary`/`request_firmware`; the live custom
firmware path is `/vendor/firmware`. The MCU/OIS loader independently requests
`fimc_is_fw_mcu.bin`. External `setfile_*.bin` ISP tuning is distinct from
compiled sensor register tables. The configuration's previous contrary
statements are corrected. No EEPROM/OIS contents were modified or dumped.

Two additional source findings affect any next trial:

* `CAL_READ_DONE` is set before the failed open. A repeated selection can skip
  the reader; a second apparently successful selection would not prove repair.
* Live `CONFIG_USE_SENSOR_GROUP=y` uses packed position/scenario/video fields.
  Previous input 37 decoded to position zero, scenario zero and source video
  zero; it was **not** interpreted as sensor enum 37. The selected rear module
  comes from the platform's rear sensor ID. The client now rejects the old enum
  option and supports explicit rear position zero for the bounded diagnostic.

## Firmware reproduced and compared

The owner AP SHA-256 was rehashed and matches the SSP evidence:
`bf00219f90f7bfc7612cbabf10992fdad79dd7a6dcc3e279b64817ed444dc68d`.
Fresh host-only extraction used `tar -xOf AP…tar.md5 vendor.img.lz4`, `lz4 -dc`,
the SSP sparse-image reader and read-only `debugfs dump`. The fresh image
reproduced all eight files and `build.prop` from the earlier SSP extraction.
Fingerprint: `samsung/beyond2ltexx/beyond2:10/QP1A.190711.020/G975FXXS9DTK9:user/release-keys`.
The AP trailer integrity was verified in the earlier SSP record; no independent
Samsung cryptographic authentication or redistribution license is claimed.

| Comparison | Result |
|---|---|
| Current bundled vs independently extracted owner AP | 8/8 identical |
| Current bundled vs supplied ZIP evidence | 8/8 identical |
| Owner AP vs existing public manifest | 1/8 identical; seven different revisions |
| Hash-pinned Linux4 download vs existing public manifest | 8/8 identical |
| 3J1 vs 4HA | Identical in both independently sourced sets |

[All file hashes](evidence/camera-recovery-20261117/firmware-comparison.json),
[fresh extraction](evidence/camera-recovery-20261117/fresh-ap-extraction.json),
[embedded versions](evidence/camera-recovery-20261117/versions.json).
Stock library/RTA report `L12XLNH01GM`; public reference reports `L12XLOD01GM`.
The stock library build marker is August 2020; public library is April 2021.
Duplicate setfiles are therefore reproducible OEM packaging, not by themselves
proof of corruption. The public manifest was **not** rewritten.

The public source is Linux4/proprietary_vendor_samsung at
`05c9ef8f16e0ad5ab274e408c120dfd99fd5c628`, fetched using the supplied hash-pinned
tool. Evolution-X's device manifest was checked at
`e35cc6e063fb9a2d25b49f0ed54d1b3c9f241901`; it lists the same eight names.
[Exact URL, hash and entries](evidence/camera-recovery-20261117/evolution-manifest.json).
Filename agreement does not establish binary compatibility or a license.

Owner-local, outside Git:

* `~/.local/share/nuxel-camera/fresh-ap` — fresh AP extraction.
* `~/.local/share/nuxel-camera/pinned-reference` — verified public comparator.
* `~/.local/share/nuxel-camera/reviewed-stock-candidate-20261117` — verified
  stock candidate plus blocked deployment proposal.
* `~/.local/share/nuxel-camera/nuxel-fimc-capture-aarch64` — built diagnostic.

## Implementation and validation

The capture client now honors effective device capabilities, rejects zero or
oversized bytesused, invalid data offsets, errored/constant payloads, unsupported
multiple memory planes and missing strides. It logs kernel sequence/timestamp,
refuses output overwrite, checks output writes and STREAMOFF, bounds EAGAIN
polling, and never labels dequeued bytes as physical scene verification.
Single-plane mapping remains a limitation, explicitly refused otherwise.
All S_INPUT modes require informed opt-in; the shell diagnostic no longer
scans through capture candidates or ignores probe failure.

The supplied audit gained strict all-eight reference verification. The generic
verifier exposes `--camera-root`; the downloader validates camera hashes before
publication and propagates failure. Generic firmware installation now skips
camera entries pending a dedicated review. Stock preparation pins independently
reproduced AP hashes in a **separate provenance manifest**, validates source
identity/copies and produces a host-only transaction proposal. It cannot deploy.

Validation evidence in `reports/evidence/camera-recovery-20261117/`:

* Kit: 24 unittest cases (includes inherited baseline cases).
* Stock preparation: 8 tests (provenance, hashes, EOF/size, paths, duplicates,
  symlinks, occupied destination).
* Capture: 5 tests, including executable ASan/UBSan payload boundary tests, CLI rejection tests,
  existing consent/format gates and cleanup regression.
* Native and static AArch64 builds with `-Wall -Wextra -Werror`.
* Inventory, frontend and portal/privacy offline scripts: pass; five diagnostic
  fixtures pass. Missing macOS D-Bus exercised the fail-closed path, not live
  portal operation.
* Public camera verification exits 0; exact DTK9 stock against that public pin
  exits 3, as required. Shell syntax and Git whitespace checks pass.

## Remaining compatibility gate and bounded procedure

The running kernel's interface-library source is byte-identical to its initial
`G973FXXU9FUBD` import (`5c435c1f1cfe`); later camera changes reach FUH3.
DTK9 is Android 10. This is a compatibility question, **not proof that DTK9 is
incompatible**. The version strings and sizes cannot certify callback tables,
metadata layouts, executable entry points or signed-memory behavior.
Additional comparisons against CruelKernel `ac35d5ff…` and older v3.6
`adda2347…` found identical interface files, but different metadata, and did
not establish DTK9 ancestry. The older metadata lacks `remosaic_rotation` and
`mcsc_flip`/`mcsc_flip_result` arrays present in the current shot extension;
callback-file equality therefore does not prove shared data-layout equality.
The full [older-source diff](evidence/camera-recovery-20261117/older-source-comparison.json)
is retained. The failed
GitHub history API request (HTTP 500) was superseded by local Git history.
[Comparison evidence](evidence/camera-recovery-20261117/abi-source-comparison.json).

The missing artifact is a DTK9-correlated camera driver/DDK ABI reference or a
verified exact-module trace with this kernel and a coherent candidate set.
The already recovered AP is **not missing**. No arbitrary replacement archive
is requested, and neither candidate is approved for executable deployment.

The [transaction proposal](evidence/camera-recovery-20261117/deployment-plan.json)
lists every stock file, hash and intended target: the exact direct-read path
under `/system/vendor/firmware` and request_firmware path `/vendor/firmware`,
root:root, mode 0644. It is deliberately `BLOCKED_DDK_ABI_NOT_VERIFIED`.
No kernel flash is required merely to correct these paths.

After resolving compatibility, the reviewable first trial will:

1. Confirm owner presence, recoverable Nuxel boot and TWRP route; record current
   state and reject existing targets/symlink parents. No partition writes.
2. Stage one coherent approved set, verify every target hash, and establish a
   fresh calibration state through a separately approved single reboot if
   required. Never force-reset calibration flags or repeat initialization.
3. Make one rear-only group-input attempt with the corrected diagnostic and a
   15-second external deadline; preserve logs and close the descriptor. Kernel
   hangs may outlive userspace timeout; owner recovery remains necessary.
4. Stop immediately on error, timeout, fault or ambiguous cached selection.
   No automatic retry, other-camera scan or flash. Capture streaming needs a
   separately established ISP-chain configuration and valid G_FMT/planes.
5. Remove only transaction-created files after checking hashes; remove only
   newly created empty directories. If inaccessible, use owner-present TWRP to
   remove the same listed rootfs files. No boot image replacement is planned.

This is a blocked proposal, not an approval-ready executable trial. Once the
ABI gate is resolved, present the exact selected-set command sequence for
approval before hardware action, as requested. First-frame verification still
requires two controlled physical scenes; full module, app/PipeWire/portal,
recording, privacy, suspend and reboot acceptance remain unverified.
