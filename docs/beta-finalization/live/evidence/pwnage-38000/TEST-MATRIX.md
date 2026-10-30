# PWNAGE-38000 test matrix

| Test ID | Output | Device/adapter | Precondition | Action | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|---|---|---|---|
| SPK-1 | Built-in speaker | internal CS35L41 x2 | route service applied; PipeWire default sink | bridge `audio.test-audio` | stream linked to default sink; sound audible | stream linked; `played=true`; audibility unverified | Software PASS / Audibility NEEDS_OWNER_TEST | 04-pipewire-and-bridge.txt |
| VOL-1 | Speaker volume | PipeWire default sink | cap 25 % | `audio.set-volume` 10/15/25 | sink volume changes and reads back | 10/15/25 read-back | PASS | 04 |
| MUTE-1 | Speaker mute | PipeWire default sink | unmuted | `audio.set-muted true/false` | muted then unmuted | `true` then `false` | PASS | 04 |
| CUE-1 | Volume feedback | PipeWire pulsesink | normal sound mode | `nuxel-sound-cue volume --level 20` | `player_ok`, output pipewire | `player_ok`, output pipewire, audible unverified | PASS (software) | 04/08 |
| BT-1 | Bluetooth | BCM43xx adapter | no paired device | `bluetoothctl show` / devices | adapter powered | powered, no devices | Not runnable without accessory | 07 |
| HP-1 | Wired headphone | madera-extcon | none inserted | extcon HEADPHONE | route Headphones | HEADPHONE=0 (none inserted) | Not runnable without accessory | 06 |
| USB-1 | USB-C UAC DAC | none attached | no UAC card | hotplug UAC | new card + sink | no accessory attached | Not runnable | 06 |
| HDMI-1 | USB-C HDMI audio | none attached | no DRM | connect DP display | audio endpoint | CONFIG_DRM not set, no /sys/class/drm | BLOCKED (kernel config) | 06 |

## Audibility rule

Only a human listening test can turn a software `played=true` into audibility.
Every software-only row above records `audible=unverified` and is not counted as
a physical pass.
