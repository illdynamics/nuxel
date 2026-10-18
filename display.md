# NUXEL — INSTALL A35 DISPLAY FIX 🐧

Replace the current Nuxel repository with the attached patched ZIP, preserving Git history and existing uncommitted changes.

Read `docs/s10plus-autonomous-boot-repair/TOUCHDOWN/A35-DECON-FRAME-COMMIT.md`.

**MISSION: Install and physically verify the new DECON frame-commit repair on the running Galaxy S10+.**

1. Inspect the current MacBook USB live-console connection and phone state.
2. Build the patched `tools/s10plus/a34/nuxel-wl-fb.c` as a compatible Linux AArch64 ELF using the existing build infrastructure.
3. Run the new DECON tests and existing A34 regressions.
4. Back up the phone's current `/usr/lib/nuxel/nuxel-wl-fb` and record SHA-256.
5. Deploy the new binary through `scripts/s10plus-debug-pack/nuxel-live-deploy.sh`, restart only `nuxel-wl-fb`, and verify the installed checksum.
6. Verify `decon_pan_ok` increases and `decon_pan_failed` remains zero.
7. Announce a **90-second physical test**. Tell me to tap applications, close them, swipe, press Volume and perform screen-off/wake. Capture logs while I test.
8. Diagnose and fix any failures, then repeat the physical test.
9. Once interaction works, perform one safe normal Nuxel reboot and confirm the launcher appears automatically without Power-button intervention.

If the display becomes unusable, restore the previous binary using the USB console and restart the bridge.

**NO FLASHING. NO KERNEL CHANGES. NO RAW PARTITION WRITES.**

Do not declare success until I confirm that app taps update visibly and the AMOLED fully switches off with one Power press.

**EXECUTE NOW.**
