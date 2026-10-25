Implement three new animated status indicators in the **Nuxel lockscreen UI**, using these existing transparent PNG assets:

- `./assets/nuxel-charging.png` — Charger connected / charging
- `./assets/nuxel-connected-pc.png` — USB connected to a computer
- `./assets/nuxel-live-console-active.png` — Live console / root shell active

**Requirements:**

1. Deep-inspect the existing lockscreen, lockhead animations, status detection, and UI architecture before implementing.
2. Display all three indicators near the existing animated penguin lockhead, matching Nuxel's pixel-art visual style, sizing, glow, and animation behavior.
3. Each indicator must operate **completely independently**, allowing any combination of the three to be active simultaneously.
4. **Charging:** Illuminate and gently pulse when external power is connected. Add a subtle charging animation while the battery is actually charging. Turn off when disconnected.
5. **PC connected:** Illuminate with a soft cyan glow and subtle animation when a real USB data connection to a computer is established. Do not confuse ordinary USB charging with PC connectivity.
6. **Live console:** Illuminate with a subtle amber/red glow and animated pulse only when the actual live console/root-shell session is active. Never infer active status merely because root access is available.
7. Use the existing lockhead animation framework wherever possible. Add smooth fade-in/out, gentle breathing/pulsing, and subtle pixel-style glow. Keep animations lightweight and GPU-friendly.
8. Inactive indicators should remain visible but dimmed (approximately 20–30% opacity), without active glow.
9. Use real Linux system state through the existing Nuxel services (power_supply, USB gadget/UDC or appropriate connection state, and live-console session tracking). Prefer event-driven updates over polling.
10. Ensure indicators update immediately on connection/disconnection, survive screen lock/unlock, and initialize with correct states at boot. No fake states, hardcoded statuses, mocks, placeholders, or arbitrary delays.
11. Maintain correct transparency and aspect ratios of the PNG assets. Do not alter the original images.
12. Preserve all existing lockscreen functionality, responsiveness, and animations.

**Acceptance tests:** Verify all 8 possible combinations of the three independent indicators, including transitions while the lockscreen is visible. Confirm no false PC detection from charging-only cables, no false live-console detection, and no noticeable UI performance degradation.

Implement directly into the existing codebase, integrate fully, and report exactly which files were modified and how each indicator's real system state is detected.
