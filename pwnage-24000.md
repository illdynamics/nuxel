# 🐧💥 KICKSTART: NUXEL A75 / 24000 — SMOOTH PENGUIN + NETWORK/RADIO RESTORATION

Read and execute the complete mission in `./NUXEL-A75-OPERATION-SMOOTH-PENGUIN-24000-NETWORK-RESTORE-UBERPROMPT.md` from the current Nuxel repository root. Work against the actual checkout and deployed Galaxy S10+ SM-G975F / beyond2lte; do not assume an old ZIP matches the running phone.

**New critical symptoms to include:** Wi-Fi is now broken and shows the same/similar D-Bus error as Bluetooth and GPS/Location—approximately “no service provider provides Nuxel bridge.” Bluetooth and Location still cannot turn on. Capture the exact error, identify the real system/session bus, service owner, destination name, object/interface/method, activation descriptor, systemd unit, environment and deployed-version match. Fix the proven shared provider/bridge failure if shared; then verify Wi-Fi, Bluetooth and Location against their actual backends. Do not fake toggles or assume GPS fix equals Location enabled.

Priority order:
1. Inspect current checkout/deployed state and establish a safe recovery/rollback path.
2. Diagnose and fix USB detach: PC-connected and Live Console icons clear on real host disconnect, charging stays independent, and unplug never hangs/reboots Nuxel. Prove this with evidence and safe physical testing.
3. Fix D-Bus/Nuxel bridge provider wiring; restore real Wi-Fi scan/connect, IP/route, DNS, TLS and browser behavior.
4. Restore Bluetooth and Location controls through real supported backends, or report exact evidenced hardware/driver/firmware limitations truthfully.
5. Baseline performance; animate all meaningful UI movement consistently and responsively. Give charging, PC-connected and Live Console penguins distinct lightweight state-bound animations while preserving their working artwork, size and position.
6. Optimize measured JS/CSS/rendering/app lifecycle and oversized assets only where evidence shows benefit; preserve transparency and pixel-art quality.
7. Add automated tests, safe rollback, before/after metrics, bridge/network/radio tests and clearly separated physical-device acceptance results.

Do not flash the kernel/bootloader/partitions, disable thermal/watchdog protections, run a second framebuffer writer, blindly mass-upgrade packages, wipe saved Wi-Fi profiles, install a competing network manager, or claim physical success without testing. Do not restart the only network/recovery path without an alternative. If the only recovery channel is USB, do not pull it until a safe owner-supervised plan exists.

Read the entire uberprompt first and follow its gates and deliverables. Make narrow, evidence-led patches. If a test cannot run, label it `NOT_TESTED` or `BLOCKED_HARDWARE` with the reason—never guess.
