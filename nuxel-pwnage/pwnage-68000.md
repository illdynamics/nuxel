# PWNAGE-68000 — Kickstarter / execution prompt

Read `full-pwnage-68000.md` in full and execute it as the complete PWNAGE-68000 mission. This is a continuation of PWNAGE-61000, not a fresh investigation.

The previous mission built the MFC fail-closed kernel patch, kernel/DTB, firmware verification, safety receipt, diagnostic, vendor-ABI decoder helper, player wrapper, tests and rollback. **It did not flash the patched kernel, install the firmware on the live phone, open `/dev/video6`, or decode a frame.** The live handset still runs its pre-patch `4.14.253-gf7194c1d15ed-dirty` kernel; live status is `BLOCKED_FIRMWARE_MISSING`; hardware decode and performance remain unproven.

Your first task is to verify the current repository and handset state, inspect every PWNAGE-61000 report/artifact, and investigate the owner's earlier TWRP/boot hang. Do not repeat the previous flash procedure unchanged. Complete the exact BOOT image packaging, hash/DTB/initramfs verification, fresh rollback capture plan and all automated tests before requesting any flash approval.

**Do not ask the owner to enter TWRP yet.** Keep the phone in normal Nuxel with USB/SSH available during preflight. Do not toggle OEM unlock/FRP/KG, relock the bootloader, wipe userdata, or touch any partition other than a later verified BOOT-only target. If a separately approved TWRP update becomes necessary, verify device identity and partition mapping, flash once, read back and hash-verify, then choose **Reboot → System** (not Recovery). If it fails, restore the fresh exact BOOT backup and stop; do not loop attempts.

After the patched kernel is confirmed live and `/lib/firmware/mfc_fw.bin` is verified against the exact 685832-byte / SHA-256 manifest entry, preserve the GStreamer/WirePlumber guards and use the owner-approved, receipt-bound diagnostic for one controlled query-only/open-close test. Do not open the decoder early. Proceed to the vendor V4L2 queue test only if the first operations are clean, and claim hardware decoding only after a real frame, fixture hash and output checksum are proven.

Keep `mpv --hwdec=no` software playback and boot preload working. Do not claim 4K, HEVC or performance benefits until measured. Preserve the existing Mali GPU path and verify Phoc/framebuffer health after any deployment.

Implement, build, test, prepare deployment and rollback, and create every report/evidence artifact required by the full prompt. Stop at each explicit owner-approval boundary. If the phone is unavailable, complete all offline work and mark hardware stages `NOT_RUN`—never simulate success.
