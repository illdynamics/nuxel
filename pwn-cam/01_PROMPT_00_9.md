# 01_PROMPT_00_9 — FINAL LIVE EVIDENCE, OWNER TRUST, REAL GOLDEN NO-OP, AND PROMPT 02 ENTRY

**Target:** Nuxel Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos9820, native Fedora, downstream kernel 4.14.253.  
**Purpose:** Finish the *real, evidence-backed* exit gates of Prompt 00 and Prompt 01, then issue an honest `READY_FOR_PROMPT_02` decision. This is not Prompt 02 itself.  
**Safety:** No on-device partition writes, reboots, TWRP flashes, camera streaming, mutable DT operations, or changes to working Nuxel. Keep all raw device images, device identifiers and signing keys on a **private host path outside Git**.

## 0. Governing contract, prior results, and facts not to assume

Read verbatim and obey:

- `pwn-cam/00_MASTER_CONTRACT.md`
- `pwn-cam/01_PROMPT_00.md`
- `pwn-cam/01_PROMPT_00_7.md`
- `pwn-cam/01_PROMPT_00_8.md`
- `pwn-cam/02_PROMPT_01.md`
- `pwn-cam/03_PROMPT_02.md` (read for prerequisites only; do not begin implementation until released)
- `tools/s10plus/{camera-dt-gate.py,camera-dt-diff.py,camera-release-gate.py,verify-boot-image.py,nuxel-camera-release-gate.sh,camera-00-artifact-manifest.NOT_SIGNED.template.json}`
- `tools/s10plus/tests/*`, `boot/s10plus/tests/test-boot-image-gates.sh`
- All **private** prior `reports/camera-00*`, `reports/camera-01*`, `reports/camera-02-source-readiness.md`, prior partition maps, and TWRP recovery documentation, wherever they actually reside.

The owner's last *reported* result, **not independent proof for this run**, is:

```
current Nuxel reachable/healthy: reported YES
kernel: 4.14.253-gf7194c1d15ed-dirty
SM-G975F / beyond2lte / BEYOND2LTE EUR OPEN 26
board revision: 26
selected Android DTBO entry: 9
live merged FDT SHA-256:
761df64ac4417f6dd5bbb468eeb6dc2305cbf45f8541d3639d5a50ca2ffc7cad
51/51 synthetic camera offline checks: reported PASS
historical A5/A25 test script: SKIP-PREREQ, exit 3 (not PASS)
real signed golden no-op: BLOCKED
complete private partition backups: unavailable on the previous host
owner signing key and approved fingerprint: unavailable
TWRP exact restoration path: not independently reverified
previous on-device writes/reboots: ZERO
```

**The attached public repository ZIP contains no `current-boot.img`, `current-dtb.img`, `current-dtbo.img`, `active-merged.fdt`, owner key or signed manifest.** Do not claim these are there. Do not substitute A5/A25 images, a dummy manifest, an earlier repo ZIP, synthetic images, or `/PRIVATE` (which on macOS is a system location, NOT the intended private artifact directory).

**Git provenance:** The owner reported recent branch `cs/cam` commit `e1fa2d00`. Independently check `git rev-parse HEAD`, `git status`, `git log`, remote, and content hashes. A ZIP alone does not prove HEAD. Never discard uncommitted changes or overwrite private reports. No public push of this stage's private evidence.

## 1. Privately establish a real Mac-host recovery-evidence directory

On the OWNER'S MAC, select an existing protected private volume or **new host-only directory** outside the Nuxel checkout, outside public cloud synchronization, and outside the repository's ignored `reports/` directory. Suggested illustration only: `$HOME/Nuxel-private-camera-recovery/<timestamp>`; create the directory only after confirming it will stay private. Use `umask 077`, restrictive ownership and permissions, and verify available disk space (more than all four full partition images plus spare room). Do not use `/PRIVATE` as a fake path or store keys in source trees.

1. Confirm fresh reachable target and *trusted SSH host identity*. Do not bypass SSH host-key checking.
2. Confirm no camera/vendor `STREAMON`, no speculative GPIO/regulator/rail writes, no boot or partition changes since the last baseline.
3. Read and privately record current `/proc/cmdline`, `uname -a`, `/proc/version`, active FDT, and board model. Re-check the **full** FDT SHA and report any changes from the reported hash. A new capture must be treated as the new authoritative truth only after consistency checks, not automatically declared PASS.
4. Discover partitions from **actual current device evidence**, not `/dev/block/by-name` (which may not exist on native Fedora) and **never from guessed `/dev/sdaN` numbers**. Use read-only `lsblk -b -o NAME,TYPE,SIZE,PARTLABEL,PARTUUID,MOUNTPOINTS`, `/sys/class/block/*/uevent`, GPT/partition metadata, TWRP fstab and any trustworthy historical map. Cross-check sizes and labels independently. Note Fedora root reportedly uses `/dev/sda31`; this is only a warning not to assume a number. BOOT, DTB, DTBO, RECOVERY must be uniquely resolved or BLOCK.
5. Require a written mapping table: semantic partition role, actual block device, partition name/GPT label/UUID evidence, capacity bytes, independent corroboration, and which files prove that mapping. Reject duplicates, rootfs/system/data/EFS/modem/persist, or ambiguous mappings.

**Optional provided capture helper:** `scripts/camera_readback_host.py` (from the companion kit). It performs **READ-ONLY** SSH copies only after explicit confirmed device-path arguments and `--confirm-mapping`. It deliberately does not discover partitions or decide if TWRP works. Review its source and `python3 ... --help` before use. Use only if its assumptions hold on the actual device. If not, build an equivalent evidence-driven, read-only stream and document every step. Never run any command with an `of=/dev/...` destination on Nuxel.

Example **PLACEHOLDERS ONLY** (not usable until discovered and verified):

```bash
python3 scripts/camera_readback_host.py \
  --device root@VERIFIED_NUXEL_HOST \
  --private-dir "$HOME/Nuxel-private-camera-recovery/NEW_TIMESTAMP" \
  --boot /dev/VERIFIED_BOOT_PARTITION \
  --dtb /dev/VERIFIED_DTB_PARTITION \
  --dtbo /dev/VERIFIED_DTBO_PARTITION \
  --recovery /dev/VERIFIED_RECOVERY_PARTITION \
  --confirm-mapping
```

This example WILL NOT pass the helper's device-path validation until placeholders are replaced. Do not silently choose partition numbers to make it run.

## 2. Capture, protect and independently verify the actual currently installed images

From the normally booted Nuxel, capture off-device, using **reads only**:

- Exact **full partition** BOOT image → host `current-boot.img`
- Exact **full partition** DTB image → host `current-dtb.img` (only if physically present; report layout discrepancy otherwise)
- Exact **full partition** DTBO image → host `current-dtbo.img`
- Exact **full partition** RECOVERY image → host `current-recovery.img`
- **Raw active merged FDT** from `/sys/firmware/fdt` → host `active-merged.fdt` (or independently explained equivalent if that interface is absent)
- Raw partition metadata, capacities, model, kernel, `/proc/cmdline`, selected board/revision/DTBO-index, and exact recovery target evidence.

**Required integrity rules:**

1. For each partition, compare host file length with independently measured raw partition capacity. If readback is shorter or larger, FAIL; do not pad, truncate or infer sizes.
2. Compute host SHA-256 and independent device-side source hashes **before and after the transfer**. Require equality, note exact capture UTC and device uptime; if the source changed, recapture/diagnose rather than sign.
3. Recompute all host SHA-256 values with a second independent host invocation and compare; optionally make a separate second host copy and compare if feasible. Record readback evidence in private files.
4. Protect from accidental overwrites: never reuse a filled capture directory, never overwrite a golden image, never modify a golden image in place. Use copies for negative testing.
5. Independently verify the selected DTBO entry against actual table metadata: board revision `26` and selected entry `9` **only if live evidence still confirms them**. Do not infer selected index solely from DTS naming, a report, or a model string.
6. Prove which physical DT source the bootloader selected, including **separate DTB/DTBO** vs appended BOOT DTBs; correlate boot-image header, partition data, runtime FDT, bootloader/command-line evidence, known hardware topology, and any machine-specific merge/fixups. Explain runtime differences in a machine-readable report; if merge provenance is insufficient, `bootloader_dt_source_verified` remains `false`.
7. Review the existing stock flash/torch GPIO dual-reference in the real FDT: only unchanged, hash-pinned **exact** golden owner/property tuples may be grandfathered. New conflicts, changed GPIO flags, or unrelated property changes must fail.

When this phase passes, store a privately documented, separately reviewable statement that original recovery images match the running phone. A matching file hash alone does not prove recovery bootability.

## 3. Recovery-readiness evidence — do not invent TWRP confidence

Produce a recovery document **specific to the mapped Nuxel partitions and exact image sizes**. Prove:

- Owner can access the known TWRP/Download Mode route for this S10+ (credible prior successful session, current verified device documentation, or supervised owner confirmation; label the strength/date of evidence).
- Host can detect and communicate with TWRP via the expected trusted ADB/USB path when actually in recovery, and knows the correct, previously proven restore commands and targets. No use of fastboot on this device.
- `current-boot.img`, DTB/DTBO where applicable, and RECOVERY can be located on the recovery host with known-good, independently rechecked hashes; the restore procedure names the exact image/partition mapping, safety prechecks and post-restore Nuxel boot checks.
- Restoration is **documented only** in this stage; do not run restore or flash while the phone is healthy.

**If the current TWRP route cannot be adequately established without actually rebooting**, do NOT claim `rollback_ready=true`. Present the owner with a **separate, explicitly permissioned, read-only TWRP access check** for a future session after verified backups. It must not be silently executed within this no-reboot stage. Mark `ROLLBACK_READY=UNKNOWN` and STOP the real release gate pending that check.

## 4. Owner-approved signing identity: stop for owner action if not yet authorized

The owner has **NOT yet authorized a particular camera trust anchor** simply by requesting a prompt. Do not reuse the unrelated `penguru-service` Ed25519 key, choose a random `.pem`, upload keys, or fabricate an approval.

Two permitted options:

**Option A — owner supplies a pre-existing dedicated trust anchor:** owner independently provides a public verification key/fingerprint and indicates which local protected private key is authorized for **Nuxel camera manifest + release receipts**. Verify that the private/public pair match and that the key is restricted to this workflow. Never expose private material.

**Option B — owner expressly approves creating a NEW dedicated local trust anchor:** ask for explicit approval; then the **owner** may run the supplied `scripts/owner_init_camera_trust.sh` on the Mac with `--owner-approves-camera-trust` and a new private directory. The script generates an EC P-256 signing key locally with OpenSSL, stores it privately, exports only its public verification key and displays its SHA-256 fingerprint. It deliberately cannot run without explicit authorization. The owner must independently record/confirm the fingerprint and storage location; do not call a merely newly created public key "independently trusted" until that step is documented. Private keys remain on the owner host. This script makes an unencrypted local key with restrictive permissions; use a protected/encrypted host volume and owner-controlled backup/permissions.

Owner-only example, **ONLY AFTER EXPRESS APPROVAL**:

```bash
bash scripts/owner_init_camera_trust.sh \
  --owner-approves-camera-trust \
  "$HOME/Nuxel-private-camera-recovery/owner-trust-NEW"
```

Never ask the owner to paste the private key or private identifiers into ChatGPT/DeepSeek. Do not self-generate a purported owner-approved identity in an unattended agent run.

## 5. Produce and owner-sign the exact real Prompt 00 manifest

Use the exact schema in `tools/s10plus/camera-00-artifact-manifest.NOT_SIGNED.template.json` **as code expects it**, without weakening required fields.

Populate, after independent verification:

- `schema: nuxel.camera.prompt00/v1`; `capture_utc` timezone-aware, **less than 72 hours old at release invocation**.
- `device.model=SM-G975F`, `codename=beyond2lte`, `status=NUXEL_HEALTHY`; verified numeric `board_revision`, numeric `dtbo_index`, correct `dt_layout`, `appended_dtb_index` (`null` **only** for proven separate-DT layout).
- `proof.off_device`, `proof.rollback_ready`, `proof.selected_overlay_verified`, `proof.active_tree_matches_onflash`, `proof.bootloader_dt_source_verified` must each describe **genuinely proven facts**, not hoped-for ones.
- `proof.{boot,dtb,dtbo}_readback_sha256` match independent source-side readback digests.
- `partitions.{boot,dtb,dtbo}_bytes` are actual partition capacities.
- `artifacts` include exact private absolute `path`, real full 64-digit `sha256`, and `size_bytes` for `boot`, `dtb`, `dtbo`, `merged_fdt`, `recovery`, `selected_board_evidence`, and `rollback_plan`. The additional evidence files must be real verified files, not mere assertions.

Run the unsigned manifest through an **independent content audit** before signing: verify every byte path, hash, size, identity and physical proof, and ensure originals remain immutable. Explicitly confirm freshness. Any unsupported TRUE blocks signature.

The **owner** reviews the entire final manifest and signs the exact file using their approved local key. You may provide this owner-only command (do not impersonate their consent):

```bash
bash scripts/owner_sign_camera_manifest.sh \
  --owner-reviewed-manifest \
  /ACTUAL_PRIVATE_DIR/camera-00-artifact-manifest.json \
  /ACTUAL_OWNER_APPROVED_DIR/owner-camera-manifest-and-receipt-signing.key.pem \
  /ACTUAL_OWNER_APPROVED_DIR/owner-camera-manifest-verification.pub.pem
```

This creates a **detached signature** and immediately verifies it against the owner's public key. Re-verify independently with `openssl dgst -sha256 -verify` and compare recorded public-key fingerprint. Never sign the placeholder template. A signature establishes approval for those bytes, not a hardware proof by itself.

## 6. Qualify Prompt 01 against **real data**, then run real signed golden no-op

First reproduce the offline test statuses without hiding skips:

```bash
bash tools/s10plus/tests/test-camera-dt-gate.sh
bash boot/s10plus/tests/test-boot-image-gates.sh
```

- Expect the synthetic tests to pass completely (previously reported 51/51).
- `test-boot-image-gates.sh` may exit **3** because A5/A25 historical images and A4 cpio are not in this repo; record **HISTORICAL SKIP-PREREQ**, **not PASS**, and never synthesize hardware-proven historical images. Verify all *mandatory* synthetic checks separately. Do not rewrite the script to return 0 merely to hide missing fixtures.

Then, against the newly verified private current baseline:

1. Validate actual BOOT image container, exact kernel/ramdisk/DT source and partition capacity.
2. Parse exact DTB/DTBO, selected entry, active merged FDT, static camera graph, `#address-cells`, endpoints, I2C collisions, GPIO, clocks/PHY/rails and FIMC/native CSIS exclusivity. Do not run any camera STREAMON.
3. Validate **real** golden no-change graph and semantic diff: exact original BOOT, DTB, DTBO and active merged FDT as candidate; expected zero semantic changes. No modified candidate permitted in Prompt 01.
4. Use the release wrapper's **actual** required options, with owner-approved paths. For an unchanged golden no-op, no candidate approval or change allowlist should be necessary:

```bash
bash tools/s10plus/nuxel-camera-release-gate.sh \
  --manifest /ACTUAL_PRIVATE_DIR/camera-00-artifact-manifest.json \
  --signature /ACTUAL_PRIVATE_DIR/camera-00-artifact-manifest.json.sig \
  --trusted-pubkey /ACTUAL_OWNER_APPROVED_DIR/owner-camera-manifest-verification.pub.pem \
  --candidate-boot /ACTUAL_PRIVATE_DIR/current-boot.img \
  --candidate-dtb /ACTUAL_PRIVATE_DIR/current-dtb.img \
  --candidate-dtbo /ACTUAL_PRIVATE_DIR/current-dtbo.img \
  --candidate-merged /ACTUAL_PRIVATE_DIR/active-merged.fdt \
  --receipt-dir /ACTUAL_PRIVATE_DIR/camera-00_9-golden-noop-receipts \
  --receipt-signing-key /ACTUAL_OWNER_APPROVED_DIR/owner-camera-manifest-and-receipt-signing.key.pem
```

5. Require exit code 0 **and** receipt `result=PASS_OFFLINE_ONLY` with the five mandatory PASS gates exactly: `BOOT_CONTAINER_PASS`, `CAMERA_DT_GRAPH_PASS`, `ACTIVE_BOARD_MATCH`, `NO_UNRELATED_DT_DELTA`, `ROLLBACK_READY`. Independently verify the receipt detached signature against the owner public key. **This is an OFFLINE, exact-baseline self-comparison. It is NOT a new physical BOOT success or flash approval.**
6. Use immutable **copies** of the candidate inputs and negative fixtures to prove that absent/wrong signature, key fingerprint mismatch, wrong board rev, wrong selected overlay, stale evidence, wrong DT layout, missing source proof, modified stock flash GPIO owner/flags, broken endpoint, unknown PHY/clock, conflicting I2C, simultaneous FIMC/native CSIS, unexpected NFC/SSP/display property changes, oversized partitions, wrong backup hashes, missing rollback plan, and unexpected BOOT payload all fail nonzero. Preserve actual expected failure results, input SHA/fixture provenance and tool exit codes in private logs.
7. If the real unchanged golden no-op fails, diagnose using the *actual* FDT/member/partition evidence; fix host-only defects **without generic allowlists, ignore flags, removed checks or spoofed proofs**. Add positive and negative regression cases and rerun **all** mandatory tests. Do not introduce a camera DT experiment in this stage.
8. If any required signature, backup, recovery, graph, board-merge, historical prerequisite marked mandatory by current tooling or negative case remains absent, declare the exact blocker and STOP. Do not declare a partial or synthetic PASS equivalent to live Prompt 00/01 PASS.

## 7. Only after passing: prepare Prompt 02 handoff

On the host, locate the actual full exact kernel source `Linux4` or equivalent, expected commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0`, all Nuxel patches, actual live `.config`, toolchain, and `drivers/s10-camera-v4l2/{exynos9820-csis.c,s5k-cis.c,ak7374.c}` if available elsewhere. The uploaded public ZIP did **not** include these. Verify upstream camera source at recorded `d8135b2465b3` if it still exists, pin SHA and license. Source prerequisites may still block Prompt 02 implementation even after 00/01 pass.

Deliver an offline, sanitized (no proprietary firmware/private evidence/keys) source handoff with build commands and provenance. **Do not port/probe/flash/reboot in Prompt 00_9.** Prompt 02 itself only authorizes offline 4.14 source/build work; all BOOT flash authority remains deferred to later gates.

## 8. Required delivery and honesty ledger

Write private reports, not public dumps:

- `reports/camera-00_9-device-partition-map.md`
- `reports/camera-00_9-recovery-and-trust.md`
- `reports/camera-00_9-real-golden-noop.md`
- `reports/camera-01-real-regression-matrix.md`
- `reports/camera-02-source-readiness.md`
- Private backup SHA manifest, current signed Prompt 00 artifact manifest + detached signature, owner-approved **public** fingerprint, and signed release receipt **only if actually achieved**.

The readable reports can be kept gitignored locally; never put private raw images, identifiers, keys, tokenized SSH logs or recovery secrets into GitHub or this chat. Preserve raw failure logs in the owner's protected private folder. Produce a redacted progress summary separately.

State **each** field as `PASS/FAIL/BLOCKED/UNKNOWN/SKIP` with supporting evidence, not just prose:

```
DEVICE_REACHED=
CURRENT_NUXEL_HEALTHY=
LIVE_FDT_HASH_MATCH=
PARTITION_IDENTITY_INDEPENDENTLY_VERIFIED=
PARTITION_BACKUPS_MATCH=
BOARD_REV=
DTBO_INDEX=
BOOT_DT_LAYOUT=
BOOTLOADER_DT_SOURCE_PROOF=
OWNER_SIGNING_TRUST=
MANIFEST_SIGNED_AND_VERIFIED=
ROLLBACK_READY=
CAMERA_DT_GRAPH_PASS=
NO_UNRELATED_DT_DELTA=
REAL_GOLDEN_NOOP=
NEGATIVE_GATE_TESTS=
HISTORICAL_A5_A25_SUITE=
DEVICE_PARTITION_WRITES=0
DEVICE_REBOOTS=0
PROMPT00_PASS=
PROMPT01_PASS=
PROMPT02_SOURCE_READY=
READY_FOR_PROMPT_02=
```

**Only** set `PROMPT00_PASS=YES`, `PROMPT01_PASS=YES`, and `READY_FOR_PROMPT_02=YES` if all their **actual, owner-approved, live-proven required exit gates** are PASS. A synthetic green suite or a correctly signed false assertion is not enough. If blocked, give the owner **one exact minimal intervention** (e.g., sign reviewed manifest, authorize dedicated key, or approve a separate controlled recovery-access verification). Then stop without speculative flash.

**No device partition writes, no reboot, no TWRP entry, no kernel/DT changes in this stage.**
