# REPORT-PWNAGE-103000 — USB-C hub mouse and keyboard

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Live access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`  
**Path:** USB-C hub → DP Alt Mode → HDMI (unchanged) + USB HID mouse/keyboard  
**Run:** 2026-11-09 20:00–20:20 CET  
**Status:** `MOUSE_FIXED_LIVE`; `KEYBOARD_INPUT_PATH_FIXED_LIVE`; keyboard hardware on hub port 3 is `BLOCKED_USB_ENUM` (see §F)

---

## A. Symptom

The external HDMI picture through the USB-C hub was already correct. The USB
mouse and keyboard attached to the same hub did nothing in the Nuxel UI.

## B. Root cause (input stack)

`libnuxel-libinput-path.so` is the discovery shim used because `systemd-udevd`
cannot run on this 4.14 kernel. It scanned `/dev/input` but accepted **only**
`INPUT_PROP_DIRECT` touch surfaces. Every mouse/keyboard event node was rejected
with:

```
reject: INPUT_PROP_DIRECT absent (not a touch surface)
```

The kernel already enumerated the Razer mouse and its HID interfaces; Phoc
simply never received them. The old `HOTPLUG_ADD` lines in
`/run/nuxel-libinput-path.state` show the three Razer nodes being rejected.

A second defect was exposed while testing replug: the old tracked-device table
deduplicated by **product name**, so the mouse pointer interface and the two
Razer keyboard interfaces (same product string) could not all be tracked. The
old removal path also called `libinput_path_remove_device()` from inside
`libinput_dispatch()`, which crashes libinput 1.30 on this device (SIGSEGV in
`libinput_path_remove_device`, coredumps 38699/40783/43784).

## C. Fix (input stack only; no display code changed)

`tools/s10plus/a33/nuxel-libinput-path.c` (and the byte-identical A31 copy):

- **Pointer acceptance:** `REL_X` + `REL_Y` + a real button (`BTN_LEFT/RIGHT/
  MIDDLE`), or `ABS_X/Y` + a real button. This accepts USB mice and touchpads.
- **Keyboard acceptance:** at least 10 keys from the standard letter block
  (Q..P, A..L, Z..M). This accepts USB HID keyboards and their media-key
  interfaces, while gpio_keys, the headset button node, hall/sensor nodes and
  the panel's non-DIRECT `sec_touchpad` emulation node stay rejected.
- **Touch path unchanged:** a DIRECT multitouch panel is still selected by the
  same capability test and remains the only device that receives the
  orientation calibration matrix. Mouse/keyboard devices never get it.
- **Accurate udev entries:** non-touch nodes are tagged
  `ID_INPUT_MOUSE`/`ID_INPUT_KEYBOARD` (and `ID_INPUT_TOUCHPAD` when named as
  one); `ID_INPUT_TOUCHSCREEN` is now gated by the touch kind.
- **Per-node/inode tracking:** entries are keyed by event node and devtmpfs
  inode, not product name. A hub re-enumeration that reuses `eventN` is handled
  as a replace, and a late removal cannot delete the new entry.
- **No unsafe remove:** the shim no longer calls
  `libinput_path_remove_device()`; libinput's path backend tears down the dead
  fd itself. The handset proved this by closing the old mouse/keyboard fds
  after a hub reset while Phoc stayed alive.
- **Idle hotplug wake:** an `eventfd` is registered as a Wayland event source via
  `wl_display_get_event_loop()`. The inotify watcher wakes the compositor and
  the queue is drained on the compositor thread outside `libinput_dispatch()`,
  so a replug is added even when the screen is idle. Adds are retried 8 times
  (200 ms → 1.6 s) to cover USB enumeration.
- **Pointer settings:** `nuxel-input-apply.sh` + a `.path` unit apply
  `/etc/nuxel/input/input.json` to `org.gnome.desktop.peripherals.mouse` and
  `.touchpad`; the shim also applies the same values directly to libinput.

## D. Settings panel

Added **Settings → Mouse & Keyboard**:

- Connected physical devices and the two consumer verdicts
  (`/run/nuxel-input.state`, `/run/nuxel-input-gsettings.state`).
- Mouse: speed, acceleration profile, natural scrolling, left-handed buttons,
  middle-click emulation.
- Touchpad: speed, acceleration, natural scrolling, tap-to-click, two-finger
  scrolling, disable-while-typing, left-handed buttons.
- Physical keyboard: layout, key repeat, delay, interval and passthrough. These
  write the existing `/etc/nuxel/keyboard/keyboard.json`, whose existing applier
  reaches Phoc's XKB/repeat settings. No second keyboard document was created.

`nuxel-pwa-host` was rebuilt from the repository A45 source so `config.get`,
`config.set`, `input-state` and `input-gsettings-state` are whitelisted. The
new Settings HTML/model/JS were deployed to
`/usr/share/nuxel/pwa/nuxel-apps/settings/`.

## E. Validation (live)

| Check | Result |
|---|---|
| `nuxel-wayland`, `nuxel-displayd`, `nuxel-wl-fb-ext` | active |
| External display state | `RUNNING ... color=argb orient_eff=0 orient_tf=0`, frames increasing |
| HDMI/DP source code | **not changed** |
| Shim scan | `event12` pointer, `event13`/`event14` keyboard, touch `event2` |
| Phoc open fds | `/dev/input/event2`, `event11`, `event12`, `event13`, `event14` |
| `/run/nuxel-input.state` | `pointer_devices=2 keyboard_devices=3 touch_devices=1 verdict=READY` |
| Hub reset (real USB re-enumeration) | mouse/keyboard interfaces re-added; Phoc PID unchanged; no Phoc coredump |
| Transient keyboard hotplug (uinput) | `HOTPLUG_ADD ... kind=keyboard accepted=1`; Phoc opened it; removal closed the fd |
| Touch calibration | still applied only to `sec_touchscreen`; no matrix on mouse/keyboard |
| Settings web assets | served; `data-tab="mouse"` present; pwa host has the input whitelist |
| Pointer GSettings applier | `verdict=APPLIED`; readback verified |
| Offline gates | `run-touch-tests.sh`: **ALL PASS** (shim fixtures, parity, invocation, physical-input, touch tracer, boot guard, no-eventN gate) |

The deliberate `nuxel-wayland` restarts during deployment produce a shutdown
SIGSEGV/SIGBUS coredump from Phoc; these are teardown-only. The final running
session (Phoc PID 59519 at the time of this report) stayed alive through the
real hub reset, the re-add of all five event nodes, and the transient keyboard
hotplug, with no new Phoc coredump after the last deliberate restart.

Rollback files: `/root/nuxel-input-backup-20261109T200048/` (shim, pwa host,
Settings tree, previous input document if any).

## F. Keyboard hardware finding (not the input stack)

The separate keyboard is electrically present on hub port 3 but never
enumerates. Live `dmesg`:

```
usb 1-1.3: new full-speed USB device number 61 using xhci-hcd
usb 1-1.3: Device not responding to setup address.
usb 1-1.3: device not accepting address 61, error -71
usb 1-1.3: device descriptor read/64, error -32
usb 1-1-port3: unable to enumerate USB device
```

This happens before Linux input exists, so no libinput/Settings change can
accept the device yet. Tried and ineffective:

- USBDEVFS reset of the USB2 hub (mouse re-enumerated; keyboard failed again)
- `usbcore.old_scheme_first=Y`, autosuspend disabled
- deauthorizing the 288 mA Ethernet adapter and/or the 500 mA-declaring mouse
  to free power budget
- power-cycling hub port 3 through the hub reset path

The port consistently reports 12 Mb/s, then fails descriptor/address setup.
Recommended next step (hardware): move the keyboard to another downstream hub
port (port 1 or 4), connect it directly to the phone's USB-C port, or use a
powered/PD-passthrough hub. Once the kernel enumerates it, the new shim accepts
it automatically and it appears in Settings → Mouse & Keyboard. This is the
same path proven by the Razer mouse and by the transient keyboard hotplug test.

## G. Files changed

- `tools/s10plus/a33/nuxel-libinput-path.c` (+ byte-identical A31 copy)
- `tools/s10plus/a33/nuxel-input-apply.sh`
- `tools/s10plus/a33/tests/test-physical-input.py`
- `tools/s10plus/a33/tests/test-libinput-path-fixture.py`
- `tools/s10plus/a33/tests/fixtures/usb-hid/`
- `tools/s10plus/a33/tests/run-touch-tests.sh`
- `configs/nuxel/input/input.json`, `README.md`, service and path units
- `pwa/nuxel-apps/settings/index.html`, `settings-model.js`,
  `physical-input-settings.js`
- `tools/s10plus/a33/nuxel-pwa-host.c`, `tools/s10plus/a45/nuxel-pwa-host.c`

## H. Live deployment

Installed the rebuilt AArch64 shim, pwa host, input document, applier and units;
enabled `nuxel-input-apply.path` and `.service`; restarted only
`nuxel-wayland.service`; re-started the external display bridge with its
unchanged unit. The HDMI path, colour format, orientation handling and hotplug
code were not edited.
