# PWNAGE-37000 🐧 BUTTERSCOTCH BUTTERSMOOTH

The full mega prompt is at ./full-pwnage-37000.dm use it and read it properly.

Take the current Nuxel codebase and perform an aggressive, evidence-driven performance optimization pass focused on making the Samsung Galaxy S10+ feel unbelievably responsive while preserving its 8-bit arcade identity.

**THE VIBE:** pixel-art Linux arcade phone, instant controls, crisp sprites, snappy transitions, playful penguin personality, smooth scrolling, instant Back/Home/Tabs, lightweight rendering, no unnecessary visual bloat.

**THE MISSION:**

1. Profile the real rendering backend and complete UI pipeline. Determine whether Nuxel currently uses fbdev, DRM/KMS, a framebuffer-backed toolkit, a WebView, or another renderer. Optimize the actual implementation.
2. Create a lightweight arcade visual profile: minimize expensive transparency, blur, shadows, glow, filters, layered compositing, excessive animation, and full-screen redraws. Preserve our pixel-art aesthetic, colors, icons, typography, and character.
3. Make touch input, navigation, app switching, scrolling, keyboard interaction, menus, and quick settings respond immediately. Keep slow operations off the UI thread.
4. Optimize rendering for the real hardware: reuse assets, reduce redundant drawing, minimize allocations, avoid unnecessary image decoding, and use efficient damage-region updates or framebuffer operations where supported.
5. Eliminate startup contention, excessive polling, duplicated event handlers, blocking subprocesses, memory churn, unnecessary background work, and other verified bottlenecks.
6. Preserve the Nuxel penguin animations and arcade personality, but make them lightweight, bounded, and nonblocking. Prefer crisp pixel-art motion over resource-heavy visual effects.
7. Add repeatable before/after performance measurements, regression tests, and physical-device verification wherever possible.

**HARD RULES:** Do not replace the graphics stack or kernel just to chase performance. Do not blindly force fbdev if the device currently relies on DRM/KMS or another backend. Do not remove useful features, fake responsiveness, or sacrifice correctness. Preserve recovery access, touch usability, application state, and existing functionality.

Inspect the current repository and `docs/pwnage-37000.md` if present. Implement and test the changes, deploy through the established safe workflow, and document the actual results.

**DEFINITION OF DONE:** Nuxel feels dramatically snappier and smoother, renders its arcade UI with less overhead, stays responsive under load, and retains its recognizable penguin-powered personality. Prove the improvement with measurements rather than vibes alone.

MAKE IT BUTTERSCOTCH. MAKE IT BUTTERSMOOTH. PENGUIN GO BRRR. 🐧
