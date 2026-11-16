# 🐧⚡ NUXEL A50 — OPERATION SMOOTH PENGUIN (AGENT LAUNCHER)

Read the adjacent file `NUXEL-A50-OPERATION-SMOOTH-PENGUIN-UBERPROMPT.md` **completely**, then execute its phases on my **current Nuxel checkout and actual Samsung Galaxy S10+ (SM-G975F)**. Use DeepSeek-v4-pro-thinking level of investigation.

Mission: make every swipe, tap, Home/Back/Recents action, drawer, keyboard, lock/unlock and application open feel **immediate and butter-smooth**, and resolve avoidable rendering jank with measured performance improvements.

**Important historical clue:** An older build ran Phoc headless/pixman at 720×1520 with scale 2, then used `nuxel-wl-fb` to scale/convert/commit to the 1440×3040 panel at ~24–28 FPS and ~34–43 ms measured blit time. These may have changed. **Verify the live display setup and profile the full pipeline first.** Do not assume lowering resolution helps when compositor resolution may already be 720×1520.

Preserve Nuxel visuals, all working phone features, the live USB recovery console, idle and thermal safety. Use reversible userspace-only modifications, baseline/after benchmarks, focused regression tests and real physical device proof. No flashing, kernel replacement, unsafe performance governor, bootlogo edits, or unapproved reboot. Before changing running graphics, prepare a verified rollback.

**Do not mark done until measurements and live phone tests show the result.** If 60 FPS is impossible on the current framebuffer architecture, report the measured ceiling and deliver the smoothest stable achievable UX rather than cheating metrics.

Start immediately with read-only inventory, environment identity and baseline measurement. 🐧⚡
