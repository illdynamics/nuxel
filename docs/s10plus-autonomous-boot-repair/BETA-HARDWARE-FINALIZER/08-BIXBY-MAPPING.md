# 08 — BIXBY / ASSISTANT BUTTON → NUXEL TERMINAL

**Status: implemented, deployed, key code measured, mapping changeable from Settings and
from the console.  The physical press confirmation is the user’s (see 11).**

## 1. The physical key, measured (not assumed)

```
$ nuxel-button-manager --probe | grep -A2 gpio_keys
/dev/input/event1 name=gpio_keys bus=0019 vid=0001 pid=0001
    EVIOCGBIT(EV_KEY) rc=96 keys: 114 115 116 703
```

`703` (0x2BF) is the Samsung assistant key; it is the only key in the bitmap above
`BTN_MISC`, it is decoded both by the kernel bitmap in `/proc/bus/input/devices` and by
the tool’s own `EVIOCGBIT` walk (they agree — see
`tests/input-bitmap-decode.py`), and the manager logs it as
`ASSISTANT/BIXBY` when it arrives.

## 2. Architecture — logical actions, not hardcoded buttons

```
KEY_SOURCE (evdev code, per device) → LOGICAL_ACTION → APPLICATION_OR_SYSTEM_ACTION
```

Mappings live in `/etc/nuxel/input/buttons.json`:

```json
{ "schema_version": 1,
  "bixby_short": "open-terminal", "bixby_long": "disabled",
  "power_short": "screen-toggle", "power_long": "power-menu",
  "volume_up": "volume-up", "volume_down": "volume-down" }
```

Supported actions: `open-terminal`, `home`, `search`, `settings`, `screen-on/off/toggle`,
`volume-up/down/mute`, `app:<registry-id>` (any app in the launcher’s own registry — the
authoritative list, not a copy), `disabled`, `power-menu`.  Human-readable names come
from the same registry at runtime, so a future phone only needs a new key→source table,
not new logic.

The manager reloads the file within 1 s of a change (mtime poll), so remapping takes
effect **without a reboot or a restart**.

## 3. The Terminal

* Default action for a short Bixby press is `open-terminal`.
* The Nuxel Terminal is a real PTY: `nuxel-pwa-host` calls `forkpty()` and runs `/bin/sh`,
  streams the PTY output into `pwa/nuxel-apps/terminal/` and receives keystrokes back
  through the same host API.  No emulated shell, no canned prompt.
* **One instance only**: `term.open` focuses the existing fullscreen terminal window
  (`TERMINAL_FOCUS_EXISTING`) instead of spawning another shell; `term.close`/window
  destroy kills the child (`TERMINAL_EXIT bytes=…`).
* The terminal page carries a compact on-screen keyboard (letters/digits, space, Enter,
  Tab, Backspace, Ctrl-C, a Ctrl modifier), because this compositor has no system
  keyboard for a touch-only phone.
* Two entry points, both ending in the same window: the hardware key
  (`/run/nuxel-pwa-host.cmd` ← `open-terminal`) and the launcher tile (the page asks the
  host for the single terminal window).

It is honest to state that the original registry contained **no** terminal application,
so this frontend was added *to the registry* under the launcher’s own app model
(`org.nuxel.Terminal`, name/icon/category/dock entry) rather than as a second UI.

## 4. Remapping in Settings and on the console

* **Settings → Buttons & Gestures → Bixby / assistant button**: short and long action
  pickers, populated from the live registry (`app:<id>` entries) plus Home/Search/
  Settings/Terminal/Disabled; also Power short/long and both volume keys.  Saving writes
  the same JSON through the launcher host (validated: allow-listed file name, JSON object
  required, atomic replace).
* **Console**: `nuxelctl buttons list`, `nuxelctl buttons set bixby_short home`,
  `nuxelctl buttons set bixby_short app:org.nuxel.Mail`, `nuxelctl buttons reload`,
  `nuxelctl action open-terminal`.
* No arbitrary shell execution is reachable from launcher content: the host accepts a
  fixed verb set, and `app:` ids are charset-validated before the launcher resolves them.
