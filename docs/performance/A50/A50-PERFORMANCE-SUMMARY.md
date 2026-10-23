# A50 — Performance summary (one page)

## Verdict
**`IMPROVED_BUT_LIMITED`** — the current build already ships the two most
valuable optimisations for this architecture (damage-driven present-skip and
screen-off capture-stop). Remaining smoothness is hard-limited by an
all-software (no-DRM/GPU) display path; no safe userspace change within this
mission's constraints removes that ceiling.

## Measured truth (live SM-G975F, read-only)
- Compositor: phoc headless/pixman **720×1520 scale 2** (already "720p-class").
- Panel: native **1440×3040**; bridge 2× upscales + XRGB→ABGR converts + `FBIOPAN`.
- **`blit_avg_ms` = 74–79 ms per changed frame → ~13 FPS ceiling** (30 FPS budget
  = 33.3 ms; 60 FPS = 16.7 ms — both impossible).
- Present-skip: **93 %** of captured frames skipped (idle content is cheap).
- Screen-off: bridge `capture=stopped`, 0.1 % CPU, panel powered down, cool.
- Graphics stack CPU (screen-on, locked): phoc 31 % + WebKit 28 % + bridge 21 %
  ≈ 86 % of one core.

## What was NOT changed (and why)
- No binary/graphics change: live `nuxel-wl-fb` is an **uncommitted build newer
  than repo a34**; rebuilding from a34 would regress damage-skip + screen-off
  capture-stop.
- No visual PWA change (`backdrop-filter` blur, asset resize): cannot be
  verified visually without physical/camera access; visuals must be preserved.
- No flashing, kernel/governor/sysctl/bootlogo change, no reboot.

## Remaining best levers (documented, not applied)
1. Recover live bridge source → NEON upscale/convert (~10–15 ms/frame).
2. Remove software `backdrop-filter` blur (owner visual A/B).
3. Resize 1 MB+ nav/dock PNGs to viewport size.
4. Optional 720→540 compositor A/B (owner readability call).
5. Long-term: kernel 6.x DRM + Mali/panfrost + wlroots gles2 (see
   `A50-FUTURE-RENDERER-MIGRATION.md`).

## Honest bottom line
60 FPS is not achievable on the current framebuffer architecture. The measured
ceiling is ~13 FPS for continuously-changing full-screen content, and the
current build already delivers the smoothest stable achievable idle UX through
damage-skip. The largest remaining gains require the uncommitted bridge source
(NEON), a visual A/B of software-rendered blur/asset changes, or a future
kernel/GPU migration.
