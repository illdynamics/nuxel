# 🐧 PWNAGE 27000 — GPS UBERFIXER KICKSTARTER

Read and follow `NUXEL-27000-GPS-UBERFIXER-UBERPROMPT.md` in full.

Fix the remaining GPS, Location provider and Maps problems on Nuxel for the Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820.

### Main objectives

1. Diagnose why the Location Quick Setting says “No fix.” Trace the real GNSS hardware, kernel/driver, firmware, provider, permissions, Nuxel bridge and UI state. Never fake coordinates or treat a map search result as a GPS fix.

2. Fix Maps showing `no tile source configured`. Configure a valid tile source, ensure the actual renderer loads and displays tiles, provide correct OpenStreetMap attribution, and handle network errors, offline caching and missing tiles gracefully.

3. Fix duplicate Eindhoven/search pins, map labels, viewport updates and asynchronous search results. Keep search results, saved pins and genuine current GPS location distinct.

4. Make Location Quick Settings report the actual provider state: unavailable, disabled, searching, no fix, stale fix or fresh fix. Do not claim GPS is fixed when it is not.

5. Add or improve Location/GPS and Maps diagnostics in Settings, including provider status, last real fix age, accuracy where available, tile-source status and useful errors.

6. Add unit and integration tests for provider failures, stale fixes, invalid tile configuration, tile/network failures, offline cache behavior and duplicate pins.

### Safety

- Inspect the repository, Git diff, current services and tests first.
- Check for active agents, deployment processes and serial locks. If another PWNAGE task or physical deployment is active, perform read-only investigation until it is safe to proceed.
- Preserve working Wi-Fi, internet, browser, shell, lockscreen, charging indicator and serial Live Console.
- No kernel/firmware flashing, partition changes or data wipes.
- Do not fabricate hardware, GPS coordinates, satellite readings or successful tile loading.

### Verification

Run relevant tests and report exact commands and results. Distinguish code-level tests from physical-device tests. If the phone is accessible, test map tiles and obtain a genuine outdoor GNSS fix where possible. If kernel or hardware support is missing, identify the exact blocker and a safe follow-up.

Start with Phase Zero of the full uberprompt and proceed in small, reversible steps. Do not claim success without evidence.
