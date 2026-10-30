# P2 slow reboot initiation — fix deployed

Root cause:
- Live /usr/lib/nuxel/nuxel-pwa-host was an older (a33) build whose
  `action_perform()` did NOT implement `restart`/`poweroff`. The a45 repo source
  already contained the PWNAGE-35000 fix: fork `systemctl reboot` in the
  background and acknowledge the UI immediately (`{"ok":true,"pending":true}`)
  instead of blocking GTK inside `action_perform` while systemd waited to stop
  the session (the black-screen stall).

Action:
- Cross-checked a45 source tools/s10plus/a45/nuxel-pwa-host.c (already carries
  the fix), compiled it natively on the device in /tmp (gcc + webkit2gtk-4.1),
  produced /tmp/nuxel-pwa-host.a45 (80008 bytes), renamed the busy old binary
  and installed the new one at /usr/lib/nuxel/nuxel-pwa-host.
- Backups:
  /usr/lib/nuxel/nuxel-pwa-host.running-pwnage39000-20261030T120317Z (old inode)
  /usr/lib/nuxel/nuxel-pwa-host.bak-pwnage39000-20261030T120317Z (pre-deploy copy)
- Restarted nuxel-wayland.service; new nuxel-pwa-host PID 10474 running, launcher
  ready, nuxel-wayland + nuxel-wl-fb active.

Verification:
- New binary strings contain restart/poweroff/`{"ok":true,...,"pending":true}`.
- Full reboot-path live verification deferred to the final deliberate reboot
  (no extra reboot was taken to preserve the two-reboot protocol).
