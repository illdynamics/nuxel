# configs/g7power/display/ — G7 Power display configuration

Device-keyed display configuration for the Motorola Moto G7 Power (ocean,
XT1955, SDM632 / msm8953). Everything under this directory is G7
Power-specific; nothing here applies to any other Nuxel target.

## Panel (verified hardware facts)

| Role      | Part                                   | Notes                          |
|-----------|----------------------------------------|--------------------------------|
| Panel     | 6.2" IPS LCD, **1520x720** (19:9)      | Portrait scanout 720x1520      |
| Backlight | Texas Instruments **LM3697**           | i2c_5 @ 0x36                   |
| Output    | **DSI-1** (default)                    | Verify on device (`wlr-randr`) |

## Script

* `nuxel-g7power-display.sh` — sets the native 1520x720 portrait mode via
  `wlr-randr --output DSI-1 --mode 720x1520`. Installs to
  `/usr/local/bin/nuxel-g7power-display` (mode 0755) and can be autostarted
  with Phosh (`~/.config/autostart/nuxel-g7power-display.desktop`) or an
  OpenRC "local" hook on the pmOS target.

  The script fails **gracefully** (WARN + exit 0, mirroring the s10plus
  display script's graceful-failure convention): on the UTM VM there is no
  msm8953 panel, and on real hardware the display node may simply not be up
  yet. `wlr-randr` must be present (install the `wlr-randr` package); if it
  is absent the script warns and exits 0.

## Verify on device

The output connector name is **NOT guaranteed** to be `DSI-1` on every
build. Before relying on this script, check the real output name:

```sh
wlr-randr                 # list outputs and their modes on the device
ls /sys/class/drm/        # grep for the card/connector node
```

If the real connector differs, export `NUXEL_DISPLAY_OUTPUT=<name>` and
update the script default once the Phase 0 inventory confirms it. The exact
DDIC/LCM name remains UNKNOWN (only present in the stock vendor tree);
mainline uses the MSM DRM panel driver (Adreno 506 / freedreno,
`CONFIG_DRM_MSM`). See phones/g7power/g7power-requirements.md and
docs/g7power-device-inventory.md.
