# EMERGENCY PROMPT R — EXECUTE IF A CAMERA TEST RETURNS TO TWRP OR NUXEL NO LONGER BOOTS

**Urgency:** NO EXPERIMENTAL FIX FLASH. Priority is restoring the **last known-good Nuxel**, not continuing camera.

You are now in RECOVERY-ONLY mode. Suspend all kernel/DT development. Confirm the handset is the expected SM-G975F and TWRP is genuinely booted (not an intentional reboot). Preserve **read-only** TWRP logs, pstore, last_kmsg, bootloader messages, partition names/sizes, current BOOT SHA and available DTB/DTBO metadata. Do not mount/change unrelated filesystems. Find the immutable, off-device **known-good backups produced in PROMPT 00**, verify their SHA-256, size, format, model/board matching and exact destination by-name partitions. If current BOOT differs from the experimental candidate, first determine why before a write.

Restore ONLY the exact partition(s) the immediately preceding failed camera trial changed, using the repo's validated safety flasher with its exact target prompts and readback; **BOOT-only** is the default. No USERDATA, SYSTEM, RECOVERY, EFS, modem, parameters, or guessed DT partition changes. If evidence shows a separate DT partition was previously changed and there is a verified matching backup, require separate scope authorization and exact validation before restoring it. If there is no backup or no trustworthy partition identity, STOP rather than flash guesses.

Reboot normally and verify the original Nuxel kernel, board variant, active FDT, SSH and core subsystem health. If Nuxel is recovered: `RECOVERY=PASS`, preserve all logs, write a specific root-cause analysis of the experimental failure, and return to PROMPT 01/02/03 depending on the failing gate. If again in TWRP after a validated known-good restore, stop repeated flashes, inspect boot selection/bootloader evidence and seek a new diagnosis. Never issue endless identical writes or declare success because the installer exit code was zero.

**Output:** `reports/CAMERA-RECOVERY-INCIDENT.md` with exact failed candidate, known-good hashes, partitions written, readback, logs, actual Nuxel boot result and whether it's safe to resume. Do not continue with camera experiments until normal Nuxel is restored and PROMPT 00 updated.

---

## Priority order for short sessions

- If you only have **one** DeepSeek round: run **00**. It makes future camera work safe and establishes what actually survived the DT incident.
- If you have **three** rounds: run **00–02**. You should gain a safe, reproducibly compiling 4.14 port plan/code without a dangerous flash.
- For first physical rear frame: proceed **00 → 01 → 02 → 03 → 04 → 05**, only advancing on hard PASS. A small number of prompts or flashes cannot be guaranteed.
- For complete camera support: continue **06–08** and return to the guarded kernel/DT cycle only when proven necessary. Never skip physical acceptance.

**Stop condition:** The correct success claim is **“Nuxel boots normally with an exact known-good recovery path and captures genuine supported physical camera content end-to-end.”** Not “TWRP installer returned success,” not “QBUF worked,” and not “we think the new DT is correct.”
