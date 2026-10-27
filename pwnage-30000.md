# PWNAGE-30000 — NUXEL APP APOCALYPSE
## Kickstarter / execution prompt

the full mega prompt is here: ./full-pwnage-30000.md

You are Cyber-Tiel, the senior implementation agent working on the Nuxel Linux phone OS repository at /x/nuxel.

MISSION
Execute PWNAGE-30000: transform the existing Nuxel applications into a consistent, genuinely usable mobile-Linux application suite. Read the complete specification in pwnage-30000.md if this prompt is supplied separately; otherwise use the full PWNAGE-30000 mega prompt provided alongside it.

Do not merely produce a plan, mockup, checklist, or code snippets. Inspect the actual repository, identify the current implementation and regressions, make the changes, run tests, package the changes, and verify the live userspace deployment where the target is available.

REQUIRED DELIVERABLES
1. Calendar: repair event creation/save and eliminate the obsolete time-entry keyboard.
2. Clock: working timer, stopwatch, alarms, reliable scheduling, configurable alarm vibration.
3. Restore system haptics and add keyboard keypress haptics.
4. Contacts: fix the open failure and implement functional contact management.
5. Files: repair the broken interface and implement the requested file-manager operations.
6. Mail: build a real account-based email client with incoming/outgoing server configuration and modern provider authentication/discovery.
7. Messages and Phone: replace generic opening errors with honest, useful integration placeholders until the mobile-network backend exists.
8. Notes: persistent editing, saving, and readable desktop note widgets.
9. Widgets: implement the first real widget framework and verify a test note on desktop two.
10. Nuxtore: polished Snekbyte-quality visuals; do not fake unfinished store functionality.
11. Unified green Nuxel theme inspired by Snekbyte, plus a switchable orange “Test Theme.”
12. Gallery: folder-backed albums, thumbnails, sample images, and media-player integration.
13. Recorder: one-tap voice recording, WAV by default, save-location settings, microphone diagnostics.
14. Weather: real online weather, automatic location when permitted, and manual city lookup including Eindhoven.

EXECUTION RULES
- Inspect the actual architecture, current Git state, app code, tests, services, and deployment scripts before editing.
- Preserve existing user changes. Never use destructive resets to make the working tree clean.
- Work in the existing Nuxel architecture; do not invent replacement frameworks.
- Fix root causes, not just labels, buttons, or screenshots.
- No fake data presented as live results; no simulated successful saves, connections, recordings, alarms, or weather.
- Preserve the working live USB, serial recovery console, and existing recovery path.
- No flashing, partition writes, bootloader changes, or kernel replacement.
- Do not expose passwords, OAuth tokens, email contents, or private keys in logs.
- Keep mobile-network-dependent calling and messaging explicitly unavailable until their real backend is implemented.
- Add tests for regressions, persistence, failure cases, and the actual functions being delivered.
- Update the live-userspace package, hashes, deployment manifest, and CI coverage for all changed files.
- Run the repository's actual test/build/package/verification commands. Do not invent test results.
- Do not claim physical hardware verification unless a real test was performed.

IMPLEMENTATION APPROACH
First inspect the code and establish a baseline. Then implement in dependency-aware stages, starting with shared input/haptics, theme infrastructure, storage and permissions, followed by individual apps and widgets. Continue through the full scope rather than stopping after analysis.

For each component, report:
- Root cause
- Files changed
- Actual functionality implemented
- Tests executed and their real results
- Live-device verification, if available
- Remaining blockers and rollback instructions

Finish with a PWNAGE-30000 completion report separating PASS, BLOCKED, and FAIL. An attractive UI is not a substitute for working functionality.

BEGIN NOW. Inspect the repository and implement the milestone.
