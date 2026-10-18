# TOUCH COORDINATE MAPPING — A34

Measured chain:

```
sec_ts ABS_MT_POSITION_X/Y   0..4095
        │  libinput normalises
        ▼
phoc headless output         720 × 1520 physical output pixels, scale 2
        │  ÷ 2
        ▼
WebKit CSS viewport          360 × 760 CSS px, devicePixelRatio = 2
        │
        ▼
DECON panel                  1440 × 3040 physical pixels
```

The tap at CSS `(155,235)` hit the Mail tile in the launcher grid. The same tap
produced the correct app:launch; there is no horizontal inversion, vertical
inversion or offset large enough to miss a 64px tile. `dpr=2` and
`innerWidth=360` / `innerHeight=760` were reported by the diag script.

The coordinate map used by `nuxel-touch-trace` is therefore:

```
logical_x = raw_x * 720 / 4095 / 2
logical_y = raw_y * 1520 / 4095 / 2
```

with no rotation and no safe-area offset for the raw device (safe-area padding
is a launcher layout concern, not an input transform).

## Verdict

Coordinate mapping **PASS for the correlated tap**. The top-left / centre /
bottom-right corner test is still requested from the owner to rule out a
nonlinear panel/controller calibration.
