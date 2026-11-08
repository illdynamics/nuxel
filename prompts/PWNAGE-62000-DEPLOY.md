# PWNAGE-62000 — Safe Wi-Fi SSH Deployment and Rollback

**Target:** `root@10.20.30.16` (S10+ `beyond2lte`, WiFi `wlan0`)  
**Key:** `$HOME/.ssh/wicked_wqn_id_rsa`  
**Final backup:** `/var/backups/nuxel/p62000-20261103T080758Z`  
**Backup manifest:** 38 files, `sha256sum -c SHA256SUMS --quiet` verified  
**No kernel/DTB/BOOT/modem/partition writes are performed.**

## 1. Exact deploy command

```sh
cd /x/nuxel
SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
  tools/pwnage62000/deploy-pwnage62000.sh root@10.20.30.16
```

The script:

1. verifies the target is aarch64/Fedora and has `nuxel-pwa-host`;
2. creates `/var/backups/nuxel/p62000-<UTC stamp>/`;
3. copies every target that will be replaced and writes a self-excluding
   `SHA256SUMS`;
4. stages only userspace sources/PWA/systemd files;
5. builds `nuxel-navdock`, `nuxel-statusbar`, `nuxel-foreign-toplevel`,
   `nuxel-pwa-host`, `nuxel-button-manager` on the target;
6. atomically installs binaries, helpers, drop-ins, PWA assets and the guarded
   PWN36000 bootstrap/stage preload copy;
7. `daemon-reload`, `systemd-analyze verify`;
8. restarts `nuxel-http-bridge`, `nuxel-button-manager`, `nuxel-wayland`, then
   `nuxel-wl-fb`, and waits for a real `FRAMES_OK` receipt plus chrome readiness;
9. runs health checks, including live foreign-toplevel enumeration and the
   WLAN-readiness-vs-session assertion.

It **never reboots automatically**.

## 2. Recorded backup

```sh
/var/backups/nuxel/p62000-20261103T080758Z
cat /run/nuxel-p62000-backup-dir
cat /run/nuxel-p62000-deploy.json
```

The backup contains the pre-mission binaries, configs, units/drop-ins, PWA files
and the pre-fix stage copies. It is intentionally not updated with post-deploy
hotfixes; rollback therefore returns to the pre-mission state.

## 3. Exact rollback

```sh
ssh -i "$HOME/.ssh/wicked_wqn_id_rsa" \
  -o BatchMode=yes -o StrictHostKeyChecking=yes root@10.20.30.16 \
  '/usr/lib/nuxel/rollback-pwnage62000.sh \
   /var/backups/nuxel/p62000-20261103T080758Z'
```

The rollback:

- restores prior binaries, helpers, units/drop-ins, preload controller and PWA assets
  from the timestamped backup only;
- restores the pre-mission stage preload/bootstrap copies;
- removes mission-only helpers/drop-ins that were absent from the backup after
  proving they are PWNAGE-62000 files;
- daemon-reloads and restarts only `nuxel-http-bridge`, `nuxel-button-manager` and
  `nuxel-wayland`;
- never removes user data, app data, Flatpak state, SSH keys, `authorized_keys`,
  `known_hosts` or unrelated settings.

If the display/chrome is broken after rollback, the old Home DOM bar/dock remains
the fallback; the rollback does not flash or alter boot partitions.

## 4. Health checks after deploy/rollback

```sh
ssh -i "$HOME/.ssh/wicked_wqn_id_rsa" root@10.20.30.16 '
  systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-http-bridge \
    nuxel-button-manager nuxel-bridge
  systemctl show nuxel-wayland.service -p TimeoutStopUSec -p ExecStop --value
  systemctl show nuxel-wl-fb.service -p TimeoutStopUSec -p ExecStop --value
  systemctl show nuxel-audio-session.service -p TimeoutStopUSec -p ExecStop --value
  cat /run/nuxel/shell-chrome.json
  cat /run/nuxel-navdock.json
  cat /run/nuxel-statusbar.state
  cat /run/nuxel/foreground.state
  cat /run/nuxel/lock-enforcement.state
  XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
    /usr/lib/nuxel/nuxel-foreign-toplevel list
'
```

Expected: `2s` + helper ExecStop for wayland/audio, `5s` + hold helper for wl-fb;
one Home toplevel; navdock/statusbar state files present; lock fails closed.

## 5. Reboot policy used

The final validation used a normal, non-forced command over verified WiFi SSH:

```sh
printf 'source=owner-wifi-ssh ...\n' > /run/nuxel/reboot-request
systemctl --no-block reboot
```

No `reboot -f`, `systemctl reboot --force`, SysRq, `kill -9 1`, global timeout
slash or boot-image write was used. The beta USB-serial verifier is
`BLOCKED_EXTERNAL_RESOURCE` (no CDC-ACM gadget); WiFi SSH was the recovery channel.
The beta `reboot-policy.sh pre --run` checklist has a known bug (it executes prose
labels), while plan mode and policy `check` pass.

## 6. Post-deploy hotfixes applied during this run

The deployed tree was validated and then hot-installed with the same source hashes
for these late fixes (all now included in the deploy script):

- corrected foreign-toplevel `NULL` new-id interface / seat events / enum;
- new preload controller in live **and** stage36000 paths;
- guarded PWN36000 preload bootstrap;
- `nuxel-audio-stop.sh` + 2 s audio drop-in;
- navdock readiness/lock state republishing.

This means the **next** clean run of `deploy-pwnage62000.sh` installs the complete
set in one pass.
