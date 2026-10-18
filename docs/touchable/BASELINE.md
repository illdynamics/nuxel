# Operation Touchable baseline

Started 2026-10-18, Europe/Amsterdam. Acceptance is **PENDING**.

All pre-existing tracked and untracked work was preserved in commit `9145338`
on `feature/pre-touchable-snapshot-20261018` and pushed to origin. The working
branch is `feature/operation-touchable`. No AGENTS.md was found in the workspace
or its ancestor directories.

Read: latest v0.5.2 TODO/RESUME, Astra Touchdown handoff, LIVE-TOUCH-20261018,
touch interaction, application lifecycle, and GUI responsiveness reports.
Historical evdev/DOM evidence is not evidence of today's visible interaction.
Latest report says app.js was installed as
`eea79efd49ac7c973ab48ada52ed788fcffb2480f2d0471ac886657a3fd77a9a`.
Current phone state and source parity are being measured.

No local inference server was visible in the initial listening TCP inventory.
Requested Cyber-Tiel context/output/temperature/concurrency limits are not
verified or changed. This repository task does not configure the active model.

Constraints: userspace only; no flash, kernel, partition, bootloader, EFS/radio
changes; exclusive serial ownership; never open /dev/fb0 for diagnostics.

Measured live at 2026-10-18 23:01 CEST: console /dev/cu.usbmodem1201 selected by
VID/PID/serial and verified frames. Boot 2efd316a-3c15-441d-ae9d-54cd9b30aacd.
One phoc, one nuxel-pwa-host, one nuxel-wl-fb (sole fb0 owner), touch-arm and button
manager active; no previous owner-capture service active. sec_touchscreen is
event2; Phoc holds it. The old app.js hash matched eea79e, but current source
had additional app-frame observation and Home-bar repairs. Eight PWA baseline
paths differed/missing. Existing launcher.js matched the dock-bug source.
No local Cyber-Tiel/llama/MLX/Ollama/vLLM process was found. Requested inference
ceilings remain unverifiable without a running server endpoint.
