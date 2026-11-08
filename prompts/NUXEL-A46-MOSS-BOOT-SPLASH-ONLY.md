# 🐧🔥 NUXEL A46 — OPERATION PENGUIN FIRST LIGHT
## MOSS-BASED SAMSUNG EARLY BOOT SPLASH — SINGLE-PURPOSE TWRP MISSION

**Executor:** `deepseek-v4-pro-thinking` (or an equally careful agent), on the MacBook with the owner's Samsung Galaxy S10+ attached in **TWRP recovery**.

**Target:** **SM-G975F** / `beyond2lte` / Samsung Exynos 9820, running the existing Fedora ARM64 Nuxel installation.

**Owner-provided source:** `MOSS-main(2).zip` — *My Own Splash Screen* (MOSS, by sofikuw). Verify archive available; if missing, stop and request it; do not install any Magisk package.

**Exact artwork:** `./assets/nuxel-boot-screen.jpg` in the owner's **current** Nuxel working checkout.

**SOLE OBJECTIVE:** Replace the *earliest replaceable Samsung Galaxy S10+ boot-logo artwork* with the exact Nuxel image, and **only if independently proven safe** optionally replace the *cosmetic unlocked-bootloader-warning artwork* in the same supported splash archive. Reboot into **the existing Nuxel OS** without changing its installation.

**ABSOLUTELY OUT OF SCOPE:** A45 keyboard, on-screen keyboard, focus, lockscreen, `nuxel-lockscreen.jpg`, `nuxel-lockhead.png`, screen timeout, Home, systemd graphical services, Wi-Fi, audio, boot animation inside Linux, kernel, rootfs, recovery image, bootloader binaries, security state, release/version bump and GitHub PRs. The A45 agent may be working concurrently. **Never change its files or restart its services.**

**EXECUTION MODEL:** Read-only discovery → off-device backups → exact-device analysis → offline splash build → independent validation → **ONE-TIME CONDITIONAL OWNER-AUTHORIZED FLASH ONLY AFTER ALL SAFETY GATES PASS** → single controlled TWRP write → whole-partition readback → reboot → observe real boot → rollback if needed.

---

## PHASE 0 — DEFINE WHICH SCREEN YOU ARE CHANGING

Identify the powered-off-to-Nuxel boot sequence in order:

1. Samsung early boot splash / “Samsung Galaxy S10+” image shown **before Linux starts**.
2. Possible unlocked-bootloader security-warning stage.
3. Nuxel Linux userspace startup/animation.
4. Nuxel graphical lockscreen (currently being worked on separately under A45).

**Change only (1).** For (2), investigate an optional *artwork-only* replacement, and seek separate explicit consent if a different partition/resource must be changed. **Do not disable, bypass or alter bootloader security enforcement, verification, Knox, eFuses, lock state, signatures, or warning timing.** A cosmetic image replacement cannot truthfully be called “disabling the warning.”

No requirement here calls for flashing boot.img, rootfs, system, vendor, userdata or a complete Nuxel image.

A normal userspace JPG change does **not** affect the Samsung image shown before the Linux kernel starts. A real earliest-stage splash replacement generally entails a **raw partition write** if that model's bootloader reads a writable splash archive. This is not a whole-OS reflash, but it **is** flashing and requires recovery safeguards.

---

## PHASE 1 — FORENSIC AUDIT OF *ACTUAL* MOSS SOURCE

Unpack and read `MOSS-main(2).zip` fully. Do not execute the installer.

Files confirmed in the provided archive, whose exact behavior you must review yourself:

- `README.md` — proposes a bootloader-visible `up_param` GNU tar container of JPEGs, including `logo.jpg`.
- `customize.sh` — Android/Magisk installer: looks for `up_param/up_param.bin`, checks that `tar -tf` succeeds, discovers a block device called `up_param`, checks size where possible, backs up to `/data/adb/samsung_splash_backup/up_param_original.bin`, then writes the replacement with `dd`.
- `post-fs-data.sh` — Android early-boot hook that **re-applies a raw `up_param` write** when the module boots.
- `service.sh` — backup boot-time path that can perform **another raw `up_param` write**.
- `tools/pack_up_param.sh` — packs `*.jpg` into tar; copying only JPEGs may discard non-JPEG entries, archive metadata, original ordering, or unknown blobs.
- `tools/restore_up_param.sh` — uses Android backup paths and a broad device discovery loop; do not trust it as the sole restoration mechanism.
- `images/logo.jpg`, `images/lpm.jpg`, `images/download.jpg` — sample MOSS artwork, **not** the owner's requested Nuxel artwork.

**Critical conclusions:**

- MOSS is **not** evidence that this exact phone's current firmware matches its format claims; verify using the physical device's partition bytes.
- MOSS is packaged for Android/Magisk (`/system/bin/sh`, `/data/adb`, Android boot hooks). Nuxel is Fedora Linux. **Do not install MOSS as a Magisk module, copy its Android hooks, or run its install script against Nuxel.**
- **Do not enable any repeated/automatic boot-time partition rewrites.** One verified TWRP write is sufficient if the target accepts the modification.
- A successful `tar -tf` or `dd` exit alone is inadequate evidence of a safe image or a successful boot.
- Do not weaken SELinux or other protections simply to make MOSS run.

Use MOSS only as source-level reference to understand Samsung image naming and tar packing; write a **minimal, explicit, dry-run-by-default image preparation/verification workflow** tailored to evidence from this S10+.

Record MOSS ZIP SHA-256 and source code findings. Do not make silent modifications to its source copy.

---

## PHASE 2 — PRE-FLIGHT AND CONCURRENT A45 PROTECTION

1. Confirm repository location, clean/dirty worktree, current branch and actual Nuxel revision. **Do not checkout a different branch in the active A45 agent's working tree**. If source changes are needed, use a **separate Git worktree** or external scratch directory.
2. Verify `./assets/nuxel-boot-screen.jpg` exists in the **current checkout**. It was absent from a previously reviewed v0.6.3-beta ZIP, so its existence must not be assumed. If missing, **STOP and request the exact asset; do not improvise**.
3. Inspect the **actual JPEG visually** and record SHA-256, magic bytes/decoder results, width, height, chroma subsampling, progressive vs. baseline encoding, EXIF orientation, ICC profile/color space, and visible text/artwork. The `.jpg` filename alone does not prove the bytes are JPEG: if the file is mislabeled, STOP and report it rather than blindly copying it to the splash archive. Never substitute MOSS sample logos.
4. Record exact target model and Nuxel boot/recovery status from the owner and from actual device evidence.
5. Verify the MacBook has sufficient free space for **every requested partition backup**, including `userdata` if readable. This can require tens/hundreds of GB. If complete backup is impractical, stop and explain the shortfall; this run must not proceed to flashing with a narrower scope.
6. Confirm A45 is not sharing TWRP/ADB access right now. Ask the owner to explicitly confirm that **the phone is in TWRP and currently available for A46** before any device operation. Do not reboot or disrupt an in-progress A45 live deployment.
7. Use only documented, reversible, target-verified actions. Maintain a durable run log in a separate directory, not Git.

---

## PHASE 3 — VERIFY TWRP, PHONE IDENTITY AND BLOCK DEVICES (READ-ONLY)

In TWRP, identify the connected phone conclusively:

- `adb devices -l` and a working recovery shell; check the correct physical device is selected.
- Available model/build identifiers (`getprop`, `/proc/cmdline`, device-tree nodes where present).
- `SM-G975F`, `beyond2lte` / `universal9820` only. Stop if another model or ambiguous device.
- `/dev/block/by-name`, `/dev/block/bootdevice/by-name`, `/dev/block/platform/*/by-name`, `/proc/partitions`, `/sys/class/block` and partition size data, where present.
- Exact canonical targets for **`up_param` and `param` separately**. Not all devices expose both; never infer equivalence.
- Whether each is a real block device, its size in bytes, mount state, accessibility and current read-only/read-write status.

**NO guesses:** no copying a block-device name from MOSS's generic README, no writing to a random `mmcblk*` device by numerical offset, no assuming that finding the name `up_param` proves the correct archive contents.

If TWRP ADB is unavailable, **STOP** and diagnose read-only USB/recovery connectivity. Do not silently switch to Odin, Heimdall, or rooted Nuxel live writing.

---

## PHASE 4 — OWNER-REQUESTED ALL-PARTITION BACKUP, OFF-DEVICE

Before modifying **any** block device, enumerate *all addressable/readable partitions* on this phone and make an accurate backup inventory. This includes boot, recovery, dtbo, vbmeta (if present), system/vendor, modem/CP, EFS/NV/calibration partitions, splash partitions and userdata, based on the **real device** rather than a canned list.

1. Create a private, time-stamped backup location **on the MacBook** separate from the Git repo and agents' temporary worktrees.
2. Record for each partition: canonical block device (after resolving aliases), byte size, read method, resulting image path, transferred bytes, SHA-256, and command status/failure evidence. Also record partition-table metadata where accessible; never put the inventory or dumps in the public repository.
3. Do **not** blindly copy the whole storage parent device while simultaneously dumping its partitions unless explicitly justified; avoid waste and inconsistent duplicates.
4. Use binary-safe recovery transfer (for example a carefully checked `adb exec-out` stream, if supported), verify **remote command status**, **local file length** and independent hashes. Beware of shell/PTY newline conversion, truncated streams, USB disconnects and `adb` masking remote command failures. A created file or apparent 100% progress alone does not prove a successful block read.
5. Verify exact byte counts and, where feasible, independently hash the source block device and compare with the saved image.
6. Preserve two independently verified copies of small irreplaceable partitions such as EFS/NV and the actual splash target if feasible.
7. Keep EFS/NV, userdata and partition dumps **private and outside GitHub**. Do not expose device identifiers or secrets in public logs.
8. Treat TWRP-encrypted or mounted userdata carefully: a raw image can be inaccessible, inconsistent, or impractically huge. Do not claim encrypted userdata has been logically backed up merely because TWRP reports success.
9. Record partitions not readable as normal blocks, including protected secure storage (eFuses/RPMB), and be precise that a complete raw image may not be possible.
10. Prepare and verify a **target-partition restoration plan** using the Mac-backed original image and the same TWRP connection before a write is authorized.

**Mandatory all-partitions backup gate:** The owner explicitly requests **every readable/addressable partition first**. If any such partition cannot be backed up and verified, **STOP** and report missing coverage. Do not silently narrow the scope. Partition nodes that cannot be read (such as protected RPMB/eFuses) must be listed as inaccessible with exact evidence; do not claim those have backups. In all circumstances, the **original exact target partition must have an independently verified off-device backup and restoration path** or the write is forbidden.

**Backup completeness verification:** Treat symlinks/aliases pointing to the same block node as one partition, but enumerate all aliases. Obtain actual lengths from the kernel block-device interfaces instead of trusting file size of symlinks. Require a nonempty partition inventory, one unique verified file per accessible block partition, accurate byte-count reconciliation and SHA-256 manifest. Take extra independent copies of irreplaceable calibration/identity partitions. Before large partitions, estimate destination disk requirements plus margin; avoid taking the MacBook storage to zero. Backups of encrypted userdata may be raw ciphertext only, not a logical recovery of user files; describe that distinction explicitly.

---

## PHASE 5 — ANALYZE THE ORIGINAL BOOT-LOGO CONTAINER OFFLINE

Operate exclusively on the Mac copy of the original `up_param`/`param` partition:

1. Identify the actual on-device format: tar archive, header, signatures, padding, entries, checksum behavior, and any non-archive trailer/opaque data. Do not rely on generic MOSS descriptions.
2. List **all archive entries**, not merely `*.jpg`; inspect filenames, ordering, type, exact sizes, dimensions, JPEG encodings, orientation and any unknown data.
3. Determine whether `logo.jpg` actually supplies the first Samsung splash on the specific firmware; corroborate by original image preview and archive content. If uncertain, do not alter it by guesswork.
4. Distinguish any warning artwork (`svb_orange.jpg`, `booting_warning.jpg`, `warning.jpg`, or other names) from the primary splash. Only the exact names **present in the real partition** matter.
5. Preserve images for Download Mode, error displays, battery charging and other critical stages **unchanged**.
6. Compare partition size with unpacked archive size and trailing bytes. Do not throw away unknown original data as “padding” without proof.
7. Stop if the format cannot be reconstructed losslessly enough to restore every non-target entry.

Create `A46-ORIGINAL-IMAGE-ANALYSIS.md` with concrete evidence: original entry list, actual source of Samsung splash and original partition SHA-256.

---

## PHASE 6 — CREATE THE EXACT NUXEL BOOT SPLASH OFFLINE

From **`./assets/nuxel-boot-screen.jpg` only**:

1. Match the actual confirmed boot-logo entry's file type, orientation, pixel dimensions and encoder expectations. MOSS suggests the common case is baseline JPEG named `logo.jpg`, but prove that from the original.
2. **The owner's source is already named `.jpg`. Verify it truly decodes as JPEG**, then compare its encoding, dimensions, subsampling, EXIF orientation, color profile and baseline/progressive mode to the **original splash JPEG extracted from this device**. If the bootloader requires a different JPEG variant, perform a documented image decode/re-encode from the owner's exact JPG with preserved artwork, correct orientation, contrast, crop/padding and aspect ratio. No blind extension renaming; do not convert from a PNG unless the owner separately provides a PNG and approves that change.
3. Verify final Nuxel image against the original boot-frame scale. Avoid unintentional cropping, rotation, distortion, blur or pixel-art smoothing. Preserve the original splash's pixel dimensions when required, check JPEG decodability with independent tools, and inspect whether its firmware requires no EXIF rotation, baseline JPEG, specific chroma sampling or particular maximum byte sizes.
4. Build a candidate that changes **only** the confirmed early-boot splash entry; retain every other image/file, filename, entry type and order where required, and preserve non-archive bytes where supported.
5. Produce a validated full-size candidate image appropriate for the partition **with the exact expected byte length**. In no case may the payload exceed the device-reported capacity, contain malformed tar headers, omit protected resources or write past the destination boundary.
6. Analyze before/after differences: exact list of modified entries, JPEG properties, entry checksums, archive listing, total bytes and candidate SHA-256.
7. Independently decode/extract the candidate with two available tools when feasible and compare all untouched content byte-for-byte.
8. Generate a **preview** of the real owner artwork at expected phone dimensions. Label it clearly as a preview, **not** proof of actual early boot rendering.

**Optional warning-artwork subtask:** If owner still wants the visual warning customized, establish its original filename and boot-stage behavior separately. Cosmetic substitution must retain bootloader state and security checks. Do not use a “1-pixel blank image” technique without exact firmware compatibility evidence, and do not touch a second partition without **new explicit consent** and independent backup/validation. It's acceptable to complete the boot-logo-only mission and report warning replacement blocked/unverified.

**Do not install MOSS's auto-reapply `post-fs-data.sh`/`service.sh`.** The finished candidate should need **one** bounded flash, not repeated boot writes.

---

## PHASE 7 — PRE-FLASH VALIDATION AND CONDITIONAL AUTHORIZATION GATE

Run all checks **before exercising the owner's strictly conditional one-time authorization**:

- Confirm exact physical model and target block device; report symbolic and canonical paths.
- Confirm the complete verified inventory/backup manifest for **every readable/addressable partition**; no missing backup may be waived under this run's conditional authorization.
- Confirm Mac-backed original target image matches the current live block device hash.
- Confirm candidate image and intended target lengths are correct and every untouched original component remains identical.
- Confirm both tar and JPEG parsing work, including padding and archive integrity.
- Confirm approved image is the exact owner-supplied art.
- Confirm tested restoration process does not depend on Magisk/Android or a running Nuxel installation.
- Confirm a working recovery connection and sufficient battery/power stability.
- Confirm **no current A45 process is using the phone**.

Present a concise final prewrite verification summary **in the agent's own execution log**:

`DEVICE MODEL | FIRMWARE | PARTITION NAME | CANONICAL DEVICE | PARTITION BYTES | ORIGINAL SHA-256 | CANDIDATE SHA-256 | OFF-DEVICE BACKUP COVERAGE | RESTORE PLAN | KNOWN RISKS`

**One-time conditional owner authorization from this current request:** The owner has asked the agent to flash the Nuxel boot splash **after** backing up **all readable/addressable partitions** while the SM-G975F is in TWRP. This authorizes **only one** fully validated write of the **first-splash resource**, on the **exact verified, original-backed-up splash partition**, **provided every gate in this document is conclusively passed**. It does **not** authorize changes to other partitions, warning/security enforcement, firmware, bootloader, recovery, kernel, rootfs, or a second image. Stop and ask the owner for fresh explicit approval if the intended write is to anything other than the verified splash partition, if any backup is missing, if the device model differs, if the image format is not proven, if the candidate cannot be validated, or if any unexpected failure occurs.

**The conditional authorization is NOT permission to guess.** There must be no write until model, partition identity, all-partition backup coverage, original partition hash, candidate integrity, tested restore path, and reliable recovery transport are established. Do not treat TWRP's presence as proof any of those conditions are true. Immediately before writing, recheck them and make the final summary available to the owner.

---

## PHASE 8 — ONE GUARDED TWRP WRITE (ONLY WHEN CONDITIONAL AUTHORIZATION AND EVERY GATE PASS)

1. Reconfirm recovery connection, model, intended canonical device, battery/USB stability, size, backup integrity, current partition hash, and absence of conflicting device access.
2. Transfer the validated candidate via an appropriate binary-safe method to **verified temporary recovery storage with sufficient space**, verify its byte count and SHA-256 there. Do not stage on the target partition or an uncertain/encrypted user-data mount; if TWRP has no safe staging capacity, stop and design/validate an alternate binary-safe method before proceeding.
3. Execute **one size-bounded, exact-target raw write** only to the owner-authorized and independently verified splash partition. Verify process exit status, bytes written and storage errors; call `sync`.
4. Read back the **entire target partition** to an independent recovery file and compare its SHA-256 with the candidate **before reboot**. If the archive occupies less than the partition, compare the **entire full-size partition image**, not only the tar portion. Never compute an expected hash from truncated/padded image assumptions that were not separately validated.
5. If mismatch: **DO NOT REBOOT**. Use verified restore plan for the original target partition, read it back in full, confirm exact original SHA-256, and abort.
6. Do not write boot, recovery, sboot/bootloader, kernel, rootfs, vendor, userdata, EFS/NV or modem partitions. No `setenforce 0`, no Magisk installation, no auto-start flash services.
7. If a second partition turns out to be necessary, stop and request a separate approved write; never silently batch writes.

If the device refuses the candidate or partition is read-only, report the actual error and stop. Do not search for less-verified alternative firmware or force permissive writes.

---

## PHASE 9 — FIRST BOOT AND NUXEL VERIFICATION

After whole-partition readback matches:

1. Reboot from TWRP using **the existing normal Nuxel boot path**, not a freshly flashed OS image.
2. Record the powered-on screen with an external camera or owner observation. Verify the exact Nuxel graphic replaces the original earliest Samsung logo, not merely the Linux boot animation.
3. Note the warning-stage behavior accurately; a cosmetic resource change does not alter real bootloader unlock state.
4. Verify no image corruption, rotated logo, clipping, strange color conversion, delays or errors.
5. Confirm the existing Fedora/Nuxel installation boots with its kernel, userdata, compositor, connectivity and USB console preserved.
6. **Do not test or change A45 keyboard or lockscreen during this mission.** Record only that the boot path reaches the expected existing graphical screen; allow A45's owner/agent to continue separately.
7. Perform another cold boot only after the initial one succeeds. Confirm the custom splash persists without MOSS Android boot hooks.
8. If boot fails, recover to TWRP, restore the verified original splash partition, independently verify the restore hash and retry boot; do not experiment with unrelated partitions.

---

## PHASE 10 — DELIVERABLES AND HONEST STATUS

Create:

- `A46-MOSS-SOURCE-AUDIT.md` — precise effects/risks of the included MOSS scripts and why they were not run unchanged.
- `A46-PARTITION-INVENTORY.md` — exact model, names, sizes and device-node identities.
- `A46-BACKUP-MANIFEST.json` — off-device backup receipts, bytes, hashes, coverage and explicit limitations. **No sensitive raw dumps in Git.**
- `A46-ORIGINAL-IMAGE-ANALYSIS.md` — actual archive layout, original splash filename, image format and partition hash.
- `A46-NUXEL-BOOT-PREVIEW.png` — clearly labeled *preview export* rendered from the exact owner-supplied JPG; this preview PNG is NOT flashed.
- `A46-CANDIDATE-VALIDATION.md` — candidate SHA-256, complete format/size checks, unchanged-entry verification, and a plain-language summary of all altered bytes.
- `A46-FLASH-AUTHORIZATION.md` — record the scope of conditional permission from the owner, each passed/failed safety gate, exact approved target and final prewrite checks; do not invent a new approval.
- `A46-READBACK-AND-BOOT-RESULT.md` — actual partition readback, live physical result, recovery availability, photos/observations and exact PASS/FAIL/BLOCKED.
- `A46-ROLLBACK.md` — exact off-device original location, guarded restore procedure and expected hash.

Statuses: `DISCOVERED`, `BACKED_UP`, `CANDIDATE_BUILT`, `VALIDATED_OFFLINE`, `GATES_PASSED`, `FLASHED`, `READBACK_VERIFIED`, `BOOT_VERIFIED`, `OWNER_CONFIRMED`, `BLOCKED`, `RESTORED`.

**Never claim a successful logo swap just because the offline candidate was built or the block write returned success.** Successful completion requires the actual **first** boot frame visibly showing the exact Nuxel artwork and the existing Fedora Nuxel installation booting again.

---

## FINAL STRICT RULES

- Only the early Samsung boot splash; optional cosmetic warning image only after separate evidence/approval.
- **ZERO** keyboard, lockscreen, OSK, Home, idle/power setting or Nuxel graphical code changes.
- **ZERO** bootloader unlock/security-state changes.
- **ZERO** boot/kernel/rootfs/recovery replacement.
- **ZERO** automatic Magisk installs or periodic splash partition rewrites.
- All requested partitions backed up under this authorization; any requested reduction of scope requires a fresh owner decision and a new safety review. The original target backup and tested restore route are mandatory without exception.
- Flash **only** after all stringent gates pass and only within this request's one-time, splash-target-specific conditional authorization. Otherwise **STOP** and ask; never silently weaken the backup scope.
- Never flash the same image repeatedly in an automated recovery loop, and never enable any boot hook to rewrite the partition.
- Use device-derived evidence rather than generic Samsung/MOSS assumptions.
- Do not disrupt the concurrent A45 agent.
- No fabricated hardware validation or misleading claims about disabling security warnings.

**SUCCESS:** The actual Galaxy S10+ boots from a personalized **Nuxel early splash** into the existing Nuxel system, with its A45 keyboard/lockscreen work undisturbed, full target-partition readback verified and an off-device rollback ready.

**BEGIN WITH READ-ONLY INSPECTION OF MOSS, THE BOOT JPG AND THE TWRP DEVICE. 🐧🔥**
