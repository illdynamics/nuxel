# Nuxel v0.5.2-beta completion checklist

This checklist is derived from `task.md`, `task2.md`, and `beta.md`. Historical
hardware-expansion work is preserved, but this release is scoped to the A34
interaction fixes, source/image parity, and reproducible S10+ release path.

## Repository and runtime audit

- [x] Read the A34 touch, WebKit, Phoc, display, button, deployment, and owner-test evidence.
- [x] Inventory current uncommitted work and preserve unrelated/user-authored changes.
- [x] Verify `term_close_window()`, `NuxelLauncherClose()`, host bridge, gesture, SYN_REPORT, and frame-presentation fixes remain in source.
- [ ] Inspect the connected phone when the CDC-ACM console is available; record source-to-runtime hashes without flashing.

## Interaction fixes

- [x] Complete and test app lifecycle states: CLOSED, LAUNCHING, ACTIVE, BACKGROUND, CLOSING, FAILED.
- [x] Ensure closing/Home removes frames, overlays, focus, pointer capture, handlers, and native Terminal surfaces.
- [x] Ensure failed/empty applications stay identifiable and escapable.
- [x] Verify Quick Settings and Home/Back gestures do not leave invisible input interceptors.
- [x] Complete keyboard Shift, symbols, Backspace, Enter, Space, dismissal, Terminal, and search behavior.
- [x] Add regression coverage for app switching, stale surfaces, Terminal reopening, gestures, keyboard, buttons, and frame readiness.

## Image and release parity

- [x] Stage every current interaction asset and keyboard component in the S10+ Fedora rootfs.
- [x] Verify S10+ rootfs contents against current source, including launcher, apps, bridge, Terminal, button manager, and framebuffer bridge.
- [x] Verify the authoritative Samsung BOOT build remains structurally valid without changing/flashing the known-working kernel.
- [x] Make the release workflow pin build and publication to the tagged source SHA and reject VERSION/tag mismatches.
- [x] Preserve the G7 Power build path.
- [ ] Run static, unit/regression, clean-build, and image-content verification gates.

## Version and documentation

- [x] Normalize all active release metadata to `v0.5.2-beta` / `0.5.2-beta` without rewriting historical evidence.
- [x] Update README, CHANGELOG, build/release instructions, capability metadata, and current architecture documentation.
- [x] Complete `docs/beta-finalization/v0.5.2/` evidence and reports with truthful pass/block/not-run results.

## Physical and publication gates

- [ ] Owner confirms: tap Settings, close, open Calendar, Home, Quick Settings open/close, open Terminal, type, close, open another app, Home, with no Power-button redraw workaround.
- [ ] Commit the complete reviewed change set.
- [ ] Create exactly the annotated tag `v0.5.2-beta` at that commit and push commit plus tag.
- [ ] Trigger/observe the `release` workflow for S10+ and verify the published artifacts correspond to that exact commit.

Publication blocker observed on 2026-10-18: the managed workspace denies writes
to `.git` and the configured GitHub CLI token is invalid. These items must be
finished from a Git-writable, authenticated session.

No physical interaction item may be marked complete from synthetic input. No image
may be flashed as part of this checklist.
