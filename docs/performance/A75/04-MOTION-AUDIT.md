# A75 — Motion Audit (existing system, factual)

The launcher motion system is CSS-token/keyframe based. Verified current state:

## Three lockscreen status penguins (distinct, state-bound)
`pwa/nuxel-home/css/lockscreen.css` already implements separate keyframes:
- charging: `nuxel-indicator-charge` 1.45s ease-in-out (scale 0.96↔1.04 + opacity)
- PC-connected: `nuxel-indicator-usb` 3.0s ease-in-out (subtle 1px translateY sway)
- Live Console: `nuxel-indicator-live` 1.9s ease-in-out (rhythmic opacity pulse)
- glow: `nuxel-indicator-breathe` 3.4s (radial gradient opacity/scale)
All use `transform`/`opacity` only; `image-rendering: pixelated`; inactive icons
are `display:none`; `body.display-off` pauses all animation; and
`prefers-reduced-motion: reduce` disables it. Positions/sizes/artwork (A70/A71/
A72/A73) are preserved: `top:184px`, charging 68×68, usb 91×76, live 82×82.

## Other meaningful movements
- Quick Settings open/close, panel expansion, tile press and pending states are
  in `qs.js`/`style.css`; nav-dock press feedback in `launcher.css`; dialog/
  modal and switch transitions in `style.css`/`home-settings.css`. These were
  **not** re-measured frame-by-frame this run.

## Deliberately unanimated (correct)
- Continuous scrolling (native/direct), lockscreen unlock drag geometry
  (direct manipulation), and keyboard typing (must not wait for decorative
  motion).

## Remaining for a full A75 pass
A before/after frame-pacing and touch-to-feedback benchmark (the mission's
baseline section) was not completed in this run; prior baseline captures exist
in `docs/performance/A50` and
`docs/beta-finalization/live/evidence/a75-baseline-20261026/`.
