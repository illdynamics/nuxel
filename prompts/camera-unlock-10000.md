# 🐧🔓📸 NUXEL A61 — CAMERA ESCAPE + PENGUIN UNLOCK RECOVERY

Read `./NUXEL-A61-OPERATION-PENGUIN-EYES-AND-UNLOCK-RECOVERY-UBERPROMPT.md` **completely** and execute it on the **current Nuxel source and physical Galaxy S10+** in its exact phase order.

The owner currently has two critical regressions:

1. **The camera app starts loading forever and traps the user.** Fix the custom Nuxel Camera UI to render immediately and always permit Back, Close and Penguin Home, including when physical camera capture isn't supported. Install/repair real native GNOME Snapshot and make it launchable and escapable as well. Diagnose the Exynos camera pipeline honestly: hardware enumeration is not proof of working frames.
2. **The beautiful penguin lockscreen no longer unlocks on upward drag.** Restore the previous working gesture, trusted authoritative session-unlock handoff and focus restoration. Preserve lockhead art/position/wiggle. Never fake an unlock by merely hiding the UI or expose an unrestricted unlock API.

**Do the lockscreen first, camera escape second, camera apps third, and read-only hardware diagnostics last.** Establish verified USB console/rollback before changing any lock manager or app shell. Preserve the existing Nuxel boot path, keyboard, Wi-Fi, launcher, SnekByte and user media. Test every change on the actual phone, including lock/wake, app hung/loading, Home/Back, service restart and an owner-approved reboot.

No kernel/partition flashing, no camera spoofing, no unrelated UI redesign, no unauthorized reboot. Report actual evidence, exact blockers and rollback instructions. Do not declare hardware camera success without a genuine sensor-produced frame.

**OPERATION PENGUIN EYES & UNLOCK RECOVERY — FIX THE TRAP, FREE THE PENGUIN! 🐧🔓📸🔥**
