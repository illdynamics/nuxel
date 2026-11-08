# 🐧📸 NUXEL A52 — OPERATION PENGUIN VISION

You are the engineering agent implementing camera support and completing the Nuxel Camera and Photos applications on the Samsung Galaxy S10+ SM-G975F, Exynos 9820, Fedora ARM64.

**FIRST:** Read `./NUXEL-A52-PENGUIN-CAMERA-AND-APPLICATION-COMPLETION-UBERPROMPT.md` **in full**. That document is your authoritative mission specification. Follow its phases and safety requirements, not merely this abbreviated launcher.

**Core outcome:** Real S10+ camera preview, real saved photos, real Photos/Gallery, real playable video when the camera and microphone paths support it, permission controls, persistent settings/files and verified physical-device behavior. Preserve the currently working Nuxel Home, keyboard, lockscreen, navigation, performance improvements, Wi-Fi and USB console.

**Critical technical audit:** An older Camera app used `getUserMedia` + canvas-to-data-URL/localStorage, had front/rear stream-state bugs and lacked working video capture. Its experimental custom “camera portal” used nonstandard methods on the standard portal D-Bus interface. Audit current sources before assuming those historical defects still exist; correct service contracts and file-backed storage as needed.

**Hardware honesty:** Built-in S10+ camera support is unverified. Do not claim a camera works unless actual real moving scene frames from the phone's own sensor are captured and observed. Synthetic test patterns, an external USB webcam, merely seeing /dev/video*, or a working Camera UI do not count as internal camera hardware success. If blocked by kernel, firmware, ISP or device tree, deliver all independently verifiable application/backend work plus a concrete gap report. No fake green statuses.

**Execution:** Dedicated A52 branch/worktree; read-only investigation first; incremental code and automated tests; safe live USB userspace deployment; owner-assisted physical capture/recording tests; explicit authorization for any reboot. NO kernel/boot/recovery/partition flashing, no unlicensed firmware substitutions, no blind hardware register writes, no destructive media migrations. Preserve recoverability and prepare rollback.

**Deliver:** code, tests, audited architecture, hardware inventory, real media pipeline, completed Camera/Photos apps, persistent saves, accurate permissions, deployment/rollback notes, actual proof and an honest final PASS/PARTIAL/BLOCKED table.

**GO GIVE THE PENGUIN EYES! 🐧📸🔥**
