# 🐧 NUXEL 23000 — USB UNPLUG PWNAGE KICKSTART

Read and execute the full `./NUXEL-A74-OPERATION-USB-UNPLUG-PWNAGE-23000-UBERPROMPT.md` against my CURRENT Nuxel repo and ACTUALLY DEPLOYED Samsung Galaxy S10+ SM-G975F.

Owner report: **all charging / PC-connected / Live Console penguin indicators now work properly, but unplugging the USB cable from the computer makes the phone hang and reboot.** Diagnose and prove the real failure class first (kernel panic/oops, watchdog, userspace reboot, console teardown race, systemd/udev restart loop, power/PMIC issue, or UI-only hang). Preserve bounded durable on-device logs before the controlled detach, because USB access itself disappears. Inspect pstore/previous-boot logs after reboot if needed.

Trace the entire detach path through UDC/gadget, `ttyGS0`, console service/session/lease, systemd/udev scripts, power-supply events and UI/bridge. Fix the narrow evidenced cause. Treat unplug as normal and idempotent; no reboot command, panic/watchdog suppression, stale icon hack, or kernel flash. Keep the existing 4.14 kernel and all current working icon artwork, sizes, positions, animations, charging/PC/Live Console behavior, Wi-Fi/browser, Bluetooth/Location toggles, lockscreen/navigation and apps intact.

Back up changed files, prove repo-vs-deployed hashes, preserve an alternate recovery path, deploy minimally, run regression tests, then physically verify at least 5 controlled PC unplug/replug cycles without hang/reboot. Prove boot ID stays unchanged and uptime continues. If the first detach reproduces an unlogged hard reset, stop and improve evidence before retrying. Do not claim physical success from mocks. Write the required evidence and `docs/a74/FINAL-STATUS.md`; include tested rollback instructions.

**UNPLUG THE CABLE, NOT NUXEL. 🐧⚡**
