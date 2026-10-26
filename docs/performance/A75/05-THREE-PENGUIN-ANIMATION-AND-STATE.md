# A75 — Three Penguin Animation and State

Assets (source of truth, unchanged):
- `assets/nuxel-charging.png` (1254×1254 RGBA)
- `assets/nuxel-connected-pc.png` (1374×1145 RGBA)
- `assets/nuxel-live-console-active.png` (1254×1254 RGBA)

State binding is independent (never a shared "USB active" class):
- `.charging-ind.active` (power) and `.charging-ind.active.charging` (real charge)
- `.usb-ind.active` (PC data link)
- `.live-ind.active` (live console session)

Stop conditions:
- animation runs only while the matching `active` class is present;
- `body.display-off` pauses animation;
- `prefers-reduced-motion: reduce` disables it;
- a failed indicator read clears PC/Live `active` (fails closed).

Visual acceptance on device: NOT physically re-observed this run (screen was
off/sleeping); DOM/classes and CSS selectors verified in source and deployed
files. No asset was regenerated or reformatted, so artwork/size/position are
preserved by construction.
