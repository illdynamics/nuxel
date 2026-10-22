# A50 — 05: A/B benchmark results

Only the **E0 baseline** was executed on the live device. No experimental
modification (E1–E7) was applied, because every promotion-eligible change would
have required either (a) rebuilding an uncommitted newer-than-repo binary, or
(b) a visual/readability change that cannot be verified without physical
access. Results are recorded honestly as `NOT_RUN` with the blocking reason.

| Experiment | Independent variable | Status | Result / blocking reason |
|---|---|---|---|
| E0 | Baseline (current build) | **RUN** | `blit_avg_ms` 74–79 ms; `fps_1s` 8–25; 93 % present-skip; ~86 % of one core graphics stack; 13 FPS full-change ceiling |
| E1 | Bridge hot-loop / NEON upscale | NOT_RUN | live binary source not in repo (newer than a34); rebuild would regress damage-skip |
| E2 | Screencopy/buffer reuse | NOT_RUN | already largely present in live build (copy_with_damage + present-skip); no source to safely iterate |
| E3 | UI gesture/layout changes | NOT_RUN | identified candidates (`backdrop-filter` blur, asset sizes, `void grid.offsetWidth`) need owner visual A/B |
| E4 | Warm-app lifecycle | NOT_RUN | requires unlocking + app-launch instrumentation; no physical interaction available |
| E5 | 720/1080/native/540 buffer trials | NOT_RUN | needs phoc restart + owner readability A/B; 720 is already deployed |
| E6 | 30/45/60 FPS cap | NOT_RUN | full-frame work is 74–79 ms; raising target FPS cannot help, lowering is already implicit |
| E7 | Idle/wake scheduling | **effectively already present** | `DISPLAY_SLEEP capture=stopped`, bridge 0.1 % CPU screen-off |

## Honest headline
The current build already contains the single most valuable optimisation for
this architecture — **damage-driven present-skip** (93 % of captured frames do
not touch the panel) and **screen-off capture-stop** (bridge goes quiet when
the panel is off). What remains is the irreducible cost of *changed* frames on
an all-software (no-DRM) stack: ~74–79 ms → ~13 FPS.
