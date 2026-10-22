# A50 — 04: Changes and safety review

## What was changed
**No persistent device change was made.** The mission was executed as a
read-only inventory + live baseline + root-cause investigation.

The only live action taken was a **reversible screen wake** using the supported
button-manager control FIFO (`printf 'action screen-on\n' >
/run/nuxel-buttons.cmd`) so the display-on pipeline could be measured. The wake
path is exactly what a physical power short-press / `nuxelctl` / the launcher
uses. The 60 s idle timer subsequently returned the panel to its original
screen-off state (`DISPLAY_SLEEP display=off capture=stopped`, `bl_power=4`,
`brightness=0`), which was verified.

## Why no binary/graphics changes were deployed
1. **`nuxel-wl-fb` is an uncommitted build newer than repo a34.** Rebuilding
   from a34 (the newest committed source) and deploying it would **regress**
   the already-shipped damage-skip (`present_skipped`) and screen-off
   capture-stop (`DISPLAY_SLEEP capture=stopped`) behavior. This is exactly the
   regression the prompt warned about ("deployed binary may not equal
   repository source"; "do not overwrite newer fixes with old A34 artifacts").
2. The highest-value safe lever (removing software-rendered `backdrop-filter`
   blur; resizing 1 MB nav-button PNGs) changes **visual appearance**, which
   cannot be verified without physical/camera access. Per the prime directive,
   visuals must be preserved and changes proven on the real device — so they
   are documented as recommendations, not applied unattended.
3. No kernel, governor, sysctl, bootlogo, flashing, or reboot changes were
   made. The `schedutil` governor and thermal protections are untouched.

## Invariants re-verified
- Single framebuffer owner: `nuxel-wl-fb` pid 5399, `stage=LAUNCHER_DISPLAY_OWNER`,
  `ui_writer=1`, lock `/run/nuxel-fb-owner.lock`. No second writer.
- `decon_pan_failed=0` throughout (no commit errors).
- No failed systemd units (`systemctl --failed` empty).
- No service restarts during the session.
- Device returned to screen-off; SoC thermals cool (25 °C floor), battery 21 °C.
