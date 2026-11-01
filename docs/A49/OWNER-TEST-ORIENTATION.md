# A49 Owner test — rotation

**Status: PWNAGE-54000 implemented.** Fixed 0/90/180/270 transforms, geometry and
libinput touch matrices are verified live on `HEADLESS-1`. A physical finger test
is still required on the glass; Auto is hardware-blocked by the SSP sensor hub. Exact labels are now
`Auto (FULL)`, `Auto (PT)`, `Auto (LS)`, `Locked (PT)`, `Locked (LS)`,
`Locked (RPT)`, `Locked (RLS)`.

## Prerequisites
1. Phone booted into Nuxel, USB console reachable, screen on.
2. Confirm the service surface first (do NOT rely on the tile until proven):

   ```sh
   /usr/libexec/nuxel/nuxel-orientationd status --json
   /usr/libexec/nuxel/nuxel-orientationd modes
   cat /run/nuxel-orientation/input.json
   cat /run/nuxel-touch-calibration.state
   ```

   The touch owner is `libnuxel-libinput-path.so` (LD_PRELOADed into Phoc), not
   wlroots: Phoc 0.54 does not rotate `wlr_touch` with the output. The shim
   applies exactly one libinput calibration matrix derived from the verified
   transform and records read-back evidence in the state file.

## 1. Calibrate the accelerometer (Phase 1)
1. `nuxel-sensors-diag.sh watch accelerometer 20` while tilting the phone left,
   right, forward and back; the axis values must change and settle.
2. Record X/Y/Z for the four poses (normal, upside-down, left, right, face-up,
   face-down) and note the sensor identity. If only `ssp_context` hub events are
   exposed (no IIO channels), record that as the exact blocker.
3. Derive the mount matrix + gravity reference from those readings and update
   `orientation.json` (`sensor.mount_matrix`, `sensor.gravity_reference`), then
   set `calibration_status` to `verified` only after a re-run confirms the four
   poses classify correctly (`nuxel-orientationd status`).

## 2. Manual modes
For each fixed mode (`portrait`, `reverse-portrait`, `landscape`,
`reverse-landscape`), `/usr/libexec/nuxel/nuxel-orientationd set <mode> --apply` and:
* confirm the compositor applies the transform (or reports exactly why not),
* confirm `/run/nuxel-touch-calibration.state` reports the same transform and
  `applied=1` with the expected matrix,
* touch all four corners + the keyboard: **hit boxes must match the visuals**,
* check status bar, dock, OSK, a modal dialog and the camera cutout/safe areas,
* if the display blanks or input becomes unusable, the service must auto-revert
  to the last-good transform within the bounded interval — confirm this.

If the compositor cannot apply the transform, STOP and record it as a Phase 3
blocker; do not ship "rotation" that only rotates pixels.

## 3. Auto modes
1. `nuxel-orientationd set auto --apply`, then turn through all four sides and
   confirm the screen follows with ~300–800 ms settle and no flapping.
2. `auto_portrait`: only upright/upside-down, **never** sideways.
3. `auto-landscape`: only the two sideways positions, **never** portrait.
4. Lay the phone flat: orientation must keep the last good pose, not flap.

## 4. UI
1. Home → QS → long-press Rotate: all seven choices must appear; tap toggles
   portrait/auto; the tile shows Auto/Locked + sensor availability.
2. Settings → Display → Screen rotation: seven radio choices, effective
   orientation and calibration status; no cosmetic toggle success.

## 5. Persistence + no regression
Reboot (with permission) and confirm the saved mode is restored. Confirm
lockscreen unlock, navigation, battery/metrics, Wi-Fi and the USB console still
work, and that the lockscreen stays portrait unless its landscape layout passes
full touch/non-overlap tests.

## PWNAGE-54000 live closure (2026-11-01)

### Recovered working path
The successful path is the one already present in the repository:

```text
nuxel-orientationd -> wlr-randr -> Phoc HEADLESS-1
0 -> normal, 90 -> 270, 180 -> 180, 270 -> 90
portrait scale 2 (360x760 logical), landscape scale 1 (1520x720 logical)
```

The active output is discovered at runtime (`HEADLESS-1` today), never assumed.

### Framebuffer-level proof
A raw `/dev/fb0` capture was compared with a Phoc `grim` capture for every pose.
The correlation result proves the glass-side orientation:

| Pose | RFB/logical | framebuffer vs grim |
|---|---|---|
| Locked (PT) 0° | 360x760 | direct match, corr 0.998 |
| Locked (LS) 90° | 1520x720 | fb rotated 90°, corr 0.999 |
| Locked (RPT) 180° | 360x760 | fb rotated 180°, corr 1.000 |
| Locked (RLS) 270° | 1520x720 | fb rotated 270°, corr 0.999 |

This is the expected relationship: the panel scanout is physically portrait,
so a landscape pose presents the landscape logical frame rotated by the image
viewer's physical 90° pose.

### Touch
`libnuxel-libinput-path.so` applies one libinput calibration matrix selected from
the live compositor transform. The matrix corner math is unit-tested and matches
the conceptual mappings `(x,y)`, `(1-y,x)`, `(1-x,1-y)`, `(y,1-x)`. Read-back is
in `/run/nuxel-touch-calibration.state`. A physical finger test is still the
owner's final acceptance step; it cannot be replaced by these captures.

### Quick Settings behavior
Short tap now rotates 90° through the four **Locked** poses. It never selects
Auto. Long-press/context-menu exposes all seven exact labels. A selected Auto
mode with no live sensor is rendered as degraded (amber), not green.

### Remote sessions
VNC follows the real Phoc session. When the sequence changes, the remote-sync
helper calls `wayvncctl detach` + `attach wayland-0` + `output-set <discovered-output>`, which re-reads the current transform and updates RFB ServerInit/DesktopSize without restarting wayvnc or dropping the client. XRDP sessions are updated per display with
`xrandr`; xorgxrdp's unsupported native rotation is reported honestly and never
forces a logout or session restart.


## PWNAGE-55000 Auto start test

Before testing Auto, run:

```sh
sudo /usr/libexec/nuxel/nuxel-orientationd sensor --start --json
```

`hub_start.streaming` must be `true` before any Auto angle claim is valid. On
the current S10+ image it is `false` with `reason` naming the absent Android
`lhd`/Bionic runtime, while `raw_data` stays `0,0,0`; Auto is therefore
`blocked_sensor_unavailable`. This is a hardware/userspace-runtime blocker, not
a saved-preference success and not a simulated sensor.
