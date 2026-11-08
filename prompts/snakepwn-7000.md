# 🐍💩⚡ NUXEL A58 — SNAKEPWN 7000 LAUNCHER

Read `NUXEL-A58-SNAKEPWN-7000-BUTTER-SNEK-UBERPROMPT.md` **completely**, then execute its phases in order against the **current working SnekByte source**.

The game already works. Do **not** rebuild it from scratch or regress Android/Nuxel support.

**Top goals**:
1. Adjustable, persistent speed that truly updates while the game is running.
2. Infinite wraparound at all four board edges (right→left, left→right, top→bottom, bottom→top), ON by default, while self/poop collisions still kill.
3. Fix delayed controls at the event level: D-pad on pointerdown, swipe recognized on pointermove, a short deterministic direction queue, and no impossible reversals.
4. Preserve WoNQ Mode, five-food Poop-o-meter, original icon, offline play, scores, assets, Nuxel PWA, and existing Android app identity.
5. Add regression tests, optimize tick/render loops, rebuild a genuine Android APK update, deploy updated Nuxel PWA, and report real device acceptance with rollback instructions.

Historical clues: A56 `js/snekbyte.js` used `pointerup`-only swipes, D-pad `click`, one-turn-per-tick drops, and a settings snapshot that delayed speed changes. A56 `js/snek-engine.js` killed the snake on boundary crossing. **Verify the actual newer code first.**

No OS/kernel/partition modifications. Don't erase scores. No invented tests or APK. Proceed to implement and verify now.

**SNAKEPWN 7000 — FREE THE SNEK! 🐍💩⚡**
