# POWER MENU — A34

The existing A33/A34 button manager already implements the long-press menu:

* `power_long=power-menu` in `/etc/nuxel/input/buttons.json`.
* Menu entries (from `nuxel-button-fsm.h`, 11 total):
  `cancel`, `lock-screen`, `screenshot`, `restart`, `power-off`,
  `reboot-verbose`, `reboot-safe-mode`, `reboot-diag`, `reboot-debug`,
  `recovery`, `download-mode`. **Cancel is first and initially selected**; its
  action is the internal `menu-close`, not a reboot path.
* Volume Up/Down move the selection; a short Power press confirms.
* `recovery` and `download-mode` have `trigger_allowed=0` and dispatch
  `MENU_REFUSED ... reason=NO_FLASH_INVARIANT`. They never invoke a low-level
  Samsung reboot interface.
* `restart` / `power-off` pass through the reboot gate
  (`/etc/nuxel/buttons/reboot-gate.json`); they request an orderly systemd
  action, never Recovery.
* The menu is rendered by `osd_publish("power-menu", ...)` to
  `/usr/share/nuxel/runtime/osd.json`; the launcher's `osd.js` polls and displays
  it. The current A34 OSD path was verified with a volume action.

Deployed `/usr/lib/nuxel/nuxel-button-manager` SHA-256
`f5f9c6f88c141d667b17772dc59bbe9897271da0718b6e0fb05cc9f2bdfe0ab9`, with
`/etc/nuxel/input/button-fsm.json` SHA-256
`46a90ab9aae0bf641cf7137deaefecdada8919f858d577fc2755f1f0171348aa`.
`--menu-dump` now reports `MENU_COUNT 11`, `ENTRY 0 cancel action=menu-close`.
`--config-check` prints `reboot_gate decide=ALLOW reason=allowed`.

Physical acceptance is still required: long-press Power, use Volume Up/Down,
confirm Cancel / Restart / Power Off, and verify Recovery / Download Mode are
refused. No menu item was triggered in this session.
