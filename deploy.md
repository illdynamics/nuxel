# NUXEL A37 — LIVE USB DEPLOY & VERIFY 🐧

Read `DEPLOY-A37.md` in the supplied patched repository.

**MISSION: Actually deploy and verify A37 on our running Samsung Galaxy S10+.**

1. Preserve Git history and existing work. Verify the MacBook USB live console and capture rollback backups.
2. Deploy the updated Nuxel launcher, app/navigation/Quick Settings PNGs, JavaScript, CSS and service-worker files into the **actual active webroot**.
3. Restart/reload the affected web and launcher services so WebKit loads the new PNGs rather than stale cached assets.
4. Install both original MP3 files, the patched `nuxel-sound-cue` helper, boot-sound service and A37 verification tool. Install missing ALSA utilities and `mpg123` safely.
5. Rebuild and deploy the updated button manager as a Linux AArch64 binary if the installed version lacks the volume-cue hook.
6. Run `nuxel-assets-audio-check`. Verify actual HTTP 200 responses and PNG byte identity.
7. **PRIORITY AUDIO:** Diagnose why the speaker is silent using the existing `nuxel-audio-diag.sh pipeline` and ALSA tools. Inspect the real CS47L93/CS35L40 routing and firmware. Establish a verified, low-volume speaker route without guessing mixer values or overwriting an already calibrated UCM. Then test `nuxel-pow.mp3` on Volume Up/Down and the boot MP3 at 44% software gain.
8. Verify that tapping the virtual keyboard produces real haptic feedback.
9. Announce a **90-second physical test** and tell me to check icons, keyboard vibrations and sound. Capture logs, collect my PASS/FAIL feedback, fix remaining problems and retest.
10. Perform one safe normal reboot when ready to verify the startup audio.

Never count an MP3 decoder exit code as proof that I heard sound.

**NO FLASHING. NO PARTITION WRITES. NO KERNEL REPLACEMENT.**

Don't stop after dry runs or merely installing files. Verify the actual phone and report the first remaining blocker.

**EXECUTE NOW.**
