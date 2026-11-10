# Nuxel physical pointer settings

`input.json` is the durable settings document for a USB HID mouse or touchpad
connected through the phone's USB-C hub. It is written by **Settings → Mouse &
Keyboard** and by `nuxelctl` when used on the same document.

Consumers, both real:

1. `libnuxel-libinput-path.so` reads the document and applies accel speed,
   accel profile, natural scrolling, left-handed mode, middle-click emulation,
   tap-to-click, two-finger scrolling and disable-while-typing directly to each
   accepted libinput pointer device. This is the path that guarantees a newly
   hotplugged mouse gets the user's values before its first motion event.
2. `nuxel-input-apply.sh` writes the same values to
   `org.gnome.desktop.peripherals.mouse` / `.touchpad` GSettings. Phoc listens
   to those schemas and re-applies them to every pointer, including after its
   own hotplug handling.

The shim writes `/run/nuxel-input.state` (discovered devices + effective
values); the applier writes `/run/nuxel-input-gsettings.state` (GSettings
verdicts). Settings shows both.

Keyboard layout, repeat, delay, interval and physical passthrough are **not**
duplicated here: they live in `/etc/nuxel/keyboard/keyboard.json`, whose
existing `nuxel-keyboard-apply.sh` consumer already writes the XKB input source
and keyboard GSettings that phoc uses.
