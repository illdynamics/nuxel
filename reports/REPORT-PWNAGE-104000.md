# REPORT-PWNAGE-104000 — Nuxel cyan pointer, live USB keyboard and OSK auto-hide

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Live access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`  
**Path:** USB-C hub → DP Alt Mode → HDMI + USB HID mouse/keyboard  
**Run:** 2026-11-09 20:20–20:58 CET  
**Status:** `POINTER_VISIBLE_CYAN_LIVE`; `KEYBOARD_ENUMERATED_BOUND_LIVE`;
`OSK_AUTO_HIDE_PHYSICAL_KEYBOARD_LIVE`

---

## A. Result

The external mouse pointer is now visible, cyan and Nuxel-branded on both the
phone panel and the HDMI output. The Keychron K5 Max enumerates on the hub,
Phoc holds live event-node fds for it, and the focused-entry keyboard path is
working. Stevia hides the on-screen keyboard while a real keyboard is attached
and still raises it when the hardware-keyboard check is disabled. The Razer
mouse's macro keyboard endpoints and the ydotoold virtual device no longer
count as a physical keyboard.

## B. Mouse pointer

### Root cause

Both framebuffer bridges copied the compositor output with
`zwlr_screencopy_manager_v1_capture_output(scm, 0, output)`. The first argument
is the **overlay-cursor** flag, so every frame the user actually saw excluded
the cursor even though Phoc was tracking it correctly.

### Fix

- `services/nuxel-display/bin/nuxel-wl-fb-ext.c`: `capture_output(..., 1, ...)`
  for the external `/dev/fb1` bridge.
- `tools/s10plus/a33/nuxel-wl-fb.c`: both screencopy calls now pass `1`.
- `tools/s10plus/a67/nuxel-wl-fb.c`: same for the optimized panel bridge source.
- Regenerated `/usr/lib/nuxel/nuxel-wl-fb-ext` and `/usr/lib/nuxel/nuxel-wl-fb`
  from those sources on the phone and restarted both units.

### Nuxel cyan cursor theme

`tools/s10plus/a77/nuxel-cursor-theme.py` generates a dependency-free Xcursor
theme at `/usr/share/icons/nuxel` (79 cursor names, sizes 24/32/48/64/96) using
the launcher cyan palette: `#8BF7FF` → `#00B8DD`, dark-teal outline and cyan glow.
The theme is selected with:

```
org.gnome.desktop.interface cursor-theme = 'nuxel'
org.gnome.desktop.interface cursor-size  = 32
```

`XCURSOR_THEME=nuxel` and `XCURSOR_SIZE=32` are also exported by the Wayland
wrapper and session script for client-side cursors.

### Evidence

- `grim -c` with the pointer parked at the top-left: **924 cyan pixels** at
  `(2,3)`, colour `(133,244,254)` — the Nuxel cursor.
- Same capture after moving the pointer: **0 cyan pixels** in the top-left
  region.
- External `/dev/fb1` after parking the pointer at source `(0,0)`:
  **475 cyan pixels** at the letterboxed origin `(706,3)` — the cursor is in the
  actual HDMI scan-out buffer, not only in the compositor screenshot.

## C. Keyboard

### Enumeration and binding

After the replug the Keychron is a real USB HID device (product `3434:0a50`).
At the final boot it exposed two input nodes:

```
event15  Keychron Keychron K5 Max  kind=keyboard
event16  Keychron Keychron K5 Max  kind=pointer+keyboard
```

Phoc holds live fds for `event15` and `event16`; `libinput list-devices` shows
the Keychron keyboard interface with keyboard capability.

### Stale-udev and USB-grouping fix

The shim previously wrote `/run/udev/data/c13:<minor>` only once. Event node
numbers are reused after a hub reset, so a new Keychron node could inherit the
old Razer `ID_INPUT_MOUSE` tags and be misclassified by libinput. The shim now:

- rewrites the seeded udev entry on every accepted add;
- resolves the full sysfs path with `realpath()` and groups nodes by USB
  product/interface;
- tags a product whose interface 0 is a pointer as
  `NUXEL_INPUT_AUX_KEYBOARD=1` (Razer event13/14), and a real keyboard product as
  `NUXEL_INPUT_HW_KEYBOARD=1` (Keychron event15/16);
- tags Bluetooth/non-USB keyboards through the existing capability fallback.

The final tags are:

```
event12  ID_INPUT_MOUSE=1                              (Razer pointer)
event13  ID_INPUT_KEYBOARD=1 NUXEL_INPUT_AUX_KEYBOARD=1 (Razer macro keys)
event14  ID_INPUT_KEYBOARD=1 NUXEL_INPUT_AUX_KEYBOARD=1 (Razer macro keys)
event15  ID_INPUT_KEYBOARD=1 NUXEL_INPUT_HW_KEYBOARD=1  (Keychron keyboard)
event16  ID_INPUT_MOUSE=1 ID_INPUT_KEYBOARD=1 NUXEL_INPUT_HW_KEYBOARD=1
```

### Keyboard-path proof

A focused GTK3 `Gtk.Entry` was used as the DOM hop. `wtype "abc"` then
`ydotool type "xyz"` produced:

```
ENTRY_TEXT='a'
ENTRY_TEXT='ab'
ENTRY_TEXT='abc'
ENTRY_TEXT='abcx'
ENTRY_TEXT='abcxy'
ENTRY_TEXT='abcxyz'
```

This proves the compositor keyboard group, focus handling and web/GTK text-input
path. The physical Keychron is another live libinput keyboard in that same
group. A 10-second `libinput debug-events --device /dev/input/event15` probe
saw no keypress during the automated run (the user was not typing at that
instant); type on the keyboard to confirm the final hardware hop.

## D. On-screen keyboard auto-hide

### Policy

`mobi.phosh.osk ignore-hw-keyboards` is now **false** (upstream default), both
at boot and from `nuxel-keyboard-apply.sh`. Stevia then uses Phoc's
`zphoc_device_state_v1` keyboard capability to suppress the OSK only when a real
keyboard is attached.

Phoc's `phoc_seat_has_hw_keyboard()` now ignores:

- `BUS_VIRTUAL` devices (`ydotoold` virtual keyboard);
- `NUXEL_INPUT_AUX_KEYBOARD` nodes (mouse macro-keyboard endpoints);

and counts `NUXEL_INPUT_HW_KEYBOARD` nodes (Keychron USB interface 0, or a
capability-fallback non-USB keyboard).

The tap-to-reshow hook from A75 also skips `sm.puri.OSK0.SetVisible(TRUE)` when a
real keyboard is attached, so tapping an already-focused field cannot force the
OSK back over the app.

### Evidence

With the Keychron attached, `phoc-example device-state` reports:

```
Got capabilities: 4
```

A focused `Gtk.Entry` then produced:

| `ignore-hw-keyboards` | OSK `Visible` |
|---|---|
| `false` (physical keyboard policy) | `false` |
| `true` (temporary allow flag) | `true` |
| `false` (physical keyboard policy again) | `false` |

The entry was genuinely focused (`ENTRY_FOCUS_IN` logged) and the `true` result
proves Stevia could raise the OSK; restoring the policy hid it again.

## E. Validation

| Check | Result |
|---|---|
| `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-wl-fb-ext` | all active |
| External bridge | `RUNNING`, frames increasing (20 fps) |
| Phoc input fds | `event2`, `event11`–`event16` live |
| Keychron enumeration | `event15` keyboard, `event16` pointer+keyboard |
| `zphoc_device_state_v1` | `capabilities=4` with Keychron attached |
| Focused-entry keyboard path | `wtype` + `ydotool` produced `abcxyz` |
| OSK with real keyboard | `Visible=false` |
| OSK allow-flag test | `Visible=true` |
| OSK after restoring policy | `Visible=false` |
| Cursor in compositor | 924 cyan pixels at pointer |
| Cursor in external scan-out | 475 cyan pixels in `/dev/fb1` |
| Offline gates | `tools/s10plus/a33/tests/run-touch-tests.sh`: **ALL PASS** |

## F. Incident note (transparent)

While trying to simulate a keyboard unplug, unbinding the Keychron HID
interfaces caused the hub to re-enumerate. A `dwc3` controller reset used to
recover the hub rebooted the handset. After the reboot all USB devices (hub,
Razer mouse, Keychron, Ethernet adapter) returned, the shim re-enumerated every
node, and the final session has been stable. No further unbind/rebind tests were
run; the final auto-hide verification used the focused-entry/allow-flag method
above instead.

## G. Files changed

- `services/nuxel-display/bin/nuxel-wl-fb-ext.c` (capture cursor overlay)
- `tools/s10plus/a33/nuxel-wl-fb.c` (capture cursor overlay)
- `tools/s10plus/a67/nuxel-wl-fb.c` (capture cursor overlay)
- `tools/s10plus/a31/nuxel-libinput-path.c`
- `tools/s10plus/a33/nuxel-libinput-path.c`
  (realpath USB grouping, HW/AUX properties, always-rewrite udev data,
  hotplug re-classification)
- `tools/s10plus/a77/phoc-input-auto-hide.patch`
- `tools/s10plus/a77/build-phoc-input-auto-hide.sh`
- `tools/s10plus/a77/nuxel-cursor-theme.py`
- `tools/s10plus/a77/install-nuxel-cursors.sh`
- `tools/s10plus/a33/nuxel-keyboard-apply.sh`
- `tools/s10plus/a45/nuxel-session.sh`
- `release/s10plus/gpu/nuxel-session.sh`
- `tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh`
- `release/s10plus/gpu/nuxel-wayland-gpu-wrapper.sh`
- `CHANGELOG.md`

Live rollback copies:

- `/root/nuxel-pointer-keyboard-backup-20261109T193923Z/`
  - `_usr_sbin_phoc` (pre-change)
  - `phoc.working-104000` (final working phoc)
  - `shim.working-104000.so` / `.c` (final working shim)
  - session, keyboard-applier and bridge originals
- `/var/backups/nuxel/phoc-input-auto-hide-*` (per-build phoc backups)
