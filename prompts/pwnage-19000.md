# 🐧 NUXEL 19000 — PENGUIN INDICATOR PRECISION — GPT-5.6 SOL

Read `./NUXEL-A70-OPERATION-PENGUIN-INDICATOR-POSITION-SIZE-USB-TRUTH-19000-UBERPROMPT.md` **in full**. This is a lockscreen-only repair on my physical Nuxel S10+ with the three *already integrated* PNG icons. Start by checking today's Git code against the live deployed WebKit/PWA/bridge files and preserving rollback.

**Fix ONLY:** (1) move three indicators UP, directly below clock/date/battery and above center; (2) double the *actual visible penguin artwork size*, not just parent box size; (3) stop the middle USB PC icon showing when a charger-only cable is connected or after the computer is disconnected; the middle icon is only for proven USB data host enumeration. Preserve working charging and live-console detection. Inactive icons must disappear rather than stay ghosted. No new artwork, no lockhead changes, no OS-wide repairs.

The attached ZIP analysis points to `pwa/nuxel-home/css/lockscreen.css`, `index.html`, `js/lockscreen-indicators.js`, `services/nuxel-bridge/src/system_indicators.py`, and both nuxel PWA host C sources. In CSS note the 108px clamp, alpha-padding, and ineffective crop-only clip-path; in Python investigate `addressed`, stale `CONFIGURED`, and actual host enumeration. **Do not guess**—use real physical snapshots. Correct stale deployed files and versioned cache if needed.

Apply minimal reversible changes, run actual tests, deploy safely, photograph the phone before/after, prove 2× visible-size and desired placement, test wall charger vs PC cable and console activation, and report any unverified physical scenario honestly. **Leave Wi-Fi/browser/launcher/unlock working.**
