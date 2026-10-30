# Power menu regression — root cause (2026-10-30)

Live host: `root@192.168.178.167` over Wi-Fi SSH (`~/.ssh/wicked_wqn_id_rsa`).

## What the owner saw
Long-press POWER showed a short menu, Restart/Power off were "gated", and
Cancel / Reboot Verbose / Safe Mode / Reboot Diag / Reboot Debug / Back /
Forward / Stop / Reload launcher were missing.

## Measured causes (device evidence)

1. **The installed manager was compiled against a mutated FSM header.**
   `nuxel-button-manager --menu-dump` reported `MENU_COUNT 6`:
   lock-screen, screenshot, restart(allowed=0), power-off(allowed=0),
   recovery, download-mode. The repository header
   `tools/s10plus/a33/nuxel-button-fsm.h` has 15 entries with Restart and
   Power off allowed (the gate, not the table, decides). The on-device
   `/root/pwnage-40000/build/nuxel-button-fsm.h` is the one that was used for
   that build; its menu table is the 6-entry variant.
2. **Installed configs drifted.** `/etc/nuxel/power/power-menu.json` said
   `trigger_allowed:false` for restart/power-off, and
   `/etc/nuxel/input/button-fsm.json` was the old 6-entry table, while the
   repository ships the full table.
3. **The Settings power surface could never allow Restart.**
   `ind_gate_allows()` in `nuxel-pwa-host` read only the FIRST LINE of
   `/etc/nuxel/buttons/reboot-gate.json`. That file is pretty-printed, so
   `allow_restart` is never on line 1 → always `reboot-gate-closed`.
4. **Gate state path collided with the manager state file.**
   `STATE_FILE` is `/var/lib/nuxel/buttons` (a regular file) while
   `GATE_STATE` was `/var/lib/nuxel/buttons/reboot-gate.json`, i.e. a file
   below a regular file. `mkdir()` failed, the min-interval record was never
   written, and `/var/lib/nuxel/buttons` could not be a directory.
5. **One-shot reboot flags raced the reboot.**
   `reboot_mode_once()` called `gated_system_action()` (which forks
   `systemctl reboot`) and only THEN wrote the `verbose-once` /
   `safe-mode-once` / `diag-once` / `debug-once` flag, so the flag could be
   lost. `nuxel-bootmode-oneshot.service` additionally had
   `ConditionPathExists=/var/lib/nuxel/boot`, a directory that does not exist,
   so the flags were never consumed at all.
6. **"Take screenshot" did nothing.** The manager forwards `action screenshot`
   to `/run/nuxel-pwa-host.cmd`, but the host had no `screenshot` action and
   replied `unknown-action`.
7. **The Settings Power page was orphaned** (no tab/link from Settings), so
   the power surface was unreachable from the UI.
