# PROMPT 00_11 — OWNER CAMERA TRUST ANCHOR + CLOSE THE REAL 00/01 GATES

**For:** DeepSeek V4 Pro Thinking acting on the owner's **Mac** and the existing Nuxel camera repository.

**Mission:** Obtain an **authentic owner-authorized, camera-specific** signing identity, then actually close the remaining **Prompt 00 / Prompt 01** evidence, manifest, recovery and signed golden no-op requirements. Continue into the independently supplied Prompt 02/03 **offline** work only if the genuine prerequisites pass; do not substitute a synthetic pass for the real result. The objective is evidence-backed readiness for Prompt 04, **not permission to flash**.

## 0. Nonnegotiable contract and entry facts

1. Read and obey `pwn-cam/00_MASTER_CONTRACT.md`, `pwn-cam/01_PROMPT_00.md`, `pwn-cam/02_PROMPT_01_IMPLEMENTATION_STATUS.md` if present, the latest `01_PROMPT_00_9.md`, `01_PROMPT_00_10_OPTION_A_AND_02_03_HANDOFF.md`, and both subsequent `03_PROMPT_02(2).md` and `04_PROMPT_03(1).md` if supplied. Inspect **current** source and script `--help`/contents; do not assume commands from stale notes.
2. Model is Samsung S10+ **SM-G975F / beyond2lte / Exynos9820**, Nuxel native Fedora, Linux **4.14.253**, A-only BOOT. Previously observed board revision 26 and selected DTBO entry 9 are **hypotheses to re-prove**, not constants that authorize a device write. Historical kernel string `4.14.253-gf7194c1d15ed-dirty` and active merged FDT hash `761df64ac4417f6dd5bbb468eeb6dc2305cbf45f8541d3639d5a50ca2ffc7cad` are **cross-check hints**, not substitutes for a current capture.
3. **ZERO device writes, ZERO device reboots, ZERO TWRP sessions, ZERO BOOT/DTB/DTBO/RECOVERY flashes, ZERO camera STREAMON** in this mission. Host-side private backup files, reports, signature creation and source builds are allowed. Do not accidentally mount/write phone partitions. No fastboot, no unguarded `dd` to a device, no permissive DT validator changes, and no invented board topology.
4. Keep secret keys, private hardware readbacks, serials, SSH credentials and sensitive output **outside Git, release ZIPs, cloud-sync folders, chat transcripts and public reports**. Never display `*.key.pem` contents or transmit private key bytes. Strict SSH host identity checking stays enabled.
5. This prompt is **not** the owner's signing confirmation. The owner must explicitly approve key choice/creation and the complete manifest using the existing scripts' interactive `/dev/tty` prompts. Do not answer those prompts yourself, pipe responses, or automate around them.

## 1. First determine whether Option A is genuinely possible

Inspect only **owner-designated** private key locations (not all the Mac's secrets). Identify whether the owner already has a **dedicated, pre-existing Nuxel camera signing private/public PEM pair** with independent provenance and an owner-verified public DER SHA-256 fingerprint. The existing PenGuru service key **must not** be reused, renamed or relabelled. An unrecognized `.pem` is not camera trust.

- If the authentic pair exists, present key paths, nonsecret public fingerprint, purpose, and provenance for owner review. On the owner's Mac run the repository's **existing** `scripts/owner_register_existing_camera_trust.sh` with the exact flags below, and let **the owner personally** type its interactive token:

  ```bash
  bash scripts/owner_register_existing_camera_trust.sh \
    --existing-private-key '/ABS/EXISTING_CAMERA_PRIVATE_KEY.pem' \
    --existing-public-key '/ABS/EXISTING_CAMERA_PUBLIC_KEY.pem' \
    --expected-public-sha256 'OWNER_INDEPENDENTLY_VERIFIED_64_HEX' \
    --new-private-record-dir '/ABS/NEW_PRIVATE_CAMERA_TRUST_RECORD_DIR' \
    --owner-authorizes-existing-camera-key
  ```

  The record directory must be **new**, outside the Git checkout. Check its existing signing challenge and resulting `trust-registration.json`; do not claim this creates a new key.

- If no such key exists, **Option A is impossible**. Inform the owner succinctly, then offer the proper **Option B: locally create a new dedicated camera trust identity**. Request their express approval of that change of path; do not conflate this with previously selecting Option A. If owner approves, have them execute on **their Mac's interactive terminal**, not on Nuxel:

  ```bash
  mkdir -p "$HOME/Nuxel-private-camera-recovery"
  chmod 700 "$HOME/Nuxel-private-camera-recovery"
  bash scripts/owner_init_camera_trust.sh \
    --owner-approves-camera-trust \
    "$HOME/Nuxel-private-camera-recovery/owner-trust-NEW"
  ```

  **Preflight:** ensure the `owner-trust-NEW` destination does **not** already exist and is outside Git/cloud sync. If that name already exists, choose a **different new directory**, do not delete/overwrite it. The owner—not you—types `CREATE_CAMERA_TRUST` when the script asks. The script creates a local `prime256v1`/P-256 PEM signing key and matching public PEM. It creates an **unencrypted private key**, so explicitly check that private storage is local, access-restricted (`0700` parent, `0600` key), and protected by the owner's Mac disk encryption; otherwise BLOCK and ask for a protected key arrangement. Do not paste or upload any private material.

- Independently verify local public/private correspondence using a random temporary challenge signed locally and verified using `openssl dgst -sha256 -verify`; retain only nonsecret pass/fail and public DER fingerprint. Record the **public** fingerprint independently with the owner, then require their affirmative confirmation that this exact public key is now the Nuxel camera trust anchor, **scoped only to camera manifest and release receipts**. Never equate key creation or challenge verification with real hardware evidence.

**Mandatory result from this phase:** `CAMERA_TRUST_OWNER_APPROVED=YES`, `PRIVATE_KEY_PRESENT_ON_OWNER_MAC=YES`, `PUBLIC_KEY_SHA256_VERIFIED=YES`, and `PRIVATE_KEY_EXPORTED_OR_LOGGED=NO`; otherwise `BLOCKED`.

## 2. Reconstruct genuine, current off-device device evidence

Leave Nuxel **normally booted**. Prove trusted SSH host identity and model. Recheck `/proc/cmdline`, `/sys/firmware/fdt`, kernel, root filesystem and actual UFS/GPT mapping. Do not assume `/dev/block/by-name` exists or infer BOOT from Fedora's `/dev/sda31` root partition. Use read-only inspection of `lsblk -b -o NAME,TYPE,SIZE,PARTLABEL,PARTUUID,MOUNTPOINTS`, `blkid`, `/sys/class/block`, GPT metadata and relevant historical recovery documentation. Establish the *real* partition node for each of BOOT, DTB, DTBO and RECOVERY, or document why an item is genuinely absent/embedded. Respect the actual current layout; do not invent paths to satisfy a schema.

Use `scripts/camera_readback_host.py` only after independently reviewing its source, confirming all four **actual** block device paths, and acknowledging its `--confirm-mapping` flag **after** verification. It requires a **new empty host-private directory** and uses strict SSH. Argument shape:

```bash
python3 scripts/camera_readback_host.py \
  --device 'root@VERIFIED_DEVICE_HOST' \
  --private-dir '/ABS/NEW_EMPTY_PRIVATE_CAPTURE_DIR' \
  --boot '/dev/VERIFIED_BOOT_PARTITION' \
  --dtb '/dev/VERIFIED_DTB_PARTITION' \
  --dtbo '/dev/VERIFIED_DTBO_PARTITION' \
  --recovery '/dev/VERIFIED_RECOVERY_PARTITION' \
  --confirm-mapping
```

These are **placeholders**: determine their real values first. Capture complete partition bytes and the live `/sys/firmware/fdt`, write SHA-256 manifest, compare device-before/device-after/host-local hashes and partition capacities, and preserve immutable backups. Cross-check selected DTBO entry, board revision, actual DT_TABLE header/entries, source/selection chain and merged FDT against physical readbacks. Keep every image and log private. **Do not mark `active_tree_matches_onflash=true` merely because the active tree hash matches another copy of itself**; show independently supported relationship to source partitions and the selected bootloader overlay, or report UNKNOWN.

If the previous private captures are genuinely present elsewhere, verify their exact host paths, age, device provenance, hashes and completeness before deciding whether fresh readbacks are still required. **Do not claim they exist merely because an earlier agent's report said they did.** The release gate enforces a capture timestamp not older than **72 hours**; recapture if stale.

## 3. Recovery truth before signing

Locate the known-good current BOOT backup and current recovery image on the Mac. Verify that each matches the actual present partition and record partition map, sizes, and exact restoration interface expected by `scripts/nuxel-adb-flash-pack`. Reconcile the A-only device and TWRP ADB availability with logs/evidence. Produce a detailed rollback plan including **verified** correct target and host backup hash, safe command syntax, detection of failed candidate boot, healthy-baseline checks, and stop conditions.

An untested description of a restore command is **NOT** an end-to-end tested recovery path. If an indispensable TWRP access/recovery test would require rebooting, **STOP and request separate explicit owner approval for that limited check**, rather than silently rebooting. Record `ROLLBACK_READY=UNKNOWN` until its real acceptance criteria are satisfied; do not sign unsupported `true` values.

## 4. Owner-reviewable real Prompt 00 manifest, not a template

Inspect `tools/s10plus/camera-00-artifact-manifest.NOT_SIGNED.template.json` and `tools/s10plus/camera-release-gate.py` in the current repository. Create a **new private** filled manifest, schema `nuxel.camera.prompt00/v1`, from verified evidence only. It requires, among other things:

- Device `model=SM-G975F`, `codename=beyond2lte`, `status=NUXEL_HEALTHY`, measured `board_revision`, measured `dtbo_index`, and explicitly verified `dt_layout=separate-dtb-dtbo` (or actual proven alternative). In separate-DT mode `appended_dtb_index=null` and `proof.bootloader_dt_source_verified=true` **only when truly supported**.
- Proof flags `off_device`, `rollback_ready`, `selected_overlay_verified`, `active_tree_matches_onflash`, each **true only when proven**. No auto-approval or inference from timestamps.
- Verified `boot_readback_sha256`, `dtb_readback_sha256`, `dtbo_readback_sha256`, measured partition byte capacities, and SHA-256 + size + private path for each required `boot`, `dtb`, `dtbo`, `merged_fdt`, `recovery`, `selected_board_evidence`, `rollback_plan` artifact. The gate checks that these files exist and exactly match the signed values.
- `capture_utc` matching the fresh capture (within the release gate's 72-hour freshness window).

Before signing: present the complete human-readable findings and manifest SHA-256 **locally to the owner** (avoid dumping sensitive identifiers into public chat), flag any UNKNOWN, and require their independent review. If any mandatory assertion remains unproven, do not change it to `true` and **do not sign**.

Only after approval, run the existing script from an owner-controlled interactive terminal with the already reviewed **private** manifest, local private key and matching public key:

```bash
bash scripts/owner_sign_camera_manifest.sh \
  --owner-reviewed-manifest \
  '/ABS/PRIVATE/camera-prompt00-manifest.json' \
  '/ABS/PRIVATE/owner-camera-manifest-and-receipt-signing.key.pem' \
  '/ABS/PRIVATE/owner-camera-manifest-verification.pub.pem'
```

For **Option A**, use the **actual previously authorized existing private key path** and corresponding existing/matching public path, not necessarily the example Option B filenames above. The owner personally types `SIGN_CAMERA_MANIFEST`; verify detached `.sig` with `openssl dgst -sha256 -verify` and confirm the exact local trust fingerprint again.

## 5. Real signed golden no-op: exact same bytes

Run the actual wrapper `tools/s10plus/nuxel-camera-release-gate.sh` with the real files, **not** the old synthetic fixture. This is an offline check on the Mac; no phone writes.

```bash
bash tools/s10plus/nuxel-camera-release-gate.sh \
  --manifest '/ABS/PRIVATE/camera-prompt00-manifest.json' \
  --signature '/ABS/PRIVATE/camera-prompt00-manifest.json.sig' \
  --trusted-pubkey '/ABS/PRIVATE/owner-camera-manifest-verification.pub.pem' \
  --candidate-boot '/ABS/PRIVATE/CAPTURE/current-boot.img' \
  --candidate-dtb '/ABS/PRIVATE/CAPTURE/current-dtb.img' \
  --candidate-dtbo '/ABS/PRIVATE/CAPTURE/current-dtbo.img' \
  --candidate-merged '/ABS/PRIVATE/CAPTURE/active-merged.fdt' \
  --receipt-dir '/ABS/PRIVATE/NEW_RECEIPT_DIRECTORY' \
  --receipt-signing-key '/ABS/PRIVATE/owner-camera-manifest-and-receipt-signing.key.pem'
```

For **Option A**, supply its real approved key path. Use a **new** receipt directory, keep reports and private artifacts off Git. Confirm nonzero exit on any missing/unsigned/mismatched asset. For a successful real no-op, require actual `result=PASS_OFFLINE_ONLY`, all five named steps (`BOOT_CONTAINER_PASS`, `CAMERA_DT_GRAPH_PASS`, `ACTIVE_BOARD_MATCH`, `NO_UNRELATED_DT_DELTA`, `ROLLBACK_READY`) individually `PASS`, plus a receipt `.sig` that independently verifies against the same trusted public key. Also prove the live merged tree matches the authorized current capture. The result is an offline safety acceptance **not** a device camera test or permission to flash.

Run the existing `tools/s10plus/tests/test-camera-dt-gate.sh` and `boot/s10plus/tests/test-boot-image-gates.sh` as appropriate. Synthetic tests remain useful but **cannot replace** real evidence. Historical A5/A25 `SKIP-PREREQ (exit 3)` must be labelled SKIP, never PASS. No gate bypass or exception broadening to manufacture a green result.

## 6. Prompt 02/03 readiness: continue only after genuine 00/01 PASS

If and only if 00 and 01 physically grounded exit gates PASS, move into `03_PROMPT_02(2).md` and `04_PROMPT_03(1).md` under their exact scopes. Pinned public reference `butztill/s10-linux@d8135b2465b3`; exact Nuxel base `Linux4/android_kernel_samsung_exynos9820@f7194c1d15eded1c2a1a4dc63825b26103435cc0` plus Nuxel patches. Confirm source commit/licensing and fetch if missing; do not pretend the ZIP has complete kernel/driver source. Port the real 4.14 APIs and V4L2 drivers, Kbuild and config, compile complete kernel + modules with modpost, preserve non-camera config, produce hashes/build artifacts. In Prompt 03 build real beyond2lte rear-main-only DT topology from the real active FDT and board source, avoid 973F-to-975F guessing and simultaneous vendor/native binding, compile dtbs, and pass all graph/diff checks. **No image flashing, TWRP, reboot or camera streaming**; do not call these prompts PASS unless their exit gates really pass. Separate Stage 04 authorization will be needed for an eventual guarded BOOT-only experiment.

You may perform safe offline source research in parallel while waiting for the owner's key confirmation, but **must not relabel this as Prompt 02 or Prompt 03 PASS**.

## 7. Required concrete deliverables and final decision

Write local private reports `reports/camera-00_11-owner-trust-and-readbacks.md`, `reports/camera-01-real-golden-noop.md`, `reports/camera-02-source-and-build-status.md`, `reports/camera-03-board-topology-status.md` (if Git ignores `reports`, keep them local; never force-add private data). Include:

- owner-choice **A-existing** or **B-new**, local trust reference, nonsecret public DER SHA-256 fingerprint, owner interactive approval result, keypair proof result;
- real partition-to-block mapping with independent source evidence, complete backup hashes and sizes, active merged FDT/DTBO proof, capture freshness, rollback confidence;
- signed Prompt00 manifest SHA-256 and signature verification, five real golden-noop gate steps and signed receipt location/hash;
- synthetic test totals and independently marked historical SKIPs;
- 02/03 complete-source/build/DT gates and only honestly achieved statuses, plus exactly one concrete next action if blocked;
- git branch/HEAD and safe code changes, **on-device writes=0; on-device reboots=0**.

Final explicit summary (no optimistic language):

```text
DEVICE_REACHED=YES|NO
CAMERA_TRUST_OWNER_APPROVED=YES|NO
CAMERA_PUBLIC_FINGERPRINT=...
CURRENT_PARTITION_MAPPING_VERIFIED=YES|NO
PRIVATE_OFF_DEVICE_READBACKS_VERIFIED=YES|NO
RECOVERY_ROLLBACK_READY=YES|NO|UNKNOWN
PROMPT00_SIGNED_MANIFEST_VERIFIED=YES|NO
REAL_GOLDEN_NOOP=PASS_OFFLINE_ONLY|BLOCKED|FAIL
PROMPT00_PASS=YES|NO
PROMPT01_PASS=YES|NO
PROMPT02_FULL_KERNEL_AND_CAMERA_BUILD_PASS=YES|NO
PROMPT03_REAL_SELECTED_S10PLUS_DT_PASS=YES|NO
READY_FOR_PROMPT04=YES|NO
DEVICE_WRITES=0
DEVICE_REBOOTS=0
```

**STOP rules:** If the owner does not authorize a legitimate camera key, if the partition map/backups are incomplete, if TWRP rollback remains unproven, or if the signed real golden no-op fails, return `BLOCKED` with precise missing evidence rather than inventing success. **Do not weaken the release gate, forge signatures, self-authorize owner actions, or rush into Prompt 04.**
