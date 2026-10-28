# PWNAGE-31000 — NUXEL PRELOAD CINEMA
## Kickstarter prompt for Cyber-Tiel

The full prompt is at ./full-pwnage-31000.md, use it.

Repository: /x/nuxel
Milestone: PWNAGE-31000
Asset: ./assets/nuxel-preloading-screen.mp4
Target: Existing Nuxel Fedora-based Linux phone OS and live-userspace workflow.

MISSION
Implement a polished, fullscreen pre-lockscreen boot-video experience using
./assets/nuxel-preloading-screen.mp4.

Read and execute the complete specification in pwnage-31000.md.

The video should appear immediately before the real Nuxel lockscreen while
the existing startup services initialize concurrently. Make startup feel
cinematic without compromising boot reliability, security, recovery access,
or actual service initialization.

REQUIRED SEQUENCE
1. Preserve the existing boot and warning screens and their behavior.
2. Once the display system can play the video, start the preloading animation.
3. Allow existing startup services to initialize concurrently.
4. Wait for both video completion and the required lockscreen-readiness
   conditions, with a bounded video display time.
5. Transition directly to the real, interactive Nuxel lockscreen.
6. Continue noncritical background initialization without blocking the
   lockscreen indefinitely.
7. If video decoding or playback fails, fall back to the existing safe
   boot-screen/loading behavior and continue startup.

EXECUTION RULES
- Inspect the actual boot flow, service dependencies, compositor, media
  stack, MP4 metadata, asset packaging and current lockscreen implementation.
- Do not assume a codec, player, display server or service manager without
  verifying the running environment.
- Do not start duplicate service instances or eagerly launch every app.
- Never fake service readiness or progress.
- Never show the desktop before the real lockscreen is ready.
- Preserve the existing unlock flow, lockscreen assets and input handling.
- Preserve the live console and recovery path.
- No flashing, partition writes, bootloader changes or kernel replacement.
- Back up modified configuration and provide rollback instructions.
- Add automated tests, packaging/hash verification and deployment-manifest
  coverage using the repository's existing workflow.
- Do not claim physical-device success unless actually verified.

Inspect the repository, implement the complete feature, run the real tests,
package the changes, validate deployment and report PASS/BLOCKED/FAIL with
actual evidence.

Do not stop at a design or a plan. Begin implementation now.
