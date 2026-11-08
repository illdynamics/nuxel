# PWNAGE-62000 — KICKSTART THE FULL IMPLEMENTATION

You are working in the Nuxel repository. Read **`full-pwnage-62000.md` from beginning to end** and execute it as the authoritative implementation specification. This is a coding/repair mission, not a request for research notes.

First inspect the current branch, verify the source paths and build/deploy manifests, run the existing relevant tests, and record the baseline. Then implement the full mission in the specified order:

1. Fix compositor-level lock enforcement so an already-running Stremio/GTK/Flatpak app can never cover or receive interaction above the lockscreen.
2. Finish, build, package and start the native top bar over non-Home Wayland apps; diagnose and repair the existing navdock show/FIFO/runtime path so Back / Penguin Home / Tabs remain visible over native apps while unlocked. Keep Home's DOM bar unique and hide normal chrome on lock.
3. Correct the live-console indicator model: background service-ready state drives the base penguin; only real interactive USB-serial / USB-network / WLAN SSH sessions drive transport penguins. Wi-Fi/sshd availability alone must never count as an active WLAN console. Track session close/stale-PID behavior properly.
4. Fix the preload final-frame hang, remove conflicting JSON-versus-shell timing defaults, and split presentation readiness from touch/input readiness so the real locked UI appears promptly without showing a blank or unlocked screen.
5. Diagnose the actual reboot black-screen delay from installed systemd properties, journal timestamps, stop jobs and process/cgroup evidence. Repair only the measured blocker; do not use forced reboot or globally slash stop timeouts.
6. Add regression tests, build/package changes, a PWNAGE-62000 report, deployment manifest and exact rollback procedure.

Use the current repository's canonical sources and tests, not stale backups. Preserve the one-writer `/dev/fb0` rule, lock fail-closed semantics, USB single-owner console, SSH key-only security, known Type-C/DWC3 safety constraints and normal systemd shutdown. Do not weaken Flatpak sandboxing, touch kernel/BOOT/DTB/modem/partitions, or claim physical verification from offline tests.

**Do not stop after the audit.** Make the code changes, run the tests, build the AArch64 native components, integrate them into the real S10+ image/deploy path, and prepare a recoverable Wi-Fi SSH deployment with a timestamped backup and tested rollback. Do not reboot the phone until the existing reachability, rollback and reboot-policy gates pass.

At completion, report exact files changed, commands/results, measured before/after timings, actual lock/chrome and indicator behavior, package/deployment status, physical S10+ evidence, the exact deploy command and rollback path, and every remaining `NOT TESTED` or blocked item. See `full-pwnage-62000.md` for all detailed requirements and acceptance criteria.

