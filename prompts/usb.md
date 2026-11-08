# NUXEL v0.6.3-beta — LIVE S10+ USB DEPLOY 🐧

Read `DEPLOY-v0.6.3-beta.md`, `docs/releases/v0.6.3-beta.md` and `final.md`.

On the running SM-G975F, confirm USB connectivity, active static webroot and
service paths. Back up changed files and preserve rollback + console access.
Verify the supplied `nuxel-v0.6.3-beta-live-userspace.tar.gz` SHA256 manifest.
Deploy its launcher, dock assets, Browser registry, Settings and NetworkManager
bridge into the **active** userspace paths atomically, then restart only affected
services. Never flash or write a partition, kernel, modem or firmware.

Physically verify BG1/BG2 visuals, icon tapping, Home zoom prevention, bottom
half app-drawer swipes, Wi-Fi scan/join/DNS/HTTPS and Browser launch. For audio,
run `tools/s10plus/a33/nuxel-audio-diag.sh pipeline`, trace the actual Madera/
ALSA/UCM speaker route safely and report the first hardware blocker. No guessed
amplifier controls, no fake PASS from a successful decoder. Ask for my 90-second
physical PASS/FAIL test. Roll back failed changes. Record live hashes, services,
logs and owner confirmation separately.

**DO NOT claim all final.md hardware tasks are resolved without physical evidence.**

