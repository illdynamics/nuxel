# 🐧🔥 NUXEL A46.1 — OPERATION CLEAN PENGUIN BOOT
## Cosmetic bootloader-warning artwork fine-tune, layered ON TOP of the already-working A46 Nuxel early splash

**Executor:** `deepseek-v4-pro-thinking` operating in the owner's current Nuxel checkout on the MacBook.  
**Device:** owner-owned Samsung Galaxy S10+ **SM-G975F**, `beyond2lte`, Exynos 9820, booting existing Fedora ARM64 Nuxel.  
**Owner's exact logo:** `./assets/nuxel-boot-screen.jpg` (actual JPEG; verify).  
**Read first:** `./NUXEL-A46-MOSS-BOOT-SPLASH-ONLY.md` for the previous safety architecture, plus the previous **A46 real execution receipts**, backup manifest, candidate image, verified readback, and rollback location. This A46.1 addendum **supersedes A46's old scope restriction only for cosmetic warning resources**; all protective boundaries remain in force.

## Mission and current known-good state

**A46 SUCCEEDED ON REAL HARDWARE. THE FIRST NUXEL BOOT LOGO IS ALREADY SHOWING. DO NOT UNDO IT.**

The owner wants the remaining Samsung pre-Linux boot warning visuals refined to show the same Nuxel artwork instead of intrusive stock unlock warnings:

1. **Warning stage A:** full-screen **unlocked bootloader** warning appearing after/before the first logo.
2. **Warning stage B:** when the logo comes back a second time, the **exclamation/warning image near the top**.

**Deliverable:** an aesthetically consistent Nuxel boot sequence with these two cosmetic resources handled **if the exact live firmware makes them safely editable**, with the already working first splash byte-for-byte preserved and Nuxel boot continuing normally. It is entirely acceptable to mark one stage **BLOCKED/UNMODIFIABLE** if it is composited by the bootloader or isn't in a verified writable image resource.

**Important distinction:** changing or hiding a JPEG warning graphic **does not lock the bootloader, restore verified boot, modify Knox state, enforce OS signing, or eliminate any underlying security risk**. Do not describe the device as locked, verified, or unmodified. Never patch security checks or bootloader executable code. If a warning requires pressing Power to continue, preserve that behavior and make the necessary instruction visible enough for the owner to operate it; do not bypass it.

---

## Absolute scope and non-negotiable safeguards

- **Only** the boot-time *cosmetic image resources* proven to belong to warning stages A/B; expected candidates include `svb_orange.jpg` and `booting_warning.jpg`, **but names alone prove nothing**.
- **DO NOT** modify `logo.jpg` or any other already-working primary Nuxel splash bytes. Do not change its image dimensions, JPEG content, boot timing, or source file.
- Do not change bootloader binaries (`sboot`, `abl`, `lk`, etc.), trust anchors, eFuses, Knox, signature checking, lock state, AVB, vbmeta, kernel, boot.img, recovery.img, DTB, rootfs, system, vendor, userdata, EFS/NV, modem, Android/Magisk or Nuxel graphical code.
- Never run MOSS `customize.sh`, `post-fs-data.sh`, `service.sh`, or TWRP patcher's `update-binary`/recovery ZIP as-is. In particular, the TWRP patcher may discover **and automatically flash BOTH `up_param` and `param`**, and copies `logo.jpg` plus a one-pixel image. It is a **research reference**, not permission for broad writes.
- **No automatic repeated flashing.** This should be at most one verified write per separately approved, independently backed-up target partition.
- Do not reboot a phone that another agent, USB deployment, or user is actively using. Phone may **no longer be in TWRP** after the successful A46 boot. Establish its current state; do not assume recovery availability.
- If you cannot safely identify/alter a particular overlay while preserving the original Nuxel logo and other boot resources, **stop that subtask** and report the precise blocker. Never try a firmware/bootloader binary patch as fallback.
- Do not publish any partition dump, serial number, EFS/NV backup, or private userdata into Git or public reports.

---

## PHASE 0 — Capture the actual sequence BEFORE working on archives

1. Ask the owner for a short external-camera video or stills of **every transition from power-on to Nuxel lockscreen**. Record order, duration, exact top exclamation mark, any yellow/orange text, and whether Power must be pressed.
2. If you have physical-camera access through an authorized host setup, capture it yourself. Otherwise use owner observations; **do not invent visual evidence**.
3. Write `A46.1-BOOT-STAGE-MAP.md` with the visible stages:
   - S0: first working Nuxel logo.
   - S1: unlocked warning full-screen, if present.
   - S2: second logo with top warning/exclamation.
   - S3: Linux/Nuxel startup and lockscreen.
4. Establish whether S2 is the same JPEG with another graphic composited on it, or an independent file. Image compositing cannot be inferred just from appearance.
5. Preserve timing and user-required interaction (e.g. Power confirmation). Cosmetic styling must not make a required prompt impossible to understand.

**Do not enter recovery or flash anything in this phase.**

## PHASE 1 — Source forensics: MOSS and TWRP warning patcher (read-only)

Inspect these owner-supplied archives if present:

- `MOSS-main(2).zip` — MOSS tar/JPEG boot artwork convention and known risks.
- `TWRP_Bootlogo_patcher-master(1).zip` — Exynos warning-resource precedent. It lists **G975F** as supported and its script processes **`up_param` and `param` separately**; relevant names are typically `svb_orange.jpg` and `booting_warning.jpg`.

**Verify actual code, don't trust a README as an implementation guarantee.** The provided TWRP patcher script in `META-INF/com/google/android/update-binary` finds partition names dynamically, backs them up (to `/sdcard`, not automatically off-device), repacks tar content, and writes raw partitions. It may replace `svb_orange.jpg` with `logo.jpg` and `booting_warning.jpg` with a tiny `1px.jpg`. **Do not run it**: its automatic two-target write, shallow safety checks, lost metadata potential, and opaque one-pixel overlay behavior are unsuitable for this mission without proof on the actual current firmware.

Perform a conservative format review and record sources/hashes. Distinguish:

- `logo.jpg`: current working main image — **unchanged**.
- `svb_orange.jpg`: possible unlocked-warning full-screen visual — validate against actual extracted pixels and S1.
- `booting_warning.jpg`: possible second-stage warning overlay — validate against actual extracted pixels and S2.
- Other entries: charge/offline/download/diagnostic imagery, `letter.jpg`, `lpm.jpg`, unknown files, and archive padding/opaque metadata — **unchanged**.

Note: this naming comes from community patcher source; a particular S10+ firmware revision may have a different arrangement, absent entries, multiple copies, or some bootloader-generated graphics.

## PHASE 2 — Verify the owner has restorable backups of EVERYTHING requested in A46

1. Locate **the actual completed A46 backup manifest** and logs from the successful physical flashing run. Do not use a fictional manifest or an unverified `.img` name.
2. Reconcile the earlier inventory with the actual current device, confirming that **every readable/addressable partition requested in A46** was backed up off-device, with correct sizes, SHA-256 and documented exceptions. If required coverage was skipped or cannot be independently verified, halt any flash and arrange to finish the backup before proceeding; do not silently waive it.
3. Check the complete original A46 splash partition backup from BEFORE the first successful logo change is still securely stored as historical fallback.
4. **Critically, create a NEW off-device full-size backup of the CURRENT splash partition containing the WORKING NUXEL LOGO**. This is the **A46.1 immediate rollback baseline**, not the old stock/Samsung image. Check whole-image SHA-256 and byte size. Keep two copies if practical.
5. If `param` is a separate candidate, back up its entire CURRENT image independently as well (and verify); never assume it is an alias of `up_param`.
6. Record the real device identities and partition sizes from TWRP, not a memorized `mmcblk` number; use device-side hash verification where feasible.
7. Backups must be stored on the MacBook **outside Git, outside the working phone and outside the target partition**. Document the required disk space (all-partition snapshots may be large); keep them private and readable.
8. Require a **working verified restore procedure** for each proposed write, including how recovery is reached after a failed boot. If TWRP, ADB, USB, or backups are unavailable, do not write.

**Mandatory gate:** all earlier required partition backups verified or completed; fresh full current image for EVERY proposed target independently backed up; restoration path prepared. No exceptions for splash-partition backups.

## PHASE 3 — Read the LIVE working splash container and map each warning

1. Using TWRP's read-only shell, verify `SM-G975F`, `beyond2lte`, current firmware/recovery evidence, exact partition names, actual canonical block nodes and byte sizes.
2. Copy the current candidate partition(s) off-device **without changing them**. Record original SHA-256, size and metadata before even building a patch.
3. Independently parse the actual archive/container; list all entries with order, sizes, properties and hashes, including duplicates, padding, opaque trailer and non-JPEG content. Do not assume everything is an ordinary tar.
4. Extract and visually inspect all likely warning JPEGs in isolation. Match their text/image/shape against S1 and S2 video/stills, not just filename patterns.
5. Compare the extracted current `logo.jpg` SHA-256, dimensions and pixels with the successfully flashed A46 record and `./assets/nuxel-boot-screen.jpg`. Preserve the **EXTRACTED WORKING `logo.jpg` bytes** even if the source JPG has changed or has different metadata.
6. Investigate whether S2's exclamation mark is embedded in a warning JPG, displayed as an overlay JPEG, or drawn programmatically by bootloader firmware.
7. For each visible stage, produce a table: **stage → evidence → resource name → containing partition → confidence → safe art-only change possible?**
8. If there is no provable image resource for S2, stop that stage. **Never patch bootloader executable or security code** to remove an overlay.

## PHASE 4 — Design a cosmetic warning-specific patch that PRESERVES the logo

For each conclusively identified editable warning resource:

1. Use the verified owner source `./assets/nuxel-boot-screen.jpg` for Nuxel-themed visuals. Compare it to the working current `logo.jpg`. Do not overwrite `logo.jpg` itself.
2. **Full-screen warning** (`svb_orange.jpg` if proven): render Nuxel branding in a JPEG compatible with this exact warning entry's expected layout, dimensions, orientation, encoding, and resource size limits. A straight byte-copy of `logo.jpg` is allowed only when safe on this firmware; otherwise do a documented composition/re-encode of the same art for this entry.
3. **Second-logo exclamation overlay** (`booting_warning.jpg` if proven): first establish how the bootloader blends/places it. It may be a compact overlay rather than a full-screen image. Do **not** replace a small overlay with full-screen Nuxel art merely because both are JPG. Only use a minimal cosmetic replacement if the precise image behavior is demonstrated safe. A tiny/one-pixel neutral image is NOT automatically safe on this device; require format/size/placement evidence. If unknown, keep the warning intact and report the blocked stage.
4. Preserve mandatory user interaction. If the bootloader actually requires 'Press Power to continue', create visually consistent guidance rather than misleadingly pretending it has already continued.
5. Avoid suggesting the device is locked, verified, stock, or secure. The change affects graphics only; maintain a durable record that the bootloader is unlocked and that the warning art was customized.
6. Leave every other archive member, metadata and opaque payload intact, especially `logo.jpg`, `lpm.jpg`, Download Mode and battery/error/charging graphics.
7. Generate before/after visual previews for S1 and S2 **labeled as predicted**, not actual device proof.
8. Produce a concise change manifest describing every target entry and **exactly which file bytes changed**.

If exact archive reconstruction without harming unrelated data is not possible, **do not patch**. If target resource is immutable or bootloader generated, return BLOCKED with explanation.

## PHASE 5 — Offline validation, backup gate and flash authorization

Do not proceed based solely on `tar -tf` or the exit code of an archive repacker.

For each *separately verified* target image:

- Full partition image candidate is no larger than and ideally **exactly equal to** the device-reported partition length, accounting for all legitimate padding/opaque bytes.
- Container parses correctly with independent methods where feasible; JPEGs decode cleanly with expected orientation, color, dimensions and subsampling.
- Archive entries, ordering, ownership/metadata where relevant and all unrelated bytes/assets remain unchanged.
- The working `logo.jpg` is **byte-for-byte identical** to the current verified A46 logo; if not, FAIL.
- `param` and `up_param` are tracked as distinct targets even if both exist; do not flash one in place of the other.
- New baseline backup current partition hash equals a fresh device-side read/hash immediately before write.
- Restoration image and restore command/procedure are independently validated; stage recovery/USB is still available.
- All-partition backup coverage from previous A46 run is independently verified or completed before proceeding.
- No concurrent agent/session is accessing the phone.
- Show a stage mapping, image previews and clear risk analysis to the owner.

**Hard approval gate for A46.1:** This conversation authorizes investigation and prompt preparation, not an unspecified new partition rewrite. After preflight validation, ask the owner to approve a card with `SM-G975F | boot stages | exact target partition(s) | canonical block node(s) | sizes | current working-logo hash | baseline backup location/hash | candidate hash | entries changed | rollback plan | risk`. Require explicit owner confirmation **`APPROVE A46.1 WARNING ART FLASH: <EXACT PARTITION NAME>`** for EACH target partition. Do not reuse old A46 consent for this new write, and do not assume that approving `up_param` approves `param`.

If one candidate partition can implement both stages, prefer **one** well-validated image and **one** approved write. If two separate partitions are genuinely necessary, treat them as two separately authorized transactions; validate and restore the first before requesting the second.

## PHASE 6 — Controlled TWRP flash, full readback and recovery

**Only after the corresponding explicit approval:**

1. Reconfirm model, actual canonical block node, device/USB stability, correct current-hash baseline, storage, exact approved candidate, and independent restoration images.
2. Transfer candidate into TWRP safe temporary storage with binary-safe transfer; verify exact image SHA-256 there. Never write through Magisk or in the running Fedora OS.
3. Perform **one exact-target, size-checked write** for the specifically approved *cosmetic warning image partition*. Do not touch unrelated partitions or rescan/write broad targets automatically.
4. Sync and read back the **entire partition** independently into a separate file, verifying byte count and exact whole-image SHA-256 against candidate. A successful `dd` exit is insufficient.
5. If readback differs, **DO NOT REBOOT**. Restore the fresh A46.1 backup **containing the known-good Nuxel logo**, re-read the entire partition, and verify the full original SHA-256; then stop.
6. Only after readback verification and owner's approval to reboot, reboot normally into the EXISTING Nuxel OS; record S0/S1/S2/S3 on the actual device using external camera or owner observation.
7. Verify **first Nuxel logo still works**, modified warning stage(s) match predicted previews, Power-continue interaction is preserved if needed, lockscreen/Home/USB console still boot, and there is no added delay/boot loop.
8. If broken, recover via TWRP and restore **A46.1 current pre-patch baseline**, NOT historical stock artwork; verify the partition hash and original working splash.
9. Do not automatically retry another resource/partition if one image didn't fix the observed overlay. Diagnose evidence and seek new authorization.

### Required acceptance matrix

| Gate | PASS requires |
|---|---|
| S0 first Nuxel logo | EXACTLY as before; same working `logo.jpg` |
| S1 unlocked warning stage | Owner-selected Nuxel cosmetic art **or** evidence-backed BLOCKED |
| S2 top exclamation on second logo | Correct cosmetic result **or** evidence-backed BLOCKED |
| Bootloader security/knox/unlock status | **Unchanged**, explicitly acknowledged unlocked |
| Physical continuation | Any required Power press still works |
| Download/error/battery imagery | Unchanged |
| Nuxel Fedora boot | Working after patch |
| TWRP recovery | Still accessible |
| A46.1 partition readback | Entire target SHA-256 verified |
| Rollback | Restores the already-working A46 boot splash |

No fabricated PASS from offline previews or static source inspection.

## PHASE 7 — Deliverables

Save a dedicated `artifacts/A46.1-warning-art/` report folder **without private partition images**. Include:

1. `A46.1-BOOT-STAGE-MAP.md` (observed screens and timings).
2. `A46.1-WARNING-RESOURCE-MAPPING.md` (actual matched image/partition per stage, confidence and blockers).
3. `A46.1-PATCHER-SOURCE-AUDIT.md` (source review; why third-party scripts weren't run directly).
4. `A46.1-BACKUP-VERIFICATION.md` (all-partition previous coverage check; newly backed-up current target hashes, references but no private dumps).
5. `A46.1-PREVIEW-S1.jpg` and `A46.1-PREVIEW-S2.jpg` when stages are editable (predictions only).
6. `A46.1-CANDIDATE-DIFF.md` (entry-level and complete-image before/after hashes, logo byte identity).
7. `A46.1-OWNER-APPROVAL.md` (exact partition authorization or NOT APPROVED).
8. `A46.1-FLASH-READBACK-RESULT.md` (real transaction data, backup restore results where needed).
9. `A46.1-PHYSICAL-BOOT-ACCEPTANCE.md` (S0–S3 outcomes, evidence, honest status).
10. `A46.1-ROLLBACK.md` (restores **post-A46 known-good** logo, NOT old Samsung logo).

Status progression: `INSPECTING` → `BACKUPS_VERIFIED` → `RESOURCE_MAPPED` → `OFFLINE_PATCH_VALIDATED` → `AWAITING_SPECIFIC_APPROVAL` → `FLASHED` → `READBACK_VERIFIED` → `PHYSICALLY_CONFIRMED` (or `BLOCKED`, `RESTORED`).

## FINISH LINE

**Keep the first Nuxel logo exactly as it is. Make the remaining two warning-image stages visually match Nuxel only by changing proven cosmetic resources. Preserve all other functionality and security-state semantics. Never sacrifice a proven-working boot for a speculative overlay hack.**

**BEGIN WITH THE EXISTING A46 SUCCESS RECEIPTS AND REAL BOOT-STAGE VIDEO. 🐧🔥**
