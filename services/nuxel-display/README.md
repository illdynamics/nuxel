# Nuxel external display (S10+ USB-C DisplayPort / HDMI)

This service owns Nuxel's **real** external-display path on the Samsung Galaxy
S10+ (`beyond2lte`, Exynos 9820).  The S10+ kernel has no DRM/KMS.  The path
that actually exists is:

```
USB-C connector
  -> max77705 CCIC / USB-PD / DP Alt Mode VDM
  -> exynos-displayport (DP PHY, AUX, link training, EDID)
  -> 19050000.decon_t
  -> /dev/fb1
```

`nuxel-displayd` monitors that path, offers Mirror / Separate desktop once a DP
link is genuinely ready, starts `nuxel-wl-fb-ext` on `/dev/fb1`, and returns to
internal-only on disconnect.  It never opens `/dev/fb0` and never replaces the
Phoc compositor.

## Components

| Component | Purpose |
|---|---|
| `bin/nuxel-displayd` | authoritative state machine, notification generation, mode controller |
| `bin/nuxel-display-ctl` | bounded CLI used by the HTTP bridge / Settings |
| `bin/nuxel-wl-fb-ext.c` | Wayland screencopy -> `/dev/fb1` bridge (mirror / separate output) |
| `bin/build-nuxel-wl-fb-ext.sh` | on-device build (gcc + wayland-scanner) |
| `lib/nuxel_display.py` | pure sysfs model, classification, notification planner |
| `protocol/wlr-screencopy-unstable-v1.xml` | protocol definition used for the build |

## State model

```
DISCONNECTED -> PARTNER_NO_PD -> PD_NO_DP -> DP_NO_FB -> DP_LINK_READY
                                                    -> MIRRORING
                                                    -> SEPARATE_DESKTOP
```

`PARTNER_NO_PD` is important: a Type-C adapter that does not present a USB-PD
identity cannot negotiate DisplayPort Alt Mode (DP Alt Mode uses USB-PD
structured VDM).  A charge-only/passive USB-C-to-HDMI adapter is therefore not
a supported video path, even though the phone reports a Type-C partner.

## Commands

```sh
nuxel-display-ctl status --json
nuxel-display-ctl outputs
nuxel-display-ctl set-mode mirror
nuxel-display-ctl set-mode desktop
nuxel-display-ctl set-mode off
nuxel-display-ctl notify-test
```

`set-mode` only succeeds when the kernel reports a real DP link and the
`decon_t` framebuffer exists.  Separate desktop additionally requires a second
compositor output (`HEADLESS-2`); with the current single-headless-output Phoc
configuration the daemon reports `DESKTOP_OUTPUT_UNAVAILABLE` instead of
pretending.

## Diagnostics

```sh
cat /sys/class/switch/secdp/state
cat /sys/class/extcon/extcon0/state
cat /sys/class/sec/ccic/usbpd_ids /sys/class/sec/ccic/usbpd_type
cat /sys/class/graphics/fb1/modes
cat /run/nuxel-display/status.json
cat /run/nuxel-display/ext.state
journalctl -u nuxel-displayd -u nuxel-wl-fb-ext -b
```

`/sys/class/dp_sec/monitor_info` is only used when a live DP link exists: the
vendor driver also writes the same attribute from its built-in unit-test EDID.

## Safety

* `/dev/fb0` (internal AMOLED) remains owned by `nuxel-wl-fb`.
* `/dev/fb1` has a single-writer flock (`/run/nuxel-fb1-owner.lock`).
* Disconnect stops the external bridge and leaves the phone display untouched.
* No kernel, boot image, DTB, firmware, modem or partition is modified.

## HDMI / DisplayPort audio

The display daemon reports the independent audio capability in
`status.json.audio`, but it does not change PipeWire sinks or defaults.
`nuxel-soundd` owns that policy. On the current S10+ boot the real endpoint is
the Samsung `DP Audio` PCM discovered from `/proc/asound/pcm` (currently
`hw:0,22`), and `/sys/class/switch/ch_hdmi_audio/state` is an EDID-derived
bitmask (live value `0x043b0102`), not a boolean. See
`docs/audio-output-routing-102000.md`.
