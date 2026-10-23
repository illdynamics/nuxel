# 🐧🔥 NUXEL A46.3 — SPLIT WARNING-SCREEN FINALIZATION

## GOAL
Refine the Samsung Galaxy S10+ boot visuals so the boot sequence becomes:

1. **Normal Nuxel logo**
2. **Funny Nuxel unlocked-bootloader warning screen** using `./assets/nuxel-boot-screen-warn.jpg`
3. **Normal Nuxel logo again**
4. **Spinning penguin boot animation**

Only the unlocked-bootloader warning full-screen image and the exclamation-mark warning overlay should change in this mission.

---

## REQUIRED VISUAL PLAN

### Keep unchanged
- The **first normal Nuxel logo** screen that is already working.
- The **later normal Nuxel logo** screen behind the warning overlay, unless the actual resource mapping proves it is a separate editable image and it is already correct.
- The **spinning penguin boot animation**.
- Nuxel boot flow, userspace, lockscreen, keyboard, launcher, rootfs, kernel, recovery, and other boot resources.

### Change only these two things

#### 1. Fullscreen unlocked-bootloader warning background
Replace the **fullscreen unlocked bootloader warning screen** with:

`./assets/nuxel-boot-screen-warn.jpg`

This is the funny/custom warning background.

#### 2. Exclamation-mark warning overlay
Replace the warning overlay itself (the warning/exclamation asset shown on top of the later logo) with a **1 black pixel** image, only if the resource format safely supports that.

This means:
- the **warning overlay** should effectively disappear
- the **background/logo behind it stays the normal logo**

---

## IMPORTANT CLARIFICATION
Do **not** assume the first logo and the later logo-behind-warning are necessarily the same image resource.

Your first task is to determine the actual resource mapping on the phone:

- Is the first normal logo one file?
- Is the logo behind the exclamation-warning the same file or a different one?
- Is the full-screen unlocked-bootloader warning a separate image?
- Is the exclamation warning itself a separate overlay image?

Use the actual extracted partition contents to answer this.

If the two normal logos are in fact separate resources, preserve them both unless one is already supposed to remain visually identical and is already correct.

If they are the same resource, do not replace that shared resource with the warning background. The unlocked warning screen must specifically use the funny warning image while the normal logos remain normal.

If achieving that distinction requires editing a different warning-specific resource, do that instead.

---

## MISSION SCOPE
This is a **minimal surgical boot-resource finetune**.

### Allowed
- Inspect current working boot-resource partitions.
- Back up relevant partitions to the host.
- Extract and inspect images/resources.
- Replace the unlocked-warning fullscreen image with `./assets/nuxel-boot-screen-warn.jpg`.
- Replace the exclamation/warning overlay with a 1-pixel black image if validated safe.
- Rebuild the resource archive.
- Flash only the verified target resource partition.
- Read back and verify.

### Forbidden
- Do not alter the working first normal Nuxel logo.
- Do not replace the normal logo behind the warning unless the mapping proves that resource itself is the overlay target and the plan still preserves the intended normal logo sequence.
- Do not alter the spinning penguin animation.
- Do not install MOSS or Magisk hooks.
- Do not run broad auto-patching across unrelated partitions.
- Do not modify bootloader binaries, kernel, recovery, rootfs, userdata, or userspace.
- Do not touch keyboard/lockscreen work.

---

## DEVICE MODE
Phone is in **TWRP mode**.
Use TWRP only as a safe environment for:
- identification
- partition backup
- controlled single-partition write
- rollback if needed

---

## BACKUP REQUIREMENTS
Before any modification:

1. Identify the exact resource partition(s) containing the current working Nuxel boot visuals.
2. Dump the relevant partition(s) to the host machine.
3. Record:
   - partition path
   - byte size
   - SHA-256 hash
   - timestamp
4. Preserve these as the rollback baseline.
5. Use the dumped partition as the source for all editing.

If backup fails, stop.

---

## REQUIRED SOURCE ASSETS
Verify these exist before continuing:

### Custom unlocked-warning background
`./assets/nuxel-boot-screen-warn.jpg`

Verify:
- file exists
- valid JPEG
- readable
- dimensions known
- encoding known

### Overlay neutralization asset
Create a **1 black pixel** replacement in the exact image format required by the target resource.

If the target resource does not safely support 1x1 dimensions, create the smallest safe black image that preserves decoding and rendering while still effectively hiding the overlay.

Do **not** risk a broken decode for cosmetic reasons.

---

## RESOURCE-MAPPING PHASE (MANDATORY)
Extract and inspect the active working resource archive/partition.
Determine exactly which resource corresponds to:

1. First normal Nuxel logo
2. Fullscreen unlocked-bootloader warning image
3. Later normal logo behind the exclamation-warning
4. Exclamation/warning overlay itself
5. Spinning penguin animation, if present in the same archive

Document the exact filenames and which partition they came from.

### Important rule
Do not proceed based on assumptions from third-party patchers alone.
Use the real extracted files from the current phone image.

---

## IMPLEMENTATION PLAN
Using the backed-up current working partition image:

1. Extract/unpack it.
2. Locate the **fullscreen unlocked-warning image**.
3. Replace only that background with `./assets/nuxel-boot-screen-warn.jpg`, converted/re-encoded only as needed for exact compatibility.
4. Locate the **warning/exclamation overlay resource**.
5. Replace that overlay with the validated black minimal image.
6. Leave the normal logo resources unchanged.
7. Leave the spinning penguin animation unchanged.
8. Rebuild the archive/partition image.

---

## VALIDATION BEFORE FLASHING
Before writing anything, confirm:

- the resource mapping is understood
- the first normal logo remains unchanged
- the full-screen unlocked-warning background now maps to `nuxel-boot-screen-warn.jpg`
- the warning overlay is replaced with the black minimal image
- the later normal logo remains normal
- the spinning penguin animation remains intact
- only intended files changed
- the rebuilt image fits partition size constraints
- the rebuild format matches the source format
- rollback is ready

Produce a small before/after resource diff.

If uncertain, stop and report.

---

## WRITE AUTHORIZATION
After validation, request approval conceptually within the execution flow, then perform **one verified write** to the correct target partition only.

Do not write any other partition.

---

## FLASH PROCEDURE
1. Confirm model: **SM-G975F**.
2. Confirm TWRP environment.
3. Confirm backup exists.
4. Flash only the rebuilt target resource partition image.
5. Read back the full partition.
6. Compute SHA-256.
7. Confirm the readback exactly matches the intended rebuilt image.
8. Reboot into the existing Nuxel installation.

---

## EXPECTED FINAL BOOT FLOW
After successful patching, the phone should boot visually as:

1. **Normal Nuxel logo**
2. **Funny/custom warning screen** from `./assets/nuxel-boot-screen-warn.jpg`
3. **Normal Nuxel logo**
4. **Spinning penguin boot animation**

The exclamation-mark warning overlay should no longer visibly interfere.

---

## PHYSICAL ACCEPTANCE TEST
After reboot, verify on the actual phone:

1. First normal Nuxel logo still appears.
2. Full-screen unlocked-warning screen now shows `./assets/nuxel-boot-screen-warn.jpg`.
3. The later logo remains the normal logo.
4. The exclamation/warning overlay is gone or effectively invisible.
5. The spinning penguin animation still appears.
6. Nuxel continues booting normally.

If any stage is wrong, use rollback.

---

## ROLLBACK
If the result is incorrect:
- restore the backed-up current working resource partition
- verify readback
- reboot
- confirm return to last known-good state

---

## REPORTING
At the end, report:
- target partition path
- exact extracted resource names
- which files represented:
  - first normal logo
  - unlocked-warning background
  - later logo
  - exclamation overlay
- which files were changed
- SHA-256 of backup image
- SHA-256 of rebuilt image
- SHA-256 of readback
- whether 1x1 black was used or a larger safe black substitute was required
- physical boot verification result
- rollback artifact path

---

## ABSOLUTE RULES
- DO NOT touch the already-working normal boot logo(s) except to preserve them.
- DO NOT replace the normal logo with the warning image.
- DO NOT modify the spinning penguin animation.
- DO NOT broad-patch unrelated assets.
- DO NOT install MOSS hooks.
- DO NOT proceed without a verified backup.
- DO NOT proceed if `./assets/nuxel-boot-screen-warn.jpg` is missing.
- DO NOT risk a corrupted resource archive for a cosmetic tweak.
- DO NOT claim success without a real boot test.

---

## FINAL DIRECTIVE
Perform a final, minimal, safe finetune so the sequence becomes:

**normal logo → funny warning background → normal logo → spinning penguin**

with the exclamation-mark warning itself hidden via a black minimal overlay replacement.

Preserve the rest exactly as it is.

**BACK UP. MAP RESOURCES. PATCH ONLY THE WARNING-SPECIFIC ASSETS. VERIFY. FLASH ONCE. REBOOT. CONFIRM.** 🐧🔥
