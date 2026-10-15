# A16 FIRST LIGHT — physical evidence record

```
MILESTONE_AMOLED_FIRST_LIGHT=PROVEN
MILESTONE_PENGUIN_ANIMATION=USER_OBSERVED
MILESTONE_FIRST_LIGHT_OBSERVED_AT=2026-10-15
CANDIDATE=A16   boot.img sha256 603c2e9a3fd434d451aea0b614fe5978a9ad6178ade6edc1831afc708ee36222
```

## What was seen

The operator photographed the physical Samsung AMOLED panel showing the Nuxel
first-light screen — deep-blue NUXEL frame with the animated (spinning) penguin —
while the phone was running candidate A16.

## Why this is not just a userspace buffer write

The mission forbids equating a userspace write with visible output, so A16 was
deliberately built to leave kernel-side evidence. From the A16 ram console
(`captures/20261015T143625Z-A16-postfail/`):

| Evidence | Meaning |
|---|---|
| `FB_SYSFS bits_per_pixel=32 stride=5760 virtual_size=1440,6080 modes=U:1440x3040p-0` | the fbdev is the real 1440×3040 AMOLED panel, not a stub |
| `nuxel-fb-phone:3316` → `FIRSTLIGHT_ANIMATION_DONE`, `FIRSTLIGHT exit=0` | the one-shot paint completed |
| `nuxel-fb-phone:3342` → `FIRSTLIGHT_ANIMATION_DONE` | the resident `hold` animator started |
| `170.209871 nuxel-fb-phone [decon_wait_for_vsync]` | 162 s later the animator is **blocked inside the DECON's vsync wait** — the only way to get there is a real page-flip/commit against the display controller |
| `decon-0 UNBLANK`, `decon_blank -`, `PANEL:INFO:panel_fb_notifier:UNBLANK`, `panel_set_mdnie`, `dsim_enable` | DECON/DSIM/panel are enabled and being driven |
| operator photograph | the panel output itself |

Kernel-side DECON activity + the operator's photograph = proven visible render.

## What this is NOT

* Not a Fedora phone UI. No service ran (see `A16-POSTMORTEM.md` §4/§6).
* Not proof that the touchscreen works.
* Not proof that a compositor can own the display.

The first-light renderer is preserved unchanged in A17 and later candidates, as
the regression test and as the fallback visual state.
